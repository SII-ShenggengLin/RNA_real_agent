"""Layer 3 — Planning & Control: Planner ABC, ExecutionPlan, ExecutionController."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.workflow_models import WorkflowResult


class PlanStep(BaseModel):
    """One step inside an ``ExecutionPlan``."""

    step_id: str
    type: Literal["capability", "workflow"]
    target: str
    input_binding: dict[str, Any] = Field(default_factory=dict)
    output_key: str = ""
    description: str = ""


class ExecutionPlan(BaseModel):
    """Produced by a ``Planner``; consumed by ``ExecutionController``."""

    steps: list[PlanStep]
    max_retries: int = 2
    fallback_on_error: Literal["abort", "skip", "retry_with_alternative"] = "retry_with_alternative"


class AgentContext(BaseModel):
    """Read-only context passed to ``Planner.plan``."""

    session_id: str = ""
    available_capabilities: list[str] = Field(default_factory=list)
    available_workflows: list[str] = Field(default_factory=list)
    previous_plans: list[ExecutionPlan] = Field(default_factory=list)


class Planner(ABC):
    """Abstract planner backend.

    A planner is **stateless** and **pure**: given a user request + context, it
    produces an ``ExecutionPlan``.  It does **not** execute the plan.
    """

    @abstractmethod
    def plan(self, user_text: str, context: AgentContext) -> ExecutionPlan:
        """Return an execution plan for *user_text*."""
        ...


class Critic(ABC):
    """Quality gate that decides whether to retry or finish.

    Must be co-designed with its paired ``BaseDomainWorkflow`` so that the
    checked metrics are exactly the ones the workflow optimises.
    """

    @abstractmethod
    def should_retry(self, workflow_result: WorkflowResult, state: dict[str, Any]) -> bool:
        """Return ``True`` if the controller should trigger a retry."""
        ...


@dataclass
class ExecutionController:
    """Bridge between Planner (what to do) and lower layers (how to do it).

    Executes an ``ExecutionPlan`` step by step, writes results back to state,
    and delegates retry decisions to a ``Critic``.
    """

    capability_registry: CapabilityRegistry
    workflow_registry: Optional[Dict[str, Any]] = None
    critic: Optional[Critic] = None

    def execute(
        self,
        plan: ExecutionPlan,
        state: dict[str, Any],
        *,
        replan_fn: Optional[Callable[[dict[str, Any]], ExecutionPlan]] = None,
    ) -> dict[str, Any]:
        """Run every step in *plan* and return the updated *state*.

        When a workflow step triggers a critic retry and *replan_fn* is
        provided, the controller increments ``retry_count``, calls
        ``replan_fn(state)`` to obtain a new plan, and re-executes from the
        first step.  This is a **workflow-level** retry: the entire
        ``MrnaCdsDesignWorkflow`` is re-run, not individual capabilities.
        """
        from agent_core.workflows.registry import get_critic_for_workflow

        while True:
            retry_triggered = False

            for step in plan.steps:
                result = self._run_step(step, state)
                if step.output_key:
                    state[step.output_key] = result

                # Merge workflow internal state writebacks into outer state
                if step.type == "workflow" and hasattr(result, "_state_writeback"):
                    wb = getattr(result, "_state_writeback", {})
                    if isinstance(wb, dict):
                        for key, value in wb.items():
                            state[key] = value

                # Critic checks the *result* of this step if it's a workflow
                if step.type == "workflow":
                    critic = self._resolve_critic(step, get_critic_for_workflow)
                    if critic is not None and isinstance(result, WorkflowResult):
                        if critic.should_retry(result, state):
                            state["_critic_should_retry"] = True
                            retry_triggered = True
                            break

            if not retry_triggered:
                state["_plan_executed"] = True
                return state

            # Workflow-level retry bookkeeping
            retry_count = state.get("retry_count", 0)
            if retry_count >= plan.max_retries:
                state["_plan_executed"] = True
                return state

            state["retry_count"] = retry_count + 1

            if replan_fn is not None:
                plan = replan_fn(state)
                if not isinstance(plan, ExecutionPlan):
                    raise RuntimeError("replan_fn must return an ExecutionPlan")
            else:
                state["_plan_executed"] = True
                return state

    def _resolve_critic(
        self,
        step: PlanStep,
        get_critic_for_workflow: Callable[[str], Optional[Critic]],
    ) -> Optional[Critic]:
        """Return the critic for a workflow step.

        Priority:
        1. Registry lookup via ``get_critic_for_workflow``.
        2. Fallback to ``self.critic`` (global override).
        """
        if step.type != "workflow":
            return None
        critic = get_critic_for_workflow(step.target)
        if critic is not None:
            return critic
        return self.critic

    def _run_step(self, step: PlanStep, state: dict[str, Any]) -> Any:
        inputs = self._resolve_bindings(step.input_binding, state)

        if step.type == "capability":
            cap = self.capability_registry.get(step.target)
            return cap.invoke(inputs, state=state)

        # workflow
        if self.workflow_registry and step.target in self.workflow_registry:
            wf = self.workflow_registry[step.target]
            return wf.run(inputs)

        raise RuntimeError(f"Unknown step target: {step.target}")

    @staticmethod
    def _resolve_bindings(binding: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Resolve ``$state.foo`` references in step input bindings."""
        resolved: dict[str, Any] = {}
        for key, value in binding.items():
            if isinstance(value, str) and value.startswith("$state."):
                state_key = value[7:]
                resolved[key] = state.get(state_key)
            else:
                resolved[key] = value
        return resolved
