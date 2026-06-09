"""Layer-3 integration tests for MrnaSequenceScoringWorkflow + ExecutionController.

Covers:
- Math formula correctness and boundary handling in ``score_mrna_candidate``
- ``ExecutionController`` can execute ``mrna_sequence_scoring`` workflow step
- No critic retry is triggered for this workflow
- Graceful degradation when underlying tools fail
- State writeback contains expected score fields
"""

from __future__ import annotations

import math

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflow_baseline_eval import StubCaiTool, StubFoldTool, StubGcTool
from agent_core.sequence_utils import (
    compute_mrna_metric_bundle,
    score_mrna_candidate)
from agent_core.workflows.mrna_sequence_scoring import (
    MrnaSequenceScoringInput,
    MrnaSequenceScoringWorkflow,
    run_mrna_sequence_scoring)
from agent_core.workflows.registry import get_critic_for_workflow


# ═══════════════════════════════════════════════════════════════════════════════
# Stub tools
# ═══════════════════════════════════════════════════════════════════════════════


class _FailCaiTool:
    name = "compute_cai_for_cds_sequence"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "cai down"})


class _FailFoldTool:
    name = "predict_rna_secondary_structure_with_linearfold"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "fold down"})


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _build_controller_with(*tools, workflow_registry=None):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_cai_for_cds_sequence"):
        cap_reg.register(name)
    controller = ExecutionController(
        capability_registry=cap_reg,
        workflow_registry=workflow_registry or {})
    return controller


def _make_scoring_plan(**input_overrides):
    binding = {
        "sequence": "AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC"}
    binding.update(input_overrides)
    return ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_sequence_scoring",
                input_binding=binding,
                output_key="scoring_result",
                description="Score mRNA sequence")
        ],
        max_retries=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Score formula tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_score_mrna_candidate_formula_correctness():
    """total_score = -mfe + codon_count * log(CAI)"""
    bundle = compute_mrna_metric_bundle(
        sequence="AUG" * 30,  # 90 nt → 30 codons
        gc_from_tools=0.5,
        sequence_length_from_tools=90,
        mfe_kcal_per_mol=-10.0,
        cai_score=math.e,  # log(e) == 1.0
    )
    scores = score_mrna_candidate(bundle)
    # -(-10.0) + 30 * log(e) = 10.0 + 30 * 1.0 = 40.0
    assert scores["total_score"] == pytest.approx(40.0, abs=0.001)
    assert scores["combined_score"] == pytest.approx(40.0, abs=0.001)
    assert scores["cai_score"] == pytest.approx(math.e, abs=0.001)
    assert scores["mfe_per_nt"] == pytest.approx(-10.0 / 90, abs=0.001)


def test_score_mrna_candidate_boundary_conditions():
    # CAI == 0 → fallback total_score = 0.0
    b1 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=-5.0,
        cai_score=0.0)
    s1 = score_mrna_candidate(b1)
    assert s1["total_score"] == 0.0
    assert "combined_score" not in s1

    # CAI < 0 → fallback
    b2 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=-5.0,
        cai_score=-0.5)
    s2 = score_mrna_candidate(b2)
    assert s2["total_score"] == 0.0

    # length_nt == 0 → fallback
    b3 = compute_mrna_metric_bundle(
        sequence="",
        gc_from_tools=0.5,
        sequence_length_from_tools=0,
        mfe_kcal_per_mol=-5.0,
        cai_score=0.8)
    s3 = score_mrna_candidate(b3)
    assert s3["total_score"] == 0.0

    # Missing MFE → fallback
    b4 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=None,
        cai_score=0.8)
    s4 = score_mrna_candidate(b4)
    assert s4["total_score"] == 0.0
    assert "cai_score" in s4

    # Missing CAI → fallback
    b5 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=-5.0,
        cai_score=None)
    s5 = score_mrna_candidate(b5)
    assert s5["total_score"] == 0.0
    assert "mfe_per_nt" in s5

    # NaN / inf values → fallback
    b6 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=float("nan"),
        cai_score=0.8)
    s6 = score_mrna_candidate(b6)
    assert s6["total_score"] == 0.0

    b7 = compute_mrna_metric_bundle(
        sequence="AUG" * 10,
        gc_from_tools=0.5,
        sequence_length_from_tools=30,
        mfe_kcal_per_mol=-5.0,
        cai_score=float("inf"))
    s7 = score_mrna_candidate(b7)
    assert s7["total_score"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow input flexibility
# ═══════════════════════════════════════════════════════════════════════════════


def test_dict_input_accepted_by_run():
    """ExecutionController passes dict inputs; workflow must accept them."""
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    reg.register(StubCaiTool())
    ex = ToolExecutor(reg)
    wf = MrnaSequenceScoringWorkflow(ex)
    result = wf.run(
        {
            "sequence": "AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC"}
    )
    assert result.success is True
    assert result.best_candidate is not None
    assert "total_score" in result.best_candidate.scores


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionController integration
# ═══════════════════════════════════════════════════════════════════════════════


def test_execution_controller_runs_scoring_workflow():
    _reg = ToolRegistry()
    _reg.register(StubGcTool())
    _reg.register(StubFoldTool())
    _reg.register(StubCaiTool())
    wf_registry = {
        "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(ToolExecutor(_reg))}
    controller = _build_controller_with(
        StubGcTool(),
        StubFoldTool(),
        StubCaiTool(),
        workflow_registry=wf_registry)
    plan = _make_scoring_plan()
    state = {}
    result_state = controller.execute(plan, state)

    assert result_state["_plan_executed"] is True
    assert "scoring_result" in result_state
    assert "workflow_result" in result_state

    wf_result = result_state["workflow_result"]
    assert wf_result.success is True
    assert wf_result.best_candidate is not None
    assert "total_score" in wf_result.best_candidate.scores
    assert "gc_content" in wf_result.best_candidate.scores
    assert "sequence_length" in wf_result.best_candidate.scores


def test_execution_controller_no_critic_retry():
    """mrna_sequence_scoring has no critic → retry must not be triggered."""
    _reg = ToolRegistry()
    _reg.register(StubGcTool())
    _reg.register(StubFoldTool())
    _reg.register(StubCaiTool())
    wf_registry = {
        "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(ToolExecutor(_reg))}
    controller = _build_controller_with(
        StubGcTool(),
        StubFoldTool(),
        StubCaiTool(),
        workflow_registry=wf_registry)
    plan = _make_scoring_plan()
    state = {}
    result_state = controller.execute(plan, state)

    assert result_state.get("retry_count", 0) == 0
    assert "_critic_should_retry" not in result_state
    log = result_state.get("_execution_log", [])
    assert not any(entry.get("event") == "critic_retry" for entry in log)


def test_graceful_degradation_on_tool_failure():
    """When all tools fail, workflow still succeeds with fallback scores."""
    _reg = ToolRegistry()
    _reg.register(StubGcTool())
    _reg.register(_FailFoldTool())
    _reg.register(_FailCaiTool())
    wf_registry = {
        "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(ToolExecutor(_reg))}
    controller = _build_controller_with(
        StubGcTool(),
        _FailFoldTool(),
        _FailCaiTool(),
        workflow_registry=wf_registry)
    plan = _make_scoring_plan()
    state = {}
    result_state = controller.execute(plan, state)

    wf_result = result_state["workflow_result"]
    assert wf_result.success is True
    assert wf_result.best_candidate is not None
    # All tools failed → MFE and CAI missing → total_score falls back to 0.0
    assert wf_result.best_candidate.scores["total_score"] == 0.0
    assert len(wf_result.errors) >= 2  # fold + cai errors


def test_state_contains_expected_score_fields():
    """After ExecutionController run, state workflow_result has canonical keys."""
    _reg = ToolRegistry()
    _reg.register(StubGcTool())
    _reg.register(StubFoldTool())
    _reg.register(StubCaiTool())
    wf_registry = {
        "mrna_sequence_scoring": MrnaSequenceScoringWorkflow(ToolExecutor(_reg))}
    controller = _build_controller_with(
        StubGcTool(),
        StubFoldTool(),
        StubCaiTool(),
        workflow_registry=wf_registry)
    plan = _make_scoring_plan()
    state = {}
    result_state = controller.execute(plan, state)

    wf_result = result_state["workflow_result"]
    best = wf_result.best_candidate
    assert best is not None
    scores = best.scores
    assert "total_score" in scores
    assert "gc_content" in scores
    assert "sequence_length" in scores

    metrics = best.metadata.get("metrics_bundle", {})
    assert "gc_content" in metrics
    assert "sequence_length" in metrics
    assert "mfe_kcal_per_mol" in metrics
    assert "cai_score" in metrics
    assert "mfe_per_nt" in metrics


# ═══════════════════════════════════════════════════════════════════════════════
# Registry & runner integration
# ═══════════════════════════════════════════════════════════════════════════════


def test_registry_has_no_critic_for_mrna_sequence_scoring():
    """get_critic_for_workflow must return None for mrna_sequence_scoring."""
    critic = get_critic_for_workflow("mrna_sequence_scoring")
    assert critic is None


def test_runner_registry_contains_scoring_workflow():
    """AgentRunner.workflow_registry must include mrna_sequence_scoring."""
    from agent_core.planning.llm_planner import LLMPlanner
    from agent_core.runner import AgentRunner
    from agent_core.tool_executor import build_default_tool_registry

    planner = LLMPlanner()
    executor = ToolExecutor(build_default_tool_registry(include_demo=False))
    runner = AgentRunner(planner, executor)

    assert "mrna_sequence_scoring" in runner.workflow_registry
    wf = runner.workflow_registry["mrna_sequence_scoring"]
    assert isinstance(wf, MrnaSequenceScoringWorkflow)


# ═══════════════════════════════════════════════════════════════════════════════
# Functional entry-point tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_run_mrna_sequence_scoring_functional_entry():
    """``run_mrna_sequence_scoring`` should work without an explicit registry/executor."""
    from agent_core.tool_executor import build_default_tool_registry

    reg = build_default_tool_registry(include_demo=False)
    ex = ToolExecutor(reg)
    # The default registry may not have all tools, so we register stubs
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    reg.register(StubCaiTool())

    inp = MrnaSequenceScoringInput(
        sequence="AUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC")
    result = run_mrna_sequence_scoring(inp, executor=ex)
    assert result.success is True
    assert result.best_candidate is not None
