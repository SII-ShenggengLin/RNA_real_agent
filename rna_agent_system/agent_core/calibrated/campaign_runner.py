"""CalibratedCampaignRunner: the standard seven-step campaign flow.

Implements design doc §2.3 end-to-end: (1) SelfModel query, (2) LLM dependency
declaration, (3) on-demand profiling, (4) plan + DecisionGate, (5) execution
with budget accounting, (6) ClaimGate, (7) archival to CaseMemory + AuditTrail.
Execution itself is delegated to an injected callable (Layer-2 workflows run
there), keeping this orchestrator deterministic apart from the declaration LLM.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.case_memory import CaseMemory
from agent_core.calibrated.claim_gate import ClaimGate
from agent_core.calibrated.experiment_planner import CampaignDeclaration, ExperimentPlanner
from agent_core.calibrated.models import (
    CampaignRecord,
    Claim,
    ClaimVerdict,
    GateDecision,
    PlannedAction,
)
from agent_core.calibrated.profiler import CapabilityProfiler, ProfileRequest

_LOGGER = logging.getLogger(__name__)

# execute(allowed_actions, budget_allocation) -> (outcomes, execution_claims)
ExecuteFn = Callable[[list[PlannedAction], dict[str, int]], tuple[dict[str, Any], list[Claim]]]


class CampaignResult(BaseModel):
    """Everything one campaign produced, ready for E3 adjudication."""

    campaign_id: str
    declaration: CampaignDeclaration | None = None
    gate_decisions: list[GateDecision] = Field(default_factory=list)
    budget_allocation: dict[str, int] = Field(default_factory=dict)
    claim_verdicts: list[ClaimVerdict] = Field(default_factory=list)
    outcomes: dict[str, Any] = Field(default_factory=dict)
    record: CampaignRecord | None = None


class CalibratedCampaignRunner:
    """Orchestrates one gated campaign (the E3 treatment arm)."""

    def __init__(
        self,
        *,
        case_memory_root: str | Path | None = None,
        audit_path: str | Path | None = None,
        llm: Any | None = None,
        profiler_scorers: dict[str, Callable[[str], float]] | None = None,
    ) -> None:
        self.case_memory = CaseMemory(case_memory_root)
        self.audit = AuditTrail(audit_path or (self.case_memory.root / "audit_trail.jsonl"))
        self.self_model = self.case_memory.load_self_model(audit=self.audit)
        self.profiler = CapabilityProfiler(
            self.self_model, audit=self.audit, scorers=profiler_scorers
        )
        self.planner = ExperimentPlanner(self.self_model, audit=self.audit, llm=llm)
        self.claim_gate = ClaimGate(self.self_model, audit=self.audit)

    def run_campaign(
        self,
        *,
        campaign_id: str,
        task_description: str,
        task_type: str,
        target_family: str,
        candidate_oracles: list[str],
        total_budget: int,
        execute: ExecuteFn,
        target_features: dict[str, float | str] | None = None,
        declaration: CampaignDeclaration | None = None,
    ) -> CampaignResult:
        # Step 2: hypothesis / dependency declaration (LLM) unless supplied.
        if declaration is None:
            declaration = self.planner.declare(
                task_description,
                candidate_oracles=candidate_oracles,
                task_type=task_type,
                target_family=target_family,
            )

        # Step 3: on-demand profiling for unprofiled declared needs.
        for spec in declaration.profiling_plan:
            record = self.self_model.query(spec.oracle, task_type, target_family)
            if record.assessment(spec.capability).grade == "unprofiled" and spec.anchor_set:
                _LOGGER.info("on-demand profiling: %s/%s", spec.oracle, spec.capability)
                self.profiler.profile(ProfileRequest(
                    oracle=spec.oracle,
                    task_type=task_type,
                    target_family=target_family,
                    anchor_set=spec.anchor_set,
                    capabilities=[spec.capability],
                    backend=spec.backend,
                ))

        # Step 4: plan + decision gating.
        decisions = self.planner.gate_plan(
            declaration, task_type=task_type, target_family=target_family
        )
        allocation = self.planner.allocate_budget(
            declaration.actions, decisions, total_budget=total_budget
        )
        blocked = {"reject", "require_profiling"}
        allowed = [
            a for a, d in zip(declaration.actions, decisions) if d.verdict not in blocked
        ]

        # Step 5: execution (Layer-2 workflows live in the injected callable).
        outcomes, exec_claims = execute(allowed, allocation)
        self.audit.record("budget_event", {
            "kind": "consumption",
            "campaign_id": campaign_id,
            "spent": outcomes.get("budget_spent", {}),
        })

        # Step 6: claim gating over declared + execution claims.
        verdicts = self.claim_gate.review(
            [*declaration.claims, *exec_claims],
            task_type=task_type,
            target_family=target_family,
        )

        # Step 7: archival.
        record = CampaignRecord(
            campaign_id=campaign_id,
            task_type=task_type,
            target_family=target_family,
            target_features=target_features or {},
            profiling_used=[
                {"oracle": s.oracle, "capability": s.capability}
                for s in declaration.profiling_plan
            ],
            interventions=[a.action_id for a in allowed],
            budget={"total": total_budget, "allocation": allocation},
            outcomes=outcomes,
            verdict="gated",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.case_memory.add_campaign(record)
        self.case_memory.save_self_model(self.self_model)

        return CampaignResult(
            campaign_id=campaign_id,
            declaration=declaration,
            gate_decisions=decisions,
            budget_allocation=allocation,
            claim_verdicts=verdicts,
            outcomes=outcomes,
            record=record,
        )
