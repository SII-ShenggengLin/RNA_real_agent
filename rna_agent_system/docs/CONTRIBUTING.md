# Contributing Guide

> **Scope**: coding standards, new-tool procedure, interface lock annotations, and commit conventions.
> **Last updated**: 2026-06-01

---

## 1. Commit Conventions

- **Do not use `git add .`**.
- Recommended workflow:
  ```bash
  git status --short
  git submodule status
  git add <specific_file>
  git commit -m "meaningful message"
  git push origin main
  ```

## 2. Do Not Commit

- `__pycache__/` / `*.pyc`
- `.DS_Store`
- `workspace/` runtime outputs
- Large weight files (`*.pt` / `*.pth`)
- `.env` (contains API keys)

## 3. Coding Standards

### 3.1 Python style

- Follow PEP 8.
- Use type hints for public functions.
- Pydantic models for all inputs/outputs that cross layer boundaries.

### 3.2 Error handling

- Microservices should return HTTP 200 with `{"error": "..."}` rather than raising unhandled exceptions.
- Agent-core tools should catch `requests` exceptions and return structured error dicts.

## 4. New Tool Standard Procedure

```
1. Clone upstream repo into external_repos/ (git submodule add)
2. Create microservices/<tool>_service/
   ├── environment.yml
   ├── main.py         (FastAPI: GET /health + POST /...)
   ├── start.sh
   └── install_*.sh    (optional)
3. Add @tool wrapper in agent_core/tools.py
4. Add ToolSpec in agent_core/tool_specs.py
5. Add a writeback entry in agent_core/capabilities/writebacks.py
6. Add state fields in agent_core/state.py (if needed)
7. Register in ALL_LANGCHAIN_AGENT_TOOLS
8. Test order: raw command → microservice endpoint → Agent invocation → CLI
```

## 5. Interface Lock Annotations

When locking a new tool interface, add a comment block like this in **all** affected files:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# <Tool name> INTERFACE LOCK (vX.Y.Z) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# Synchronized files (must all be updated together):
#   - microservices/<tool>_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py
#   - agent_core/state.py
#   - agent_core/capabilities/writebacks.py
#   - tests/test_<tool>.py
#   - rna_agent_system/docs/INTERFACE_LOCKS.md
# ═══════════════════════════════════════════════════════════════════════════════
```

**Rule**: Do NOT modify any function signature, Pydantic field, return dict key, or state field inside an INTERFACE LOCK block without updating **all** files listed in the lock comment and re-running the full test suite.

## 6. How to Extend

### 6.1 Add a new tool

1. Implement the function in `agent_core/tools.py`.
2. Add its spec to `agent_core/tool_specs.py`.
3. Register it in `ALL_LANGCHAIN_AGENT_TOOLS`.
4. If it writes to agent state, add an INTERFACE LOCK block in `agent_core/state.py`.
5. Add a writeback entry in `agent_core/capabilities/writebacks.py`.
6. Add a microservice under `microservices/<tool>_service/`.

### 6.2 Add a new workflow

1. Build the workflow module (`workflows/{name}.py`) inheriting from `BaseDomainWorkflow`.
2. Export it from `workflows/__init__.py`.
3. Register it in `AgentRunner.workflow_registry` (`agent_core/runner.py`).
4. If it needs a critic, register the pair in `workflows/registry.py`.
5. Expose it via the natural-language `/v1/agent/run` endpoint (no hard-coded task type dispatch).
6. Add tests under `tests/test_{name}_workflow.py`.

### 6.3 Add a new workflow tool wrapper

1. Use `PythonFunctionTool` from `tool_runtime.py`.
2. Wrap it with a `create_*` + `register_*` pair (pattern: `workflow_tools/rna_gc_content_workflow.py`).
3. Ensure HTTP delegation goes through `agent_core/tools.py`, not direct `requests.post`.
