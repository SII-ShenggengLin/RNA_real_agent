"""W3.1 — aggregate CRISOT-Spec specificity wiring in the sgRNA workflow (v1.2.0).

The optional ``off_target_sequences`` input drives a new
``CRISOTSpecificityEvaluator``: aggregate CRISOT-Spec via the
``calculate_crispr_specificity_with_crisot`` capability, cached per run,
surfaced as a ``crisot_specificity`` scoring component.  Default (empty list)
must leave workflow behaviour unchanged.
"""

from __future__ import annotations

import json
import tempfile

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflows.sgrna_design import SgRnaDesignInput, SgRnaDesignWorkflow

from tests.test_sgrna_design_workflow import (  # noqa: F401  (reuse stubs)
    _StubCrisotTool,
    _StubDesignTool,
    _StubScoreTool,
)

_GUIDE = "ATGCATGCATGCATGCATGCTGG"
_OFFS = ["ATGCATGCATGCATGCATGCAAG", "ATGCATGCATGCGTGCATGCAGG"]


class _StubSpecTool:
    name = "calculate_crispr_specificity_with_crisot"

    def __init__(self, spec: float = 0.85):
        self.spec = spec
        self.calls: list[dict] = []

    def invoke(self, kwargs):
        self.calls.append(kwargs)
        return {
            "input_csv_filepath": kwargs.get("csv_filepath", ""),
            "on_item": "On",
            "off_item": "Off",
            "crisot_spec": self.spec,
            "row_count": len(_OFFS),
            "model": "CRISOT-Score",
        }


class _FailSpecTool:
    name = "calculate_crispr_specificity_with_crisot"

    def __init__(self):
        self.calls = 0

    def invoke(self, kwargs):
        self.calls += 1
        from agent_core.tool_executor import ToolResult

        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "spec service down"},
        )


def _build_workflow(*tools):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "design_sgrna_handle_with_crgpt",
        "score_sgrna_handle_with_crgpt",
        "score_crispr_off_target_with_crisot",
        "calculate_crispr_specificity_with_crisot",
    ):
        cap_reg.register(name)
    return SgRnaDesignWorkflow(cap_reg)


def _base_input(**extra) -> SgRnaDesignInput:
    return SgRnaDesignInput(
        seed_sequence="ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC",
        n_samples=3,
        guide_sequence=_GUIDE,
        target_sequence=_GUIDE,
        **extra,
    )


def test_no_off_targets_leaves_behaviour_unchanged():
    spec = _StubSpecTool()
    wf = _build_workflow(_StubDesignTool(), _StubScoreTool(), _StubCrisotTool(), spec)
    result = wf.run(_base_input())
    assert result.success
    assert spec.calls == []  # evaluator short-circuits on the empty list
    for c in result.all_candidates:
        assert c.metadata.get("metrics_bundle", {}).get("crisot_specificity") is None
        assert "crisot_specificity_component" not in c.scores


def test_off_targets_produce_specificity_component():
    spec = _StubSpecTool(spec=0.85)
    wf = _build_workflow(_StubDesignTool(), _StubScoreTool(), _StubCrisotTool(), spec)
    result = wf.run(_base_input(off_target_sequences=list(_OFFS)))
    assert result.success
    assert len(spec.calls) == 1  # cached per run despite multiple candidates
    # The On/Off CSV contains the guide against every off-target.
    csv_path = spec.calls[0]["csv_filepath"]
    content = open(csv_path).read().strip().splitlines()
    assert content[0] == "On,Off"
    assert len(content) == 1 + len(_OFFS)
    for c in result.all_candidates:
        mb = c.metadata.get("metrics_bundle", {})
        assert mb.get("crisot_specificity") == 0.85
        assert c.scores.get("crisot_specificity_component") == 0.85
    assert result.best_candidate is not None


def test_failed_spec_call_degrades_gracefully():
    spec = _FailSpecTool()
    wf = _build_workflow(_StubDesignTool(), _StubScoreTool(), _StubCrisotTool(), spec)
    result = wf.run(_base_input(off_target_sequences=list(_OFFS)))
    assert result.success  # specificity is optional; the run survives
    assert spec.calls >= 1
    for c in result.all_candidates:
        assert "crisot_specificity_component" not in c.scores
