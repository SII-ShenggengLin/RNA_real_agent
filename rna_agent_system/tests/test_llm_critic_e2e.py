"""End-to-end tests for LLM Critic retry flow."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.planning.llm_critic import (
    CriticDiagnosis,
    CriticIssue,
)
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignLLMCritic,
)


def _make_candidate(sequence: str, cai: float, mfe: float, gc: float) -> Candidate:
    """Helper to build a candidate with metrics."""
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


class TestLLMCriticRetryFlow:
    """Test the complete retry flow: execute -> critic -> parameter override -> re-execute."""

    def test_critic_detects_low_cai_and_recommends_retry(self):
        """Mock LLM returns 'retry_with_adjustments' with lambda_value change."""
        critic = MrnaCdsDesignLLMCritic()

        # Build result with low CAI candidates
        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_candidate("AUG" * 30, cai=0.25, mfe=-100, gc=0.52),
                _make_candidate("AUG" * 30, cai=0.28, mfe=-110, gc=0.50),
            ],
        )

        # Mock diagnose to return a retry recommendation
        mock_diagnosis = CriticDiagnosis(
            overall_assessment="CAI too low across all candidates",
            quality_score=0.2,
            issues=[
                CriticIssue(
                    severity="critical",
                    category="cds_quality",
                    description="CAI < 0.4 for all candidates",
                    metric_value=0.25,
                    affected_candidate_count=2,
                )
            ],
            action="retry_with_adjustments",
            parameter_overrides={"lambda_value": 4.0},
            reasoning="Low CAI suggests lambda too low; increase to favor stability less",
            confidence=0.9,
        )

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            state = {"_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0}}
            should_retry = critic.should_retry(result, state)

        assert should_retry is True
        assert state.get("_parameter_overrides") == {"lambda_value": 4.0}
        assert state["_last_diagnosis"]["action"] == "retry_with_adjustments"

    def test_critic_proceeds_when_quality_good(self):
        """Mock LLM returns 'proceed' when quality is acceptable."""
        critic = MrnaCdsDesignLLMCritic()

        result = WorkflowResult(
            success=True,
            task_id="test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_candidate("AUG" * 30, cai=0.75, mfe=-150, gc=0.50),
            ],
        )

        mock_diagnosis = CriticDiagnosis(
            overall_assessment="Good quality candidates",
            quality_score=0.85,
            issues=[],
            action="proceed_with_filtered",
            parameter_overrides={},
            reasoning="All metrics within acceptable ranges",
            confidence=0.95,
        )

        with patch.object(critic, "diagnose", return_value=mock_diagnosis):
            state = {"_last_workflow_params": {"design_tool": "all"}}
            should_retry = critic.should_retry(result, state)

        assert should_retry is False
        assert "_parameter_overrides" not in state

    def test_execution_controller_applies_overrides_on_retry(self):
        """Verify ExecutionController merges parameter_overrides into plan."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf1",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLW", "design_tool": "all"},
                )
            ]
        )

        state = {
            "_last_workflow_params": {"protein_sequence": "MKLW", "design_tool": "all"},
            "_parameter_overrides": {"lambda_value": 4.0, "design_tool": "lineardesign"},
        }

        controller._apply_parameter_overrides(
            plan, state, state["_parameter_overrides"]
        )

        binding = plan.steps[0].input_binding
        assert binding["lambda_value"] == 4.0
        assert binding["design_tool"] == "lineardesign"
        assert binding["protein_sequence"] == "MKLW"  # unchanged

    def test_critic_disabled_by_state_flag(self):
        """When _llm_critic_enabled=False, should_retry returns False immediately."""
        critic = MrnaCdsDesignLLMCritic()
        result = WorkflowResult(
            success=True, task_id="t", summary="s", errors=[], all_candidates=[]
        )
        state = {"_llm_critic_enabled": False}

        # diagnose should NOT be called
        with patch.object(critic, "diagnose") as mock_diag:
            retry = critic.should_retry(result, state)
            mock_diag.assert_not_called()

        assert retry is False

    @pytest.mark.skipif(
        not os.environ.get("DEEPSEEK_API_KEY"),
        reason="Requires DEEPSEEK_API_KEY",
    )
    def test_live_critic_on_low_quality_result(self):
        """Optional live test with real LLM. Requires API key."""
        critic = MrnaCdsDesignLLMCritic()
        result = WorkflowResult(
            success=True,
            task_id="live_test",
            summary="test",
            errors=[],
            all_candidates=[
                _make_candidate("AUG" * 50, cai=0.20, mfe=-80, gc=0.65),
                _make_candidate("AUG" * 50, cai=0.22, mfe=-85, gc=0.63),
            ],
        )
        state = {"_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0}}

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        print(f"Live diagnosis: {diagnosis.model_dump_json(indent=2)}")
