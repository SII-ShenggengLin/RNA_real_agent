"""Tests for agent_core.calibrated.self_model."""

from __future__ import annotations

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import CapabilityAssessment, CapabilityRecord
from agent_core.calibrated.self_model import TRANSFER_CONFIDENCE_DECAY, SelfModel


def _record(family: str, grade: str = "failed", confidence: float = 0.9) -> CapabilityRecord:
    return CapabilityRecord(
        oracle="egarps_native_probability",
        task_type="aptamer_affinity",
        target_family=family,
        capabilities={"screening": CapabilityAssessment(grade=grade, confidence=confidence)},
    )


def test_query_exact_hit():
    model = SelfModel([_record("thrombin")])
    got = model.query("egarps_native_probability", "aptamer_affinity", "thrombin")
    assert got.assessment("screening").grade == "failed"
    assert got.assessment("screening").confidence == 0.9


def test_query_unprofiled_when_nothing_known():
    model = SelfModel()
    got = model.query("proteinx_iptm", "aptamer_affinity", "vegf")
    assert got.oracle == "proteinx_iptm"
    assert got.target_family == "vegf"
    assert got.assessment("screening").grade == "unprofiled"
    assert got.assessment("ranking").grade == "unprofiled"


def test_query_transfer_from_other_family_downgrades_confidence():
    model = SelfModel([_record("thrombin", grade="verified", confidence=0.8)])
    got = model.query("egarps_native_probability", "aptamer_affinity", "vegf")
    cell = got.assessment("screening")
    assert cell.grade == "transferred"
    assert cell.confidence == round(0.8 * TRANSFER_CONFIDENCE_DECAY, 4)
    assert cell.source_case_id == "egarps_native_probability:aptamer_affinity:thrombin"
    assert cell.transferred_from_grade == "verified"


def test_no_transfer_across_task_type():
    model = SelfModel([_record("thrombin")])
    got = model.query("egarps_native_probability", "small_molecule_binding", "thrombin")
    assert got.assessment("screening").grade == "unprofiled"


def test_update_emits_audit_event(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    model = SelfModel(audit=trail)
    model.update(_record("thrombin"))
    events = trail.events()
    assert len(events) == 1
    assert events[0].event_type == "self_model_update"
    assert events[0].payload["grades"] == {"screening": "failed"}


def test_to_dict_from_dict_roundtrip():
    model = SelfModel([_record("thrombin"), _record("vegf", grade="verified", confidence=0.7)])
    restored = SelfModel.from_dict(model.to_dict())
    assert {r.target_family for r in restored.records()} == {"thrombin", "vegf"}
    assert restored.query("egarps_native_probability", "aptamer_affinity", "vegf").assessment(
        "screening"
    ).grade == "verified"
