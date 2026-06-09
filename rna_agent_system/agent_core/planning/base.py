"""Layer 3 — Planning & Control: Planner ABC, ExecutionPlan, ExecutionController."""

from __future__ import annotations

import inspect
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Literal, Optional

_LOGGER = logging.getLogger(__name__)

from pydantic import BaseModel, Field

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.workflow_models import WorkflowResult
from agent_core.workflow_run_storage import maybe_persist_workflow_run


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
    # NOTE: When a workflow has a paired Critic with its own MAX_RETRIES,
    # this value should be kept equal to (or lower than) that constant so
    # that the controller exhaustion logic fires predictably.
    max_retries: int = 2
    fallback_on_error: Literal["abort", "skip", "retry_with_alternative"] = (
        "retry_with_alternative"
    )


class AgentContext(BaseModel):
    """Read-only context passed to ``Planner.plan``."""

    session_id: str = ""
    available_capabilities: list[str] = Field(default_factory=list)
    available_workflows: list[str] = Field(default_factory=list)
    previous_plans: list[ExecutionPlan] = Field(default_factory=list)
    workflow_param_schemas: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping workflow_name -> human-readable default-parameter summary for the planner prompt.",
    )


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
    def should_retry(
        self, workflow_result: WorkflowResult, state: dict[str, Any]
    ) -> bool:
        """Return ``True`` if the controller should trigger a retry."""
        ...


@dataclass
class ExecutionController:
    """Bridge between Planner (what to do) and lower layers (how to do it).

    Executes an ``ExecutionPlan`` step by step, writes results back to state,
    and delegates retry decisions to a ``Critic``.
    """

    capability_registry: CapabilityRegistry
    workflow_registry: Optional[dict[str, Any]] = None
    critic: Optional[Critic] = None

    def _maybe_persist_state(
        self,
        state: dict[str, Any],
        enabled: bool,
    ) -> None:
        # Always attach audit metadata to WorkflowResult for AgentRunner-path observability
        wf_result = state.get("workflow_result")
        if isinstance(wf_result, WorkflowResult):
            wf_result._workflow_input = state.get("_last_workflow_params") or {}
            wf_result._execution_log = list(state.get("_execution_log", []))

        if not enabled:
            return
        wf_result = state.get("workflow_result")
        if not isinstance(wf_result, WorkflowResult):
            return
        inp_dict = state.get("_last_workflow_params") or {}

        # Extract full audit trail from state for persistent storage
        execution_log = state.get("_execution_log")
        diagnosis_history = state.get("_diagnosis_history")
        bmc_trace = state.get("_bmc_trace")

        maybe_persist_workflow_run(
            wf_result,
            inp_dict,
            enabled=True,
            operational_summary=wf_result.summary,
            execution_log=execution_log,
            bmc_trace=bmc_trace,
            diagnosis_history=diagnosis_history,
        )

    def execute(
        self,
        plan: ExecutionPlan,
        state: dict[str, Any],
        *,
        persist_run: bool = False,
        replan_fn: Optional[Callable[[dict[str, Any]], ExecutionPlan]] = None,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """Run every step in *plan* and return the updated *state*.

        When a workflow step triggers a critic retry and *replan_fn* is
        provided, the controller increments ``retry_count``, calls
        ``replan_fn(state)`` to obtain a new plan, and re-executes from the
        first step.  This is a **workflow-level** retry: the entire
        ``MrnaCdsDesignWorkflow`` is re-run, not individual capabilities.
        """
        from agent_core.workflows.registry import get_critic_for_workflow

        state.setdefault("_execution_log", [])
        log: list[dict[str, Any]] = state["_execution_log"]

        while True:
            retry_triggered = False
            # 清除上一轮 critic retry 标志，避免残留状态误导外层代码
            state.pop("_critic_should_retry", None)

            for step in plan.steps:
                inputs = self._resolve_bindings(step.input_binding, state)
                start_ts = time.time()
                start_entry = {
                    "event": "step_start",
                    "step_id": step.step_id,
                    "type": step.type,
                    "target": step.target,
                    "description": step.description,
                    "timestamp": start_ts,
                    "inputs": inputs,
                }
                log.append(start_entry)
                if progress_callback is not None:
                    progress_callback(start_entry)

                try:
                    result = self._run_step(
                        step, state, progress_callback=progress_callback, _resolved_inputs=inputs
                    )
                except Exception as exc:
                    elapsed = time.time() - start_ts
                    error_entry = {
                        "event": "step_error",
                        "step_id": step.step_id,
                        "type": step.type,
                        "target": step.target,
                        "timestamp": time.time(),
                        "elapsed_ms": round(elapsed * 1000, 2),
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                    log.append(error_entry)
                    if progress_callback is not None:
                        progress_callback(error_entry)
                    raise

                if step.output_key:
                    state[step.output_key] = result

                # Always store workflow result so the presentation layer can find it
                if step.type == "workflow" and isinstance(result, WorkflowResult):
                    state["workflow_result"] = result

                # Merge workflow internal state writebacks into outer state
                if step.type == "workflow" and hasattr(result, "_state_writeback"):
                    wb = getattr(result, "_state_writeback", {})
                    if isinstance(wb, dict):
                        for key, value in wb.items():
                            # 深度合并 dict 值（如 tool_results），避免覆盖外层已有的 capability 记录
                            if isinstance(value, dict) and isinstance(
                                state.get(key), dict
                            ):
                                state[key].update(value)
                            else:
                                state[key] = value

                # Log completion
                success = True
                if isinstance(result, WorkflowResult):
                    success = getattr(result, "success", True)
                elapsed = time.time() - start_ts
                done_entry = {
                    "event": "step_done",
                    "step_id": step.step_id,
                    "type": step.type,
                    "target": step.target,
                    "success": success,
                    "timestamp": time.time(),
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "output_summary": self._summarize_result(result),
                }
                log.append(done_entry)
                if progress_callback is not None:
                    progress_callback(done_entry)

                # Critic checks the *result* of this step if it's a workflow
                if step.type == "workflow":
                    critic = self._resolve_critic(step, get_critic_for_workflow)
                    if critic is not None and isinstance(result, WorkflowResult):
                        if critic.should_retry(result, state):
                            # Attempt evaluator-only partial rerun first
                            partial_success = self._try_partial_rerun(
                                step, state, result, progress_callback
                            )
                            if partial_success:
                                # Partial rerun succeeded — log it and continue
                                # without triggering a full workflow retry.
                                partial_entry = {
                                    "event": "partial_rerun",
                                    "target": step.target,
                                    "reason": "evaluator-only parameter change",
                                    "timestamp": time.time(),
                                }
                                log.append(partial_entry)
                                if progress_callback is not None:
                                    progress_callback(partial_entry)
                                # Clean up evaluator-only flags so they don't
                                # leak into the next critic check.
                                state.pop("_evaluator_only_retry", None)
                                state.pop("_affected_evaluators", None)
                                continue

                            state["_critic_should_retry"] = True
                            retry_triggered = True
                            retry_entry = {
                                "event": "critic_retry",
                                "target": step.target,
                                "timestamp": time.time(),
                            }
                            log.append(retry_entry)
                            if progress_callback is not None:
                                progress_callback(retry_entry)
                            break
                    elif critic is None:
                        skipped_entry = {
                            "event": "critic_skipped",
                            "target": step.target,
                            "reason": "no_critic_registered",
                            "timestamp": time.time(),
                        }
                        log.append(skipped_entry)
                        if progress_callback is not None:
                            progress_callback(skipped_entry)

            if not retry_triggered:
                state["_plan_executed"] = True
                complete_entry = {
                    "event": "plan_complete",
                    "step_count": len(plan.steps),
                    "timestamp": time.time(),
                }
                log.append(complete_entry)
                if progress_callback is not None:
                    progress_callback(complete_entry)
                self._maybe_persist_state(state, persist_run)
                return state

            # Workflow-level retry bookkeeping
            retry_count = state.get("retry_count", 0)
            if retry_count >= plan.max_retries:
                state["_plan_executed"] = True
                complete_entry = {
                    "event": "plan_complete",
                    "step_count": len(plan.steps),
                    "retries_exhausted": True,
                    "timestamp": time.time(),
                }
                log.append(complete_entry)
                if progress_callback is not None:
                    progress_callback(complete_entry)
                self._maybe_persist_state(state, persist_run)
                return state

            state["retry_count"] = retry_count + 1

            # 优先使用critic提供的parameter_overrides修改当前plan
            parameter_overrides = state.pop("_parameter_overrides", None)
            if parameter_overrides:
                self._apply_parameter_overrides(plan, state, parameter_overrides)
                override_entry = {
                    "event": "parameter_override",
                    "overrides": parameter_overrides,
                    "timestamp": time.time(),
                }
                log.append(override_entry)
                if progress_callback is not None:
                    progress_callback(override_entry)
            elif replan_fn is not None:
                plan = replan_fn(state)
                if not isinstance(plan, ExecutionPlan):
                    raise RuntimeError("replan_fn must return an ExecutionPlan")
                replan_entry = {
                    "event": "replan",
                    "new_step_count": len(plan.steps),
                    "timestamp": time.time(),
                }
                log.append(replan_entry)
                if progress_callback is not None:
                    progress_callback(replan_entry)
            else:
                state["_plan_executed"] = True
                complete_entry = {
                    "event": "plan_complete",
                    "step_count": len(plan.steps),
                }
                log.append(complete_entry)
                if progress_callback is not None:
                    progress_callback(complete_entry)
                self._maybe_persist_state(state, persist_run)
                return state

    def _try_partial_rerun(
        self,
        step: PlanStep,
        state: dict[str, Any],
        current_result: WorkflowResult,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> bool:
        """Attempt an evaluator-only partial rerun for *step*.

        Returns ``True`` if the partial rerun succeeded and the state has been
        updated with the new result.  Returns ``False`` to fall back to a full
        workflow retry.
        """
        if not state.get("_evaluator_only_retry"):
            return False

        if not self.workflow_registry or step.target not in self.workflow_registry:
            return False

        wf = self.workflow_registry[step.target]
        if not hasattr(wf, "partial_rerun"):
            return False

        existing = getattr(current_result, "all_candidates", None)
        if not existing:
            return False

        inputs = self._resolve_bindings(step.input_binding, state)
        _LOGGER.info(
            "Attempting partial rerun for %s with %d candidates",
            step.target,
            len(existing),
        )

        try:
            sig = inspect.signature(wf.partial_rerun)
            if "progress_callback" in sig.parameters:
                new_result = wf.partial_rerun(
                    inputs,
                    existing,
                    progress_callback=progress_callback,
                )
            else:
                new_result = wf.partial_rerun(inputs, existing)
        except Exception as exc:
            _LOGGER.warning(
                "Partial rerun failed for %s: %s. Falling back to full retry.",
                step.target,
                exc,
            )
            return False

        if new_result is None:
            return False

        # Update state with the partial-rerun result
        if step.output_key:
            state[step.output_key] = new_result
        state["workflow_result"] = new_result
        # Preserve the writeback pattern used by full runs
        if hasattr(new_result, "_state_writeback"):
            wb = getattr(new_result, "_state_writeback", {})
            if isinstance(wb, dict):
                for key, value in wb.items():
                    if isinstance(value, dict) and isinstance(state.get(key), dict):
                        state[key].update(value)
                    else:
                        state[key] = value

        _LOGGER.info(
            "Partial rerun succeeded for %s", step.target
        )
        return True

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

    def _run_step(
        self,
        step: PlanStep,
        state: dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
        _resolved_inputs: Optional[dict[str, Any]] = None,
    ) -> Any:
        inputs = _resolved_inputs if _resolved_inputs is not None else self._resolve_bindings(step.input_binding, state)

        if step.type == "capability":
            cap = self.capability_registry.get(step.target)
            result = cap.invoke(inputs)

            # Store raw tool output under state["tool_results"][tool_name]
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"][step.target] = result.output

            # Apply optional writebacks (field aliases / side effects)
            from agent_core.capabilities.writebacks import apply_writeback
            apply_writeback(state, step.target, result.output)

            return result

        # workflow
        if self.workflow_registry and step.target in self.workflow_registry:
            wf = self.workflow_registry[step.target]

            # 保存完整参数供Critic诊断使用
            state["_last_workflow_params"] = dict(inputs)
            state["_last_workflow_target"] = step.target
            # 保留所有 workflow 参数，避免多 step 时被覆盖
            all_params = state.setdefault("_all_workflow_params", {})
            all_params[step.step_id] = {
                "target": step.target,
                "params": dict(inputs),
            }

            sig = inspect.signature(wf.run)
            if "progress_callback" in sig.parameters:
                result = wf.run(inputs, progress_callback=progress_callback)
            else:
                result = wf.run(inputs)

            # 如果workflow执行后有parameter_overrides，也保存
            if hasattr(result, '_state_writeback'):
                wb = getattr(result, '_state_writeback', {})
                if isinstance(wb, dict) and '_workflow_params' in wb:
                    state['_last_workflow_params'] = wb['_workflow_params']

            return result

        raise RuntimeError(f"Unknown step target: {step.target}")

    @staticmethod
    def _summarize_result(result: Any) -> dict[str, Any]:
        """Build a concise, serializable summary of a step result for the execution log."""
        if isinstance(result, WorkflowResult):
            best = getattr(result, "best_candidate", None)
            return {
                "result_type": "WorkflowResult",
                "success": result.success,
                "candidate_count": len(getattr(result, "all_candidates", [])),
                "best_candidate_id": getattr(best, "id", None) if best else None,
                "summary_preview": (result.summary or "")[:200],
            }
        if hasattr(result, "output"):
            output = result.output
            if isinstance(output, str):
                return {
                    "result_type": "capability",
                    "output_preview": output[:200],
                    "output_length": len(output),
                }
            return {
                "result_type": "capability",
                "output_type": type(output).__name__,
            }
        return {
            "result_type": type(result).__name__,
        }

    def _apply_parameter_overrides(
        self,
        plan: ExecutionPlan,
        state: dict[str, Any],
        overrides: dict[str, Any],
    ) -> None:
        """Merge parameter_overrides from Critic into the workflow step's input_binding.

        The original input_binding is preserved in state under ``_original_input_binding``
        so that overrides are always applied on top of the first-run binding, not
        accumulated across retries.
        """
        for step in plan.steps:
            if step.type != "workflow":
                continue

            # Save original binding on first override
            orig_key = f"_original_input_binding_{step.step_id}"
            if orig_key not in state:
                state[orig_key] = dict(step.input_binding)

            # Merge: original → current overrides
            original = state[orig_key]
            merged = {**original, **overrides}

            # Only keep keys that exist in the original binding or are known params.
            # This prevents the LLM from inventing invalid parameters.
            # We allow any key from original (it was validated by the planner)
            # plus keys from overrides that look like valid param names.
            valid_keys = set(original.keys())
            for k in overrides.keys():
                if isinstance(k, str) and k.isidentifier() and not k.startswith("_"):
                    valid_keys.add(k)
            filtered = {k: v for k, v in merged.items() if k in valid_keys}

            step.input_binding = filtered

            _LOGGER.info(
                "applied_parameter_overrides step=%s original_keys=%d override_keys=%d merged_keys=%d",
                step.step_id,
                len(original),
                len(overrides),
                len(filtered),
            )

    @staticmethod
    def _resolve_bindings(
        binding: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve ``$state.foo`` references in step input bindings."""
        resolved: dict[str, Any] = {}
        for key, value in binding.items():
            if isinstance(value, str) and value.startswith("$state."):
                state_key = value[7:]
                resolved[key] = state.get(state_key)
            else:
                resolved[key] = value
        return resolved
