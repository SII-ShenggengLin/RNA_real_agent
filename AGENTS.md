# Agent Guidelines for RNA_real_agent

> **This file has been consolidated.**  
> All authoritative documentation now lives in `rna_agent_system/docs/`:
> - `README.md` — project overview, capability matrix, quick start
> - `ARCHITECTURE.md` — architecture, core module APIs, Interface Lock Policy, **and the five-layer architecture (§9)**
> - `TOOLS_AND_TASKS.md` — per-tool specs, task definitions, workflow patterns
> - `DEVELOPMENT.md` — deployment, testing, change logs, enhancement proposals

## Project Phase

The codebase has completed the **five-layer architecture migration** (commits `dbc4ba1`–`88296c5`). Layer 0–5 are all implemented and wired together:
- Layer 0: Tool wrappers, specs, registry, executor (frozen)
- Layer 1: `Capability` + `CapabilityRegistry` + declarative writebacks (`capabilities/`)
- Layer 2: `BaseDomainWorkflow` + `MrnaCdsDesignWorkflow` (`workflows/`) — scoring uses `-mfe + codon_count * log(CAI)`; no retry critic (re-running the same tools on the same protein does not improve candidates)
- Layer 3: `Planner` / `ExecutionController` / `RuleBasedPlanner` (`planning/`)
- Layer 4: `SessionMemory` + `WorkspaceManager` (in-memory, swappable)
- Layer 5: `AgentRunner` unified façade (Streamlit / FastAPI / CLI)

The monolithic 3,786-line `nodes.py` was retired and replaced by thin `graph_nodes.py` wrappers.

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
