"""Lightweight wiring checks for the production tool registry (no HTTP calls)."""

from __future__ import annotations

from agent_core.tool_executor import build_default_tool_registry


def test_default_registry_registers_core_mrna_tools():
    reg = build_default_tool_registry(include_demo=False)
    assert reg.has("compute_rna_sequence_gc_content")
    assert reg.has("predict_rna_secondary_structure_with_linearfold")
    assert reg.has("design_mrna_cds_with_lineardesign")


def test_demo_tool_only_when_requested():
    reg_demo = build_default_tool_registry(include_demo=True)
    assert reg_demo.has("workflow_demo_echo")
    reg_no = build_default_tool_registry(include_demo=False)
    assert not reg_no.has("workflow_demo_echo")
