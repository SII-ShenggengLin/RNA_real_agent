"""LLM-driven Critic infrastructure — diagnosis, parameter adjustment, retry decisions.

This module provides ``BaseLLMCritic``, which uses an LLM to analyze workflow
results, diagnose issues, and recommend parameter adjustments for retry.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from agent_core.llm_config import get_deepseek_llm
from agent_core.planning.base import Critic
from agent_core.workflow_models import WorkflowResult

_LOGGER = logging.getLogger(__name__)


class CriticIssue(BaseModel):
    """One specific issue found by the LLM Critic."""

    severity: Literal["critical", "warning", "info"]
    category: str
    description: str
    metric_value: float | None = None
    threshold: float | None = None
    affected_candidate_count: int = 0


class CriticDiagnosis(BaseModel):
    """Structured output from LLM Critic — forces the model to return this shape."""

    overall_assessment: str
    quality_score: float = Field(..., ge=0.0, le=1.0)
    issues: list[CriticIssue] = Field(default_factory=list)

    action: Literal[
        "retry_with_adjustments",   # modify params and retry
        "retry_with_alternative",   # change strategy/tool and retry
        "proceed_with_filtered",    # filter bad candidates, proceed
        "abort",                    # stop, unrecoverable
    ]
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)
    reasoning: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    # Names of evaluators that should be re-run (partial retry optimisation)
    affected_evaluators: list[str] = Field(default_factory=list)


@dataclass
class CriticConfig:
    """Configuration for a workflow-specific LLM Critic.

    Each workflow registers one CriticConfig instance; ``BaseLLMCritic``
    uses it to build the diagnosis prompt.
    """

    workflow_name: str
    workflow_description: str = ""
    evaluation_dimensions: list[str] = field(default_factory=list)
    adjustable_params: dict[str, dict] = field(default_factory=dict)
    retry_strategy: Literal["adjust_params", "change_tool", "abort_only"] = "adjust_params"
    max_retries: int = 2
    # Parameters that only affect evaluators (not candidate generation).
    # When *all* overrides are in this set, the controller may trigger a
    # partial retry that re-runs only the affected evaluators instead of
    # regenerating candidates from scratch.
    evaluator_only_params: set[str] = field(default_factory=set)
    # Mapping: param name → list of evaluator class names affected by that param.
    # Used by the controller to determine which evaluators to re-run.
    param_to_evaluators: dict[str, list[str]] = field(default_factory=dict)


class BaseLLMCritic(Critic):
    """Unified LLM Critic implementation.

    Subclasses or instances only need to provide a ``CriticConfig``.
    All LLM interaction (prompt building, invocation, output parsing) is handled
    by this base class.
    """

    def __init__(self, config: CriticConfig | None = None) -> None:
        self.config = config or self._default_config()
        self._llm = None  # lazy init

    @property
    def llm(self):
        if self._llm is None:
            # Slightly higher temperature for creative diagnosis
            self._llm = get_deepseek_llm(temperature=0.2)
        return self._llm

    # ------------------------------------------------------------------
    # Abstract hooks (subclasses may override)
    # ------------------------------------------------------------------

    def _default_config(self) -> CriticConfig:
        raise NotImplementedError("Subclasses must provide a CriticConfig")

    def _build_context(self, result: WorkflowResult, state: dict[str, Any]) -> dict[str, Any]:
        """Extract workflow-specific context for the LLM prompt.

        Default implementation uses a generic summary. Subclasses may override
        to inject domain-specific context (e.g., biological constraints).
        """
        # Try to get the full parameters used in the last run
        params = state.get("_last_workflow_params", {})

        # Build a candidate metrics summary
        candidate_summaries: list[dict[str, Any]] = []
        for c in result.all_candidates:
            mb = c.metadata.get("metrics_bundle", {}) if c.metadata else {}
            summary = {
                "id": c.id,
                "source": c.source,
                "length": len(c.sequence) if c.sequence else 0,
                "scores": c.scores,
                "metrics": {k: v for k, v in mb.items() if isinstance(v, (int, float, str, bool))},
            }
            candidate_summaries.append(summary)

        return {
            "workflow_name": self.config.workflow_name,
            "workflow_description": self.config.workflow_description,
            "success": getattr(result, "success", False),
            "candidate_count": len(result.all_candidates),
            "best_candidate_summary": candidate_summaries[0] if candidate_summaries else None,
            "all_candidate_summaries": candidate_summaries[:10],  # limit context
            "parameters_used": params,
            "user_text": state.get("user_text", ""),
            "previous_issues": [
                d.get("issues", [])
                for d in state.get("_diagnosis_history", [])
            ],
        }

    def _build_diagnosis_prompt(self, context: dict[str, Any]) -> list[tuple[str, str]]:
        """Build (role, content) message pairs for the LLM."""
        system_lines = [
            "You are an expert RNA bioinformatics reviewer and quality-assurance engineer.",
            "Your job is to evaluate the output of an RNA design workflow and decide if retry is needed.",
            "",
            "## Evaluation Criteria",
            *self.config.evaluation_dimensions,
            "",
            "## Adjustable Parameters (for retry recommendations)",
        ]

        for name, spec in self.config.adjustable_params.items():
            hint = spec.get("hint", "")
            type_info = spec.get("type", "any")
            system_lines.append(f"- {name} ({type_info}): {hint}")

        system_lines.extend([
            "",
            "## Rules",
            "1. Analyze ALL candidates, not just the best one.",
            "2. Identify specific issues with severity (critical/warning/info).",
            "3. If retry is warranted, recommend concrete parameter_overrides.",
            "4. Only recommend parameters listed above in 'Adjustable Parameters'.",
            "5. Consider previous issues (if any) to avoid repeating the same mistakes.",
            "6. PAY SPECIAL ATTENTION to the user's original request (below). If the user stated specific thresholds or constraints (e.g., 'MFE must be < -30', 'CAI > 0.9'), evaluate whether the results meet those constraints. Failure to meet user constraints is a CRITICAL issue.",
            "7. DEFAULT PARAMETERS ARE CAREFULLY TUNED. Only recommend parameter_overrides when you have STRONG evidence that the current parameter directly caused the issue. Do NOT adjust defaults speculatively or just because 'it might help'.",
            "8. Return your diagnosis in the EXACT JSON structure specified below.",
            "",
            "## Output Format",
            "Return a single JSON object matching this schema:",
            json.dumps(CriticDiagnosis.model_json_schema(), indent=2),
        ])

        user_lines = [
            f"Workflow: {context['workflow_name']}",
            f"Description: {context['workflow_description']}",
            f"Success: {context['success']}",
            f"Candidates: {context['candidate_count']}",
            "",
            "## User's Original Request",
            context.get("user_text", "(no user text available)"),
            "",
            "## Parameters Used in This Run",
            json.dumps(context['parameters_used'], indent=2, default=str),
            "",
            "## Candidate Summaries (top 10)",
            json.dumps(context['all_candidate_summaries'], indent=2, default=str),
        ]

        if context["previous_issues"]:
            user_lines.extend([
                "",
                "## Previous Issues (from prior retries)",
                json.dumps(context["previous_issues"], indent=2, default=str),
            ])

        return [
            ("system", "\n".join(system_lines)),
            ("user", "\n".join(user_lines)),
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def diagnose(self, result: WorkflowResult, state: dict[str, Any]) -> CriticDiagnosis:
        """Run LLM diagnosis and return structured output."""
        try:
            context = self._build_context(result, state)
            messages = self._build_diagnosis_prompt(context)

            from langchain_core.messages import HumanMessage, SystemMessage
            msg_map = {"system": SystemMessage, "user": HumanMessage}
            lc_messages = [msg_map[role](content=text) for role, text in messages]

            raw = self.llm.invoke(lc_messages)
            content = raw.content if hasattr(raw, "content") else str(raw)
            diagnosis = self._parse_diagnosis_from_text(content)

            # Record in state history
            state.setdefault("_diagnosis_history", []).append(diagnosis.model_dump())
            return diagnosis

        except Exception as exc:
            _LOGGER.exception("LLM Critic diagnose failed completely")
            return CriticDiagnosis(
                overall_assessment=f"LLM diagnosis failed: {type(exc).__name__}",
                quality_score=0.0,
                action="abort",
                reasoning=str(exc),
                confidence=0.0,
            )

    def should_retry(self, result: WorkflowResult, state: dict[str, Any]) -> bool:
        """Compatibility shim for ExecutionController.

        Wraps diagnose() in broad exception handling so that an LLM failure
        never crashes the workflow — it simply falls back to 'no retry'.
        """
        if state.get("_llm_critic_enabled") is False:
            _LOGGER.debug("LLM Critic disabled by state flag")
            return False

        try:
            diagnosis = self.diagnose(result, state)
        except Exception as exc:
            _LOGGER.warning(
                "LLM Critic diagnose failed for %s: %s. "
                "Falling back to no-retry.",
                self.config.workflow_name,
                exc,
            )
            state["_llm_critic_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            return False

        state["_last_diagnosis"] = diagnosis.model_dump()

        if diagnosis.action in ("retry_with_adjustments", "retry_with_alternative"):
            valid_keys = set(self.config.adjustable_params.keys())
            filtered_overrides = {
                k: v for k, v in diagnosis.parameter_overrides.items()
                if k in valid_keys
            }
            if filtered_overrides != diagnosis.parameter_overrides:
                _LOGGER.warning(
                    "Critic recommended unknown parameters: %s. Filtered to: %s",
                    set(diagnosis.parameter_overrides.keys()) - valid_keys,
                    set(filtered_overrides.keys()),
                )
            state["_parameter_overrides"] = filtered_overrides

            # Determine whether this is an evaluator-only retry
            if filtered_overrides and self.config.evaluator_only_params:
                override_keys = set(filtered_overrides.keys())
                if override_keys.issubset(self.config.evaluator_only_params):
                    state["_evaluator_only_retry"] = True
                    # Map params to affected evaluators
                    affected: set[str] = set()
                    for k in override_keys:
                        affected.update(self.config.param_to_evaluators.get(k, []))
                    state["_affected_evaluators"] = sorted(affected)
                    _LOGGER.info(
                        "Critic recommends evaluator-only retry: params=%s evaluators=%s",
                        override_keys,
                        sorted(affected),
                    )
                else:
                    state.pop("_evaluator_only_retry", None)
                    state.pop("_affected_evaluators", None)

            return bool(filtered_overrides)

        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_diagnosis_from_text(content: str) -> CriticDiagnosis:
        """Manual JSON extraction from raw LLM text.

        Handles markdown code fences, trailing commentary, and raw JSON.
        """
        import json

        content = content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            if content.endswith("```"):
                content = content[:-3].strip()

        # Try direct parse first
        try:
            data = json.loads(content)
            return CriticDiagnosis.model_validate(data)
        except Exception:
            pass

        # Fallback: extract the first top-level JSON object by brace matching
        start = content.find("{")
        if start != -1:
            depth = 0
            in_string = False
            escape_next = False
            for i, ch in enumerate(content[start:], start=start):
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\":
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(content[start : i + 1])
                            return CriticDiagnosis.model_validate(data)
                        except Exception:
                            break

        # Ultimate fallback
        return CriticDiagnosis(
            overall_assessment="Failed to parse LLM output",
            quality_score=0.0,
            action="abort",
            reasoning=f"Parse error on content: {content[:200]}...",
            confidence=0.0,
        )
