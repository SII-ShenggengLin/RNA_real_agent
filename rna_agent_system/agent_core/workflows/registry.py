"""Workflow–Critic registry.

Each entry is a ``(workflow_class, critic_class)`` pair so that
``ExecutionController`` can look up the correct critic automatically.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Type

from agent_core.planning.base import Critic
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.mrna_cds_critic import MrnaCdsDesignCritic
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow

#: Mapping of workflow step target → (workflow_class, critic_class).
WORKFLOW_CRITIC_PAIRS: Dict[str, Tuple[Type[Any], Type[Critic]]] = {
    "mrna_cds_design": (MrnaCdsDesignWorkflow, MrnaCdsDesignCritic),
}


def get_critic_for_workflow(workflow_name: str) -> Critic | None:
    """Instantiate the critic registered for *workflow_name*, if any."""
    pair = WORKFLOW_CRITIC_PAIRS.get(workflow_name)
    if pair is None:
        return None
    return pair[1]()
