# Interface Lock Policy

> **Scope**: the Interface Lock Policy, canonical references for locked tools, and synchronization checklists.  
> **Last updated**: 2026-07-06

---

## 1. Policy

This project uses **INTERFACE LOCK** comments to prevent accidental breaking changes to tool contracts. When you see a block like this:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# <Tool name> INTERFACE LOCK (vX.Y.Z) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
```

**Do NOT modify any function signature, Pydantic field, return dict key, or state field** inside that lock without updating **all** files listed in the lock comment and re-running the full test suite.

---

## 2. Currently Locked Interfaces

| Tool / Module | Version | Lock File / Doc |
|---------------|---------|-----------------|
| `compute_rna_sequence_gc_content` | v0.1.0 | This doc §3 |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | This doc §4 |
| `compute_rna_sequence_u_content` | v0.1.0 | This doc §5 |
| `compute_cai_for_cds_sequence` | v0.1.0 | This doc §6 |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `run_bowtie2_short_alignment` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `score_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| CRISOT suite (8 tools) | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | This doc §7 |
| `design_mrna_cds_junction_aware_with_lineardesign` | v0.1.0 | This doc §21 |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `predict_5utr_mrl_with_gemorna` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `predict_3utr_stability_with_gemorna` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `shuffle_cds_junction_codons` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `identify_protein_binding_hotspots` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `analyze_rna_protein_interface` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `score_structure_alignment` | v0.1.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `MrnaCdsDesignWorkflow` | v1.1.0 | This doc §8 |
| `RnaSmallMoleculeInteractionWorkflow` | v1.1.0 | This doc §9 |
| `SirnaDesignWorkflow` | v1.1.1 | This doc §10 |
| `SgRnaDesignWorkflow` | v1.1.0 | This doc §11 |
| `AsoTargetScreeningWorkflow` | v1.0.0 | This doc §12 |
| `IresPredictionWorkflow` | v1.1.0 | This doc §13 |
| `FullLengthMrnaDesignWorkflow` | v2.8.0 | This doc §14 |
| `RnaAptamerDesignWorkflow` | v1.4.2 | This doc §15 |
| `RnaSecondaryStructureDesignWorkflow` | v1.0.0 | This doc §16 |
| `RnaTertiaryStructureDesignWorkflow` | v1.0.0 | This doc §17 |
| `MrnaSequenceScoringWorkflow` | v1.1.0 | This doc §18 |
| `AgentRunner` | v3.4.0 | This doc §19 |
| `CLI End-to-End Execution Flow` | v2.3.0 | `rna_agent_system/docs/INTERFACE_LOCKS.md` §20 |

---

## 3. Canonical Reference: GC Content Tool

> **Locked on**: 2026-04-25

### Locked contracts

- **Input schema** (`RnaGcContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaGcContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `g_count`, `c_count`, `gc_count`, `gc_content`, `model`
- **ToolSpec identity**: `compute_rna_sequence_gc_content`
- **Microservice endpoint**: `POST /gc-content` on port `8020`
- **State storage**: `state["tool_results"]["compute_rna_sequence_gc_content"]` contains keys `gc_content`, `sequence_length`, `gc_count`, `g_count`, `c_count`

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/workflows/mrna_sequence_scoring.py`
- `agent_core/sequence_utils.py`
- `agent_core/workflow_baseline_eval.py`
- `tests/test_compute_rna_sequence_gc_content.py`

### Tests that must pass

```bash
pytest tests/test_compute_rna_sequence_gc_content.py -v
pytest tests/test_mrna_workflow.py tests/test_workflow_observability.py -v
pytest tests/test_integration_registry_smoke.py -v
```

---

## 4. Canonical Reference: Dot-Bracket Unpaired Fraction Tool

> **Locked on**: 2026-04-25

### Locked contracts

- **Input schema** (`DotBracketUnpairedFractionInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`DotBracketUnpairedFractionOutput`): `input_filepath`, `resolved_filepath`, `structure_length`, `dot_count`, `unpaired_fraction`, `model`
- **ToolSpec identity**: `compute_dot_bracket_unpaired_fraction`
- **Microservice endpoint**: `POST /unpaired-fraction` on port `8020`
- **State storage**: `state["tool_results"]["compute_dot_bracket_unpaired_fraction"]` contains keys `unpaired_fraction`, `structure_length`, `dot_count`

### Synchronization checklist

- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/sequence_utils.py`
- `tests/test_compute_dot_bracket_unpaired_fraction.py`

---

## 5. Canonical Reference: RNA Sequence U Content Tool

> **Locked on**: 2026-04-28

### Locked contracts

- **Input schema** (`RnaUContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaUContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `u_count`, `u_fraction`, `model`
- **ToolSpec identity**: `compute_rna_sequence_u_content`
- **Microservice endpoint**: `POST /u-content` on port `8020`
- **State storage**: `state["tool_results"]["compute_rna_sequence_u_content"]` contains keys `u_fraction`, `u_count`, `sequence_length`

### Synchronization checklist

- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/sequence_utils.py`
- `agent_core/workflows/evaluators.py` (`UContentEvaluator`)
- `tests/test_compute_rna_sequence_u_content.py`

---

## 6. Canonical Reference: CAI for CDS Tool

> **Locked on**: 2026-04-28

### Locked contracts

- **Input schema** (`CaiForCdsInput`): `filepath`, `species`, `custom_codon_table_path`
- **Output schema** (`CaiForCdsOutput`): `input_filepath`, `cai_score`, `species`, `cds_length_nt`, `codon_count`, `valid_codons`, `invalid_codons`, `stop_codons_encountered`, `model`
- **ToolSpec identity**: `compute_cai_for_cds_sequence`
- **Transport**: `python_api` (pure Python, no microservice)
- **State storage**: `state["tool_results"]["compute_cai_for_cds_sequence"]` contains keys `cai_score`, `species`, `cds_length_nt`, `codon_count`

### Synchronization checklist

- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/sequence_utils.py`
- `agent_core/data/codon_usage_kazusa.json`
- `tests/test_compute_cai_for_cds_sequence.py`

---

## 7. Canonical Reference: LinearDesign Interface

> **Locked on**: 2026-04-24

### Single-sequence tool

- **Tool name**: `design_mrna_cds_with_lineardesign`
- **Endpoint**: `POST http://127.0.0.1:8014/generate/cds`
- **Parameters**: `lambda_value` (float, ge=0.0, default=0.0), `codon_usage_path` (Optional[str]), `verbose` (bool)
- **Required output fields**: `generated_sequence`, `structure`, `mfe`, `cai_score`, `lambda_value`, `codon_usage_path`, `raw_output`, `stderr`, `model`, `input_filepath`, `output_filepath`

### Batch tool

- **Tool name**: `design_mrna_cds_batch_with_lineardesign`
- **Endpoint**: `POST http://127.0.0.1:8014/generate/cds/batch`
- **Required output fields**: `count`, `success_count`, `items`, `best_generated_sequence`, `best_structure`, `best_mfe`, `best_cai_score`, `batch_json_filepath`, `lambda_value`, `codon_usage_path`, `model`

### Synchronization checklist

- `microservices/lineardesign_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `tests/test_integration_registry_smoke.py`

---

## 8. Canonical Reference: mRNA CDS Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §2`](WORKFLOWS.md#2).
>
> **Locked on**: 2026-05-10
> **Version**: v1.1.0
> **Status**: ✅ Tested

### v1.1.0 changelog

- **Changed**: Workflow no longer embeds an `MrnaCdsDesignLLMCritic` subclass. Quality review is now performed by the unified `QualityAgent` using the `MRNA_CDS_QUALITY_PROFILE` in `agent_core/quality_profiles/mrna_cds_design.py`.
- **Unchanged**: Input model, pipeline stage order, scoring formula, required capabilities, and state writeback remain identical to v1.0.0.

### Locked contracts

#### Input model (`MrnaCdsDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `protein_sequence: str` — required
  - `truncate_n_terminal: Optional[int]` — default `None`; use only the first N amino acids
  - `truncate_c_terminal: Optional[int]` — default `None`; use only the last N amino acids
  - `design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"]` — default `"all"`
  - `lambda_value: Optional[float]` — required when `design_tool="lineardesign"`
  - `model_type: Literal[7 RNARL types]` — default `"Homo sapiens mRNA"`
  - `cai_species: str` — default `"Homo sapiens"`
  - `run_fold: bool` — default `True`
  - `run_gc: bool` — default `True`

  **Note**: `truncate_n_terminal` and `truncate_c_terminal` are mutually exclusive. They preserve the original `protein_sequence` in the audit trail while directing the workflow to design only for the specified region. The allowed `model_type` values and `cai_species` aliases are maintained in `agent_core/constants/species.py` (`RNARLModelType` / `RNARL_MODEL_TYPES_LIST` and `CAI_SPECIES_ALIASES` / `DEFAULT_CAI_SPECIES`).

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → produces `list[Candidate]`
2. `evaluate()` → produces `dict[str, Any]` (metrics_bundle per candidate)
3. `score()` → calls `score_mrna_candidate()` from `agent_core/sequence_utils.py`
4. `rank_and_format()` → produces `WorkflowResult`

#### Scoring formula (must NOT be changed without updating docs and tests)

```python
total_score = -mfe + codon_count * log(CAI)
```

Only `total_score` (and intermediate `combined_score`) affect ranking. Raw metrics (GC, unpaired, RNASTOP) are displayed but do NOT enter the formula.

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "design_mrna_cds_with_lineardesign",
    "design_mrna_cds_with_rnarl",
    "design_mrna_cds_with_gemorna",
    "predict_rna_secondary_structure",
    "predict_rna_secondary_structure_with_linearfold",
    "compute_rna_sequence_gc_content",
    "compute_rna_sequence_u_content",
    "compute_dot_bracket_unpaired_fraction",
    "predict_mrna_stability_with_rnastop",
    "compute_cai_for_cds_sequence",
]
```

#### Quality configuration (`MRNA_CDS_QUALITY_PROFILE`)

- **evaluation_dimensions**: 8 items covering CAI, MFE, GC, U content, unpaired, RNASTOP, lambda physics, tool diversity
- **adjustable_params**: `design_tool`, `lambda_value`, `model_type`, `cai_species`, `run_fold`, `run_gc`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### Quality report output (`QualityReport`)

- Must match Pydantic schema in `agent_core/agents/quality_agent.py`
- `action` must be one of: `"pass"`, `"retry_with_adjustments"`, `"retry_with_alternative"`, `"abort"`
- `parameter_overrides` must only contain keys from `adjustable_params`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing at minimum:
- `_workflow_params`: the exact `MrnaCdsDesignInput` dict used

This is consumed by `AgentRunner` to populate `_last_workflow_params` for cross-turn prefilling and audit.

### Synchronization checklist

- `agent_core/workflows/mrna_cds_design.py` (source of truth)
- `agent_core/sequence_utils.py` (scoring formula, `compute_mrna_metric_bundle`)
- `agent_core/workflows/evaluators.py` (`UContentEvaluator`, `CompositeEvaluator`)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/mrna_cds_design.py` (quality profile)
- `agent_core/quality_profiles/__init__.py` (quality profile registry)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_mrna_cds_design.py -v

# Full stack including live QualityAgent
pytest tests/test_mrna_cds_design.py -v --live-llm

# Existing test suites
pytest tests/test_mrna_cds_design_layer4.py tests/test_quality_agent.py -v
```

### Known third-party scientific limitations for PA_023

PA_023 is a **process-aware** benchmark: it verifies that the CLI/agent correctly executes the `ires_prediction` workflow across three modes and preserves multi-turn context. However, the **scientific objective of round 3 (finding a positive IRES in the 100–300 nt subsequence) is intentionally not achieved by the underlying third-party IRESfinder model**:

- IRESfinder mode 1 on `pa023_mode1_5utr.fa` (positions 100–300, 201 nt) returns `max_score = 0.4986`, which is below the user-specified `probability_threshold = 0.5`.
- Consequently the workflow returns a rejected candidate with `ires_probability = 0.0` and `confidence = rejected`, while still emitting the full structural metrics bundle (MFE, dot-bracket unpaired fraction, RNAplfold local accessibility).
- This negative result is **expected and informative**: it demonstrates that the system correctly surfaces a third-party model limitation rather than fabricating a positive candidate or dropping structural validation. Future changes to IRESfinder weights or thresholds may change the numeric outcome, but the workflow behavior (mode switch, coordinate parsing, comparison reporting, QualityAgent diagnosis) must remain stable.


## 9. Canonical Reference: RNA-Small Molecule Interaction Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §8`](WORKFLOWS.md#8).
>
> **Locked on**: 2026-05-12
> **Version**: v1.1.0 (2026-07-17: added `predict_rna_tertiary_structure_with_rhofold` to `required_capabilities`)
> **Status**: ✅ Tested

### Locked contracts

#### Input model (`RnaSmallMoleculeInteractionInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `rna_sequence: str` — required; validated to A/U/G/C only
  - `smiles: str` — required; validated to contain atom symbols
  - `rna_structure_path: Optional[str]` — PDB/CIF for GerNA-Bind
  - `secondary_structure: Optional[str]` — dot-bracket for GerNA-Bind
  - `scoring_tools: List[Literal["rnasmol", "gernabind"]]` — default `["rnasmol", "gernabind"]`
  - `dataset: Optional[str]` — GerNA-Bind dataset hint
  - `split_method: Optional[str]` — GerNA-Bind split hint

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → wraps user input as a single `Candidate`
2. `evaluate()` → calls RNAsmol and/or GerNA-Bind capability; populates `metrics_bundle`
3. `score()` → calls `score_rna_ligand_candidate()`; averages available probabilities
4. `rank_and_format()` → produces `WorkflowResult`; fails if both tools return `None`

#### Scoring formula (must NOT be changed without updating docs and tests)

```python
total_score = average(available probability_positive values)
```

Each tool's `probability_positive` is a float in `[0, 1]`. Missing tool results contribute `0.0` to components but do NOT participate in the average.

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "score_rna_ligand_binding_with_rnasmol",
    "score_rna_ligand_binding_with_gernabind",
    # GerNA-Bind folds the RNA with RhoFold at runtime when no PDB is
    # supplied, so the RhoFold service is a hard runtime dependency.
    "predict_rna_tertiary_structure_with_rhofold",
]
```

#### Quality review

This workflow uses a placeholder `QualityProfile` (`RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE`).
Reason: the inputs (RNA + SMILES) are fixed; re-running produces identical results, so retry cannot improve outcomes.
The unified `QualityAgent` therefore always returns `action="pass"` for this workflow.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing the internal `_workflow_state` dict, including `tool_results` from both scoring capabilities.

### Synchronization checklist

- `agent_core/workflows/rna_small_molecule_interaction.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry)
- `agent_core/state.py` (`tool_results["score_rna_ligand_binding_with_rnasmol"]` / `tool_results["score_rna_ligand_binding_with_gernabind"]`)
- `agent_core/quality_profiles/rna_small_molecule_interaction.py` (placeholder QualityProfile)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Existing unit/integration tests
pytest tests/test_rna_small_molecule_interaction.py -v
```


## 10. Canonical Reference: siRNA Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §4`](WORKFLOWS.md#4).
>
> **Locked on**: 2026-05-13
> **Version**: v1.1.1
> **Status**: ✅ Tested

### v1.1.1 changelog

- **Changed**: `SirnaDesignWorkflow.run()` now delegates to `BaseDomainWorkflow.run()` instead of reimplementing the generate → evaluate → score → rank loop. siRNA-specific GC filtering and rank-based scoring were moved into `rank_and_format()`; public signature, return type, and output structure are unchanged.

### v1.1.0 changelog

- **Changed**: Workflow no longer embeds a `SirnaDesignLLMCritic` subclass. Quality review is now performed by the unified `QualityAgent` using the `SIRNA_QUALITY_PROFILE` in `agent_core/quality_profiles/sirna_design.py`.

### Locked contracts

#### Input model (`SirnaDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `mode: Literal["antiviral", "generic"]` — default `"antiviral"`
  - `target_sequence: Optional[str]` — plain RNA/DNA sequence (generic mode)
  - `target_fasta_path: Optional[str]` — FASTA filepath (antiviral mode)
  - `candidate_count: int` — default `10`, range `[1, 100]`
  - `off_target_scan: bool` — default `True`
  - `transcriptome_fasta_path: Optional[str]` — for BLAST subject
  - `blast_subject_db: Optional[str]` — for BLAST subject DB
  - `species: str` — default `"homo_sapiens"`
  - `evitar_mode: Literal["existing", "predesign"]` — default `"existing"`
  - `evitar_predict: Literal["predsi", "rnaxs", "multifapredsi", "CRISPR"]` — default `"predsi"`
  - `maxgc: float` — default `0.60`, range `[0.0, 1.0]`
  - `mingc: float` — default `0.25`, range `[0.0, 1.0]`
  - `middlegc: float` — default `0.45`, range `[0.0, 1.0]`
  - `blast_perc_identity: float` — default `90.0`, range `[70.0, 100.0]`

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → antiviral (Evitar) or generic (sliding window 21-nt)
2. `evaluate()` → GC content + duplex MFE + self-structure + off-target BLAST
3. `score()` → legacy `score_sirna_candidate()` (per-candidate, kept for API compatibility)
4. `rank_and_format()` → GC filter → `compute_sirna_rank_scores()` → produces `WorkflowResult`

#### Scoring formula (must NOT be changed without updating docs and tests)

Rank-based scoring via `compute_sirna_rank_scores()`:

```python
# Rank 1 = best (most negative MFE)
sorted_by_mfe = sorted(candidates, key=lambda c: c.metadata["duplex_mfe"])
# Rank 1 = best (fewest off-target hits)
sorted_by_off = sorted(candidates, key=lambda c: c.metadata["off_target_count"])
# Lower total_rank = better
total_rank = rank_mfe + rank_offtarget
```

`score_sirna_candidate()` is a **legacy per-candidate scoring** kept for API compatibility only. New ranking uses `compute_sirna_rank_scores()` on the full candidate list.

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "design_sirna_with_evitar",          # antiviral mode only
    "compute_rna_sequence_gc_content",   # optional GC evaluation
    "compute_sirna_duplex_binding_vienna",  # optional duplex MFE
    "predict_rna_secondary_structure",   # optional self-structure (fallback)
    "predict_rna_secondary_structure_with_linearfold",  # optional self-structure (primary)
    "run_blastn_similarity_search",      # optional off-target scan (BLAST)
    "run_bowtie2_short_alignment",       # optional off-target scan (Bowtie2)
]
```

#### Quality configuration (`SIRNA_QUALITY_PROFILE`)

- **evaluation_dimensions**: 5 items covering duplex MFE, off-target count, GC content, homopolymers, Evitar efficiency
- **adjustable_params**: `mode`, `candidate_count`, `maxgc`, `mingc`, `off_target_scan`, `blast_perc_identity`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing at minimum:
- `_workflow_params`: the exact `SirnaDesignInput` dict used
- `_sirna_input`: the parsed input model

This is consumed by `AgentRunner` to populate `_last_workflow_params` for cross-turn prefilling and audit.

### Synchronization checklist

- `agent_core/workflows/sirna_design.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/quality_profiles/sirna_design.py` (quality profile)
- `agent_core/quality_profiles/__init__.py` (quality profile registry)
- `agent_core/agents/pipeline_agent.py` (PipelineAgent)
- `agent_core/agents/specialist_agent.py` (SpecialistAgent retry logic)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Existing test suites
pytest tests/test_sirna_design_workflow.py -v
```


## 11. Canonical Reference: sgRNA Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §5`](WORKFLOWS.md#5).
>
> **Locked on**: 2026-05-13
> **Version**: v1.1.0
> **Status**: ✅ Tested

### v1.1.0 changelog

- **Changed**: Workflow no longer embeds a `SgRnaDesignLLMCritic` subclass. Quality review is now performed by the unified `QualityAgent` using the `SGRNA_QUALITY_PROFILE` in `agent_core/quality_profiles/sgrna_design.py`.
- **Unchanged**: Input model, pipeline stage order, scoring formula, required capabilities, and state writeback remain identical to v1.0.0.

### Locked contracts

#### Input model (`SgRnaDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `seed_sequence: Optional[str]` — inline sgRNA handle seed (40–120 nt)
  - `seed_filepath: Optional[str]` — filepath containing seed sequence
  - `guide_sequence: Optional[str]` — 23-nt guide for CRISOT off-target scoring
  - `target_sequence: Optional[str]` — 23-nt target for CRISOT off-target scoring
  - `n_samples: int` — default `10`, range `[1, 200]`
  - `mutation_number: int` — default `22`, range `[1, 40]`
  - `temperature: Optional[float]` — MCMC/naive sampling temperature
  - `sampling_mode: str` — `"mcmc"` or `"naive"`
  - `max_overlap: int` — default `21`, range `[1, 60]`
  - `evaluate_crgpt_score: bool` — default `True`
  - `evaluate_crisot: bool` — default `True`
  - `weight_nn_score: float` — default `0.5`, range `[0.0, 1.0]`
  - `weight_crisot: float` — default `0.5`, range `[0.0, 1.0]`

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → CRGPT design endpoint (`design_sgrna_handle_with_crgpt`)
2. `evaluate()` → CRGPT re-score (`score_sgrna_handle_with_crgpt`) + optional CRISOT (`score_crispr_off_target_with_crisot`)
3. `score()` → `score_sgrna_candidate()` (weighted nn_component + crisot_component)
4. `rank_and_format()` → produces `WorkflowResult`; fails if candidate list is empty

#### Scoring formula (must NOT be changed without updating docs and tests)

```python
# nn_score is perplexity (lower is better); map via reciprocal
nn_component = 1.0 / nn_score  # clamped to [0, 1]
# crisot_score is directly used
crisot_component = clamp(crisot_score, 0.0, 1.0)
# Weighted average
total_score = (weight_nn * nn_component + weight_crisot * crisot_component) / active_weights
```

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "design_sgrna_handle_with_crgpt",       # mandatory for candidate generation
    "score_sgrna_handle_with_crgpt",        # optional re-scoring
    "score_crispr_off_target_with_crisot",  # optional CRISOT off-target
]
```

#### Quality configuration (`SGRNA_QUALITY_PROFILE`)

- **evaluation_dimensions**: 5 items covering nn_score perplexity, CRISOT off-target, diversity, mutation count, MFE stability
- **adjustable_params**: `n_samples`, `mutation_number`, `temperature`, `sampling_mode`, `max_overlap`, `evaluate_crgpt_score`, `evaluate_crisot`, `weight_nn_score`, `weight_crisot`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### CRISOT caching

CRISOT off-target score is computed **once per workflow run** and cached in `_workflow_state["_crisot_score_cache"]`.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `SgRnaDesignInput` dict used
- `_sgrna_input`: the parsed input model

### Synchronization checklist

- `agent_core/workflows/sgrna_design.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/quality_profiles/sgrna_design.py` (quality profile)
- `agent_core/quality_profiles/__init__.py` (quality profile registry)
- `agent_core/agents/pipeline_agent.py` (PipelineAgent)
- `agent_core/agents/specialist_agent.py` (SpecialistAgent retry logic)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Existing unit/integration tests (stubs, no LLM required)
pytest tests/test_sgrna_design_workflow.py -v

# End-to-end tests with real microservices (Layers 0–2)
pytest tests/test_sgrna_design_e2e.py::TestLayer0DirectToolInvocation -v
pytest tests/test_sgrna_design_e2e.py::TestLayer1Capability -v
pytest tests/test_sgrna_design_e2e.py::TestLayer2Workflow -v

# Layer 4 tests with live DeepSeek API
pytest tests/test_sgrna_design_e2e.py::TestLayer4PlanningAndControl -v
```


## 12. Canonical Reference: ASO Target Screening Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §11`](WORKFLOWS.md#11).
>
> **Locked on**: 2026-05-14
> **Version**: v1.0.0
> **Status**: ✅ Tested

### Locked contracts

#### Input model (`AsoScreeningInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `target_mrna_filepath: str` — required; path to target mRNA FASTA/plain file
  - `aso_length: int` — default `18`, range `[10, 50]`
  - `window_step: int` — default `1`, range `[1, 10]`
  - `top_n_windows: int` — default `10`, range `[1, 100]`
  - `binding_evaluation_tool: Literal["rnaup", "rnacofold"]` — default `"rnaup"`

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → read target → RNAplfold profile → sliding-window scan → reverse-complement ASO design
2. `evaluate()` → region-specific RNAplfold accessibility + RNAup/RNAcofold binding evaluation
3. `score()` → accessibility_component (mean unpaired prob) + binding_component (−ΔG)
4. `rank_and_format()` → rank-based scoring (accessibility_rank + binding_rank) → composite ranking → `WorkflowResult`

#### Scoring formula (must NOT be changed without updating docs and tests)

Rank-based scoring:

```python
# Step 1: rank by accessibility (descending) → 1 = best
by_acc = sorted(candidates, key=lambda c: c.scores["accessibility_component"], reverse=True)
acc_rank_map = {id(c): r for r, c in enumerate(by_acc, start=1)}

# Step 2: rank by binding (descending) → 1 = best
by_bind = sorted(candidates, key=lambda c: c.scores["binding_component"], reverse=True)
bind_rank_map = {id(c): r for r, c in enumerate(by_bind, start=1)}

# Step 3: sum ranks and final sort (ascending) → 1 = best
for c in candidates:
    c.scores["sum_rank"] = acc_rank_map[id(c)] + bind_rank_map[id(c)]
```

Best candidate = lowest `sum_rank` (most balanced between accessibility and binding).

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "predict_rna_local_accessibility_profile_vienna",
    "compute_aso_target_accessibility_vienna",
    "compute_rna_rna_interaction_vienna",
    "compute_sirna_duplex_binding_vienna",
]
```

#### Quality review

This workflow uses an empty `QualityProfile` (`ASO_TARGET_SCREENING_QUALITY_PROFILE`).
Reason: ASO screening is a deterministic evaluation-only pipeline; the same input always
yields the same accessibility profile and binding energies. Retry would only waste compute.
The unified `QualityAgent` therefore always returns `action="pass"` for this workflow.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_aso_input`: the parsed `AsoScreeningInput` model
- `target_filepath`: path to saved normalized target sequence
- `target_sequence`: normalized RNA sequence string
- `profile_tsv`: path to RNAplfold TSV profile

### Synchronization checklist

- `agent_core/workflows/aso_target_screening.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/quality_profiles/aso_target_screening.py` (empty QualityProfile)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_aso_target_screening.py -v
```


## 13. Canonical Reference: IRES Prediction & Validation Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §10`](WORKFLOWS.md#10).
>
> **Locked on**: 2026-05-14
> **Version**: v1.1.0
> **Status**: ✅ Tested; PA_023 regression addressed

### v1.1.0 changelog

- **Changed**: In `iresfinder_mode=2` (sliding window), `generate_candidates()` now returns the top-N **individual positive windows** as distinct candidate regions, rather than merging all overlapping windows into a single wide region. This satisfies user requests like "return the top 5 candidate regions" and improves spatial resolution.
- **Added**: When no windows pass the probability threshold but `run_structural_validation=True`, the workflow now returns a single rejected candidate for the input sequence (or the mode-1 specified subsequence). The candidate has `ires_probability=0.0`, `confidence=rejected`, and a complete structural metrics bundle, so the user still receives MFE, unpaired fraction, and RNAplfold results.
- **Added**: `AgentRunner` now extracts `iresfinder_mode`, `window_size`, `step_size`, `probability_threshold`, `top_n_candidates`, and `sequence_filepath` deterministically from the user text for the `ires_prediction` workflow. These parameters are marked as user-explicit, preventing the QualityAgent from silently overriding them during auto-retry.
- **Improved**: The IRES prediction quality review (`QualityAgent` + `IRES_QUALITY_PROFILE`) now receives (a) a note confirming that the workflow DNA-normalises RNA input (U→T) before IRESfinder, and (b) the raw IRESfinder summary (`max_score`, `decision_threshold`, `has_putative_ires`, etc.). This prevents the LLM from incorrectly diagnosing a low/zero probability as a nucleotide-alphabet mismatch.

### Locked contracts

#### Input model (`IresPredictionInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `sequence_filepath: str` — required; path to input FASTA or plain sequence file
  - `iresfinder_mode: int` — default `0`, range `[0, 2]` (0=full, 1=header, 2=sliding window)
  - `probability_threshold: float` — default `0.5`, range `[0.0, 1.0]`
  - `window_size: int` — default `174`, range `[20, 5000]` (mode 2 only)
  - `step_size: int` — default `50`, range `[1, 5000]` (mode 2 only)
  - `top_n_candidates: int` — default `5`, range `[1, 100]`
  - `run_structural_validation: bool` — default `True`

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → IRESfinder prediction → **mode 0/1:** merge overlapping windows; **mode 2:** select top-N individual positive windows → extract subsequence → build `Candidate` list (no-positive fallback when structural validation is enabled)
2. `evaluate()` → LinearFold fold (MFE + structure, primary) / ViennaRNA fold (fallback) → dot-bracket unpaired fraction → RNAplfold local accessibility
3. `score()` → composite_score = ires_probability (structure metrics are reported but NOT folded into score)
4. `rank_and_format()` → sort by composite_score → assign confidence → build summary → `WorkflowResult`

#### Scoring formula (must NOT be changed without updating docs and tests)

```python
# Score is driven SOLELY by IRESfinder probability
prob = float(metrics.get("ires_probability", 0.0))
return {
    "ires_probability": prob,
    "composite_score": prob,
}
```

Structural metrics (`mfe_kcal_per_mol`, `mean_unpaired_fraction`, `mean_unpaired_prob_1nt`) are stored in `metrics_bundle` for QualityAgent review and user inspection, but they do NOT affect the numeric score due to lack of calibrated evidence for an optimal unpaired-fraction target.

#### Confidence assignment (must NOT change thresholds without updating tests)

```python
# With structural data
if prob >= 0.8 and 0.3 <= unpaired <= 0.7:  → "high"
if prob >= 0.6 and 0.2 <= unpaired <= 0.8:  → "medium"
if prob >= 0.5:                              → "low"
else:                                        → "rejected"

# Without structural data (downgrade one tier)
prob > 0.8 → "medium", prob > 0.6 → "low", prob > 0.5 → "rejected"
```

#### Required capabilities (must NOT be removed from `required_capabilities`)

```python
required_capabilities = [
    "predict_putative_ires_with_iresfinder",
    "predict_rna_secondary_structure_with_linearfold",  # primary fold
    "predict_rna_secondary_structure",                  # fallback fold
    "predict_rna_local_accessibility_profile_vienna",
    "compute_dot_bracket_unpaired_fraction",
]
```

#### Quality configuration (`IRES_QUALITY_PROFILE`)

- **evaluation_dimensions**: 6 items covering IRES probability, structural validation, unpaired fraction balance, coverage distribution, user constraints, and automatic DNA normalisation
- **adjustable_params**: `probability_threshold`, `window_size`, `step_size`, `top_n_candidates`, `run_structural_validation`, `iresfinder_mode`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `IresPredictionInput` dict used
- `_last_workflow_params`: same as above (for `QualityAgent` reference)
- Internal `tool_results` from IRESfinder and ViennaRNA tools

### Synchronization checklist

- `agent_core/workflows/ires_prediction.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/coordinator_agent.py` (BMC coordination)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/ires_prediction.py` (quality profile)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Existing test suite
pytest tests/test_ires_prediction.py -v
```


## 14. Canonical Reference: Full-Length mRNA Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §4`](WORKFLOWS.md#4).
>
> **Locked on**: 2026-07-05
> **Version**: v2.8.0 (JunctionEvaluator upgraded to full-length constrained-fold ddG W1/W2 report metric; fragment-fold AUG/Kozak burial booleans removed; BMC junction auto-repair via codon shuffling stripped — ddG is report-only)
> **Status**: Borda-count ranking removed; per-junction scores are internal diagnostics only; CDS-level BMC feedback is split by CAI vs MFE; junction GC-diff now uses the actual UTR/CDS fragment boundary instead of the midpoint of the overlap window; BMC diagnosis now considers the ASF best candidate plus per-objective leaders; user-provided `reference_point` is normalized against the initial candidate pool and kept fixed across BMC rounds

### v2.8.0 changelog

- **Changed**: `JunctionEvaluator` now reports a full-length constrained-fold ddG at the 5'UTR-CDS junction instead of fragment-fold burial booleans: `ddG_open = MFE_constrained − MFE_unconstrained` on the full construct (utr5+cds+utr3) via LinearFold, with the AUG-context window forced unpaired ('?' over the full length, '.' inside the window). Two windows: W1 (narrow, CDS start −6..+9, 15 nt) and W2 (wide, 5'UTR tail 60 nt + CDS head 30 nt, clipped to the actual UTR length; actual coordinates recorded per candidate). New `metrics_bundle` fields: `junction_5utr_cds_ddg_open_w1`, `junction_5utr_cds_ddg_open_w2`, `junction_5utr_cds_ddg_{w1,w2}_{start,end}`. The unconstrained full-length MFE is reused from the workflow's full fold (same LinearFold backend only); on any fold failure the ddG fields are `None`. ddG is a **report/profile metric only** — it feeds no score, issue, or repair path. Rationale: the legacy 40-nt fragment-fold + `aug_buried`/`kozak_buried` booleans were falsified as a translation-initiation proxy by three pre-registered experiments (P1 v2, P2, and the Phase 0 ddG pilot `experiments/results/junction_ddg_pilot_summary.json`, 2026-08-05: burial uncorrelated — even anti-correlated — with full-length ddG).
- **Removed**: `JunctionEvaluator` output fields `junction_5utr_cds_aug_found`, `junction_5utr_cds_aug_buried`, `junction_5utr_cds_aug_position`, `junction_5utr_cds_kozak_buried`, `junction_5utr_cds_kozak_position_start` and their propagation in `FullLengthMrnaDesignWorkflow.evaluate()`. `JunctionEvaluator._check_translation_start()` is retained unchanged for experiment-script reproducibility (`experiments/junction_aware_codon_optimizer.py`).
- **Removed**: the BMC junction auto-repair path. `_collect_boolean_issues()` (the only source of boolean issues) and the `boolean_issues` parameter of `ReferencePointCoordinator.diagnose()` are gone, together with the `JUNCTION_5UTR_CDS_AUG_BURIED` / `JUNCTION_5UTR_CDS_KOZAK_BURIED` issue types. `_regenerate_modules()` no longer calls `shuffle_cds_junction_codons`; the `shuffled` CDS source label, `bmc_shuffle_end` candidate metadata, and the `issues` parameter of `_regenerate_modules()` are removed. The `shuffle_cds_junction_codons` tool itself (INTERFACE LOCK v0.1.0) is untouched and remains available for explicit user invocation; it is also removed from `required_capabilities` since the workflow no longer invokes it.
- **Changed**: junction score gaps (`JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE`, `JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE`) are now handled by UTR-preset exploration only; no junction-triggered CDS mutation remains in the workflow.

### v2.7.0 changelog

- **Removed**: the coordinator's `utr_preset_exploration` adjustment and its handling in `_regenerate_modules()`. The mechanism was a no-op for `utr_mode="all"` and a silent violation of the user's explicit single-preset `utr_mode` otherwise (flagged by QualityAgent during PA_019 e2e). UTR presets in BMC rounds now always come from `utr_mode`; junction issues are addressed solely by junction codon shuffling (`shuffle_cds_junction_codons`).

### v2.6.3 changelog

- **Changed**: `required_capabilities` updated for consistency: added `compute_cai_for_cds_sequence` and `shuffle_cds_junction_codons` (local tools); removed unused `predict_putative_ires_with_iresfinder`. `bmc_run_round()` now re-runs service pre-flight at the start of each BMC round so crashed services can be recovered.

### v2.6.2 changelog

- **Changed**: BMC convergence loop migrated from `FullLengthMrnaDesignWorkflow.run()` up into `CoordinatorAgent`. The workflow now exposes the BMC-capable interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`) and `run()` delegates to `CoordinatorAgent` via lazy import. Public `run()` signature and return type are unchanged; behavior is preserved.
- **Added**: `agent_core/agents/coordinator_agent.py` to the synchronization checklist.

### v2.6.1 changelog

- **Modified**: `reference_point` no longer accepts the internal `cds_component` key from users. The valid user-facing keys are now `utr5_mrl`, `utr3_stability`, and `full_mfe_score`. CDS objectives must be specified via `target_cds_mfe` and `target_cds_cai`, which are automatically synthesized into the internal `cds_component` reference point.
- **Modified**: `FullLengthMrnaDesignInput._validate_reference_point()` now validates user-provided `reference_point` keys before injecting the synthesized `cds_component`, and rejects direct user-supplied `cds_component` with a clear error message.

### v2.6.0 changelog

- **Modified**: User-provided `reference_point` is now normalized against the **initial** candidate pool once, before the first BMC round, and the normalized coordinates are kept fixed for diagnosis and ASF comparison across all BMC rounds. This prevents the aspiration level from drifting as new candidates are regenerated. The auto-derived utopian reference point is still re-derived from the current candidate pool each round.
- **Added**: Internal workflow state fields `_reference_point_mode` (`"user"` | `"utopian"`), `_fixed_norm_ref_point`, and `_fixed_dim_bounds` to implement the fixed user-reference-point behavior.
- **Added**: `CoordinationRound` now records `reference_point_mode`, normalized `reference_point`, and per-dimension `dim_bounds` for each BMC round, improving audit traceability.
- **Tests added**: `test_user_reference_point_fixed_across_bmc_rounds`, `test_utopian_reference_point_mode_across_bmc_rounds`, `test_bmc_trace_records_reference_point_metadata`.

### v2.5.2 changelog

- **Modified**: BMC Phase diagnosis in `FullLengthMrnaDesignWorkflow.run()` now diagnoses a representative set containing the ASF `best_candidate` plus the per-objective leader for each user-facing objective (`cds_component`, `utr5_mrl`, `utr3_stability`, `full_mfe_score`). Issues are merged by `issue_type` keeping the maximum `violation`. This exposes trade-offs across the candidate pool without changing the public API or output structure.
- **Added**: `_select_diagnosis_candidates()` and `_merge_issues_with_sources()` helper methods to `FullLengthMrnaDesignWorkflow`.
- **Added**: BMC feedback now uses the metrics of the candidate that triggered the worst `CDS_COMPONENT_BELOW_REFERENCE` / `FULL_MFE_SCORE_BELOW_REFERENCE` gap, improving `lambda_value` adjustment direction when the ASF best is not the CDS-quality leader.
- **Added**: `_regenerate_modules()` collects CDS seeds from the full diagnosis set (best + per-objective leaders) when CDS parameters are unchanged, preserving trade-off diversity instead of only reusing the best CDS.
- **Added**: `bmc_max_rounds: int` and `bmc_improvement_threshold: float` to `FullLengthMrnaDesignInput`. `max_rounds` replaces the previous hard-coded value of 1; `bmc_max_rounds=0` disables BMC iteration.
- **Added**: Hard cap of 24 on the number of new candidates generated during a single BMC regeneration round.
- **Added**: Optional `diagnosis_candidate_ids` field to `CoordinationRound` for audit traceability.

### v2.5.1 changelog

- **Fixed**: `JunctionEvaluator` now computes `junction_*_gc_diff` across the actual UTR/CDS boundary (the left fragment is the UTR side, the right fragment is the CDS side), rather than splitting the concatenated overlap sequence at its midpoint. This preserves biological meaning when one side is shorter than the 20-nt overlap window. The scoring formula is unchanged; only the definition of the left/right GC content is corrected.
- **Modified**: `JunctionEvaluator._evaluate_junction()` accepts an optional `split_offset` parameter specifying the boundary between the left and right fragments. `evaluate()` passes `split_offset=len(j1_left)` and `split_offset=len(j2_left)` for the two junctions.

### v2.5.0 changelog

- **Removed**: 5-dimensional equal-weight Borda count from `rank_and_format()`. Candidates are now ranked by ASF distance to the reference point.
- **Removed**: `total_rank`, `total_score`, `cds_rank`, `utr5_rank`, `utr3_rank`, `full_mfe_rank`, `junction_rank` from `candidate.scores`.
- **Removed**: `junction_score` from `ReferencePointCoordinator.OBJECTIVES` and from user-facing `reference_point` keys.
- **Modified**: `reference_point` valid keys reduced to user-facing objectives only: `cds_component`, `utr5_mrl`, `utr3_stability`, `full_mfe_score`. `junction_5utr_cds_score` and `junction_cds_3utr_score` remain internal coordinator diagnostics.
- **Modified**: `FullLengthBMCScoringFunction` junction GC-diff penalty coefficient reduced from `5.0` to `1.0` so MFE and GC-smoothness terms contribute on comparable scales.
- **Modified**: BMC convergence metric changed from Borda `total_score` to normalized ASF improvement; `improvement_threshold` changed from `1.0` to `0.05`.
- **Modified**: CDS-level BMC feedback is now split: `CDS_CAI_BELOW_REFERENCE` increases λ by 2; `CDS_MFE_BELOW_REFERENCE` decreases λ by 2.
- **Added**: `target_cds_mfe` and `target_cds_cai` input fields. When both are provided, they are converted into a `cds_component` reference point value.
- **Added**: Full-length GC content evaluation (`full_length_gc` in `metrics_bundle`).

### v2.4.0 changelog

- **Removed**: `pareto_output: bool` from `FullLengthMrnaDesignInput`. The Pareto frontier is now always computed and returned.
- **Removed**: `bmc_targets: Optional[dict[str, float]]` from `FullLengthMrnaDesignInput`.
- **Removed**: `FullLengthCoordinator` and `LLMFullLengthCoordinator`; replaced by `ReferencePointCoordinator`.
- **Modified**: `bmc_mode: Literal["rp"]` — retained for interface compatibility; only `"rp"` (reference-point driven) is accepted.
- **Modified**: `rank_and_format()` — `best_candidate` is now always selected by ASF distance to a reference point. If the user does not supply `reference_point`, a utopian point is derived from the candidate pool. The legacy 5-d Borda winner path is removed; `total_rank`/`total_score` are still computed for display and backward compatibility.
- **Modified**: `WorkflowResult` always carries `pareto_frontier`, `reference_point`, and `best_candidate_source` fields (when candidates exist).
- **Modified**: BMC Phase diagnosis now measures normalized gaps to the reference point in maximization-space objective dimensions. Convergence uses continuous violation scores (`sum(issue.violation)`).
- **Added**: Per-junction score dimensions `junction_5utr_cds_score` and `junction_cds_3utr_score`, enabling precise feedback for the 5'UTR-CDS and CDS-3'UTR junctions respectively.

### v2.3.0 changelog

- **Added**: `reference_point: Optional[dict[str, float]]` to `FullLengthMrnaDesignInput` — user-provided per-objective aspiration point for Achievement Scalarizing Function (ASF) selection. Valid keys: `cds_component`, `utr5_mrl`, `utr3_stability`, `full_mfe_score`, `junction_score`.
- **Added**: `pareto_output: bool` to `FullLengthMrnaDesignInput` — when `True`, `rank_and_format()` computes and returns the Pareto-optimal frontier via `WorkflowResult.pareto_frontier`.
- **Added**: `agent_core/workflows/multi_objective.py` — reusable utilities for normalization, ASF scalarization, Pareto dominance, and frontier capping.
- **Modified**: `rank_and_format()` — when `reference_point` is provided, `best_candidate` is selected by ASF distance to the reference point (per-dimension min-max normalized within the candidate pool); otherwise the existing 5-d Borda winner is used. `total_rank`/`total_score` are preserved for backward compatibility.
- **Modified**: `WorkflowResult` now optionally carries `pareto_frontier`, `reference_point`, and `best_candidate_source` fields.

### v2.2.0 changelog

- **Modified**: `FullLengthCoordinator.THRESHOLDS` junction MFE thresholds are now length-normalized (`junction_5utr_cds_mfe_per_nt: -0.50`, `junction_cds_3utr_mfe_per_nt: -0.375`), derived from the previous absolute thresholds calibrated on a 40-nt overlap. The coordinator and BMC scoring function now require `junction_*_mfe_per_nt`; raw `junction_*_mfe` values are no longer interpreted for threshold or scoring decisions.
- **Fixed**: `FullLengthMrnaDesignWorkflow.evaluate()` now propagates `junction_5utr_cds_aug_*` and `junction_5utr_cds_kozak_*` accessibility metrics into the coordinator `metrics_bundle`, activating the previously dormant AUG/Kozak burial diagnosis rules.
- **Improved**: `JunctionEvaluator._check_translation_start()` now receives the CDS start offset within the junction sequence. It checks the canonical start codon at the 5'UTR–CDS boundary instead of scanning for the first AUG, avoiding false positives from upstream AUGs (uAUGs) in the 5'UTR portion.
- **Modified**: `FullLengthBMCScoringFunction.score()` now uses length-normalized `junction_*_mfe_per_nt` values to compute `junction_score`.
- **Added**: `JunctionEvaluator` now records `junction_*_length` and `junction_*_mfe_per_nt` for each junction.

### v2.1.0 changelog

- **Added**: `bmc_mode: Literal["full", "llm_coord"]` to `FullLengthMrnaDesignInput` — selects deterministic `FullLengthCoordinator` (default) or `LLMFullLengthCoordinator` ablation.
- **Added**: `LLMFullLengthCoordinator` — inherits from `FullLengthCoordinator`, overrides only `diagnose()` with an LLM call, reuses `broadcast_feedback()`/`has_converged()`, and falls back to deterministic rules on any failure.
- **Modified**: `FullLengthCoordinator.THRESHOLDS` now includes `junction_5utr_cds_mfe: -20.0` (previously hard-coded in `diagnose()`).

### v2.0.0 changelog

- **Added**: `Bounded Multi-Module Coordination (BMC)` — deterministic, rule-based coordinator for inter-module conflict diagnosis and iterative refinement.
- **Added**: `JunctionEvaluator` — evaluates 5'UTR–CDS and CDS–3'UTR junction MFE and GC continuity.
- **Added**: `FullLengthBMCScoringFunction` — weighted scoring with junction-aware penalty terms.
- **Added**: `FullLengthCoordinator` — deterministic rule engine (not LLM) for auditable conflict diagnosis.
- **Added**: `UContentEvaluator` — evaluates U content for both CDS (via `MrnaCdsDesignWorkflow` sub-evaluator) and full-length sequence.
- **Restored**: `UTR5MrlEvaluator` and `UTR3StabilityEvaluator` real invocation (previously hard-coded to empty dict in benchmark mode). Both evaluators now call `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna` respectively.
- **Modified**: `run()` method — now executes three phases (generate → evaluate/rank → bounded iterative coordination).
- **Modified**: `rank_and_format()` — uses a 5-dimensional equal-weight Borda count over CDS, 5'UTR MRL, 3'UTR stability, full-length MFE, and junction metrics.

### Locked contracts

#### Input model (`FullLengthMrnaDesignInput`)

- `protein_sequence: str` — required
- `design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"]` — default `"all"`
- `lambda_value: Optional[float]` — required when `design_tool="lineardesign"`
- `model_type: str` — default `"Homo sapiens mRNA"`
- `cai_species: str` — default `"Homo sapiens"`
- `utr_mode: Literal["short", "medium", "long", "all"]` — default `"all"`
- `run_fold: bool` — default `True`
- `run_gc: bool` — default `True`
- `bmc_mode: Literal["rp"]` — default `"rp"`; retained for interface compatibility. Only the reference-point driven coordinator is supported.
- `reference_point: Optional[dict[str, float]]` — default `None`; per-objective aspiration point for ASF-based `best_candidate` selection and BMC coordination. If omitted, a utopian point is derived from the candidate pool. **User-facing keys only**: `utr5_mrl`, `utr3_stability`, `full_mfe_score`. The internal `cds_component` key is no longer accepted directly from users; CDS objectives are supplied via `target_cds_mfe` and `target_cds_cai`, which are automatically synthesized into `cds_component`. Junction scores remain internal diagnostics and are rejected as user reference-point keys.
- `target_cds_mfe: Optional[float]` — default `None`; user-aspired CDS MFE in kcal/mol (more negative = more stable). Must be provided together with `target_cds_cai`.
- `target_cds_cai: Optional[float]` — default `None`; user-aspired CAI in `(0, 1]`. Must be provided together with `target_cds_mfe`. When both are provided, the workflow computes and injects the internal `cds_component` value into `reference_point`.

  The allowed `model_type` values and `cai_species` aliases are maintained in `agent_core/constants/species.py` (`RNARL_MODEL_TYPES_LIST` and `CAI_SPECIES_ALIASES` / `DEFAULT_CAI_SPECIES`).

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.

#### Output extensions (v2.4.0)

`WorkflowResult` always includes (when candidates exist):

- `pareto_frontier: List[Candidate]` — non-dominated candidates; each may carry `metadata["pareto_tag"]` describing its leading dimension.
- `reference_point: dict[str, float]` — the reference point used for ASF selection (user-provided or auto-derived utopian).
- `best_candidate_source: str` — `"reference_point_optimization"`.
#### `required_capabilities` (v2.8.0)

```python
required_capabilities = [
    # UTR design / prediction
    "design_5utr_with_gemorna",               # port 8004
    "design_3utr_with_gemorna",               # port 8004
    "predict_5utr_mrl_with_gemorna",          # port 8004
    "predict_3utr_stability_with_gemorna",    # port 8004
    # CDS generation / evaluation (delegated to MrnaCdsDesignWorkflow)
    "design_mrna_cds_with_lineardesign",      # port 8014
    "design_mrna_cds_with_rnarl",             # port 8008
    "design_mrna_cds_with_gemorna",           # port 8004
    "compute_cai_for_cds_sequence",           # local pure-Python tool
    "compute_rna_sequence_gc_content",        # port 8020
    "compute_dot_bracket_unpaired_fraction",  # port 8020
    # Shared folding / metrics
    "predict_rna_secondary_structure",        # port 8003 (ViennaRNA)
    "predict_rna_secondary_structure_with_linearfold",  # port 8015
    "predict_mrna_stability_with_rnastop",    # port 8009
    "compute_rna_sequence_u_content",         # port 8020
]
```

> **Note**: `predict_mrna_stability_with_rnastop` is registered in `required_capabilities` but may be skipped in certain execution paths (e.g. benchmark timeout guards). `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna` are **always invoked** via their respective evaluators as of 2026-06-09. `compute_cai_for_cds_sequence` is a local tool with no microservice; it is listed for capability consistency and future service-proofing. `shuffle_cds_junction_codons` was removed from this list in v2.8.0 when the BMC junction auto-repair path was stripped; the tool itself remains locked and available for explicit user invocation. `predict_rna_secondary_structure_with_linearfold` also serves the junction ddG report metric (constrained full-length folds, v2.8.0).

#### Pipeline stages (v2.5.0)

1. `generate_candidates()` → CDS via `MrnaCdsDesignWorkflow` + UTR combinations
2. `evaluate()` → full-length fold + **5'UTR MRL (`predict_5utr_mrl_with_gemorna`)** + **3'UTR stability (`predict_3utr_stability_with_gemorna`)** + junction metrics + CDS U content + full-length U content + **full-length GC content**
3. `score()` → per-module raw scores for reference-point optimization
4. `rank_and_format()` → ASF-based ranking; Pareto frontier on user-facing objectives
5. **BMC Phase** (bounded):
   - Coordinator: `ReferencePointCoordinator`
   - Build normalized reference point from the candidate pool and user `reference_point` (user-facing objectives only)
   - `coordinator.diagnose(norm_best_vector, norm_reference_point)` → list of `Issue`
   - If total violation > 0 → `broadcast_feedback(issues, best_candidate_metrics)` → `_regenerate_modules()` → re-evaluate → re-rank
   - Hard bounds: `max_rounds=1`, `improvement_threshold=0.05` (normalized ASF space); early stop on degradation or insufficient improvement

#### BMC Coordinator (reference-point driven)

The `ReferencePointCoordinator` diagnoses gaps in normalized objective space. Each objective is converted to maximization space and min-max normalized within the candidate pool. The reference point is user-provided (`reference_point`) or auto-derived as the utopian point. A gap (`reference − candidate`) > 0 produces an issue whose `violation` equals the gap.

| Score dimension | Module(s) | Issue type (when below reference) | Parameter action |
|-----------------|-----------|-----------------------------------|------------------|
| `cds_component` | CDS | `CDS_COMPONENT_BELOW_REFERENCE` | See sub-diagnosis below |
| `full_mfe_score` | 5UTR, CDS, 3UTR | `FULL_MFE_SCORE_BELOW_REFERENCE` | See sub-diagnosis below |
| `utr5_mrl` | 5UTR | `UTR5_MRL_BELOW_REFERENCE` | None (UTR presets honour `utr_mode`) |
| `utr3_stability` | 3UTR | `UTR3_STABILITY_BELOW_REFERENCE` | None (UTR presets honour `utr_mode`) |
| `junction_5utr_cds_score` (internal) | 5UTR, CDS | `JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE` | None (UTR-preset exploration only) |
| `junction_cds_3utr_score` (internal) | CDS, 3UTR | `JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE` | None (UTR-preset exploration only) |

**CDS sub-diagnosis**: When `CDS_COMPONENT_BELOW_REFERENCE` or `FULL_MFE_SCORE_BELOW_REFERENCE` is emitted, the coordinator inspects raw `cds_cai` and `cds_mfe` to decide the λ direction:
- CAI is the weak component (`cds_cai` well below aspiration) → **Increase** λ by 2 (favor CAI).
- MFE stability is the weak component (`cds_mfe` less negative than aspiration) → **Decrease** λ by 2 (favor MFE).
- Both weak, or raw metrics unavailable → **Decrease** λ by 2 (default to stability).

**Physics note**: LinearDesign λ is inversely related to MFE stability — **lower λ → more negative MFE** (more stable), **higher λ → higher CAI**. Pure junction issues do **not** adjust λ, because λ is a global CDS parameter and its effect on a 40-nt junction (only 20 nt from the CDS side) is heavily diluted.

**Length-normalization note**: Absolute MFE is proportional to sequence length (Zhang et al., Nature 2023). The Coordinator uses `MFE / total_length` (kcal/mol/nt) and `paired_fraction` (from the dot-bracket structure produced by the fold tool — LinearFold primary, ViennaRNA fallback) instead of fixed absolute thresholds, ensuring fairness across targets of different lengths.

**Junction local-control note**: As of v2.8.0 there is no junction-triggered CDS mutation in the workflow: the former junction codon-shuffling repair (`shuffle_cds_junction_codons` on `JUNCTION_*` issues) was removed after the burial booleans it served were falsified (P1 v2 / P2 / Phase 0 ddG pilot). Pure junction score gaps are addressed only by UTR-preset exploration, which always honours the user's `utr_mode` selection (the former "UTR preset exploration" adjustment was removed in v2.7.0 because it only ever took effect by silently violating an explicit single-preset `utr_mode`). The 5'UTR-CDS junction's translation-start openness is reported via the full-length ddG metrics (`junction_5utr_cds_ddg_open_w1/w2`) — report/profile only, never a repair trigger. When no λ adjustment is needed, the current best CDS is reused instead of re-generated, avoiding wasted computation.

**Tool-switch note**: If `design_tool="all"` and a global issue triggers a λ adjustment, `_adjust_input_from_feedback()` automatically switches `design_tool` to `"lineardesign"` so the λ change takes effect (the fixed λ grid for `"all"` would otherwise ignore the adjustment).

#### Scoring formulas

Per-module raw scores (all in maximization space):

```python
cds_component      = (-cds_mfe + codons * log(cai)) / cds_length
utr5_mrl           = predicted_mean_ribosomal_load
utr3_stability     = predicted_3utr_stability
full_mfe_score     = -full_length_mfe
junction_5utr_cds_score = -junction_5utr_cds_mfe_per_nt - junction_5utr_cds_gc_diff
junction_cds_3utr_score = -junction_cds_3utr_mfe_per_nt - junction_cds_3utr_gc_diff
```

where `junction_*_gc_diff = abs(gc_content(left_fragment) - gc_content(right_fragment))`. The left and right fragments are the actual UTR and CDS portions of the overlap window (e.g. last 20 nt of 5'UTR vs first 20 nt of CDS), not the first and second halves of the concatenated sequence.

`best_candidate` is selected by minimizing the Achievement Scalarizing Function (ASF) distance to the reference point in normalized objective space. Candidates are ranked by ASF distance (lower = better). The Pareto frontier is computed on the four user-facing objectives.

`FullLengthBMCScoringFunction` is used by `FullLengthMrnaDesignWorkflow.score()` for all candidates.

#### State writeback additions (v2.0.0)

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `FullLengthMrnaDesignInput` dict used
- `_bmc_trace`: list of `CoordinationRound` dicts recording each iteration's issues, feedback, modules reinvoked, and timing

### Synchronization checklist

- `agent_core/workflows/full_length_mrna_design.py` (source of truth)
- `agent_core/workflows/coordinator.py` (BMC coordinator)
- `agent_core/workflows/evaluators.py` (JunctionEvaluator, UContentEvaluator)
- `agent_core/workflows/scoring.py` (FullLengthBMCScoringFunction)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/coordinator_agent.py` (BMC Agent-layer controller)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/full_length_mrna_design.py` (quality profile)
- ... (see source lock comment for full list)

### Tests that must pass

```bash
# Core unit tests (no microservices)
pytest tests/test_full_length_mrna_design.py tests/test_bmc_full_length_mrna.py -v

# Layer 4 tests
pytest tests/test_full_length_mrna_design_layer4.py -v

# E2E mock tests
pytest tests/test_bmc_workflow_e2e_mock.py -v
```

### Live microservice end-to-end smoke test

Required services are auto-started by the workflow pre-flight (no manual launcher). Run the PA_004 human EPO regression with real LinearDesign/GEMORNA/ViennaRNA/LinearFold/IRESfinder/RNASTOP/sequence-metrics services:

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" python tests/test_full_length_mrna_e2e_live.py
```

> The full-length workflow uses the deterministic `ReferencePointCoordinator` by default. No LLM API key is required for BMC coordination.


## 15. Canonical Reference: RNA Aptamer Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §10`](WORKFLOWS.md#10-rna-aptamer-design).
>
> **Locked on**: 2026-07-05
> **Version**: v1.4.2 (reference-point/ASF ranking; hard-threshold BMC replaced by reference-point diagnosis; BMC loop orchestrated by CoordinatorAgent)
> **Status**: ✅ Implemented with BMC Type-II Coordinator

> **Additive note (2026-07-20, Fig 5b ablation, no version bump)**: `AptamerCoordinator.broadcast_feedback()` gained an optional `pool_metrics` keyword argument, and `RnaAptamerDesignWorkflow` gained a private `_pool_mean_metrics()` helper. Both are inert unless the subprocess runs with `APTAMER_FEEDBACK_MODE=pool_average`; the default `source_aware` path is byte-identical to v1.4.2. No locked field, signature, or return structure was changed.

### v1.4.2 changelog

- **Changed**: `RnaAptamerDesignWorkflow._ensure_services_running()` now returns a failed `WorkflowResult` instead of raising `RuntimeError` on pre-flight failure. `run_initial()` returns this structured result, and `bmc_run_round()` re-runs service pre-flight at the start of each BMC round so crashed services can be recovered between rounds.

### v1.4.1 changelog

- **Changed**: BMC convergence loop migrated from `RnaAptamerDesignWorkflow.run()` up into `CoordinatorAgent`. The workflow now exposes the BMC-capable interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`) and `run()` delegates to `CoordinatorAgent` via lazy import. Public `run()` signature and return type are unchanged; behavior is preserved.
- **Added**: `agent_core/agents/coordinator_agent.py` to the synchronization checklist.

### v1.4.0 changelog

- **Removed**: `bmc_mode` and `bmc_targets` from `RnaAptamerDesignInput`.
- **Removed**: `LLMAptamerCoordinator` and all mode-specific BMC branches.
- **Removed**: weighted-sum `total_score` from `score_aptamer_candidate()` and ranking. Candidates are now ranked strictly by ASF distance to the reference point.
- **Added**: `bmc_max_rounds: int` (default `1`, `ge=0`) to `RnaAptamerDesignInput`.
- **Added**: `bmc_improvement_threshold: float` (default `0.05`, `ge=0.0`) to `RnaAptamerDesignInput`.
- **Modified**: `RnaAptamerDesignWorkflow.rank_and_format()` now applies `_apply_reference_point_and_pareto()` (mirrors `FullLengthMrnaDesignWorkflow`). `best_candidate` is the ASF closest candidate; `pareto_frontier` is always returned; `reference_point` is normalized against the initial candidate pool and fixed across BMC rounds.
- **Modified**: `score_aptamer_candidate()` returns only component scores (`egarps_component`, `rhofold_component`, `iptm_component`); no `total_score`.
- **Modified**: `AptamerCoordinator.diagnose()` compares normalized objective vectors against the reference point and emits `{objective}_BELOW_REFERENCE` issues.
- **Modified**: BMC module adjustments now map directly to reference-point gaps: `EGARPS_COMPONENT_BELOW_REFERENCE`, `RHOFOLD_COMPONENT_BELOW_REFERENCE`, `IPTM_COMPONENT_BELOW_REFERENCE`.
- **Modified**: `AptamerCoordinationRound` added `reference_point_mode`, `reference_point`, and `dim_bounds`; `diagnosis_candidate_ids` was retained.

### v1.3.0 changelog

- **Added**: `RnaAptamerDesignWorkflow._select_diagnosis_candidates()` — returns the ASF best candidate plus per-objective leaders for BMC diagnosis.
- **Added**: `RnaAptamerDesignWorkflow._merge_issues_with_sources()` — merges diagnosed issues by type, keeping the worst violation and the source candidate's metrics bundle.
- **Modified**: `AptamerCoordinator.broadcast_feedback()` — `metrics` is now a required argument; feedback rules are source-aware.
- **Modified**: `AptamerCoordinator._target_adjustments()` and `_aptamer_adjustments()` — `metrics` is now a required argument.
- **Modified**: `AptamerCoordinationRound` — added `diagnosis_candidate_ids: list[str]` to the audit trace.
- **Modified**: `RnaAptamerDesignWorkflow._regenerate_modules()` — added required `issues` and `issue_source_metrics` arguments.
- **Modified**: BMC Phase 3 now diagnoses a representative candidate set (best + per-objective leaders), uses the worst issue's source metrics for feedback, and adjusts `aptamer_length_delta` aggressively (10 nt) when `rhofold_mean_plddt < 60.0`.

### v1.2.0 changelog

- **Removed**: `pareto_output: bool` from `RnaAptamerDesignInput`. The Pareto frontier is now always computed and returned.
- **Added**: `bmc_targets: Optional[dict[str, float]]` to `RnaAptamerDesignInput` — optional overrides for `AptamerCoordinator` target values. Valid keys: `egarps_native_probability`, `rhofold_mean_plddt`, `proteinx_ipTM`, `interface_contacts`, `buried_sasa`, `gc_content`.
- **Modified**: `rank_and_format()` — `best_candidate` is now always selected by ASF distance to a reference point. If the user does not supply `reference_point`, a utopian point is derived from the candidate pool. The legacy weighted-sum winner path is removed; `total_score` is still computed for display and backward compatibility.
- **Modified**: `WorkflowResult` always carries `pareto_frontier`, `reference_point`, and `best_candidate_source` fields (when candidates exist).
- **Modified**: BMC Phase convergence now uses continuous violation scores (`sum(issue.violation)`) instead of a binary issue count.

### v1.1.0 changelog

- **Added**: `reference_point: Optional[dict[str, float]]` to `RnaAptamerDesignInput` — user-provided per-objective aspiration point for Achievement Scalarizing Function (ASF) selection. Valid keys: `egarps_component`, `rhofold_component`, `iptm_component`.
- **Added**: `pareto_output: bool` to `RnaAptamerDesignInput` — when `True`, `rank_and_format()` computes and returns the Pareto-optimal frontier via `WorkflowResult.pareto_frontier`.
- **Modified**: `rank_and_format()` — when `reference_point` is provided, `best_candidate` is selected by ASF distance to the reference point (per-dimension min-max normalized within the candidate pool), using `weight_egarps`/`weight_rhofold`/`weight_iptm` as dimension weights; otherwise the existing weighted-sum winner is used. `total_score` is preserved for backward compatibility.
- **Modified**: `WorkflowResult` now optionally carries `pareto_frontier`, `reference_point`, and `best_candidate_source` fields.

### Locked contracts

#### Input model (`RnaAptamerDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `protein_sequence: Optional[str]` — amino-acid string (fallback when no structure path is supplied; if both are provided, the structure path is used)
  - `protein_structure_path: Optional[str]` — PDB or mmCIF file path
  - `chain_id: str` — default `"A"`
  - `aptamer_length: int` — default `30`
  - `hotspot_residues: Optional[str]` — e.g. `"A/18,A/90"`; auto-detected if omitted
  - `n_odesign_samples: int` — default `8`
  - `odesign_seeds: list[int]` — default `[42, 123]`
  - `bmc_max_rounds: int` — default `1`, must be `>= 0`
  - `bmc_improvement_threshold: float` — default `0.05`, must be `>= 0.0`
  - `reference_point: Optional[dict[str, float]]` — default `None`; per-objective aspiration point for ASF-based ranking and BMC diagnosis. If omitted, a utopian point is derived from the candidate pool. Valid keys: `egarps_component`, `rhofold_component`, `iptm_component`.

  Internal defaults (not exposed as input fields):
  - Hierarchical evaluation: light stage (GC + RhoFold) runs on all candidates; full stage (ProteinX + interface + EGARPS) runs only on `top_k = max(5, int(len(candidates) * 0.5))` candidates.
  - BMC: `max_rounds = bmc_max_rounds`; `improvement_threshold = bmc_improvement_threshold`.
  - Concurrent evaluation: `ThreadPoolExecutor(max_workers=4)` for both light and full stages.
  - EGARPS gating: skipped when `rhofold_mean_plddt < 65.0` or `gc_content < 0.25` or `gc_content > 0.85`.

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.

#### Pipeline stages

1. `identify_protein_binding_hotspots()` — hotspot residue identification (cached by structure+chain)
2. `build_odesign_aptamer_input_json()` — ODesign input preparation
3. `run_odesign_inference()` — aptamer sequence generation (port 8012)
4. `evaluate()` — per candidate; the workflow uses a two-stage hierarchical filter:
   - **light stage** (`_evaluate_light()`): GC content + RhoFold 3D structure prediction (port 8005) for all candidates
   - **full stage** (`evaluate()`): ProteinX RNA-protein complex prediction (port 8022) + EGARPS complex scoring (port 8023) + interface analysis (pure Python) only for the top `max(5, int(n*0.5))` candidates by coarse score
   - EGARPS is further gated: skipped when `rhofold_mean_plddt < 65.0` or GC content is outside `[0.25, 0.85]`
5. `score()` — component scoring (`egarps_component`, `rhofold_component`, `iptm_component`)
6. `rank_and_format()` — ASF-distance ranking to the reference point; Pareto frontier always returned
7. BMC Phase-II coordination (`AptamerCoordinator`), only if `bmc_max_rounds > 0`:
   - `_select_diagnosis_candidates()` builds a representative set: ASF best + per-objective leaders across `AptamerCoordinator.USER_FACING_OBJECTIVES`.
   - Each candidate in the set is diagnosed against the reference point; issues are merged by type with `_merge_issues_with_sources()`, preserving the source metrics bundle of the worst violation.
   - `broadcast_feedback()` receives the source metrics of the worst issue, enabling differentiated module adjustments (e.g., `aptamer_length_delta` becomes 10 nt when `rhofold_mean_plddt < 60.0`).
   - `_regenerate_modules()` consumes the merged issues and source metrics to produce adjusted candidates.

#### Scoring formula

```python
# Component scores (all in [0, 1])
egarps_component  = max(0.0, min(1.0, egarps_native_probability))
rhofold_component = max(0.0, min(1.0, rhofold_mean_plddt / 100.0))
iptm_component    = max(0.0, min(1.0, proteinx_ipTM))

# Ranking: ASF distance to the reference point
candidate_vector = [egarps_component, rhofold_component, iptm_component]
asf_distance = max(
    weight_i * (reference_point[i] - normalized(candidate_vector[i]))
    for i in objectives
)
```

`weight_i` defaults to `1/3` per objective. User-provided `reference_point` values are normalized against the initial candidate pool; if omitted, a utopian point is derived from the pool.

#### Output extensions

`WorkflowResult` always includes (when candidates exist):

- `pareto_frontier: List[Candidate]` — non-dominated candidates; each may carry `metadata["pareto_tag"]` describing its leading dimension.
- `reference_point: dict[str, float]` — the reference point used for ASF selection (user-provided or auto-derived utopian).
- `best_candidate_source: str` — `"reference_point_optimization"`.

#### BMC Type-II Coordinator reference-point diagnosis

The `AptamerCoordinator` no longer uses fixed biological thresholds. The reference point is the single source of truth. For each candidate in the diagnosis set, the coordinator computes the normalized gap `reference_point[dim] - candidate_value[dim]` and emits an issue when the gap is positive.

| Issue type | Objective | Affected modules | Meaning |
|------------|-----------|------------------|---------|
| `EGARPS_COMPONENT_BELOW_REFERENCE` | `egarps_component` | Target, Aptamer | Affinity below the reference point |
| `RHOFOLD_COMPONENT_BELOW_REFERENCE` | `rhofold_component` | Aptamer | Foldability below the reference point |
| `IPTM_COMPONENT_BELOW_REFERENCE` | `iptm_component` | Target, Aptamer | Complex confidence below the reference point |

Each issue carries a continuous `violation` equal to the normalized gap.

#### BMC module adjustments (source-aware, v1.4.0)

Feedback is generated from the metrics of the candidate that triggered the worst violation, not from the ASF best candidate. Key adjustments:

| Issue type | Affected module | Adjustment | Notes |
|------------|-----------------|------------|-------|
| `EGARPS_COMPONENT_BELOW_REFERENCE` | Target | `hotspot_expansion += 2` | Expand hotspot window |
| `IPTM_COMPONENT_BELOW_REFERENCE` | Target | `hotspot_expansion += 2` | Expand hotspot window |
| `RHOFOLD_COMPONENT_BELOW_REFERENCE` | Aptamer | `aptamer_length_delta = 5` (default) or `10` if `rhofold_mean_plddt < 60.0` | Increase length to improve foldability |
| `EGARPS_COMPONENT_BELOW_REFERENCE` | Aptamer | `n_samples_delta += 5`, `seed_change` | More samples + new seeds; final `n_odesign_samples` capped at 20 |
| `IPTM_COMPONENT_BELOW_REFERENCE` | Aptamer | `n_samples_delta += 5`, `seed_change` | More samples + new seeds; final `n_odesign_samples` capped at 20 |

The `aptamer_length_delta` value is added to `inp.aptamer_length` in `_regenerate_modules()` (capped at 200 nt). The adjusted sample count is capped at 20 in the same function.

#### Quality review

- **AptamerCoordinator** (workflow-internal): deterministic reference-point-driven diagnosis engine.
- **QualityAgent** (pipeline-level): LLM-driven quality review using `RNA_APTAMER_QUALITY_PROFILE` for user-intent alignment and advisory retry decisions.

### Synchronization checklist

- `agent_core/workflows/rna_aptamer_design.py`
- `agent_core/workflows/coordinator.py`
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/coordinator_agent.py` (BMC Agent-layer controller)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/rna_aptamer_design.py` (quality profile)
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `tests/test_rna_aptamer_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `docs/BMC_FRAMEWORK.md`
- `AGENTS.md`

---

## 16. Canonical Reference: RNA Secondary Structure Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §6`](WORKFLOWS.md#6).
>
> **Locked on**: 2026-05-20
> **Version**: v1.0.0
> **Status**: ✅ Implemented

### Locked contracts

#### Input model (`RnaSecondaryStructureDesignInput`)

- `target_structure: str` — required, dot-bracket notation
- `start_sequence: Optional[str]` — optional hint sequence
- `repeats: int` — default `10`
- `num_invocations: int` — default `3`
- `temp_c: float` — default `37.0`; folding temperature (°C)
- `function_mode: Literal["m", "p", "mp"]` — default `"m"`; RNAinverse mode

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages

1. `inverse_fold_rna_secondary_structure_vienna()` — ViennaRNA RNAinverse (port 8003)
2. Deduplication
3. `evaluate()` — GC content + RNAfold validation + structure Hamming distance
4. `score()` — `structure_component = 1 - structure_distance / sequence_length`

#### Quality strategy

- Retry trigger: no candidates, or all `structure_distance / length > 0.02`
- Retry limit: 3 total runs (configured in `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE`)
- Retry actions: increase `repeats`, increase `num_invocations`

### Synchronization checklist

- `agent_core/workflows/rna_secondary_structure_design.py`
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/rna_secondary_structure_design.py` (quality profile)
- `tests/test_rna_secondary_structure_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`

---

## 17. Canonical Reference: RNA Tertiary Structure Design Workflow

> For full pipeline, scoring details, and quality review strategy, see [`WORKFLOWS.md §7`](WORKFLOWS.md#7).
>
> **Locked on**: 2026-05-20
> **Version**: v1.0.0
> **Status**: ✅ Implemented

### Locked contracts

#### Input model (`RnaTertiaryStructureDesignInput`)

- `structure_filepath: str` — required; accepts a repo-relative path, absolute path, or PDB ID (e.g., `"1ehz"` resolves to `data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/structures/1ehz_clean.pdb`)
- `secondary_structure_filepath: Optional[str]` — optional contact-map `.npy`; accepts a path or PDB ID and is auto-resolved against the same benchmark directory
- `design_tools: Literal["all", "rhodesign", "ribodiffusion"]` — default `"all"`
- `n_samples_per_tool: int` — default `3`
- `rhodesign_temperature: float` — default `0.8`
- `rhodesign_temperature_range: float` — default `0.5`
- `ribodiffusion_sampling_steps: int` — default `50`
- `ribodiffusion_cond_scale: float` — default `-1.0`
- `ribodiffusion_dynamic_threshold: bool` — default `True`
- `weight_rhofold: float` — default `0.5`; weight for RhoFold pLDDT component
- `weight_rmsd: float` — default `0.5`; weight for RMSD component

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages

1. Candidate generation:
   - `design_rna_sequence_with_rhodesign()` (port 8006), one call per temperature sample
   - `design_rna_inverse_fold_with_ribodiffusion()` (port 8021), one call with `n_samples = n_samples_per_tool`, `deterministic=False`, `dynamic_threshold=True`
2. Deduplication across both tools by exact sequence identity
3. State field `_pre_dedup_design_tool_counts` records raw counts before deduplication (RhoDesign, RiboDiffusion, unique) for auditability and `QualityAgent` context
3. `evaluate()` — GC + MFE + RhoFold pLDDT + RMSD/TM-score
4. `score()` — `0.5 * (pLDDT/100) + 0.5 * max(0, 1 - RMSD/5.0)`

#### Quality strategy

- Retry trigger: all candidates pLDDT < 70, or candidate count < 2, or all GC outside [0.25, 0.75]
- Retry limit: 3 total runs (configured in `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE`)
- Retry actions: increase `n_samples`, adjust temperature, filter GC outliers, adjust `ribodiffusion_cond_scale` / `ribodiffusion_dynamic_threshold`
- Quality context includes `_pre_dedup_design_tool_counts` and `tool_presence_verdict` so the `QualityAgent` can distinguish "tool failed" from "tool produced only duplicate sequences"

### Synchronization checklist

- `agent_core/workflows/rna_tertiary_structure_design.py`
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution and retry)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/rna_tertiary_structure_design.py` (quality profile)
- `tests/test_rna_tertiary_structure_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`

---

## 18. Canonical Reference: mRNA Sequence Scoring Workflow

> **Locked on**: 2026-05-15
> **Version**: v1.1.0
> **Status**: ✅ Implemented

### v1.1.0 changelog

- **Changed**: `MrnaSequenceScoringWorkflow.__init__` now takes a `CapabilityRegistry` like every other workflow (previously a raw `ToolExecutor`). The registry's `executor` is still used internally for tool dispatch and trace records. `AgentRunner` and `run_mrna_sequence_scoring()` updated accordingly; the convenience function now accepts `capability_registry=` instead of `registry=`/`executor=`.

### Locked contracts

#### Input model (`MrnaSequenceScoringInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `sequence: Optional[str]` — single RNA/DNA sequence string
  - `sequences: Optional[List[str]]` — multiple sequences (alternative to `sequence`)
  - `gc_tool_name: str` — default `"compute_rna_sequence_gc_content"`
  - `fold_tool_name: str` — default `"predict_rna_secondary_structure_with_linearfold"`
  - `fold_service_url: str` — default `"http://127.0.0.1:8015/fold"`
  - `gc_service_url: str` — default `"http://127.0.0.1:8020/gc-content"`
  - `run_gc_tool: bool` — default `True`
  - `run_fold_tool: bool` — default `True`

  Additionally, every tool invoked by this workflow exposes its parameters as optional `{tool_alias}_{param}` override fields, populated from `tools_parameter_analysis.json`. Workflow-level fields keep their original defaults and semantics; tool-level defaults are used only when the override field is explicitly supplied.
#### Pipeline stages

1. `generate_candidates()` → read sequence → wrap as single `Candidate`
2. `evaluate()` → GC content + LinearFold fold (primary) / ViennaRNA fold (fallback) + CAI
3. `score()` → `-mfe + codon_count * log(CAI)` (higher = better)
4. `rank_and_format()` → produces `WorkflowResult`

#### Scoring formula

```python
# total_score = -mfe + codon_count * log(CAI)
# where codon_count = sequence_length // 3
# Raw metrics (GC, MFE) are preserved for display but do NOT affect ranking.
combined_score = -mfe_val + codon_count * math.log(cai_val)
total_score = combined_score
```

#### Required capabilities

```python
required_capabilities = [
    "compute_rna_sequence_gc_content",
    "predict_rna_secondary_structure_with_linearfold",
    "predict_rna_secondary_structure",
    "compute_cai_for_cds_sequence",
]
```

#### Quality review

This workflow uses an empty `QualityProfile` (`MRNA_SEQUENCE_SCORING_QUALITY_PROFILE`).
Reason: deterministic evaluation-only pipeline; retry cannot improve scores for a fixed input sequence.
The unified `QualityAgent` therefore always returns `action="pass"` for this workflow.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `MrnaSequenceScoringInput` dict used

### Synchronization checklist

- `agent_core/workflows/mrna_sequence_scoring.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/agents/quality_agent.py` (QualityReport schema)
- `agent_core/agents/specialist_agent.py` (workflow execution)
- `agent_core/agents/pipeline_agent.py` (pipeline orchestration)
- `agent_core/quality_profiles/mrna_sequence_scoring.py` (quality profile)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- ... (see source lock comment for full list)

---

## 19. Canonical Reference: AgentRunner

> **Locked on**: 2026-07-05
> **Version**: v3.4.0
> **Status**: ✅ Implemented

### v3.4.0 changelog

- **Removed**: The `planner` constructor parameter and the whole `agent_core/planning/` package (`Planner` ABC, `AgentContext`, `LLMPlanner`, `build_planner`). The production path (CLI / FastAPI / `AgentRunner`) never invoked the planner — routing is explicit-only — and the parameter only stored an unused attribute. LLM clients for `QualityAgent` / `SynthesisAgent` are built directly via `agent_core/llm_config.py` (`get_llm_for_provider` / `get_deepseek_llm`). The runner no longer keeps the planner-context leftovers `_available_capabilities` / `_available_workflows` (nothing consumed them).
- **Changed**: `MrnaSequenceScoringWorkflow` is now constructed from `self.capability_registry` (see §18 v1.1.0).

### v3.3.0 changelog

- **Changed**: Renamed constructor parameters and state keys to remove legacy `critic` terminology:
  - `llm_critic_enabled` → `quality_review_enabled`
  - `critic_auto_retry` → `quality_auto_retry`
  - `_llm_critic_enabled` → `_quality_review_enabled`
  - `_critic_auto_retry` → `_quality_auto_retry`
  - `_llm_critic_error` → `_quality_review_error`
  - This is a breaking change; all callers, tests, CLI consumers, and docs must use the new names.
- **Changed**: `CoordinatorAgent` is now a real BMC controller for `full_length_mrna_design` and `rna_aptamer_design`. It detects the BMC-capable workflow interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`) and orchestrates the bounded convergence loop, instead of acting as a facade.

### v3.2.1 changelog

- **Fixed**: `run_form()` and `stream_form()` now correctly copy the previous turn's `workflow_result` to `_previous_workflow_result` and append it to `_workflow_result_history` before clearing the stale result. This restores the cross-turn quality comparison context documented in v3.2.0.

### v3.2.0 changelog

- **Added**: New public method `AgentRunner.run_pipeline(plan: PipelinePlan) -> PipelineResult`. This is the unified execution entry for both single-workflow and multi-workflow pipelines.
- **Changed**: `run_form()` and `stream_form()` now internally build a single-node `PipelinePlan` and delegate to `run_pipeline()`. Their signatures and return types remain unchanged.
- **Added**: `AgentState` now includes `pipeline_result` (JSON-serialized `PipelineResult`) as an additive audit field.
- **Changed**: Internal execution engine switched from `ExecutionController` to `PipelineAgent`.
- **Removed**: Legacy `ExecutionController`, per-workflow `*LLMCritic` classes, and `WORKFLOW_CRITIC_PAIRS` registry. Quality review is now performed by the unified `QualityAgent` using workflow-specific `QualityProfile` instances.

### v3.0.0 changelog

- **Removed**: Natural-language parameter extraction. All deterministic `_extract_*_param_overrides`, `_apply_*_overrides`, sequence pre-extraction, and clarification-loop handling have been deleted.
- **Added**: Form-driven execution entry points `run_form()` and `stream_form()`. Callers must supply an `explicit_workflow` and a `form_params` dict.
- **Changed**: `ExecutionPlan` no longer carries `needs_clarification`, `missing_params`, `extracted_params`, or `clarification_message`.
- **Changed**: `AgentState` adds `_form_params`, `_last_form_params`, and `_last_form_params_by_workflow` for form prefilling; removes `_extracted_sequences`, `_extracted_rna_sequences`, and `_user_supplied_params`.

### Locked contracts

#### Constructor

```python
AgentRunner(
    executor: ToolExecutor,
    *,
    session_memory: Optional[SessionMemory] = None,
    quality_review_enabled: bool = True,
    quality_auto_retry: bool = False,
    persist_run: bool = False,
) -> None
```

- `executor` is positional/required.
- `session_memory` is optional; when `None`, every `.run()` call starts from a fresh state.
- `quality_review_enabled` controls whether the `QualityAgent` invokes its LLM for quality diagnosis.
- `quality_auto_retry` is retained as a configuration name but retry decisions are now made by `SpecialistAgent` based on the `QualityReport` returned by `QualityAgent`.

#### `run_form()` method

```python
AgentRunner.run_form(
    form_params: dict[str, Any],
    *,
    session_id: str,
    explicit_workflow: str,
    user_text: str = "",
    state: Optional[AgentState] = None,
) -> AgentState
```

- `explicit_workflow` is required and selects the workflow to execute.
- `form_params` contains the validated workflow input parameters. Unknown keys are filtered against the workflow input model.
- `user_text` is optional context used only for report generation.

#### `stream_form()` method

```python
AgentRunner.stream_form(
    form_params: dict[str, Any],
    *,
    session_id: str,
    explicit_workflow: str,
    user_text: str = "",
) -> Iterator[dict[str, Any]]
```

- Yields step events as `{node_name: state_dict}` dicts for live progress reporting.

### Default behavior

- `quality_review_enabled=True, quality_auto_retry=False` (advisory mode):
  - `QualityAgent` always records a `QualityReport` in the node result metadata.
  - `SpecialistAgent` retries only on hard failures (workflow `success=False`, empty candidate list, tool error) unless `quality_auto_retry=True`.
  - Soft quality suggestions are surfaced in the report but require user confirmation in the next turn.
- Multi-provider LLM configuration is handled externally via environment variables / `.env`; `AgentRunner` does not accept provider keys directly.
- Cross-turn isolation: at the start of each new turn that contains a workflow step, `AgentRunner` removes any stale `workflow_result` left in session memory from a previous turn. This prevents old candidates (e.g., a full-length GFP design) from polluting a new design task (e.g., a truncated N-terminal redesign).
- Cross-turn quality context: before clearing the stale `workflow_result`, `AgentRunner` copies it to `_previous_workflow_result` and appends it to `_workflow_result_history`. This lets the `QualityAgent` compare current metrics (e.g., CAI) against the previous turn's best candidate, and lets the CLI resolve explicit references to any earlier turn (e.g. "与第一轮对比") instead of only the immediately previous turn.
- Form validation: `_validate_required_params()` raises `ValueError` if a required workflow parameter is missing from `form_params`.
- Cross-turn prefilling: `_last_form_params_by_workflow` stores the most recent form submission per workflow. On subsequent turns the TUI pre-fills the form with these values.
- Parameter source is trustworthy: because parameters come directly from the form, every key in `form_params` is recorded in `_user_explicit_params` and protected from QualityAgent overrides.

### State fields consumed / produced

The returned `AgentState` (a dict) contains both public result fields and underscore-prefixed execution metadata. The following keys are read or written by `AgentRunner` and the CLI (see `agent_core/state.py` for the `TypedDict` declaration):

- Result fields: `workflow_result`, `tool_results`, `final_report`, `retry_count`, `max_retries`, `pipeline_result`
- Routing / planning metadata:
  - `_routing_method`: always `"explicit"` (LLM routing removed in v3.4.0)
  - `_execution_plan`: serialized `PipelinePlan`
  - `_execution_log`: list of step records (legacy, may be empty for pipeline-driven runs)
  - `_plan_executed`: boolean flag (legacy)
- Quality / retry metadata:
  - `_quality_review_enabled`: copy of runner flag
  - `_quality_auto_retry`: copy of runner flag
  - `_diagnosis_history`: list of `QualityReport` snapshots from `QualityAgent`
  - `_quality_review_error`: dict capturing `QualityAgent` LLM API failures
  - `_parameter_overrides`: parameter adjustments suggested by `QualityAgent`
- Multi-turn / form context:
  - `_form_params`: parameters submitted in the current turn
  - `_last_form_params`: parameters submitted in the previous turn (same workflow)
  - `_last_form_params_by_workflow`: dict mapping workflow name → last submitted params
  - `_last_workflow_params`: parameters used by the most recent workflow run
  - `_last_workflow_target`: workflow key from the most recent run
  - `_user_explicit_params`: keys from the current form submission, protected from quality-driven overrides
  - `_previous_workflow_result`: transient copy of the previous turn's `workflow_result`, used by the `QualityAgent` and the CLI report generator for cross-turn comparison
  - `_workflow_result_history`: list of workflow-result snapshots accumulated across turns

`tool_results` is the generic container for tool outputs; tool-specific keys are no longer stored at the top level of state.

### Synchronization checklist

- `agent_core/runner.py` (source of truth)
- `agent_core/agents/pipeline_agent.py` (`PipelineAgent`)
- `agent_core/agents/specialist_agent.py` (`SpecialistAgent`)
- `agent_core/agents/quality_agent.py` (`QualityAgent` and `QualityReport`)
- `agent_core/agents/synthesis_agent.py` (`SynthesisAgent`)
- `agent_core/agents/coordinator_agent.py` (`CoordinatorAgent` for BMC workflows)
- `agent_core/state.py` (`AgentState` schema)
- `agent_core/session_memory.py` (multi-turn persistence)
- `agent_core/form/` (form schema, validation, and rendering)
- `cli/form_chat.py` (CLI entry point)
- `workflow_api/app.py` (API entry point)
- `tests/test_session_memory.py`
- `tests/test_runner_form.py`
- ... (see source lock comment for full list)

---

## 20. Canonical Reference: CLI End-to-End Execution Flow

> **Locked on**: 2026-07-04
> **Version**: v2.3.0
> **Status**: ✅ Implemented

### v2.3.0 changelog

- **Added**: CLI now supports `--pipeline-file PATH` for non-interactive execution of a multi-node `PipelinePlan`. The file must contain a JSON object matching the `PipelinePlan` schema (`plan_id`, `nodes`, `edges`). The CLI starts the union of required microservices and executes the plan via `AgentRunner.run_pipeline()`.
- **Added**: Pipeline artifacts are written as `workspace/sessions/<session_id>/pipeline_results_<hash>.json` and `workspace/sessions/<session_id>/report_<timestamp>_<hash>.md`.

### v2.2.0 changelog

- **Changed**: Underlying execution engine switched from `ExecutionController` to `PipelineAgent` + `SpecialistAgent` + `QualityAgent` + `SynthesisAgent`. Observable CLI behavior remains unchanged.
- **Removed**: Legacy `ExecutionController` and per-workflow Critic references from the CLI flow.

### v2.1.0 changelog

- **Added**: Multi-workflow pipeline support. The CLI/API may accept a `PipelinePlan` (via `--pipeline-file` or a dedicated endpoint) and execute it through the same `PipelineAgent` used by single-workflow forms.
- **Changed**: Single-workflow forms continue to use `AgentRunner.run_form()`; internally they now produce a single-node `PipelinePlan`.
- **Added**: JSON workflow artifact now includes `pipeline_result` as an additive field when available.

### v2.0.0 changelog

- **Removed**: Natural-language input path and clarification loop. The CLI no longer calls `_read_multiline_query()` or processes `needs_clarification`/`missing_params`/`extracted_params`.
- **Added**: Form-driven TUI entry point `cli/form_chat.py`. Each turn renders a structured form based on the workflow's Pydantic input model.
- **Changed**: Non-interactive mode accepts `--params-file PATH` instead of `--single TEXT`.
- **Changed**: Multi-turn state uses `_last_form_params_by_workflow` for per-workflow form prefilling.

This lock covers the entire observable chain from the command-line invocation of `cli/form_chat.py` through microservice orchestration, form rendering, workflow execution, `QualityAgent` diagnosis, report generation, and the final JSON/Markdown artifacts written to `workspace/sessions/<session_id>/`.

### Locked contracts

#### CLI entry flow (`cli/form_chat.py`)

The interactive CLI MUST preserve the following sequence and public behavior:

1. **Resource pre-check** — `resource_checker.check_all()` (GPU ≥ 24 GB, RAM/CPU).
2. **Workflow multi-select** — `_select_workflows()` returns a list of workflow keys.
3. **Microservice orchestration** — `service_orchestrator.ensure_multi_workflow_services_ready(selected_workflows)` health-checks and launches the union of required microservices.
4. **Per-turn workflow selection** — `_select_active_workflow(enabled_workflows)` returns one of the enabled workflow keys (or `None` to exit).
5. **TUI form** — `TuiFormRenderer.render()` displays the workflow's structured form, with basic parameters expanded and advanced tool overrides folded by default. The form is pre-filled from `_last_form_params_by_workflow`.
6. **Form validation** — `FormValidator.validate_with_model()` validates the raw form values against the workflow's Pydantic input model. On failure the form is reshown with error hints.
7. **Non-interactive mode** — `python cli/form_chat.py --workflow NAME --params-file PATH` MUST continue to accept `--workflow` and `--params-file`.
8. **Pipeline non-interactive mode** — `python cli/form_chat.py --pipeline-file PATH` accepts a JSON `PipelinePlan` and executes it via `AgentRunner.run_pipeline()`. It is mutually exclusive with `--workflow` and `--params-file`.
9. **Session ID** — `--session-id <id>` MUST be honored so that multi-turn runs share the same workspace directory.
10. **Pipeline artifacts** — Multi-node pipeline runs write `pipeline_results_<hash>.json` and `report_<timestamp>_<hash>.md` under the session workspace.

#### AgentRunner public API (`agent_core/runner.py`)

Locked signatures (already covered by AgentRunner v3.2.1 lock, restated here because the CLI depends on them):

```python
AgentRunner.run_form(
    form_params: dict[str, Any],
    *,
    session_id: str,
    explicit_workflow: str,
    user_text: str = "",
    state: Optional[AgentState] = None,
) -> AgentState

AgentRunner.stream_form(
    form_params: dict[str, Any],
    *,
    session_id: str,
    explicit_workflow: str,
    user_text: str = "",
) -> Iterator[dict[str, Any]]
```

The `stream_form()` event shape consumed by the CLI MUST remain `{node_name: state_dict}` with nodes `router`, `plan`, `progress`, `tool_execution`, `runner`.

#### State fields consumed / produced in this flow

The CLI and `AgentRunner` read and write the following keys (declared in `agent_core/state.py` unless noted as runtime-only):

- Core result fields: `workflow_result`, `tool_results`, `final_report`, `retry_count`, `max_retries`, `pipeline_result`
- Quality / execution metadata:
  - `_diagnosis_history`: `list[dict[str, Any]]`
  - `_quality_review_enabled`: `bool`
  - `_quality_review_error`: `dict[str, Any]` (optional)
  - `_parameter_overrides`: `dict[str, Any]`
  - `_quality_auto_retry`: `bool` (set by `AgentRunner._prepare_state_form()`)
- Routing / planning metadata:
  - `_routing_method`: `str` (runtime-only, set by `AgentRunner._build_plan()`)
  - `_execution_plan`: serialized `PipelinePlan`
  - `_execution_log`: `list[dict[str, Any]]` (legacy)
  - `_plan_executed`: `bool` (legacy)
- Multi-turn / form context:
  - `_form_params`: `dict[str, Any]` (runtime-only, current turn form values)
  - `_last_form_params`: `dict[str, Any]` (runtime-only, previous turn form values for the same workflow)
  - `_last_form_params_by_workflow`: `dict[str, dict[str, Any]]` (runtime-only, per-workflow form history)
  - `_last_workflow_params`: `dict[str, Any]`
  - `_last_workflow_target`: `str`
  - `_user_explicit_params`: `list[str]` (runtime-only, keys from the current form submission)
  - `_previous_workflow_result`: `Any` (transient copy of previous turn's `workflow_result`)
  - `_workflow_result_history`: `list[Any]` (cross-turn result history)

The CLI writes the following files and MUST keep their naming convention and location:

- `workspace/sessions/<session_id>/workflow_results_<hash>.json`
- `workspace/sessions/<session_id>/report_<timestamp>_<hash>.md`

#### Workflow result artifact contract

Same as v1.0.1. The JSON artifact produced by `_save_workflow_results()` MUST contain at minimum (optional fields are omitted when empty/falsy):

```json
{
  "task_id": "...",
  "success": true,
  "timestamp": "...",
  "session_id": "...",
  "candidate_count": 1,
  "candidates": [...],
  "best_candidate": {...},
  "summary": "...",
  "errors": [...],
  "tool_results": {...},
  "_diagnosis_history": [...],
  "_quality_auto_retry": false,
  "retry_count": 0,
  "_quality_review_error": {...}
}
```

The artifact MAY also contain the additive audit fields from v1.0.1 (`workflow_input`, `trace`, `_bmc_trace`, `_tool_timings`) plus v2.0.0's `_last_form_params`.

The Markdown report produced by `_save_report()` MUST keep the front-matter structure:

```markdown
# RNA Design Agent Report

**Session ID:** <session_id>

**Timestamp:** <timestamp>

---

<report body>
```

### Regression tests

The following tests MUST be updated and re-run after any change to this lock. The PA end-to-end drivers are consolidated in `run_pa_test.py` with benchmark configs in `pa_benchmarks.json`; the driver generates per-turn JSON parameter files and invokes `cli/form_chat.py` non-interactively, replacing the old pexpect/expect natural-language drivers.

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_form_schema_builder.py tests/test_form_validator.py tests/test_tui_form_renderer.py tests/test_runner_form.py tests/test_session_memory.py -v
```

### What CAN be safely changed

- **Cosmetic CLI text**: prompts, banner, emoji, progress spinner formatting.
- **Report content**: changes to the report prompt or default `_format_final_report()` text, as long as the output remains human-readable and references the locked state keys.
- **Additional progress events**: new `progress` event sub-types are safe as long as existing `step_start` / `step_done` / `plan_complete` / `generate_complete` / `evaluate_progress` events continue to be emitted.
- **Adding new workflow options**: extending `_WORKFLOW_LIST` with new workflow numbers is safe; existing numbers 1–11 must not be reassigned.
- **Form UI details**: colors, layout, and control choices within the TUI, as long as the submitted values map to the workflow input model fields.

### What MUST NOT be changed without full retest

- CLI argument names (`--workflow`, `--params-file`, `--session-id`)
- `_select_workflows()` / `_select_active_workflow()` return types
- `AgentRunner.run_form()` and `AgentRunner.stream_form()` signatures
- `stream_form()` event node names and top-level shape
- `AgentState` field names consumed by the CLI (`workflow_result`, `tool_results`, `_diagnosis_history`, `_quality_auto_retry`, `retry_count`, `_form_params`, `_last_form_params_by_workflow`, etc.)
- JSON/Markdown artifact file naming convention or directory layout
- Required keys in `_save_workflow_results()` JSON output

---

## 21. Canonical Reference: Junction-Aware LinearDesign Tool

> **Locked on**: 2026-08-04
> **Status**: registered capability, **not wired into any workflow** (P2 acceptance NO-GO, see `docs/tools/design_mrna_cds_junction_aware_with_lineardesign.md` §7). Depends on the local LinearDesign C++ JUNCTION-PATCH (`docs/change_logs/2026-08-04_lineardesign_junction_patch.md`).

### Tool

- **Tool name**: `design_mrna_cds_junction_aware_with_lineardesign`
- **Endpoint**: `POST http://127.0.0.1:8014/generate/cds_junction_aware`
- **Parameters**: `protein_sequence` (required, via `filepath`/`protein_sequence` in the wrapper), `lambda_value` (float, ge=0.0, default=0.0), `utr5_flank` / `utr3_flank` (Optional[str]; junction-side `flank_nt` nt used, default 21, multiple of 3 and ≥ 3 else 422), `junction_weight` (float, ge=0.0, default=0.0), `junction_window_nt` (int, gt=0, default=20), `flank_nt` (int, default=21), `codon_usage_path` (Optional[str]), `verbose` (bool)
- **Required output fields**: `generated_sequence`, `full_construct_sequence`, `cds_sequence`, `structure`, `mfe` (CKY objective value = thermodynamic MFE + `junction_weight × junction_window_pair_count`), `mfe_thermo`, `cai_score`, `cds_cai`, `junction_window_pair_count`, `utr5_flank`, `utr3_flank`, `junction_weight`, `junction_window_nt`, `flank_nt`, `lambda_value`, `codon_usage_path`, `raw_output`, `stderr`, `model`, `input_filepath`, `output_filepath`

### Behavioral contracts

- Zero-flank calls degenerate to the legacy 4-argument binary invocation and legacy parsing; penalty not applied, `mfe_thermo == mfe`.
- `junction_window_pair_count` window coordinates (full-construct 0-based): W1 = `[max(0, L5−w), L5+w)`, W2 = `[L5+Lcds−w, L5+Lcds+w)` — identical to the C++ penalty windows.
- At `junction_weight == 0` with flanks present, flanks still fold (argc == 8 path): deterministic across identical calls, but NOT byte-identical to the legacy no-flank endpoint.

### Synchronization checklist

- `microservices/lineardesign_service/main.py` :: `LinearDesignJunctionAwareRequest` / `LinearDesignJunctionAwareResponse`
- `agent_core/tools.py` :: `LinearDesignCdsJunctionAwareInput` / `design_mrna_cds_junction_aware_with_lineardesign`
- `agent_core/tool_specs.py` :: `LinearDesignCdsJunctionAwareOutput` + ToolSpec registration
- `agent_core/services/service_manager.py` :: `CAPABILITY_SERVICE_MAP` (8014)
- `docs/tools/design_mrna_cds_junction_aware_with_lineardesign.md`
- `docs/change_logs/2026-08-04_design_mrna_cds_junction_aware_tool_v0.1.0.md`
- `docs/TOOLS.md` §3.1

### Tests that must pass

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x -q
```
