"""Tests for agent_core.calibrated.case_memory and audit_trail."""

from __future__ import annotations

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.case_memory import CaseMemory
from agent_core.calibrated.models import CampaignRecord, CapabilityAssessment, CapabilityRecord
from agent_core.calibrated.self_model import SelfModel


def _campaign(cid: str, task_type: str, family: str, length: float) -> CampaignRecord:
    return CampaignRecord(
        campaign_id=cid,
        task_type=task_type,
        target_family=family,
        target_features={"length_nt": length},
        created_at="2026-08-04T00:00:00+00:00",
    )


def test_audit_trail_append_and_read(tmp_path):
    trail = AuditTrail(tmp_path / "sub" / "audit.jsonl")
    trail.record("gate_decision", {"action_id": "a1", "verdict": "reject"})
    trail.record("budget_event", {"spent": 10})
    events = trail.events()
    assert [e.event_type for e in events] == ["gate_decision", "budget_event"]
    assert events[0].payload["verdict"] == "reject"
    assert events[0].timestamp  # filled automatically


def test_audit_trail_missing_file_is_empty(tmp_path):
    assert AuditTrail(tmp_path / "nope.jsonl").events() == []


def test_case_memory_add_and_list(tmp_path):
    mem = CaseMemory(tmp_path)
    mem.add_campaign(_campaign("c1", "aptamer_affinity", "thrombin", 32))
    mem.add_campaign(_campaign("c2", "mrna_cds", "covid", 1200))
    assert [c.campaign_id for c in mem.campaigns()] == ["c1", "c2"]


def test_case_memory_similar_ranking_deterministic(tmp_path):
    mem = CaseMemory(tmp_path)
    mem.add_campaign(_campaign("c_same", "aptamer_affinity", "thrombin", 30))
    mem.add_campaign(_campaign("c_family", "aptamer_affinity", "vegf", 30))
    mem.add_campaign(_campaign("c_other", "mrna_cds", "covid", 30))

    hits = mem.similar("aptamer_affinity", "thrombin", {"length_nt": 32}, k=3)
    ids = [c.campaign_id for c in hits]
    # task_type+family match beats task_type-only, which beats no match.
    assert ids[0] == "c_same"
    assert ids[1] == "c_family"
    assert ids[2] == "c_other"
    # Deterministic: repeated call gives the same order.
    assert [c.campaign_id for c in mem.similar("aptamer_affinity", "thrombin", {"length_nt": 32}, k=3)] == ids


def test_case_memory_self_model_roundtrip(tmp_path):
    mem = CaseMemory(tmp_path)
    model = SelfModel(
        [
            CapabilityRecord(
                oracle="rhofold_plddt",
                task_type="aptamer_affinity",
                target_family="pdgf_bb",
                capabilities={"ranking": CapabilityAssessment(grade="failed", confidence=0.8)},
            )
        ]
    )
    mem.save_self_model(model)
    restored = mem.load_self_model()
    cell = restored.query("rhofold_plddt", "aptamer_affinity", "pdgf_bb").assessment("ranking")
    assert cell.grade == "failed"
    assert cell.confidence == 0.8


def test_case_memory_load_missing_self_model_is_empty(tmp_path):
    mem = CaseMemory(tmp_path)
    assert mem.load_self_model().records() == []
