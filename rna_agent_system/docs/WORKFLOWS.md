# Workflows Reference

> **Scope**: all Layer-2 domain workflows — their pipelines, scoring formulas, and quality review strategies.  
> **Last updated**: 2026-07-06

---

## Table of Contents

1. [Base Interface](#1-base-interface)
2. [mRNA CDS Design](#2-mrna-cds-design)
3. [mRNA Sequence Scoring](#3-mrna-sequence-scoring)
4. [Full-Length mRNA Design](#4-full-length-mrna-design)
5. [siRNA Design](#5-sirna-design)
6. [sgRNA Handle Design](#6-sgrna-handle-design)
7. [RNA Secondary Structure → Sequence Design](#7-rna-secondary-structure--sequence-design)
8. [RNA Tertiary Structure → Sequence Design](#8-rna-tertiary-structure--sequence-design)
9. [RNA–Small Molecule Interaction](#9-rnasmall-molecule-interaction)
10. [RNA Aptamer Design](#10-rna-aptamer-design)
11. [IRES Prediction & Validation](#11-ires-prediction--validation)
12. [ASO Target Screening](#12-aso-target-screening)

---

## 1. Base Interface

All workflows inherit from `BaseDomainWorkflow`:

```python
class BaseDomainWorkflow(ABC, Generic[WorkflowInputT, WorkflowResultT]):
    name: str
    description: str
    required_capabilities: list[str]

    @abstractmethod
    def generate_candidates(self, inp: WorkflowInputT) -> list[Candidate]: ...
    @abstractmethod
    def evaluate(self, candidate: Candidate) -> dict[str, Any]: ...
    @abstractmethod
    def score(self, metrics: dict[str, Any]) -> dict[str, float]: ...

    def run(
        self,
        inp: WorkflowInputT,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResultT:
        candidates = self.generate_candidates(inp)
        if progress_callback:
            progress_callback({
                "event": "generate_complete",
                "candidate_count": len(candidates),
                "workflow": self.name,
            })
        for i, candidate in enumerate(candidates):
            try:
                metrics = self.evaluate(candidate)
                candidate.scores = self.score(metrics)
                candidate.status = "evaluated"
            except Exception:
                candidate.status = "failed"
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })
        return self.rank_and_format(candidates)
```

The authoritative `required_capabilities` list for each workflow is the class attribute in its source file. Required-capability blocks are reproduced below only for workflows where they are especially relevant; for the others, see the source file directly.

---

## 2. mRNA CDS Design

> **File**: `workflows/mrna_cds_design.py` | **QualityProfile**: `MRNA_CDS_QUALITY_PROFILE`

**Purpose**: Design optimal coding sequences from a protein sequence using LinearDesign, RNARL, and GEMORNA.

**Pipeline**
1. **Generate** — LinearDesign (λ = 0, 1, 4, 10), RNARL (1, only when the expression species has a supported RNARL checkpoint), GEMORNA (1); up to 6 candidates, deduplicated
2. **Evaluate** — GC content, U content (reference only), LinearFold MFE (ViennaRNA fallback), unpaired fraction, RNASTOP stability, CAI
3. **Score** — `total_score = -mfe + codon_count * log(CAI)`
4. **Rank** — by `total_score` descending; a **Pareto frontier annotation** (CAI max × MFE/nt min, the classic LinearDesign trade-off view) is attached as `pareto_frontier` extras + `pareto_frontier_size` in the summary — ranking itself is unchanged

**GenNav-λ navigation (opt-in, v1.2.0)**: set `navigation=True` to replace the static LinearDesign λ grid with the deterministic, zero-LLM constraint navigation (E6 evidence promoted to production; E8–E14 levers; pure core `agent_core/generation/gennav_mrna_lambda.py`): λ-curve probe {0, 1, 2, 4, 8, 10, 20, 50} → band-gap-first interstitial reinforcement (refinement λ set, 16-raw budget, cycling guarantee) → per-profile matrix delivery (expression/stability/balanced, 5 each, D1 diversity ≥ 0.15). Every LinearDesign/CAI/LinearFold call is audited; the full trace is written to `_state_writeback["_gennav_trace"]`; an empty delivery is the dedicated `navigation_delivery_empty` degrade. On the navigation path RNARL/GEMORNA are not called and `design_tool` is ignored for generation; evaluation/scoring/ranking are unchanged.

**Truncation support**: Set `truncate_n_terminal=N` to design only for the first N amino acids, or `truncate_c_terminal=N` for the last N. The original `protein_sequence` is preserved in the audit trail; the workflow saves and uses the truncated region.

**RNARL species note**: RNARL only supports the model types listed in `agent_core/constants/species.py` (`RNARL_MODEL_TYPES_LIST`). When `cai_species` does not map to one of those checkpoints (e.g. yeast), RNARL is skipped rather than silently run with the wrong organism model.

**QualityAgent** (advisory by default): produces a `QualityReport`; the `SpecialistAgent` decides retry only on hard failures. Adjustable params: `design_tool`, `lambda_value`, `model_type`, `cai_species`.

**Required capabilities**
```python
["design_mrna_cds_with_lineardesign", "design_mrna_cds_with_rnarl", "design_mrna_cds_with_gemorna",
 "predict_rna_secondary_structure", "predict_rna_secondary_structure_with_linearfold",
 "compute_rna_sequence_gc_content", "compute_rna_sequence_u_content",
 "compute_dot_bracket_unpaired_fraction", "predict_mrna_stability_with_rnastop",
 "compute_cai_for_cds_sequence"]
```

---

## 3. mRNA Sequence Scoring

> **File**: `workflows/mrna_sequence_scoring.py` | **QualityProfile**: **None** (deterministic ranking-only)

**Purpose**: Evaluate existing mRNA sequences with GC content, secondary-structure MFE, and CAI — no generation step.

**Pipeline**: `generate_candidates()` (wrap input sequence(s)) → `evaluate()` (GC + LinearFold/ViennaRNA + CAI) → `score()` → `rank_and_format()`

**Scoring**
```python
combined_score = -mfe + codon_count * math.log(cai)
total_score = combined_score
```

**Required capabilities**
```python
["compute_rna_sequence_gc_content", "predict_rna_secondary_structure_with_linearfold",
 "predict_rna_secondary_structure", "compute_cai_for_cds_sequence"]
```

---

## 4. Full-Length mRNA Design

> **File**: `workflows/full_length_mrna_design.py` | **QualityProfile**: `FULL_LENGTH_MRNA_QUALITY_PROFILE`

**Purpose**: Design complete mRNA (5'UTR + CDS + 3'UTR). Reuses `MrnaCdsDesignWorkflow` for CDS, then appends UTR combinations and evaluates full-length metrics, ranking by reference-point (ASF) optimization.

**Pipeline**
1. **Generate** — CDS via `MrnaCdsDesignWorkflow` × UTR presets (short/medium/long) → full-length candidates
2. **Evaluate** — full-length MFE, 5'UTR MRL, 3'UTR stability, U content, **full-length GC content**, **junction MFE** (5'UTR–CDS, CDS–3'UTR), **junction GC diff**, **junction full-length ddG** (5'UTR–CDS, report-only; IRES potential and RNASTOP overall stability are computed by underlying tools but are not propagated into the coordinator metrics in the current implementation)
3. **Score** — per-module raw scores are computed for reference-point optimization
4. **Rank** — `rank_and_format()` sorts candidates by ASF distance to the reference point and returns a Pareto frontier on the user-facing objectives

**Reference-point ranking**

`best_candidate` selection uses a normalized objective space:

- Each objective is converted to maximization space and min-max normalized within the candidate pool.
- The reference point is user-provided (`reference_point`) or auto-derived as the utopian point (best observed value per dimension).

**User-facing score dimensions** (valid `reference_point` keys)

| Dimension | Module(s) | Interpretation |
|-----------|-----------|----------------|
| `utr5_mrl` | 5'UTR | Predicted mean ribosomal load (higher = better) |
| `utr3_stability` | 3'UTR | Predicted 3'UTR stability (higher = better) |
| `full_mfe_score` | 5'UTR, CDS, 3'UTR | Inverted full-length MFE (higher = less negative) |

The CDS dimension is supplied indirectly via `target_cds_mfe` and `target_cds_cai` (see below); it is synthesized into the internal `cds_component` = (`-mfe + codons*log(CAI)`) / `cds_length_nt`.

**Internal diagnostic dimensions** (not exposed as `reference_point` keys)

| Dimension | Module(s) | Interpretation |
|-----------|-----------|----------------|
| `junction_5utr_cds_score` | 5'UTR, CDS | Inverted 5'UTR–CDS junction MFE/nt minus GC-diff penalty |
| `junction_cds_3utr_score` | CDS, 3'UTR | Inverted CDS–3'UTR junction MFE/nt minus GC-diff penalty |

The junction GC-diff compares the GC content of the actual UTR and CDS fragments at the junction boundary (e.g. the last 20 nt of 5'UTR vs the first 20 nt of CDS), not the midpoint of the concatenated overlap sequence. This ensures the metric reflects the GC continuity across the biological boundary, even when one side is shorter than the 20-nt overlap window. The penalty coefficient is `1.0` so that MFE and GC-smoothness contribute on comparable scales.

**Issue types & actions**

| Issue type | Meaning | Action |
|------------|---------|--------|
(The BMC coordination layer that consumed these gap diagnoses was removed on
2026-08-18 after triple falsification — DECISIONS.md (a), (m). The ASF
reference-point ranking above is unaffected.)

> **Note (v2.8.0)**: The fragment-fold AUG/Kozak burial booleans and the junction codon-shuffling repair path were removed after three pre-registered experiments (P1 v2, P2, Phase 0 ddG pilot) falsified fragment burial as a translation-initiation proxy. Translation-start openness at the 5'UTR–CDS junction is now reported as a full-length constrained-fold ddG (`junction_5utr_cds_ddg_open_w1/w2` = MFE_constrained − MFE_unconstrained on the full construct, W1 = CDS start −6..+9, W2 = 5'UTR tail 60 nt + CDS head 30 nt clipped to the actual UTR). ddG is a report/profile metric only — it never triggers automatic repair.

**Scoring**

`rank_and_format()` sorts candidates by ASF distance to the reference point. Per-module raw metrics include CDS `-mfe + codons*log(CAI)`, 5'UTR MRL, 3'UTR stability, full-length MFE, and junction MFE/GC-diff.

**Reference-point optimization (default, v2.5.0)**

`best_candidate` is always selected by Achievement Scalarizing Function (ASF) distance to the reference point described above. Each dimension is min-max normalized within the candidate pool:

```python
ASF = max_i { w_i * (r_i - s_i) } + rho * sum_i { w_i * |r_i - s_i| }
```

User-facing valid `reference_point` keys: `utr5_mrl`, `utr3_stability`, `full_mfe_score`. The CDS objective is supplied via `target_cds_mfe` and `target_cds_cai`. Weights default to equal over the specified dimensions.

**Shared ASF ranking policy (2026-08-20 audit; 2026-08-22 every ASF workflow surfaces the Pareto frontier)**

All ASF-ranking workflows share one implementation
(`workflows/multi_objective.py::apply_reference_point_ranking`) with these
semantics:

- **Per-candidate missing dimension → pool-worst imputation.** Omitting a
  dimension from a candidate's Chebyshev max can only lower its ASF, so the
  pre-2026-08-20 omission semantics rewarded evaluation failures; a missing
  measurement now ranks exactly like the measured pool-worst value and no
  longer distorts the min-max normalization of measured candidates.
- **Pool-wide unmeasured dimension → dropped for everyone.** An oracle gated
  off by CapGate (e.g. `utr3_stability` in enforce mode) or a disabled
  optional evaluator disappears from the ranking for the whole pool equally
  and is reported via `asf_ranking_note` in the summary.
- **Partial user reference point → loud restriction.** A `reference_point`
  covering only a subset of the measurable dimensions restricts the ranking
  to that subset; this is flagged (`asf_ranking_note`, logged warning) rather
  than applied silently.
- **Weights** are renormalized to sum 1 over the ranking dimensions; uniform
  by default.
- The Pareto frontier is always computed on raw measured values with
  conservative dominance (a candidate missing a dimension cannot dominate one
  that has it).

**Ranking governance (2026-08-21, DECISIONS (p))**

Before ranking, every ASF workflow assembles its objective set from CapGate
verdicts (`agent_core/calibrated/objective_assembly.py`, design doc
[`RANKING_GOVERNANCE.md`](RANKING_GOVERNANCE.md)):

- verified oracle → dimension kept; transferred-verified → kept + flag;
  failed (direct or transferred) → **demoted to `scoring_annotation`**
  (excluded from ranking pool-wide equally; value/gated marker still
  reported); pending oracles (CRISOT-Score / CRGPT) → kept + `pending` flag;
  unprofiled-enforce → kept + `unprofiled` flag; deterministic compute
  metrics never enter the mechanism.
- Assembly is **mode-independent**: advisory and enforce produce the same
  ranking wherever SelfModel records exist — this resolves the pre-2026-08-21
  state where advisory ranked by falsified metrics while enforce crashed or
  silently returned generation order.
- Under the packaged SelfModel the aptamer trio (EGARPS/RhoFold/ipTM) is
  fully demoted: `rna_aptamer_design` returns the
  `ranking_evidence_unavailable` degrade (success=True, generation order,
  annotations intact, no fabricated `asf_distance`), and the light-stage
  RhoFold pLDDT top-k filter degrades to deterministic pool order.
- Every run records `_state_writeback["_ranking_governance"]`
  (ranking_dims / kept_flags / demoted / degrade_reason) and one
  `ranking_objective_assembly` audit event.


**User-friendly CDS targets**

Users must specify CDS objectives via `target_cds_mfe` (kcal/mol) and `target_cds_cai`; the internal `cds_component` is no longer accepted as a user-facing `reference_point` key. When both `target_cds_mfe` and `target_cds_cai` are supplied, the workflow converts them:

```python
cds_component = (-target_cds_mfe + codons * log(target_cds_cai)) / cds_length_nt
```

**Pareto frontier output (default, v2.5.0)**

The non-dominated candidate set is always returned in `WorkflowResult.pareto_frontier`, computed on the four user-facing objectives. Each frontier member may carry `metadata["pareto_tag"]` indicating the dimension it leads in (e.g., `cds_component`, `full_mfe_score`, `balanced`). The frontier is capped at 10 members to keep responses manageable.

**QualityAgent** (advisory by default): produces a `QualityReport` for every run. The `SpecialistAgent` decides workflow-level retry based on the `QualityReport`; retry is only triggered on hard failures (empty candidates, tool failures, sequence anomalies). Soft suggestions are reported to the user for confirmation.

**Required capabilities**
```python
["design_5utr_with_gemorna", "design_3utr_with_gemorna",
 "predict_5utr_mrl_with_gemorna", "predict_3utr_stability_with_gemorna",
 "design_mrna_cds_with_lineardesign", "design_mrna_cds_with_rnarl",
 "design_mrna_cds_with_gemorna", "compute_cai_for_cds_sequence",
 "compute_rna_sequence_gc_content", "compute_dot_bracket_unpaired_fraction",
 "predict_rna_secondary_structure",
 "predict_rna_secondary_structure_with_linearfold",
 "predict_mrna_stability_with_rnastop", "compute_rna_sequence_u_content"]
```

---

## 5. siRNA Design

> **File**: `workflows/sirna_design.py` | **QualityProfile**: `SIRNA_QUALITY_PROFILE`

**Purpose**: Design siRNA guides with safety gating on off-target count and specificity.

**Modes**
- `antiviral` — Evitar design (port 8016)
- `generic` — Sliding window (21 nt, step 1) over target sequence; local GC/homopolymer filters

**Evaluation**: GC content, duplex MFE (ViennaRNA RNAcofold), off-target scan (Bowtie2 by default; BLAST optional via `alignment_tool`)

**Scoring**

```python
total_rank = rank(duplex_mfe) + rank(off_target_count)   # smaller = better; diagnostics only
```

The legacy weighted formula is not used for ranking.

**Ranking (ASF, 2026-08-20; asymmetry dimension added same day)**:
candidates are ordered by ASF reference-point distance over the three
heterogeneous objectives `efficiency_component` (−duplex MFE / 40, clamped
[0, 1]), `specificity_component` (1 / (1 + off_target_count)) and
`asymmetry_component` (thermodynamic end asymmetry from the sirna-duplex
service: terminal 5-bp nearest-neighbour evaluation,
`asymmetry = ΔG(antisense 5′ end) − ΔG(sense 5′ end)`, higher = antisense
5′ end less stable = preferential guide loading — Khvorova 2003 / Schwarz
2003; mapped linearly −3→0, 0→0.5, +3→1 kcal/mol), utopian reference,
uniform weights. On service instances without the v0.5.0 asymmetry keys the
dimension drops pool-wide. The Borda
`total_rank` is retained as a reported diagnostic but no longer drives the
ordering. Missing measurements impute at pool-worst (shared
`apply_reference_point_ranking` policy, see §2). The full passing pool is
ranked first and only then truncated to `candidate_count` — the returned
top-N are the globally best-N (the pre-2026-08-20 truncate-then-rank order
could drop a window beyond position N in generation order before it was
ever ranked). Since v1.3.1 (2026-08-22) the Pareto frontier is surfaced as
`pareto_frontier` extras + `pareto_frontier_size` (shared-layer consistency
across every ASF workflow).

**Required capabilities**
```python
["design_sirna_with_evitar", "compute_rna_sequence_gc_content",
 "compute_sirna_duplex_binding_vienna", "predict_rna_secondary_structure",
 "predict_rna_secondary_structure_with_linearfold",
 "run_blastn_similarity_search", "run_bowtie2_short_alignment"]
```

**QualityAgent** (advisory by default): produces a `QualityReport`. The `SpecialistAgent` decides retry only on hard failures.

---

## 6. sgRNA Handle Design

> **File**: `workflows/sgrna_design.py` | **QualityProfile**: `SGRNA_QUALITY_PROFILE`

**Purpose**: Optimize sgRNA handle sequences using CRGPT, with optional CRISOT off-target scoring.

**Pipeline**: seed handle → CRGPT design (mcmc/naive) → CRGPT re-score → optional CRISOT → component scoring → ASF rank (+ `pareto_frontier` extras surfacing, v1.3.1)

**Scoring**
```python
nn_component = 1.0 / nn_score  # clamped [0, 1]
crisot_component = clamp(crisot_score, 0.0, 1.0)
total_score = (weight_nn * nn_component + weight_crisot * crisot_component) / active_weights  # diagnostic
```

**Ranking (ASF, 2026-08-20)**: candidates are ordered by ASF reference-point
distance over `nn_component` / `crisot_component` /
`crisot_specificity_component` (utopian reference; `weight_nn_score`,
`weight_crisot`, `weight_crisot_specificity` are renormalized as ASF weights
over the measurable dimensions). The weighted `total_score` is retained as a
reported diagnostic. Components whose source metric is absent are treated as
unmeasured (pool-worst imputation; a dimension absent pool-wide — e.g. CRISOT
off — drops for everyone).

**QualityAgent** (advisory by default): produces a `QualityReport`. The `SpecialistAgent` decides retry only on hard failures. Adjustable params: `n_samples`, `mutation_number`, `temperature`, `sampling_mode`, `max_overlap`, `evaluate_crgpt_score`, `evaluate_crisot`, `weight_nn_score`, `weight_crisot`.

---

## 7. RNA Secondary Structure → Sequence Design

> **File**: `workflows/rna_secondary_structure_design.py` | **QualityProfile**: `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE`

**Purpose**: Design RNA sequences from a target secondary structure (dot-bracket) using ViennaRNA `RNAinverse`. No PDB or GPU required.

**Prerequisites**: ViennaRNA (port 8003), RNA metrics (port 8020)

**Pipeline**: validate input → `inverse_fold_rna_secondary_structure_vienna` (`num_invocations` × `repeats`, default `repeats=10`) → deduplicate → GC + RNAfold validation → structure-distance scoring → rank

**Input notes**
- `repeats` default is **10**.
- `temp_c` sets the folding temperature (°C).
- `function_mode` selects inverse-folding mode (`m`, `p`, or `mp`).

**Scoring**: `total_score = structure_distance / sequence_length` (smaller is better; 0 = perfect match)

**QualityAgent** (advisory by default): produces a `QualityReport`. The `SpecialistAgent` decides retry only on hard failures.

---

## 8. RNA Tertiary Structure → Sequence Design

> **File**: `workflows/rna_tertiary_structure_design.py` | **QualityProfile**: `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE`

**Purpose**: Design RNA sequences from a 3D structure (PDB/CIF) using RhoDesign and/or RiboDiffusion, validated with RhoFold and structure alignment.

**Prerequisites**: RhoDesign (8006), RiboDiffusion (8021), RhoFold (8005), biopython

**Pipeline**: resolve structure path (PDB ID fallback) → RhoDesign + RiboDiffusion generation → deduplication → evaluate (GC + MFE + RhoFold pLDDT + RMSD/TM-score) → score → ASF rank (+ `pareto_frontier` extras surfacing, v1.2.1)

**Structure-path resolution**
- `structure_filepath` accepts a repo-relative path, absolute path, or PDB ID.
- A PDB ID such as `"1ehz"` is resolved against `data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/structures/1ehz_clean.pdb`.
- `secondary_structure_filepath` accepts a path or PDB ID and resolves the corresponding `{id}_contact_map.npy`.

**RhoDesign defaults**
- `rhodesign_temperature = 0.8`
- `rhodesign_temperature_range = 0.5`
- Each temperature sample uses a distinct random seed to ensure diversity.
- The default sweep [0.3, 0.8, 1.3] for `n_samples_per_tool=3` is chosen so that RhoDesign produces three distinct sequences on typical tRNA targets while keeping recovery rates above ~0.9.

**RiboDiffusion preprocessing**
- Modified nucleotides in HETATM records (e.g., 2MG, PSU) are canonicalized to A/C/G/U before upstream parsing so the output sequence length matches the input structure.

**Scoring**
```python
rhofold_component = pLDDT / 100
rmsd_component    = max(0, 1 - RMSD / 5.0)
total_score       = 0.5 * rhofold_component + 0.5 * rmsd_component   # diagnostic
```

**Ranking (ASF, 2026-08-20)**: candidates are ordered by ASF reference-point
distance over `rhofold_component` / `rmsd_component` / `tm_component`
(utopian reference; `weight_rhofold` / `weight_rmsd` / `weight_tm_score` are
renormalized as ASF weights). The TM-score dimension is injected at ranking
time from the already-computed alignment TM-score — it stays informative
where RMSD saturates (≥ 5 Å clamps to 0). The weighted `total_score` is
retained as a reported diagnostic. In de-novo runs without a reference
structure both native-closeness dimensions are unmeasured pool-wide and drop
out for everyone; per-candidate misses impute at pool-worst.

**Weight guidance (audit follow-up)**: with the default 0.5/0.5/0.5 weights
the pool-relative min-max normalization can let a pLDDT champion outrank the
native-closest candidate when the latter has pool-worst pLDDT. RMSD and
TM-score are measured against the actual reference structure while pLDDT is
model self-confidence; when a reference exists, lower `weight_rhofold`
below the closeness weights (e.g. 0.3 vs 0.5/0.5) so the two reference-based
dimensions outvote the confidence dimension.

**QualityAgent** (advisory by default): produces a `QualityReport`. The `SpecialistAgent` decides retry only on hard failures.

**Input notes**
- `structure_filepath` accepts a repo-relative path, absolute path, or PDB ID (resolved against `data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/structures/`).
- `weight_rhofold` and `weight_rmsd` act as the ASF dimension weights (defaults 0.5 each); the blend they previously controlled survives only as the reported `total_score` diagnostic.

**Known third-party limitations on tRNA-Phe 1EHZ**
- RiboDiffusion can collapse to wild-type-like sequences for this target.
- RhoFold single-sequence prediction fails to recapitulate the native fold for 1EHZ, so RMSD/TM-score metrics are dominated by the predictor, not the workflow.

---

## 9. RNA–Small Molecule Interaction

> **File**: `workflows/rna_small_molecule_interaction.py` | **QualityProfile**: **None**

**Purpose**: Predict RNA-small molecule binding propensity for a given RNA sequence and ligand SMILES. Runs RNAsmol and/or GerNA-Bind, averages their probability scores.

**Prerequisites**: RNAsmol (8007), GerNA-Bind (8010)

**Pipeline**: validate (RNA + SMILES) → wrap as single `Candidate` → RNAsmol + GerNA-Bind scoring → average probabilities → rank

**Scoring**: `total_score = average(available probability_positive values)`

---

## 10. RNA Aptamer Design

> **File**: `workflows/rna_aptamer_design.py` | **QualityProfile**: `RNA_APTAMER_QUALITY_PROFILE`

**Purpose**: Design RNA aptamers targeting a protein using ODesign, then validate with ProteinX complex prediction, EGARPS scoring, and interface analysis.

**Pipeline**: hotspot identification → `build_odesign_aptamer_input_json` → `run_odesign_inference` (8012) → hierarchical evaluate (light stage: GC + RhoFold 8005 on all candidates; full stage: ProteinX 8022 + EGARPS 8023 + interface analysis on top `max(5, int(n*0.5))` candidates; EGARPS gated by RhoFold ≥ 65 and GC ∈ [0.25, 0.85]) → score → ASF reference-point ranking

**Required capabilities**

```python
[
    "identify_protein_binding_hotspots",
    "build_odesign_aptamer_input_json",
    "run_odesign_inference",
    "compute_rna_sequence_gc_content",
    "predict_rna_secondary_structure_with_linearfold",  # navigation-mode constraint matrix folding
    "predict_rna_tertiary_structure_with_rhofold",
    "score_rna_protein_complex_with_egarps",
    "extract_rna_sequence_from_cif",
    "predict_rna_protein_complex_with_proteinx",
    "analyze_rna_protein_interface",
    "predict_protein_structure_with_proteinx",  # used only when protein_sequence is provided without a structure file
]
```

**Scoring**

`score_aptamer_candidate()` returns per-objective raw scores normalized to `[0, 1]`:

```python
{
    "egarps_component": egarps_native_probability,
    "rhofold_component": rhofold_mean_plddt / 100,
    "iptm_component": proteinx_ipTM,
}
```

There is no weighted-sum `total_score`. Ranking is performed by Achievement Scalarizing Function (ASF) distance to a reference point.

An unavailable oracle measurement yields a `None` component (not 0.0): the shared ASF layer imputes pool-worst for per-candidate misses and drops pool-wide unmeasured dimensions for everyone (see the shared ASF ranking policy in §2; previously a 0.0 literal both penalized skipped candidates as if measured and distorted the min-max normalization of the measured ones).

**Reference-point optimization (default, v1.4.0)**

`best_candidate` is always selected by ASF distance to a reference point. Users can supply a `reference_point` dictionary; if omitted, a utopian point is derived from the candidate pool. Each objective is min-max normalized within the candidate pool. Valid keys: `egarps_component`, `rhofold_component`, `iptm_component`.

The candidate list in `WorkflowResult.all_candidates` is sorted by ASF distance (`asf_distance`), with the best candidate first.

**Pareto frontier output (default, v1.4.0)**

The non-dominated candidate set is always returned in `WorkflowResult.pareto_frontier`. Frontier members are tagged by their leading dimension and capped at 10 members.

**GenNav navigation mode (opt-in, v2.1.0)**

Setting `navigation: true` replaces the single static ODesign gear with the E14-validated generation-layer constraint navigation (pure-function core: `agent_core/generation/gennav_aptamer.py`):

1. **Lattice probe** — one ODesign sample at each of the 17 densified lattice lengths (25–80 nt, seed 42), each candidate folded with LinearFold (8015) and graded against the pre-registered constraint matrix v3 (per-profile length band, GC window, homopolymer cap, stem cap).
2. **Guaranteed-repair reinforcement** — cycling allocation (one round per repairable delivery band before any band's second) of ODesign requests (≤ 6 samples, seeds 7/99) chosen by Laplace-smoothed per-length pass rates; mechanized band-gap-first proposals fill any remaining budget. Deterministic — zero LLM calls.
3. **Per-profile delivery** — matrix-pass filter → fixed utility order (stem asc, |GC−0.55| asc) → D1 greedy top-5 (pairwise normalized edit distance ≥ 0.15) per profile (compact 25–34 / standard 40–55 / extended 61–80 nt). Shortfalls are explicit degrades.

The generation budget is capped at 48 raw candidates per run; the loop stops early once every profile is deliverable. Every ODesign/LinearFold call goes through the capability layer (CapGate audit trail), and the full navigation trace (probe, rounds, gaps, deliveries) is written to `_state_writeback["_gennav_trace"]`. Delivered candidates then enter the standard two-stage evaluation and ASF ranking with `nav_bands` / `nav_gear` / `nav_matrix_pass` metadata. A run where no candidate passes any profile fails with the dedicated `navigation_delivery_empty` error (explicit degrade, not a silent empty result).

**QualityAgent** (advisory by default): produces a `QualityReport` for every run. The `QualityAgent` focuses on user-intent alignment and exploration strategy. Retry decisions are made by the `SpecialistAgent` based on the `QualityReport` and the `quality_auto_retry` setting; retry is triggered on hard failures (tool failures, empty candidates).

> **History**: the BMC Type-II coordination layer (`AptamerCoordinator` rounds:
> hotspot expansion / length-seed-sample adjustments) was removed on
> 2026-08-18 after the coordination-gain narrative was falsified
> (DECISIONS.md (a), (m)); the ASF/Pareto ranking shown above is unchanged.
> The E6 mRNA-side λ-lattice navigation remains validated campaign machinery
> (evidence under `experiments/results/`); the distilled production core is
> the aptamer-side module above.

---

## 11. IRES Prediction & Validation

> **File**: `workflows/ires_prediction.py` | **QualityProfile**: `IRES_QUALITY_PROFILE`

**Purpose**: Identify potential IRES elements within a 5'UTR or candidate sequence, with structural validation.

**Pipeline**: IRESfinder prediction (port 8013; modes 0/1/2) → extract candidates (threshold > 0.5, merge overlaps) → structural validation (LinearFold primary / ViennaRNA fallback, RNAplfold accessibility, unpaired fraction) → score → rank

**Required capabilities**
```python
["predict_putative_ires_with_iresfinder",
 "predict_rna_secondary_structure_with_linearfold",
 "predict_rna_secondary_structure",
 "predict_rna_local_accessibility_profile_vienna",
 "compute_dot_bracket_unpaired_fraction"]
```

**Scoring**
```python
composite_score = ires_probability
```

Structural metrics (MFE, unpaired fraction, RNAplfold) are reported in candidate metadata for user inspection and `QualityAgent` review, but they are not folded into the numeric score.

**QualityAgent** (advisory by default): produces a `QualityReport`. The `SpecialistAgent` decides retry only on hard failures.

**Empty-result contract** (2026-08-22, Layer-4 audit): a scan that *ran* and found nothing returns `success=True` with `"No IRES candidate regions found."` (benchmark rubric `min_candidates=0`). A *generation tool failure* (e.g. IRESfinder erroring on a missing input file) is a hard failure: `success=False` with the tool error surfaced via `_generation_errors` — never mistaken for a legitimate no-hit. Pinned by `tests/test_layer4_fresh_audit_regressions.py`.

**Confidence assignment**

| IRES probability | Unpaired fraction | Confidence |
|------------------|-------------------|------------|
| ≥ 0.8 | 0.3–0.7 | high |
| ≥ 0.6 | 0.2–0.8 | medium |
| ≥ 0.5 | any | low |
| < 0.5 | any | rejected |

Without structural data: downgrade one tier.

---

## 12. ASO Target Screening

> **File**: `workflows/aso_target_screening.py` | **QualityProfile**: **None** (deterministic)

**Purpose**: Screen a full-length mRNA to identify the most accessible regions for ASO binding.

**Pipeline**: RNAplfold accessibility profile (8003) → sliding-window scan (15–20 nt) → reverse-complement ASO design → binding evaluation (RNAup or RNAcofold, 8003) → ASF reference-point ranking (Borda ranks retained as diagnostics)

**Scoring (v1.1.0, 2026-08-22)**: candidates are ordered by augmented-Chebyshev ASF distance over `accessibility_component` (mean unpaired prob, max) and `binding_component` (−ΔG, max) via the shared `apply_reference_point_ranking` layer (utopian reference, uniform weights); missing measurements impute at the measured pool-worst value (never 0.0-literal fills). The Borda `sum_rank = accessibility_rank + binding_rank` is retained as a reported diagnostic but no longer drives the ordering (the siRNA v1.3.0 precedent). `composite_score` keeps its meaning (final rank, 1 = best); `asf_distance` is added to candidate scores and `AsoSite`; the Pareto frontier is attached as extras + `pareto_frontier_size`.

---

## Workflow Landscape Summary

### Quality review coverage

Quality review is performed by the unified `QualityAgent` using workflow-specific `QualityProfile` instances from `agent_core/quality_profiles/`.

| Priority | Domain | Workflow | Quality review | QualityProfile |
|----------|--------|----------|----------------|----------------|
| P0 | mRNA | CDS design | ✅ Yes | `MRNA_CDS_QUALITY_PROFILE` |
| P0 | mRNA | Full-length mRNA design | ✅ Yes | `FULL_LENGTH_MRNA_QUALITY_PROFILE` |
| P1 | siRNA | siRNA design | ✅ Yes | `SIRNA_QUALITY_PROFILE` |
| P1 | structure | 2° structure → sequence | ✅ Yes | `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` |
| P1 | structure | 3° structure → sequence | ✅ Yes | `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE` |
| P1 | mRNA | IRES prediction | ✅ Yes | `IRES_QUALITY_PROFILE` |
| P2 | mRNA | mRNA sequence scoring | ❌ No | — |
| P2 | ligand | RNA–small molecule interaction | ❌ No | — |
| P2 | RNA-protein | Aptamer design | ✅ Yes | `RNA_APTAMER_QUALITY_PROFILE` |
| P2 | CRISPR | sgRNA handle design | ✅ Yes | `SGRNA_QUALITY_PROFILE` |
| P2 | ASO | ASO target screening | ❌ No | — |

### Retry behavior

The execution engine is `PipelineAgent` + `SpecialistAgent` + `QualityAgent` + `SynthesisAgent`. The `SpecialistAgent` invokes `QualityAgent` to produce a `QualityReport` for workflows that have a `QualityProfile`. In advisory mode (`quality_auto_retry=False`), the `QualityReport` is recorded but the `SpecialistAgent` retries only on hard failures (`success=False`, empty candidates, or tool errors). In auto-retry mode (`quality_auto_retry=True`), the `SpecialistAgent` may re-run the workflow with overrides when the `QualityReport` recommends adjustments.

*For per-tool specs and microservice details, see [`TOOLS.md`](TOOLS.md).  
For architecture and core module APIs, see [`ARCHITECTURE.md`](ARCHITECTURE.md).*
