# Architecture & Core Interfaces

> **Scope**: design principles, agent workflow architecture, core module APIs, and the Interface Lock Policy.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Agent Workflow Architecture](#2-agent-workflow-architecture)
3. [Core Modules](#3-core-modules)
4. [Workflow Layer](#4-workflow-layer)
5. [Interface Lock Policy](#5-interface-lock-policy)
6. [Canonical Reference: GC Content Tool](#6-canonical-reference-gc-content-tool)
7. [Canonical Reference: Dot-Bracket Unpaired Fraction Tool](#7-canonical-reference-dot-bracket-unpaired-fraction-tool)
8. [Routing Strategy: Deterministic vs. LLM-Driven](#8-routing-strategy-deterministic-vs-llm-driven)
9. [Target Architecture: Five-Layer Design](#9-target-architecture-five-layer-design)
   1. [Layer 2 Deep Dive — Domain Workflows](#931-layer-2-deep-dive--how-basedomainworkflow-works)
   2. [Layer 3 Deep Dive — Planner & Control](#941-layer-3-deep-dive--planner-backends--execution-control)
   3. [Workflow–Critic Co-Design](#99-workflowcritic-co-design)
   4. [Full-Length mRNA Design Workflow](#910-full-length-mrna-design-workflow)
   5. [ASO Target Screening Workflow](#911-aso-target-screening-workflow)
   6. [IRES Prediction & Validation Workflow](#912-ires-prediction--validation-workflow)

---

## 1. Design Principles

### 1.1 Single Source of Truth for HTTP

`agent_core/tools.py` is the **only** module that calls `requests.post` to microservice ports. Workflow-layer tools (e.g., `workflow_tools/rna_gc_content_workflow.py`) delegate to the LangChain `@tool` wrappers via `.invoke()`. This prevents duplicate HTTP logic and path-resolution bugs.

### 1.2 Shared Sequence Utilities

`agent_core/sequence_utils.py` contains `normalize_rna_sequence()`, `compute_gc_content()`, `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()`. Both agent-core scoring modules (e.g., `workflows/mrna_scoring.py`) and microservices import from here so that local fallbacks and server results never drift apart.

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

## 2. Agent Workflow Architecture

### 2.1 LangGraph StateGraph

```
START → router_node → [sirna|mrna|crispr]_specialist_node
                                    ↓
                         tool_execution_node
                                    ↓
                           critic_node
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
              (retry edge)                      END
           (if retry_count < max_retries)
```

### 2.2 Node Responsibilities

| Node | File | Responsibility |
|------|------|----------------|
| `router_node` | `graph_nodes.py` | Thin wrapper around `RuleBasedPlanner` (Layer 3) |
| `tool_execution_node` | `graph_nodes.py` | Delegates to `ExecutionController` (Layer 3), which invokes Layer 1 `Capability` objects |
| `critic_node` | `graph_nodes.py` | Optional quality gate (currently unused for mRNA CDS; ranking is sufficient) |
| *(specialist logic)* | `planning/rule_based/specialists/` | Deterministic tool selection extracted from retired monolithic `nodes.py` |

### 2.3 Conditional Edges

- Router → Specialist: determined by keyword matching on `user_text`.
- Specialist → Tool Execution: deterministic tool selection.
- Tool Execution → Critic: optional (only if a workflow is registered with a critic in `WORKFLOW_CRITIC_PAIRS`).
- Critic → Specialist (retry) or END: based on `critic_verdict` and `retry_count < max_retries`.

---

## 8. Routing Strategy: Deterministic vs. LLM-Driven

### 8.1 Why deterministic routing is used today

The current agent uses **deterministic keyword-based routing** (`router_node` → `specialist_node` → `tool_execution_node`) instead of letting an LLM choose tools dynamically. This is an **intentional architectural decision**, not a temporary workaround.

**Rationale**

| Concern | Deterministic routing addresses it by... |
|---------|------------------------------------------|
| **Test cost & efficiency** | Every routing branch is explicit code. We can unit-test each `if/elif` path without calling an LLM, making regression tests fast and cheap. |
| **Reproducibility** | Same input → same tool → same output. No temperature or prompt-drift variance. |
| **Debugging** | When a wrong tool is called, the bug is in `nodes.py` logic, not in an LLM’s latent reasoning. Stack traces point to exact lines. |
| **Baseline performance** | If the agent cannot perform well with perfect (hand-coded) routing, it will not perform well with LLM-driven routing either. Deterministic routing lets us validate that the **tools and evaluation metrics** are sound before adding the extra variable of LLM decision-making. |

### 8.2 How this relates to the clear tool interfaces

The project invests heavily in making tool interfaces self-describing:

- Every tool has a rich `ToolSpec` with `capabilities`, `limitations`, `task_tags`, `input_model`, and `output_model`.
- Every wrapper uses Pydantic `BaseModel` schemas with `Field(description=...)`.
- `tool_specs.py` could, in principle, be serialized into JSON and fed to an LLM as a function-calling schema.

**The tool layer is already "LLM-ready"**; only the routing layer is intentionally kept deterministic for now.

### 8.3 Migration path to LLM-driven routing

When the deterministic system is fully tested and performance is validated, the plan is to migrate to **LLM-driven tool selection**:

1. Serialize `TOOL_SPECS` into the system prompt (or use native function-calling).
2. Let the LLM emit `tool_name` + structured arguments directly, validated against `input_model`.
3. Retain the deterministic specialist nodes as **fallback / guardrails** for critical paths (e.g., CRISPR off-target safety checks).
4. Use the existing `tool_execution_node` unchanged — it already validates outputs with `output_model.model_validate()`.

> **Rule of thumb**: if the deterministic router cannot correctly dispatch a task, the LLM will not magically do better. Fix the task boundaries and evaluation metrics first; then replace the router.

---

## 3. Core Modules

### 3.1 `agent_core/state.py` — AgentState

`AgentState` is a `TypedDict` shared across all LangGraph nodes. It defines ~80 typed fields tracking outputs from every locked tool integration.

**Key structural observations**

- **INTERFACE LOCK** blocks group fields by tool (CRISOT v0.2.0, sgrna_design v0.3.0, codonw-slim v0.2.0, LinearDesign v0.2.0, RiboDiffusion v0.2.0, GerNA-Bind, RNAsmOL v0.2.0, RNASTOP v0.1.0, IRESfinder v0.2.0, ViennaRNA v0.4.0, BLAST+ v0.2.0, GC content v0.1.0, dot-bracket unpaired fraction v0.1.0, extract RNA from CIF v0.1.0, ODesign aptamer input v0.1.0, ColabFold protein structure v0.1.0, structure alignment v0.1.0).
- Each lock lists the full set of files that must be updated in sync.

**Notable generic fields**

- `messages`, `current_task`, `workspace_files`, `input_sequence`, `candidate_sequence`
- `route`: `"sirna" | "mrna" | "crispr" | "unsupported"`
- `active_specialist`, `next_action`, `critic_verdict`, `final_report`
- `retry_count`, `max_retries`

**Public factory**

```python
def default_state(user_text: str) -> AgentState: ...
```

**Extension rule**: any new field inside an INTERFACE LOCK block requires updating all files listed in that block and re-running end-to-end tests.

### 3.2 `agent_core/tools.py` — Tool Wrappers

~4,850 lines of `@tool` wrappers. Each wrapper:

1. Normalizes input (often via `file_manager.py` or `sequence_utils.py`).
2. Calls a microservice HTTP endpoint via `requests.post`.
3. Parses the response.
4. Returns a structured dict.

This is the **single source of truth** for HTTP calls to the microservices.

### 3.3 `agent_core/tool_specs.py` — Output Schemas & ToolSpec Registry

Pydantic `ToolSpec` registry and output schemas (`BlastnSearchOutput`, `ViennaFoldOutput`, `EvitarDesignOutput`, etc.). Defines identity, transport, capabilities, input/output models, and status for every tool.

### 3.4 `agent_core/tool_registry.py` — Tool Registry

Minimal name-based registry for LangChain-compatible tools (anything with `.invoke(dict)`).

| Symbol | Description |
|--------|-------------|
| `ToolNotRegisteredError` | Custom `KeyError` for missing lookups |
| `ToolRegistry` | Mutable mapping wrapper |
| `.register(tool, *, name=None)` | Register by explicit name or `tool.name` |
| `.register_many(tools)` | Bulk registration |
| `.unregister(name)` | Remove entry |
| `.get(name) -> Any` | Lookup or raise `ToolNotRegisteredError` |
| `.has(name) -> bool` | Membership test |
| `.list_names() -> list[str]` | Alphabetically sorted names |
| `.snapshot() -> Mapping[str, Any]` | Read-only copy |

**Extension point**: drop any object with a `.name` attribute and `.invoke(dict)` method into the registry.

### 3.5 `agent_core/tool_executor.py` — Tool Execution & Tracing

Resolves tools from a `ToolRegistry`, invokes them via LangChain `.invoke`, normalizes results, and optionally appends trace records to workflow models.

| Symbol | Description |
|--------|-------------|
| `build_default_tool_registry(*, include_demo=False) -> ToolRegistry` | Populate from `agent_core.tools.ALL_LANGCHAIN_AGENT_TOOLS` |
| `ToolExecutor` | Main dispatcher |
| `.run_tool(tool_name, **kwargs) -> ToolResult` | Invoke by name with success/error handling and timing |
| `.run_tool_for_workflow(tool_name, *, task, candidate=None, step_name="tool", write_candidate=True, write_task_log=True, **kwargs) -> ToolResult` | Runs `.run_tool`, then builds a `ToolCallRecord` and appends it to `candidate.tool_records` and/or `task.logs` |

**Extension point**: provide a custom `result_normalizer` callable `(tool_name: str, raw: Any) -> ToolResult` to change how raw tool outputs are wrapped.

### 3.6 `agent_core/tool_runtime.py` — Execution Primitives

| Symbol | Description |
|--------|-------------|
| `ToolResult` | Normalized result container (success, output, error, elapsed_time) |
| `CommandExecutionOutput` | stdout / stderr / returncode wrapper |
| `run_subprocess_command(...)` | Subprocess runner with timeout and streaming |
| `run_python_function(...)` | In-process Python callable runner |

### 3.7 `agent_core/workflow_models.py` — Serializable Workflow Models

Pydantic models for iterative candidate-based agent runs.

| Class | Key Fields | Methods |
|---|---|---|
| `ToolCallRecord` | `step_name`, `tool_name`, `input_summary`, `output_summary`, `success`, `error`, `elapsed_time`, `artifacts`, `metrics`, `created_at` | — |
| `Candidate` | `id` (auto UUID), `sequence`, `sequence_type="mrna"`, `source`, `scores`, `metadata`, `tool_records`, `rank`, `status` | `.add_tool_record(record)` |
| `TaskState` | `task_id`, `task_type`, `input_payload`, `constraints`, `candidates`, `best_candidate`, `iteration_index`, `messages`, `logs`, `status` | `.append_candidate()`, `.append_log()`, `.update_best_candidate(score_key, descending=True)` |
| `WorkflowResult` | `success`, `task_id`, `best_candidate`, `all_candidates`, `summary`, `errors`, `trace`, `public_summary`, `run_artifact_dir`, `run_result_json_path` | — |

| Function | Description |
|---|---|
| `sort_candidates_by_score(candidates, score_key, descending=True) -> list[Candidate]` | Sort by score; missing scores placed at end. Auto-sets `.rank`. |

**Extension point**: `extra="allow"` on all models means workflows can attach arbitrary fields without schema changes.

### 3.8 `agent_core/workflow_dispatch.py` — Task Type Dispatch

Lightweight classification for RNA workflow routing (no planner / DSL).

| Symbol | Description |
|--------|-------------|
| `UnknownTaskTypeError` | `task_type` not in known vocabulary |
| `TaskPlaceholderError` | Known but not yet implemented |
| `normalize_task_type(raw: str) -> str` | Strips punctuation, lowercases, maps aliases (e.g. `"5utr"` → `"utr5"`). Defaults to `"mrna"` |
| `classify_task_type(raw: str) -> "implemented" \| "placeholder" \| "unknown"` | Lifecycle bucket for dispatch decisions |
| `assert_dispatchable(raw: str) -> str` | Returns canonical name or raises one of the two exceptions above |

**Constants**

- `IMPLEMENTED_TASK_TYPES = {"mrna"}`
- `PLACEHOLDER_TASK_TYPES = {"utr5", "utr3", "circrna", "ires", "intron"}`

### 3.9 `agent_core/sequence_utils.py` — Shared Sequence Utilities

| Function | Returns | Description |
|---|---|---|
| `normalize_rna_sequence(raw: str) -> str` | Clean AUGC string | Strips FASTA headers (`>`), uppercases, T→U, drops non-AUGC |
| `compute_gc_content(normalized_seq: str) -> dict` | `{"sequence_length", "g_count", "c_count", "gc_count", "gc_content"}` | GC metrics for already-normalized input. Empty → zeros |
| `extract_dot_bracket(raw: str) -> str` | Clean structure string | Skips FASTA headers and empty lines, concatenates rest |
| `validate_dot_bracket(struct: str) -> None` | Raises `ValueError` | Ensures only `.()[]{}<>` characters |
| `compute_dot_bracket_unpaired_fraction(struct: str) -> dict` | `{"structure_length", "dot_count", "unpaired_fraction"}` | Validates first, then computes fraction of dots |

**Design principle**: these mirror the logic in `microservices/rna_sequence_metrics_service/main.py` so agent-core code never drifts from the microservice.

---

## 4. Workflow Layer

### 4.1 `workflows/` — Higher-Level Workflows

| Module | Purpose |
|--------|---------|
| `workflows/mrna_workflow.py` | `MrnaWorkflow` / `run_mrna_workflow` — fixed pipeline: generate candidates → save → ToolExecutor (GC + LinearFold MFE) → `mrna_scoring.py` → sort → `WorkflowResult` |
| `workflows/mrna_candidates.py` | Candidate generation helpers |
| `workflows/mrna_scoring.py` | Ranking scores: `total_score = -mfe + codon_count * log(CAI)`; component scores (GC, MFE, unpaired) computed for display only |

**Key functions in `mrna_scoring.py`**

| Symbol | Description |
|--------|-------------|
| `gc_fraction_from_sequence(sequence: str) -> float` | Local GC fallback using `sequence_utils` |
| `gc_fraction_from_sequence(sequence: str) -> float` | Local GC fallback using `sequence_utils` |
| `compute_mrna_metric_bundle(...)` | Collects canonical keys: `gc_content`, `gc_content_local`, `sequence_length`, `mfe_kcal_per_mol`, `target_length_nt` |
| `score_mrna_candidate(bundle) -> dict[str, float]` | Returns `total_score` = `-mfe + codon_count * log(CAI)`; raw metrics preserved for display |

### 4.2 `workflow_tools/` — Runnable Workflow Tools

Contains `rna_gc_content_workflow.py` — a LangChain `Runnable`-style workflow tool that delegates to `agent_core/tools.py::compute_rna_sequence_gc_content` so HTTP logic is not duplicated.

| Symbol | Description |
|--------|-------------|
| `WORKFLOW_RNA_GC_CONTENT_TOOL_NAME` | `"workflow_rna_gc_content"` |
| `RnaGcContentWorkflowInput` | `filepath`, `service_url`, `timeout_seconds` |
| `run_rna_gc_content_workflow(payload) -> ToolResult` | Invokes the LangChain tool, unpacks result into `ToolResult` |
| `create_workflow_rna_gc_content_tool(...) -> PythonFunctionTool` | Builds a `PythonFunctionTool` ready for registry/executor |
| `register_workflow_rna_gc_content_tool(registry, ...) -> PythonFunctionTool` | Convenience to register onto an existing `ToolRegistry` |

### 4.3 `workflow_api/` — HTTP API Entrypoints

FastAPI layer exposing workflow execution over HTTP.

| File | Role |
|------|------|
| `app.py` | FastAPI app with two endpoints: `POST /v1/workflows/mrna/run` and `POST /v1/workflows/run` (unified) |
| `mrna_handler.py` | `execute_mrna_workflow_http()` — orchestrates GC, fold, scoring, and candidate ranking |
| `mrna_schemas.py` | Pydantic request/response models (`MrnaWorkflowHttpRequest`, `MrnaWorkflowHttpResponse`) |
| `rna_unified_handler.py` | Unified dispatch across task types |

### 4.4 `cli/` — Command-Line Entrypoints

Single file: `cli/mrna_workflow.py` — CLI entry for the mRNA ranking workflow.

- Supports `--sequence`, `--sequences`, or `--protein` input.
- Optional `--constraints` (JSON), `--top-k`, `--debug`, `--json` output.
- Delegates to `workflow_api.mrna_handler.execute_mrna_workflow_http()`.

---

## 5. Interface Lock Policy

This project uses **INTERFACE LOCK** comments to prevent accidental breaking changes to tool contracts. When you see a block like this:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
```

**Do NOT modify any function signature, Pydantic field, return dict key, or state field** inside that lock without updating **all** files listed in the lock comment and re-running the full test suite.

### Currently locked interfaces

| Tool / Module | Version | Lock File / Doc |
|---------------|---------|-----------------|
| `compute_rna_sequence_gc_content` | v0.1.0 | `DEVELOPMENT.md` §6 + `gc_content` sync checklist |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `DEVELOPMENT.md` §7 + `dot_bracket` sync checklist |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `DEVELOPMENT.md` §8 + `lineardesign` sync checklist |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |

---

## 6. Canonical Reference: GC Content Tool

The **GC content calculation tool** was refactored on 2026-04-25. Its interface is the **baseline** for all future modifications.

### Key architectural rules

1. **Single source of truth for HTTP**: `agent_core/tools.py::compute_rna_sequence_gc_content` is the only place that calls `requests.post` to port 8020. `workflow_tools/rna_gc_content_workflow.py` delegates to it via `.invoke()`.
2. **Shared normalization**: `agent_core/sequence_utils.py` contains `normalize_rna_sequence()` and `compute_gc_content()`. Both `mrna_scoring.py` (local fallback) and `workflow_baseline_eval.py` (test stub) import from here so they stay consistent with the microservice.
3. **Complete state tracking**: The agent state tracks 5 GC fields (`sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`), not just `gc_content`.

### Locked contracts

- **Input schema** (`RnaGcContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaGcContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `g_count`, `c_count`, `gc_count`, `gc_content`, `model`
- **ToolSpec identity**: `compute_rna_sequence_gc_content`
- **Workflow tool name**: `workflow_rna_gc_content`
- **Microservice endpoint**: `POST /gc-content` on port `8020`
- **State fields**: `sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`

### Synchronization checklist

If you need to change **any** of the locked contracts, update **all** of these files and re-run the tests:

- `microservices/rna_sequence_metrics_service/main.py`
- `agent_core/tools.py`
- `agent_core/tool_specs.py`
- `agent_core/state.py`
- `agent_core/graph_nodes.py`
- `agent_core/capabilities/writebacks.py`
- `agent_core/workflow_tools/rna_gc_content_workflow.py`
- `agent_core/workflows/mrna_workflow.py`
- `agent_core/workflows/mrna_scoring.py`
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

## 7. Canonical Reference: Dot-Bracket Unpaired Fraction Tool

The **dot-bracket unpaired fraction tool** was refactored alongside GC content on 2026-04-25. It follows the same architectural rules:

### Key architectural rules

1. **Single source of truth for HTTP**: `agent_core/tools.py::compute_dot_bracket_unpaired_fraction` is the only place that calls `requests.post` to port 8020 `/unpaired-fraction`.
2. **Shared parsing and validation**: `agent_core/sequence_utils.py` contains `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()`. The microservice imports from here so that local stubs and the server never drift apart.
3. **Complete state tracking**: The agent state tracks 3 unpaired-fraction fields (`dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`), not just the fraction.

### Locked contracts

- **Input schema** (`DotBracketUnpairedFractionInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`DotBracketUnpairedFractionOutput`): `input_filepath`, `resolved_filepath`, `structure_length`, `dot_count`, `unpaired_fraction`, `model`
- **ToolSpec identity**: `compute_dot_bracket_unpaired_fraction`
- **Microservice endpoint**: `POST /unpaired-fraction` on port `8020`
- **State fields**: `dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`

### Before you edit anything dot-bracket-related

Read the dot-bracket section in `TOOLS_AND_TASKS.md` first, then check `agent_core/sequence_utils.py` and `microservices/rna_sequence_metrics_service/main.py`.

---

## 8. How to Extend

### Add a new tool

1. Implement the function in `agent_core/tools.py`.
2. Add its spec to `agent_core/tool_specs.py`.
3. Register it in `ALL_LANGCHAIN_AGENT_TOOLS`.
4. If it writes to agent state, add an INTERFACE LOCK block in `agent_core/state.py`.
5. Add routing logic in `agent_core/graph_nodes.py` (or `planning/rule_based/specialists/` for deterministic keyword-based routing).
6. Add a microservice under `microservices/<tool>_service/`.

### Add a new workflow type

1. Add the canonical name to `IMPLEMENTED_TASK_TYPES` in `workflow_dispatch.py`.
2. Build the handler module (pattern: `workflows/{type}_workflow.py`).
3. Add scoring components reusing `sequence_utils.py` and the combined-formula pattern in `mrna_scoring.py`.

### Add a new workflow tool wrapper

1. Use `PythonFunctionTool` from `tool_runtime.py`.
2. Wrap it with a `create_*` + `register_*` pair (pattern: `workflow_tools/rna_gc_content_workflow.py`).
3. Ensure HTTP delegation goes through `agent_core/tools.py`, not direct `requests.post`.

---

## 9. Five-Layer Architecture

> **Status**: **Implemented** (commits `dbc4ba1`–`88296c5`).  
> **Goal**: a layered system where deterministic routing and LLM-driven routing can coexist, and where the LangGraph chat path and the Workflow API path share the same domain logic.

### 9.1 Overview

```
┌──────────────────────────────────────────┐
│ Layer 5  Presentation                    │
│          Streamlit / FastAPI / CLI       │
├──────────────────────────────────────────┤
│ Layer 4  Session & Memory                │
│          Multi-turn context, workspace   │
│          files, candidate history        │
├──────────────────────────────────────────┤
│ Layer 3  Planning & Control              │
│          Task decomposition → execution  │
│          plan → dynamic routing          │
│          [rule backend] ↔ [LLM backend]  │
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
4. **Planner is backend-pluggable**. We can ship with `RuleBasedPlanner` today and swap to `LLMPlanner` later without touching Layer 2 or below.

---

### 9.2 Layer 1 — Atomic Capabilities

**Responsibility**: turn a single tool invocation into a typed, self-describing sub-task result, and write it back to state automatically.

**Why this layer exists**: the legacy `tool_execution_node` (in the retired 3,786-line `nodes.py`) contained ~800 lines of `if tool_name == "..."` manual result unpacking. Layer 1 replaced that with a declarative mapping driven by `ToolSpec.output_model`.

**Implementation**

| File | Role |
|------|------|
| `agent_core/capabilities/base.py` | `Capability` dataclass + `CapabilityRegistry`; wraps `ToolExecutor` and validates `output_model` |
| `agent_core/capabilities/writebacks.py` | Declarative `STANDARD_WRITEBACKS` mapping (30+ tools); replaces the old manual if-elif chain |

**State contract**: instead of 80+ flat fields (`crisot_score`, `lineardesign_mfe`, …), the agent state stores:

```python
tool_results: dict[str, Any]   # tool_name → normalized result dict
candidates: list[Candidate]    # from workflow_models.py
```

Adding a new tool no longer requires editing `state.py`. You register its `Capability` and add a writeback entry in `capabilities/writebacks.py`.

---

### 9.3 Layer 2 — Domain Workflows

**Responsibility**: fixed multi-step pipelines for each RNA sub-domain (mRNA design, siRNA design, CRISPR evaluation, …). Each workflow generates candidates, evaluates them with capabilities, scores, and ranks.

**Why this is one of the two most important layers**: this is where **biological domain expertise** lives. The scoring weights, candidate generation strategies, and evaluation order are domain-specific. If this layer is solid, both Chat and API users get the same high-quality analysis.

**Base abstraction**

```python
class BaseDomainWorkflow(ABC, Generic[WorkflowInputT, WorkflowResultT]):
    name: str
    required_capabilities: list[str]

    def run(self, inp: WorkflowInputT) -> WorkflowResultT:
        candidates = self.generate_candidates(inp)
        for cand in candidates:
            metrics = self.evaluate(cand)      # calls Layer 1 capabilities
            cand.scores = self.score(metrics)   # domain-specific scoring
        return self.rank_and_format(candidates)
```

**Implemented workflows**

| Workflow | File | Status |
|----------|------|--------|
| `MrnaWorkflow` | `workflows/mrna_workflow.py` | ✅ Available (GC + fold + scoring pipeline) |
| `MrnaCdsDesignWorkflow` | `workflows/mrna_cds_design.py` | ✅ Available (golden path: LinearDesign/RNARL/GEMORNA → fold → GC → score → rank) |
| `SirnaWorkflow` | — | 📝 Design only (see §9.11, §9.12) |
| `CrisprWorkflow` | — | 📝 Design only |

**Workflow as a compound capability**

The `ExecutionController` (Layer 3) can invoke a workflow just like a single tool. From the Planner’s perspective, calling `workflow_mrna_cds_design` is identical to calling `predict_rna_secondary_structure` — both are a single `PlanStep`. The Planner decides **what** to do; the Workflow decides **how** to do it well.

---

### 9.4 Layer 3 — Planning & Control

**Responsibility**: convert a user’s natural language request into an `ExecutionPlan` (a linear sequence of capabilities/workflows), then dispatch and monitor execution.

**Why this is the other most important layer**: this is the **decision-making brain**. It decides *what* to do, *in what order*, and *when to stop or retry*. It is also the exact layer we will swap from rules to LLM in the future.

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

| Backend | Class | Status | When to use |
|---------|-------|--------|-------------|
| Rule-based | `RuleBasedPlanner` | ✅ Implemented | Zero LLM cost, fully testable. Extracted from legacy `router_node` + `specialist_node`. |
| LLM function-calling | `LLMFunctionCallingPlanner` | 📝 Future | Serializes `TOOL_SPECS` into the system prompt. LLM emits `tool_name` + structured args. |
| Hybrid | `HybridPlanner` | 📝 Future v2 | Simple intents → rule; ambiguous / multi-step intents → LLM. |

**Rule-based structure (implemented)**

```
planning/
├── base.py                  # Planner + ExecutionPlan + ExecutionController + Critic abstractions
├── rule_based/
│   ├── router.py            # keyword → domain
│   ├── planner.py           # orchestrates router + specialists
│   ├── specialists/
│   │   ├── mrna_specialist.py
│   │   ├── sirna_specialist.py
│   │   └── crispr_specialist.py
│   └── parsers/             # NL → structured args
│       └── common.py        # ~1,700 lines of detection + param builders
└── llm_based/
    └── (reserved for future)
```

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

### 9.5 Layer 4 — Session & Memory

**Responsibility**: persist context across turns.

**Implementation**

| File | Class | Description |
|------|-------|-------------|
| `agent_core/session_memory.py` | `SessionMemory` | In-memory dict store (`load` / `save`). Can be swapped for Redis/SQLite without changing `AgentRunner`. |
| `agent_core/workspace_manager.py` | `WorkspaceManager` | Session-scoped directory management |
| `agent_core/file_manager.py` | `save_sequence`, `read_sequence`, etc. | Workspace file I/O helpers |

RNA design is iterative. A typical session looks like:
1. "Design an mRNA for GFP"
2. "The MFE is too high, give me a more stable one"
3. "Now run BLAST on the best candidate"

Without Layer 4, turn 3 does not know which candidate was chosen in turn 1.

---

### 9.6 Layer 5 — Presentation

**Responsibility**: human-facing UI and programmatic API.

**Implementation**

`AgentRunner` (`agent_core/runner.py`) is the unified façade. All presentation layers go through it:

```python
class AgentRunner:
    def __init__(self, planner: Planner, executor: ToolExecutor, *, session_memory=None):
        self.planner = planner
        self.executor = executor
        self.capability_registry = build_default_capability_registry(executor)
        self.workflow_registry = {"mrna_cds_design": MrnaCdsDesignWorkflow(...)}
        self.controller = ExecutionController(...)

    def run(self, user_input: str, session_id: str = "") -> dict: ...
    def run_chat(self, user_input: str, session_id: str = "") -> dict: ...
    def stream_chat(self, user_input: str, session_id: str = "") -> Iterator[dict]: ...
```

**Presentation layer mapping**

| Layer | File | Uses `AgentRunner` |
|-------|------|-------------------|
| Streamlit UI | `frontend/app.py` | ✅ `stream_chat()` |
| FastAPI API | `workflow_api/app.py` | ✅ `run()` |
| CLI | `cli/mrna_workflow.py` | ✅ via `workflow_api/` handlers |
| LangGraph legacy | `graph.py` / `graph_nodes.py` | ✅ `RuleBasedPlanner` + `ExecutionController` |

---

### 9.7 Migration Completed

The monolithic 3,786-line `nodes.py` was retired in commit `8fc361d`. All logic has been migrated to the five-layer architecture:

| Original location | Migration status | New home |
|-------------------|-----------------|----------|
| `nodes.py` `_build_*_args` | ✅ Migrated | `planning/rule_based/parsers/common.py` |
| `nodes.py` `router_node` | ✅ Migrated | `planning/rule_based/router.py` + `planner.py` |
| `nodes.py` `*_specialist_node` | ✅ Migrated | `planning/rule_based/specialists/{mrna,sirna,crispr}_specialist.py` |
| `nodes.py` `tool_execution_node` | ✅ Migrated | `capabilities/base.py` + `capabilities/writebacks.py` |
| `nodes.py` `critic_node` | ✅ Simplified | `graph_nodes.py` (thin wrapper); mRNA CDS has no critic — ranking is sufficient |
| `workflows/mrna_workflow.py` | ✅ Integrated | Layer 2 `MrnaWorkflow` + `MrnaCdsDesignWorkflow` |
| `workflow_api/app.py` | ✅ Integrated | Layer 5 via `AgentRunner` |
| `frontend/app.py` | ✅ Integrated | Layer 5 via `AgentRunner` |

---

### 9.8 Migration History

The migration was executed in the following order (all steps completed):

1. ✅ **Define top-level interface** (`AgentRunner`, `Planner`, `ExecutionPlan`) and run one golden-path end-to-end test (mRNA design from chat UI).
2. ✅ **Extract rule-based planner** from `nodes.py` into `planning/rule_based/` without changing behaviour.
3. ✅ **Build Layer 1 capabilities** for the tools used by the mRNA golden path; replace manual if-elif with auto-writeback.
4. ✅ **Unify paths**: LangGraph calls `MrnaCdsDesignWorkflow` as a compound capability via `ExecutionController`.
5. ✅ **Generalize Layer 2**: extract `BaseDomainWorkflow`; implement `MrnaCdsDesignWorkflow` (scoring via `-mfe + codon_count * log(CAI)`; no critic needed).
6. 📝 **Add LLM planner backend**: reserved for future — serialize `TOOL_SPECS`, let LLM choose tools; keep rule backend as fallback.
7. ✅ **Add Layer 4 memory**: `SessionMemory` + `WorkspaceManager` with session isolation.

> **Key rule followed**: at every step, the system remained end-to-end runnable. The codebase was never left in a "half-refactored, nothing works" state.

---

## 9.10 Full-Length mRNA Design Workflow

> **Status**: ✅ Implemented (`agent_core/workflows/full_length_mrna_design.py`)
>
> **Architecture**: Reuses `MrnaCdsDesignWorkflow` for CDS generation and evaluation;
> only full-length and UTR metrics are computed incrementally.

### 9.10.1 Why this workflow is distinct from CDS-only design

| Dimension | CDS-only (`mrna_cds_design`) | Full-length (`full_length_mrna_design`) |
|-----------|------------------------------|----------------------------------------|
| **Biological goal** | Maximize translation efficiency | Balance translation + UTR regulation + overall stability |
| **Generation tools** | LinearDesign, RNARL, GEMORNA | `MrnaCdsDesignWorkflow` + GEMORNA UTRs |
| **Evaluation scope** | CDS internal: CAI, MFE, GC | **Segmented**: CDS (reused) + 5'UTR + 3'UTR + full-length coordination |
| **Key extra metrics** | — | UTR MRL, UTR stability, IRES potential, full-length MFE |

### 9.10.2 Candidate generation

**Strategy C only** (CDS-only baseline + UTR append).

`generate_candidates()` calls `MrnaCdsDesignWorkflow.run()` to obtain already-evaluated CDS candidates, then appends 3×3 UTR combinations (short/medium/long) from GEMORNA.

```python
cds_workflow = MrnaCdsDesignWorkflow(capability_registry)
cds_result = cds_workflow.run(MrnaCdsDesignInput(protein_sequence=...))
for cds_cand in cds_result.all_candidates:
    for utr5_preset in ("short", "medium", "long"):
        for utr3_preset in ("short", "medium", "long"):
            full_seq = utr5 + cds_cand.sequence + utr3
```

CDS metrics (`mfe_kcal_per_mol`, `cai_score`, `gc_content`) are carried forward via `candidate.metadata["cds_metrics"]` so the full-length workflow never re-evaluates the CDS segment.

### 9.10.3 Incremental evaluation pipeline

Only full-length and UTR metrics are computed. CDS metrics are read from the reused `metrics_bundle`.

```python
def evaluate(self, candidate: Candidate) -> dict[str, Any]:
    # Reuse CDS metrics from MrnaCdsDesignWorkflow
    cds_metrics = candidate.metadata.get("cds_metrics", {})
    cds_mfe = cds_metrics.get("mfe_kcal_per_mol")
    cds_cai = cds_metrics.get("cai_score")
    cds_gc  = cds_metrics.get("gc_content")

    # 1. Full-length structure
    full_fold = capabilities["predict_rna_secondary_structure"].invoke({"filepath": full_fp})
    
    # 2. 5'UTR specific
    if len(utr5) >= 30:
        ires = capabilities["predict_putative_ires_with_iresfinder"].invoke({"filepath": utr5_fp})
    
    # 3. 5'UTR MRL & 3'UTR stability (GEMORNA)
    utr5_mrl = capabilities["predict_5utr_mrl_with_gemorna"].invoke({"filepath": utr5_fp})
    utr3_stab = capabilities["predict_3utr_stability_with_gemorna"].invoke({"filepath": utr3_fp})
    
    # 4. Full-length stability
    stability = capabilities["predict_mrna_stability_with_rnastop"].invoke({"filepath": full_fp})
    
    return {
        "cds_cai": cds_cai,
        "cds_mfe": cds_mfe,
        "cds_gc": cds_gc,
        "full_length_mfe": full_fold.get("mfe_kcal_per_mol"),
        "utr5_ires_potential": ires_max_score,
        "utr5_predicted_mrl": utr5_mrl,
        "utr3_predicted_stability": utr3_stab,
        "overall_stability": stability,
    }
```

**Not called**: `analyze_cds_codon_metrics_with_codonw_slim`, `compute_cai_for_cds_sequence`, `compute_rna_sequence_gc_content` for the CDS segment.

### 9.10.4 Scoring formula (rank aggregation / Borda count)

Full-length mRNA uses **rank aggregation** to combine the three functional modules.
This avoids the quantity-scale mismatch problem (e.g. CDS component ≈ 0.3 while
UTR5 MRL ≈ 6.5) that occurs when raw values are added directly.

```python
# 1. Rank each module independently (descending; higher = better)
cds_rank      = rank_by(candidates, key="cds_component",      descending=True)
utr5_rank     = rank_by(candidates, key="utr5_mrl",           descending=True)
utr3_rank     = rank_by(candidates, key="utr3_stability",     descending=True)

# 2. Sum the three ranks
total_rank = cds_rank + utr5_rank + utr3_rank

# 3. Sort by total_rank ascending (smaller sum = better overall candidate)
```

Where:
- `cds_component`: `cds_combined_score / cds_length` from the classic CDS-only score (`-mfe + codon_count * log(CAI)`)
- `utr5_mrl`: GEMORNA predicted Mean Ribosomal Load for 5'UTR
- `utr3_stability`: GEMORNA predicted stability score for 3'UTR

**Rationale**: Raw values from different predictors live on incompatible scales.
Ranking normalises each module to the same ordinal scale (1 … N), so a one-position
advantage in CDS quality is worth exactly as much as a one-position advantage in
UTR stability. Missing values are handled by assigning the worst possible rank to
the affected candidate in that module only.

All other metrics (full-length MFE, IRES potential, GC content, RNASTOP
overall_stability, 5'UTR folding balance) are **still computed during evaluation**
and included in the output report for human review, but they do **not**
participate in ranking.

### 9.10.5 Critic strategy

The critic filters candidates on **5'UTR IRES potential** only.  IRESfinder outputs
a probability in `[0, 1]`; the default decision threshold is `0.5`.  For standard
mRNA (cap-dependent translation) a putative IRES in the 5'UTR is undesirable
because it can interfere with canonical ribosome loading.

Retry is triggered **only** when the number of candidates that survive the IRES
filter (≤ `0.5`) drops below `MIN_GOOD_CANDIDATES = 5`:

```python
class FullLengthMrnaCritic(Critic):
    IRES_THRESHOLD: float = 0.5
    MIN_GOOD_CANDIDATES: int = 5

    def should_retry(self, workflow_result: WorkflowResult, state: AgentState) -> bool:
        all_candidates = workflow_result.all_candidates
        bad_count = sum(
            1 for c in all_candidates
            if c.metadata.get("metrics_bundle", {}).get("utr5_ires_potential")
            is not None and float(...) > self.IRES_THRESHOLD
        )
        remaining = len(all_candidates) - bad_count
        if remaining < self.MIN_GOOD_CANDIDATES:
            state["next_constraints"]["avoid_ires_in_5utr"] = True
            return True
        return False
```

### 9.10.6 When to use which mRNA workflow

| User request | Recommended workflow |
|-------------|---------------------|
| "Design the optimal coding sequence" | `mrna_cds_design` (Workflow ①) |
| "Design a full mRNA vaccine with UTRs" | `full_length_mrna_design` (Workflow ①b) |
| "I have a CDS, add UTRs to it" | `full_length_mrna_design` hybrid mode |
| "Evaluate my lab-synthesized mRNA" | `mrna_health_check` (Workflow ②) |

---

### 9.3.1 Layer 2 Deep Dive — How `BaseDomainWorkflow` Works

**Where domain expertise lives.**

Layer 2 is not just "calling a few tools in sequence." It is the **biological-knowledge container**: which metrics matter, how to weight them, how many candidates to generate, what trade-offs exist between stability and expression.

#### Base interface

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

#### `MrnaWorkflow` example (refactored from existing code)

```python
class MrnaWorkflow(BaseDomainWorkflow[MrnaWorkflowInput, WorkflowResult]):
    name = "mrna_design"
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "predict_rna_secondary_structure",
        "compute_rna_sequence_gc_content",
        "analyze_cds_codon_metrics_with_codonw_slim"
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry

    def generate_candidates(self, inp: MrnaWorkflowInput) -> list[Candidate]:
        cands = []
        # LinearDesign lambda=0 (MFE-optimal)
        ld = self.capabilities.get("design_mrna_cds_with_lineardesign").invoke(
            {"filepath": inp.protein_filepath, "lambda_value": 0.0}
        )
        cands.append(Candidate(sequence=ld["generated_sequence"], source="lineardesign_lambda0", scores={}))
        # RNARL Homo sapiens
        rnarl = self.capabilities.get("design_mrna_cds_with_rnarl").invoke(
            {"filepath": inp.protein_filepath, "model_type": "homo_mrna"}
        )
        cands.append(Candidate(sequence=rnarl["generated_sequence"], source="rnarl_homo", scores={}))
        return cands

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        filepath = save_sequence_to_workspace(candidate.sequence)
        fold = self.capabilities.get("predict_rna_secondary_structure").invoke({"filepath": filepath})
        gc = self.capabilities.get("compute_rna_sequence_gc_content").invoke({"filepath": filepath})
        cai = self.capabilities.get("compute_cai_for_cds_sequence").invoke({"filepath": filepath, "species": "Homo sapiens"})
        return {
            "mfe_kcal_per_mol": fold.get("mfe_kcal_per_mol"),
            "gc_content": gc.get("gc_content"),
            "cai_score": cai.get("cai_score"),
            "sequence_length": len(candidate.sequence)
        }

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return score_mrna_candidate(metrics)
```

#### Workflow as a compound capability

This is the mechanism that unifies the LangGraph chat path and the Workflow API path:

```python
class WorkflowCapability(Capability):
    """Wraps a Domain Workflow so the Planner can invoke it like any single tool."""
    def __init__(self, workflow: BaseDomainWorkflow):
        self.workflow = workflow

    @property
    def name(self) -> str:
        return f"workflow_{self.workflow.name}"

    def invoke(self, ctx: CapabilityContext) -> CapabilityResult:
        workflow_input = self._adapt_context(ctx)
        result = self.workflow.run(workflow_input)
        return CapabilityResult(
            output=result.model_dump(),
            artifacts=[c.sequence for c in result.all_candidates]
        )
```

From the Planner’s perspective, calling `workflow_mrna_design` is identical to calling `predict_rna_secondary_structure` — both are a single `PlanStep`. The Planner decides **what** to do; the Workflow decides **how** to do it well.

---

### 9.4.1 Layer 3 Deep Dive — Planner Backends & Execution Control

#### Planner is stateless and pure

```python
class Planner(ABC):
    @abstractmethod
    def plan(self, user_text: str, context: AgentContext) -> ExecutionPlan: ...

class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
    max_retries: int = 2
    fallback_on_error: Literal["abort", "skip", "retry_with_alternative"] = "retry_with_alternative"
```

The Planner only produces a plan. It does **not** execute it, does **not** read tool results, and does **not** decide whether to retry. This makes testing trivial: given input text, assert the expected `ExecutionPlan`.

#### Three backends

| Backend | Class | Description |
|---------|-------|-------------|
| Rule-based | `RuleBasedPlanner` | Extracted from current `router_node` + `specialist_node`. Keyword matching + hard-coded parameter parsers. Zero LLM cost. |
| LLM function-calling | `LLMFunctionCallingPlanner` | Serializes `TOOL_SPECS` into the system prompt. LLM emits `tool_name` + structured args. Reuses the rich `ToolSpec` metadata already written. |
| Hybrid | `HybridPlanner` | Simple / unambiguous intents → rule backend. Complex / multi-step / fuzzy intents → LLM backend. Best of both worlds. |

#### Rule-based structure (refactored from `nodes.py`)

```
planning/
├── base.py
├── rule_based/
│   ├── router.py            # keyword → domain
│   ├── specialists/
│   │   ├── mrna_specialist.py
│   │   ├── sirna_specialist.py
│   │   └── crispr_specialist.py
│   └── parsers/             # NL → structured args, independently testable
│       ├── evitar_parser.py
│       ├── lineardesign_parser.py
│       └── ...
└── llm_based/
    └── function_calling_planner.py
```

#### ExecutionController (bridge between Planner and lower layers)

```python
class ExecutionController:
    def __init__(self, capability_registry, workflow_registry, critic: Critic):
        self.capabilities = capability_registry
        self.workflows = workflow_registry
        self.critic = critic

    def execute(self, plan: ExecutionPlan, state: AgentState) -> AgentState:
        for step in plan.steps:
            inputs = self._resolve_bindings(step.input_binding, state)

            if step.type == "capability":
                result = self.capabilities.get(step.target).invoke(inputs)
            else:  # workflow
                result = self.workflows.get(step.target).run(inputs)

            self._write_result(state, step.output_key, result)

            # Critic checks the *result* of this step
            if self.critic.should_retry(step, result, state):
                # Trigger replan or fallback
                pass
        return state
```

**Why critic lives in the Controller, not the Planner**: the Planner creates the plan *before* execution. The Critic needs the *actual tool outputs* (e.g., the real MFE value) to make a judgment. Planner = "what to do"; Controller + Critic = "whether it was good enough."

---

## 9. Workflow–Critic Co-Design

> **Scope**: why Workflow and Critic must be designed together, and how their coupling varies by task type.
>
> **Implementation status**: `MrnaCdsDesignCritic` was **removed** (see §9.3.1 below); `SirnaCritic` and `CrisprCritic` remain design proposals only.

### 9.1 Why this matters more than Planner design

The Planner is a **scheduler** — it decides the order of operations. The Workflow is the **engine** — it produces candidates. The Critic is the **quality gate** — it decides whether the output is acceptable.

A bad Planner might choose a sub-optimal sequence. A **mismatched Workflow–Critic pair will either never finish (critic too strict) or produce garbage (critic too loose)**.

| Scenario | Symptom | Root cause |
|----------|---------|------------|
| Critic rejects every candidate | Infinite retry loop | Critic thresholds are stricter than the design tool can physically achieve |
| Critic accepts everything | Low-quality output | Critic only checks "result exists" without biological relevance |
| Critic checks metrics Workflow does not optimize | User confusion | Workflow minimizes MFE; Critic demands high CAI — no joint optimization |

### 9.2 Design principle: critic must reflect the workflow's objective function

**Rule**: when a Critic *is* used, its pass/fail criteria should be derivable from the Workflow’s scoring function.

For example, if a Workflow ranks candidates by a combined formula such as `-mfe + codon_count * log(CAI)`, a paired Critic should check the same raw metrics (MFE, CAI) and overall score — not introduce unrelated thresholds that the Workflow does not optimize.

If the Workflow scoring changes, the Critic must be updated in the same PR. They share a **joint objective**.

### 9.3 Task-type-specific critic strategies

Different RNA design tasks require different Workflow–Critic contracts. Some tasks benefit from retry; others do not.

#### mRNA CDS design — **NO CRITIC** (ranking-only)

> **Rationale for removal**: `MrnaCdsDesignCritic` was deleted because retrying the same protein sequence with the same design tools does not produce meaningfully different candidates. The workflow already generates diversity (LinearDesign λ=[0,1,4,10] + RNARL + GEMORNA), evaluates every candidate, and ranks them by `-mfe + codon_count * log(CAI)`. A retry loop would only waste compute.

| Aspect | Design |
|--------|--------|
| Workflow | Generate N candidates → evaluate all (GC, fold, RNASTOP, CAI) → score → rank |
| Critic strategy | **None** — ranking is sufficient |
| Retry action | N/A |

```python
# workflows/registry.py — mrna_cds_design is intentionally absent
WORKFLOW_CRITIC_PAIRS: Dict[str, Tuple[Type[Any], Type[Critic]]] = {}
```

#### siRNA design (off-target safety-critical)

| Aspect | Design |
|--------|--------|
| Workflow | Design guides → off-target scan → specificity check |
| Critic strategy | **Absolute safety gate**: off-target count must be zero; specificity must exceed threshold. No negotiation. |
| Retry action | Relax design constraints (e.g., fewer GC clamps) and re-run; or abort with explicit safety warning |

```python
class SirnaCritic(Critic):
    def should_retry(self, workflow_result: WorkflowResult, state: AgentState) -> bool:
        best = workflow_result.best_candidate
        # Safety-critical: hard thresholds
        if best.scores.get("off_target_count", 999) > 0:
            state["safety_warning"] = "Off-targets detected; relaxing seed constraints"
            state["next_constraints"]["seed_gc_min"] = 0.3  # relax
            return True
        if best.scores.get("specificity", 0) < 0.95:
            return True
        return False
```

#### CRISPR sgRNA optimization (constrained search)

| Aspect | Design |
|--------|--------|
| Workflow | Search → score → optimize → re-evaluate |
| Critic strategy | **Convergence check**: improvement between iterations drops below epsilon → stop. |
| Retry action | Continue optimization; or switch algorithm (CRISOT → CRGPT) |

```python
class CrisprCritic(Critic):
    def should_retry(self, workflow_result: WorkflowResult, state: AgentState) -> bool:
        current_best = workflow_result.best_candidate.scores[" specificity"]
        previous_best = state.get("previous_best_specificity", 0)
        improvement = current_best - previous_best

        if improvement < 0.01:  # converged
            return False  # stop

        state["previous_best_specificity"] = current_best
        return True  # keep optimizing
```

### 9.4 Critic as an optional per-workflow plugin

Critic logic is tightly coupled to workflow scoring, so when one exists it should be registered alongside its Workflow. However, **not every workflow needs a critic**:

```python
# workflows/registry.py
# Only workflows that genuinely benefit from retry are registered here.
# mRNA CDS design is intentionally omitted — see §9.3.1.
WORKFLOW_CRITIC_PAIRS = {
    "sirna_design": (SirnaWorkflow, SirnaCritic),
    "crispr_optimization": (CrisprWorkflow, CrisprCritic),
}
```

The `ExecutionController` looks up the critic only if the workflow is registered:

```python
def execute(self, plan: ExecutionPlan, state: AgentState) -> AgentState:
    for step in plan.steps:
        ...
        if step.type == "workflow":
            critic = get_critic_for_workflow(step.target)
            if critic is not None and critic.should_retry(result, state):
                # Replan: same workflow with modified parameters
                pass
```

### 9.5 Two-level critic architecture (future)

For complex tasks, a single pass/fail critic is not enough. We propose a **two-level** design:

| Level | Name | When it runs | Decision |
|-------|------|--------------|----------|
| L1 | **Step Critic** | After each individual tool call | "Did this tool succeed?" (e.g., ViennaRNA returned valid structure?) |
| L2 | **Workflow Critic** | After the full Workflow completes | "Is the final candidate good enough?" (biological quality gate) |

```python
class TwoLevelCritic:
    def __init__(self, step_critic: StepCritic, workflow_critic: WorkflowCritic):
        self.step_critic = step_critic
        self.workflow_critic = workflow_critic

    def check_step(self, step: PlanStep, result: Any, state: AgentState) -> CriticVerdict:
        return self.step_critic.check(step, result)

    def check_workflow(self, workflow_result: WorkflowResult, state: AgentState) -> CriticVerdict:
        return self.workflow_critic.check(workflow_result, state)
```

- **Step Critic** is generic: "Did the HTTP call return 200? Is the output schema valid?" → can be reused across all tasks.
- **Workflow Critic** is domain-specific: "Is MFE < -20? Is off-target count == 0?" → must be co-designed with the Workflow.

### 9.6 Summary: Workflow–Critic design checklist

When adding a new task type, decide whether a Critic is needed, then verify:

1. [ ] The Workflow’s scoring function is explicit and documented.
2. [ ] If a Critic is used, its thresholds are derivable from the scoring function (same metrics, compatible ranges).
3. [ ] If a Critic is used, it knows what to change on retry (parameter adjustment strategy, not just "try again").
4. [ ] Step-level failures (tool errors) are handled separately from workflow-level quality failures.
5. [ ] If a Critic is used, both are registered as a pair in `WORKFLOW_CRITIC_PAIRS`.

---

## 9.11 ASO Target Screening Workflow

> **Domain**: antisense oligonucleotide (ASO) therapeutics  
> **Type**: evaluation / screening (no candidate generation)  
> **Key tools**: `predict_rna_local_accessibility_profile_vienna` (RNAplfold), `compute_aso_target_accessibility_vienna` (RNAup), `compute_sirna_duplex_binding_vienna` (RNAcofold)

### 9.11.1 Biological scenario

The user has a target mRNA and wants to identify the most accessible regions for ASO binding. An ASO can only work if its target region is single-stranded (not buried in RNA secondary structure). This workflow screens the full-length mRNA, ranks windows by accessibility, and evaluates ASO binding strength at the top sites.

### 9.11.2 Pipeline

```
1. Input validation
   └─ sequence length, FASTA format

2. Full-length local accessibility profiling (RNAplfold)
   └─ per-position unpaired probability
   └─ output: accessibility curve TSV

3. Identify high-accessibility windows (sliding window)
   └─ window size: 15–20 nt (typical ASO length)
   └─ step size: 1–3 nt
   └─ score each window: mean unpaired probability
   └─ keep top-N windows (e.g., top 10)

4. For each top window:
   ├─ Design complementary ASO sequence (simple reverse complement)
   ├─ ASO–target binding evaluation (RNAup or RNAcofold)
   │   └─ binding free energy (ΔG)
   └─ Secondary structure of the duplex (RNAcofold)

5. Ranking
   └─ composite_score = accessibility_weight × mean_unpaired_prob
                        + binding_weight × normalized_binding_strength
   └─ sort descending

6. Report
   ├─ top-k target sites (start/end coordinates)
   ├─ ASO sequences
   ├─ binding free energies
   ├─ local structure contexts
   └─ risk flags (e.g., site overlaps SNP, repetitive region)
```

### 9.11.3 Input / output

```python
class AsoScreeningInput(BaseModel):
    target_mrna_filepath: str
    aso_length: int = 18           # 15–20 nt typical
    window_step: int = 1
    top_n_windows: int = 10
    binding_evaluation_tool: Literal["rnaup", "rnacofold"] = "rnaup"

class AsoScreeningResult(BaseModel):
    accessibility_profile_tsv: str
    top_sites: list[AsoSite]
    
class AsoSite(BaseModel):
    start: int          # 1-based
    end: int
    aso_sequence: str
    mean_unpaired_prob: float
    binding_dg_kcal_per_mol: float
    duplex_structure: str
    composite_score: float
```

### 9.11.4 Critic strategy

This is an **evaluation-only workflow**; there is no retry loop. The Critic’s role is risk classification:

```python
class AsoScreeningCritic(Critic):
    def classify(self, site: AsoSite) -> RiskLevel:
        if site.binding_dg_kcal_per_mol > -5.0:
            return RiskLevel.HIGH    # binding too weak
        if site.mean_unpaired_prob < 0.3:
            return RiskLevel.HIGH    # region too structured
        if -8.0 <= site.binding_dg_kcal_per_mol <= -6.0:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
```

**Note**: unlike design workflows, the Critic here produces a **risk report**, not a retry signal.

---

## 9.12 IRES Prediction & Validation Workflow

> **Domain**: internal ribosome entry site (IRES) discovery  
> **Type**: evaluation / screening  
> **Key tools**: `predict_putative_ires_with_iresfinder`, `predict_rna_secondary_structure` (ViennaRNA), `predict_rna_local_accessibility_profile_vienna` (RNAplfold)

### 9.12.1 Biological scenario

The user wants to identify potential IRES elements within a 5'UTR (or other candidate sequence). IRESfinder gives a probability score, but IRES function is strongly linked to specific RNA structures (complex stem-loops with exposed initiation sites). This workflow combines computational prediction with structural validation.

### 9.12.2 Pipeline

```
1. Input validation
   └─ sequence length (IRESfinder has internal limits)
   └─ DNA-normalized input (U→T if needed)

2. IRES prediction (IRESfinder)
   ├─ Mode 0: training-set-like prediction
   ├─ Mode 1: direct prediction
   └─ Mode 2: full-window scan with sliding window
   └─ output: per-position or per-window probability scores

3. Extract top candidate regions
   └─ threshold: probability > 0.5 (configurable)
   └─ merge overlapping windows
   └─ keep top-N candidate regions

4. Structural validation for each candidate
   ├─ Secondary structure prediction (ViennaRNA fold)
   │   └─ look for complex stem-loop patterns
   ├─ Local accessibility profile (RNAplfold)
   │   └─ verify the core IRES region is single-stranded or has specific accessibility pattern
   └─ Dot-bracket analysis
       └─ compute unpaired fraction in candidate region

5. Scoring & ranking
   └─ composite = ires_probability × structure_complexity_score × accessibility_consistency
   └─ structure_complexity_score: derived from stem-loop count / branch count

6. Report
   ├─ candidate regions (coordinates, sequences)
   ├─ IRES probability scores
   ├─ structural features (MFE, stem-loop map)
   ├─ accessibility curves
   └─ confidence level (high / medium / low)
```

### 9.12.3 Input / output

```python
class IresValidationInput(BaseModel):
    sequence_filepath: str
    iresfinder_mode: int = 2           # 0=train, 1=predict, 2=scan
    probability_threshold: float = 0.5
    window_size: int | None = None     # for mode 2
    top_n_candidates: int = 5

class IresValidationResult(BaseModel):
    iresfinder_raw_output: str
    candidate_regions: list[IresCandidate]

class IresCandidate(BaseModel):
    start: int
    end: int
    sequence: str
    ires_probability: float
    predicted_structure: str
    mfe_kcal_per_mol: float
    mean_unpaired_fraction: float
    stem_loop_count: int
    confidence: Literal["high", "medium", "low"]
```

### 9.12.4 Critic strategy

Evaluation-only. The Critic assigns confidence by cross-checking IRESfinder score against structural features:

```python
class IresValidationCritic(Critic):
    def assign_confidence(self, cand: IresCandidate) -> str:
        # IRES typically needs a complex structure, not just a simple hairpin
        if cand.ires_probability > 0.8 and cand.stem_loop_count >= 3:
            return "high"
        if cand.ires_probability > 0.6 and cand.stem_loop_count >= 2:
            return "medium"
        if cand.ires_probability > 0.5:
            return "low"
        return "rejected"   # does not meet minimum threshold
```

### 9.12.5 Relationship to other workflows

- This workflow can be called **as a sub-step** of the **full-length mRNA design workflow** (§9.10): after GEMORNA generates a 5'UTR, run IRES validation to check whether the UTR contains a functional IRES.
- It can also be triggered standalone when a user asks "Does my 5'UTR have an IRES?"

---

### Updated workflow landscape

| Priority | Domain | Workflow | Type |
|----------|--------|----------|------|
| P0 | mRNA | ① CDS design & optimization | design |
| P0 | mRNA | ①b Full-length mRNA design | design |
| P0 | mRNA | ② mRNA health check | evaluation |
| P0 | CRISPR | ③ sgRNA design + safety | design |
| P1 | siRNA | ④ siRNA design + safety | design |
| P1 | structure | ⑤ 2D→3D structure prediction | evaluation |
| P1 | structure | ⑥ Inverse folding | design |
| P1 | mRNA | ⑦ Homology screening | evaluation |
| P2 | ligand | ⑧ RNA–ligand scoring | evaluation |
| P2 | CRISPR | ⑨ sgRNA handle optimization | design |
| P2 | siRNA | ⑩ ASO accessibility (single-tool) | evaluation |
| P2 | mRNA | ⑪ IRES prediction (single-tool) | evaluation |
| P2 | general | ⑫ Sequence homology (BLAST) | evaluation |
| **P2** | **ASO** | **⑬ ASO target screening** | **evaluation** |
| **P2** | **IRES** | **⑭ IRES prediction & validation** | **evaluation** |
