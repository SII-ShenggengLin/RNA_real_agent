"""Tests for PipelineAgent."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.agents.base import AgentResult
from agent_core.agents.pipeline_agent import PipelineAgent
from agent_core.agents.quality_agent import QualityAgent, QualityProfile, QualityReport
from agent_core.agents.specialist_agent import SpecialistAgent
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.pipeline.models import PipelineEdge, PipelineNode, PipelinePlan
from agent_core.workflow_models import Candidate, WorkflowResult


class _DummyWorkflow:
    name = "dummy"
    input_model = None

    def __init__(self, sequence: str = "AUG") -> None:
        self.sequence = sequence

    def run(self, inp: Any, *, progress_callback: Any = None) -> WorkflowResult:
        candidate = Candidate(sequence=inp.get("seq", self.sequence), source="dummy")
        return WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=candidate,
            all_candidates=[candidate],
            summary=f"seq={candidate.sequence}",
        )


def _make_specialist(sequence: str = "AUG") -> SpecialistAgent:
    profile = QualityProfile(
        workflow_name="dummy",
        evaluation_dimensions=["quality"],
        max_retries=0,
    )
    return SpecialistAgent(_DummyWorkflow(sequence), profile)


def _make_quality_agent() -> QualityAgent:
    report = QualityReport(
        overall_assessment="ok", quality_score=1.0, action="pass", reasoning="fine"
    )
    return QualityAgent(llm=_mock_llm(report))


def _mock_llm(report: QualityReport) -> MagicMock:
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=report.model_dump_json())
    return llm


def test_single_node_pipeline() -> None:
    plan = PipelinePlan.single("dummy", {"seq": "AUGCGC"}, plan_id="p1")
    specialist = _make_specialist()
    agent = PipelineAgent(
        {"dummy": specialist},
        _make_quality_agent(),
        SynthesisAgent(enable_llm=False),
    )
    result = agent.execute(plan)
    assert result.success is True
    assert "AUGCGC" in result.final_report


def test_multi_node_pipeline_binding() -> None:
    plan = PipelinePlan(
        plan_id="chain",
        nodes=[
            PipelineNode(
                node_id="cds",
                workflow="dummy",
                static_params={"seq": "AUG"},
                output_alias="cds",
            ),
            PipelineNode(
                node_id="fold",
                workflow="dummy",
                static_params={},
                input_bindings={"seq": "$cds.best_candidate.sequence"},
                output_alias="fold",
            ),
        ],
        edges=[PipelineEdge(source="cds", target="fold")],
    )
    specialist = _make_specialist()
    agent = PipelineAgent(
        {"dummy": specialist},
        _make_quality_agent(),
        SynthesisAgent(enable_llm=False),
    )
    result = agent.execute(plan)
    assert result.success is True
    assert result.node_results["fold"].workflow_result.best_candidate.sequence == "AUG"


def test_critical_failure_aborts() -> None:
    plan = PipelinePlan(
        plan_id="fail",
        nodes=[
            PipelineNode(node_id="a", workflow="dummy", static_params={}),
            PipelineNode(node_id="b", workflow="dummy", static_params={}),
        ],
        edges=[PipelineEdge(source="a", target="b")],
    )

    class _FailSpecialist(SpecialistAgent):
        def run(self, node_id, params, quality_agent, *, state=None, progress_callback=None):
            return AgentResult(
                node_id=node_id,
                workflow="dummy",
                success=False,
                errors=["boom"],
                metadata={"quality_report": QualityReport(
                    overall_assessment="fail", quality_score=0.0, action="abort", reasoning="boom"
                )},
            )

    agent = PipelineAgent(
        {"dummy": _FailSpecialist(None, QualityProfile(workflow_name="dummy"))},
        QualityAgent(llm=MagicMock()),
        SynthesisAgent(enable_llm=False),
    )
    result = agent.execute(plan)
    assert result.success is False
    assert "a" in result.node_results
    assert "boom" in result.errors


def test_quality_state_merged_back_to_shared_state() -> None:
    """SpecialistAgent/QualityAgent state mutations must survive in the shared state."""
    plan = PipelinePlan.single("dummy", {"seq": "AUGCGC"}, plan_id="p1")
    specialist = _make_specialist()
    agent = PipelineAgent(
        {"dummy": specialist},
        _make_quality_agent(),
        SynthesisAgent(enable_llm=False),
    )
    shared_state: dict[str, Any] = {}
    agent.execute(plan, state=shared_state)

    assert "_diagnosis_history" in shared_state
    assert len(shared_state["_diagnosis_history"]) == 1
    assert shared_state["_diagnosis_history"][0]["action"] == "pass"
    assert "_last_diagnosis" in shared_state
    assert shared_state["_last_diagnosis"]["action"] == "pass"
