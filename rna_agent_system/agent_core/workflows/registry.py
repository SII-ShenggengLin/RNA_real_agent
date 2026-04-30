"""Workflow–Critic registry.

Each entry is a ``(workflow_class, critic_class)`` pair so that
``ExecutionController`` can look up the correct critic automatically.

NOTE: mrna_cds_design intentionally has NO critic paired.
Reason: For CDS design from a fixed protein sequence, retrying the same
tools with the same inputs does not produce meaningfully different results.
Ranking by the combined score (-mfe + codon_count * log(CAI)) is sufficient;
adding a retry loop would only waste compute without improving candidate
quality. If a future workflow genuinely benefits from iterative refinement,
it should be registered here with its own critic.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Type

from agent_core.planning.base import Critic
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaCritic,
    FullLengthMrnaDesignWorkflow,
)
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow

#: Mapping of workflow step target → (workflow_class, critic_class).
#: Workflows without a critic are omitted; ExecutionController treats
#: missing entries as "no critic → no retry".
#:
#: NOTE: full_length_mrna_design has a structurally-complete critic but is
#: currently disabled (returns False) to avoid unnecessary compute during
#: initial rollout. Uncomment the line below to enable retry logic.
WORKFLOW_CRITIC_PAIRS: Dict[str, Tuple[Type[Any], Type[Critic]]] = {
    # "full_length_mrna_design": (FullLengthMrnaDesignWorkflow, FullLengthMrnaCritic),
}


def get_critic_for_workflow(workflow_name: str) -> Critic | None:
    """Instantiate the critic registered for *workflow_name*, if any."""
    pair = WORKFLOW_CRITIC_PAIRS.get(workflow_name)
    if pair is None:
        return None
    return pair[1]()
