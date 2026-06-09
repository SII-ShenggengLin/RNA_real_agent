# Interface Lock Policy

> **Scope**: the Interface Lock Policy, canonical references for locked tools, and synchronization checklists.

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
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `score_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| CRISOT suite (8 tools) | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | This doc §7 |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `MrnaCdsDesignWorkflow` | v1.0.0 | This doc §8 |
| `RnaSmallMoleculeInteractionWorkflow` | v1.0.0 | This doc §9 |
| `SirnaDesignWorkflow` | v1.0.0 | This doc §10 |
| `SgRnaDesignWorkflow` | v1.0.0 | This doc §11 |
| `AsoTargetScreeningWorkflow` | v1.0.0 | This doc §12 |
| `IresPredictionWorkflow` | v1.0.0 | This doc §13 |
| `FullLengthMrnaDesignWorkflow` | v2.0.0 | This doc §14 |
| `RnaAptamerDesignWorkflow` | v1.0.0 | This doc §15 |
| `RnaSecondaryStructureDesignWorkflow` | v1.0.0 | This doc §16 |
| `RnaTertiaryStructureDesignWorkflow` | v1.0.0 | This doc §17 |

---

## 3. Canonical Reference: GC Content Tool

> **Locked on**: 2026-04-25

### Locked contracts

- **Input schema** (`RnaGcContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaGcContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `g_count`, `c_count`, `gc_count`, `gc_content`, `model`
- **ToolSpec identity**: `compute_rna_sequence_gc_content`
- **Workflow tool name**: `workflow_rna_gc_content`
- **Microservice endpoint**: `POST /gc-content` on port `8020`
- **State storage**: `state["tool_results"]["compute_rna_sequence_gc_content"]` contains keys `gc_content`, `sequence_length`, `gc_count`, `g_count`, `c_count`

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/capabilities/writebacks.py`
- `agent_core/workflow_tools/rna_gc_content_workflow.py`
- `agent_core/workflows/mrna_sequence_scoring.py`
- `agent_core/sequence_utils.py`
- `agent_core/workflow_baseline_eval.py`
- `agent_core/sequence_utils.py`
- `tests/test_rna_gc_content_workflow.py`
- `tests/test_compute_rna_sequence_gc_content.py`

### Tests that must pass

```bash
pytest tests/test_compute_rna_sequence_gc_content.py tests/test_rna_gc_content_workflow.py -v
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
- `agent_core/capabilities/writebacks.py`
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
- `agent_core/capabilities/writebacks.py`
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
- `agent_core/capabilities/writebacks.py`
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
- `agent_core/capabilities/writebacks.py`
- `workflow_api/mrna_handler.py`
- `workflow_api/mrna_schemas.py`
- `tests/test_integration_registry_smoke.py`

---

## 8. Canonical Reference: mRNA CDS Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §2`](WORKFLOWS.md#2).
>
> **Locked on**: 2026-05-10
> **Version**: v1.0.0
> **Status**: ✅ Tested end-to-end (Layers 0–3), all 29 tests passing

### Locked contracts

#### Input model (`MrnaCdsDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `protein_sequence: str` — required
  - `design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"]` — default `"all"`
  - `lambda_value: Optional[float]` — required when `design_tool="lineardesign"`
  - `model_type: Literal[7 RNARL types]` — default `"Homo sapiens mRNA"`
  - `cai_species: str` — default `"Homo sapiens"`
  - `run_fold: bool` — default `True`
  - `run_gc: bool` — default `True`

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

#### Critic configuration (`MRNA_CDS_CRITIC_CONFIG`)

- **evaluation_dimensions**: 8 items covering CAI, MFE, GC, U content, unpaired, RNASTOP, lambda physics, tool diversity
- **adjustable_params**: `design_tool`, `lambda_value`, `model_type`, `cai_species`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### Critic diagnosis output (`CriticDiagnosis`)

- Must match Pydantic schema in `planning/llm_critic.py`
- `action` must be one of: `"retry_with_adjustments"`, `"retry_with_alternative"`, `"proceed_with_filtered"`, `"abort"`
- `parameter_overrides` must only contain keys from `adjustable_params`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing at minimum:
- `_workflow_params`: the exact `MrnaCdsDesignInput` dict used

This is consumed by `ExecutionController._run_step()` (line 291–294).

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/mrna_cds_design.py` (source of truth)
- `agent_core/sequence_utils.py` (scoring formula, `compute_mrna_metric_bundle`)
- `agent_core/workflows/evaluators.py` (`UContentEvaluator`, `CompositeEvaluator`)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (critic registration)
- `agent_core/planning/llm_critic.py` (diagnosis schema)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- `agent_core/tool_specs.py` (if any tool schema changes)
- `agent_core/tools.py` (if any tool implementation changes)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `tests/test_mrna_cds_design_comprehensive.py` (comprehensive test)
- `tests/test_mrna_cds_design_full_stack.py` (existing full-stack test)
- `tests/test_mrna_cds_design_layer3.py` (layer 3 test)
- `tests/test_llm_critic_mrna_cds.py` (critic test)
- `docs/WORKFLOWS.md` §2 (this document)
- `AGENTS.md` (interface lock table)

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_mrna_cds_design_comprehensive.py -v

# Full stack including live LLM Critic
pytest tests/test_mrna_cds_design_comprehensive.py -v --live-llm

# Existing test suites
pytest tests/test_mrna_cds_design_full_stack.py tests/test_mrna_cds_design_layer3.py -v
pytest tests/test_llm_critic_mrna_cds.py -v
```

### What CAN be safely changed

- **Adding new evaluation metrics**: Add to `evaluate()` and `compute_mrna_metric_bundle()`; as long as they don't affect `total_score` formula, existing tests pass.
- **Adding new design tools**: Add to `generate_candidates()` and `required_capabilities`; existing tests that use `design_tool="lineardesign"` are unaffected.
- **Improving summary formatting**: Changes to `rank_and_format()` summary text are cosmetic.
- **Critic hints and evaluation dimensions**: Text changes to `MRNA_CDS_CRITIC_CONFIG.evaluation_dimensions` are safe.

### What MUST NOT be changed without full retest

- Input model field names or types
- Scoring formula (`total_score = -mfe + codon_count * log(CAI)`)
- `required_capabilities` list (removals break the workflow)
- `CriticDiagnosis` schema structure
- `adjustable_params` keys (renaming breaks Critic→Controller parameter override)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_workflow_params` key

---

## 9. Canonical Reference: RNA-Small Molecule Interaction Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §8`](WORKFLOWS.md#8).
>
> **Locked on**: 2026-05-12
> **Version**: v1.0.0
> **Status**: ✅ Tested end-to-end (Layers 0–3), all 29 tests passing

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
]
```

#### No Critic

This workflow intentionally has **no paired Critic** (registered in `registry.py`). Reason: the inputs (RNA + SMILES) are fixed; re-running produces identical results, so retry cannot improve outcomes. This is a design decision, not a temporary omission.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing the internal `_workflow_state` dict, including `tool_results` from both scoring capabilities.

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/rna_small_molecule_interaction.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (no-critic note)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry)
- `agent_core/state.py` (`tool_results["score_rna_ligand_binding_with_rnasmol"]` / `tool_results["score_rna_ligand_binding_with_gernabind"]`)
- `agent_core/capabilities/writebacks.py` (writeback mapping)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- `tests/test_rna_small_molecule_interaction.py` (existing tests)
- `tests/test_rna_small_molecule_interaction_comprehensive.py` (comprehensive test)
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_rna_small_molecule_interaction_comprehensive.py -v

# Full stack including live LLM Planner
pytest tests/test_rna_small_molecule_interaction_comprehensive.py -v --live-llm

# Existing unit/integration tests
pytest tests/test_rna_small_molecule_interaction.py -v
```

### What CAN be safely changed

- **Adding new optional fields** to `RnaSmallMoleculeInteractionInput` (must not break existing dict-based callers)
- **Improving summary formatting** in `rank_and_format()`: changes to summary text are cosmetic
- **Adding new scoring tools**: add to `scoring_tools` Literal and `required_capabilities`; existing tests using `rnasmol`/`gernabind` are unaffected
- **Logging improvements**: changes to `_LOGGER` calls are safe

### What MUST NOT be changed without full retest

- Input model field names or types (especially `rna_sequence`, `smiles`)
- `required_capabilities` list (removals break the workflow)
- Scoring formula (`average(available probability_positive values)`)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or structure
- No-critic design decision (adding a critic requires updating `registry.py` and tests)

---

## 10. Canonical Reference: siRNA Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §4`](WORKFLOWS.md#4).
>
> **Locked on**: 2026-05-13
> **Version**: v1.0.0
> **Status**: Tested end-to-end (Layers 0–3), all 29 tests passing

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

#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → antiviral (Evitar) or generic (sliding window 21-nt)
2. `evaluate()` → GC content + duplex MFE + self-structure + off-target BLAST
3. `score()` → `compute_sirna_rank_scores()` (rank-based, NOT per-candidate formula)
4. `rank_and_format()` → produces `WorkflowResult`

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
    "predict_rna_secondary_structure",   # optional self-structure
    "run_blastn_similarity_search",      # optional off-target scan
]
```

#### Critic configuration (`SIRNA_CRITIC_CONFIG`)

- **evaluation_dimensions**: 5 items covering duplex MFE, off-target count, GC content, homopolymers, Evitar efficiency
- **adjustable_params**: `mode`, `candidate_count`, `maxgc`, `mingc`, `off_target_scan`, `blast_perc_identity`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing at minimum:
- `_workflow_params`: the exact `SirnaDesignInput` dict used
- `_sirna_input`: the parsed input model

This is consumed by `ExecutionController._run_step()` (line 291–294).

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/sirna_design.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (critic registration)
- `agent_core/planning/llm_critic.py` (diagnosis schema)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- `agent_core/tool_specs.py` (if any tool schema changes)
- `agent_core/tools.py` (if any tool implementation changes)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `agent_core/state.py` (`tool_results["design_sirna_with_evitar"]`)
- `tests/test_sirna_design_workflow.py` (existing tests)
- `tests/test_sirna_design_comprehensive.py` (comprehensive test)
- `tests/test_sirna_workflow_api.py` (API tests)
- `tests/test_cli_sirna_entry.py` (CLI tests)
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_sirna_design_comprehensive.py -v -k "not live_llm"

# Full stack including live LLM Critic
pytest tests/test_sirna_design_comprehensive.py -v --live-llm

# Existing test suites
pytest tests/test_sirna_design_workflow.py tests/test_sirna_workflow_api.py tests/test_cli_sirna_entry.py -v
```

### What CAN be safely changed

- **Adding new evaluation metrics**: Add to `evaluate()`; as long as they don't affect `total_rank` ranking, existing tests pass.
- **Adding new design tools**: Add to `generate_candidates()` and `required_capabilities`; existing tests using generic mode are unaffected.
- **Improving summary formatting**: Changes to `rank_and_format()` summary text are cosmetic.
- **Critic hints and evaluation dimensions**: Text changes to `SIRNA_CRITIC_CONFIG.evaluation_dimensions` are safe.

### What MUST NOT be changed without full retest

- Input model field names or types
- `compute_sirna_rank_scores()` ranking logic or score keys (`rank_mfe`, `rank_offtarget`, `total_rank`)
- `required_capabilities` list (removals break the workflow)
- `CriticDiagnosis` schema structure
- `adjustable_params` keys (renaming breaks Critic→Controller parameter override)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_workflow_params` / `_sirna_input` keys

---

## 11. Canonical Reference: sgRNA Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §5`](WORKFLOWS.md#5).
>
> **Locked on**: 2026-05-13
> **Version**: v1.0.0
> **Status**: Tested end-to-end (Layers 0–3), all 40 tests passing

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

#### Critic configuration (`SGRNA_CRITIC_CONFIG`)

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

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/sgrna_design.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (critic registration)
- `agent_core/planning/llm_critic.py` (diagnosis schema)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `agent_core/state.py` (`tool_results["design_sgrna_handle_with_crgpt"]`)
- `microservices/sgrna_design_service/main.py` (microservice)
- `microservices/crisot_service/main.py` (microservice)
- `tests/test_sgrna_design_workflow.py` (existing tests)
- `tests/test_sgrna_design_e2e.py` (end-to-end Layer 0–3 tests)
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Existing unit/integration tests (stubs, no LLM required)
pytest tests/test_sgrna_design_workflow.py -v

# End-to-end tests with real microservices (Layers 0–2)
pytest tests/test_sgrna_design_e2e.py::TestLayer0DirectToolInvocation -v
pytest tests/test_sgrna_design_e2e.py::TestLayer1Capability -v
pytest tests/test_sgrna_design_e2e.py::TestLayer2Workflow -v

# Layer 3 tests with live DeepSeek API
pytest tests/test_sgrna_design_e2e.py::TestLayer3PlanningAndControl -v
```

### What CAN be safely changed

- **Adding new evaluation metrics**: Add to `evaluate()`; as long as they don't affect `score_sgrna_candidate()` formula, existing tests pass.
- **Improving summary formatting**: Changes to `rank_and_format()` summary text are cosmetic.
- **Critic hints and evaluation dimensions**: Text changes to `SGRNA_CRITIC_CONFIG.evaluation_dimensions` are safe.
- **Logging improvements**: Changes to `_LOGGER` calls are safe.
- **Service-side optimizations**: Changes to `microservices/sgrna_design_service/main.py` that don't affect the HTTP API contract are safe.

### What MUST NOT be changed without full retest

- Input model field names or types
- `score_sgrna_candidate()` scoring formula
- `required_capabilities` list (removals break the workflow)
- `CriticDiagnosis` schema structure
- `adjustable_params` keys (renaming breaks Critic→Controller parameter override)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_workflow_params` / `_sgrna_input` keys

---

## 12. Canonical Reference: ASO Target Screening Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §11`](WORKFLOWS.md#11).
>
> **Locked on**: 2026-05-14
> **Version**: v1.0.0
> **Status**: Tested end-to-end (Layers 0–3), all 36 tests passing

### Locked contracts

#### Input model (`AsoScreeningInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `target_mrna_filepath: str` — required; path to target mRNA FASTA/plain file
  - `aso_length: int` — default `18`, range `[10, 50]`
  - `window_step: int` — default `1`, range `[1, 10]`
  - `top_n_windows: int` — default `10`, range `[1, 100]`
  - `binding_evaluation_tool: Literal["rnaup", "rnacofold"]` — default `"rnaup"`

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

#### No Critic

This workflow intentionally has **no paired Critic** in `WORKFLOW_CRITIC_PAIRS` (`registry.py`).
Reason: ASO screening is a deterministic evaluation-only pipeline; the same input always
yields the same accessibility profile and binding energies. Retry would only waste compute.

The `AsoScreeningCritic` class is an empty interface (`should_retry` always returns `False`).

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_aso_input`: the parsed `AsoScreeningInput` model
- `target_filepath`: path to saved normalized target sequence
- `target_sequence`: normalized RNA sequence string
- `profile_tsv`: path to RNAplfold TSV profile

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/aso_target_screening.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (no-critic note)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `agent_core/state.py` (`tool_results["compute_aso_target_accessibility_vienna"]`)
- `agent_core/sequence_utils.py` (normalize_rna_sequence, _pick_float)
- `tests/test_aso_target_screening.py` (existing stub tests)
- `tests/test_aso_target_screening_comprehensive.py` (comprehensive Layer 0–3 test)
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_aso_target_screening.py -v
pytest tests/test_aso_target_screening_comprehensive.py -v

# Full stack including live LLM Critic and E2E retry
pytest tests/test_aso_target_screening_comprehensive.py -v --live-llm
```

### What CAN be safely changed

- **Adding new evaluation metrics**: Add to `evaluate()`; as long as they don't affect rank-based scoring, existing tests pass.
- **Improving summary formatting**: Changes to `rank_and_format()` summary text are cosmetic.
- **Logging improvements**: Changes to `_LOGGER` calls are safe.
- **Critic interface changes**: `AsoScreeningCritic` is an empty placeholder; cosmetic changes are safe.

### What MUST NOT be changed without full retest

- Input model field names or types
- Rank-based scoring logic (`accessibility_rank`, `binding_rank`, `sum_rank`, `composite_score`)
- `required_capabilities` list (removals break the workflow)
- `AsoScreeningInput` default values (they are carefully tuned for general-use ASO screening)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_aso_input` / `target_filepath` / `target_sequence` keys

---

## 13. Canonical Reference: IRES Prediction & Validation Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §10`](WORKFLOWS.md#10).
>
> **Locked on**: 2026-05-14
> **Version**: v1.0.0
> **Status**: Tested end-to-end (Layers 0–3), all 45 tests passing

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

#### Pipeline stages (must NOT change execution order or skip stages silently)

1. `generate_candidates()` → IRESfinder prediction → merge overlapping windows → extract subsequence → build `Candidate` list
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

Structural metrics (`mfe_kcal_per_mol`, `mean_unpaired_fraction`, `mean_unpaired_prob_1nt`) are stored in `metrics_bundle` for LLM Critic review and user inspection, but they do NOT affect the numeric score due to lack of calibrated evidence for an optimal unpaired-fraction target.

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
    "predict_rna_secondary_structure",
    "predict_rna_local_accessibility_profile_vienna",
    "compute_dot_bracket_unpaired_fraction",
]
```

#### Critic configuration (`IRES_PREDICTION_CRITIC_CONFIG`)

- **evaluation_dimensions**: 5 items covering IRES probability, structural validation, unpaired fraction balance, coverage distribution, user constraints
- **adjustable_params**: `probability_threshold`, `window_size`, `step_size`, `top_n_candidates`, `run_structural_validation`, `iresfinder_mode`
- **retry_strategy**: `"adjust_params"`
- **max_retries**: `2`

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `IresPredictionInput` dict used
- `_last_workflow_params`: same as above (for Critic reference)
- Internal `tool_results` from IRESfinder and ViennaRNA tools

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/ires_prediction.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (critic registration in `WORKFLOW_CRITIC_PAIRS`)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/planning/llm_critic.py` (diagnosis schema)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `agent_core/state.py` (`tool_results["predict_putative_ires_with_iresfinder"]`)
- `microservices/iresfinder_service/main.py` (microservice contract)
- `tests/test_ires_prediction.py` (existing tests)
- `tests/test_ires_prediction_comprehensive.py` (comprehensive Layer 0–3 test)
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Layers 0–2 (no LLM required)
pytest tests/test_ires_prediction_comprehensive.py -v -k "not Layer3"

# Full stack including live LLM Critic and retry
pytest tests/test_ires_prediction_comprehensive.py::TestLayer3LLMCritic -v
pytest tests/test_ires_prediction_comprehensive.py::TestLayer3ExecutionControllerRetry -v

# Existing test suite
pytest tests/test_ires_prediction.py -v
```

### What CAN be safely changed

- **Adding new evaluation metrics** to `evaluate()`: as long as they are stored in `metrics_bundle` and don't affect the scoring formula, existing tests pass.
- **Improving summary formatting** in `rank_and_format()`: changes to summary text are cosmetic.
- **Critic hints and evaluation dimensions**: Text changes to `IRES_PREDICTION_CRITIC_CONFIG.evaluation_dimensions` are safe.
- **Adding new IRESfinder modes**: If IRESfinder service adds new modes, extend `iresfinder_mode` enum values and `IresPredictionInput` validator.

### What MUST NOT be changed without full retest

- Input model field names or types
- Scoring formula (`composite_score = ires_probability`)
- Confidence assignment thresholds
- `required_capabilities` list (removals break the workflow)
- `adjustable_params` keys (renaming breaks Critic→Controller parameter override)
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_workflow_params` / `_last_workflow_params` keys


---

## 14. Canonical Reference: Full-Length mRNA Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §3`](WORKFLOWS.md#3).
>
> **Locked on**: 2026-05-24
> **Version**: v2.0.0 (BMC edition)
> **Status**: Core BMC logic implemented; e2e tests with live microservices pending

### v2.0.0 changelog

- **Added**: `Bounded Multi-Module Coordination (BMC)` — deterministic, rule-based coordinator for inter-module conflict diagnosis and iterative refinement.
- **Added**: `JunctionEvaluator` — evaluates 5'UTR–CDS and CDS–3'UTR junction MFE and GC continuity.
- **Added**: `FullLengthBMCScoringFunction` — weighted scoring with junction-aware penalty terms.
- **Added**: `FullLengthCoordinator` — deterministic rule engine (not LLM) for auditable conflict diagnosis.
- **Added**: `UContentEvaluator` — evaluates U content for both CDS (via `MrnaCdsDesignWorkflow` sub-evaluator) and full-length sequence.
- **Restored**: `UTR5MrlEvaluator` and `UTR3StabilityEvaluator` real invocation (previously hard-coded to empty dict in benchmark mode). Both evaluators now call `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna` respectively.
- **Modified**: `run()` method — now executes three phases (generate → evaluate/rank → bounded iterative coordination).
- **Modified**: `rank_and_format()` — automatically detects BMC mode via presence of `junction_score` key and sorts by `total_score` (descending) instead of Borda-count `total_rank`.

### Locked contracts

#### Input model (`FullLengthMrnaDesignInput`)

Unchanged from v1.0.0:
- `protein_sequence: str` — required
- `design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"]` — default `"all"`
- `lambda_value: Optional[float]` — required when `design_tool="lineardesign"`
- `model_type: str` — default `"Homo sapiens mRNA"`
- `cai_species: str` — default `"Homo sapiens"`
- `utr_mode: Literal["short", "medium", "long", "all"]` — default `"all"`
- `run_fold: bool` — default `True`
- `run_gc: bool` — default `True`

#### `required_capabilities` (v2.0.0)

```python
required_capabilities = [
    "design_5utr_with_gemorna",               # port 8004
    "design_3utr_with_gemorna",               # port 8004
    "predict_5utr_mrl_with_gemorna",          # port 8004
    "predict_3utr_stability_with_gemorna",    # port 8004
    "predict_rna_secondary_structure",        # port 8003 (ViennaRNA)
    "predict_rna_secondary_structure_with_linearfold",  # port 8015
    "predict_putative_ires_with_iresfinder",  # port 8013
    "predict_mrna_stability_with_rnastop",    # port 8009
    "compute_rna_sequence_u_content",         # port 8020
]
```

> **Note**: `predict_putative_ires_with_iresfinder` and `predict_mrna_stability_with_rnastop` are registered in `required_capabilities` but may be skipped in certain execution paths (e.g. benchmark timeout guards). `predict_5utr_mrl_with_gemorna` and `predict_3utr_stability_with_gemorna` are **always invoked** via their respective evaluators as of 2026-06-09.

#### Pipeline stages (v2.0.0)

1. `generate_candidates()` → CDS via `MrnaCdsDesignWorkflow` + UTR combinations
2. `evaluate()` → full-length fold + **5'UTR MRL (`predict_5utr_mrl_with_gemorna`)** + **3'UTR stability (`predict_3utr_stability_with_gemorna`)** + junction metrics + CDS U content + full-length U content
3. `score()` → classic Borda-count **OR** BMC `FullLengthBMCScoringFunction` (auto-detected)
4. `rank_and_format()` → Borda-rank **OR** BMC `total_score` descending
5. **BMC Phase** (NEW, bounded):
   - `FullLengthCoordinator.diagnose(best.metrics)` → list of `Issue`
   - If issues found → `broadcast_feedback()` → `_regenerate_modules()` → re-evaluate → re-rank
   - Hard bounds: max 3 rounds; early stop on degradation or insufficient improvement

#### BMC Coordinator thresholds (deterministic, auditable)

| Issue type | Threshold | Affected modules | Parameter action |
|------------|-----------|------------------|------------------|
| `FULL_MFE_TOO_HIGH` | MFE/nt > −0.25 kcal/mol/nt | 5UTR, CDS, 3UTR | **Decrease** λ by 2 |
| `FULL_STRUCTURE_TOO_LOOSE` | paired fraction < 0.65 | 5UTR, CDS, 3UTR | **Decrease** λ by 2 |
| `JUNCTION_5UTR_CDS_TOO_STABLE` | junction MFE < −20 | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_5UTR_CDS_AUG_BURIED` | AUG start codon paired | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_5UTR_CDS_KOZAK_BURIED` | Kozak region paired | 5UTR, CDS | **Explore 5'UTR presets**; **shuffle N-terminus codons** |
| `JUNCTION_CDS_3UTR_UNSTABLE` | junction MFE > −15 | CDS, 3UTR | **Explore 3'UTR presets**; **shuffle C-terminus codons** |
| `JUNCTION_CDS_3UTR_GC_MISMATCH` | GC diff > 0.15 | CDS, 3UTR | **Diagnostic only** (recorded in BMC trace) |
| `JUNCTION_5UTR_CDS_GC_MISMATCH` | GC diff > 0.15 | 5UTR, CDS | **Diagnostic only** (recorded in BMC trace) |

**Physics note**: LinearDesign λ is inversely related to MFE stability — **lower λ → more negative MFE** (more stable). λ adjustments are triggered **only** by global issues (`FULL_MFE_TOO_HIGH`, `FULL_STRUCTURE_TOO_LOOSE`). Pure junction issues do **not** adjust λ, because λ is a global CDS parameter and its effect on a 40-nt junction (only 20 nt from the CDS side) is heavily diluted.

**Length-normalization note**: Absolute MFE is proportional to sequence length (Zhang et al., Nature 2023). The Coordinator uses `MFE / total_length` (kcal/mol/nt) and `paired_fraction` (from the dot-bracket structure produced by the fold tool — LinearFold primary, ViennaRNA fallback) instead of fixed absolute thresholds, ensuring fairness across targets of different lengths.

**Junction local-control note**: For pure junction issues, `_regenerate_modules()` fuses two local strategies: (1) **UTR preset exploration** (changes the UTR side of the junction), and (2) **junction codon shuffling** via `shuffle_cds_junction_codons` (synonymous substitution at the CDS terminus, 6 codons / up to 4 variants, changing the CDS side directly). When no λ adjustment is needed, the current best CDS is reused instead of re-generated, avoiding wasted computation.

**Tool-switch note**: If `design_tool="all"` and a global issue triggers a λ adjustment, `_adjust_input_from_feedback()` automatically switches `design_tool` to `"lineardesign"` so the λ change takes effect (the fixed λ grid for `"all"` would otherwise ignore the adjustment).

#### Scoring formulas

**Classic mode** (no junction metrics present):
```python
cds_rank  = rank_by(candidates, key="cds_component",  descending=True)
utr5_rank = rank_by(candidates, key="utr5_mrl",       descending=True)
utr3_rank = rank_by(candidates, key="utr3_stability", descending=True)
total_rank = cds_rank + utr5_rank + utr3_rank
total_score = -total_rank
```

**BMC mode** (junction metrics present):
```python
total_score = 0.25 * cds_component
            + 0.15 * utr5_mrl
            + 0.15 * utr3_stability
            + 0.20 * (-full_length_mfe)
            + 0.25 * junction_score

junction_score = Σ(-junction_mfe) - 5.0 * Σ(junction_gc_diff)
```

#### State writeback additions (v2.0.0)

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `FullLengthMrnaDesignInput` dict used
- `_bmc_trace`: list of `CoordinationRound` dicts recording each iteration's issues, feedback, modules reinvoked, and timing

### Synchronization checklist

If you change any locked contract, update **all** of these and re-run tests:

- `agent_core/workflows/full_length_mrna_design.py` (source of truth)
- `agent_core/workflows/coordinator.py` (BMC coordinator)
- `agent_core/workflows/evaluators.py` (JunctionEvaluator, UContentEvaluator)
- `agent_core/workflows/scoring.py` (FullLengthBMCScoringFunction)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/registry.py` (critic registration)
- `agent_core/workflows/mrna_cds_design.py` (CDS sub-workflow)
- `agent_core/planning/llm_critic.py` (diagnosis schema)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/runner.py` (AgentRunner, state writeback consumption)
- `agent_core/tool_specs.py` (if any tool schema changes)
- `agent_core/tools.py` (if any tool implementation changes)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `tests/test_full_length_mrna_design.py`
- `tests/test_full_length_mrna_design_layer3.py`
- `tests/test_full_length_mrna_design_comprehensive.py`
- `tests/test_bmc_full_length_mrna.py`
- `tests/test_bmc_workflow_e2e_mock.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

### Tests that must pass

```bash
# Core unit tests (no microservices)
pytest tests/test_full_length_mrna_design.py tests/test_bmc_full_length_mrna.py -v

# Layer 3 tests
pytest tests/test_full_length_mrna_design_layer3.py -v

# E2E mock tests
pytest tests/test_bmc_workflow_e2e_mock.py -v

# Comprehensive tests (requires live microservices)
pytest tests/test_full_length_mrna_design_comprehensive.py -v
```

### What CAN be safely changed

- **Coordinator thresholds**: Adjusting `THRESHOLDS` dict values in `coordinator.py` is safe as long as tests are updated.
- **BMC scoring weights**: Changing `FullLengthBMCScoringFunction.weights` is safe.
- **JunctionEvaluator overlap length**: Changing the 20-nt overlap window is safe.
- **BMC bounds**: Changing `max_rounds` or `improvement_threshold` is safe.
- **Critic hints**: Text changes to `FULL_LENGTH_MRNA_CRITIC_CONFIG.evaluation_dimensions` are safe.

### What MUST NOT be changed without full retest

- Input model field names or types
- `required_capabilities` list (removals break the workflow)
- Classic Borda-count ranking logic (`cds_component`, `utr5_mrl`, `utr3_stability`, `total_rank`)
- `CriticDiagnosis` schema structure
- `adjustable_params` keys
- Pipeline execution order (generate → evaluate → score → rank)
- `_state_writeback` attribute name or its `_workflow_params` / `_bmc_trace` keys


---

## 15. Canonical Reference: RNA Aptamer Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §9`](WORKFLOWS.md#9).
>
> **Locked on**: 2026-05-28
> **Version**: v1.0.0
> **Status**: ✅ Implemented with BMC Type-II Coordinator

### Locked contracts

#### Input model (`RnaAptamerDesignInput`)

- **Fields** (must NOT be renamed, removed, or have their type narrowed):
  - `protein_structure_filepath: str` — required (PDB or mmCIF)
  - `protein_chain_id: str` — default `"A"`
  - `hotspot_window_size: int` — default `5`
  - `aptamer_length: int` — default `30`
  - `n_samples: int` — default `10`
  - `seed: int` — default `42`
  - `run_rhofold: bool` — default `True`
  - `run_proteinx: bool` — default `True`
  - `run_egarps: bool` — default `True`

#### Pipeline stages

1. `identify_protein_binding_hotspots()` — hotspot residue identification
2. `build_odesign_aptamer_input_json()` — ODesign input preparation
3. `run_odesign_inference()` — aptamer sequence generation (port 8012)
4. `evaluate()` — per candidate:
   - RhoFold 3D structure prediction (port 8005)
   - ProteinX RNA-protein complex prediction (port 8022)
   - EGARPS complex scoring (port 8023)
   - Interface analysis (pure Python)
5. `score()` — aggregated scoring function
6. `AptamerCoordinator.diagnose()` — BMC Type-II deterministic evaluation

#### Scoring formula

```python
total_score = egarps_native_probability + (rhofold_mean_plddt / 100) + proteinx_ipTM
```

#### BMC Type-II Coordinator thresholds

| Metric | Threshold |
|--------|-----------|
| `egarps_native_probability` | ≥ 0.30 |
| `rhofold_mean_plddt` | ≥ 70.0 |
| `proteinx_ipTM` | ≥ 0.60 |
| `interface_contacts` | ≥ 5 |
| `buried_sasa` | ≥ 500.0 Å² |
| `gc_content` | [0.30, 0.70] |

#### Two-tier Critic

- **AptamerCoordinator** (workflow-internal): deterministic rule engine for hard-threshold conflicts
- **RnaAptamerDesignLLMCritic** (ExecutionController-level): LLM-driven for user-intent alignment

### Synchronization checklist

- `agent_core/workflows/rna_aptamer_design.py`
- `agent_core/workflows/coordinator.py`
- `agent_core/workflows/registry.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `tests/test_rna_aptamer_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`

---

## 16. Canonical Reference: RNA Secondary Structure Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §6`](WORKFLOWS.md#6).
>
> **Locked on**: 2026-05-20
> **Version**: v1.0.0
> **Status**: ✅ Implemented

### Locked contracts

#### Input model (`RnaSecondaryStructureDesignInput`)

- `target_structure: str` — required, dot-bracket notation
- `start_sequence: Optional[str]` — optional hint sequence
- `repeats: int` — default `5`
- `num_invocations: int` — default `3`

#### Pipeline stages

1. `inverse_fold_rna_secondary_structure_vienna()` — ViennaRNA RNAinverse (port 8003)
2. Deduplication
3. `evaluate()` — GC content + RNAfold validation + structure Hamming distance
4. `score()` — `structure_component = 1 - structure_distance / sequence_length`

#### Critic strategy

- Retry trigger: no candidates, or all `structure_distance / length > 0.02`
- Retry limit: 3 total runs
- Retry actions: increase `repeats`, increase `num_invocations`

### Synchronization checklist

- `agent_core/workflows/rna_secondary_structure_design.py`
- `agent_core/workflows/registry.py`
- `tests/test_rna_secondary_structure_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`

---

## 17. Canonical Reference: RNA Tertiary Structure Design Workflow

> For full pipeline, scoring details, and critic strategy, see [`WORKFLOWS.md §7`](WORKFLOWS.md#7).
>
> **Locked on**: 2026-05-20
> **Version**: v1.0.0
> **Status**: ✅ Implemented

### Locked contracts

#### Input model (`RnaTertiaryStructureDesignInput`)

- `pdb_filepath: str` — required
- `design_tools: list[Literal["rhodesign", "ribodiffusion"]]` — default `["rhodesign", "ribodiffusion"]`
- `n_samples_per_tool: int` — default `3`

#### Pipeline stages

1. Candidate generation:
   - `design_rna_sequence_with_rhodesign()` (port 8006)
   - `design_rna_inverse_fold_with_ribodiffusion()` (port 8021)
2. Deduplication across both tools
3. `evaluate()` — GC + MFE + RhoFold pLDDT + RMSD/TM-score
4. `score()` — `0.5 * (pLDDT/100) + 0.5 * max(0, 1 - RMSD/5.0)`

#### Critic strategy

- Retry trigger: all candidates pLDDT < 70, or candidate count < 2, or all GC outside [0.25, 0.75]
- Retry limit: 3 total runs
- Retry actions: increase `n_samples`, adjust temperature, filter GC outliers

### Synchronization checklist

- `agent_core/workflows/rna_tertiary_structure_design.py`
- `agent_core/workflows/registry.py`
- `tests/test_rna_tertiary_structure_design.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`

---

## 18. Canonical Reference: mRNA Sequence Scoring Workflow

> **Locked on**: 2026-05-15
> **Version**: v1.0.0
> **Status**: ✅ Implemented

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

#### No Critic

This workflow intentionally has **no paired Critic**.
Reason: deterministic evaluation-only pipeline; retry cannot improve scores for a fixed input sequence.

#### State writeback

Workflow result MUST include `_state_writeback` attribute containing:
- `_workflow_params`: the exact `MrnaSequenceScoringInput` dict used

### Synchronization checklist

- `agent_core/workflows/mrna_sequence_scoring.py` (source of truth)
- `agent_core/workflows/base.py` (pipeline interface)
- `agent_core/workflows/__init__.py` (exports)
- `agent_core/workflows/registry.py` (no-critic note)
- `agent_core/runner.py` (workflow_registry entry)
- `agent_core/planning/base.py` (ExecutionController)
- `agent_core/tool_specs.py` (tool schemas)
- `agent_core/tools.py` (tool wrappers)
- `agent_core/capabilities/writebacks.py` (if state field names change)
- `agent_core/workflow_models.py` (Candidate, WorkflowResult)
- `agent_core/state.py` (`tool_results` keys)
- `agent_core/sequence_utils.py` (scoring helpers)
- `tests/test_mrna_sequence_scoring_comprehensive.py`
- `tests/test_mrna_sequence_scoring_layer3.py`
- `docs/INTERFACE_LOCKS.md` (this document)
- `docs/WORKFLOWS.md`
- `AGENTS.md`
