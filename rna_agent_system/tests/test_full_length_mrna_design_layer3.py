"""Layer-3 integration tests for FullLengthMrnaDesignWorkflow via ExecutionController.

Covers:
- Workflow invocation through ExecutionController
- State writeback (tool_results merged into outer state)
- Progress callback propagation
- FullLengthMrnaDesignLLMCritic integration (fallback to no-retry when LLM unavailable)
"""

from __future__ import annotations

from typing import Any, Optional

from agent_core.capabilities.base import CapabilityResult
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignLLMCritic,
    FullLengthMrnaDesignWorkflow,
)


class _StubCapability:
    """Minimal capability stub for unit tests."""

    def __init__(self, name: str, output: dict[str, Any]) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    def _build_output(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        return dict(self._output)

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        output = self._build_output(tool_args)
        result = CapabilityResult(
            success=True,
            tool_name=self._name,
            output=output,
        )
        # Mirror Capability._writeback behaviour
        if state is not None:
            state.setdefault("tool_results", {})
            state["tool_results"][self._name] = output
        return result


class _StubLinearDesign(_StubCapability):
    """Returns distinct sequences per lambda so deduplication yields multiple candidates."""

    def _build_output(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        lam = float(tool_args.get("lambda_value", 0.0))
        repeats = 30 + int(lam) * 5
        seq = "AUG" * repeats
        return {
            "generated_sequence": seq,
            "structure": "." * len(seq),
            "mfe": -10.0 - lam,
            "cai_score": 0.8,
        }


class _StubRegistry:
    """Duck-typed registry satisfying CapabilityRegistry interface."""

    def __init__(self, caps: dict[str, _StubCapability]) -> None:
        self._caps = caps

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> _StubCapability:
        return self._caps[name]

    def list_names(self) -> list[str]:
        return sorted(self._caps.keys())


def _build_full_registry(ires_score: float = 0.1) -> _StubRegistry:
    """Registry with all capabilities required by FullLengthMrnaDesignWorkflow."""
    caps: dict[str, _StubCapability] = {
        # CDS design tools (reused by internal MrnaCdsDesignWorkflow)
        "design_mrna_cds_with_lineardesign": _StubLinearDesign(
            "design_mrna_cds_with_lineardesign", {}
        ),
        "design_mrna_cds_with_rnarl": _StubCapability(
            "design_mrna_cds_with_rnarl",
            {"generated_sequence": "AUG" * 35},
        ),
        "design_mrna_cds_with_gemorna": _StubCapability(
            "design_mrna_cds_with_gemorna",
            {"generated_sequence": "AUG" * 40},
        ),
        # Fold & eval tools (reused by internal CDS workflow + full-length)
        "predict_rna_secondary_structure": _StubCapability(
            "predict_rna_secondary_structure",
            {
                "structure": "." * 300,
                "mfe_kcal_per_mol": -60.0,
            },
        ),
        "predict_rna_secondary_structure_with_linearfold": _StubCapability(
            "predict_rna_secondary_structure_with_linearfold",
            {
                "structure": "." * 300,
                "mfe": -55.0,
            },
        ),
        "compute_rna_sequence_gc_content": _StubCapability(
            "compute_rna_sequence_gc_content",
            {"gc_content": 0.5, "sequence_length": 300},
        ),
        "compute_dot_bracket_unpaired_fraction": _StubCapability(
            "compute_dot_bracket_unpaired_fraction",
            {"unpaired_fraction": 0.5, "structure_length": 300, "dot_count": 150},
        ),
        "predict_mrna_stability_with_rnastop": _StubCapability(
            "predict_mrna_stability_with_rnastop",
            {"overall_stability": 0.5},
        ),
        "compute_cai_for_cds_sequence": _StubCapability(
            "compute_cai_for_cds_sequence",
            {"cai_score": 0.85, "species": "Homo sapiens"},
        ),
        # UTR design tools
        "design_5utr_with_gemorna": _StubCapability(
            "design_5utr_with_gemorna",
            {"generated_sequence": "AUGC" * 15},  # 60 nt
        ),
        "design_3utr_with_gemorna": _StubCapability(
            "design_3utr_with_gemorna",
            {"generated_sequence": "AUGC" * 15},  # 60 nt
        ),
        # UTR prediction tools
        "predict_5utr_mrl_with_gemorna": _StubCapability(
            "predict_5utr_mrl_with_gemorna",
            {"predicted_mrl": 5.0},
        ),
        "predict_3utr_stability_with_gemorna": _StubCapability(
            "predict_3utr_stability_with_gemorna",
            {"predicted_stability": 0.8},
        ),
        # IRES prediction (configurable score for critic testing)
        "predict_putative_ires_with_iresfinder": _StubCapability(
            "predict_putative_ires_with_iresfinder",
            {"max_score": ires_score},
        ),
    }
    return _StubRegistry(caps)


def test_full_length_mrna_design_via_execution_controller():
    """FullLengthMrnaDesignWorkflow executes end-to-end through ExecutionController."""
    registry = _build_full_registry(ires_score=0.1)
    workflow = FullLengthMrnaDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"full_length_mrna_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="full_length_mrna_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                    "lambda_value": 0.0,
                    "utr_mode": "short",
                },
                output_key="full_result",
                description="Design full-length mRNA",
            ),
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    assert "full_result" in result_state
    wf_result = result_state["full_result"]
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
    assert wf_result.best_candidate is not None

    # Full-length candidates should contain UTR and CDS metadata
    best = wf_result.best_candidate
    assert "utr5_sequence" in best.metadata
    assert "cds_sequence" in best.metadata
    assert "utr3_sequence" in best.metadata

    # State writeback merged
    tool_results = result_state.get("tool_results", {})
    # Full-length stage tools
    assert "design_5utr_with_gemorna" in tool_results
    assert "design_3utr_with_gemorna" in tool_results
    # CDS sub-workflow tools must also be present (merged, not overwritten)
    assert "design_mrna_cds_with_lineardesign" in tool_results
    assert "compute_rna_sequence_gc_content" in tool_results

    # No critic retry when disabled
    assert result_state.get("retry_count", 0) == 0
    assert "_critic_should_retry" not in result_state


def test_full_length_mrna_design_progress_callback():
    """Progress callback receives step events from ExecutionController."""
    registry = _build_full_registry(ires_score=0.1)
    workflow = FullLengthMrnaDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"full_length_mrna_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="full_length_mrna_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                    "lambda_value": 0.0,
                    "utr_mode": "short",
                },
            ),
        ],
    )

    events: list[dict[str, Any]] = []

    def _cb(evt: dict[str, Any]) -> None:
        events.append(evt)

    controller.execute(plan, {"_llm_critic_enabled": False}, progress_callback=_cb)

    assert any(e.get("event") == "step_start" for e in events)
    assert any(e.get("event") == "step_done" for e in events)
    assert any(e.get("event") == "plan_complete" for e in events)


def test_full_length_mrna_critic_disabled_no_retry():
    """LLM Critic falls back to no-retry when disabled or LLM unavailable."""
    registry = _build_full_registry(ires_score=0.8)
    workflow = FullLengthMrnaDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"full_length_mrna_design": workflow},
    )
    # Disable LLM critic via state flag so it falls back to no-retry
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="full_length_mrna_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                    "lambda_value": 0.0,
                    "utr_mode": "short",
                },
            ),
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {"_llm_critic_enabled": False}
    result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

    # With critic disabled, no retry should happen
    assert result_state.get("retry_count", 0) == 0
    assert "_critic_should_retry" not in result_state


def test_full_length_mrna_critic_build_context_from_controller():
    """LLM Critic's _build_context extracts full-length stats correctly from real workflow output."""
    registry = _build_full_registry(ires_score=0.1)
    workflow = FullLengthMrnaDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"full_length_mrna_design": workflow},
    )
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="full_length_mrna_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                    "lambda_value": 0.0,
                    "utr_mode": "short",
                },
            ),
        ],
    )

    state: dict[str, Any] = {"user_text": "Design a stable mRNA with short UTRs", "_llm_critic_enabled": False}
    result_state = controller.execute(plan, state)

    # ExecutionController stores workflow result in state["workflow_result"]
    wf_result = result_state.get("workflow_result")
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True

    critic = FullLengthMrnaDesignLLMCritic()
    ctx = critic._build_context(wf_result, result_state)

    # Verify full-length specific context is populated
    stats = ctx.get("full_length_stats", {})
    assert "utr5_preset_distribution" in stats
    assert "utr3_preset_distribution" in stats
    assert "cds_source_distribution" in stats
    assert "utr5_mrl_range" in stats
    assert "utr3_stability_range" in stats

    # Best candidate breakdown should exist since we have candidates
    best_breakdown = ctx.get("best_candidate_breakdown")
    assert best_breakdown is not None
    assert best_breakdown.get("utr5_preset") == "short"
    assert best_breakdown.get("utr3_preset") == "short"


def test_llm_critic_unit_disabled():
    """When LLM critic is explicitly disabled, should_retry returns False immediately."""
    critic = FullLengthMrnaDesignLLMCritic()
    result = WorkflowResult(
        success=True,
        task_id="test",
        all_candidates=[],
    )
    state: dict[str, Any] = {"_llm_critic_enabled": False}
    assert critic.should_retry(result, state) is False
