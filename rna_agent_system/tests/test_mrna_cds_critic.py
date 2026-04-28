"""Unit tests for MrnaCdsDesignCritic and ExecutionController retry logic."""

from __future__ import annotations

from typing import Any

import pytest

from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.mrna_cds_critic import MrnaCdsDesignCritic
from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS, get_critic_for_workflow


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_result(total_score: float, mfe_component: float, gc_component: float) -> WorkflowResult:
    candidate = Candidate(
        sequence="AUGC" * 10,
        scores={
            "total_score": total_score,
            "mfe_component": mfe_component,
            "gc_component": gc_component,
            "length_component": 1.0,
        },
    )
    return WorkflowResult(
        success=True,
        task_id="test_001",
        best_candidate=candidate,
        all_candidates=[candidate],
        summary="test",
        errors=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Critic unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMrnaCdsDesignCritic:
    def test_pass_when_scores_are_good(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = _make_result(total_score=0.75, mfe_component=0.6, gc_component=0.8)
        assert critic.should_retry(result, state) is False
        assert state["critic_verdict"] == "pass"
        assert state["next_action"] == "finish"

    def test_retry_when_total_score_below_threshold(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = _make_result(total_score=0.65, mfe_component=0.6, gc_component=0.8)
        assert critic.should_retry(result, state) is True
        assert state["next_constraints"]["increase_diversity"] is True
        assert state["critic_verdict"] == "reject"
        assert state["next_action"] == "retry"

    def test_retry_when_mfe_component_low(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = _make_result(total_score=0.80, mfe_component=0.3, gc_component=0.8)
        assert critic.should_retry(result, state) is True
        assert state["next_constraints"]["prioritize_stability"] is True

    def test_retry_when_gc_component_zero(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = _make_result(total_score=0.80, mfe_component=0.6, gc_component=0.0)
        assert critic.should_retry(result, state) is True
        assert state["next_constraints"]["target_gc_mid"] == 0.50

    def test_no_retry_when_max_retries_reached(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 2, "max_retries": 2}
        result = _make_result(total_score=0.65, mfe_component=0.3, gc_component=0.0)
        assert critic.should_retry(result, state) is False
        assert state["critic_verdict"] == "reject"
        assert state["next_action"] == "finish"

    def test_no_retry_on_failed_workflow(self) -> None:
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = WorkflowResult(success=False, task_id="test_002", summary="fail", errors=["boom"])
        assert critic.should_retry(result, state) is False

    def test_priority_total_score_over_mfe(self) -> None:
        """When both total_score and mfe_component fail, total_score rule fires first."""
        critic = MrnaCdsDesignCritic()
        state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
        result = _make_result(total_score=0.60, mfe_component=0.3, gc_component=0.8)
        assert critic.should_retry(result, state) is True
        assert state["next_constraints"]["increase_diversity"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Registry tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_registry_contains_mrna_cds_design(self) -> None:
        assert "mrna_cds_design" in WORKFLOW_CRITIC_PAIRS
        wf_cls, critic_cls = WORKFLOW_CRITIC_PAIRS["mrna_cds_design"]
        assert wf_cls.__name__ == "MrnaCdsDesignWorkflow"
        assert critic_cls.__name__ == "MrnaCdsDesignCritic"

    def test_get_critic_for_workflow_instantiates(self) -> None:
        critic = get_critic_for_workflow("mrna_cds_design")
        assert isinstance(critic, MrnaCdsDesignCritic)

    def test_get_critic_for_unknown_workflow_returns_none(self) -> None:
        assert get_critic_for_workflow("unknown_workflow") is None


# ─────────────────────────────────────────────────────────────────────────────
# ExecutionController retry tests
# ─────────────────────────────────────────────────────────────────────────────

class FakeCapabilityRegistry:
    def get(self, name: str) -> Any:
        raise RuntimeError("should not be called in these tests")

    def has(self, name: str) -> bool:
        return False

    def list_names(self) -> list[str]:
        return []


class FakeWorkflow:
    def __init__(self, result: WorkflowResult):
        self._result = result
        self.run_count = 0

    def run(self, inputs: dict[str, Any]) -> WorkflowResult:
        self.run_count += 1
        return self._result


def test_controller_triggers_retry_and_replans() -> None:
    """ExecutionController must rerun the workflow when critic says retry."""
    # First run: low score → retry; second run: good score → pass
    result_bad = _make_result(total_score=0.60, mfe_component=0.6, gc_component=0.8)
    result_good = _make_result(total_score=0.75, mfe_component=0.6, gc_component=0.8)

    fake_wf = FakeWorkflow(result_bad)
    reg = FakeCapabilityRegistry()
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"mrna_cds_design": fake_wf},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="cds",
                type="workflow",
                target="mrna_cds_design",
                input_binding={"protein_sequence": "MVSK"},
                output_key="workflow_result",
            )
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}

    replan_calls = 0

    def _replan(s: dict[str, Any]) -> ExecutionPlan:
        nonlocal replan_calls
        replan_calls += 1
        # Swap workflow result to good on second run
        fake_wf._result = result_good
        return plan

    final_state = controller.execute(plan, state, replan_fn=_replan)

    assert replan_calls == 1
    assert fake_wf.run_count == 2
    assert final_state["retry_count"] == 1
    assert final_state["_critic_should_retry"] is True  # set during first run
    assert final_state.get("critic_verdict") == "pass"   # from second run


def test_controller_respects_max_retries() -> None:
    """When critic always wants retry, controller must stop at max_retries."""
    result_bad = _make_result(total_score=0.60, mfe_component=0.6, gc_component=0.8)
    fake_wf = FakeWorkflow(result_bad)
    reg = FakeCapabilityRegistry()
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"mrna_cds_design": fake_wf},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="cds",
                type="workflow",
                target="mrna_cds_design",
                input_binding={"protein_sequence": "MVSK"},
                output_key="workflow_result",
            )
        ],
        max_retries=1,
    )

    state: dict[str, Any] = {"retry_count": 0, "max_retries": 1}

    def _replan(s: dict[str, Any]) -> ExecutionPlan:
        return plan

    final_state = controller.execute(plan, state, replan_fn=_replan)

    # initial + 1 retry = 2 runs
    assert fake_wf.run_count == 2
    assert final_state["retry_count"] == 1


def test_controller_no_replan_fn_returns_early_on_retry() -> None:
    """Without replan_fn, controller stops after first retry trigger."""
    result_bad = _make_result(total_score=0.60, mfe_component=0.6, gc_component=0.8)
    fake_wf = FakeWorkflow(result_bad)
    reg = FakeCapabilityRegistry()
    controller = ExecutionController(
        capability_registry=reg,
        workflow_registry={"mrna_cds_design": fake_wf},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="cds",
                type="workflow",
                target="mrna_cds_design",
                input_binding={"protein_sequence": "MVSK"},
                output_key="workflow_result",
            )
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {"retry_count": 0, "max_retries": 2}
    final_state = controller.execute(plan, state)

    assert fake_wf.run_count == 1
    assert final_state["_critic_should_retry"] is True
