"""ExperimentPlanner: LLM dependency declaration + deterministic budgeting.

Step 2/4 of the standard campaign flow (design doc §2.3): the LLM declares the
capability grades this campaign's claims depend on and proposes a minimal
profiling plan; a deterministic module allocates the evaluation budget
conditioned on capability grades (no large screening budget for oracles
without verified screening power). Every plan passes DecisionGate before
execution and consumption is logged as budget events.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.models import (
    CapabilityKind,
    Claim,
    GateDecision,
    PlannedAction,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.llm_config import get_deepseek_llm

_LOGGER = logging.getLogger(__name__)


class ProfilingSpec(BaseModel):
    """One minimal profiling job proposed by the LLM (design doc §2.3 step 2)."""

    oracle: str
    capability: CapabilityKind
    anchor_set: str = ""
    backend: str = "e1_driver"


class CampaignDeclaration(BaseModel):
    """LLM-declared campaign plan: claims, actions, minimal profiling plan."""

    claims: list[Claim] = Field(default_factory=list)
    actions: list[PlannedAction] = Field(default_factory=list)
    profiling_plan: list[ProfilingSpec] = Field(default_factory=list)


class ExperimentPlanner:
    """Budget-aware experiment planner conditioned on the SelfModel."""

    def __init__(
        self,
        self_model: SelfModel,
        *,
        audit: AuditTrail | None = None,
        llm: Any | None = None,
    ) -> None:
        self._self_model = self_model
        self._audit = audit
        self._llm = llm

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = get_deepseek_llm(temperature=0.0)
        return self._llm

    # ------------------------------------------------------------------ LLM part

    def declare(
        self,
        task_description: str,
        *,
        candidate_oracles: list[str],
        task_type: str,
        target_family: str,
    ) -> CampaignDeclaration:
        """Ask the LLM to declare claim capability dependencies + minimal plan."""
        schema = json.dumps(CampaignDeclaration.model_json_schema(), ensure_ascii=False)
        known = {
            o: {
                k: v.grade
                for k, v in self._self_model.query(o, task_type, target_family).capabilities.items()
            }
            for o in candidate_oracles
        }
        messages = [
            (
                "system",
                "You are the declaration stage of a calibrated RNA-design agent. "
                "For the campaign below, declare: (1) every quantitative claim you "
                "intend to make, with the oracle and CASF capability (scoring / "
                "screening / ranking / docking) it depends on; (2) the planned "
                "actions, each tagged with how its oracle is used "
                "(ranking_objective / screening_evaluation / docking_validation / "
                "scoring_annotation / none); (3) the minimal profiling plan for any "
                "capability you depend on that is not yet verified. "
                "Reply with JSON only, matching this schema:\n" + schema,
            ),
            (
                "user",
                f"task_type: {task_type}\ntarget_family: {target_family}\n"
                f"candidate_oracles: {candidate_oracles}\n"
                f"known_capability_grades: {json.dumps(known, ensure_ascii=False)}\n\n"
                f"campaign task:\n{task_description}",
            ),
        ]
        raw = self._invoke(messages)
        return CampaignDeclaration.model_validate(_parse_json_object(raw))

    def _invoke(self, messages: list[tuple[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        msg_map = {"system": SystemMessage, "user": HumanMessage}
        lc_messages = [msg_map[role](content=text) for role, text in messages]
        raw = self.llm.invoke(lc_messages)
        return raw.content if hasattr(raw, "content") else str(raw)

    # ------------------------------------------------------------- deterministic

    def gate_plan(
        self,
        declaration: CampaignDeclaration,
        *,
        task_type: str,
        target_family: str,
    ) -> list[GateDecision]:
        """Pass every planned action through DecisionGate (design doc §2.3 step 4)."""
        gate = DecisionGate(self._self_model, audit=self._audit)
        return gate.review(
            declaration.actions, task_type=task_type, target_family=target_family
        )

    def allocate_budget(
        self,
        actions: list[PlannedAction],
        decisions: list[GateDecision],
        *,
        total_budget: int,
    ) -> dict[str, int]:
        """Split *total_budget* across allowed actions.

        Rejected / require_profiling actions get zero. Downgraded actions keep
        half their share (capped conclusions need less evidence). The rest is
        split proportionally to ``estimated_budget`` (equally when all zero).
        """
        verdict_by_id = {d.action_id: d.verdict for d in decisions}
        weights: dict[str, float] = {}
        for action in actions:
            verdict = verdict_by_id.get(action.action_id, "reject")
            if verdict in ("reject", "require_profiling"):
                weights[action.action_id] = 0.0
            elif verdict == "downgrade":
                weights[action.action_id] = max(float(action.estimated_budget), 1.0) * 0.5
            else:
                weights[action.action_id] = max(float(action.estimated_budget), 1.0)
        total_weight = sum(weights.values())
        allocation = {
            aid: int(round(total_budget * w / total_weight)) if total_weight > 0 else 0
            for aid, w in weights.items()
        }
        if self._audit is not None:
            self._audit.record(
                "budget_event",
                {"kind": "allocation", "total_budget": total_budget, "allocation": allocation},
            )
        return allocation


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object from LLM output (strip fences, brace-scan fallback)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
