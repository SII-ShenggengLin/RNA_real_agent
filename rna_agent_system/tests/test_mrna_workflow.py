from __future__ import annotations



from agent_core.capabilities.base import CapabilityRegistry
from agent_core.tool_executor import ToolExecutor, ToolResult
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_baseline_eval import StubCaiTool, StubFoldTool, StubGcTool
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringInput, run_mrna_sequence_scoring


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
    reg.register(StubCaiTool())
    ex = ToolExecutor(reg)

    seq_a = "AUGCCCGGGUUUAAAUUUAAAUUUAAA"  # 27 nt, partial swaps for synonymous mode
    seq_b = "AUGCCCGGGUUUAAAUUUAAAUUUAAA"
    inp = MrnaSequenceScoringInput(
        sequences=[seq_a, seq_b + "AAA"])
    out = run_mrna_sequence_scoring(inp, capability_registry=CapabilityRegistry(ex), auto_start_services=False)
    assert out.success is True
    assert out.best_candidate is not None
    assert out.best_candidate.rank == 1
    assert len(out.all_candidates) == 2
    assert out.best_candidate.scores["total_score"] >= out.all_candidates[-1].scores["total_score"]
    assert len(out.trace) == 6  # 2 candidates × 3 tools (gc + fold + cai)
    assert all(r.success for r in out.trace)


def test_mrna_workflow_tools_fail_gracefully():
    reg = ToolRegistry()
    reg.register(_FailGcTool())
    reg.register(_FailFoldTool())
    ex = ToolExecutor(reg)

    inp = MrnaSequenceScoringInput(sequence="AUGCAUGCAUGCAU")
    out = run_mrna_sequence_scoring(inp, capability_registry=CapabilityRegistry(ex), auto_start_services=False)
    assert out.success is True
    assert out.best_candidate is not None
    assert len(out.errors) >= 2
    assert not any(r.success for r in out.trace)
    # All tools failed → CAI and MFE missing → total_score falls back to 0.0
    assert out.best_candidate.scores["total_score"] == 0.0
