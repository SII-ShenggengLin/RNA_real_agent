"""RuleBasedPlanner — deterministic planner backend (Layer 3)."""

from __future__ import annotations

from typing import Any

from agent_core.planning.base import AgentContext, ExecutionPlan, Planner
from agent_core.planning.rule_based.router import RuleBasedRouter
from agent_core.planning.rule_based.specialists.crispr_specialist import CrisprSpecialist
from agent_core.planning.rule_based.specialists.mrna_specialist import MrnaSpecialist
from agent_core.planning.rule_based.specialists.sirna_specialist import SirnaSpecialist


class RuleBasedPlanner(Planner):
    """Deterministic planner extracted from ``nodes.py`` router + specialist nodes.

    The planner is **stateless** in its decision logic, but it may mutate the
    passed *state* dict to prepare workspace file paths so that the
    ``ExecutionController`` can execute the plan without re-parsing natural
    language.

    This is an intentional pragmatic compromise during the migration; in the
    target architecture file preparation will move into the controller.
    """

    def __init__(self) -> None:
        self.router = RuleBasedRouter()
        self.mrna_specialist = MrnaSpecialist()
        self.sirna_specialist = SirnaSpecialist()
        self.crispr_specialist = CrisprSpecialist()

    def plan(self, user_text: str, context: AgentContext) -> ExecutionPlan:
        """Return an ``ExecutionPlan`` for *user_text*.

        The returned plan uses ``state`` side-effects for workspace-file
        preparation; callers should ensure *state* is passed through to the
        ``ExecutionController``.
        """
        # We intentionally do not use context for rule-based routing today,
        # but the signature matches the abstract Planner interface.
        domain = self.router.classify(user_text)
        if domain == "mrna_specialist":
            return self.mrna_specialist.plan(user_text, {})
        if domain == "sirna_specialist":
            return self.sirna_specialist.plan(user_text, {})
        if domain == "crispr_specialist":
            return self.crispr_specialist.plan(user_text, {})
        # unsupported
        return ExecutionPlan(steps=[])

    def plan_with_state(self, user_text: str, state: dict[str, Any]) -> ExecutionPlan:
        """Plan while updating *state* in place (workspace files, current_filepath, etc.).

        This is the **pragmatic** entry point used by ``AgentRunner`` during
        the migration, because the existing specialist logic prepares files
        before emitting tool calls.
        """
        domain = self.router.classify(user_text)
        state["route"] = domain.replace("_specialist", "") if domain != "unsupported" else "unsupported"
        state["current_task"] = (
            "sirna_design" if domain == "sirna_specialist"
            else "mrna_design" if domain == "mrna_specialist"
            else "crispr_analysis" if domain == "crispr_specialist"
            else "unsupported"
        )
        if domain == "mrna_specialist":
            return self.mrna_specialist.plan(user_text, state)
        if domain == "sirna_specialist":
            return self.sirna_specialist.plan(user_text, state)
        if domain == "crispr_specialist":
            return self.crispr_specialist.plan(user_text, state)
        return ExecutionPlan(steps=[])
