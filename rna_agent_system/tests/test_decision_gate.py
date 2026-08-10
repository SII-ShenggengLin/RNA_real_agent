"""Tests for agent_core.calibrated.decision_gate."""

from __future__ import annotations

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.models import CapabilityAssessment, CapabilityRecord, PlannedAction
from agent_core.calibrated.self_model import SelfModel


def _model_with(grade: str, family: str = "thrombin") -> SelfModel:
    return SelfModel([
        CapabilityRecord(
            oracle="oracle_x",
            task_type="aptamer_affinity",
            target_family=family,
            capabilities={"ranking": CapabilityAssessment(grade=grade, confidence=0.9)},
        )
    ])


def _action(use: str = "ranking_objective", oracle: str | None = "oracle_x") -> PlannedAction:
    return PlannedAction(action_id="a1", kind="evaluate", oracle=oracle, use=use)


def test_verified_allows():
    gate = DecisionGate(_model_with("verified"))
    [d] = gate.review([_action()], task_type="aptamer_affinity", target_family="thrombin")
    assert d.verdict == "allow"
    assert d.required_capability == "ranking"


def test_failed_rejects_with_substitute():
    gate = DecisionGate(_model_with("failed"))
    [d] = gate.review([_action()], task_type="aptamer_affinity", target_family="thrombin")
    assert d.verdict == "reject"
    assert d.substitute == {"use": "scoring_annotation"}


def test_unprofiled_requires_profiling():
    gate = DecisionGate(SelfModel())
    [d] = gate.review([_action()], task_type="aptamer_affinity", target_family="thrombin")
    assert d.verdict == "require_profiling"


def test_transferred_verified_downgrades():
    gate = DecisionGate(_model_with("verified", family="thrombin"))
    [d] = gate.review([_action()], task_type="aptamer_affinity", target_family="vegf")
    assert d.verdict == "downgrade"
    assert "transferred" in d.reason


def test_transferred_failed_rejects():
    gate = DecisionGate(_model_with("failed", family="thrombin"))
    [d] = gate.review([_action()], task_type="aptamer_affinity", target_family="vegf")
    assert d.verdict == "reject"


def test_annotation_and_none_always_allowed():
    gate = DecisionGate(SelfModel())
    decisions = gate.review(
        [_action(use="scoring_annotation"), _action(use="none", oracle=None)],
        task_type="aptamer_affinity",
        target_family="thrombin",
    )
    assert [d.verdict for d in decisions] == ["allow", "allow"]


def test_screening_use_requires_screening_grade():
    model = SelfModel([
        CapabilityRecord(
            oracle="oracle_x",
            task_type="aptamer_affinity",
            target_family="thrombin",
            capabilities={"ranking": CapabilityAssessment(grade="verified", confidence=0.9)},
        )
    ])
    gate = DecisionGate(model)
    [d] = gate.review([_action(use="screening_evaluation")],
                      task_type="aptamer_affinity", target_family="thrombin")
    # Only ranking was profiled; screening stays unprofiled.
    assert d.verdict == "require_profiling"
    assert d.required_capability == "screening"


def test_audit_events_emitted(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    gate = DecisionGate(_model_with("failed"), audit=trail)
    gate.review([_action(), _action(use="none", oracle=None)],
                task_type="aptamer_affinity", target_family="thrombin")
    events = [e for e in trail.events() if e.event_type == "gate_decision"]
    assert [e.payload["verdict"] for e in events] == ["reject", "allow"]
