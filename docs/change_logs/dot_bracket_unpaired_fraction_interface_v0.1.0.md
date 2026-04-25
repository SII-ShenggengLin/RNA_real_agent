# Dot-Bracket Unpaired Fraction Tool Interface Baseline — v0.1.0

> **Status**: LOCKED — This document defines the canonical interface for `compute_dot_bracket_unpaired_fraction`. Any future modification must synchronize all files listed below and re-run the full test suite.
>
> **Locked on**: 2026-04-25
> **Author**: Agent refactor pass

## 1. What is locked

The following contracts are frozen:

- **Input schema** (`DotBracketUnpairedFractionInput`): `filepath`, `service_url`, `timeout_seconds`
- **Output schema** (`DotBracketUnpairedFractionOutput`): `input_filepath`, `resolved_filepath`, `structure_length`, `dot_count`, `unpaired_fraction`, `model`
- **ToolSpec identity**: `compute_dot_bracket_unpaired_fraction`
- **Microservice endpoint**: `POST /unpaired-fraction` on port `8020`
- **State fields**: `dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`

## 2. Architecture decision record

### Why the LangChain tool is the single source of truth for HTTP

The wrapper `compute_dot_bracket_unpaired_fraction` in `agent_core/tools.py` is the **only** place that calls `requests.post` to port `8020/unpaired-fraction`. Any workflow or scoring layer that needs this metric must delegate to `compute_dot_bracket_unpaired_fraction.invoke()`.

### Why `agent_core/sequence_utils.py` was extended with dot-bracket helpers

Previously the microservice (`microservices/rna_sequence_metrics_service/main.py`) maintained private copies of `_extract_dot_bracket()` and `_DOT_BRACKET_ALLOWED`. After this refactor:

- `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()` live in `agent_core.sequence_utils`.
- The microservice imports these helpers so its parsing/validation logic cannot drift from agent-core stubs or local fallback code.
- The GC-content helper `compute_gc_content()` and `normalize_rna_sequence()` were also centralized into `sequence_utils.py` for the same reason.

### Why `timeout_seconds` was added to `DotBracketUnpairedFractionInput`

The LangChain tool previously hard-coded `timeout=120`. Adding `timeout_seconds` to the Pydantic input model lets both the agent LLM and downstream workflows customize the timeout without editing the wrapper code. This brings the tool into alignment with `compute_rna_sequence_gc_content`, which already had `timeout_seconds`.

### Why `read_sequence()` was removed from the tool wrapper

The wrapper previously called `read_sequence(filepath)` as a pre-check. That function is semantically a **sequence** reader (intended for A/U/G/C text), not a structure reader. It happened to work for dot-bracket files because it only reads raw text, but using it was misleading and could break if `read_sequence` ever gains sequence-specific validation. The wrapper now relies on `_absolute_path_under_project()` for path resolution and lets the microservice handle file existence and content validation.

### Why state tracking was expanded from 1 field to 3 fields

The original state only tracked `dot_bracket_unpaired_fraction: float`. Following the GC-content tool's pattern (which tracks 5 fields: `sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`), the unpaired-fraction tool now tracks:

- `dot_bracket_unpaired_fraction` — the primary metric
- `dot_bracket_structure_length` — total length of the parsed structure
- `dot_bracket_dot_count` — raw count of unpaired symbols

This gives downstream scoring nodes and report generators access to the raw counts, not just the derived ratio.

## 3. Synchronization checklist

If you need to change **any** of the locked contracts, update **all** of these files and re-run the tests:

- [ ] `microservices/rna_sequence_metrics_service/main.py`
- [ ] `microservices/rna_sequence_metrics_service/start.sh`
- [ ] `agent_core/tools.py`
- [ ] `agent_core/tool_specs.py`
- [ ] `agent_core/state.py`
- [ ] `agent_core/nodes.py`
- [ ] `agent_core/sequence_utils.py`
- [ ] `tests/test_compute_dot_bracket_unpaired_fraction.py`
- [ ] `docs/tools/compute_dot_bracket_unpaired_fraction.md`
- [ ] `docs/change_logs/dot_bracket_unpaired_fraction_interface_v0.1.0.md` (this file)
- [ ] `AGENTS.md`

## 4. Tests that must pass

```bash
pytest tests/test_compute_dot_bracket_unpaired_fraction.py -v
pytest tests/test_compute_rna_sequence_gc_content.py -v
pytest tests/test_integration_registry_smoke.py -v
pytest tests/test_tool_specs_output_models.py -v
```

## 5. How to verify the live service

```bash
# 1. Start the microservice
export PYTHONPATH="/path/to/repo/rna_agent_system:$PYTHONPATH"
conda run -n rna_sequence_metrics_service_env \
  python -m uvicorn rna_agent_system.microservices.rna_sequence_metrics_service.main:app \
  --host 127.0.0.1 --port 8020

# 2. Health check
curl http://127.0.0.1:8020/health

# 3. Unpaired fraction call
curl -X POST http://127.0.0.1:8020/unpaired-fraction \
  -H "Content-Type: application/json" \
  -d '{"structure_filepath":"workspace/your_structure.ss"}'
```

## 6. Notes for future maintainers

- Do **not** inline `extract_dot_bracket()` or `compute_dot_bracket_unpaired_fraction()` back into the microservice `main.py`. That re-creates duplication between the microservice and agent-core stubs.
- Do **not** remove `timeout_seconds` from `DotBracketUnpairedFractionInput`. It is required for API consistency with `RnaGcContentInput`.
- Do **not** reduce state tracking back to a single `dot_bracket_unpaired_fraction` field. Downstream scoring and reporting nodes depend on `dot_bracket_structure_length` and `dot_bracket_dot_count`.
- If you add new dot-bracket symbols to the allowed set (e.g., alphabetic pseudoknot notation), you **must** update `_DOT_BRACKET_ALLOWED` in `agent_core/sequence_utils.py` and the corresponding regex in the microservice (via the shared import).
- The microservice **must** be started with `PYTHONPATH` pointing to `rna_agent_system` so it can import `agent_core.sequence_utils`. The `start.sh` script handles this automatically.
