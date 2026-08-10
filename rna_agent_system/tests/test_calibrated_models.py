"""Tests for agent_core.calibrated.models (schema round-trips and validation)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.calibrated.models import (
    CAPABILITY_KINDS,
    AuditEvent,
    CampaignRecord,
    CapabilityAssessment,
    CapabilityRecord,
    ClaimDependency,
    ClaimVerdict,
    EvidencePointer,
    GateDecision,
    PlannedAction,
)


def test_capability_kinds_cover_casf_four():
    assert set(CAPABILITY_KINDS) == {"scoring", "screening", "ranking", "docking"}


def test_capability_record_roundtrip():
    rec = CapabilityRecord(
        oracle="egarps_native_probability",
        task_type="aptamer_affinity",
        target_family="thrombin",
        capabilities={
            "screening": CapabilityAssessment(
                grade="failed",
                confidence=0.9,
                metrics={"auroc": 0.286},
                evidence=[EvidencePointer(kind="summary_json", path="e1_capability_summary_v2.json")],
                profiled_at="2026-08-04T00:00:00+00:00",
            )
        },
    )
    payload = rec.model_dump(mode="json")
    restored = CapabilityRecord.model_validate(payload)
    assert restored.key() == ("egarps_native_probability", "aptamer_affinity", "thrombin")
    assert restored.assessment("screening").grade == "failed"
    # Missing cells default to unprofiled.
    assert restored.assessment("ranking").grade == "unprofiled"
    assert restored.assessment("docking").confidence == 0.0


def test_assessment_confidence_bounds():
    with pytest.raises(ValidationError):
        CapabilityAssessment(grade="verified", confidence=1.5)


def test_invalid_capability_grade_rejected():
    with pytest.raises(ValidationError):
        CapabilityAssessment(grade="maybe")


def test_gate_decision_verdicts():
    for verdict in ("allow", "substitute", "downgrade", "reject", "require_profiling"):
        dec = GateDecision(action_id="a1", verdict=verdict)
        assert dec.verdict == verdict
    with pytest.raises(ValidationError):
        GateDecision(action_id="a1", verdict="yolo")


def test_planned_action_use_literals():
    action = PlannedAction(action_id="a1", kind="evaluate", oracle="proteinx_iptm", use="ranking_objective")
    assert action.use == "ranking_objective"
    with pytest.raises(ValidationError):
        PlannedAction(action_id="a2", kind="evaluate", use="magic")


def test_claim_verdict_roundtrip():
    verdict = ClaimVerdict(
        claim_id="c1",
        verdict="downgrade",
        dependencies=[ClaimDependency(oracle="rhofold_plddt", capability="ranking", grade="failed")],
        rewritten_text="Within-target relative trend only.",
    )
    restored = ClaimVerdict.model_validate(verdict.model_dump(mode="json"))
    assert restored.dependencies[0].grade == "failed"
    assert restored.rewritten_text == "Within-target relative trend only."


def test_campaign_record_and_audit_event_roundtrip():
    rec = CampaignRecord(
        campaign_id="camp_001",
        task_type="aptamer_affinity",
        target_family="thrombin",
        target_features={"length_nt": 32, "gc": 0.5},
        created_at="2026-08-04T00:00:00+00:00",
    )
    assert CampaignRecord.model_validate(rec.model_dump(mode="json")).campaign_id == "camp_001"

    event = AuditEvent(event_type="gate_decision", payload={"action_id": "a1"}, timestamp="t")
    assert AuditEvent.model_validate(event.model_dump(mode="json")).event_type == "gate_decision"
    with pytest.raises(ValidationError):
        AuditEvent(event_type="mystery", payload={}, timestamp="t")
