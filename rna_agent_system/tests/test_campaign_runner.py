"""Tests for agent_core.calibrated.campaign_runner (seven-step flow)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_core.calibrated.campaign_runner import CalibratedCampaignRunner
from agent_core.calibrated.experiment_planner import CampaignDeclaration
from agent_core.calibrated.models import Claim, ClaimDependency, PlannedAction


def _anchor_set(path: Path) -> Path:
    entries = []
    for i, seq in enumerate(("GCGCGC", "GCGCAU", "GCAUAU", "GUAUAU")):
        entries.append({
            "id": f"b{i}", "name": f"b{i}", "target": "t1", "sequence": seq,
            "alphabet": "rna", "length_nt": len(seq), "kd_nm": float(10 ** i),
            "role": "binder", "ranking_eligible": True,
        })
    for i, seq in enumerate(("AUAUAU", "AUAAUA", "AAUUAA")):
        entries.append({
            "id": f"n{i}", "name": f"n{i}", "target": "t1", "sequence": seq,
            "alphabet": "rna", "length_nt": len(seq), "kd_nm": None, "role": "negative",
        })
    path.write_text(json.dumps({"entries": entries, "n_entries": len(entries)}), encoding="utf-8")
    return path


def test_run_campaign_end_to_end(tmp_path):
    anchor = _anchor_set(tmp_path / "anchors.json")
    runner = CalibratedCampaignRunner(
        case_memory_root=tmp_path / "memory",
        audit_path=tmp_path / "audit.jsonl",
    )

    declaration = CampaignDeclaration.model_validate({
        "claims": [{
            "claim_id": "c1", "text": "screening separates binders",
            "scope": "within_target_relative",
            "dependencies": [{"oracle": "gc_content", "capability": "screening"}],
        }],
        "actions": [
            {"action_id": "screen", "kind": "evaluate", "oracle": "gc_content",
             "use": "screening_evaluation", "estimated_budget": 4},
            {"action_id": "rank", "kind": "evaluate", "oracle": "gc_content",
             "use": "ranking_objective", "estimated_budget": 4},
        ],
        "profiling_plan": [
            {"oracle": "gc_content", "capability": "screening",
             "anchor_set": str(anchor), "backend": "deterministic"},
        ],
    })

    executed: list[str] = []

    def execute(allowed, allocation):
        executed.extend(a.action_id for a in allowed)
        return {"budget_spent": allocation, "best": "b0"}, []

    result = runner.run_campaign(
        campaign_id="camp_1",
        task_description="screen and rank candidates",
        task_type="aptamer_affinity",
        target_family="t1",
        candidate_oracles=["gc_content"],
        total_budget=10,
        execute=execute,
        declaration=declaration,
    )

    verdict_by_action = {d.action_id: d.verdict for d in result.gate_decisions}
    # Profiling ran on demand: screening verified, ranking never profiled.
    assert verdict_by_action["screen"] == "allow"
    assert verdict_by_action["rank"] == "require_profiling"
    # Only the allowed action reached the executor, with the full budget.
    assert executed == ["screen"]
    assert result.budget_allocation == {"screen": 10, "rank": 0}
    # Claim passed (screening verified on this family).
    assert [v.verdict for v in result.claim_verdicts] == ["pass"]
    # Archival: campaign appended, self model persisted.
    assert [c.campaign_id for c in runner.case_memory.campaigns()] == ["camp_1"]
    reloaded = runner.case_memory.load_self_model()
    assert reloaded.query("gc_content", "aptamer_affinity", "t1").assessment(
        "screening"
    ).grade == "verified"
    # Audit trail covers the full loop.
    event_types = [e.event_type for e in runner.audit.events()]
    for expected in ("self_model_update", "profiling_run", "gate_decision",
                     "budget_event", "claim_verdict"):
        assert expected in event_types


def test_run_campaign_execution_claims_gated(tmp_path):
    runner = CalibratedCampaignRunner(
        case_memory_root=tmp_path / "memory",
        audit_path=tmp_path / "audit.jsonl",
    )
    declaration = CampaignDeclaration.model_validate({
        "claims": [],
        "actions": [{"action_id": "ann", "kind": "annotate", "oracle": None,
                     "use": "none", "estimated_budget": 0}],
        "profiling_plan": [],
    })

    def execute(allowed, allocation):
        return {"budget_spent": {}}, [Claim(
            claim_id="exec_c", text="X binds better than Y", scope="absolute",
            dependencies=[ClaimDependency(oracle="unprofiled_oracle", capability="ranking")],
        )]

    result = runner.run_campaign(
        campaign_id="camp_2",
        task_description="t",
        task_type="aptamer_affinity",
        target_family="t1",
        candidate_oracles=["unprofiled_oracle"],
        total_budget=5,
        execute=execute,
        declaration=declaration,
    )
    assert [v.verdict for v in result.claim_verdicts] == ["reject"]
