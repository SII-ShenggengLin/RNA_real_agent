"""Shared test helpers to reduce duplication across test files."""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock

from agent_core.capabilities.base import CapabilityResult
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflow_models import WorkflowResult


def make_mock_capability(output: dict[str, Any]) -> MagicMock:
    """Build a minimal MagicMock capability that returns *output* on invoke."""
    cap = MagicMock()
    cap.invoke.return_value = CapabilityResult(
        success=True,
        tool_name="mock",
        output=output,
    )
    return cap


def build_mock_plan(target: str, input_binding: dict[str, Any]) -> ExecutionPlan:
    """Build a single-step ExecutionPlan for *target* with *input_binding*."""
    return ExecutionPlan(
        steps=[
            PlanStep(
                step_id="s1",
                type="workflow",
                target=target,
                input_binding=input_binding,
                output_key="result",
            )
        ],
        max_retries=2,
    )


def reverse_complement_rna(seq: str) -> str:
    """Return reverse complement of an RNA sequence."""
    rc_map = {"A": "U", "U": "A", "G": "C", "C": "G"}
    return "".join(rc_map.get(base, base) for base in reversed(seq.upper()))


# ═══════════════════════════════════════════════════════════════════════════════
# Shared stub classes (previously duplicated in test_mrna_cds_design_layer3.py
# and test_full_length_mrna_design_layer3.py)
# ═══════════════════════════════════════════════════════════════════════════════


class StubCapability:
    """Minimal capability stub for unit tests.

    Mirrors real :class:`Capability` writeback behaviour so layer-3 state
    tests work without a full registry.
    """

    def __init__(self, name: str, output: dict[str, Any]) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    def _build_output(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        """Subclasses may override to vary output based on *tool_args*."""
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
        if state is not None:
            state.setdefault("tool_results", {})
            state["tool_results"][self._name] = output
        return result


class StubLinearDesign(StubCapability):
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


class StubRegistry:
    """Duck-typed registry satisfying :class:`CapabilityRegistry` interface."""

    def __init__(self, caps: dict[str, StubCapability]) -> None:
        self._caps = caps

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> StubCapability:
        return self._caps[name]

    def list_names(self) -> list[str]:
        return sorted(self._caps.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow-result factories (previously duplicated across comprehensive tests)
# ═══════════════════════════════════════════════════════════════════════════════


def make_low_quality_cds_result() -> WorkflowResult:
    """Return a low-quality :class:`WorkflowResult` for mRNA CDS critic tests."""
    from agent_core.workflow_models import Candidate

    candidates = []
    for i, metric in enumerate([
        {"gc_content": 0.35, "cai_score": 0.5, "mfe": -5.0},
        {"gc_content": 0.36, "cai_score": 0.51, "mfe": -4.8},
    ]):
        c = Candidate(
            sequence="AUG" * 30,
            sequence_type="mrna_cds",
            source=f"tool_variant_{i}",
            metadata={"metrics_bundle": metric},
        )
        c.scores = metric
        candidates.append(c)
    return WorkflowResult(
        success=True,
        task_id="test_low_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low quality CDS design for critic testing",
        errors=[],
    )


def make_good_quality_cds_result() -> WorkflowResult:
    """Return a high-quality :class:`WorkflowResult` for mRNA CDS critic tests."""
    from agent_core.workflow_models import Candidate

    c = Candidate(
        sequence="AUG" * 30,
        sequence_type="mrna_cds",
        source="lineardesign",
        metadata={
            "metrics_bundle": {
                "gc_content": 0.55,
                "cai_score": 0.92,
                "mfe": -150.0,
            }
        },
    )
    c.scores = {
        "gc_content": 0.55,
        "cai_score": 0.92,
        "mfe": -150.0,
    }
    return WorkflowResult(
        success=True,
        task_id="test_good_quality",
        best_candidate=c,
        all_candidates=[c],
        summary="High quality CDS design for critic testing",
        errors=[],
    )


def make_low_quality_sirna_result() -> WorkflowResult:
    """Return a low-quality :class:`WorkflowResult` for siRNA critic tests."""
    from agent_core.workflow_models import Candidate

    candidates = []
    for i, metric in enumerate([
        {"gc_content": 0.35, "binding_energy": -5.0, "off_target_count": 10},
        {"gc_content": 0.36, "binding_energy": -4.8, "off_target_count": 12},
    ]):
        c = Candidate(
            sequence="AUGC" * 5,
            sequence_type="sirna",
            source=f"tool_variant_{i}",
            metadata={"metrics_bundle": metric},
        )
        c.scores = metric
        candidates.append(c)
    return WorkflowResult(
        success=True,
        task_id="test_low_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low quality siRNA design for critic testing",
        errors=[],
    )


def make_good_quality_sirna_result() -> WorkflowResult:
    """Return a high-quality :class:`WorkflowResult` for siRNA critic tests."""
    from agent_core.workflow_models import Candidate

    c = Candidate(
        sequence="AUGC" * 5,
        sequence_type="sirna",
        source="evitar",
        metadata={
            "metrics_bundle": {
                "gc_content": 0.55,
                "binding_energy": -35.0,
                "off_target_count": 0,
            }
        },
    )
    c.scores = {
        "gc_content": 0.55,
        "binding_energy": -35.0,
        "off_target_count": 0,
    }
    return WorkflowResult(
        success=True,
        task_id="test_good_quality",
        best_candidate=c,
        all_candidates=[c],
        summary="High quality siRNA design for critic testing",
        errors=[],
    )


def make_low_quality_tertiary_result() -> WorkflowResult:
    """Return a low-quality :class:`WorkflowResult` for tertiary-structure critic tests."""
    from agent_core.workflow_models import Candidate

    candidates = []
    for i, metric in enumerate([
        {"rmsd": 8.0, "tm_score": 0.3, "gdt_ts": 20.0},
        {"rmsd": 7.5, "tm_score": 0.35, "gdt_ts": 25.0},
    ]):
        c = Candidate(
            sequence="AUGC" * 10,
            sequence_type="rna_tertiary",
            source=f"tool_variant_{i}",
            metadata={"metrics_bundle": metric},
        )
        c.scores = metric
        candidates.append(c)
    return WorkflowResult(
        success=True,
        task_id="test_low_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low quality tertiary structure for critic testing",
        errors=[],
    )


def make_good_quality_tertiary_result() -> WorkflowResult:
    """Return a high-quality :class:`WorkflowResult` for tertiary-structure critic tests."""
    from agent_core.workflow_models import Candidate

    c = Candidate(
        sequence="AUGC" * 10,
        sequence_type="rna_tertiary",
        source="rhofold",
        metadata={
            "metrics_bundle": {
                "rmsd": 2.0,
                "tm_score": 0.95,
                "gdt_ts": 90.0,
            }
        },
    )
    c.scores = {
        "rmsd": 2.0,
        "tm_score": 0.95,
        "gdt_ts": 90.0,
    }
    return WorkflowResult(
        success=True,
        task_id="test_good_quality",
        best_candidate=c,
        all_candidates=[c],
        summary="High quality tertiary structure for critic testing",
        errors=[],
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionController helpers
# ═══════════════════════════════════════════════════════════════════════════════


def build_controller(
    registry,
    workflow,
    workflow_name: str,
) -> ExecutionController:
    """Build an :class:`ExecutionController` with a single workflow registered."""
    return ExecutionController(
        capability_registry=registry,
        workflow_registry={workflow_name: workflow},
    )


def run_workflow_step(
    controller: ExecutionController,
    workflow_name: str,
    input_binding: dict[str, Any],
    output_key: str = "result",
    state: Optional[dict[str, Any]] = None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Execute a single-step plan and return the result state.

    Previously duplicated in ~30 test files.
    """
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target=workflow_name,
                input_binding=input_binding,
                output_key=output_key,
            )
        ],
        max_retries=max_retries,
    )
    return controller.execute(plan, state or {})


def assert_controller_success(
    result_state: dict[str, Any],
    output_key: Optional[str] = None,
    retry_count: int = 0,
) -> None:
    """Assert that a controller execution succeeded with expected log events."""
    assert result_state.get("_plan_executed") is True, "Plan was not executed"
    if output_key is not None:
        assert output_key in result_state, f"Missing output_key: {output_key}"
    assert result_state.get("retry_count", 0) == retry_count, (
        f"Unexpected retry_count: {result_state.get('retry_count')}"
    )
    assert "_critic_should_retry" not in result_state

    log = result_state.get("_execution_log", [])
    assert any(e.get("event") == "step_start" for e in log), "Missing step_start event"
    assert any(e.get("event") == "step_done" for e in log), "Missing step_done event"
    assert any(e.get("event") == "plan_complete" for e in log), "Missing plan_complete event"


def collect_progress_events(
    controller: ExecutionController,
    plan: ExecutionPlan,
    state: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Execute a plan with a progress callback and return captured events."""
    events: list[dict[str, Any]] = []
    controller.execute(plan, state or {}, progress_callback=events.append)
    return events


# ═══════════════════════════════════════════════════════════════════════════════
# Assertion helpers
# ═══════════════════════════════════════════════════════════════════════════════


def assert_state_writeback(
    result: WorkflowResult,
    expected_keys: Optional[list[str]] = None,
) -> None:
    """Assert that a workflow result carries the expected state writeback keys."""
    assert hasattr(result, "_state_writeback"), "Missing _state_writeback attribute"
    wb = getattr(result, "_state_writeback", {})
    assert "_workflow_params" in wb, "Missing _workflow_params in writeback"
    for k in expected_keys or []:
        assert k in wb, f"Missing expected key in writeback: {k}"


def assert_progress_events(
    events: list[dict[str, Any]],
    expected: set[str],
) -> None:
    """Assert that *events* contains all event types in *expected*."""
    event_types = {e.get("event") for e in events}
    missing = expected - event_types
    assert not missing, f"Missing progress events: {missing}"
