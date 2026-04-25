# GC Content Tool Interface Baseline — v0.1.0

> **Status**: LOCKED — This document defines the canonical interface for `compute_rna_sequence_gc_content` and `workflow_rna_gc_content`. Any future modification must synchronize all files listed below and re-run the full test suite.
>
> **Locked on**: 2026-04-25
> **Author**: Agent refactor pass

## 1. What is locked

The following contracts are frozen:

- **Input schema** (`RnaGcContentInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`RnaGcContentOutput`): `input_filepath`, `resolved_filepath`, `sequence_length`, `g_count`, `c_count`, `gc_count`, `gc_content`, `model`
- **ToolSpec identity**: `compute_rna_sequence_gc_content`
- **Workflow tool name**: `workflow_rna_gc_content`
- **Microservice endpoint**: `POST /gc-content` on port `8020`
- **State fields**: `sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`

## 2. Architecture decision record

### Why the LangChain tool is the single source of truth for HTTP

Previously `workflow_rna_gc_content` duplicated the `requests.post` call and path-resolution logic found in `agent_core.tools.compute_rna_sequence_gc_content`. After this refactor:

- `run_rna_gc_content_workflow()` delegates to `compute_rna_sequence_gc_content.invoke()`.
- HTTP logic lives in **one place**: `agent_core/tools.py`.
- The workflow layer only wraps the dict result into a `ToolResult`.

### Why `agent_core/sequence_utils.py` was introduced

Three independent GC-calculation implementations existed:

1. Microservice (`microservices/rna_sequence_metrics_service/main.py`)
2. Local fallback scorer (`workflows/mrna_scoring.py::gc_fraction_from_sequence`)
3. Test stub (`workflow_baseline_eval.py::StubGcTool`)

The agent-core fallback and the test stub now import `normalize_rna_sequence` and `compute_gc_content` from `agent_core.sequence_utils`, ensuring they match the microservice normalization rules (strip FASTA headers, T→U, filter non-AUGC). The microservice keeps its own copy because it runs in an isolated conda environment.

### Why `timeout_seconds` was added to `RnaGcContentInput`

The LangChain tool previously hard-coded `timeout=120`. Adding `timeout_seconds` to the Pydantic input model lets both the agent LLM and downstream workflows customize the timeout without editing the wrapper code.

## 3. Synchronization checklist

If you need to change **any** of the locked contracts, update **all** of these files and re-run the tests:

- [ ] `microservices/rna_sequence_metrics_service/main.py`
- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/nodes.py`
- [ ] `agent_core/workflow_tools/rna_gc_content_workflow.py`
- [ ] `agent_core/workflows/mrna_workflow.py`
- [ ] `agent_core/workflows/mrna_scoring.py`
- [ ] `agent_core/workflow_baseline_eval.py`
- [ ] `agent_core/sequence_utils.py`
- [ ] `tests/test_rna_gc_content_workflow.py`
- [ ] `tests/test_compute_rna_sequence_gc_content.py`
- [ ] `docs/tools/compute_rna_sequence_gc_content.md`
- [ ] `docs/change_logs/gc_content_interface_v0.1.0.md` (this file)

## 4. Tests that must pass

```bash
pytest tests/test_compute_rna_sequence_gc_content.py tests/test_rna_gc_content_workflow.py -v
pytest tests/test_mrna_workflow.py tests/test_workflow_observability.py -v
pytest tests/test_integration_registry_smoke.py -v
```

## 5. How to verify the live service

```bash
# 1. Start the microservice
conda run -n rna_sequence_metrics_service_env \
  python -m uvicorn microservices.rna_sequence_metrics_service.main:app \
  --host 127.0.0.1 --port 8020

# 2. Health check
curl http://127.0.0.1:8020/health

# 3. GC content call
curl -X POST http://127.0.0.1:8020/gc-content \
  -H "Content-Type: application/json" \
  -d '{"sequence_filepath":"workspace/your_sequence.fasta"}'
```

## 6. Notes for future maintainers

- Do **not** revert `workflow_tools/rna_gc_content_workflow.py` to its pre-refactor state (direct `requests.post`). That pattern creates duplicate HTTP logic.
- Do **not** remove `agent_core/sequence_utils.py` and inline the math back into `mrna_scoring.py` or `workflow_baseline_eval.py`. That re-creates the 3-way duplication.
- If you change the normalization rules in the microservice (e.g., which characters are stripped), you **must** update `sequence_utils.py` as well, or local fallback scores and stub test results will diverge from the microservice.
