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
| `router_node` | `nodes.py` | Keyword-based dispatch to a specialist |
| `sirna_specialist_node` | `nodes.py` | Decide which siRNA tool to call |
| `mrna_specialist_node` | `nodes.py` | Decide which mRNA / structure / design tool to call (priority-ordered matching) |
| `crispr_specialist_node` | `nodes.py` | Decide which CRISPR tool to call |
| `tool_execution_node` | `nodes.py` | Invoke the selected tool, write results into `AgentState`, and auto-chain downstream tools (e.g., CDS design → fold) |
| `critic_node` | `nodes.py` | Apply hard thresholds (MFE, off-target count) and decide pass / retry |

### 2.3 Conditional Edges

- Router → Specialist: determined by keyword matching on `user_text`.
- Specialist → Tool Execution: deterministic tool selection.
- Tool Execution → Critic: always.
- Critic → Specialist (retry) or END: based on `critic_verdict` and `retry_count < max_retries`.

---

## 3. Core Modules

### 3.1 `agent_core/state.py` — AgentState

`AgentState` is a `TypedDict` shared across all LangGraph nodes. It defines ~80 typed fields tracking outputs from every locked tool integration.

**Key structural observations**

- **INTERFACE LOCK** blocks group fields by tool (CRISOT v0.2.0, sgrna_design v0.3.0, codonw-slim v0.2.0, LinearDesign v0.2.0, RiboDiffusion v0.2.0, GerNA-Bind, RNAsmOL v0.2.0, RNASTOP v0.1.0, IRESfinder v0.2.0, ViennaRNA v0.4.0, BLAST+ v0.2.0, GC content v0.1.0, dot-bracket unpaired fraction v0.1.0).
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
| `workflows/mrna_scoring.py` | Simple ranking scores built from tool metrics + sequence-derived features. Weights: `gc=0.40`, `mfe=0.35`, `length=0.25` |

**Key functions in `mrna_scoring.py`**

| Symbol | Description |
|--------|-------------|
| `gc_fraction_from_sequence(sequence: str) -> float` | Local GC fallback using `sequence_utils` |
| `gc_band_score(gc, *, low=0.42, mid=0.50, high=0.58) -> float` | Triangle peak at `mid`; 0 outside band |
| `mfe_stability_component(mfe_kcal_per_mol) -> float` | Maps MFE to [0, 1]; missing → 0.45 |
| `length_target_score(length_nt, *, target_nt) -> float` | Triangular peak at target; ignore if `None` |
| `compute_mrna_metric_bundle(...)` | Collects canonical keys: `gc_content`, `gc_content_local`, `sequence_length`, `mfe_kcal_per_mol`, `target_length_nt` |
| `score_mrna_candidate(bundle, *, weights=None, target_length_nt=None) -> dict[str, float]` | Returns `gc_component`, `mfe_component`, `length_component`, `total_score` in [0, 1] |

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
- `agent_core/nodes.py`
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
5. Add routing logic in `agent_core/nodes.py`.
6. Add a microservice under `microservices/<tool>_service/`.

### Add a new workflow type

1. Add the canonical name to `IMPLEMENTED_TASK_TYPES` in `workflow_dispatch.py`.
2. Build the handler module (pattern: `workflows/{type}_workflow.py`).
3. Add scoring components reusing `sequence_utils.py` and the `MrnaScoreWeights` pattern in `mrna_scoring.py`.

### Add a new workflow tool wrapper

1. Use `PythonFunctionTool` from `tool_runtime.py`.
2. Wrap it with a `create_*` + `register_*` pair (pattern: `workflow_tools/rna_gc_content_workflow.py`).
3. Ensure HTTP delegation goes through `agent_core/tools.py`, not direct `requests.post`.
