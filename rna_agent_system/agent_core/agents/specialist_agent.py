"""SpecialistAgent: per-workflow strategy and retry decisions."""

from __future__ import annotations

import copy
import logging
import os
from typing import Any

from agent_core.agents.base import AgentResult, BaseAgent
from agent_core.agents.quality_agent import QualityAgent, QualityProfile
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow

_LOGGER = logging.getLogger(__name__)


class SpecialistAgent(BaseAgent):
    """Decision-making agent responsible for a single workflow domain.

    SpecialistAgent runs a workflow, asks QualityAgent for a review, and decides
    whether to retry with adjusted parameters or abort. It returns an AgentResult
    that the PipelineAgent aggregates.
    """

    def __init__(
        self,
        workflow: BaseDomainWorkflow[Any, Any],
        quality_profile: QualityProfile,
    ) -> None:
        self.workflow = workflow
        self.quality_profile = quality_profile

    def run(
        self,
        node_id: str,
        params: dict[str, Any],
        quality_agent: QualityAgent,
        *,
        progress_callback: Any | None = None,
        state: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Execute the workflow and apply quality-driven retry logic."""
        state = state or {}
        state["_last_workflow_params"] = dict(params)

        inp = self._build_input(params)
        result = self._run_workflow(inp, progress_callback)

        retry_count = 0
        max_retries = self.quality_profile.max_retries
        # RNADA_SPECIALIST_MAX_RETRIES (default unset) mirrors the
        # RNADA_CAPGATE / RNADA_QUALITY_REVIEW env-knob convention: batch
        # drivers / ops can disable the retry loop for A/B instrumentation
        # without touching code. The interactive default is unchanged (the
        # profile's own value).
        env_retries = os.environ.get("RNADA_SPECIALIST_MAX_RETRIES")
        if env_retries is not None and env_retries.strip() != "":
            max_retries = int(env_retries)

        auto_retry = state.get("_quality_auto_retry", False)

        while retry_count < max_retries:
            report = quality_agent.review(result, self.quality_profile, state)

            if report.action == "pass":
                break

            if report.action == "abort":
                # GOVERNANCE (2026-08-10): an LLM-chosen "abort" is advisory
                # only. It stays recorded in state["_diagnosis_history"] and in
                # the AgentResult metadata, but it must NOT flip a successful
                # run to failed. Two real incidents from the 2026-07 Fig-3/4
                # campaign motivate this:
                #   1. DeepSeek billing exhaustion (HTTP 402): QualityAgent's
                #      old LLM-failure fallback returned abort, so EVERY
                #      reviewed run died at the last step for hours. The
                #      fallback now reports review_unavailable/pass instead,
                #      with state["_quality_review_error"] as the infra-failure
                #      marker.
                #   2. LLM hallucinated abort (Myoglobin r3: "no user request"
                #      reasoning on a fully successful run) — advisory LLMs can
                #      misfire, and a misfire must not be destructive.
                # Hard-failure retries are decided solely by
                # WorkflowResult.is_hard_failure (see the retry branch below).
                _LOGGER.warning(
                    "quality_abort_advisory node=%s workflow=%s reasoning=%s",
                    node_id,
                    self.workflow.name,
                    report.reasoning,
                )
                break

            # retry_with_adjustments or retry_with_alternative
            if not auto_retry and not result.is_hard_failure:
                # Advisory mode: QualityAgent suggestions require user confirmation;
                # only hard failures (success=False, empty candidates, tool errors)
                # trigger automatic retry.
                break

            if not report.parameter_overrides:
                # No actionable overrides; stop retrying.
                break

            retry_count += 1
            _LOGGER.info(
                "specialist_retry node=%s workflow=%s attempt=%d/%d action=%s",
                node_id,
                self.workflow.name,
                retry_count,
                max_retries,
                report.action,
            )

            merged_params = self._apply_overrides(params, report.parameter_overrides, state)
            if merged_params == params:
                # All suggested overrides were protected as user-explicit, so
                # this attempt never re-runs anything. Drop it from the retry
                # count so the reported count reflects real re-executions.
                retry_count -= 1
                _LOGGER.info(
                    "specialist_no_actionable_overrides node=%s workflow=%s; stopping retries",
                    node_id,
                    self.workflow.name,
                )
                break
            inp = self._build_input(merged_params)
            state["_last_workflow_params"] = merged_params
            params = merged_params

            if report.evaluator_only and result.all_candidates:
                # Try a cheap partial rerun with the existing candidates.
                partial = self.workflow.partial_rerun(
                    inp,
                    list(result.all_candidates),
                    progress_callback=progress_callback,
                )
                if partial is not None:
                    result = partial
                    continue
                _LOGGER.warning(
                    "specialist_partial_rerun_failed node=%s workflow=%s; falling back to full rerun",
                    node_id,
                    self.workflow.name,
                )

            result = self._run_workflow(inp, progress_callback)

        # Final review after retries are exhausted so the last state is captured.
        final_report = quality_agent.review(result, self.quality_profile, state)

        summary = result.summary or ""
        if final_report.reasoning:
            summary = f"{summary}\nQuality review: {final_report.reasoning}".strip()

        return AgentResult(
            node_id=node_id,
            workflow=self.workflow.name,
            # Run success comes from the workflow result alone; an advisory
            # "abort" from the quality review never flips a successful run.
            success=getattr(result, "success", True),
            workflow_result=result,
            summary=summary,
            errors=list(getattr(result, "errors", []) or []),
            metadata={
                "quality_report": final_report,
                "retry_count": retry_count,
                "max_retries": max_retries,
            },
        )

    def _build_input(self, params: dict[str, Any]) -> Any:
        if self.workflow.input_model is None:
            return params
        return self.workflow.input_model(**params)

    def _run_workflow(
        self,
        inp: Any,
        progress_callback: Any | None,
    ) -> WorkflowResult:
        return self.workflow.run(inp, progress_callback=progress_callback)

    @staticmethod
    def _apply_overrides(
        base_params: dict[str, Any],
        overrides: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge parameter overrides, protecting user-explicit values."""
        protected = set(state.get("_user_explicit_params", []))
        merged = copy.deepcopy(base_params)
        for k, v in overrides.items():
            if k in protected:
                _LOGGER.info("SpecialistAgent preserving user-explicit parameter: %s", k)
                continue
            merged[k] = v
        return merged

