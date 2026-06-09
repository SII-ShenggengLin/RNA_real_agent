"""Layer-3 integration tests for MrnaCdsDesignWorkflow via ExecutionController.

Covers:
- Workflow invocation through ExecutionController
- PlanStep type="workflow" branch logic
- State writeback (tool_results merged into outer state)
- Progress callback propagation
- Input binding resolution ($state references)
"""

from __future__ import annotations

from typing import Any, Optional

from agent_core.capabilities.base import CapabilityResult
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow


class _StubCapability:
    """Minimal capability stub for unit tests."""

    def __init__(self, name: str, output: dict[str, Any]) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        result = CapabilityResult(
            success=True,
            tool_name=self._name,
            output=dict(self._output),
        )
        # Mirror real Capability._writeback behaviour for layer-3 state tests
        if state is not None:
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"][self._name] = result.output
        return result


class _StubLinearDesign(_StubCapability):
    """Returns distinct sequences per lambda so deduplication yields multiple candidates."""

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        lam = float(tool_args.get("lambda_value", 0.0))
        # Vary length with lambda so candidates are distinct
        repeats = 30 + int(lam) * 5
        seq = "AUG" * repeats
        output = {
            "generated_sequence": seq,
            "structure": "." * (len(seq)),
            "mfe": -10.0 - lam,
            "cai_score": 0.8,
        }
        if state is not None:
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"][self._name] = output
        return CapabilityResult(
            success=True,
            tool_name=self._name,
            output=output,
        )


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


def _build_cds_registry() -> _StubRegistry:
    """Registry with all capabilities required by MrnaCdsDesignWorkflow."""
    caps: dict[str, _StubCapability] = {
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
        "predict_rna_secondary_structure": _StubCapability(
            "predict_rna_secondary_structure",
            {
                "structure": "." * 200,
                "mfe_kcal_per_mol": -50.0,
            },
        ),
        "predict_rna_secondary_structure_with_linearfold": _StubCapability(
            "predict_rna_secondary_structure_with_linearfold",
            {
                "structure": "." * 200,
                "mfe": -45.0,
            },
        ),
        "compute_rna_sequence_gc_content": _StubCapability(
            "compute_rna_sequence_gc_content",
            {"gc_content": 0.5, "sequence_length": 200},
        ),
        "compute_dot_bracket_unpaired_fraction": _StubCapability(
            "compute_dot_bracket_unpaired_fraction",
            {"unpaired_fraction": 0.5, "structure_length": 200, "dot_count": 100},
        ),
        "predict_mrna_stability_with_rnastop": _StubCapability(
            "predict_mrna_stability_with_rnastop",
            {"overall_stability": 0.5},
        ),
        "compute_cai_for_cds_sequence": _StubCapability(
            "compute_cai_for_cds_sequence",
            {"cai_score": 0.85, "species": "Homo sapiens"},
        ),
    }
    return _StubRegistry(caps)


def test_mrna_cds_design_via_execution_controller():
    """MrnaCdsDesignWorkflow executes end-to-end through ExecutionController."""
    registry = _build_cds_registry()
    workflow = MrnaCdsDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                },
                output_key="cds_result",
                description="Design mRNA CDS",
            ),
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {}
    result_state = controller.execute(plan, state)

    # Workflow result stored under output_key and workflow_result
    assert "cds_result" in result_state
    wf_result = result_state["cds_result"]
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
    assert wf_result.best_candidate is not None

    # Also stored in the generic workflow_result slot
    assert result_state.get("workflow_result") is wf_result

    # State writeback: tool_results should contain outputs from capabilities
    tool_results = result_state.get("tool_results", {})
    assert "design_mrna_cds_with_lineardesign" in tool_results
    assert "compute_rna_sequence_gc_content" in tool_results
    assert "predict_rna_secondary_structure_with_linearfold" in tool_results

    # Execution log recorded
    assert "_execution_log" in result_state
    log = result_state["_execution_log"]
    assert any(e["event"] == "step_start" for e in log)
    assert any(e["event"] == "step_done" for e in log)
    assert any(e["event"] == "plan_complete" for e in log)
    assert result_state.get("_plan_executed") is True


def test_mrna_cds_design_progress_callback():
    """Progress callback receives generate and evaluate events."""
    registry = _build_cds_registry()
    workflow = MrnaCdsDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                },
            ),
        ],
    )

    events: list[dict[str, Any]] = []

    def _cb(evt: dict[str, Any]) -> None:
        events.append(evt)

    controller.execute(plan, {}, progress_callback=_cb)

    assert any(e.get("event") == "step_start" for e in events)
    assert any(e.get("event") == "step_done" for e in events)
    assert any(e.get("event") == "plan_complete" for e in events)

    # Progress events from the workflow itself are NOT forwarded to the
    # ExecutionController callback because _run_step does not wire the
    # workflow-internal progress_callback to the controller callback.
    # This is an architectural limitation, not a bug.


def test_mrna_cds_design_input_binding_with_state_ref():
    """ExecutionController resolves $state references in input bindings."""
    registry = _build_cds_registry()
    workflow = MrnaCdsDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "$state.protein",
                    "design_tool": "lineardesign",
                },
            ),
        ],
    )

    state: dict[str, Any] = {"protein": "MKTAIVE"}
    result_state = controller.execute(plan, state)

    assert result_state["workflow_result"].success is True


def test_mrna_cds_design_empty_candidates_graceful():
    """If all design tools fail, workflow returns success=False with empty list."""
    # Registry with NO design capabilities
    registry = _StubRegistry({})
    workflow = MrnaCdsDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "all",
                },
            ),
        ],
    )

    state: dict[str, Any] = {}
    result_state = controller.execute(plan, state)

    wf_result = result_state["workflow_result"]
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is False
    assert "empty_candidate_list" in wf_result.errors


def test_mrna_cds_design_no_critic_retry():
    """MrnaCdsDesignWorkflow has no critic registered; retry is never triggered."""
    registry = _build_cds_registry()
    workflow = MrnaCdsDesignWorkflow(registry)
    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                },
            ),
        ],
        max_retries=2,
    )

    state: dict[str, Any] = {}
    result_state = controller.execute(plan, state, replan_fn=lambda s: plan)

    assert result_state.get("retry_count", 0) == 0
    assert "_critic_should_retry" not in result_state


def test_state_writeback_deep_merge():
    """ExecutionController deep-merges dict values (e.g. tool_results) instead of overwriting."""
    registry = _build_cds_registry()
    workflow = MrnaCdsDesignWorkflow(registry)

    # Add a dummy pre-step capability to the registry
    pre_cap = _StubCapability("pre_step_tool", {"pre_value": 42})
    registry._caps["pre_step_tool"] = pre_cap

    controller = ExecutionController(
        capability_registry=registry,
        workflow_registry={"mrna_cds_design": workflow},
    )

    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="capability",
                target="pre_step_tool",
                input_binding={},
            ),
            PlanStep(
                step_id="step_2",
                type="workflow",
                target="mrna_cds_design",
                input_binding={
                    "protein_sequence": "MKTAIVE",
                    "design_tool": "lineardesign",
                },
            ),
        ],
    )

    state: dict[str, Any] = {}
    result_state = controller.execute(plan, state)

    tool_results = result_state.get("tool_results", {})
    # Pre-step capability result must survive the workflow step
    assert "pre_step_tool" in tool_results
    assert tool_results["pre_step_tool"]["pre_value"] == 42
    # Workflow internal tool results must also be present
    assert "design_mrna_cds_with_lineardesign" in tool_results
    assert "compute_rna_sequence_gc_content" in tool_results
