# Agent Guidelines for RNA_real_agent

## Interface Lock Policy

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
| `compute_rna_sequence_gc_content` | v0.1.0 | `docs/change_logs/gc_content_interface_v0.1.0.md` |
| `compute_dot_bracket_unpaired_fraction` | v0.1.0 | `docs/change_logs/dot_bracket_unpaired_fraction_interface_v0.1.0.md` |
| `run_blastn_similarity_search` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sirna_with_evitar` | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_sgrna_handle_with_crgpt` | v0.3.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| `design_mrna_cds_with_lineardesign` | v0.2.0 | `docs/change_logs/lineardesign_interface_v0.2.0.md` |
| ViennaRNA suite | v0.4.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |
| LinearFold suite | v0.2.0 | `agent_core/tools.py` + `agent_core/tool_specs.py` |

## GC Content Tool — Canonical Reference

The **GC content calculation tool** was refactored on 2026-04-25. Its interface is the **baseline** for all future modifications.

### Key architectural rules

1. **Single source of truth for HTTP**: `agent_core/tools.py::compute_rna_sequence_gc_content` is the only place that calls `requests.post` to port 8020. `workflow_tools/rna_gc_content_workflow.py` delegates to it via `.invoke()`.
2. **Shared normalization**: `agent_core/sequence_utils.py` contains `normalize_rna_sequence()` and `compute_gc_content()`. Both `mrna_scoring.py` (local fallback) and `workflow_baseline_eval.py` (test stub) import from here so they stay consistent with the microservice.
3. **Complete state tracking**: The agent state tracks 5 GC fields (`sequence_gc_content`, `sequence_gc_length`, `sequence_gc_count`, `sequence_g_count`, `sequence_c_count`), not just `gc_content`.

## Dot-bracket Unpaired Fraction Tool — Canonical Reference

The **dot-bracket unpaired fraction tool** was refactored alongside GC content on 2026-04-25. It follows the same architectural rules:

1. **Single source of truth for HTTP**: `agent_core/tools.py::compute_dot_bracket_unpaired_fraction` is the only place that calls `requests.post` to port 8020 `/unpaired-fraction`.
2. **Shared parsing and validation**: `agent_core/sequence_utils.py` contains `extract_dot_bracket()`, `validate_dot_bracket()`, and `compute_dot_bracket_unpaired_fraction()`. The microservice imports from here so that local stubs and the server never drift apart.
3. **Complete state tracking**: The agent state tracks 3 unpaired-fraction fields (`dot_bracket_unpaired_fraction`, `dot_bracket_structure_length`, `dot_bracket_dot_count`), not just the fraction.

### Before you edit anything dot-bracket-related

Read `rna_agent_system/docs/tools/compute_dot_bracket_unpaired_fraction.md` first.

### Before you edit anything GC-related

Read `docs/change_logs/gc_content_interface_v0.1.0.md` first.

## Testing

Run the full agent-core test suite before committing:

```bash
cd rna_agent_system
PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest tests/ -x --ignore=tests/integration -m "not integration"
```
