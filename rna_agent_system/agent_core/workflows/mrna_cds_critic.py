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

    Retry rules (co-designed with ``MrnaCdsDesignWorkflow.score``):
    - ``total_score < 0.70``       → retry (increase diversity)
    - ``mfe_component < 0.5``      → retry (prioritise stability)
    - ``gc_component == 0``        → retry (target GC mid = 0.50)
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
        total_score = scores.get("total_score", 0.0)
        mfe_component = scores.get("mfe_component", 0.0)
        gc_component = scores.get("gc_component", 0.0)

        next_constraints: dict[str, Any] = state.setdefault("next_constraints", {})

        if total_score < 0.70:
            next_constraints["increase_diversity"] = True
            state["critic_verdict"] = "reject"
            state["next_action"] = "retry"
            return True

        if mfe_component < 0.5:
            next_constraints["prioritize_stability"] = True
            state["critic_verdict"] = "reject"
            state["next_action"] = "retry"
            return True

        if gc_component == 0.0:
            next_constraints["target_gc_mid"] = 0.50
            state["critic_verdict"] = "reject"
            state["next_action"] = "retry"
            return True

        state["critic_verdict"] = "pass"
        state["next_action"] = "finish"
        return False
