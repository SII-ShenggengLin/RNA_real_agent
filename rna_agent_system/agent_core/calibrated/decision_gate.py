"""DecisionGate: pre-action gating of experiment plans by capability grade.

Hard constraints from the design doc (§2.2): an oracle without verified
ranking power is forbidden as a candidate-ranking objective; without verified
screening power it may not carry large-scale screening evaluation. Unprofiled
requirements trigger profiling; transferred grades are usable with degraded
confidence; transferred failures are rejected like direct failures.
Deterministic; no LLM.
"""

from __future__ import annotations

import logging
from typing import Iterable

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import CapabilityKind, GateDecision, PlannedAction
from agent_core.calibrated.self_model import SelfModel

_LOGGER = logging.getLogger(__name__)

# Action use -> the CASF capability it depends on. ``scoring_annotation`` and
# ``none`` do not drive decisions and are always allowed.
REQUIRED_CAPABILITY: dict[str, CapabilityKind] = {
    "ranking_objective": "ranking",
    "screening_evaluation": "screening",
    "docking_validation": "docking",
}


class DecisionGate:
    """Reviews planned actions against the SelfModel before execution."""

    def __init__(self, self_model: SelfModel, *, audit: AuditTrail | None = None) -> None:
        self._self_model = self_model
        self._audit = audit

    def review(
        self,
        actions: Iterable[PlannedAction],
        *,
        task_type: str,
        target_family: str,
    ) -> list[GateDecision]:
        decisions = [
            self._review_one(a, task_type=task_type, target_family=target_family)
            for a in actions
        ]
        if self._audit is not None:
            for action, decision in zip(actions, decisions):
                self._audit.record(
                    "gate_decision",
                    {
                        "action_id": decision.action_id,
                        "oracle": decision.oracle,
                        "use": action.use,
                        "verdict": decision.verdict,
                        "reason": decision.reason,
                    },
                )
        return decisions

    def _review_one(
        self, action: PlannedAction, *, task_type: str, target_family: str
    ) -> GateDecision:
        required = REQUIRED_CAPABILITY.get(action.use)
        if required is None or action.oracle is None:
            return GateDecision(
                action_id=action.action_id,
                verdict="allow",
                reason=f"use={action.use} does not drive ranking/screening decisions",
                oracle=action.oracle,
            )

        record = self._self_model.query(action.oracle, task_type, target_family)
        cell = record.assessment(required)
        base = {
            "action_id": action.action_id,
            "oracle": action.oracle,
            "required_capability": required,
            "evidence": cell.evidence,
        }

        if cell.grade == "verified":
            return GateDecision(
                verdict="allow",
                reason=f"{action.oracle} has verified {required} power on {target_family}",
                **base,
            )
        if cell.grade == "failed":
            return GateDecision(
                verdict="reject",
                reason=(
                    f"{action.oracle} failed {required} profiling on {target_family}; "
                    f"substitute a verified oracle or downgrade the claim scope"
                ),
                substitute={"use": "scoring_annotation"},
                **base,
            )
        if cell.grade == "transferred":
            if cell.transferred_from_grade == "verified":
                return GateDecision(
                    verdict="downgrade",
                    reason=(
                        f"{required} grade transferred from {cell.source_case_id} with "
                        f"decayed confidence={cell.confidence}; conclusions capped at "
                        f"within-target relative comparisons"
                    ),
                    **base,
                )
            return GateDecision(
                verdict="reject",
                reason=(
                    f"transferred {required} failure from {cell.source_case_id}; "
                    f"no evidence of {required} power"
                ),
                substitute={"use": "scoring_annotation"},
                **base,
            )
        return GateDecision(
            verdict="require_profiling",
            reason=(
                f"{action.oracle} has no {required} profiling for "
                f"({task_type}, {target_family}); run CapabilityProfiler first"
            ),
            **base,
        )
