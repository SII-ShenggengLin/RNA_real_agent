"""Integration tests for LLM Critic on mrna_cds_design workflow."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.planning.llm_critic import CriticDiagnosis, CriticIssue
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignLLMCritic,
)


def _make_mock_result(
    candidate_count: int = 3,
    cai_values: list[float] | None = None,
) -> WorkflowResult:
    """Build a WorkflowResult with candidates having specified CAI values."""
    cai_values = cai_values or [0.3, 0.35, 0.4]  # all low CAI
    candidates: list[Candidate] = []
    for i, cai in enumerate(cai_values):
        c = Candidate(
            sequence="AUG" * 50,
            sequence_type="mrna",
            source=f"lineardesign_lambda{i}",
            metadata={
                "metrics_bundle": {
                    "cai_score": cai,
                    "mfe_kcal_per_mol": -150.0,
                    "gc_content": 0.52,
                    "sequence_length": 150,
                }
            },
        )
        c.scores = {"total_score": cai * 100, "combined_score": cai * 100}
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_task",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="test",
        errors=[],
    )


def _make_mock_diagnosis_low_cai() -> CriticDiagnosis:
    """Return a pre-built CriticDiagnosis simulating LLM output for low CAI."""
    return CriticDiagnosis(
        overall_assessment="All candidates have poor CAI (< 0.4), indicating suboptimal codon adaptation for human expression.",
        quality_score=0.25,
        issues=[
            CriticIssue(
                severity="critical",
                category="cai_score",
                description="CAI scores are consistently low (0.30-0.40). For human mRNA, CAI should ideally be > 0.6.",
                metric_value=0.35,
                threshold=0.6,
                affected_candidate_count=3,
            ),
            CriticIssue(
                severity="warning",
                category="design_tool_diversity",
                description="All candidates originate from the same tool configuration. Consider switching to RNARL for higher CAI.",
                affected_candidate_count=3,
            ),
        ],
        action="retry_with_adjustments",
        parameter_overrides={
            "design_tool": "rnarl",
            "lambda_value": 1.0,
        },
        reasoning="Low CAI is the primary blocker. RNARL tends to produce higher-CAI sequences. Reducing lambda_value favors expression over stability.",
        confidence=0.85,
    )


class TestMrnaCdsDesignLLMCritic:
    """Unit tests for the LLM Critic configuration and mock-diagnosis."""

    def test_config_loaded(self):
        """Verify the critic config has the expected fields."""
        critic = MrnaCdsDesignLLMCritic()
        assert critic.config.workflow_name == "mrna_cds_design"
        assert "design_tool" in critic.config.adjustable_params
        assert "lambda_value" in critic.config.adjustable_params

    def test_build_context_extracts_params(self):
        """Verify _build_context extracts parameters from state."""
        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result()
        state = {"_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0}}

        ctx = critic._build_context(result, state)
        assert ctx["workflow_name"] == "mrna_cds_design"
        assert ctx["parameters_used"]["design_tool"] == "all"
        assert ctx["candidate_count"] == 3

    def test_build_context_without_state_params(self):
        """Verify _build_context handles missing _last_workflow_params gracefully."""
        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result()
        state = {}

        ctx = critic._build_context(result, state)
        assert ctx["parameters_used"] == {}
        assert ctx["candidate_count"] == 3
        assert len(ctx["all_candidate_summaries"]) == 3

    def test_diagnosis_prompt_includes_dimensions(self):
        """Verify the prompt includes evaluation dimensions."""
        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result()
        state = {}

        ctx = critic._build_context(result, state)
        messages = critic._build_diagnosis_prompt(ctx)

        # Check system message contains evaluation criteria
        system_text = messages[0][1]  # ("system", text)
        assert "CAI" in system_text
        assert "design_tool" in system_text
        assert "lambda_value" in system_text
        assert "CriticDiagnosis" in system_text or "criticdiagnosis" in system_text.lower()

    def test_diagnosis_prompt_includes_candidates(self):
        """Verify the prompt includes candidate summaries."""
        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result(cai_values=[0.25, 0.30, 0.35])
        state = {}

        ctx = critic._build_context(result, state)
        messages = critic._build_diagnosis_prompt(ctx)

        user_text = messages[1][1]  # ("user", text)
        assert "lineardesign_lambda0" in user_text
        assert "cai_score" in user_text
        assert "0.25" in user_text or "0.3" in user_text

    def test_mock_diagnosis_low_cai(self):
        """Mock LLM diagnosis: verify CriticDiagnosis is produced with issues and parameter_overrides."""
        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result(cai_values=[0.25, 0.28, 0.30])
        state = {"_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0}}

        mock_diagnosis = _make_mock_diagnosis_low_cai()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=mock_diagnosis.model_dump_json()
        )

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            # Re-create critic so __init__ picks up the patched get_deepseek_llm
            critic = MrnaCdsDesignLLMCritic()
            diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.6  # low CAI should score poorly
        assert len(diagnosis.issues) > 0
        # At least one issue should mention CAI
        cai_issues = [
            i
            for i in diagnosis.issues
            if "cai" in i.category.lower() or "CAI" in i.description
        ]
        assert len(cai_issues) > 0
        # Should recommend parameter changes
        assert diagnosis.action in ("retry_with_adjustments", "retry_with_alternative")
        assert len(diagnosis.parameter_overrides) > 0
        assert "design_tool" in diagnosis.parameter_overrides

    def test_should_retry_returns_true_for_retry_action(self):
        """Verify should_retry returns True when action is retry_with_adjustments."""
        mock_diagnosis = _make_mock_diagnosis_low_cai()
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
            state = {}

            should_retry = critic.should_retry(result, state)

        assert should_retry is True
        assert "_parameter_overrides" in state
        assert state["_parameter_overrides"]["design_tool"] == "rnarl"

    def test_should_retry_returns_false_for_proceed_action(self):
        """Verify should_retry returns False when action is proceed_with_filtered."""
        proceed_diagnosis = CriticDiagnosis(
            overall_assessment="Results look good.",
            quality_score=0.85,
            issues=[],
            action="proceed_with_filtered",
            parameter_overrides={},
            reasoning="No critical issues found.",
            confidence=0.9,
        )
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=proceed_diagnosis.model_dump_json()
        )

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            critic = MrnaCdsDesignLLMCritic()
            result = _make_mock_result(cai_values=[0.75, 0.78, 0.80])
            state = {}

            should_retry = critic.should_retry(result, state)

        assert should_retry is False
        assert "_parameter_overrides" not in state

    def test_diagnosis_records_history(self):
        """Verify diagnose appends to _diagnosis_history in state."""
        mock_diagnosis = _make_mock_diagnosis_low_cai()
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
            state = {}

            critic.diagnose(result, state)

        assert "_diagnosis_history" in state
        assert len(state["_diagnosis_history"]) == 1
        assert state["_diagnosis_history"][0]["quality_score"] == 0.25

    def test_parse_diagnosis_from_text_fallback(self):
        """Verify _parse_diagnosis_from_text handles raw JSON fallback."""
        raw_json = """{
            "overall_assessment": "Test fallback parsing",
            "quality_score": 0.5,
            "issues": [
                {
                    "severity": "warning",
                    "category": "test",
                    "description": "Test issue",
                    "affected_candidate_count": 1
                }
            ],
            "action": "abort",
            "parameter_overrides": {},
            "reasoning": "Fallback test",
            "confidence": 0.5
        }"""

        diagnosis = MrnaCdsDesignLLMCritic._parse_diagnosis_from_text(raw_json)
        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score == 0.5
        assert len(diagnosis.issues) == 1
        assert diagnosis.issues[0].category == "test"

    def test_parse_diagnosis_from_text_malformed(self):
        """Verify _parse_diagnosis_from_text returns default on malformed input."""
        diagnosis = MrnaCdsDesignLLMCritic._parse_diagnosis_from_text("not json at all")
        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score == 0.0
        assert diagnosis.action == "abort"
        assert diagnosis.confidence == 0.0

    @pytest.mark.live_llm
    def test_live_diagnosis_low_cai(self):
        """Live test: LLM should detect low CAI and recommend parameter changes."""
        if not os.environ.get("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

        critic = MrnaCdsDesignLLMCritic()
        result = _make_mock_result(cai_values=[0.25, 0.28, 0.30])
        state = {"_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0}}

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.6  # low CAI should score poorly
        assert len(diagnosis.issues) > 0
        # At least one issue should mention CAI
        cai_issues = [
            i
            for i in diagnosis.issues
            if "cai" in i.category.lower() or "CAI" in i.description
        ]
        assert len(cai_issues) > 0
        # Should recommend parameter changes
        assert diagnosis.action in ("retry_with_adjustments", "retry_with_alternative")
        assert len(diagnosis.parameter_overrides) > 0


class TestExecutionControllerParameterOverrides:
    """Tests for ExecutionController's parameter override mechanism."""

    def test_apply_parameter_overrides(self):
        """Verify _apply_parameter_overrides merges parameters correctly."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step1",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST", "design_tool": "all"},
                )
            ]
        )
        state: dict = {}

        controller._apply_parameter_overrides(
            plan, state, {"design_tool": "lineardesign", "lambda_value": 4.0}
        )

        assert plan.steps[0].input_binding["design_tool"] == "lineardesign"
        assert plan.steps[0].input_binding["lambda_value"] == 4.0
        assert plan.steps[0].input_binding["protein_sequence"] == "MKLTEST"
        # Original should be preserved in state
        assert state["_original_input_binding_step1"]["design_tool"] == "all"

    def test_apply_parameter_overrides_filters_unknown_keys(self):
        """Unknown parameter keys should be filtered out."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step1",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST"},
                )
            ]
        )
        state: dict = {}

        controller._apply_parameter_overrides(
            plan,
            state,
            {"__malicious": "value", "protein_sequence": "CHANGED", "not an identifier": 1},
        )

        assert "__malicious" not in plan.steps[0].input_binding
        assert "not an identifier" not in plan.steps[0].input_binding
        assert plan.steps[0].input_binding["protein_sequence"] == "CHANGED"

    def test_apply_parameter_overrides_preserves_original_on_multiple_calls(self):
        """Multiple override calls should apply on top of original, not accumulate."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step1",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={
                        "protein_sequence": "MKLTEST",
                        "design_tool": "all",
                        "lambda_value": 0.0,
                    },
                )
            ]
        )
        state: dict = {}

        controller._apply_parameter_overrides(
            plan, state, {"design_tool": "lineardesign"}
        )
        assert plan.steps[0].input_binding["design_tool"] == "lineardesign"

        controller._apply_parameter_overrides(
            plan, state, {"design_tool": "rnarl"}
        )
        # Should still be based on original, not on the previous override
        assert plan.steps[0].input_binding["design_tool"] == "rnarl"
        assert plan.steps[0].input_binding["protein_sequence"] == "MKLTEST"

    def test_apply_parameter_overrides_skips_capability_steps(self):
        """Parameter overrides should only affect workflow steps."""
        registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="step1",
                    type="capability",
                    target="some_tool",
                    input_binding={"param": "original"},
                ),
                PlanStep(
                    step_id="step2",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST"},
                ),
            ]
        )
        state: dict = {}

        controller._apply_parameter_overrides(plan, state, {"protein_sequence": "CHANGED"})

        # Capability step should be untouched
        assert plan.steps[0].input_binding["param"] == "original"
        # Workflow step should be updated
        assert plan.steps[1].input_binding["protein_sequence"] == "CHANGED"


class TestExecutionControllerWithCriticRetry:
    """End-to-end tests: ExecutionController + Critic + parameter overrides."""

    def test_critic_retry_applies_parameter_overrides(self):
        """Full flow: critic triggers retry, controller applies parameter_overrides to plan."""
        mock_diagnosis = _make_mock_diagnosis_low_cai()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content=mock_diagnosis.model_dump_json()
        )

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            # Set up a minimal stub registry
            registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
            controller = ExecutionController(capability_registry=registry)

            plan = ExecutionPlan(
                steps=[
                    PlanStep(
                        step_id="cds",
                        type="workflow",
                        target="mrna_cds_design",
                        input_binding={
                            "protein_sequence": "MKLTEST",
                            "design_tool": "all",
                        },
                        output_key="cds_result",
                    )
                ],
                max_retries=2,
            )

            # Mock the workflow result that will trigger critic retry
            low_cai_result = _make_mock_result(cai_values=[0.25, 0.28, 0.30])

            # Patch _run_step to return our mock result on first call
            call_count = 0

            def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
                nonlocal call_count
                call_count += 1
                if step.target == "mrna_cds_design":
                    # Store params as real _run_step would
                    state["_last_workflow_params"] = dict(step.input_binding)
                    return low_cai_result
                raise RuntimeError(f"Unexpected step: {step.target}")

            with patch.object(controller, "_run_step", side_effect=_mock_run_step):
                # Also need to mock _resolve_critic to return our critic
                critic = MrnaCdsDesignLLMCritic()

                def _mock_resolve_critic(step, get_critic_fn):
                    if step.target == "mrna_cds_design":
                        return critic
                    return None

                with patch.object(
                    controller, "_resolve_critic", side_effect=_mock_resolve_critic
                ):
                    final_state = controller.execute(plan, {})

        # Retry should have been triggered twice (both runs return low CAI,
        # so critic requests retry each time until max_retries is reached).
        assert final_state.get("retry_count") == 2
        assert "_critic_should_retry" in final_state
        assert final_state["_critic_should_retry"] is True

        # Parameter overrides should have been applied
        assert plan.steps[0].input_binding["design_tool"] == "rnarl"
        assert plan.steps[0].input_binding["lambda_value"] == 1.0
        assert plan.steps[0].input_binding["protein_sequence"] == "MKLTEST"

        # Execution log should record the override events (applied on each retry)
        log = final_state["_execution_log"]
        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) == 2
        assert override_events[0]["overrides"]["design_tool"] == "rnarl"

        # Verify retries_exhausted is recorded since retry_count hit max_retries
        assert any(e.get("retries_exhausted") for e in log if e.get("event") == "plan_complete")

    def test_critic_no_retry_when_quality_good(self):
        """When quality is good, critic should not trigger retry."""
        proceed_diagnosis = CriticDiagnosis(
            overall_assessment="All candidates have excellent CAI.",
            quality_score=0.9,
            issues=[],
            action="proceed_with_filtered",
            parameter_overrides={},
            reasoning="No issues found.",
            confidence=0.95,
        )
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = {"parsed": proceed_diagnosis}
        mock_llm.with_structured_output.return_value = mock_structured

        with patch(
            "agent_core.planning.llm_critic.get_deepseek_llm",
            return_value=mock_llm,
        ):
            registry = CapabilityRegistry(ToolExecutor(ToolRegistry()))
            controller = ExecutionController(capability_registry=registry)

            plan = ExecutionPlan(
                steps=[
                    PlanStep(
                        step_id="cds",
                        type="workflow",
                        target="mrna_cds_design",
                        input_binding={"protein_sequence": "MKLTEST"},
                        output_key="cds_result",
                    )
                ],
                max_retries=2,
            )

            good_result = _make_mock_result(cai_values=[0.75, 0.78, 0.80])

            def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
                if step.target == "mrna_cds_design":
                    state["_last_workflow_params"] = dict(step.input_binding)
                    return good_result
                raise RuntimeError(f"Unexpected step: {step.target}")

            with patch.object(controller, "_run_step", side_effect=_mock_run_step):
                critic = MrnaCdsDesignLLMCritic()

                def _mock_resolve_critic(step, get_critic_fn):
                    if step.target == "mrna_cds_design":
                        return critic
                    return None

                with patch.object(
                    controller, "_resolve_critic", side_effect=_mock_resolve_critic
                ):
                    final_state = controller.execute(plan, {})

        # No retry should have been triggered
        assert final_state.get("retry_count", 0) == 0
        assert "_critic_should_retry" not in final_state
        assert final_state.get("_plan_executed") is True
