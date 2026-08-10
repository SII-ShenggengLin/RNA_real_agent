"""CoordinatorAgent for Bounded Multi-Module Coordination (BMC)."""

from __future__ import annotations

import logging
from typing import Any

from agent_core.agents.base import BaseAgent
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """Deterministic BMC controller for coupled workflows.

    Used for:
    - full_length_mrna_design (Type-I: 5'UTR / CDS / 3'UTR physical splicing)
    - rna_aptamer_design (Type-II: target hotspot + aptamer functional coupling)

    The agent detects whether a workflow implements the BMC-capable interface
    (``run_initial``, ``bmc_prepare``, ``bmc_run_round``, ``bmc_finalize``). For
    BMC-capable workflows it orchestrates the bounded convergence loop:

      1. Generate and rank an initial candidate pool.
      2. Prepare coordinator state from the initial result.
      3. Iteratively diagnose, broadcast feedback, regenerate, and re-evaluate
         until the coordinator reports convergence or the round budget is exhausted.
      4. Finalize the result (state writeback, BMC trace, reference point).

    For workflows that do not expose the BMC interface, the agent falls back to
    the legacy behaviour of delegating directly to ``workflow.run(...)``.
    """

    def __init__(self, workflow: BaseDomainWorkflow[Any, Any]) -> None:
        self.workflow = workflow

    @staticmethod
    def _is_bmc_capable(workflow: BaseDomainWorkflow[Any, Any]) -> bool:
        """Return True when *workflow* exposes the BMC orchestration interface."""
        return (
            hasattr(workflow, "run_initial")
            and hasattr(workflow, "bmc_prepare")
            and hasattr(workflow, "bmc_run_round")
            and hasattr(workflow, "bmc_finalize")
        )

    def run(
        self,
        inp: Any,
        *,
        progress_callback: Any | None = None,
    ) -> WorkflowResult:
        """Run the coupled workflow with BMC coordination."""
        _LOGGER.debug(
            "CoordinatorAgent running workflow=%s", getattr(self.workflow, "name", "unknown")
        )

        if not self._is_bmc_capable(self.workflow):
            return self.workflow.run(inp, progress_callback=progress_callback)

        # Phase 1 & 2: initial generation, evaluation, and ranking.
        result = self.workflow.run_initial(inp, progress_callback=progress_callback)

        # Early exit when the initial run failed or produced no candidates.
        if not result.success or not result.all_candidates:
            return self.workflow.bmc_finalize(result)

        # Phase 3: bounded multi-module coordination.
        bmc_state = self.workflow.bmc_prepare(result)
        max_rounds = bmc_state.get("max_rounds", 0)

        if max_rounds > 0:
            for round_num in range(1, max_rounds + 1):
                result, bmc_state, should_stop, reason = self.workflow.bmc_run_round(
                    round_num,
                    result,
                    bmc_state,
                    progress_callback=progress_callback,
                )
                if should_stop:
                    _LOGGER.debug(
                        "bmc_stopping workflow=%s round=%d reason=%s",
                        getattr(self.workflow, "name", "unknown"),
                        round_num,
                        reason,
                    )
                    break

        return self.workflow.bmc_finalize(result)
