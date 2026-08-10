"""Tests for SpecialistAgent."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.agents.quality_agent import QualityAgent, QualityProfile, QualityReport
from agent_core.agents.specialist_agent import SpecialistAgent
from agent_core.workflow_models import Candidate, WorkflowResult


class _DummyWorkflow:
    name = "dummy"
    input_model = None

    def __init__(self, sequences: list[str] | None = None) -> None:
        self.sequences = sequences or ["AUG"]
        self.run_calls: list[Any] = []
        self.partial_calls: list[Any] = []

    def run(self, inp: Any, *, progress_callback: Any = None) -> WorkflowResult:
        self.run_calls.append(inp)
        candidate = Candidate(sequence=self.sequences[len(self.run_calls) % len(self.sequences)], source="dummy")
        return WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=candidate,
            all_candidates=[candidate],
            summary="done",
        )

    def partial_rerun(
        self, inp: Any, existing: list[Any], *, progress_callback: Any = None
    ) -> WorkflowResult | None:
        self.partial_calls.append((inp, existing))
        candidate = existing[0]
        candidate.scores = {"x": 1.0}
        return WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=candidate,
            all_candidates=[candidate],
            summary="partial",
        )


def _make_quality_agent(report: QualityReport) -> QualityAgent:
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=report.model_dump_json())
    return QualityAgent(llm=llm)


def test_specialist_pass() -> None:
    workflow = _DummyWorkflow()
    profile = QualityProfile(workflow_name="dummy", max_retries=2)
    agent = SpecialistAgent(workflow, profile)
    report = QualityReport(
        overall_assessment="ok", quality_score=1.0, action="pass", reasoning="fine"
    )
    result = agent.run("n1", {}, _make_quality_agent(report))
    assert result.success is True
    assert result.metadata["quality_report"].action == "pass"
    assert workflow.run_calls == [{}]


def test_specialist_retry_then_pass() -> None:
    workflow = _DummyWorkflow(sequences=["AUG", "AUGG"])
    profile = QualityProfile(workflow_name="dummy", max_retries=2)
    agent = SpecialistAgent(workflow, profile)

    class _Agent(QualityAgent):
        def __init__(self) -> None:
            super().__init__(llm=MagicMock())
            self.calls = 0

        def review(self, result, profile, state):
            self.calls += 1
            if self.calls == 1:
                return QualityReport(
                    overall_assessment="low",
                    quality_score=0.3,
                    action="retry_with_adjustments",
                    reasoning="retry",
                    parameter_overrides={"x": 1},
                )
            return QualityReport(
                overall_assessment="ok",
                quality_score=0.9,
                action="pass",
                reasoning="fine",
            )

    result = agent.run("n1", {"x": 0}, _Agent(), state={"_quality_auto_retry": True})
    assert result.success is True
    assert len(workflow.run_calls) == 2
    assert workflow.run_calls[1] == {"x": 1}


def test_specialist_evaluator_only_partial_rerun() -> None:
    workflow = _DummyWorkflow()
    profile = QualityProfile(
        workflow_name="dummy",
        max_retries=2,
        evaluator_only_params={"run_fold"},
        param_to_evaluators={"run_fold": ["FoldEvaluator"]},
    )
    agent = SpecialistAgent(workflow, profile)

    class _Agent(QualityAgent):
        def __init__(self) -> None:
            super().__init__(llm=MagicMock())
            self.calls = 0

        def review(self, result, profile, state):
            self.calls += 1
            if self.calls == 1:
                return QualityReport(
                    overall_assessment="fold suspicious",
                    quality_score=0.5,
                    action="retry_with_adjustments",
                    reasoning="skip fold",
                    parameter_overrides={"run_fold": False},
                    evaluator_only=True,
                    affected_evaluators=["FoldEvaluator"],
                )
            return QualityReport(
                overall_assessment="ok", quality_score=0.9, action="pass", reasoning="fine"
            )

    result = agent.run(
        "n1", {"run_fold": True}, _Agent(), state={"_quality_auto_retry": True}
    )
    assert result.success is True
    assert len(workflow.partial_calls) == 1


def test_specialist_protects_user_explicit_params() -> None:
    workflow = _DummyWorkflow(sequences=["AUG", "AUGG"])
    profile = QualityProfile(workflow_name="dummy", max_retries=2)
    agent = SpecialistAgent(workflow, profile)

    class _Agent(QualityAgent):
        def review(self, result, profile, state):
            return QualityReport(
                overall_assessment="low",
                quality_score=0.3,
                action="retry_with_adjustments",
                reasoning="retry",
                parameter_overrides={"x": 99},
            )

    result = agent.run(
        "n1",
        {"x": 0},
        _Agent(),
        state={"_user_explicit_params": ["x"], "_quality_auto_retry": True},
    )
    assert result.success is True
    assert workflow.run_calls == [{"x": 0}]


class _HardFailureWorkflow:
    """Workflow that fails on the first call, then succeeds."""

    name = "dummy"
    input_model = None

    def __init__(self, sequences: list[str] | None = None) -> None:
        self.sequences = sequences or ["AUG"]
        self.run_calls: list[Any] = []

    def run(self, inp: Any, *, progress_callback: Any = None) -> WorkflowResult:
        self.run_calls.append(inp)
        if len(self.run_calls) == 1:
            return WorkflowResult(
                success=False,
                task_id="t1",
                best_candidate=None,
                all_candidates=[],
                summary="failed",
            )
        candidate = Candidate(
            sequence=self.sequences[(len(self.run_calls) - 1) % len(self.sequences)],
            source="dummy",
        )
        return WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=candidate,
            all_candidates=[candidate],
            summary="done",
        )


def test_specialist_advisory_mode_ignores_soft_retry() -> None:
    """Advisory mode (auto_retry=False) should not retry soft quality suggestions."""
    workflow = _DummyWorkflow()
    profile = QualityProfile(workflow_name="dummy", max_retries=2)
    agent = SpecialistAgent(workflow, profile)

    class _Agent(QualityAgent):
        def review(self, result, profile, state):
            return QualityReport(
                overall_assessment="could be better",
                quality_score=0.6,
                action="retry_with_adjustments",
                reasoning="soft suggestion",
                parameter_overrides={"x": 1},
            )

    result = agent.run(
        "n1", {"x": 0}, _Agent(), state={"_quality_auto_retry": False}
    )
    assert result.success is True
    assert workflow.run_calls == [{"x": 0}]


def test_specialist_advisory_mode_retries_hard_failure() -> None:
    """Advisory mode should still retry genuine hard failures."""
    workflow = _HardFailureWorkflow(sequences=["AUG", "AUGG"])
    profile = QualityProfile(workflow_name="dummy", max_retries=2)
    agent = SpecialistAgent(workflow, profile)

    class _Agent(QualityAgent):
        def __init__(self) -> None:
            super().__init__(llm=MagicMock())
            self.calls = 0

        def review(self, result, profile, state):
            self.calls += 1
            if self.calls == 1:
                return QualityReport(
                    overall_assessment="hard failure",
                    quality_score=0.0,
                    action="retry_with_adjustments",
                    reasoning="retry",
                    parameter_overrides={"x": 1},
                )
            return QualityReport(
                overall_assessment="ok",
                quality_score=1.0,
                action="pass",
                reasoning="fine",
            )

    result = agent.run(
        "n1", {"x": 0}, _Agent(), state={"_quality_auto_retry": False}
    )
    assert result.success is True
    assert len(workflow.run_calls) == 2
    assert workflow.run_calls[1] == {"x": 1}


def test_specialist_abort_is_advisory_only() -> None:
    """An LLM-chosen abort must not flip a successful run to failed.

    Regression test for the 2026-07 hallucinated-abort incident (Myoglobin r3):
    the abort stays in the quality report metadata as an advisory opinion.
    """
    workflow = _DummyWorkflow()
    profile = QualityProfile(
        workflow_name="dummy", evaluation_dimensions=["quality"], max_retries=2
    )
    agent = SpecialistAgent(workflow, profile)
    report = QualityReport(
        overall_assessment="hallucinated abort",
        quality_score=0.0,
        action="abort",
        reasoning="no user request",
    )
    result = agent.run("n1", {}, _make_quality_agent(report))
    assert result.success is True
    assert result.workflow_result is not None
    assert result.workflow_result.success is True
    # The advisory abort is still recorded for audit.
    assert result.metadata["quality_report"].action == "abort"
