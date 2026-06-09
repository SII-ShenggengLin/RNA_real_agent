"""Tests for partial retry (evaluator-only) optimisation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from agent_core.capabilities.base import CapabilityRegistry
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignLLMCritic,
)


def _make_candidate(sequence: str, cai: float, mfe: float, gc: float) -> Candidate:
    c = Candidate(
        sequence=sequence,
        sequence_type="mrna",
        source="test",
        metadata={
            "metrics_bundle": {
                "cai_score": cai,
                "mfe_kcal_per_mol": mfe,
                "gc_content": gc,
                "sequence_length": len(sequence),
            }
        },
    )
    c.scores = {"total_score": cai * 100}
    return c


def _make_mock_result() -> WorkflowResult:
    return WorkflowResult(
        success=True,
        task_id="test",
        summary="test",
        errors=[],
        all_candidates=[
            _make_candidate("AUG" * 30, cai=0.25, mfe=-100, gc=0.52),
            _make_candidate("AUG" * 30, cai=0.28, mfe=-110, gc=0.50),
        ],
    )


class TestPartialRetry:
    """Test evaluator-only partial retry flow."""

    def test_evaluator_only_retry_skips_full_rerun(self):
        """When critic recommends only evaluator params, partial rerun should
        be used instead of regenerating candidates."""
        # Mock diagnosis with evaluator-only parameter override
        mock_diagnosis = CriticDiagnosis(
            overall_assessment="GC evaluator seems off",
            quality_score=0.5,
            issues=[
                CriticIssue(
                    severity="warning",
                    category="gc_content",
                    description="GC values look suspicious",
                )
            ],
            action="retry_with_adjustments",
            parameter_overrides={"run_gc": False},
            reasoning="Disable GC evaluator and re-check",
            confidence=0.8,
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=mock_diagnosis.model_dump_json()
        )

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            critic = MrnaCdsDesignLLMCritic()
            result = _make_mock_result()
            state = {"_last_workflow_params": {"design_tool": "all"}}

            should_retry = critic.should_retry(result, state)

        # run_gc is in evaluator_only_params, so should_retry still returns True
        # but state should be marked for evaluator-only retry
        assert should_retry is True
        assert state.get("_evaluator_only_retry") is True
        assert "GCContentEvaluator" in state.get("_affected_evaluators", [])

    def test_full_param_retry_not_marked_evaluator_only(self):
        """When critic recommends design_tool (not evaluator-only), full retry
        should be triggered."""
        mock_diagnosis = CriticDiagnosis(
            overall_assessment="CAI too low",
            quality_score=0.3,
            issues=[
                CriticIssue(
                    severity="critical",
                    category="cai_score",
                    description="CAI < 0.4",
                )
            ],
            action="retry_with_adjustments",
            parameter_overrides={"design_tool": "rnarl"},
            reasoning="Switch to RNARL for better CAI",
            confidence=0.9,
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=mock_diagnosis.model_dump_json()
        )

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            critic = MrnaCdsDesignLLMCritic()
            result = _make_mock_result()
            state = {"_last_workflow_params": {"design_tool": "all"}}

            should_retry = critic.should_retry(result, state)

        assert should_retry is True
        assert "_evaluator_only_retry" not in state

    def test_execution_controller_partial_rerun(self):
        """Verify ExecutionController uses partial rerun when evaluator-only
        retry is flagged."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="cds",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST", "run_gc": False},
                )
            ],
            max_retries=2,
        )

        # Create a mock workflow that supports partial_rerun
        mock_wf = MagicMock()
        mock_result = _make_mock_result()
        mock_partial_result = _make_mock_result()
        mock_wf.run.return_value = mock_result
        mock_wf.partial_rerun.return_value = mock_partial_result

        # Patch the workflow registry
        controller.workflow_registry = {"mrna_cds_design": mock_wf}

        # Mock critic to trigger evaluator-only retry
        mock_critic = MagicMock()
        mock_critic.should_retry.return_value = True
        # Simulate state side-effects of should_retry
        def _should_retry_side_effect(result, state):
            state["_evaluator_only_retry"] = True
            state["_affected_evaluators"] = ["GCContentEvaluator"]
            state["_parameter_overrides"] = {"run_gc": False}
            return True
        mock_critic.should_retry.side_effect = _should_retry_side_effect

        with patch.object(
            controller, "_resolve_critic", return_value=mock_critic
        ):
            final_state = controller.execute(plan, {})

        # Partial rerun should have been called
        assert mock_wf.partial_rerun.called
        # run should NOT have been called a second time
        assert mock_wf.run.call_count == 1
        # The workflow_result should be the partial rerun result
        assert final_state["workflow_result"] is mock_partial_result

    def test_partial_rerun_fallback_on_failure(self):
        """If partial_rerun returns None, fall back to full retry."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="cds",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST"},
                )
            ],
            max_retries=2,
        )

        mock_wf = MagicMock()
        mock_result = _make_mock_result()
        mock_wf.run.return_value = mock_result
        mock_wf.partial_rerun.return_value = None  # partial rerun fails

        controller.workflow_registry = {"mrna_cds_design": mock_wf}

        call_count = 0
        def _should_retry(result, state):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                state["_evaluator_only_retry"] = True
                state["_parameter_overrides"] = {"run_gc": False}
                return True
            return False

        mock_critic = MagicMock()
        mock_critic.should_retry.side_effect = _should_retry

        with patch.object(
            controller, "_resolve_critic", return_value=mock_critic
        ):
            final_state = controller.execute(plan, {})

        # partial_rerun attempted but failed → fell back to full run
        assert mock_wf.partial_rerun.called
        # Full run called twice (first + fallback retry)
        assert mock_wf.run.call_count == 2
