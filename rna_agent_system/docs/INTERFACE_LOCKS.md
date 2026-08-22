# Interface Lock Policy

> **Scope**: the Interface Lock Policy, the locked-interface table, and per-lock essentials.  
> **Last updated**: 2026-08-18 (post-simplification state; BMC locks and the
> junction-tool lock §21 were removed with their code)

---

## 1. Policy

This project uses **INTERFACE LOCK** comments to prevent accidental breaking
changes to tool contracts. When you see a block like this:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# <Tool name> INTERFACE LOCK (vX.Y.Z) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
```

**Do NOT modify any function signature, Pydantic field, return dict key, or
state field** inside that lock without updating **all** files listed in the
lock comment (the authoritative sync list lives in the source file's lock
header) and re-running the full test suite:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x -q
```

---

## 2. Currently Locked Interfaces

| Tool / Module | Version | Lock anchor |
|---------------|---------|--------------|
| `compute_rna_sequence_gc_content` | v0.1.0 | `agent_core/tools.py` + `sequence_utils.py` |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `agent_core/tools.py` + `sequence_utils.py` |
| `compute_rna_sequence_u_content` | v0.1.0 | `agent_core/tools.py` + `sequence_utils.py` |
| `compute_cai_for_cds_sequence` | v0.1.0 | `agent_core/tools.py` |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| `run_bowtie2_short_alignment` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `tool_specs.py` |
| `score_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `tool_specs.py` |
| `score_crispr_off_target_with_crisot` | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| `calculate_crispr_specificity_with_crisot` | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `tool_specs.py` |
| LinearFold suite (`/fold`) | v0.2.0 | `agent_core/tools.py` + `tool_specs.py` |
| `predict_5utr_mrl_with_gemorna` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `predict_3utr_stability_with_gemorna` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `identify_protein_binding_hotspots` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `analyze_rna_protein_interface` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `score_structure_alignment` | v0.1.0 | `agent_core/tools.py` + `tool_specs.py` |
| `MrnaCdsDesignWorkflow` | v1.2.0 | `workflows/mrna_cds_design.py` lock header |
| `RnaSmallMoleculeInteractionWorkflow` | v1.1.0 | `workflows/rna_small_molecule_interaction.py` |
| `SirnaDesignWorkflow` | v1.3.1 | `workflows/sirna_design.py` |
| `SgRnaDesignWorkflow` | v1.3.1 | `workflows/sgrna_design.py` |
| `AsoTargetScreeningWorkflow` | v1.1.0 | `workflows/aso_target_screening.py` |
| `IresPredictionWorkflow` | v1.1.0 | `workflows/ires_prediction.py` |
| `FullLengthMrnaDesignWorkflow` | v3.1.0 | `workflows/full_length_mrna_design.py` |
| `RnaAptamerDesignWorkflow` | v2.1.0 | `workflows/rna_aptamer_design.py` |
| `RnaSecondaryStructureDesignWorkflow` | v1.0.0 | `workflows/rna_secondary_structure_design.py` |
| `RnaTertiaryStructureDesignWorkflow` | v1.2.1 | `workflows/rna_tertiary_structure_design.py` |
| `MrnaSequenceScoringWorkflow` | v1.1.0 | `workflows/mrna_sequence_scoring.py` |
| `AgentRunner` | v3.4.0 | `agent_core/runner.py` |
| `CLI End-to-End Execution Flow` | v2.4.0 | `cli/form_chat.py` |

Removed locks (2026-08-18, deleted with their code): the junction-aware
LinearDesign tool (§21, P2 NO-GO), `shuffle_cds_junction_codons`, and the six
reserved CRISOT wrappers.

---

## 3. Workflow lock essentials

Common contract for every workflow lock (details in each source file's lock
header and [`WORKFLOWS.md`](WORKFLOWS.md)):

- **Input model**: the workflow's Pydantic input model (one `{tool_alias}_{param}`
  override field per tool parameter, from the frozen parameter analysis). Field
  names, types, and defaults must not be renamed/removed/narrowed.
- **Pipeline order**: `generate_candidates()` → `evaluate()` → `score()` →
  `rank_and_format()`; execution order must not change silently.
- **State writeback**: the workflow result carries `_state_writeback` with at
  minimum `_workflow_params` (the exact input dict used) — consumed by
  `AgentRunner` for cross-turn prefilling and audit.
- **Required capabilities**: the class-level `required_capabilities` list drives
  service pre-flight (L3); entries must not be dropped casually.
- **Scoring**: each workflow's scoring function is locked with its formula
  documented in [`WORKFLOWS.md`](WORKFLOWS.md) (e.g. mRNA CDS:
  `total_score = -mfe + codon_count * log(CAI)`).

### Notable per-workflow specifics

- **`MrnaCdsDesignWorkflow` (§8)**: `truncate_n_terminal` /
  `truncate_c_terminal` are mutually exclusive; species/model enums come from
  `agent_core/constants/species.py`.
- **`SirnaDesignWorkflow` (§10, v1.3.0)**: antiviral mode (Evitar) vs generic mode
  (sliding window); off-target via BLAST+ and Bowtie2; `bowtie2_i` /
  `bowtie2_ma` upstream-only fields are strings (`'mode-dependent'`).
  Ranking is ASF reference-point over `efficiency_component` /
  `specificity_component` / `asymmetry_component` (terminal 5-bp NN end
  asymmetry via `compute_sirna_duplex_binding_vienna` v0.5.0; absent on
  older services → dimension drops pool-wide); the full passing pool is
  ranked before truncating to `candidate_count`; Borda `rank_*` /
  `total_rank` keys remain as reported diagnostics. 2026-08-21 ranking
  governance (DECISIONS (p)): no siRNA objective is oracle-backed, so
  assembly is a structural no-op that only adds the additive
  `_state_writeback["_ranking_governance"]` field.
- **`SgRnaDesignWorkflow` (§11, v1.3.0)**: optional `off_target_sequences`
  input + `CRISOTSpecificityEvaluator` + `crisot_specificity_component`
  (default-off, PA-safe). Ranking is ASF reference-point over the component
  dimensions with `weight_nn_score` / `weight_crisot` /
  `weight_crisot_specificity` renormalized as ASF weights (2026-08-20);
  `total_score` remains a reported diagnostic. 2026-08-21 ranking governance
  (DECISIONS (p)): nn/crisot are pending-governance oracles (kept +
  `pending` flag, DECISIONS (l)); `crisot_specificity_component` is aggregate
  compute and never gated; additive `_state_writeback["_ranking_governance"]`.
- **`RnaTertiaryStructureDesignWorkflow` (§12, v1.2.0)**: ranking is ASF
  reference-point over `rhofold_component` / `rmsd_component` /
  `tm_component` (TM injected at ranking time from the alignment TM-score)
  with `weight_rhofold` / `weight_rmsd` / `weight_tm_score` (new additive
  field, default 0.5) renormalized as ASF weights (2026-08-20); the previous
  0.5/0.5 blend survives only as the reported `total_score` diagnostic.
  Without a reference structure both closeness dimensions drop pool-wide.
  Audit guidance: lower `weight_rhofold` below the closeness weights when a
  reference structure exists (see WORKFLOWS.md §8 weight guidance). 2026-08-21
  ranking governance (DECISIONS (p)): `rhofold_component` is unprofiled under
  this task key (DECISIONS (k)) — kept + `unprofiled` flag, no inheritance of
  the E1 aptamer failure; additive `_state_writeback["_ranking_governance"]`.
- **`IresPredictionWorkflow` (§13)**: mode 0/1/2 semantics locked to upstream
  IRESfinder; PA_023's negative round-3 outcome (max_score 0.4986 < 0.5
  threshold) is an expected third-party model limitation, not a bug.
- **`FullLengthMrnaDesignWorkflow` (§14, v3.1.0)**: plain
  generate→evaluate→ASF/Pareto-rank run (BMC interface removed 2026-08-18).
  `reference_point` user-facing keys: `utr5_mrl`, `utr3_stability`,
  `full_mfe_score`; CDS objectives via `target_cds_mfe` + `target_cds_cai`
  (synthesized into the internal `cds_component`). Junction ddG
  (`junction_5utr_cds_ddg_open_w1/w2`) is a report-only metric. Junction
  scores are internal diagnostics, never user-facing ranking keys. Since
  2026-08-20 the ASF ranking runs on the shared
  `apply_reference_point_ranking` layer: per-candidate missing dimensions
  impute at pool-worst, pool-wide unmeasured dimensions drop for everyone,
  and a partial user reference point restricts the ranking loudly
  (`asf_ranking_note`). v3.1.0 (2026-08-21) adds ranking governance
  (DECISIONS (p)): the objective set is first assembled from CapGate
  verdicts (`objective_assembly.py`, mode-independent); demoted dims drop
  pool-wide equally, reference-point keys naming them are explained in the
  note, and `_state_writeback` gains `_ranking_governance`. No input field
  removed or narrowed.
- **`RnaAptamerDesignWorkflow` (§15, v2.2.0)**: two-stage hierarchical
  evaluation (light GC+RhoFold on all; full ProteinX+EGARPS+interface on
  top-k); EGARPS gated by RhoFold ≥ 65 and GC ∈ [0.25, 0.85]; ASF ranking on
  `egarps_component` / `rhofold_component` / `iptm_component` (shared
  `apply_reference_point_ranking` layer since 2026-08-20: missing
  measurements impute at pool-worst, pool-wide unmeasured dimensions drop
  for everyone). v2.2.0 (2026-08-21) adds ranking governance (DECISIONS (p)):
  all three objectives are assembled from CapGate verdicts; when every dim is
  demoted (the packaged-SelfModel state) the workflow returns the
  `ranking_evidence_unavailable` degrade — success=True, generation order,
  annotations intact, no fabricated `asf_distance`, marker in
  summary/extras/`_state_writeback` and never in `errors` (non-empty errors
  is a hard failure); the light-stage RhoFold pLDDT top-k filter degrades to
  deterministic pool order when the screening profile is failed; gated oracle
  calls (`GatedActionError`) are expected-missing annotations, and gated
  ProteinX no longer raises. Opt-in
  `navigation=True` (2026-08-19) routes generation through the GenNav
  E14-protocol navigation (core `agent_core/generation/gennav_aptamer.py`;
  trace in `_state_writeback["_gennav_trace"]`; empty delivery fails with
  `navigation_delivery_empty`). Zero-sequence targets (e.g. Ferritin/1FHA)
  are a target-side boundary — do not "fix" by retrying.
- **`MrnaSequenceScoringWorkflow` (§18)**: takes a `CapabilityRegistry` like
  every other workflow; `run_mrna_sequence_scoring()` convenience default
  `auto_start_services=True`.

---

## 4. AgentRunner lock (§19, v3.4.0) essentials

- Constructor: `AgentRunner(executor, *, session_memory=None,
  quality_review_enabled=True, quality_auto_retry=False, persist_run=False)`.
- `run_form(form_params, *, session_id, explicit_workflow, user_text="",
  state=None) -> AgentState`; `stream_form(...)` yields the locked event
  sequence (`router`, `plan`, `progress`…, `tool_execution`, `runner`).
- Cross-turn contract: before replacing a stale `workflow_result`, the runner
  copies it to `_previous_workflow_result` and appends to
  `_workflow_result_history`.
- The CapGate runtime is configured from `RNADA_CAPGATE`
  (`off|advisory|enforce`, default **enforce**); the runner no longer wires
  any coordinator agent (2026-08-18).

---

## 5. CLI end-to-end lock (§20, v2.4.0) essentials

- CLI arguments: `--workflow`, `--params-file`, `--session-id`.
- `AgentRunner.run_form()` / `.stream_form()` signatures and event names.
- Artifact naming: `workspace/sessions/<session_id>/workflow_results_<hash>.json`
  and `report_<timestamp>_<hash>.md`; the JSON artifact keeps the locked key
  set (`task_id`, `success`, `candidates`, `best_candidate`, `summary`,
  `errors`, `tool_results`, `_diagnosis_history`, `_quality_auto_retry`,
  `retry_count`, `workflow_input`, `trace`, `_tool_timings`), plus the
  optional `_gennav_trace` navigation audit record (v2.4.0, present only on
  navigation-mode aptamer runs). The former `_bmc_trace` field is gone
  (2026-08-18).
- Workflow numbers 1–11 in `_WORKFLOW_LIST` must not be reassigned.
- Regression: `pytest tests/test_form_schema_builder.py
  tests/test_form_validator.py tests/test_tui_form_renderer.py
  tests/test_runner_form.py tests/test_session_memory.py -v` plus the
  PA_006–PA_024 drivers (`python run_pa_test.py 006` …, configs in
  `pa_benchmarks.json`).
