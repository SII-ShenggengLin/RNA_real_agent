"""Tests for QualityAgent and QualityProfile."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.agents.quality_agent import (
    QualityAgent,
    QualityIssue,
    QualityProfile,
    QualityReport,
)
from agent_core.quality_profiles import MRNA_CDS_QUALITY_PROFILE
from agent_core.workflow_models import Candidate, WorkflowResult


def _make_result(sequence: str = "AUGCGC", success: bool = True) -> WorkflowResult:
    candidate = Candidate(sequence=sequence, source="test")
    return WorkflowResult(
        success=success,
        task_id="t1",
        best_candidate=candidate,
        all_candidates=[candidate],
        summary="ok",
    )


def _mock_llm(report: QualityReport) -> MagicMock:
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=report.model_dump_json())
    return llm


def test_quality_agent_pass() -> None:
    report = QualityReport(
        overall_assessment="Looks good",
        quality_score=0.9,
        action="pass",
        reasoning="No issues",
    )
    agent = QualityAgent(llm=_mock_llm(report))
    state: dict[str, Any] = {"_last_workflow_params": {}}
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.action == "pass"
    assert out.quality_score == 0.9
    assert "_diagnosis_history" in state


def test_quality_agent_retry_with_overrides() -> None:
    report = QualityReport(
        overall_assessment="CAI low",
        quality_score=0.4,
        action="retry_with_adjustments",
        reasoning="Increase lambda",
        parameter_overrides={"lambda_value": 5.0},
    )
    agent = QualityAgent(llm=_mock_llm(report))
    state: dict[str, Any] = {"_last_workflow_params": {}}
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.action == "retry_with_adjustments"
    assert out.parameter_overrides == {"lambda_value": 5.0}
    assert state["_parameter_overrides"] == {"lambda_value": 5.0}


def test_quality_agent_protects_user_explicit_params() -> None:
    report = QualityReport(
        overall_assessment="CAI low",
        quality_score=0.4,
        action="retry_with_adjustments",
        reasoning="Increase lambda",
        parameter_overrides={"lambda_value": 5.0, "design_tool": "lineardesign"},
    )
    agent = QualityAgent(llm=_mock_llm(report))
    state: dict[str, Any] = {
        "_last_workflow_params": {},
        "_user_explicit_params": ["design_tool"],
    }
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert "design_tool" not in out.parameter_overrides
    assert "lambda_value" in out.parameter_overrides


def test_quality_agent_hard_failure_forces_retry() -> None:
    report = QualityReport(
        overall_assessment="Looks good",
        quality_score=0.9,
        action="pass",
        reasoning="No issues",
    )
    agent = QualityAgent(llm=_mock_llm(report))
    state: dict[str, Any] = {"_last_workflow_params": {}}
    result = _make_result(success=False)
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.action == "retry_with_adjustments"


def test_quality_agent_evaluator_only_hint() -> None:
    report = QualityReport(
        overall_assessment="Fold suspicious",
        quality_score=0.6,
        action="retry_with_adjustments",
        reasoning="Re-run fold",
        parameter_overrides={"run_fold": False},
    )
    agent = QualityAgent(llm=_mock_llm(report))
    state: dict[str, Any] = {"_last_workflow_params": {}}
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.evaluator_only is True
    assert "SecondaryStructureEvaluator" in out.affected_evaluators


def test_quality_agent_disabled() -> None:
    agent = QualityAgent(llm=MagicMock())
    state: dict[str, Any] = {
        "_last_workflow_params": {},
        "_quality_review_enabled": False,
    }
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.action == "pass"


def test_parse_report_from_text_fallback() -> None:
    raw = '{"overall_assessment": "ok", "quality_score": 0.8, "action": "pass", "reasoning": "fine"}'
    report = QualityAgent._parse_report_from_text(f"```json\n{raw}\n```")
    assert report.action == "pass"


def test_profile_registry_covers_workflows() -> None:
    from agent_core.quality_profiles import QUALITY_PROFILES

    expected = {
        "mrna_cds_design",
        "sirna_design",
        "sgrna_design",
        "ires_prediction",
        "rna_secondary_structure_design",
        "rna_tertiary_structure_design",
        "full_length_mrna_design",
        "rna_aptamer_design",
        "mrna_sequence_scoring",
        "aso_target_screening",
        "rna_small_molecule_interaction",
    }
    assert set(QUALITY_PROFILES.keys()) == expected


def test_quality_agent_llm_failure_marks_review_unavailable() -> None:
    """LLM infrastructure failure → review_unavailable pass, never abort.

    Regression test for the 2026-07 DeepSeek-402 incident: the old fallback
    returned action="abort" on any exception and killed successful runs.
    """
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("HTTP 402: insufficient balance")
    agent = QualityAgent(llm=llm)
    state: dict[str, Any] = {"_last_workflow_params": {}}
    result = _make_result()
    out = agent.review(result, MRNA_CDS_QUALITY_PROFILE, state)
    assert out.action == "pass"
    assert out.confidence == 0.0
    assert "review_unavailable" in out.overall_assessment
    assert state["_quality_review_error"]["type"] == "RuntimeError"
    assert "402" in state["_quality_review_error"]["message"]
