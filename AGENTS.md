# Agent Guidelines for RNA_real_agent

> **This file has been consolidated.**  
> All authoritative documentation now lives in `rna_agent_system/docs/`:
> - `README.md` — project overview, capability matrix, quick start
> - `ARCHITECTURE.md` — architecture, core module APIs, Interface Lock Policy, **and the deterministic-routing design decision (§8)**
> - `TOOLS_AND_TASKS.md` — per-tool specs, task definitions, workflow patterns
> - `DEVELOPMENT.md` — deployment, testing, change logs, enhancement proposals

## Interface Lock Policy (retained here for visibility)

This project uses **INTERFACE LOCK** comments to prevent accidental breaking changes to tool contracts.

**Do NOT modify any function signature, Pydantic field, return dict key, or state field** inside an INTERFACE LOCK block without updating **all** files listed in the lock comment and re-running the full test suite.

### Currently locked interfaces

| Tool / Module | Version | Lock reference |
|---------------|---------|----------------|
| `compute_rna_sequence_gc_content` | v0.1.0 | `rna_agent_system/docs/DEVELOPMENT.md` §6 |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `rna_agent_system/docs/DEVELOPMENT.md` §7 |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `rna_agent_system/docs/DEVELOPMENT.md` §8 |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |

## Testing

Run the full agent-core test suite before committing:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
```
