# Architecture & Core Interfaces

> **Scope**: design principles, the five-layer architecture, core module APIs, routing strategy, and workflow–critic co-design.
> **Last updated**: 2026-06-01

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Five-Layer Architecture](#2-five-layer-architecture)
3. [Core Modules](#3-core-modules)
4. [Routing Strategy](#4-routing-strategy)
5. [Workflow–Critic Co-Design](#5-workflowcritic-co-design)
6. [Bounded Multi-Module Coordination (BMC)](#6-bounded-multi-module-coordination-bmc)
7. [How to Extend](#7-how-to-extend)

---

## 1. Design Principles

### 1.1 Single Source of Truth for HTTP

`agent_core/tools.py` is the **only** module that calls `requests.post` to microservice ports. Workflow-layer tools delegate to the LangChain `@tool` wrappers via `.invoke()`. This prevents duplicate HTTP logic and path-resolution bugs.

### 1.2 Shared Sequence Utilities

`agent_core/sequence_utils.py` contains `normalize_rna_sequence()`, `compute_gc_content()`, `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()`. Both agent-core scoring modules and microservices import from here so that local fallbacks and server results never drift apart.

### 1.3 Complete State Tracking

The agent state tracks **granular metric fields** rather than single scalar values:

- GC content: 5 fields (`sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`)
- Dot-bracket unpaired fraction: 3 fields (`dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`)

### 1.4 Decoupled Spec → Registry → Runtime → Executor

```
tool_interface.py (specs)
    ↓
tool_registry.py (name→callable lookup)
    ↓
tool_runtime.py (primitives: subprocess, timeout, error handling)
    ↓
tool_executor.py (dispatch + tracing)
```

---

## 2. Five-Layer Architecture

> **Status**: Implemented.  
> **Goal**: a layered system where deterministic routing and LLM-driven routing can coexist, and where the UI path and the Workflow API path share the same domain logic.

```
┌──────────────────────────────────────────┐
│ Layer 5  Presentation                    │
│          FastAPI / CLI                   │
├──────────────────────────────────────────┤
│ Layer 4  Session & Memory                │
│          Multi-turn context, workspace   │
│          files, candidate history        │
├──────────────────────────────────────────┤
│ Layer 3  Planning & Control              │
│          Task decomposition → execution  │
│          plan → dynamic routing          │
├──────────────────────────────────────────┤
│ Layer 2  Domain Workflows                │
│          mRNA / siRNA / CRISPR pipelines │
│          generate → evaluate → score →   │
│          rank                            │
├──────────────────────────────────────────┤
│ Layer 1  Atomic Capabilities             │
│          Single-tool invocation +        │
│          result auto-writeback           │
├──────────────────────────────────────────┤
│ Layer 0  Tool Layer (existing)           │
│          ToolSpec / Registry / Executor  │
└──────────────────────────────────────────┘
```

**Design principles**

1. **Layer 0 is frozen**. The tool wrappers, specs, registry, and executor are already well-designed. No structural changes.
2. **Bottom layers provide services to upper layers only**. No skip-level calls (e.g., Layer 3 should not call `tools.py` directly).
3. **Each layer has a single stable interface**. If you replace the implementation behind that interface, callers above do not change.
4. **Planner is backend-pluggable**. The architecture supports swapping planner implementations without touching Layer 2 or below.

---

### 2.1 Layer 0 — Tool Layer

**Files**: `tools.py`, `tool_specs.py`, `tool_registry.py`, `tool_executor.py`, `tool_runtime.py`

**Responsibility**: wrap third-party bioinformatics tools as HTTP-callable, schema-validated units.

- `tools.py`: ~6,450 lines of `@tool` wrappers. Each wrapper normalizes input, calls a microservice HTTP endpoint, parses the response, and returns a structured dict.
- `tool_specs.py`: Pydantic `ToolSpec` registry and output schemas. Defines identity, transport, capabilities, input/output models, and status for every tool.
- `tool_registry.py`: Minimal name-based registry for LangChain-compatible tools.
- `tool_executor.py`: Resolves tools from a `ToolRegistry`, invokes them via LangChain `.invoke`, normalizes results, and optionally appends trace records.
- `tool_runtime.py`: Execution primitives (`ToolResult`, `CommandExecutionOutput`, subprocess runner with timeout).

---

### 2.2 Layer 1 — Atomic Capabilities

**Files**: `capabilities/base.py`, `capabilities/writebacks.py`

**Responsibility**: turn a single tool invocation into a typed, self-describing sub-task result, and write it back to state automatically.

**Why this layer exists**: it replaces ~800 lines of manual `if tool_name == "..."` result unpacking with a declarative mapping driven by `ToolSpec.output_model`.

**Implementation**

| File | Role |
|------|------|
| `capabilities/base.py` | `Capability` dataclass + `CapabilityRegistry`; wraps `ToolExecutor` and validates `output_model` |
| `capabilities/writebacks.py` | Declarative `STANDARD_WRITEBACKS` mapping (30+ tools); replaces the old manual if-elif chain |

**State contract**: instead of 80+ flat fields, the agent state stores:

```python
tool_results: dict[str, Any]   # tool_name → normalized result dict
candidates: list[Candidate]    # from workflow_models.py
```

Adding a new tool no longer requires editing `state.py`. You register its `Capability` and add a writeback entry in `capabilities/writebacks.py`.

---

### 2.3 Layer 2 — Domain Workflows

**Files**: `workflows/*.py`

**Responsibility**: fixed multi-step pipelines for each RNA sub-domain (mRNA design, siRNA design, CRISPR evaluation, …). Each workflow generates candidates, evaluates them with capabilities, scores, and ranks.

**Base abstraction**

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
            metrics = self.evaluate(candidate)      # calls Layer 1 capabilities
            candidate.scores = self.score(metrics)   # domain-specific scoring
            candidate.status = "evaluated"
        return self.rank_and_format(candidates)
```

**Implemented workflows**

| Workflow | File | Status |
|----------|------|--------|
| `MrnaSequenceScoringWorkflow` | `workflows/mrna_sequence_scoring.py` | ✅ Available |
| `MrnaCdsDesignWorkflow` | `workflows/mrna_cds_design.py` | ✅ Available |
| `FullLengthMrnaDesignWorkflow` | `workflows/full_length_mrna_design.py` | ✅ Available |
| `RnaSmallMoleculeInteractionWorkflow` | `workflows/rna_small_molecule_interaction.py` | ✅ Available |
| `SirnaDesignWorkflow` | `workflows/sirna_design.py` | ✅ Available |
| `SgRnaDesignWorkflow` | `workflows/sgrna_design.py` | ✅ Available |
| `RnaSecondaryStructureDesignWorkflow` | `workflows/rna_secondary_structure_design.py` | ✅ Available |
| `RnaTertiaryStructureDesignWorkflow` | `workflows/rna_tertiary_structure_design.py` | ✅ Available |
| `RnaAptamerDesignWorkflow` | `workflows/rna_aptamer_design.py` | ✅ Available |
| `IresPredictionWorkflow` | `workflows/ires_prediction.py` | ✅ Available |
| `AsoTargetScreeningWorkflow` | `workflows/aso_target_screening.py` | ✅ Available |

**Workflow as a compound capability**

The `ExecutionController` (Layer 3) can invoke a workflow just like a single tool. From the Planner's perspective, calling `workflow_mrna_cds_design` is identical to calling `predict_rna_secondary_structure` — both are a single `PlanStep`. The Planner decides **what** to do; the Workflow decides **how** to do it well.

---

### 2.4 Layer 3 — Planning & Control

**Files**: `planning/base.py`, `planning/llm_planner.py`, `planning/factory.py`

**Responsibility**: convert a user's natural language request into an `ExecutionPlan` (a linear sequence of capabilities/workflows), then dispatch and monitor execution.

**Base abstraction**

```python
class Planner(ABC):
    @abstractmethod
    def plan(self, user_text: str, context: AgentContext) -> ExecutionPlan: ...

class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
    max_retries: int = 2
    fallback_on_error: Literal["abort", "skip", "retry_with_alternative"] = "retry_with_alternative"
```

**Backend implementations**

| Backend | Class | Status |
|---------|-------|--------|
| LLM-driven | `LLMPlanner` | ✅ Implemented (DeepSeek-powered) |

**Execution control**

`ExecutionController` (in `planning/base.py`) is the bridge between Planner and lower layers. It is **stateful** and executes the plan step by step:

```python
class ExecutionController:
    def execute(self, plan: ExecutionPlan, state: AgentState) -> AgentState:
        for step in plan.steps:
            inputs = self._resolve_bindings(step.input_binding, state)
            if step.type == "capability":
                result = self.capabilities.get(step.target).invoke(inputs)
            else:  # workflow
                result = self.workflows.get(step.target).run(inputs)
            self._write_result(state, step.output_key, result)
            ...
```

This keeps the planner **stateless** and **pure** (input → plan), which makes testing and swapping backends trivial.

---

### 2.5 Layer 4 — Session & Memory

**Files**: `session_memory.py`, `workspace_manager.py`, `file_manager.py`

**Responsibility**: persist context across turns.

| File | Class | Description |
|------|-------|-------------|
| `session_memory.py` | `SessionMemory` | In-memory dict store (`load` / `save`). Can be swapped for Redis/SQLite without changing `AgentRunner`. |
| `workspace_manager.py` | `WorkspaceManager` | Session-scoped directory management |
| `file_manager.py` | `save_sequence`, `read_sequence`, etc. | Workspace file I/O helpers |

RNA design is iterative. A typical session looks like:
1. "Design an mRNA for GFP"
2. "The MFE is too high, give me a more stable one"
3. "Now run BLAST on the best candidate"

Without Layer 4, turn 3 does not know which candidate was chosen in turn 1.

---

### 2.6 Layer 5 — Presentation

**Files**: `runner.py`, `workflow_api/`, `cli/`

**Responsibility**: human-facing UI and programmatic API.

`AgentRunner` (`agent_core/runner.py`) is the unified façade. All presentation layers go through it:

```python
class AgentRunner:
    def __init__(self, planner: Planner, executor: ToolExecutor, *, session_memory=None):
        self.planner = planner
        self.executor = executor
        self.capability_registry = build_default_capability_registry(executor)
        self.workflow_registry = {
            "mrna_cds_design": MrnaCdsDesignWorkflow(self.capability_registry),
            "rna_small_molecule_interaction": RnaSmallMoleculeInteractionWorkflow(self.capability_registry),
            ...
        }
        self.controller = ExecutionController(...)

    def run(self, user_input: str, session_id: str = "") -> dict: ...
    def stream(self, user_input: str, session_id: str = "") -> Iterator[dict]: ...
```

| Layer | File | Uses `AgentRunner` |
|-------|------|-------------------|
| FastAPI API | `workflow_api/app.py` | ✅ `run()` / `stream()` |
| CLI | `cli/*.py` | ✅ via `workflow_api/` handlers |

---

## 3. Core Modules

### 3.1 `agent_core/state.py` — AgentState

`AgentState` is a `TypedDict` shared across the execution pipeline. It defines typed fields tracking outputs from every locked tool integration.

**Key structural observations**

- **INTERFACE LOCK** blocks group fields by tool. Each lock lists the full set of files that must be updated in sync.
- Generic fields: `messages`, `current_task`, `workspace_files`, `input_sequence`, `candidate_sequence`, `route`, `next_action`, `critic_verdict`, `final_report`, `retry_count`, `max_retries`
- Modern storage: `tool_results: dict[str, Any]` and `candidates: list[Candidate]` reduce the need for flat fields.

**Public factory**

```python
def default_state(user_text: str) -> AgentState: ...
```

### 3.2 `agent_core/tools.py` — Tool Wrappers

~6,450 lines of `@tool` wrappers. Each wrapper:

1. Normalizes input (often via `file_manager.py` or `sequence_utils.py`).
2. Calls a microservice HTTP endpoint via `requests.post`.
3. Parses the response.
4. Returns a structured dict.

This is the **single source of truth** for HTTP calls to the microservices.

### 3.3 `agent_core/tool_specs.py` — Output Schemas & ToolSpec Registry

Pydantic `ToolSpec` registry and output schemas (`BlastnSearchOutput`, `ViennaFoldOutput`, `EvitarDesignOutput`, etc.). Defines identity, transport, capabilities, input/output models, and status for every tool.

### 3.4 `agent_core/tool_registry.py` — Tool Registry

Minimal name-based registry for LangChain-compatible tools.

| Symbol | Description |
|--------|-------------|
| `ToolNotRegisteredError` | Custom `KeyError` for missing lookups |
| `ToolRegistry` | Mutable mapping wrapper |
| `.register(tool, *, name=None)` | Register by explicit name or `tool.name` |
| `.register_many(tools)` | Bulk registration |
| `.get(name) -> Any` | Lookup or raise `ToolNotRegisteredError` |
| `.has(name) -> bool` | Membership test |
| `.list_names() -> list[str]` | Alphabetically sorted names |

### 3.5 `agent_core/tool_executor.py` — Tool Execution & Tracing

| Symbol | Description |
|--------|-------------|
| `build_default_tool_registry(*, include_demo=False) -> ToolRegistry` | Populate from `ALL_LANGCHAIN_AGENT_TOOLS` |
| `ToolExecutor` | Main dispatcher |
| `.run_tool(tool_name, **kwargs) -> ToolResult` | Invoke by name with success/error handling and timing |
| `.run_tool_for_workflow(...)` | Runs `.run_tool`, then builds a `ToolCallRecord` |

### 3.6 `agent_core/tool_runtime.py` — Execution Primitives

| Symbol | Description |
|--------|-------------|
| `ToolResult` | Normalized result container (success, output, error, elapsed_time) |
| `CommandExecutionOutput` | stdout / stderr / returncode wrapper |
| `run_subprocess_command(...)` | Subprocess runner with timeout and streaming |
| `run_python_function(...)` | In-process Python callable runner |

### 3.7 `agent_core/workflow_models.py` — Serializable Workflow Models

Pydantic models for iterative candidate-based agent runs.

| Class | Key Fields |
|---|---|
| `ToolCallRecord` | `step_name`, `tool_name`, `input_summary`, `output_summary`, `success`, `error`, `elapsed_time` |
| `Candidate` | `id` (auto UUID), `sequence`, `source`, `scores`, `metadata`, `tool_records`, `rank`, `status` |
| `TaskState` | `task_id`, `task_type`, `candidates`, `best_candidate`, `logs`, `status` |
| `WorkflowResult` | `success`, `best_candidate`, `all_candidates`, `summary`, `errors`, `trace` |

### 3.8 `agent_core/sequence_utils.py` — Shared Sequence Utilities

| Function | Returns | Description |
|---|---|---|
| `normalize_rna_sequence(raw: str) -> str` | Clean AUGC string | Strips FASTA headers, uppercases, T→U, drops non-AUGC |
| `compute_gc_content(normalized_seq: str) -> dict` | 5 GC metrics | GC metrics for already-normalized input |
| `extract_dot_bracket(raw: str) -> str` | Clean structure string | Skips FASTA headers and empty lines |
| `validate_dot_bracket(struct: str) -> None` | Raises `ValueError` | Ensures only `.()[]{}<>` characters |
| `compute_dot_bracket_unpaired_fraction(struct: str) -> dict` | 3 fields | Validates first, then computes fraction of dots |
| `compute_u_content(normalized_seq: str) -> dict` | 3 fields | U fraction metrics |

**Design principle**: these mirror the logic in `microservices/rna_sequence_metrics_service/main.py` so agent-core code never drifts from the microservice.

---

## 4. Routing Strategy

The agent uses a **two-tier routing strategy** that combines deterministic keyword matching with LLM-driven planning.

### 4.1 Tier 1: DeterministicRouter

`DeterministicRouter` (`planning/router.py`) handles ≥60% of common requests with **zero LLM calls**.

- Uses pre-compiled keyword/regex patterns (AND across groups, OR inside group).
- Supports **negative patterns** to avoid false matches.
- 11 ordered rules covering all major domains.
- Fallback heuristic: plain "mRNA"/"protein" requests without UTR keywords → `mrna_cds_design`.

| Rule # | Keywords | Routed Workflow |
|--------|----------|----------------|
| 1 | `全长mRNA`, `full.length.mRNA`, `5.UTR.*3.UTR` | `full_length_mrna_design` |
| 2 | `CDS`, `coding.sequence`, `lineardesign`, `codon.optimization` | `mrna_cds_design` |
| 3 | `siRNA`, `siRNA设计`, `Evitar` | `sirna_design` |
| 4 | `sgRNA`, `CRGPT`, `handle设计` | `sgrna_design` |
| 5 | `aptamer`, `适配体`, `ODesign`, `protein.target` | `rna_aptamer_design` |
| 6 | `二级结构`, `secondary.structure`, `RNAinverse`, `逆折叠` | `rna_secondary_structure_design` |
| 7 | `三级结构`, `tertiary.structure`, `RhoDesign`, `RiboDiffusion` | `rna_tertiary_structure_design` |
| 8 | `ASO`, `antisense`, `accessibility`, `可及性` | `aso_target_screening` |
| 9 | `IRES`, `IRESfinder` | `ires_prediction` |
| 10 | `小分子`, `small.molecule`, `GerNA-Bind`, `RNAsmol` | `rna_small_molecule_interaction` |
| 11 | `mRNA评分`, `sequence.scoring`, `codonw` | `mrna_sequence_scoring` |

### 4.2 Tier 2: LLM-Driven Routing

When `DeterministicRouter` fails to match, `LLMPlanner` (`planning/llm_planner.py`) takes over. The LLM receives a system prompt listing all available capabilities and workflows, then emits a structured JSON execution plan.

**Key features**

| Feature | Description |
|---------|-------------|
| **Default parameter conservatism** | System prompt explicitly instructs the LLM: "DEFAULT PARAMETERS ARE CAREFULLY TUNED — DO NOT CHANGE THEM LIGHTLY". Overrides only when user explicitly requests them. |
| **Capability filtering** | `_filter_capabilities_by_keywords()` ranks tools by relevance (name tokens ×3, task tags ×2, description ×1, domain boosts ×2.5) and truncates to `max_context_tools` (~20), reducing prompt length by ~50%. |
| **Robust JSON parsing** | Manual brace-matching parser handles markdown fences, trailing comments, and malformed JSON gracefully. |
| **Multi-provider support** | DeepSeek (default), OpenAI, Anthropic, Alibaba DashScope, Google Gemini — all via OpenAI-compatible endpoints. |

### 4.2 How this relates to clear tool interfaces

The project invests heavily in making tool interfaces self-describing:

- Every tool has a rich `ToolSpec` with `capabilities`, `limitations`, `task_tags`, `input_model`, and `output_model`.
- Every wrapper uses Pydantic `BaseModel` schemas with `Field(description=...)`.
- `tool_specs.py` could, in principle, be serialized into JSON and fed to an LLM as a function-calling schema.

**The tool layer is already "LLM-ready"**; the routing layer uses the LLM directly.

### 4.3 Execution Pipeline

```
User Input → LLMPlanner → ExecutionController
                                              ↓
                              ┌───────────────┴───────────────┐
                              ↓                               ↓
                    Capability / Workflow step           Critic check
                              ↓                               ↓
                         (retry loop)                      END
```

`AgentRunner.run()` or `AgentRunner.stream()` is the single entry point. `ExecutionController.execute()` drives the loop internally; there is no external graph framework.

### 4.4 Retry Logic

- **Plan-level retry**: `ExecutionController` checks `critic.should_retry()` after a workflow step. If retry is triggered and `retry_count < ExecutionPlan.max_retries`, the controller applies `parameter_overrides` and re-executes.
- **Partial rerun optimization**: If `parameter_overrides` only affect evaluator-only params (configured per-critic via `evaluator_only_params` and `param_to_evaluators`), the controller triggers `workflow.partial_rerun()` — re-evaluating existing candidates without regenerating them from scratch. This is a significant performance optimization.
- **Workflow-level retry**: If partial rerun fails or params affect generation, the controller re-runs the entire workflow from the first step.
- **Graceful degradation**: If LLM diagnosis fails, Critic automatically falls back to `action="abort"` and `should_retry=False` — the workflow never crashes.
- **No critic for some workflows**: ranking-only workflows (`mrna_sequence_scoring`, `rna_small_molecule_interaction`, `aso_target_screening`) intentionally have no critic — retrying does not improve candidates.

---

## 5. Workflow–Critic Co-Design

> **Scope**: why Workflow and Critic must be designed together, and how their coupling varies by task type.

### 5.1 Why this matters

The Planner is a **scheduler** — it decides the order of operations. The Workflow is the **engine** — it produces candidates. The Critic is the **quality gate** — it decides whether the output is acceptable.

A bad Planner might choose a sub-optimal sequence. A **mismatched Workflow–Critic pair will either never finish (critic too strict) or produce garbage (critic too loose)**.

| Scenario | Symptom | Root cause |
|----------|---------|------------|
| Critic rejects every candidate | Infinite retry loop | Critic thresholds are stricter than the design tool can physically achieve |
| Critic accepts everything | Low-quality output | Critic only checks "result exists" without biological relevance |
| Critic checks metrics Workflow does not optimize | User confusion | Workflow minimizes MFE; Critic demands high CAI — no joint optimization |

### 5.2 Design principle: critic must reflect the workflow's objective function

**Rule**: when a Critic *is* used, its pass/fail criteria should be derivable from the Workflow's scoring function.

If the Workflow scoring changes, the Critic must be updated in the same PR. They share a **joint objective**.

### 5.3 Task-type-specific critic strategies

#### mRNA CDS design — ✅ CRITIC (`MrnaCdsDesignLLMCritic`)

> **Rationale**: LLM-driven critic diagnoses output quality (CAI, MFE, GC, RNASTOP stability) and recommends parameter adjustments (`design_tool`, `lambda_value`, `model_type`, `cai_species`). Max 2 retries.

| Aspect | Design |
|--------|--------|
| Workflow | Generate N candidates → evaluate all (GC, fold, CAI) → score → rank |
| Critic strategy | **LLM-driven quality gate**: diagnoses issues and suggests parameter overrides |
| Retry action | Switch design tools, adjust λ, change species |

#### RNA-small molecule interaction — **NO CRITIC** (prediction-only)

> **Rationale**: this is a **prediction/scoring** task, not a generative design task. The inputs are fixed; re-running the same classifier produces identical results.

#### siRNA design (off-target safety-critical)

| Aspect | Design |
|--------|--------|
| Workflow | Design guides → off-target scan → specificity check |
| Critic strategy | **Absolute safety gate**: off-target count must be ≤ 3; specificity must exceed threshold. |
| Retry action | Relax design constraints (tighten BLAST identity + GC) and re-run; or abort with explicit safety warning |

#### sgRNA handle design (quality gate)

| Aspect | Design |
|--------|--------|
| Workflow | CRGPT design → CRGPT re-score → optional CRISOT → score → rank |
| Critic strategy | **Quality gate**: at least one candidate must pass `nn_score ≥ threshold` (and `crisot_score ≥ threshold` if CRISOT is enabled). |
| Retry action | Increase `n_samples` by 10 on each retry. Thresholds relax progressively. |

#### RNA tertiary structure → sequence design (inverse folding)

| Aspect | Design |
|--------|--------|
| Workflow | RhoDesign / RiboDiffusion generation → RhoFold + structure alignment → score → rank |
| Critic strategy | **Hard quality gate + retry limit**: all candidates must have RhoFold pLDDT ≥ 70; otherwise retry up to 3 times total. After 3 runs, always output best available. |
| Retry action | Adjust RhoDesign temperature sweep; increase sample count; filter GC outliers. |

#### RNA secondary structure → sequence design (ViennaRNA inverse folding)

| Aspect | Design |
|--------|--------|
| Workflow | ViennaRNA RNAinverse → RNAfold validation → structure-distance scoring → rank |
| Critic strategy | **Structure-fidelity-only gate + retry limit**: retry if no candidates are produced, or if all candidates fail to refold into the target structure (`structure_distance / length > 0.02`). |
| Retry action | Increase `repeats`; increase `num_invocations`. |

### 5.4 Critic registration

Critic logic is tightly coupled to workflow scoring, so when one exists it should be registered alongside its Workflow. However, **not every workflow needs a critic**:

```python
# workflows/registry.py
WORKFLOW_CRITIC_PAIRS = {
    "mrna_cds_design": (MrnaCdsDesignWorkflow, MrnaCdsDesignLLMCritic),
    "sirna_design": (SirnaDesignWorkflow, SirnaDesignLLMCritic),
    "sgrna_design": (SgRnaDesignWorkflow, SgRnaDesignLLMCritic),
    "rna_aptamer_design": (RnaAptamerDesignWorkflow, RnaAptamerDesignLLMCritic),
    "ires_prediction": (IresPredictionWorkflow, IresPredictionLLMCritic),
    "rna_secondary_structure_design": (RnaSecondaryStructureDesignWorkflow, RnaSecondaryStructureDesignLLMCritic),
    "rna_tertiary_structure_design": (RnaTertiaryStructureDesignWorkflow, RnaTertiaryStructureDesignLLMCritic),
    "full_length_mrna_design": (FullLengthMrnaDesignWorkflow, FullLengthMrnaDesignLLMCritic),
}
```

The `ExecutionController` looks up the critic only if the workflow is registered.

### 5.5 Workflow–Critic design checklist

When adding a new task type, decide whether a Critic is needed, then verify:

1. [ ] The Workflow's scoring function is explicit and documented.
2. [ ] If a Critic is used, its thresholds are derivable from the scoring function (same metrics, compatible ranges).
3. [ ] If a Critic is used, it knows what to change on retry (parameter adjustment strategy, not just "try again").
4. [ ] Step-level failures (tool errors) are handled separately from workflow-level quality failures.
5. [ ] If a Critic is used, both are registered as a pair in `WORKFLOW_CRITIC_PAIRS`.

---

## 6. Bounded Multi-Module Coordination (BMC)

For the detailed design of the BMC framework — including what "Bounded" means, the distinction between Type-I (Physical Assembly) and Type-II (Functional Coupling), and the motivation and strategy for both full-length mRNA design and RNA aptamer design — see **`BMC_FRAMEWORK.md`** in this directory.

Key points at a glance:
- **Type-I**: `full_length_mrna_design` — 5'UTR ⊕ CDS ⊕ 3'UTR physical concatenation, coordinated by `FullLengthCoordinator`.
- **Type-II**: `rna_aptamer_design` — target hotspot + aptamer ligand functional coupling in 3D space, coordinated by `AptamerCoordinator`.
- Both share the same three-phase BMC skeleton (Independent Generation → Assembly & Evaluation → Bounded Iteration) with `max_rounds=3` and deterministic rule-based diagnosis.

---

## 7. How to Extend

### 7.1 Add a new tool

1. Implement the function in `agent_core/tools.py`.
2. Add its spec to `agent_core/tool_specs.py`.
3. Register it in `ALL_LANGCHAIN_AGENT_TOOLS`.
4. If it writes to agent state, add an INTERFACE LOCK block in `agent_core/state.py`.
5. Add a writeback entry in `agent_core/capabilities/writebacks.py`.
6. Add a microservice under `microservices/<tool>_service/`.

### 7.2 Add a new workflow

1. Build the workflow module inheriting from `BaseDomainWorkflow`.
2. Export it from `workflows/__init__.py`.
3. Register it in `AgentRunner.workflow_registry` (`agent_core/runner.py`).
4. If it needs a critic, register the pair in `workflows/registry.py`.
5. Expose it via the natural-language `/v1/agent/run` endpoint (no hard-coded task type dispatch).
6. Add tests under `tests/test_{name}_workflow.py`.

### 7.3 Add a new workflow tool wrapper

1. Use `PythonFunctionTool` from `tool_runtime.py`.
2. Wrap it with a `create_*` + `register_*` pair.
3. Ensure HTTP delegation goes through `agent_core/tools.py`, not direct `requests.post`.
