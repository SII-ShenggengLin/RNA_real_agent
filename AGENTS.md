# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-08-10

## What's New

- **Code slimming, seven-layer renumbering & QualityAgent governance** (2026-08-10): the dead `agent_core/planning/` package (`Planner` ABC, `LLMPlanner`, `build_planner`) and `tool_runtime.py` were deleted (`ToolResult` now lives in `tool_executor.py`; `MRNA_LANGCHAIN_TOOLS` renamed `GENERAL_LANGCHAIN_TOOLS`). The architecture is renumbered to **seven layers (L0–L6)**: service orchestration is L3 (was Layer 2.5), planning & multi-agent execution is L4 (was 3), session/workspace is L5 (was 4), entry points are L6 (was 5). `AgentRunner` no longer takes a `planner` argument (LOCK §19 v3.4.0) — LLM clients are built via `agent_core/llm_config.py` (`get_llm_for_provider` / `get_deepseek_llm` / `list_supported_providers`). `MrnaSequenceScoringWorkflow` now takes a `CapabilityRegistry` like every other workflow (LOCK §18 v1.1.0). QualityAgent governance fixes: a failed LLM review call marks the report `review_unavailable` (zero-confidence `pass`, error retained in `state["_quality_review_error"]` for audit), an LLM-chosen `abort` is advisory-only, and neither can flip a successful run to failed — hard-failure retry is decided solely by `WorkflowResult.is_hard_failure`. Test baseline: **668 passed**. New `docs/DECISIONS.md` registers concluded directions and do-not-repeat items, including the **cancellation of the cross-LLM backend matrix experiment** (2026-08-10 user decision: DeepSeek results extrapolate; existing fig6b data kept as historical fact).
- **LinearDesign memory guard** (2026-08-06): unbounded LinearDesign runs on very long proteins (≥ ~2000 aa; DP-lattice memory grows ~quadratically, ~7.5 GiB at 500 aa, >160 GiB at 2351 aa) exhausted the 200 GiB container cgroup and the kernel OOM killer SIGKILLed unrelated processes (observed twice). `bin/LinearDesign_2D` is now a wrapper that caps the address space (`LINEARDESIGN_MAX_RSS_KB`, default 100 GiB; real binary at `bin/LinearDesign_2D.real`), and the 8014 service rejects oversized proteins up front (`LINEARDESIGN_MAX_AA`, default 1800 aa). Over-budget jobs now fail fast with an actionable error instead of triggering cgroup OOM. The wrapper also self-marks `oom_score_adj=1000` (preferred OOM victim; note the platform pins VS Code/agent processes at 802 and the container lacks CAP_SYS_RESOURCE, so interactive sessions cannot lower their own score — making the hog the victim is the durable protection).
- **Junction ddG metric + BMC junction auto-repair stripped** (2026-08-05, LOCK §14 v2.8.0): `JunctionEvaluator` now reports full-length constrained-fold ddG at the 5'UTR–CDS junction (`junction_5utr_cds_ddg_open_w1/w2`, LinearFold, W1 = AUG −6..+9, W2 = UTR tail 60 + CDS head 30 clipped) replacing the fragment-fold `aug_buried`/`kozak_buried` booleans falsified by P1 v2 / P2 / Phase 0 ddG pilot (`junction_ddg_pilot_summary.json`, NO-GO → plan A). ddG is report/profile only; the BMC burial→`shuffle_cds_junction_codons` auto-repair path was removed (the tool itself stays locked and user-callable).
- **Junction-aware LinearDesign capability** (2026-08-04, additive): local C++ JUNCTION-PATCH (`external_repos/LinearDesign/src`) folds fixed UTR flanks with the CDS and penalizes junction-window pairs (w_jun) inside the design objective; new endpoint `POST /generate/cds_junction_aware` (8014) and locked tool `design_mrna_cds_junction_aware_with_lineardesign` v0.1.0 (INTERFACE_LOCKS §21). **Not wired into any workflow** — the P2 pre-registered acceptance (72 cells) returned NO-GO: the global-fold window penalty does not repair fragment-fold AUG/Kozak burial (penalty/metric coordinate mismatch; `experiments/results/junction_integrated_optimizer_summary.json`).
- **Workflow service pre-flight** (`agent_core/services/service_manager.py`).  Each workflow's `required_capabilities` is mapped to the local microservices it needs; `AgentRunner` health-checks and auto-starts missing services before execution (direct workflow use defaults to `auto_start_services=False`).  No manual service launcher scripts are required for any workflow, including Bowtie2 (siRNA off-target) and RhoFold (GerNA-Bind preprocessing).
- **Stability/metric conventions now uniform**: LinearFold-C `mfe` follows "more negative = more stable" like every other backend; RNASTOP uses the DNABERT-free checkpoint by default and truncates long sequences (with structure overrides) to 512 nt service-side; RNAsmol runs on CPU by default (see `microservices/rnasmol_service/start_gpu.sh` for GPU).
- **BMC UTR handling**: `FullLengthMrnaDesignWorkflow` (LOCK §14 v2.8.0) always honours the user's `utr_mode`; junction issues are addressed by UTR-preset exploration only (the codon-shuffling auto-repair was removed in v2.8.0).

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`rna_agent_system/docs/README.md`](rna_agent_system/docs/README.md) | Project overview, quick start, capability summary |
| [`rna_agent_system/docs/ARCHITECTURE.md`](rna_agent_system/docs/ARCHITECTURE.md) | Seven-layer architecture, core module APIs, routing strategy |
| [`rna_agent_system/docs/WORKFLOWS.md`](rna_agent_system/docs/WORKFLOWS.md) | Domain workflows: pipelines, scoring formulas, critic design |
| [`rna_agent_system/docs/MANUSCRIPT.md`](rna_agent_system/docs/MANUSCRIPT.md) | Experiment manual: benchmark/anchor assets, pilot-first protocol, data availability (legacy Fig 2–7 + E1–E6) |
| [`rna_agent_system/docs/TOOLS.md`](rna_agent_system/docs/TOOLS.md) | Per-tool specs, port registry, microservice notes |
| [`rna_agent_system/docs/BMC_FRAMEWORK.md`](rna_agent_system/docs/BMC_FRAMEWORK.md) | Bounded Multi-Module Coordination (Type-I/Type-II) |
| [`rna_agent_system/docs/INTERFACE_LOCKS.md`](rna_agent_system/docs/INTERFACE_LOCKS.md) | Interface Lock Policy, canonical references, sync checklists |
| [`rna_agent_system/docs/DEPLOYMENT.md`](rna_agent_system/docs/DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`rna_agent_system/docs/CHANGELOG.md`](rna_agent_system/docs/CHANGELOG.md) | Locked interface changes and major workflow introductions |
| [`rna_agent_system/docs/DECISIONS.md`](rna_agent_system/docs/DECISIONS.md) | Decisions, concluded directions and do-not-repeat register |
| [`rna_agent_system/docs/CONTRIBUTING.md`](rna_agent_system/docs/CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
| [`rna_agent_system/docs/ANCHORS.md`](rna_agent_system/docs/ANCHORS.md) | External-anchor directory spec, anchor-set JSON schema, assertion-first curation pattern |

## Project Architecture

Seven-layer design with a multi-agent execution layer at Layer 4:

- **Layer 0**: Tool wrappers, specs, registry, executor (`tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`)
- **Layer 1**: `Capability` + `CapabilityRegistry` (`capabilities/`)
- **Layer 2**: `BaseDomainWorkflow` + 11 domain workflows, including BMC workflows (`workflows/`)
- **Layer 3**: Microservice health/orchestration (`agent_core/services/service_manager.py`) — maps `required_capabilities` to local HTTP services, checks health, and auto-starts missing services.
- **Layer 4**: Planning & multi-agent execution (`pipeline/` + `agents/`; the calibrated strategy stack lives in `agent_core/calibrated/`)
  - `PipelineAgent` — deterministic pipeline orchestration
  - `SpecialistAgent` — per-workflow strategy and retry decisions
  - `CoordinatorAgent` — BMC controller for coupled workflows (`full_length_mrna_design`, `rna_aptamer_design`)
  - `QualityAgent` — unified quality review (advisory only)
  - `SynthesisAgent` — multi-node result synthesis
- **Layer 5**: `SessionMemory` + `WorkspaceManager` + `FileManager`
- **Layer 6**: `AgentRunner` unified façade (CLI / FastAPI)

Shared cross-layer constants (e.g., the unified species/organism registry) live in `agent_core/constants/`; `agent_core/constants/species.py` is the single source of truth for CAI species, RNARL model types, and reference transcriptome species IDs.

Workflow selection is explicit: CLI menu, `--workflow`, `AgentRunner.run_form(..., explicit_workflow=...)`, or a multi-node `PipelinePlan` via `--pipeline-file`. The legacy automatic router has been removed.

## LLM Configuration

Set these environment variables (or add them to `rna_agent_system/.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (primary) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API endpoint |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | `deepseek-v4-pro` or `deepseek-v4-flash` |
| `OPENAI_API_KEY` | — | OpenAI API key (optional) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (optional) |
| `ALIBABA_API_KEY` | — | Alibaba DashScope API key (optional) |
| `GOOGLE_API_KEY` | — | Google Gemini API key (optional) |

LLM clients are built via `agent_core/llm_config.py`:
```python
from agent_core.llm_config import get_llm_for_provider, get_deepseek_llm, list_supported_providers

print(list_supported_providers())                       # deepseek, openai, anthropic, alibaba, google
llm = get_llm_for_provider("openai", model="gpt-4")     # optional: api_key=, base_url=, temperature= (default 0.1)
llm = get_deepseek_llm()                                # primary provider shortcut
```

`QualityAgent` and `SynthesisAgent` accept an injectable `llm`; when constructed with `llm=None` they lazily build a DeepSeek client (`temperature=0.2` for `QualityAgent`, `0.3` for `SynthesisAgent`).

## Multi-Agent Execution

Execution is handled by a small set of coordinated agents. Workflows remain fixed tool pipelines (Layer 2); agents provide strategy, review, and orchestration (Layer 4).

| Agent | Responsibility |
|-------|----------------|
| `PipelineAgent` | Deterministic scheduling of `PipelinePlan` nodes, input binding resolution, critical-failure handling, and final synthesis. Does **not** call LLMs. |
| `SpecialistAgent` | Per-workflow strategy: runs the workflow (or `CoordinatorAgent` for BMC workflows), invokes `QualityAgent`, decides retry/adjust/abort, and returns `AgentResult`. |
| `CoordinatorAgent` | BMC controller for coupled workflows. Detects the BMC-capable interface (`run_initial`, `bmc_prepare`, `bmc_run_round`, `bmc_finalize`) and orchestrates the bounded convergence loop, delegating diagnosis/feedback to the workflow's `ReferencePointCoordinator` / `AptamerCoordinator`. |
| `QualityAgent` | Unified quality review using workflow-specific `QualityProfile`. Outputs an advisory `QualityReport`; it neither triggers retry on its own nor can it flip a successful run to failed. |
| `SynthesisAgent` | Passes through single-node results; for multi-node pipelines, generates a concise synthesis report. |

| Workflows reviewed by QualityAgent | QualityProfile |
|-----------------------------------|----------------|
| `mrna_cds_design` | `MRNA_CDS_QUALITY_PROFILE` |
| `sirna_design` | `SIRNA_QUALITY_PROFILE` |
| `sgrna_design` | `SGRNA_QUALITY_PROFILE` |
| `rna_aptamer_design` | `RNA_APTAMER_QUALITY_PROFILE` |
| `ires_prediction` | `IRES_QUALITY_PROFILE` |
| `rna_secondary_structure_design` | `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` |
| `rna_tertiary_structure_design` | `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE` |
| `full_length_mrna_design` | `FULL_LENGTH_MRNA_QUALITY_PROFILE` |

| Workflows without quality review | Reason |
|----------------------------------|--------|
| `mrna_sequence_scoring` | Deterministic scoring task |
| `aso_target_screening` | Deterministic screening task |
| `rna_small_molecule_interaction` | Deterministic prediction task |

Configure behavior via `AgentRunner`:
```python
runner = AgentRunner(
    executor=executor,
    quality_review_enabled=True,   # enable QualityAgent LLM diagnosis
    quality_auto_retry=False,   # advisory mode by default
)
```

`AgentRunner` automatically enables `auto_start_services` on every workflow it owns.  If you instantiate a workflow directly and want the same pre-flight/auto-start behavior, set `workflow.auto_start_services = True` before calling `run()` / `run_initial()`.  The standalone convenience function `run_mrna_sequence_scoring()` also defaults to `auto_start_services=True`; pass `auto_start_services=False` when providing a custom `CapabilityRegistry` in tests or other managed environments.  When pre-flight fails, the workflow returns a `WorkflowResult(success=False, ...)` with actionable error messages instead of crashing mid-execution.

- **Advisory mode** (`quality_auto_retry=False`): `QualityAgent` records a `QualityReport` but the `SpecialistAgent` only retries on hard failures (`WorkflowResult.is_hard_failure`: `success=False`, empty candidates, tool errors).
- **Auto-retry mode** (`quality_auto_retry=True`): `SpecialistAgent` may auto-retry when `QualityReport` recommends adjustments with valid overrides.
- **Governance (2026-08-10)**: if the LLM review call fails, the report is marked `review_unavailable` (zero-confidence `pass`) and the error is retained in `state["_quality_review_error"]` for audit; an LLM-chosen `abort` is advisory-only. Neither path can flip a successful run to failed.
- **Cross-turn context**: before replacing a stale `workflow_result`, `AgentRunner` copies it to `_previous_workflow_result` and appends it to `_workflow_result_history`, enabling quality comparison and explicit historical references.

### Known limitations (do not assume these are already implemented)

1. **`PipelinePlan` edges are required for every data dependency.**
   - `input_bindings` can only reference upstream nodes/aliases that are reachable through explicit `PipelineEdge`s.
   - A binding alone does **not** create an execution dependency; if node B consumes an output from node A, there must be both an edge `A → B` and an `input_bindings` entry in B.

2. **`QualityProfile.build_prompt` is an optional extension point.**
   - It is intentionally not in the base architecture docs because only specialized profiles need it (currently `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE`).
   - Avoid adding new `build_prompt` overrides unless the default prompt cannot express workflow-specific tuning guidance.

## Interface Lock Policy

This project uses INTERFACE LOCK comments to prevent accidental breaking changes. Do not modify any function signature, Pydantic field, return dict key, or state field inside a lock block without updating all synchronized files and re-running tests.

See [`rna_agent_system/docs/INTERFACE_LOCKS.md`](rna_agent_system/docs/INTERFACE_LOCKS.md) for the canonical lock table and checklists.

### Currently locked interfaces (summary)

| Tool / Module | Version | Reference |
|---------------|---------|-----------|
| `compute_rna_sequence_gc_content` | v0.1.0 | `INTERFACE_LOCKS.md` §3 |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `INTERFACE_LOCKS.md` §4 |
| `compute_rna_sequence_u_content` | v0.1.0 | `INTERFACE_LOCKS.md` §5 |
| `compute_cai_for_cds_sequence` | v0.1.0 | `INTERFACE_LOCKS.md` §6 |
| `run_blastn_similarity_search` | v0.2.0 | `tools.py` + `tool_specs.py` |
| `run_bowtie2_short_alignment` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `tools.py` + `tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `tools.py` + `tool_specs.py` |
| `score_sgrna_handle_with_crgpt` | v0.3.0 | `tools.py` + `tool_specs.py` |
| CRISOT suite (8 tools) | v0.2.0 | `tools.py` + `tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `INTERFACE_LOCKS.md` §7 |
| `design_mrna_cds_junction_aware_with_lineardesign` | v0.1.0 | `INTERFACE_LOCKS.md` §21 |
| ViennaRNA suite | v0.4.0 | `tools.py` + `tool_specs.py` |
| LinearFold suite | v0.2.0 | `tools.py` + `tool_specs.py` |
| `predict_5utr_mrl_with_gemorna` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `predict_3utr_stability_with_gemorna` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `shuffle_cds_junction_codons` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `identify_protein_binding_hotspots` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `analyze_rna_protein_interface` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `score_structure_alignment` | v0.1.0 | `tools.py` + `tool_specs.py` |
| `MrnaCdsDesignWorkflow` | v1.1.0 | `INTERFACE_LOCKS.md` §8 |
| `RnaSmallMoleculeInteractionWorkflow` | v1.1.0 | `INTERFACE_LOCKS.md` §9 |
| `SirnaDesignWorkflow` | v1.1.1 | `INTERFACE_LOCKS.md` §10 |
| `SgRnaDesignWorkflow` | v1.1.0 | `INTERFACE_LOCKS.md` §11 |
| `AsoTargetScreeningWorkflow` | v1.0.0 | `INTERFACE_LOCKS.md` §12 |
| `IresPredictionWorkflow` | v1.1.0 | `INTERFACE_LOCKS.md` §13 |
| `FullLengthMrnaDesignWorkflow` | v2.8.0 | `INTERFACE_LOCKS.md` §14 |
| `RnaAptamerDesignWorkflow` | v1.4.2 | `INTERFACE_LOCKS.md` §15 |
| `RnaSecondaryStructureDesignWorkflow` | v1.0.0 | `INTERFACE_LOCKS.md` §16 |
| `RnaTertiaryStructureDesignWorkflow` | v1.0.0 | `INTERFACE_LOCKS.md` §17 |
| `MrnaSequenceScoringWorkflow` | v1.1.0 | `INTERFACE_LOCKS.md` §18 |
| `AgentRunner` | v3.4.0 | `INTERFACE_LOCKS.md` §19 |
| `CLI End-to-End Execution Flow` | v2.3.0 | `INTERFACE_LOCKS.md` §20 |

## Testing

Run the agent-core test suite before committing (current baseline: **668 passed**):

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

For locked CLI regressions, run the PA_006–PA_024 end-to-end inputs documented in [`rna_agent_system/docs/INTERFACE_LOCKS.md`](rna_agent_system/docs/INTERFACE_LOCKS.md) §20 using the consolidated driver:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 006
```

Benchmark configurations live in `rna_agent_system/pa_benchmarks.json`; pass any PA number `006`–`024` to the driver.

For live microservice end-to-end smoke tests, no manual service startup is needed — the CLI / `AgentRunner` pre-flight auto-starts the services each workflow requires:

- `FullLengthMrnaDesignWorkflow`: run `PYTHONPATH="$(pwd):$PYTHONPATH" python tests/test_full_length_mrna_e2e_live.py`.
- `RnaAptamerDesignWorkflow`: run the PA_020 benchmark via `PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 020`.
