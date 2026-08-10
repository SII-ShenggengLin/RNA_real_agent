"""Tests for agent_core.calibrated.claim_gate."""

from __future__ import annotations

from types import SimpleNamespace

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.claim_gate import ClaimGate
from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    ClaimDependency,
)
from agent_core.calibrated.self_model import SelfModel


def _model(grade: str, family: str = "thrombin", confidence: float = 0.9) -> SelfModel:
    return SelfModel([
        CapabilityRecord(
            oracle="oracle_x",
            task_type="aptamer_affinity",
            target_family=family,
            capabilities={"ranking": CapabilityAssessment(grade=grade, confidence=confidence)},
        )
    ])


def _claim(scope: str = "absolute") -> Claim:
    return Claim(
        claim_id="c1",
        text="Candidate A has higher affinity than candidate B.",
        scope=scope,
        dependencies=[ClaimDependency(oracle="oracle_x", capability="ranking")],
    )


def test_pass_when_verified():
    gate = ClaimGate(_model("verified"))
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="thrombin")
    assert v.verdict == "pass"
    assert v.dependencies[0].grade == "verified"


def test_reject_when_unprofiled():
    gate = ClaimGate(SelfModel())
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="thrombin")
    assert v.verdict == "reject"
    assert "profiled" in v.reason


def test_reject_when_failed():
    gate = ClaimGate(_model("failed"))
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="thrombin")
    assert v.verdict == "reject"


def test_downgrade_when_transferred_verified():
    gate = ClaimGate(_model("verified", family="thrombin"))
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="vegf")
    assert v.verdict == "downgrade"
    assert v.dependencies[0].grade == "transferred"
    assert "Within vegf only" in v.rewritten_text
    assert "[DOWNGRADED:" in v.rewritten_text


def test_downgrade_ladder_rejects_at_trend_only():
    gate = ClaimGate(_model("verified", family="thrombin"))
    [v] = gate.review([_claim(scope="trend_only")], task_type="aptamer_affinity", target_family="vegf")
    assert v.verdict == "reject"


def test_transferred_failed_rejects():
    gate = ClaimGate(_model("failed", family="thrombin"))
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="vegf")
    assert v.verdict == "reject"


def test_no_dependencies_passes():
    gate = ClaimGate(SelfModel())
    claim = Claim(claim_id="c0", text="GC content is 0.52.", dependencies=[])
    [v] = gate.review([claim], task_type="aptamer_affinity", target_family="thrombin")
    assert v.verdict == "pass"


def test_comparative_claim_without_basis_rejected():
    gate = ClaimGate(SelfModel())
    for ctype in ("ranking", "screening"):
        claim = Claim(claim_id=f"c_{ctype}", text="X is best.", claim_type=ctype, dependencies=[])
        [v] = gate.review([claim], task_type="aptamer_affinity", target_family="thrombin")
        assert v.verdict == "reject"
        assert "evidentiary basis" in v.reason


def test_llm_polish_replaces_template():
    class _MockLLM:
        def invoke(self, messages):
            return SimpleNamespace(content="[DOWNGRADED] Polished cautious wording.")

    gate = ClaimGate(
        _model("verified", family="thrombin"),
        llm=_MockLLM(),
        polish_with_llm=True,
    )
    [v] = gate.review([_claim()], task_type="aptamer_affinity", target_family="vegf")
    assert v.rewritten_text == "[DOWNGRADED] Polished cautious wording."


def test_audit_events(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    gate = ClaimGate(_model("failed"), audit=trail)
    gate.review([_claim()], task_type="aptamer_affinity", target_family="thrombin")
    events = [e for e in trail.events() if e.event_type == "claim_verdict"]
    assert len(events) == 1
    assert events[0].payload["verdict"] == "reject"
    assert events[0].payload["grades"] == {"oracle_x": "failed"}
