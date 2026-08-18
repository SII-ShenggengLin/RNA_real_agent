# Architecture & Core Interfaces

> **Scope**: design principles, seven-layer architecture, core module APIs, routing strategy, and workflow–quality co-design.  
> **Last updated**: 2026-08-18 (BMC framework removed — see DECISIONS.md (m))

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Seven-Layer Architecture](#2-seven-layer-architecture)
3. [Core Modules](#3-core-modules)
4. [Routing Strategy](#4-routing-strategy)
5. [Workflow–Quality Co-Design](#5-workflowquality-co-design)
6. [How to Extend](#6-how-to-extend)

---

## 1. Design Principles

### 1.1 Single Source of Truth for HTTP

`agent_core/tools.py` is the **only** module that calls `requests.post` to microservice ports. Workflow-layer tools delegate to the LangChain `@tool` wrappers via `.invoke()`.

### 1.2 Shared Sequence Utilities

`agent_core/sequence_utils.py` contains `normalize_rna_sequence()`, `compute_gc_content()`, `extract_dot_bracket()`, `validate_dot_bracket()`, `compute_dot_bracket_unpaired_fraction()`, and `compute_u_content()`. Both agent-core and microservices import from here so local fallbacks and server results never drift apart.

### 1.3 Complete State Tracking

The agent state is a generic `TypedDict` (`agent_core/state.py`). Granular tool-specific metrics are stored inside `tool_results[tool_name]` and inside each `Candidate.metadata["metrics_bundle"]`, not as top-level state fields. This keeps `AgentState` stable as new tools and workflows are added.

### 1.4 Decoupled Spec → Registry → Executor

```
tool_specs.py (Pydantic specs + TOOL_SPECS registry)
    ↓
tools.py (~@tool wrappers, HTTP → microservices)
    ↓
tool_registry.py (name→callable lookup)
    ↓
tool_executor.py (ToolResult, dispatch + tracing)
```

---

## 2. Seven-Layer Architecture

```
┌──────────────────────────────────────────┐
│ Layer 6  Entry Points                    │
│          AgentRunner / FastAPI / CLI     │
├──────────────────────────────────────────┤
│ Layer 5  Session & Workspace             │
│          Multi-turn context, workspace   │
├──────────────────────────────────────────┤
│ Layer 4  Planning & Multi-Agent          │
│          Execution                       │
│          PipelineAgent → Specialist/     │
│          Quality/Synthesis              │
│          (+ calibrated/ strategy stack)  │
├──────────────────────────────────────────┤
│ Layer 3  Service Orchestration           │
│          required_capabilities →         │
│          health check → auto-start       │
├──────────────────────────────────────────┤
│ Layer 2  Domain Workflows                │
│          generate → evaluate → score →   │
│          rank                            │
├──────────────────────────────────────────┤
│ Layer 1  Atomic Capabilities             │
│          Single-tool invocation +        │
│          result auto-writeback           │
├──────────────────────────────────────────┤
│ Layer 0  Tool Layer                      │
│          ToolSpec / Registry / Executor  │
└──────────────────────────────────────────┘
```

### 2.1 Layer 0 — Tool Layer

**Files**: `tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`

| File | Responsibility |
|------|---------------|
| `tools.py` | ~5,300 lines of `@tool` wrappers. Normalizes input, calls microservice HTTP endpoint, parses response. |
| `tool_specs.py` | Pydantic `ToolSpec` registry and output schemas. |
| `tool_registry.py` | Minimal name-based registry for LangChain-compatible tools. |
| `tool_executor.py` | `ToolResult` container; resolves tools, invokes via LangChain `.invoke`, normalizes results, appends trace records. |

### 2.2 Layer 1 — Atomic Capabilities

**Files**: `capabilities/base.py`

Replaces ~800 lines of manual `if tool_name == "..."` unpacking with a declarative mapping driven by `ToolSpec.output_model`.

**State contract**:

```python
tool_results: dict[str, Any]   # tool_name → normalized result dict
workflow_result: WorkflowResult  # final workflow output
```

Candidates live inside `WorkflowResult.all_candidates` / `WorkflowResult.best_candidate`. Adding a new tool no longer requires editing `state.py`.

**Note**: `capabilities/base.py` provides the `Capability` / `CapabilityRegistry` invocation layer, which validates outputs against `ToolSpec.output_model` and writes to `state["tool_results"]`. Workflows consume raw tool outputs directly or via `_state_writeback`; there is no separate declarative writeback registry.

### 2.3 Layer 2 — Domain Workflows

**Files**: `workflows/*.py`

Fixed multi-step pipelines for each RNA sub-domain. All 11 workflows inherit from `BaseDomainWorkflow`:

```python
class BaseDomainWorkflow(ABC, Generic[WorkflowInputT, WorkflowResultT]):
    @abstractmethod
    def generate_candidates(self, inp: WorkflowInputT) -> list[Candidate]: ...
    @abstractmethod
    def evaluate(self, candidate: Candidate) -> dict[str, Any]: ...
    @abstractmethod
    def score(self, metrics: dict[str, Any]) -> dict[str, float]: ...
```

| Workflow | File |
|----------|------|
| `MrnaSequenceScoringWorkflow` | `workflows/mrna_sequence_scoring.py` |
| `MrnaCdsDesignWorkflow` | `workflows/mrna_cds_design.py` |
| `FullLengthMrnaDesignWorkflow` | `workflows/full_length_mrna_design.py` |
| `RnaSmallMoleculeInteractionWorkflow` | `workflows/rna_small_molecule_interaction.py` |
| `SirnaDesignWorkflow` | `workflows/sirna_design.py` |
| `SgRnaDesignWorkflow` | `workflows/sgrna_design.py` |
| `RnaSecondaryStructureDesignWorkflow` | `workflows/rna_secondary_structure_design.py` |
| `RnaTertiaryStructureDesignWorkflow` | `workflows/rna_tertiary_structure_design.py` |
| `RnaAptamerDesignWorkflow` | `workflows/rna_aptamer_design.py` |
| `IresPredictionWorkflow` | `workflows/ires_prediction.py` |
| `AsoTargetScreeningWorkflow` | `workflows/aso_target_screening.py` |

The `SpecialistAgent` (Layer 4) invokes a workflow just like a single tool. The caller (CLI menu, `--workflow`, or a `PipelinePlan`) decides **what** to do; the Workflow decides **how** to do it well.

### 2.4 Layer 3 — Service Orchestration

**Files**: `services/service_manager.py`

Maps each workflow's `required_capabilities` to the local HTTP microservices it needs (`CAPABILITY_SERVICE_MAP`), probes `/health`, and auto-starts missing services before execution. `AgentRunner` enables this pre-flight (`auto_start_services=True`) on every workflow it owns; direct workflow instantiation defaults to `auto_start_services=False`. When pre-flight fails, the workflow returns `WorkflowResult(success=False, ...)` with actionable error messages instead of crashing mid-execution.

### 2.5 Layer 4 — Planning & Multi-Agent Execution

**Files**: `pipeline/models.py`, `agents/*.py`, `calibrated/` (additive strategy stack), `llm_config.py` (LLM client factory)

```python
class PipelinePlan(BaseModel):
    plan_id: str
    nodes: list[PipelineNode]   # workflow + static_params + input_bindings
    edges: list[PipelineEdge]   # execution dependencies
```

> **Binding/edge rule**: `input_bindings` can only reference node outputs that are reachable as ancestors through explicit `edges`. A data binding alone does **not** create an execution dependency. If node B consumes `$A.some_field`, the plan must also include `PipelineEdge(source="A", target="B")`.

**Routing is explicit and form-driven**. There is no planner and no natural-language parameter extraction: callers provide `explicit_workflow` and structured `form_params`:

```python
# CLI / API path
runner.run_form(
    form_params={"rna_sequence": "AUGC", "smiles": "CCO"},
    session_id="...",
    explicit_workflow="rna_small_molecule_interaction",
)

runner.stream_form(
    form_params={...},
    session_id="...",
    explicit_workflow="rna_small_molecule_interaction",
)
```

When `explicit_workflow` is set, the runner builds a single-node `PipelinePlan` directly from `state["_form_params"]` and records `_routing_method = "explicit"`.

The multi-agent execution layer is the stateful bridge between the entry points and the lower layers:

| Agent | Responsibility |
|-------|---------------|
| `PipelineAgent` | Deterministic scheduling of `PipelinePlan` nodes, input binding resolution, critical-failure handling, and final synthesis delegation. Does **not** call LLMs. |
| `SpecialistAgent` | Per-workflow strategy: runs the workflow, invokes `QualityAgent`, decides retry/adjust/abort, and returns `AgentResult`. |
| `QualityAgent` | Unified quality review using workflow-specific `QualityProfile`. Outputs an advisory `QualityReport`; it neither triggers retry on its own nor can it flip a successful run to failed. |
| `SynthesisAgent` | Passes through single-node results; for multi-node pipelines, generates a concise synthesis report. |

```python
# Simplified flow
plan = PipelinePlan(nodes=[...], edges=[...])   # built explicitly (single- or multi-node)
result = pipeline_agent.execute(plan, state)
# PipelineAgent delegates each node to a SpecialistAgent, which may consult QualityAgent.
```

#### 2.5.1 Calibrated Layer-4 strategy stack (`agent_core/calibrated/`)

Calibrated strategy package (empirical self-model + dual gating). All components are deterministic (no LLM):

| Module | Component | Responsibility |
|--------|-----------|----------------|
| `models.py` | — | Shared Pydantic schemas: `CapabilityRecord` ((oracle, task_type, target_family) → CASF four-capability cells with grade/confidence/evidence), `PlannedAction`, `GateDecision`, `Claim`/`ClaimVerdict`, `CampaignRecord`, `AuditEvent`. |
| `self_model.py` | `SelfModel` | Core state: query (exact → transferred with decayed confidence → unprofiled) and update; every update emits an audit event. |
| `audit_trail.py` | `AuditTrail` | Append-only JSONL event log (`self_model_update` / `profiling_run` / `gate_decision` / `claim_verdict` / `budget_event`). |
| `profiling_metrics.py` | Anchor profiling thresholds + metric helpers shared by the profiling campaigns (`AUROC_PASS`, `RHO_PASS`, bootstrap AUROC CI). |
| `decision_gate.py` | `DecisionGate` | Pre-action gating: `ranking_objective` requires verified ranking, `screening_evaluation` verified screening, `docking_validation` verified docking; failed → reject (with substitute), unprofiled → require_profiling, transferred → downgrade. |
| `claim_gate.py` | `ClaimGate` | Pre-publication gating under the uniform "no claim without a verified basis" rule: comparative claims (ranking/screening) must declare a capability-checked basis; claims pass only with verified dependencies; transferred-verified downgrades one step along the scope ladder; failed/unprofiled → reject. |
| `runtime.py` | `CalibratedRuntime` | Production CapGate integration (§2.5.3): tool-call audit trail + DecisionGate choke point keyed to the calling workflow's task type. |

#### 2.5.2 Relationship between the seven-layer architecture and the Calibrated Agent stack

- **L0–L3 are the execution base.** The tool/capability/workflow/service-orchestration layers are exactly what the calibrated stack drives; the profiling campaigns measure oracles through the same L0–L2 toolchain.
- **L5/L6 are unchanged.** Session/workspace management and the `AgentRunner` / CLI / FastAPI entry points are unaffected by the strategy layer.
- **L4 strategy.** The `calibrated/` package (`SelfModel` / `DecisionGate` / `ClaimGate` / `AuditTrail` / `CalibratedRuntime`) coexists with the classic four agents (`Pipeline` / `Specialist` / `Quality` / `Synthesis`), which are the production execution path.
- **Retired from the old L4**: `LLMPlanner` (routing has been explicit-only in production), the `CapabilityProfiler`/`ExperimentPlanner`/`CalibratedCampaignRunner`/`CaseMemory` experiment stack (superseded by the direct profiling-campaign protocol; the E4 memory strategy was NO-GO — DECISIONS.md (c)), and the entire BMC framework (`CoordinatorAgent` + coordinators, removed 2026-08-18 after triple falsification — DECISIONS.md (a), (m)).

#### 2.5.3 Platform CapGate runtime — production integration (2026-08-18)

`agent_core/calibrated/runtime.py` (`CalibratedRuntime`) connects the calibrated stack to the platform's execution path; `AgentRunner` configures it at construction from `RNADA_CAPGATE` (`off` | `advisory` | `enforce`, default **enforce**):

- **Full-pipeline auditability**: `ToolExecutor.run_tool` records *every* tool call (name, kwargs summary, success, elapsed, error type) to the runtime's append-only `AuditTrail` (default `workspace/audit/platform_audit.jsonl`, override `RNADA_CAPGATE_AUDIT`). Audit writes are best-effort and can never fail a run.
- **DecisionGate at the tool choke point**: managed oracle tools are reviewed against the SelfModel before invocation, **keyed to the calling workflow's task context** — every workflow declares `task_type` (the flagship three match their SelfModel keys exactly), `BaseDomainWorkflow` execution paths set it via `task_context(...)` (aptamer's thread-pool evaluators receive it via `contextvars.copy_context().run`), and reviews fall back to the oracle's registered default only outside a workflow. The managed set is **derived from the ToolSpec oracle ontology** (`tool_interface.py` `ToolKind`/`OracleDescriptor`; `runtime.MANAGED_ORACLE_TOOLS` + `ORACLE_GOVERNANCE`): the **9 enforce** oracles (EGARPS/Protenix/RhoFold aptamer oracles, both GEMORNA UTR predictors, RNAsmol, plus the three E16–E18 graded oracles — IRESfinder screening failed on 3 upstream families, GerNA-Bind screening failed at chance level, RNASTOP screening verified but ranking failed) are blocked under `enforce` when their evidentiary basis is absent (`failed`, or `unprofiled` with no donor) — the call returns a `GatedActionError` `ToolResult` and workflows' existing fallbacks keep runs alive (oracle components default to 0.0 for all candidates equally). The **2 remaining pending** oracles (CRGPT handle score, CRISOT off-target score — no labeled anchor set on disk, DECISIONS.md (l)) are reviewed and audited like enforced ones but never blocked. Profiling and report-only callers wrap calls in `oracle_use("scoring_annotation")`.
- **Tool inventory manifest** (`agent_core/tool_inventory.py`, `python -m agent_core.tool_inventory`): every tool's kind, oracle descriptor, backing microservice, real callers (AST-scanned) and status (production / experiment_only / reserved / demo) in one generated JSON (`experiments/results/tool_inventory.json`) — the supplementary tool table; completeness enforced by `tests/test_tool_ontology.py`.
- **Packaged default SelfModel**: `agent_core/calibrated/default_self_model.json` (generator `experiments/build_default_self_model.py`) bundles the frozen E1 (aptamer structure oracles: 36 failed screening/ranking cells + docking), E7 (GEMORNA 5′UTR MRL verified on 3 families) and RNAsmol boundary (verified in-distribution, failed short-aptamer OOD) verdicts — so production gating reflects the published profiling results from the first run.
- **ClaimGate in synthesis**: `SynthesisAgent` extracts headline claims of multi-node reports (the only LLM step), adjudicates them deterministically, and appends a "Gated claims" section (pass / downgraded wording / rejected with reason); extraction failure leaves the report unchanged and is audited.
- **Conservative transfer** (`SelfModel.query`): a never-profiled (oracle, task) family inherits the donors' **worst** grade per capability — a failed family poisons the transfer, so family choice cannot cherry-pick a pass.

### 2.6 Layer 5 — Session & Workspace

**Files**: `session_memory.py`, `workspace_manager.py`, `file_manager.py`

| File | Class | Description |
|------|-------|-------------|
| `session_memory.py` | `SessionMemory` | In-memory dict store. Swappable for Redis/SQLite. |
| `workspace_manager.py` | `WorkspaceManager` | Session-scoped directory management |
| `file_manager.py` | `save_sequence`, `read_sequence`, etc. | Workspace file I/O helpers |

### 2.7 Layer 6 — Entry Points

**Files**: `runner.py`, `workflow_api/`, `cli/`

`AgentRunner` (`agent_core/runner.py`) is the unified façade:

```python
class AgentRunner:
    def run_form(
        self,
        form_params: dict[str, Any],
        *,
        session_id: str,
        explicit_workflow: str,
        user_text: str = "",
        state: Optional[AgentState] = None,
    ) -> AgentState: ...

    def stream_form(
        self,
        form_params: dict[str, Any],
        *,
        session_id: str,
        explicit_workflow: str,
        user_text: str = "",
    ) -> Iterator[dict[str, Any]]: ...
```

Both FastAPI (`workflow_api/app.py`) and CLI (`cli/*.py`) go through `AgentRunner`.

**CLI orchestration** (`cli/`)

| File | Role |
|------|------|
| `cli/form_chat.py` | Interactive TUI entry point: resource check → workflow multi-select → microservice startup → multi-turn form |
| `cli/resource_checker.py` | GPU / RAM / CPU pre-flight checks via `nvidia-smi` and `psutil` |
| `cli/service_orchestrator.py` | Derives each workflow's microservice dependencies from its `required_capabilities`, handles health polling and deduplicated startup across multiple workflows |

---

## 3. Core Modules

### 3.1 `agent_core/state.py` — AgentState

`AgentState` is a `TypedDict` shared across the execution pipeline. Fields declared in `agent_core/state.py` are listed below; additional keys are set at runtime by `AgentRunner`.

- User / session: `messages`, `current_task`, `user_text`, `session_id`, `workspace_files`, `input_sequence`, `candidate_sequence`
- Execution control: `retry_count`, `max_retries`, `tool_results`, `workflow_result`, `final_report`, `pipeline_result`
- Planning / execution metadata: `_execution_plan`, `_execution_log`, `_plan_executed`
- Critic/quality metadata: `_quality_review_enabled`, `_quality_auto_retry`, `_diagnosis_history`, `_quality_review_error`, `_parameter_overrides`
- Multi-turn / form state: `_previous_workflow_result`, `_last_workflow_params`, `_last_workflow_target`, `_workflow_result_history`, `_form_params`, `_last_form_params`, `_last_form_params_by_workflow`, `_user_explicit_params`
- Runtime-only keys set by `AgentRunner` (not declared in `AgentState` TypedDict): `_routing_method`

### 3.2 `agent_core/tools.py` — Tool Wrappers

~5,300 lines of `@tool` wrappers. The **single source of truth** for HTTP calls to microservices.

### 3.3 `agent_core/tool_specs.py` — Output Schemas & ToolSpec Registry

Pydantic `ToolSpec` registry and output schemas (`BlastnSearchOutput`, `ViennaFoldOutput`, etc.).

### 3.4 `agent_core/tool_registry.py` — Tool Registry

Minimal name-based registry for LangChain-compatible tools.

| Symbol | Description |
|--------|-------------|
| `ToolNotRegisteredError` | Custom `KeyError` |
| `ToolRegistry` | Mutable mapping wrapper |
| `.register(tool, *, name=None)` | Register by name |
| `.get(name) -> Any` | Lookup or raise |
| `.has(name) -> bool` | Membership test |
| `.list_names() -> list[str]` | Sorted names |

### 3.5 `agent_core/tool_executor.py` — Tool Execution & Tracing

| Symbol | Description |
|--------|-------------|
| `ToolResult` | Normalized result container (success, output, error, elapsed_time) |
| `build_default_tool_registry()` | Populate from `ALL_LANGCHAIN_AGENT_TOOLS` |
| `ToolExecutor` | Main dispatcher |
| `.run_tool(tool_name, **kwargs) -> ToolResult` | Invoke with success/error handling and timing |
| `.run_tool_for_workflow(...)` | Runs `.run_tool`, then builds a `ToolCallRecord` |

### 3.6 `agent_core/workflow_models.py` — Serializable Workflow Models

| Class | Key Fields |
|---|---|
| `ToolCallRecord` | `step_name`, `tool_name`, `input_summary`, `output_summary`, `success`, `error`, `elapsed_time` |
| `Candidate` | `id` (UUID), `sequence`, `sequence_type`, `source`, `scores`, `metadata`, `tool_records`, `rank`, `status` |
| `TaskState` | `task_id`, `task_type`, `candidates`, `best_candidate`, `logs`, `status` |
| `WorkflowResult` | `success`, `task_id`, `best_candidate`, `all_candidates`, `summary`, `errors`, `trace`, `created_at`, `completed_at`, `public_summary`, `run_artifact_dir`, `run_result_json_path` |

### 3.7 `agent_core/sequence_utils.py` — Shared Sequence Utilities

| Function | Returns | Description |
|---|---|---|
| `normalize_rna_sequence(raw)` | Clean AUGC string | Strips FASTA headers, uppercases, T→U, drops non-AUGC |
| `compute_gc_content(normalized_seq)` | 5 GC metrics | GC metrics for normalized input |
| `extract_dot_bracket(raw)` | Clean structure string | Skips FASTA headers and empty lines |
| `validate_dot_bracket(struct)` | Raises `ValueError` | Ensures only `.()[]{}<>` characters |
| `compute_dot_bracket_unpaired_fraction(struct)` | 3 fields | Validates first, then computes fraction of dots |
| `compute_u_content(normalized_seq)` | 3 fields | U fraction metrics |

---

## 4. Routing Strategy

Routing is **explicit-only**: every run selects its workflow(s) up front. There is no automatic router and no LLM-driven planner.

### 4.1 Explicit Workflow Selection

`AgentRunner.run_form()` and `.stream_form()` require an `explicit_workflow` argument. The CLI (`cli/form_chat.py`) presents an interactive TUI menu for the user to select one or more workflows; on each turn it renders a structured form for the active workflow and invokes `run_form()` with the validated parameters. Multi-node runs pass a `PipelinePlan` JSON via `--pipeline-file`.

### 4.2 LLM Touchpoints

LLM calls exist only at two advisory points, both built via `agent_core/llm_config.py` (`get_llm_for_provider` / `get_deepseek_llm`; DeepSeek default, OpenAI/Anthropic/DashScope/Gemini optional — all via OpenAI-compatible endpoints):

| Touchpoint | When | Temperature |
|------------|------|-------------|
| `QualityAgent.review()` | Once per reviewed workflow run (advisory; see §4.4) | 0.2 |
| `SynthesisAgent` | Once per multi-node pipeline | 0.3 |

Both agents accept an injectable `llm`; with `llm=None` the DeepSeek client is built lazily on first use. Everything else — routing, retry gating — is rule-based, so a run without any API key still executes deterministically end to end.

### 4.3 Execution Pipeline

```
User Input ──→ explicit_workflow (CLI pick / --workflow / --pipeline-file)
                          │
                          ↓
                    PipelinePlan ──→ PipelineAgent
                                     ↓                 ↓
                            SpecialistAgent  ←→  QualityAgent (advisory)
                                     ↓
                            BaseDomainWorkflow
                                     ↓
                            SynthesisAgent ──→ Final Report
```

`AgentRunner.run_form()` or `.stream_form()` is the single entry point. `PipelineAgent.execute()` drives the loop internally; each node is executed by a `SpecialistAgent`, which consults `QualityAgent`.

### 4.4 Retry Logic

- **Quality review**: `QualityAgent.review(result, quality_profile, state)` returns a `QualityReport` with `action` in `{"pass", "retry_with_adjustments", "retry_with_alternative", "abort"}` and optional `parameter_overrides`.
- **Hard-failure retry**: the single authority is `WorkflowResult.is_hard_failure` (`success=False`, empty candidates, tool errors) — a hard failure overrides any advisory report and forces the retry path.
- **Advisory reports never destroy success**: an LLM-chosen `abort` is recorded as advice only, and if the LLM review call itself fails the report is marked `review_unavailable` (zero-confidence `pass`) with the error retained in `state["_quality_review_error"]` for audit. Neither path can flip a successful run to failed.
- **Advisory-first default**: `quality_auto_retry=False` means `QualityAgent` always records a diagnosis but `SpecialistAgent` only retries on hard failures. Soft quality suggestions are surfaced in `final_report` for user confirmation.
- **Partial rerun optimization**: If overrides only affect `quality_profile.evaluator_only_params`, the `SpecialistAgent` tries `workflow.partial_rerun()` first — re-evaluates existing candidates without regeneration.
- **Workflow-level retry**: If partial rerun is unsupported or fails, the `SpecialistAgent` applies `parameter_overrides` and re-runs the entire workflow.
- **No quality review for deterministic workflows**: `mrna_sequence_scoring`, `rna_small_molecule_interaction`, `aso_target_screening` intentionally have empty `evaluation_dimensions` — retry cannot improve fixed-input results.

---

## 5. Workflow–Quality Co-Design

### 5.1 Why this matters

The entry point is a **scheduler**, the Workflow is the **engine**, and `QualityAgent` is the **quality gate**. A mismatched Workflow–`QualityProfile` pair will either never finish (thresholds too strict) or produce garbage (review too loose).

| Scenario | Symptom | Root cause |
|----------|---------|------------|
| Quality thresholds reject every candidate | Infinite retry loop | Thresholds stricter than tool can achieve |
| Quality review accepts everything | Low-quality output | Only checks "result exists" |
| Quality dimensions mismatch Workflow scoring | User confusion | No joint optimization |

### 5.2 Design principle

When a `QualityProfile` *is* used, its pass/fail criteria must be derivable from the Workflow's scoring function. If the Workflow scoring changes, the profile must be updated in the same PR. They share a **joint objective**.

### 5.3 Task-type-specific QualityProfile mapping

| Workflow | QualityProfile | Strategy |
|----------|----------------|----------|
| `mrna_cds_design` | `MRNA_CDS_QUALITY_PROFILE` | LLM-driven review (CAI, MFE, GC, RNASTOP) |
| `sirna_design` | `SIRNA_QUALITY_PROFILE` | Safety review: off-target, specificity, GC |
| `sgrna_design` | `SGRNA_QUALITY_PROFILE` | Quality review: `nn_score` and on-target metrics |
| `rna_aptamer_design` | `RNA_APTAMER_QUALITY_PROFILE` | Reference-point-aware quality review |
| `ires_prediction` | `IRES_QUALITY_PROFILE` | IRES activity and structure fidelity |
| `rna_secondary_structure_design` | `RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE` | Structure fidelity vs target |
| `rna_tertiary_structure_design` | `RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE` | pLDDT / structural confidence |
| `full_length_mrna_design` | `FULL_LENGTH_MRNA_QUALITY_PROFILE` | Full-length objective-space review |
| `mrna_sequence_scoring` | `MRNA_SEQUENCE_SCORING_QUALITY_PROFILE` | Deterministic; empty review dimensions |
| `aso_target_screening` | `ASO_TARGET_SCREENING_QUALITY_PROFILE` | Deterministic; empty review dimensions |
| `rna_small_molecule_interaction` | `RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE` | Deterministic; empty review dimensions |

### 5.4 QualityProfile registration

```python
# agent_core/quality_profiles/__init__.py
QUALITY_PROFILES: dict[str, QualityProfile] = {
    "mrna_cds_design": MRNA_CDS_QUALITY_PROFILE,
    "sirna_design": SIRNA_QUALITY_PROFILE,
    "sgrna_design": SGRNA_QUALITY_PROFILE,
    "ires_prediction": IRES_QUALITY_PROFILE,
    "rna_secondary_structure_design": RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
    "rna_tertiary_structure_design": RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE,
    "full_length_mrna_design": FULL_LENGTH_MRNA_QUALITY_PROFILE,
    "rna_aptamer_design": RNA_APTAMER_QUALITY_PROFILE,
    # Deterministic workflows: empty evaluation_dimensions bypass LLM review.
    "mrna_sequence_scoring": MRNA_SEQUENCE_SCORING_QUALITY_PROFILE,
    "aso_target_screening": ASO_TARGET_SCREENING_QUALITY_PROFILE,
    "rna_small_molecule_interaction": RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
}
```

### 5.5 Workflow–Quality design checklist

When adding a new task type:
1. [ ] Scoring function is explicit and documented.
2. [ ] `QualityProfile.evaluation_dimensions` and thresholds are derivable from the scoring function.
3. [ ] `QualityProfile.adjustable_params` lists what can change on retry.
4. [ ] Step-level failures handled separately from workflow-level quality failures.
5. [ ] Profile registered in `QUALITY_PROFILES` and consumed by `SpecialistAgent`.

---

## 6. How to Extend

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full new-tool procedure, interface lock annotations, and commit conventions.

Quick reference:

**New tool**: implement in `tools.py` → add spec in `tool_specs.py` → register in `ALL_LANGCHAIN_AGENT_TOOLS` → add microservice in `microservices/<tool>_service/`.

**New workflow**: build module inheriting `BaseDomainWorkflow` → export from `workflows/__init__.py` → register in `AgentRunner.workflow_registry` (`agent_core/runner.py`) → add `QualityProfile` in `agent_core/quality_profiles/<workflow>.py` and register it in `agent_core/quality_profiles/__init__.py` if quality review is needed → add to `cli/form_chat.py::_WORKFLOW_LIST` and declare `required_capabilities` on the workflow class → add tests.
