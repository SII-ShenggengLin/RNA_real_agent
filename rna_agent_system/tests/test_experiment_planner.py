"""Tests for agent_core.calibrated.experiment_planner."""

from __future__ import annotations

import json
from types import SimpleNamespace

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.experiment_planner import (
    CampaignDeclaration,
    ExperimentPlanner,
    _parse_json_object,
)
from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    Claim,
    ClaimDependency,
    GateDecision,
    PlannedAction,
)
from agent_core.calibrated.self_model import SelfModel


class _MockLLM:
    def __init__(self, payload: dict):
        self._payload = payload
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content="```json\n" + json.dumps(self._payload) + "\n```")


def _declaration_payload() -> dict:
    return {
        "claims": [{
            "claim_id": "c1",
            "text": "X ranks above Y",
            "scope": "absolute",
            "dependencies": [{"oracle": "oracle_x", "capability": "ranking"}],
        }],
        "actions": [{
            "action_id": "a1", "kind": "evaluate", "oracle": "oracle_x",
            "use": "ranking_objective", "estimated_budget": 20,
        }],
        "profiling_plan": [{"oracle": "oracle_x", "capability": "ranking",
                            "anchor_set": "a.json", "backend": "e1_driver"}],
    }


def test_declare_parses_llm_json():
    llm = _MockLLM(_declaration_payload())
    planner = ExperimentPlanner(SelfModel(), llm=llm)
    decl = planner.declare(
        "rank candidates for thrombin",
        candidate_oracles=["oracle_x"],
        task_type="aptamer_affinity",
        target_family="thrombin",
    )
    assert isinstance(decl, CampaignDeclaration)
    assert decl.claims[0].dependencies[0].capability == "ranking"
    assert decl.actions[0].use == "ranking_objective"
    assert decl.profiling_plan[0].anchor_set == "a.json"
    assert llm.messages is not None  # prompt was actually built and sent


def test_parse_json_object_fallback():
    assert _parse_json_object('prefix {"a": 1} suffix') == {"a": 1}
    assert _parse_json_object("```json\n{\"b\": 2}\n```") == {"b": 2}


def test_gate_plan_delegates_to_decision_gate():
    model = SelfModel([
        CapabilityRecord(
            oracle="oracle_x", task_type="aptamer_affinity", target_family="thrombin",
            capabilities={"ranking": CapabilityAssessment(grade="failed", confidence=0.9)},
        )
    ])
    planner = ExperimentPlanner(model)
    decl = CampaignDeclaration.model_validate(_declaration_payload())
    [d] = planner.gate_plan(decl, task_type="aptamer_affinity", target_family="thrombin")
    assert d.verdict == "reject"


def test_allocate_budget_zeroes_blocked_and_halves_downgraded(tmp_path):
    trail = AuditTrail(tmp_path / "audit.jsonl")
    planner = ExperimentPlanner(SelfModel(), audit=trail)
    actions = [
        PlannedAction(action_id="ok", kind="k", estimated_budget=4),
        PlannedAction(action_id="down", kind="k", estimated_budget=4),
        PlannedAction(action_id="bad", kind="k", estimated_budget=8),
    ]
    decisions = [
        GateDecision(action_id="ok", verdict="allow"),
        GateDecision(action_id="down", verdict="downgrade"),
        GateDecision(action_id="bad", verdict="reject"),
    ]
    alloc = planner.allocate_budget(actions, decisions, total_budget=12)
    assert alloc["bad"] == 0
    assert alloc["ok"] == 8  # weight 4 of total weight 6
    assert alloc["down"] == 4  # weight 2 of total weight 6
    events = [e for e in trail.events() if e.event_type == "budget_event"]
    assert events and events[0].payload["allocation"] == alloc
