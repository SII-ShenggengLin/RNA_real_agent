"""Workflow–Critic pair for MrnaCdsDesignWorkflow.

The Critic shares the *same* scoring metrics as the Workflow so that any
change to weights or thresholds stays consistent.
"""

from __future__ import annotations

from typing import Any

from agent_core.planning.base import Critic
from agent_core.workflow_models import WorkflowResult


class MrnaCdsDesignCritic(Critic):
    """Quality gate for mRNA CDS design.

    Current rule (simplified):
    - ``gc_component < 0.5``  → retry (increase diversity)
    - ``retry_count >= max_retries`` → do **not** retry
    """

    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 2)

        if retry_count >= max_retries:
            state["critic_verdict"] = "reject"
            state["next_action"] = "finish"
            return False

        if not workflow_result.success or workflow_result.best_candidate is None:
            state["critic_verdict"] = "reject"
            state["next_action"] = "finish"
            return False

        scores = workflow_result.best_candidate.scores
        gc_component = scores.get("gc_component", 0.0)

        if gc_component < 0.5:
            state.setdefault("next_constraints", {})["increase_diversity"] = True
            state["critic_verdict"] = "reject"
            state["next_action"] = "retry"
            return True

        state["critic_verdict"] = "pass"
        state["next_action"] = "finish"
        return False
