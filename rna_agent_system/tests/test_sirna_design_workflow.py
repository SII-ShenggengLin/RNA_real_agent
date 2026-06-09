from __future__ import annotations


import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflows.sirna_design import (
    SirnaDesignInput,
    SirnaDesignLLMCritic,
    SirnaDesignWorkflow,
    score_sirna_candidate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stub tools
# ═══════════════════════════════════════════════════════════════════════════════


class _StubEvitarTool:
    name = "design_sirna_with_evitar"

    def invoke(self, kwargs):
        return {
            "top_results": [
                {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.95"},
                {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.85"},
                {"siRNA": "GGGCCCAUUAAAUUUAAAUUU", "score": "0.75"},
                {"siRNA": "CCCAUUAAAUUUAAAUUUGGG", "score": "0.65"},
            ],
            "result_count": 4,
            "mode": kwargs.get("mode", "existing"),
            "predict": kwargs.get("predict", "predsi"),
            "off_target": False,
        }


class _StubEvitarEmptyTool:
    name = "design_sirna_with_evitar"

    def invoke(self, kwargs):
        return {"top_results": [], "result_count": 0}


class _StubGcTool:
    name = "compute_rna_sequence_gc_content"

    def invoke(self, kwargs):
        seq = kwargs.get("filepath", "")
        pseudo = hash(seq) % 100 / 100.0
        gc = 0.30 + pseudo * 0.30
        return {
            "gc_content": round(gc, 3),
            "sequence_length": 21,
        }


class _StubDuplexTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -28.5,
            "sense": "AUGCCC",
            "antisense": "UUUGGG",
            "structure": "((((((",
        }


class _StubFoldTool:
    name = "predict_rna_secondary_structure"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -15.2,
            "structure": "(((...)))",
        }


class _StubBlastZeroTool:
    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 0, "subject_mode": "fasta"}


class _StubBlastHitTool:
    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 4, "subject_mode": "fasta"}


class _FailDuplexTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "duplex down"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _build_registry_with(*tools):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def _build_workflow(*tools):
    reg = _build_registry_with(*tools)
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "design_sirna_with_evitar",
        "compute_rna_sequence_gc_content",
        "compute_sirna_duplex_binding_vienna",
        "predict_rna_secondary_structure",
        "run_blastn_similarity_search",
    ):
        cap_reg.register(name)
    return SirnaDesignWorkflow(cap_reg)


def _build_controller_with_sirna(*tools):
    reg = _build_registry_with(*tools)
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "design_sirna_with_evitar",
        "compute_rna_sequence_gc_content",
        "compute_sirna_duplex_binding_vienna",
        "predict_rna_secondary_structure",
        "run_blastn_similarity_search",
    ):
        cap_reg.register(name)
    wf = SirnaDesignWorkflow(cap_reg)
    controller = ExecutionController(
        capability_registry=cap_reg,
        workflow_registry={"sirna_design": wf},
    )
    return controller, cap_reg


class _StubBlastAllHitsThenZeroTool:
    """First 3 calls (one workflow run) return high hits; subsequent calls return zero."""

    name = "run_blastn_similarity_search"

    def __init__(self):
        self._call_count = 0

    def invoke(self, kwargs):
        self._call_count += 1
        if self._call_count <= 3:
            return {"hit_count": 10, "subject_mode": "fasta"}
        return {"hit_count": 0, "subject_mode": "fasta"}


class _StubBlastHighHitTool:
    """Always returns a high off-target hit count that exceeds even relaxed thresholds."""

    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 10, "subject_mode": "fasta"}


_LONG_SEQ = "AUGC" * 30  # 120 nt


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_antiviral_mode_end_to_end():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
        candidate_count=10,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 3  # 4 raw - 1 duplicate
    assert result.best_candidate.rank == 1
    assert result.best_candidate.scores["total_rank"] <= result.all_candidates[-1].scores["total_rank"]


def test_generic_mode_sliding_window():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="generic",
        target_sequence=_LONG_SEQ,
        candidate_count=5,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    # 120 nt -> 100 windows; filtered down to max_keep=10
    assert len(result.all_candidates) <= 10
    assert all(c.source.startswith("sliding_window") for c in result.all_candidates)


def test_empty_candidates_antiviral():
    wf = _build_workflow(
        _StubEvitarEmptyTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_empty_candidates_generic_too_short():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="generic",
        target_sequence="AUGCAUGCAUGC",  # 12 nt < 40
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_tool_failure_graceful():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _FailDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
        candidate_count=3,
    )
    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    # Duplex failed -> all candidates get poor MFE ranks (inf sorted last)
    assert "rank_mfe" in best.scores
    assert "rank_offtarget" in best.scores
    # Total rank is rank sum (lower = better)
    assert "total_rank" in best.scores


def test_score_sirna_candidate_formula():
    # Perfect candidate: duplex=-40, off_target=0
    scores = score_sirna_candidate({"duplex_mfe": -40.0, "off_target_count": 0})
    assert scores["efficiency_component"] == 1.0
    assert scores["specificity_component"] == 1.0
    assert scores["total_score"] == pytest.approx(1.0, abs=0.01)

    # Worst candidate: duplex=0, off_target=9
    scores2 = score_sirna_candidate({"duplex_mfe": 0.0, "off_target_count": 9})
    assert scores2["efficiency_component"] == 0.0
    assert scores2["specificity_component"] == 0.1
    assert scores2["total_score"] < scores["total_score"]


def test_registry_has_sirna_critic():
    from agent_core.workflows.registry import get_critic_for_workflow

    critic = get_critic_for_workflow("sirna_design")
    assert critic is not None
    assert isinstance(critic, SirnaDesignLLMCritic)


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 integration tests — ExecutionController + Critic retry loop
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skip(reason="LLM-based critic does not support deterministic retry triggering from stubs")
def test_execution_controller_sirna_retry_exhausted():
    """When BLAST always returns high hits, ExecutionController marks retries_exhausted
    once plan.max_retries is reached (here set to 1 so Controller caps before Critic).
    """
    controller, _ = _build_controller_with_sirna(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastHighHitTool(),  # always returns 10 hits
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="sirna_design",
                input_binding={
                    "mode": "antiviral",
                    "target_sequence": _LONG_SEQ,
                    "candidate_count": 3,
                    "transcriptome_fasta_path": "dummy_transcriptome.fa",
                },
                output_key="sirna_result",
            )
        ],
        max_retries=1,  # stricter than Critic.MAX_RETRIES (2) to force exhaustion
    )

    def _replan(state):
        return plan

    state: dict[str, Any] = {}
    final_state = controller.execute(plan, state, replan_fn=_replan)

    # Critic should have triggered retry at least once
    log = final_state["_execution_log"]
    critic_events = [e for e in log if e.get("event") == "critic_retry"]
    assert len(critic_events) >= 1

    # retry_count should be 1 (incremented once before second run)
    assert final_state.get("retry_count") == 1

    # Because max_retries=1, the second run that triggers retry causes exhaustion
    plan_complete_events = [e for e in log if e.get("event") == "plan_complete"]
    assert any(e.get("retries_exhausted") for e in plan_complete_events)

    # workflow_result must be present and successful
    assert final_state.get("workflow_result") is not None
    assert final_state["workflow_result"].success is True
    assert final_state["workflow_result"].best_candidate is not None

    # next_constraints should carry safety warning from critic or exhaustion
    assert "next_constraints" in final_state


@pytest.mark.skip(reason="LLM-based critic does not support deterministic retry triggering from stubs")
def test_execution_controller_sirna_retry_then_pass():
    """Critic triggers retry on first run; second run passes (zero off-targets)."""
    controller, _ = _build_controller_with_sirna(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastAllHitsThenZeroTool(),  # first run all hits, then zero
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="sirna_design",
                input_binding={
                    "mode": "antiviral",
                    "target_sequence": _LONG_SEQ,
                    "candidate_count": 3,
                    "transcriptome_fasta_path": "dummy_transcriptome.fa",
                },
                output_key="sirna_result",
            )
        ],
        max_retries=2,
    )

    def _replan(state):
        return plan

    state: dict[str, Any] = {}
    final_state = controller.execute(plan, state, replan_fn=_replan)

    log = final_state["_execution_log"]
    critic_events = [e for e in log if e.get("event") == "critic_retry"]
    # Exactly one critic_retry (first run fails, second run passes)
    assert len(critic_events) == 1

    # retry_count incremented once after first retry
    assert final_state.get("retry_count") == 1

    # Should NOT be exhausted because second run passed
    plan_complete_events = [e for e in log if e.get("event") == "plan_complete"]
    assert not any(e.get("retries_exhausted") for e in plan_complete_events)

    # workflow_result present and successful
    assert final_state.get("workflow_result") is not None
    assert final_state["workflow_result"].success is True

    # State writeback from workflow internal state should be merged
    assert "_sirna_input" in final_state


def test_execution_controller_state_bindings():
    """ExecutionController resolves $state bindings and writes step output keys."""
    controller, _ = _build_controller_with_sirna(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="sirna_design",
                input_binding={
                    "mode": "antiviral",
                    "target_sequence": _LONG_SEQ,
                    "candidate_count": 3,
                },
                output_key="sirna_result",
            ),
            PlanStep(
                step_id="step_2",
                type="capability",
                target="compute_rna_sequence_gc_content",
                input_binding={
                    "filepath": "$state.sirna_result.best_candidate.sequence",
                },
                output_key="gc_check",
            ),
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {"_llm_critic_enabled": False}
    final_state = controller.execute(plan, state)

    # Step 1 output key written
    assert "sirna_result" in final_state
    assert final_state["sirna_result"].success is True

    # Step 2 should have resolved binding and produced a result
    assert "gc_check" in final_state
    assert final_state["gc_check"].success is True

    # workflow_result should also be present (auto-written for workflow steps)
    assert "workflow_result" in final_state
