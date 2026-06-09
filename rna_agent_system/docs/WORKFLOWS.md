# Workflows Reference

> **Scope**: all Layer-2 domain workflows — their pipelines, scoring formulas, critic strategies, and relationships.
> **Last updated**: 2026-06-01

---

## Table of Contents

1. [Base Interface](#1-base-interface)
2. [mRNA CDS Design](#2-mrna-cds-design)
3. [Full-Length mRNA Design](#3-full-length-mrna-design)
4. [siRNA Design](#4-sirna-design)
5. [sgRNA Handle Design](#5-sgrna-handle-design)
6. [RNA Secondary Structure → Sequence Design](#6-rna-secondary-structure--sequence-design)
7. [RNA Tertiary Structure → Sequence Design](#7-rna-tertiary-structure--sequence-design)
8. [RNA–Small Molecule Interaction](#8-rnasmall-molecule-interaction)
9. [RNA Aptamer Design](#9-rna-aptamer-design)
10. [IRES Prediction & Validation](#10-ires-prediction--validation)
11. [ASO Target Screening](#11-aso-target-screening)
12. [Workflow Landscape Summary](#12-workflow-landscape-summary)

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

    def run(self, inp: WorkflowInputT) -> WorkflowResultT:
        candidates = self.generate_candidates(inp)
        for candidate in candidates:
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
        return self.rank_and_format(candidates)
```

---

## 2. mRNA CDS Design

> **File**: `workflows/mrna_cds_design.py`  
> **Class**: `MrnaCdsDesignWorkflow`  
> **Input model**: `MrnaCdsDesignInput`  
> **Critic**: `MrnaCdsDesignLLMCritic` ✅ (registered in `workflows/registry.py`)
> **Status**: ✅ **INTERFACE LOCKED** — see [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) §8

### 2.1 Purpose

Design optimal coding sequences from a protein sequence. Uses multiple CDS design tools (LinearDesign, RNARL, GEMORNA) to generate diverse candidates, evaluates each with structural and expression metrics, scores and ranks them.

### 2.2 Pipeline

1. **Candidate generation** (`generate_candidates()`)
   - LinearDesign: λ = 0, 1, 4, 10 (4 candidates)
   - RNARL (1 candidate, GPU)
   - GEMORNA (1 candidate, GPU)
   - Total up to 6, deduplicated by sequence
2. **Evaluation** (`evaluate()`) — per candidate
   - GC content (`compute_rna_sequence_gc_content`, port 8020, CPU)
   - U content (`compute_rna_sequence_u_content`, port 8020, CPU) — reference metric only
   - Secondary structure MFE (`predict_rna_secondary_structure_with_linearfold`, LinearFold port 8015, CPU)
   - Fallback: `predict_rna_secondary_structure` (ViennaRNA port 8003, CPU)
   - Unpaired fraction (`compute_dot_bracket_unpaired_fraction`, port 8020, CPU)
   - RNASTOP overall stability (`predict_mrna_stability_with_rnastop`, port 8009, GPU)
   - CAI (`compute_cai_for_cds_sequence`, pure Python, CPU)
3. **Scoring** (`score()`)
   ```python
   total_score = -mfe + codon_count * log(CAI)
   ```
   where `codon_count = sequence_length // 3`
4. **Ranking** (`rank_and_format()`): sort by `total_score` descending

### 2.3 Critic strategy (`MrnaCdsDesignLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `MRNA_CDS_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - CAI: > 0.8 good for human, < 0.4 poor
  - MFE: more negative = more stable; too negative may impede translation
  - GC content, U content, and unpaired fraction: reported for reference only (not in score)
  - RNASTOP `overall_stability`: closer to 1.0 = higher predicted stability
  - LinearDesign λ trade-off: λ=0 favors MFE (most stable), λ→∞ favors CAI
  - Tool diversity: if all candidates from same tool, suggest switching
- **Adjustable params**:
  - `design_tool`: enum `["lineardesign", "rnarl", "gemorna", "all"]`
  - `lambda_value`: float [0.0, 20.0]
  - `model_type`: RNARL model type (7 choices)
  - `cai_species`: species string for CAI computation
- **Retry action**: `retry_with_adjustments` or `retry_with_alternative`
- **Parameter override filtering**: only keys in `CriticConfig.adjustable_params` are accepted; unknown keys are dropped with a warning

### 2.4 State writeback

The workflow result includes `_state_writeback` containing:
- `_workflow_params`: the exact input parameters used
- All tool results from the workflow's internal execution

This is consumed by `ExecutionController._run_step()` to merge workflow internal state into the outer agent state.

### 2.5 Input model (`MrnaCdsDesignInput`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `protein_sequence` | `str` | **required** | Amino-acid string (uppercase, 1-letter) |
| `design_tool` | `Literal` | `"all"` | `"lineardesign"`, `"rnarl"`, `"gemorna"`, `"all"` |
| `lambda_value` | `float` | `None` | LinearDesign MFE/CAI trade-off [0, +∞). Required when `design_tool="lineardesign"` |
| `model_type` | `Literal` | `"Homo sapiens mRNA"` | RNARL model type (7 choices) |
| `cai_species` | `str` | `"Homo sapiens"` | Species for CAI computation |
| `run_fold` | `bool` | `True` | Whether to run secondary structure prediction |
| `run_gc` | `bool` | `True` | Whether to compute GC content |

### 2.6 Required capabilities

```python
required_capabilities = [
    "design_mrna_cds_with_lineardesign",      # port 8014, CPU
    "design_mrna_cds_with_rnarl",             # port 8008, GPU
    "design_mrna_cds_with_gemorna",           # port 8004, GPU
    "predict_rna_secondary_structure",        # port 8003, CPU
    "predict_rna_secondary_structure_with_linearfold",  # port 8015, CPU
    "compute_rna_sequence_gc_content",        # port 8020, CPU
    "compute_rna_sequence_u_content",         # port 8020, CPU
    "compute_dot_bracket_unpaired_fraction",  # port 8020, CPU
    "predict_mrna_stability_with_rnastop",    # port 8009, GPU
    "compute_cai_for_cds_sequence",           # pure Python, CPU
]
```

---

## 3. Full-Length mRNA Design

> **File**: `workflows/full_length_mrna_design.py`  
> **Class**: `FullLengthMrnaDesignWorkflow`  
> **Critic**: `FullLengthMrnaDesignLLMCritic` ✅ (registered in `workflows/registry.py`)

### 3.1 Purpose

Design complete mRNA molecules including 5'UTR, CDS, and 3'UTR. Reuses `MrnaCdsDesignWorkflow` for CDS generation, then appends UTR combinations and evaluates full-length metrics.

**Since v2.0.0**: Implements **Bounded Multi-Module Coordination (BMC)** — an iterative, rule-based coordinator that diagnoses inter-module conflicts (junction stability, GC continuity) and broadcasts structured feedback to affected modules for refinement.

### 3.2 Candidate generation (Phase 1)

```python
cds_workflow = MrnaCdsDesignWorkflow(capability_registry)
cds_result = cds_workflow.run(MrnaCdsDesignInput(protein_sequence=...))
for cds_cand in cds_result.all_candidates:
    for utr5_preset in ("short", "medium", "long"):
        for utr3_preset in ("short", "medium", "long"):
            full_seq = utr5 + cds_cand.sequence + utr3
```

CDS metrics are carried forward via `candidate.metadata["cds_metrics"]`.

### 3.3 Evaluation (Phase 2)

| Metric | Tool | Purpose |
|--------|------|---------|
| Full-length MFE | `predict_rna_secondary_structure_with_linearfold` (8015) / `predict_rna_secondary_structure` (8003) fallback | Overall thermodynamic stability |
| 5'UTR IRES potential | `predict_putative_ires_with_iresfinder` (8013) | Translation initiation potential |
| 5'UTR MRL | `predict_5utr_mrl_with_gemorna` (8004) | Mean ribosomal load |
| 3'UTR stability | `predict_3utr_stability_with_gemorna` (8004) | Degradation resistance |
| Overall stability | `predict_mrna_stability_with_rnastop` (8009) | Predicted half-life |
| CDS U content | `compute_rna_sequence_u_content` (8020) via `MrnaCdsDesignWorkflow` sub-evaluator | Reference metric for CDS composition |
| Full-length U content | `compute_rna_sequence_u_content` (8020) | Reference metric for full molecule composition |
| **Junction 5'UTR–CDS MFE** | `predict_rna_secondary_structure_with_linearfold` (8015) / `predict_rna_secondary_structure` (8003) fallback | **NEW: Local stability at 5' boundary** |
| **Junction CDS–3'UTR MFE** | `predict_rna_secondary_structure_with_linearfold` (8015) / `predict_rna_secondary_structure` (8003) fallback | **NEW: Local stability at 3' boundary** |
| **Junction GC diff** | Local computation | **NEW: GC continuity across boundaries** |

### 3.4 Scoring

#### Classic mode (Borda count, no junction metrics)

```python
# Rank each module independently (descending; higher = better)
cds_rank  = rank_by(candidates, key="cds_component",  descending=True)
utr5_rank = rank_by(candidates, key="utr5_mrl",       descending=True)
utr3_rank = rank_by(candidates, key="utr3_stability", descending=True)

# Sum ranks; smaller sum = better overall candidate
total_rank = cds_rank + utr5_rank + utr3_rank
```

#### BMC mode (junction-aware, activated when junction metrics are present)

```python
total_score = 0.25 * cds_component
            + 0.15 * utr5_mrl
            + 0.15 * utr3_stability
            + 0.20 * full_mfe_score      # inverted MFE (more negative = higher score)
            + 0.25 * junction_score      # sum of inverted junction MFEs minus GC penalties
```

`junction_score` rewards stable junctions (more negative MFE) and penalizes GC discontinuities (>15% diff).

### 3.5 Bounded Multi-Module Coordination (Phase 3)

After initial ranking, the deterministic `FullLengthCoordinator` inspects the best candidate for inter-module conflicts:

| Issue type | Threshold | Affected modules | Feedback action |
|------------|-----------|------------------|-----------------|
| `FULL_MFE_TOO_HIGH` | MFE/nt > −0.25 kcal/mol/nt | 5UTR, CDS, 3UTR | **Decrease** LinearDesign λ by 2 |
| `FULL_STRUCTURE_TOO_LOOSE` | paired fraction < 65% | 5UTR, CDS, 3UTR | **Decrease** λ by 2 |
| `JUNCTION_5UTR_CDS_TOO_STABLE` | junction MFE < −20 | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_5UTR_CDS_AUG_BURIED` | AUG start codon paired | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_5UTR_CDS_KOZAK_BURIED` | Kozak region paired | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_CDS_3UTR_UNSTABLE` | junction MFE > −15 | CDS, 3UTR | **Explore 3'UTR presets**; **shuffle C-terminus codons** |
| `JUNCTION_CDS_3UTR_GC_MISMATCH` | GC diff > 0.15 | CDS, 3UTR | **Diagnostic only** (recorded in BMC trace for review) |
| `JUNCTION_5UTR_CDS_GC_MISMATCH` | GC diff > 0.15 | 5UTR, CDS | **Diagnostic only** (recorded in BMC trace for review) |

**Key design principles**:
1. **Length-normalized MFE**: Absolute MFE thresholds are unfair across different sequence lengths (MFE ∝ length per Zhang et al., Nature 2023). We use `MFE / total_length` (kcal/mol/nt) and `paired_fraction` (derived from the dot-bracket structure produced by the fold tool — LinearFold primary, ViennaRNA fallback) instead.
2. **λ is reserved for global problems only**: LinearDesign λ is **inversely** related to MFE stability — **lower λ → more negative MFE**. λ adjustments are triggered **only** by global issues (`FULL_MFE_TOO_HIGH`, `FULL_STRUCTURE_TOO_LOOSE`). Pure junction issues do **not** adjust λ, because λ is a global CDS parameter and its effect on a 40-nt junction (only 20 nt from the CDS side) is heavily diluted.
3. **Translation-initiation-aware junction evaluation**: The 5'UTR-CDS junction is evaluated for **accessibility**, not raw stability. The `JunctionEvaluator` checks whether the AUG start codon and its Kozak context are base-paired (buried), which would impede ribosome scanning.
4. **Dual local-control junction optimization**: For pure junction issues, `_regenerate_modules()` fuses two local strategies:
   - **UTR preset exploration** (changes the UTR side of the junction)
   - **Junction codon shuffling** via `shuffle_cds_junction_codons` (synonymous substitution at the CDS terminus, 6 codons / up to 4 variants, changing the CDS side of the junction directly)
   Together they provide fine-grained control over the 40-nt overlap without perturbing the rest of the CDS.
5. **Tool switch**: If `design_tool` was `"all"` and a global issue triggers a λ adjustment, BMC automatically switches `design_tool` to `"lineardesign"` so the λ change takes effect (the fixed λ grid for `"all"` would otherwise ignore the adjustment).

**Bounds**:
- Maximum 3 coordination rounds
- Early stop if score degrades or improvement < 1.0
- Each round generates ≤6 CDS candidates (λ-adjusted + shuffled) × ≤2 UTR presets

The complete BMC trace (rounds, issues, feedback, modules reinvoked) is recorded in `result._state_writeback["_bmc_trace"]`.

### 3.6 Critic strategy

Filters candidates on **5'UTR IRES potential** only. Default threshold: `0.5`. Retry is triggered only when surviving candidates drop below `MIN_GOOD_CANDIDATES = 5`.

---

## 4. siRNA Design

> **File**: `workflows/sirna_design.py`  
> **Classes**: `SirnaDesignWorkflow`, `SirnaCritic`  
> **Status**: ✅ Implemented (v1.1.0)

### 4.1 Purpose

Design siRNA guides with safety gating on off-target count and specificity.

### 4.2 Modes

| Mode | Description |
|------|-------------|
| `antiviral` | Calls `design_sirna_with_evitar` (port 8016); parses top_results into Candidates |
| `generic` | Sliding window (21 nt, step 1) over user-provided target sequence; local filters on GC, homopolymers, sense strand end |

### 4.3 Evaluation

- GC content (port 8020)
- Duplex MFE (ViennaRNA RNAcofold, port 8003)
- Off-target scan (BLAST `blastn-short`, port 8019) — or Evitar built-in counts

### 4.4 Scoring

```python
total_score = 0.4 * efficiency + 0.2 * gc_component + 0.4 * specificity_component
```

### 4.5 Critic strategy (`SirnaDesignLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `SIRNA_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - Duplex MFE (RNAcofold): more negative = more stable
  - Off-target count: should be minimal
  - GC content: 30–60% optimal range
  - Consecutive homopolymers (>3 identical bases) should be avoided
  - Evitar predicted efficiency (antiviral mode)
- **Adjustable params**:
  - `mode`: enum `["antiviral", "generic"]`
  - `candidate_count`: int [1, 100]
  - `maxgc`: float [0.0, 1.0]
  - `mingc`: float [0.0, 1.0]
  - `off_target_scan`: bool
  - `blast_perc_identity`: float [70.0, 100.0]
- **Retry action**: `retry_with_adjustments` — tighten GC bounds and BLAST identity on retry
- **Graceful degradation**: After 2 retries, accept result regardless

---

## 5. sgRNA Handle Design

> **File**: `workflows/sgrna_design.py`  
> **Classes**: `SgRnaDesignWorkflow`, `SgRnaDesignLLMCritic`  
> **Status**: ✅ Implemented (v1.0.0)

### 5.1 Purpose

Optimize sgRNA handle (scaffold) sequences using CRGPT, with optional CRISOT off-target scoring.

### 5.2 Pipeline

```
seed handle → CRGPT design (mcmc / naive) → candidate list
  → CRGPT re-score per candidate (default on)
  → CRISOT off-target score (optional, if guide + target provided)
  → scoring (nn_score + crisot_score)
  → ranking → WorkflowResult
```

### 5.3 Evaluation

1. **CRGPT re-score** (`score_sgrna_handle_with_crgpt`, port 8017): `nn_score`, `log_likelihood`, `structure_distance`, `mfe`
2. **CRISOT off-target score** (`score_crispr_off_target_with_crisot`, port 8011): only when both `guide_sequence` and `target_sequence` are provided

### 5.4 Scoring

```python
nn_component     = clamp(nn_score / 2.0, 0, 1)
crisot_component = clamp(crisot_score, 0, 1)
total_score      = weight_nn_score * nn_component + weight_crisot_score * crisot_component
```

Default weights: `0.5 / 0.5`. If CRISOT is not evaluated, falls back to `nn_component` only.

### 5.5 Critic strategy (`SgRnaDesignLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `SGRNA_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - CRGPT `nn_score` perplexity: lower is better; reflects handle quality
  - CRISOT off-target score: higher specificity is safer
  - Sequence diversity among candidates
  - Mutation count vs. seed: appropriate level of variation
  - MFE stability of designed handles
- **Adjustable params**:
  - `n_samples`: int [1, 200]
  - `mutation_number`: int [1, 40]
  - `temperature`: float (sampling temperature)
  - `sampling_mode`: enum `["mcmc", "naive"]`
  - `max_overlap`: int [1, 60]
  - `evaluate_crgpt_score`: bool
  - `evaluate_crisot`: bool
  - `weight_nn_score`: float [0.0, 1.0]
  - `weight_crisot`: float [0.0, 1.0]
- **Retry action**: `retry_with_adjustments` — increase sample count, adjust temperature, or switch sampling mode
- **Graceful degradation**: After 2 retries, accept result regardless

---

## 6. RNA Secondary Structure → Sequence Design

> **File**: `workflows/rna_secondary_structure_design.py`  
> **Classes**: `RnaSecondaryStructureDesignWorkflow`, `RnaSecondaryStructureDesignLLMCritic`  
> **Task type**: `secondary_structure_design`

### 6.1 Purpose

Design RNA sequences from a target **secondary structure** (dot-bracket notation) using ViennaRNA `RNAinverse`. No PDB or GPU required.

### 6.2 Prerequisites

| Microservice | Port | Required |
|--------------|------|----------|
| ViennaRNA fold | 8003 | `viennarna` conda package |
| RNA metrics | 8020 | GC content |

### 6.3 Pipeline

1. **Input validation**: `target_structure` must be non-empty dot-bracket; `start_sequence` (optional) must match length
2. **Candidate generation**: `inverse_fold_rna_secondary_structure_vienna` called `num_invocations` times independently, each with `repeats` stochastic searches
3. **Deduplication**: exact sequence duplicates merged
4. **Evaluation**: GC content + ViennaRNA RNAfold → structure Hamming distance
5. **Scoring**:
   ```python
   structure_component = 1 - structure_distance / sequence_length
   total_score         = structure_component
   ```
6. **Ranking**: sort by `total_score` descending

### 6.4 Critic strategy (`RnaSecondaryStructureDesignLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `RNA_SECONDARY_STRUCTURE_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - Structural fidelity: designed sequence should fold back into the target structure
  - Sequence diversity: candidates should not all be identical
  - MFE stability: reasonable thermodynamic stability
  - Score interpretation: `total_score = structure_distance_ratio` where 0.0 = perfect match, smaller is better
- **Adjustable params**:
  - `repeats`: int (RNAinverse search repeats per invocation)
  - `num_invocations`: int (independent inverse-fold calls)
  - `temp_c`: float (temperature in °C)
  - `function_mode`: enum `["m", "p", "mp"]`
- **Retry action**: `retry_with_adjustments` — increase repeats or num_invocations when structural fidelity is poor across all candidates
- **Parameter tuning guidance**: defaults (`repeats=10`, `num_invocations=3`, `function_mode="m"`, `temp_c=37.0`) are empirically tuned; only override with strong evidence

---

## 7. RNA Tertiary Structure → Sequence Design

> **File**: `workflows/rna_tertiary_structure_design.py`  
> **Classes**: `RnaTertiaryStructureDesignWorkflow`, `RnaTertiaryStructureDesignLLMCritic`  
> **Task type**: `tertiary_structure_design`

### 7.1 Purpose

Design RNA sequences from a given 3D structure (PDB/CIF) using RhoDesign and/or RiboDiffusion, then validate with RhoFold and structure alignment.

### 7.2 Prerequisites

| Microservice | Port | Required checkpoint |
|--------------|------|---------------------|
| RhoDesign | 8006 | `ss_apexp_best.pth` + `no_ss_apexp_best.pth` |
| RiboDiffusion | 8021 | `exp_inf.pth` or `exp_inf_large.pth` |
| RhoFold | 8005 | Pre-trained checkpoint |
| Structure alignment | — | biopython |

### 7.3 Pipeline

1. **Candidate generation**
   - RhoDesign: `n_samples_per_tool` independent calls with temperature sweep
   - RiboDiffusion: single call with `n_samples = n_samples_per_tool`
2. **Deduplication**: exact duplicates merged across both tools
3. **Evaluation** (per candidate)
   - GC content (8020)
   - Secondary structure MFE (8003)
   - Tertiary structure foldability — RhoFold pLDDT (8005)
   - Structural fidelity — RMSD + TM-score vs. reference
4. **Scoring**:
   ```python
   rhofold_component = pLDDT / 100
   rmsd_component    = max(0, 1 - RMSD / 5.0)
   total_score       = 0.5 * rhofold_component + 0.5 * rmsd_component
   ```
5. **Ranking**: sort by `total_score` descending

### 7.4 Critic strategy (`RnaTertiaryStructureDesignLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `RNA_TERTIARY_STRUCTURE_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - RhoFold pLDDT: predicted foldability of the designed sequence
  - TM-score: structural similarity to reference
  - RMSD: spatial deviation from reference
  - GC content: synthesis-friendly range
  - ViennaRNA MFE: thermodynamic stability
  - Recovery rate: sequence compatibility with target backbone
  - Tool diversity: candidates from both RhoDesign and RiboDiffusion
- **Adjustable params**:
  - `design_tools`: enum `["all", "rhodesign", "ribodiffusion"]`
  - `n_samples_per_tool`: int [1, 20]
  - `rhodesign_temperature`: float
  - `temperature_range`: float
  - `ribodiffusion_sampling_steps`: int
- **Retry action**: `retry_with_adjustments` — increase samples, switch design tools, or adjust temperature
- **Parameter tuning guidance**: defaults (`n_samples_per_tool=3`, `scoring weights=0.5/0.5`) are carefully tuned; only override with strong evidence

---

## 8. RNA–Small Molecule Interaction

> **File**: `workflows/rna_small_molecule_interaction.py`  
> **Class**: `RnaSmallMoleculeInteractionWorkflow`  
> **Input model**: `RnaSmallMoleculeInteractionInput`  
> **Critic**: **None** (prediction-only)  
> **Status**: ✅ **INTERFACE LOCKED** — see [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) §9

### 8.1 Purpose

Predict RNA-small molecule binding propensity for a given RNA sequence and ligand SMILES. Runs RNAsmol and/or GerNA-Bind, averages their probability scores.

### 8.2 Prerequisites

| Microservice | Port | Required |
|--------------|------|----------|
| RNAsmol | 8007 | 6 weight files |
| GerNA-Bind | 8010 | `Robin_random.pth` + `RNA-FM_pretrained.pth` |

### 8.3 Pipeline

1. **Input validation**: RNA sequence (AUGC), SMILES string, optional PDB/secondary structure
2. **Candidate generation**: wrap single `(rna_sequence, smiles)` pair as one `Candidate`
3. **Evaluation**
   - `score_rna_ligand_binding_with_rnasmol` (8007)
   - `score_rna_ligand_binding_with_gernabind` (8010)
4. **Scoring**:
   ```python
   if both tools succeed:
       total_score = average of available probability components
   else if one succeeds:
       total_score = that tool's probability
   else:
       total_score = 0.0
   ```

---

## 9. RNA Aptamer Design

> **File**: `workflows/rna_aptamer_design.py`  
> **Classes**: `RnaAptamerDesignWorkflow`, `RnaAptamerDesignLLMCritic`, `AptamerCoordinator`  
> **Critic**: ✅ `RnaAptamerDesignLLMCritic` (LLM-driven) + `AptamerCoordinator` (BMC Type-II deterministic)  
> **Status**: ✅ **INTERFACE LOCKED** — see [`INTERFACE_LOCKS.md`](INTERFACE_LOCKS.md) §15

### 9.1 Purpose

Design RNA aptamers targeting a protein using ODesign, then validate with ProteinX complex prediction, EGARPS scoring, and interface analysis.

### 9.2 Pipeline

1. **Input preparation**: `build_odesign_aptamer_input_json` from protein structure + hotspots
2. **Candidate generation**: `run_odesign_inference` (8012)
3. **Evaluation**
   - RhoFold 3D structure prediction (8005)
   - ProteinX RNA-protein complex prediction (8022)
   - EGARPS complex scoring (8023)
   - Interface analysis (pure Python)
4. **Scoring**:
   ```python
   total_score = EGARPS + (RhoFold_pLDDT / 100) + ipTM
   ```
   GC content is computed for critic gating but does not contribute to ranking.

---

## 10. IRES Prediction & Validation

> **File**: `workflows/ires_prediction.py`  
> **Classes**: `IresPredictionWorkflow`, `IresPredictionLLMCritic`  
> **Task type**: `ires`

### 10.1 Purpose

Identify potential IRES elements within a 5'UTR or candidate sequence, with structural validation.

### 10.2 Pipeline

1. **IRES prediction** (`predict_putative_ires_with_iresfinder`, port 8013)
   - Mode 0: full sequence; Mode 1: header subsequence; Mode 2: sliding window
2. **Extract top candidates**: threshold > 0.5, merge overlapping windows
3. **Structural validation** (per candidate)
   - LinearFold fold (8015, primary) / ViennaRNA fold (8003, fallback)
   - RNAplfold accessibility profile (8003)
   - Dot-bracket unpaired fraction (8020)
4. **Scoring**:
   ```python
   accessibility_score = 1 - abs(mean_unpaired_fraction - 0.5) * 2
   composite = ires_probability * accessibility_score
   ```
   (peaks at 0.5: IRES needs structured scaffold with exposed core)

### 10.3 Critic strategy (`IresPredictionLLMCritic`)

- **Type**: LLM-driven (DeepSeek)
- **Max retries**: 2 (configurable via `IRES_PREDICTION_CRITIC_CONFIG.max_retries`)
- **Evaluation dimensions**:
  - IRESfinder probability scores: confidence that a region functions as an IRES
  - Structural validation: LinearFold (primary) / ViennaRNA (fallback) predicted secondary structure and MFE
  - Mean unpaired fraction / RNAplfold accessibility: balance between structured scaffold and exposed regions
  - Coverage and distribution of candidates across the input sequence
  - User constraints: explicit thresholds or region requirements from the original prompt
- **Adjustable params**:
  - `probability_threshold`: float [0.0, 1.0]
  - `window_size`: int [20, 5000]
  - `step_size`: int [1, 5000]
  - `top_n_candidates`: int [1, 100]
  - `run_structural_validation`: bool
  - `iresfinder_mode`: int [0, 2]
- **Retry action**: `retry_with_adjustments` — lower probability threshold to catch more candidates, adjust window/step size, or enable structural validation
- **Confidence assignment** (workflow-internal, not from LLM Critic):

  | IRES probability | Unpaired fraction | Confidence |
  |------------------|-------------------|------------|
  | ≥ 0.8 | 0.3–0.7 | high |
  | ≥ 0.6 | 0.2–0.8 | medium |
  | ≥ 0.5 | any | low |
  | < 0.5 | any | rejected |

---

## 11. ASO Target Screening

> **File**: `workflows/aso_target_screening.py`  
> **Classes**: `AsoTargetScreeningWorkflow`, `AsoScreeningCritic` (empty placeholder)  
> **Task type**: `aso`

### 11.1 Purpose

Screen a full-length mRNA to identify the most accessible regions for ASO binding.

### 11.2 Pipeline

1. **Full-length accessibility profiling** (`predict_rna_local_accessibility_profile_vienna`, 8003)
2. **Identify high-accessibility windows** (sliding window, 15–20 nt)
3. **For each top window**:
   - Design complementary ASO sequence (reverse complement)
   - Evaluate binding (RNAup or RNAcofold, 8003)
4. **Rank-based scoring** (Borda count):
   ```python
   accessibility_rank = rank_by(mean_unpaired_prob, descending=True)
   binding_rank       = rank_by(binding_component, descending=True)
   sum_rank           = accessibility_rank + binding_rank
   ```
   Smaller `sum_rank` = better overall site.

### 11.3 Critic strategy

**No critic** — deterministic evaluation-only pipeline. `AsoScreeningCritic.should_retry` unconditionally returns `False`.

---

## 12. Workflow Landscape Summary

| Priority | Domain | Workflow | Type | Critic |
|----------|--------|----------|------|--------|
| P0 | mRNA | CDS design & optimization | design | ❌ None (ranking-only) |
| P0 | mRNA | Full-length mRNA design | design | ✅ `FullLengthMrnaDesignLLMCritic` |
| P0 | CRISPR | sgRNA handle design | design | ✅ `SgRnaDesignLLMCritic` |
| P1 | siRNA | siRNA design + safety | design | ✅ `SirnaDesignLLMCritic` |
| P1 | structure | 2° structure → sequence | design | ✅ `RnaSecondaryStructureDesignLLMCritic` |
| P1 | structure | 3° structure → sequence | design | ✅ `RnaTertiaryStructureDesignLLMCritic` |
| P1 | mRNA | IRES prediction | evaluation | ✅ `IresPredictionLLMCritic` (confidence only) |
| P2 | ligand | RNA–ligand scoring | evaluation | ❌ None (prediction-only) |
| P2 | RNA-protein | Aptamer design | design | ✅ `RnaAptamerDesignLLMCritic` |
| P2 | ASO | ASO target screening | evaluation | ❌ None (deterministic) |

*For per-tool specs and microservice details, see [`TOOLS.md`](TOOLS.md).*  
*For architecture and core module APIs, see [`ARCHITECTURE.md`](ARCHITECTURE.md).*
