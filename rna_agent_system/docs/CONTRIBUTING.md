# Contributing Guide

> **Scope**: coding standards, new-tool procedure, interface lock annotations, and commit conventions.
> **Last updated**: 2026-08-04

---

## 0. Simplicity-First Rule (2026-08-04 用户拍板)

- **No backward-compatibility burden**: when modifying code, do NOT preserve compatibility shims for superseded strategies. Prioritize code simplicity.
- **Delete superseded code**: once a better/newer strategy lands, delete the old strategy's code and its documentation — do not let dead code accumulate.
- **Delete superseded docs**: same rule for documentation — remove content describing abandoned strategies to keep docs concise.
- **Exceptions**: (a) INTERFACE LOCK blocks still follow §5 lock procedure (deletion of a locked interface requires the same synchronized update); (b) code/data explicitly retained as experimental baselines (e.g., the legacy agent stack serving as the E3 control arm, per `docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md` §7) stays until the experiment that needs it is done.

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
5. Register in ALL_LANGCHAIN_AGENT_TOOLS
6. If the tool publishes derived/aliased fields, consume them directly in the calling workflow / capability; no separate writeback registry is needed
7. Add an INTERFACE LOCK block in the affected files if the tool changes agent state
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

#   - tests/test_<tool>.py
#   - rna_agent_system/docs/INTERFACE_LOCKS.md
# ═══════════════════════════════════════════════════════════════════════════════
```

**Rule**: Do NOT modify any function signature, Pydantic field, return dict key, or state field inside an INTERFACE LOCK block without updating **all** files listed in the lock comment and re-running the full test suite.

## 6. How to Extend

### 6.2 Add a new workflow

1. Build the workflow module (`workflows/{name}.py`) inheriting from `BaseDomainWorkflow`.
2. Export it from `workflows/__init__.py`.
3. Register it in `AgentRunner.workflow_registry` (`agent_core/runner.py`).
4. If it needs quality review, add a `QualityProfile` in `agent_core/quality_profiles/{name}.py` and register it in `agent_core/quality_profiles/__init__.py`.
5. **Add to CLI workflow list** in `cli/form_chat.py` (`_WORKFLOW_LIST`) so the interactive menu includes it.
   - Mark core parameters with `Field(..., json_schema_extra={"ui_group": "basic"})` so they appear expanded in the TUI; tool-level overrides default to `advanced` via the schema builder's prefix rules.
6. **Register required capabilities** on the workflow class. The CLI derives the microservices to start from `workflow.required_capabilities` via `agent_core.services.service_manager.CAPABILITY_SERVICE_MAP`; no hand-maintained orchestrator mapping is needed.
7. Consider `workflow_api/app.py` request/response contracts and add API smoke tests (the API dynamically discovers workflows via `AgentRunner.workflow_registry`).
8. Add tests under `tests/test_{name}_workflow.py`.

> **Note**: Workflow exposure is **explicit** — there is no automatic routing. Users select the workflow in the CLI or pass `explicit_workflow` to `run_form()` / `stream_form()` programmatically.

### 6.3 Add a new workflow tool wrapper

1. Add a normal `@tool` wrapper in `agent_core/tools.py` if the wrapper calls a microservice.
2. For pure-Python helpers (e.g. sequence parsing, JSON builders), implement the function in `agent_core/tools.py` and add a `ToolSpec` with `transport="python_api"`.
3. Ensure HTTP delegation goes through `agent_core/tools.py`, not direct `requests.post`.

### 6.4 Add a new CLI module

If you add a new file under `cli/`:
1. Ensure it is importable both when `cli/form_chat.py` is run directly and when imported.
2. Add `sys.path` guards if the module imports other `cli/` local files (see `cli/form_chat.py` for the pattern).
3. Document the module in `docs/ARCHITECTURE.md` §2.6 and `docs/DEPLOYMENT.md` §2.

### 6.5 Form validation

If a workflow has required parameters:
1. Define them as required Pydantic fields in the workflow's `input_model`.
2. `FormValidator.validate_with_model()` will raise validation errors before execution.
3. The CLI (`cli/form_chat.py`) reshforms the TUI with error hints so the user can correct the input.
4. Tests should cover both valid and invalid parameter sets (see `tests/test_runner_form.py` and `tests/test_form_validator.py`).
