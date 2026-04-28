from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.file_manager import PROJECT_ROOT
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflow_baseline_eval import StubFoldTool, StubGcTool
from agent_core.workflows.mrna_workflow import MrnaWorkflowInput, run_mrna_workflow


@pytest.fixture(autouse=True)
def _workspace_dir():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)


class _FailGcTool:
    name = "compute_rna_sequence_gc_content"

    def invoke(self, kwargs):
        return ToolResult(success=False, tool_name=self.name, error={"type": "stub", "message": "gc down"})


class _FailFoldTool:
    name = "predict_rna_secondary_structure_with_linearfold"

    def invoke(self, kwargs):
        return ToolResult(success=False, tool_name=self.name, error={"type": "stub", "message": "fold down"})


def test_mrna_workflow_end_to_end_best_candidate():
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    ex = ToolExecutor(reg)

    seq_a = "AUGCCCGGGUUUAAAUUUAAAUUUAAA"  # 27 nt, partial swaps for synonymous mode
    seq_b = "AUGCCCGGGUUUAAAUUUAAAUUUAAA"
    inp = MrnaWorkflowInput(
        sequences=[seq_a, seq_b + "AAA"],
        persist_run=False,
    )
    out = run_mrna_workflow(inp, executor=ex)
    assert out.success is True
    assert out.best_candidate is not None
    assert out.best_candidate.rank == 1
    assert len(out.all_candidates) == 2
    assert out.best_candidate.scores["total_score"] >= out.all_candidates[-1].scores["total_score"]
    assert len(out.trace) == 4  # 2 candidates × 2 tools
    assert all(r.success for r in out.trace)


def test_mrna_workflow_tools_fail_gracefully():
    reg = ToolRegistry()
    reg.register(_FailGcTool())
    reg.register(_FailFoldTool())
    ex = ToolExecutor(reg)

    inp = MrnaWorkflowInput(sequence="AUGCAUGCAUGCAU", persist_run=False)
    out = run_mrna_workflow(inp, executor=ex)
    assert out.success is True
    assert out.best_candidate is not None
    assert len(out.errors) >= 2
    assert not any(r.success for r in out.trace)
    # MFE missing → neutral component; GC from tools missing → local GC still scores.
    assert out.best_candidate.scores["total_score"] > 0
