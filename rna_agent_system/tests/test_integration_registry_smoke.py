"""Lightweight wiring checks for the production tool registry (no HTTP calls)."""

from __future__ import annotations

from agent_core.tool_executor import build_default_tool_registry


def test_default_registry_registers_core_tools():
    reg = build_default_tool_registry()
    assert reg.has("compute_rna_sequence_gc_content")
    assert reg.has("predict_rna_secondary_structure_with_linearfold")
    assert reg.has("design_mrna_cds_with_lineardesign")
    assert len(reg.list_names()) == 41
