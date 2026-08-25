# Agent Guidelines for RNA_real_agent

> **Consolidated index.** Authoritative documentation lives in `rna_agent_system/docs/`.
> **Last updated**: 2026-08-25 (experiment-programme reset + Exp 1 executed)

## What's New

- **Experiment-programme reset + Exp 1 done** (2026-08-25, DECISIONS (z), user-directed): the architecture moved too much since the legacy campaigns — **all paper experiments re-run against the frozen gated platform** with newly written drivers/figures; legacy campaign code, plots and results deleted (retained: SelfModel evidence chain `e1_*_v2`/`e7_*`/`rnasmol_boundary_panel*`/`e16_e17_e18/` + `build_default_self_model.py`, `codon_tables/`, `tool_inventory.json`, `MODEL_API_USAGE.md`, audit trail). **RNADesign-210 audited and repaired on disk** (`experiments/audit_rnadesign210.py` / `fix_rnadesign210.py`; manifest recounts 208→210, category taxonomy → basic/edge/full, IRES fixtures rebuilt on real poliovirus/EMCV anchors with mode-0 thresholds inside the oracle's measured regime, expected tool chains regrounded from live traces; re-audit 0 issues / 0 warnings). **Exp 1 (Fig 2a) executed: 210/210 across the 11 workflows** (`experiments/exp1_rnadesign210.py`, advisory arm, records under `experiments/results/exp1_rnadesign210/`; 4-task enforce probe documents the gated-refusal signatures). **Unified figure palette locked** (`experiments/plots/palette.py` rev 7, **user-finalized** — the earthy Morandi twelve-colour set; every subsequent experiment figure draws from it exclusively, no palette revisions without user direction; Fig 2a at `experiments/plots/output/fig2a_coverage.{pdf,png}`). Experiment services are GPU-pinned to 0/1/2 by `experiments/exp1_bring_up_services.sh`.
- **Paper-preparation documentation pass** (2026-08-25, doc-only): external-baseline arms **E21 (bare-LLM)** and **E22 (same-tools ReAct)** registered in `docs/DECISIONS.md` Part 4 (planned, not yet run — see Standing facts); all six `docs/PAPER_DRAFT.md` figure legends re-lettered to `docs/FIGURE_PLAN_V5.md` (the single source of truth for panel lettering); the first Results subsection split into a system-design Overview (Fig. 1) + RNADesign-210 results (Fig. 2); Supplementary Table S1 / Note S2 registered in the figure plan. Same-day **figure-type diversification pass** (doc-only): panel chart types across Figs. 1–6 diversified after a structured survey of eight agentic-science references — registered in `docs/FIGURE_PLAN_V5.md` and named in the `docs/PAPER_DRAFT.md` legends.
- **Repo-wide simplification pass — code is the source of truth, old artifacts purged** (2026-08-22, user-directed; `docs/CHANGELOG.md` 2026-08-22 (i) + DECISIONS (y)): (1) fixed a real leak — every test-suite run wrote scratch files to the real `workspace/` root (141k files / 1.3 GB accumulated); `tests/conftest.py` now redirects all default workspace bases to a per-run `workspace/_tests` scratch (subprocess-safe via the new `RNADA_WORKSPACE_BASE` env override honoured by `WorkspaceManager`), verified zero new root files across a full suite run. (2) Demo tool `workflow_demo_echo` removed — **41 registered tools, all production** (`python -m agent_core.tool_inventory`). (3) Duplicated QualityAgent retry tests consolidated into one parametrized module; duplicated `Args/Returns` docstrings stripped from 39 `tools.py` wrappers (the Input-model `Field` descriptions are the single source). (4) Historical outputs purged: superseded figure generations (`plots/{paper,paper_v4,fig*_panels}`), archived experiment rounds, leaked workspace scratch and stale service-run intermediates — **repository 4.3 GB → 2.0 GB** (remaining bulk: 1.2 GB of required reference genomes + the retained audit trail); the CapGate audit trail (`workspace/audit/`, `workspace/sessions/`) and every `*_fresh_audit_*` evidence directory retained. Suite **635 passed, 1 skipped**; PA_006–PA_019 rerun green.
- **Full-platform E2E fresh-data audit** (2026-08-22, DECISIONS (x); evidence `workspace/e2e_fresh_audit_2026-08-22/`): whole stack — all three Layer-6 entry points driving all 11 workflows on live services + live CapGate + live DeepSeek review on entirely fresh fetched data; 56 checks / 0 failures post-fix. Three defects fixed: opaque `sgrna_design` missing-seed failure (now a clear `ValueError`), `stream_form` raising on hard failure (now a final `runner` event), ViennaRNA inverse-fold accepting pseudoknot brackets (SIGSEGV behind a 503; now rejected up-front — normalise Rfam `SS_cons` upstream).
- **Layer 0–6 fresh-data audit programme complete** (2026-08-21/22, DECISIONS (r)–(u); evidence `workspace/layer{1..6}_fresh_audit_*/`): every layer audited on live-fetched data; 17 defects fixed across the stack (WorkspaceManager path-traversal/`delete_session("")` rmtree, pipeline session-scoping leak, API success misreporting, dropped progress events, degraded-service pre-flight hole, dropped ranking-governance audit events, …).
- **GenNav production wiring** (2026-08-19/22, DECISIONS (n)/(q)): opt-in `navigation` mode on `rna_aptamer_design` (v2.1.0, length lattice) and `mrna_cds_design` (v1.2.0, GenNav-λ) — deterministic, zero-LLM, full trace in `_state_writeback["_gennav_trace"]`. Six workflows now rank by the shared ASF layer; ranking objectives are assembled from CapGate verdicts (`docs/RANKING_GOVERNANCE.md`).
- **System simplification 2026-08-18** (DECISIONS (a)/(m)/(n)): BMC framework removed after its coordination-gain narrative was triple-falsified; 12 dead tools purged; E1–E15 experiment machinery deleted (evidence JSONs kept as the audit record).

## Standing facts (keep in mind before proposing work)

- **Registered next steps**: the remaining paper experiments (2.2 节实验 2 起：Fig 2 b–i panels, Figs 3–6 campaigns, E21/E22 baseline arms) re-run under the 2026-08-25 reset — new drivers follow the Exp-1 pattern (`experiments/expN_*.py`, pre-registered docstring, advisory primary arm + enforce probes where gating semantics matter, unified palette figures); E19/E20 stay reserved for the CRISOT/CRGPT data gap.
- **Pending profiling backlog**: CRISOT-Score + CRGPT stay governance=pending on a registered data gap — no labeled anchor set exists on disk; do **not** improvise self-referential anchors (DECISIONS (l)).
- **Auditability boundary**: every ToolExecutor call lands in the CapGate platform audit trail (`workspace/audit/platform_audit.jsonl`, session-stamped); microservice-internal oracle hops (e.g. GerNA-Bind folding via RhoFold inside the service) are **not** audited at the agent layer (DECISIONS (k)).
- **Never deleted**: the workspace audit trail and the SelfModel evidence chain (`e1_*_v2`/`e7_*`/`rnasmol_boundary_panel*`/`e16_e17_e18/`); campaign artifacts are deleted per reset (DECISIONS (n)/(y)/(z)).
- Before proposing any new experiment/optimization, check `docs/DECISIONS.md` Part 1 (do-not-repeat register).

## Documentation Index

| Document | Purpose |
|----------|---------|
| [`rna_agent_system/docs/README.md`](rna_agent_system/docs/README.md) | Project overview, quick start, capability summary |
| [`rna_agent_system/docs/ARCHITECTURE.md`](rna_agent_system/docs/ARCHITECTURE.md) | Seven-layer architecture, core module APIs, routing strategy |
| [`rna_agent_system/docs/WORKFLOWS.md`](rna_agent_system/docs/WORKFLOWS.md) | Domain workflows: pipelines, scoring formulas, critic design |
| [`rna_agent_system/docs/MANUSCRIPT.md`](rna_agent_system/docs/MANUSCRIPT.md) | Experiment manual: benchmark/anchor assets, pilot-first protocol, data availability |
| [`rna_agent_system/docs/TOOLS.md`](rna_agent_system/docs/TOOLS.md) | Per-tool specs, port registry, microservice notes |
| [`rna_agent_system/docs/DEPLOYMENT.md`](rna_agent_system/docs/DEPLOYMENT.md) | Environment setup, testing recipes, curl examples |
| [`rna_agent_system/docs/CHANGELOG.md`](rna_agent_system/docs/CHANGELOG.md) | Current interface state + condensed change-era register |
| [`rna_agent_system/docs/DECISIONS.md`](rna_agent_system/docs/DECISIONS.md) | Do-not-repeat register, established results, timeline |
| [`rna_agent_system/docs/RANKING_GOVERNANCE.md`](rna_agent_system/docs/RANKING_GOVERNANCE.md) | Ranking governance design: verdict-driven ASF objective assembly (DECISIONS (p)) |
| [`rna_agent_system/docs/CONTRIBUTING.md`](rna_agent_system/docs/CONTRIBUTING.md) | Coding standards, new-tool procedure, commit conventions |
| [`rna_agent_system/docs/ANCHORS.md`](rna_agent_system/docs/ANCHORS.md) | External-anchor directory spec, anchor-set JSON schema, assertion-first curation pattern |

## Project Architecture

Seven-layer design with a multi-agent execution layer at Layer 4:

- **Layer 0**: Tool wrappers, specs, registry, executor (`tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`) — 41 registered tools, all production
- **Layer 1**: `Capability` + `CapabilityRegistry` (`capabilities/`)
- **Layer 2**: `BaseDomainWorkflow` + 11 domain workflows (`workflows/`) — all plain generate → evaluate → score → rank pipelines; six workflows rank by Achievement Scalarizing Function (`full_length_mrna_design`, `rna_aptamer_design`, `sirna_design`, `sgrna_design`, `rna_tertiary_structure_design`, `aso_target_screening`; DECISIONS (o)/(q)); GenNav constraint navigation is an opt-in path on `rna_aptamer_design` (length lattice) and `mrna_cds_design` (GenNav-λ)
- **Layer 3**: Microservice health/orchestration (`agent_core/services/service_manager.py`)
- **Layer 4**: Planning & multi-agent execution (`pipeline/` + `agents/`; the calibrated CapGate stack lives in `agent_core/calibrated/`)
  - `PipelineAgent` — deterministic pipeline orchestration
  - `SpecialistAgent` — per-workflow strategy and retry decisions
  - `QualityAgent` — unified quality review (advisory only)
  - `SynthesisAgent` — multi-node result synthesis (ClaimGate-gated)
- **Layer 5**: `SessionMemory` + `WorkspaceManager` + `FileManager` (session ids validated as single path components; `RNADA_WORKSPACE_BASE` overrides the default workspace base)
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

## Testing

Run the agent-core test suite before committing (current baseline: **635 passed, 1 skipped** — the suite is workspace-isolated: test scratch goes to `workspace/_tests/`, never the real workspace root):

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x
```

For CLI end-to-end regressions, run the PA_006–PA_036 inputs (all 11 workflows, user-input → final design result; 006–024 original batch, 025–036 the 2026-08-19 fresh-data batch including two GenNav `navigation=true` runs) using the consolidated driver:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 006
```

Benchmark configurations live in `rna_agent_system/pa_benchmarks.json`; pass any PA number `006`–`036` to the driver. The driver defaults its subprocesses to `RNADA_CAPGATE=advisory` (PA runs are process-aware CLI regressions; enforce-mode oracle gating — the registered E16–E18 consequence, DECISIONS (j)/(l) — would otherwise fail whole workflows whose scoring oracles are legitimately blocked in production). Set `RNADA_CAPGATE` explicitly to override. Static input fixtures live git-tracked under `data/benchmarks/RNA-BioBench-ProcessAware/fixtures/` (provenance in `data/benchmarks/README.md`).

For live microservice end-to-end smoke tests, no manual service startup is needed — the CLI / `AgentRunner` pre-flight auto-starts the services each workflow requires:

- `FullLengthMrnaDesignWorkflow`: run `PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/test_full_length_mrna_e2e_live.py -v` (pytest module — plain `python` invocation is a silent no-op).
- `RnaAptamerDesignWorkflow`: run the PA_020 benchmark via `PYTHONPATH="$(pwd):$PYTHONPATH" python run_pa_test.py 020`.
