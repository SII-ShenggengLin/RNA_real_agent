# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-08-21 (Layer-1 fresh-data audit)

## What's New

- **Layer-1 fresh-data audit — capability layer verified, one EGARPS path defect fixed** (2026-08-21, user-directed; full detail in `docs/CHANGELOG.md` 2026-08-21 (b)): first dedicated audit of `agent_core/capabilities/base.py` on fresh real data (sequences fetched live from NCBI — SARS-CoV-2 Spike/N, GAPDH, HCV IRES, GFP, yeast tRNA-Phe — plus RCSB 1EHZ/1CVJ; nothing reused from fixtures). 39 real tool invocations through `Capability.invoke` + registry semantics, state-writeback key uniqueness, output_model fidelity and error paths: **252 checks / 0 failures**. One defect fixed: `score_rna_protein_complex_with_egarps` posted workspace-relative paths verbatim (service 404s); the wrapper now resolves via `_absolute_path_under_project` like blast/GC (regression: `tests/test_egarps_wrapper_path.py`). Suite 541 passed. Evidence: `workspace/layer1_fresh_audit_2026-08-21/` (fetch script, audit driver, `audit_report.json`).

- **Ranking governance — ASF objectives assembled from CapGate verdicts** (2026-08-21, user-directed; full detail in `docs/RANKING_GOVERNANCE.md` + DECISIONS.md (p)): the shared ASF ranking layer now consumes DecisionGate verdicts as a first-class input (`agent_core/calibrated/objective_assembly.py`; deterministic, zero LLM, **mode-independent** — advisory and enforce produce the same ranking wherever SelfModel records exist). A dimension backed by an oracle without verified (or transferred-verified) ranking power is demoted to `scoring_annotation` pool-wide equally; pending (CRISOT/CRGPT) and unprofiled dims are kept + flagged; deterministic compute dims never enter the mechanism; `RNADA_CAPGATE=off` disables it entirely. Under the packaged SelfModel `rna_aptamer_design` (v2.2.0) delivers the `ranking_evidence_unavailable` degrade (success=True, generation order, annotations intact, marker never in `errors` — non-empty errors is a hard failure) and its light-stage RhoFold pLDDT top-k filter degrades to deterministic pool order; gated calls (`GatedActionError`) are expected-missing annotations (gated ProteinX no longer raises). `full_length_mrna_design` v3.1.0 + siRNA/sgRNA/tertiary: flags and `_state_writeback["_ranking_governance"]` only. Deferred (registered): continuous profile-derived ASF weights. Tests: `tests/test_ranking_governance.py` (15); suite 534 passed.

- **paper_v5 figure rebuild — survey-driven Nature Methods figure programme** (2026-08-20, user-directed; full detail in `docs/CHANGELOG.md` 2026-08-20): all six main figures regenerated at `experiments/plots/paper_v5/` after a systematic survey of seven Nature/Science agent-system papers (`docs/REFERENCE_FIGURE_SURVEY.md`; plan in `docs/FIGURE_PLAN_V5.md`). One script per panel (51 panels) sharing a Morandi/Arial `style.py`; `assemble.py` composes vector PDF + PNG and draws panel letters; `qa_bounds.py` is the objective clipping audit (all panels pass). Fig 1 = architecture (6 panels); Figs 2–6 = five results figures × 9 panels, every number re-derived from the retained verdict files or the live audit trail. `PAPER_DRAFT.md` is at v4.4 with panel references updated.

- **Batch-B fresh-data re-verification + session-stamped audit trail** (2026-08-19, user-directed; full detail in `docs/CHANGELOG.md` 2026-08-19 batch-B): a second full-platform pass on **entirely fresh data** — 12 new PA benchmarks (PA_025–PA_036, all 11 workflows + two GenNav `navigation=true` campaigns on 1CA2/3CNA) — **12/12 passed, 0 failed turns** (evidence: `experiments/results/pa_regression_batchB_2026-08-19/`). Both navigation campaigns delivered 5/5 in all three profiles with no degrade, exercising both the budget-capped path (1CA2, 47/48, 5 cycling guarantee rounds) and the early-stop path (3CNA, 35/48). Every `tool_call` audit record now carries `session_id` + `task_type` (audit lines are attributable to the run that produced them); enabling fix: `AgentRunner.stream_form` copies contextvars into its pipeline worker thread. New fixtures: `emcv_5utr.fa` / `poliovirus_5utr.fa` (first authentic IRES-positive PA inputs — mode-0 scans reproduced the fig2i literature scores).
- **GenNav production wiring + full-platform end-to-end verification** (2026-08-19, user-directed; full detail in `docs/CHANGELOG.md` 2026-08-19): the E14-validated GenNav constraint navigation is now a user-reachable production path — `RnaAptamerDesignWorkflow` v2.1.0 gains the opt-in `navigation` input field (default `False`; static gear unchanged). The navigation runs deterministically (zero LLM): 17-length lattice probe → cycling guaranteed-repair reinforcement (48-raw cap, early stop) → per-profile matrix-v3 + D1 delivery, with every ODesign/LinearFold call audited and the full trace in `_state_writeback["_gennav_trace"]`; empty delivery is the dedicated `navigation_delivery_empty` degrade. Core: `agent_core/generation/gennav_aptamer.py` (+ matrix/delivery pure functions); tests: `tests/test_rna_aptamer_gennav.py`. First verification pass: 496 tests green, PA_006–PA_024 rerun, live CapGate audit trail inspected. mRNA-side λ navigation (E6) remains evidence-only campaign machinery.
- **System simplification pass — BMC removed, dead tools and concluded experiment drivers purged** (2026-08-18, user-directed; full detail in `docs/CHANGELOG.md` 2026-08-18): the BMC framework (`CoordinatorAgent`, `workflows/coordinator.py`, the `bmc_*` interface) was removed after its coordination-gain narrative was triple-falsified (DECISIONS.md (a), (m)) — both coupled workflows now run the plain generate → evaluate → ASF/Pareto-rank path with unchanged audit writeback; 12 dead tools deleted (54 → 42 specs) together with their service endpoints and the whole codonw_slim_service; the E1/E3-era calibrated experiment machinery (profiler / experiment_planner / campaign_runner / case_memory) and all concluded E1–E15 drivers/probes/plots scripts were deleted (evidence JSONs under `experiments/results/` remain the audit trail). The E14 GenNav strategy survives as the pure-function core `agent_core/generation/gennav_aptamer.py`. Bug fix: `bowtie2_ma` int/str type mismatch.

## Standing facts (keep in mind before proposing work)

- **Registered next step**: RNADesign-210 / fig2 panel regeneration against the gated platform (driver `experiments/run_platform_quality_benchmark.py`).
- **Pending profiling backlog**: CRISOT-Score + CRGPT stay governance=pending on a registered data gap — no labeled anchor set exists on disk; do **not** improvise self-referential anchors (DECISIONS.md (l)).
- **Auditability boundary**: every ToolExecutor call lands in the CapGate platform audit trail; microservice-internal oracle hops (e.g. GerNA-Bind folding via RhoFold inside the service) are **not** audited at the agent layer (DECISIONS.md (k)).
- Before proposing any new experiment/optimization, check `docs/DECISIONS.md` Part 1 (do-not-repeat register).

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`rna_agent_system/docs/README.md`](rna_agent_system/docs/README.md) | Project overview, quick start, capability summary |
| [`rna_agent_system/docs/ARCHITECTURE.md`](rna_agent_system/docs/ARCHITECTURE.md) | Seven-layer architecture, core module APIs, routing strategy |
| [`rna_agent_system/docs/WORKFLOWS.md`](rna_agent_system/docs/WORKFLOWS.md) | Domain workflows: pipelines, scoring formulas, critic design |
| [`rna_agent_system/docs/MANUSCRIPT.md`](rna_agent_system/docs/MANUSCRIPT.md) | Experiment manual: benchmark/anchor assets, pilot-first protocol, data availability |
| [`rna_agent_system/docs/TOOLS.md`](rna_agent_system/docs/TOOLS.md) | Per-tool specs, port registry, microservice notes |
| [`rna_agent_system/docs/INTERFACE_LOCKS.md`](rna_agent_system/docs/INTERFACE_LOCKS.md) | Interface Lock Policy, canonical references, sync checklists |
| [`rna_agent_system/docs/DEPLOYMENT.md`](rna_agent_system/docs/DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`rna_agent_system/docs/CHANGELOG.md`](rna_agent_system/docs/CHANGELOG.md) | Current interface state + recent change era |
| [`rna_agent_system/docs/DECISIONS.md`](rna_agent_system/docs/DECISIONS.md) | Decisions, concluded directions and do-not-repeat register |
| [`rna_agent_system/docs/RANKING_GOVERNANCE.md`](rna_agent_system/docs/RANKING_GOVERNANCE.md) | Ranking governance design: verdict-driven ASF objective assembly (DECISIONS (p)) |
| [`rna_agent_system/docs/CONTRIBUTING.md`](rna_agent_system/docs/CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
| [`rna_agent_system/docs/ANCHORS.md`](rna_agent_system/docs/ANCHORS.md) | External-anchor directory spec, anchor-set JSON schema, assertion-first curation pattern |
| [`rna_agent_system/docs/CLAUDE_CODE_PLATFORM_SIGKILL.md`](rna_agent_system/docs/CLAUDE_CODE_PLATFORM_SIGKILL.md) | 平台按名查杀 claude 进程（SIGKILL）的根因、验证方法与终端/扩展修复手册 |

## Project Architecture

Seven-layer design with a multi-agent execution layer at Layer 4:

- **Layer 0**: Tool wrappers, specs, registry, executor (`tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`) — 42 registered tools (41 production / 1 demo)
- **Layer 1**: `Capability` + `CapabilityRegistry` (`capabilities/`)
- **Layer 2**: `BaseDomainWorkflow` + 11 domain workflows (`workflows/`) — all plain generate → evaluate → score → rank pipelines; the two reference-point workflows (`full_length_mrna_design`, `rna_aptamer_design`) rank by Achievement Scalarizing Function
- **Layer 3**: Microservice health/orchestration (`agent_core/services/service_manager.py`)
- **Layer 4**: Planning & multi-agent execution (`pipeline/` + `agents/`; the calibrated CapGate stack lives in `agent_core/calibrated/`)
  - `PipelineAgent` — deterministic pipeline orchestration
  - `SpecialistAgent` — per-workflow strategy and retry decisions
  - `QualityAgent` — unified quality review (advisory only)
  - `SynthesisAgent` — multi-node result synthesis (ClaimGate-gated)
- **Layer 5**: `SessionMemory` + `WorkspaceManager` + `FileManager`
- **Layer 6**: `AgentRunner` unified façade (CLI / FastAPI)

Shared cross-layer constants (e.g., the unified species/organism registry) live in `agent_core/constants/`; `agent_core/constants/species.py` is the single source of truth for CAI species, RNARL model types, and reference transcriptome species IDs.

Workflow selection is explicit: CLI menu, `--workflow`, `AgentRunner.run_form(..., explicit_workflow=...)`, or a multi-node `PipelinePlan` via `--pipeline-file`. There is no automatic router.

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

| Agent | Responsibility |
|-------|----------------|
| `PipelineAgent` | Deterministic scheduling of `PipelinePlan` nodes, input binding resolution, critical-failure handling, and final synthesis. Does **not** call LLMs. |
| `SpecialistAgent` | Per-workflow strategy: runs the workflow, invokes `QualityAgent`, decides retry/adjust/abort, and returns `AgentResult`. |
| `QualityAgent` | Unified quality review using workflow-specific `QualityProfile`. Outputs an advisory `QualityReport`; it neither triggers retry on its own nor can it flip a successful run to failed. |
| `SynthesisAgent` | Passes through single-node results; for multi-node pipelines, generates a concise synthesis report (claims pass the ClaimGate). |

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

```python
runner = AgentRunner(
    executor=executor,
    quality_review_enabled=True,   # enable QualityAgent LLM diagnosis
    quality_auto_retry=False,      # advisory mode by default
)
```

`AgentRunner` automatically enables `auto_start_services` on every workflow it owns. If you instantiate a workflow directly and want the same pre-flight/auto-start behavior, set `workflow.auto_start_services = True` before calling `run()`. The standalone convenience function `run_mrna_sequence_scoring()` also defaults to `auto_start_services=True`; pass `auto_start_services=False` when providing a custom `CapabilityRegistry` in tests or other managed environments. When pre-flight fails, the workflow returns a `WorkflowResult(success=False, ...)` with actionable error messages instead of crashing mid-execution.

- **Advisory mode** (`quality_auto_retry=False`): `QualityAgent` records a `QualityReport` but the `SpecialistAgent` only retries on hard failures (`WorkflowResult.is_hard_failure`: `success=False`, empty candidates, tool errors).
- **Auto-retry mode** (`quality_auto_retry=True`): `SpecialistAgent` may auto-retry when `QualityReport` recommends adjustments with valid overrides.
- **Governance**: if the LLM review call fails, the report is marked `review_unavailable` (zero-confidence `pass`) and the error is retained in `state["_quality_review_error"]` for audit; an LLM-chosen `abort` is advisory-only. Neither path can flip a successful run to failed.
- **Cross-turn context**: before replacing a stale `workflow_result`, `AgentRunner` copies it to `_previous_workflow_result` and appends it to `_workflow_result_history`.

### Known limitations (do not assume these are already implemented)

1. **`PipelinePlan` edges are required for every data dependency.** A binding alone does **not** create an execution dependency; if node B consumes an output from node A, there must be both an edge `A → B` and an `input_bindings` entry in B.
2. **`QualityProfile.build_prompt` is an optional extension point** — only `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` uses it. Avoid adding new `build_prompt` overrides unless the default prompt cannot express workflow-specific tuning guidance.

## Interface Lock Policy

This project uses INTERFACE LOCK comments to prevent accidental breaking changes. Do not modify any function signature, Pydantic field, return dict key, or state field inside a lock block without updating all synchronized files and re-running tests. See [`rna_agent_system/docs/INTERFACE_LOCKS.md`](rna_agent_system/docs/INTERFACE_LOCKS.md) for the canonical lock table.

## Testing

Run the agent-core test suite before committing (current baseline: **496 passed**):

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

For locked CLI regressions, run the PA_006–PA_036 end-to-end inputs (all 11 workflows, user-input → final design result; 006–024 original batch, 025–036 the 2026-08-19 fresh-data batch including two GenNav `navigation=true` runs) using the consolidated driver:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 006
```

Benchmark configurations live in `rna_agent_system/pa_benchmarks.json`; pass any PA number `006`–`036` to the driver. The driver defaults its subprocesses to `RNADA_CAPGATE=advisory` (PA runs are process-aware CLI regressions; enforce-mode oracle gating — the registered E16–E18 consequence, DECISIONS.md (j)/(l)) would otherwise fail whole workflows whose scoring oracles are legitimately blocked in production). Set `RNADA_CAPGATE` explicitly to override. Static input fixtures live git-tracked under `data/benchmarks/RNA-BioBench-ProcessAware/fixtures/` (provenance in `data/benchmarks/README.md`).

For live microservice end-to-end smoke tests, no manual service startup is needed — the CLI / `AgentRunner` pre-flight auto-starts the services each workflow requires:

- `FullLengthMrnaDesignWorkflow`: run `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_full_length_mrna_e2e_live.py -v` (pytest module — plain `python` invocation is a silent no-op).
- `RnaAptamerDesignWorkflow`: run the PA_020 benchmark via `PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 020`.
