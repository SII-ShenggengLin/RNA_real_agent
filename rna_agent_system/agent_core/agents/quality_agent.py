"""Unified quality review agent."""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from agent_core.llm_config import get_deepseek_llm
from agent_core.workflow_models import WorkflowResult

_LOGGER = logging.getLogger(__name__)


class QualityIssue(BaseModel):
    """One specific quality issue."""

    severity: Literal["critical", "warning", "info"]
    category: str
    description: str
    metric_value: float | None = None
    threshold: float | None = None


class QualityReport(BaseModel):
    """Structured quality review report."""

    overall_assessment: str
    quality_score: float = Field(..., ge=0.0, le=1.0)
    issues: list[QualityIssue] = Field(default_factory=list)
    action: Literal["pass", "retry_with_adjustments", "retry_with_alternative", "abort"]
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.5
    # Hints for evaluator-only partial reruns.
    evaluator_only: bool = False
    affected_evaluators: list[str] = Field(default_factory=list)


class QualityProfile(BaseModel):
    """Per-workflow quality review configuration.

    ``build_context`` and ``build_prompt`` are optional extension points.
    Use them only when the default context/prompt cannot express
    workflow-specific tuning guidance; prefer ``build_context`` over
    ``build_prompt`` to avoid turning profiles into a subclass hierarchy.
    """

    workflow_name: str
    workflow_description: str = ""
    evaluation_dimensions: list[str] = Field(default_factory=list)
    # {param_name: {"type": "int|float|enum|bool", "min": ..., "max": ..., "values": [...], "hint": ...}}
    adjustable_params: dict[str, dict] = Field(default_factory=dict)
    retry_strategy: Literal["adjust_params", "change_tool", "abort_only"] = "adjust_params"
    max_retries: int = 2
    # Parameters that only affect evaluators (candidate generation is unchanged).
    evaluator_only_params: set[str] = Field(default_factory=set)
    # Mapping: param -> list of evaluator class names.
    param_to_evaluators: dict[str, list[str]] = Field(default_factory=dict)
    # Optional custom context builder.
    build_context: Callable[[WorkflowResult, dict[str, Any]], dict[str, Any]] | None = None
    # Optional custom prompt builder; receives context and profile, returns message pairs.
    build_prompt: Callable[[dict[str, Any], "QualityProfile"], list[tuple[str, str]]] | None = None


class QualityAgent:
    """Unified quality review agent.

    Uses a workflow-specific QualityProfile to diagnose a WorkflowResult and
    produce a QualityReport. Retry decisions are left to SpecialistAgent.
    """

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = get_deepseek_llm(temperature=0.2)
        return self._llm

    def review(
        self,
        result: WorkflowResult,
        profile: QualityProfile,
        state: dict[str, Any],
    ) -> QualityReport:
        """Review a workflow result and return a QualityReport."""
        if state.get("_quality_review_enabled") is False:
            return self._pass_report("Quality review disabled by state flag.")

        if not profile.evaluation_dimensions:
            return self._pass_report(
                f"Workflow {profile.workflow_name} is deterministic; no LLM review needed."
            )

        hard_failure = result.is_hard_failure

        try:
            context = self._build_context(result, profile, state)
            if profile.build_prompt is not None:
                messages = profile.build_prompt(context, profile)
            else:
                messages = self._build_diagnosis_prompt(context, profile)

            from langchain_core.messages import HumanMessage, SystemMessage

            msg_map = {"system": SystemMessage, "user": HumanMessage}
            lc_messages = [msg_map[role](content=text) for role, text in messages]
            raw = self.llm.invoke(lc_messages)
            content = raw.content if hasattr(raw, "content") else str(raw)
            report = self._parse_report_from_text(content)
        except Exception as exc:
            _LOGGER.exception("QualityAgent LLM diagnosis failed")
            # GOVERNANCE (2026-08-10): the review is advisory infrastructure, so
            # an LLM failure must never decide the fate of a run. The old
            # fallback returned action="abort" on ANY exception — including
            # infrastructure failures (API billing 402, network) that have
            # nothing to do with candidate quality — and SpecialistAgent then
            # flipped successful runs to failed (DeepSeek 402 incident,
            # 2026-07-27). The review is now marked "review_unavailable" and
            # reported as a zero-confidence pass; the workflow result stands on
            # its own. state["_quality_review_error"] remains the audit marker
            # downstream consumers use to tell infra failure apart from a
            # completed review; keep setting it if this code moves.
            state["_quality_review_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            return QualityReport(
                overall_assessment=(
                    f"review_unavailable: quality diagnosis failed ({type(exc).__name__})"
                ),
                quality_score=1.0,
                action="pass",
                reasoning=(
                    f"Quality review unavailable ({type(exc).__name__}: {exc}). "
                    "Review is advisory; the workflow result is unaffected."
                ),
                confidence=0.0,
            )

        # Protect user-explicit parameters.
        protected_params = set(state.get("_user_explicit_params", []))
        filtered_overrides = self._filter_overrides(
            report.parameter_overrides, profile, protected_params, state
        )
        report.parameter_overrides = filtered_overrides

        # Determine evaluator-only retry hints.
        if report.action in ("retry_with_adjustments", "retry_with_alternative"):
            override_keys = set(filtered_overrides.keys())
            if (
                profile.evaluator_only_params
                and override_keys
                and override_keys.issubset(profile.evaluator_only_params)
            ):
                report.evaluator_only = True
                affected: set[str] = set()
                for k in override_keys:
                    affected.update(profile.param_to_evaluators.get(k, []))
                report.affected_evaluators = sorted(affected)

        # If there is a hard failure, ensure action is retry/abort, never pass.
        if hard_failure and report.action == "pass":
            report.action = "retry_with_adjustments"
            report.reasoning = (
                report.reasoning + " " if report.reasoning else ""
            ) + "Hard failure detected; converting to retry."

        # Record in state for audit.
        state.setdefault("_diagnosis_history", []).append(report.model_dump())
        state["_last_diagnosis"] = report.model_dump()
        state["_parameter_overrides"] = dict(report.parameter_overrides)
        return report

    def _pass_report(self, reasoning: str) -> QualityReport:
        return QualityReport(
            overall_assessment=reasoning,
            quality_score=1.0,
            action="pass",
            reasoning=reasoning,
            confidence=1.0,
        )

    def _build_context(
        self,
        result: WorkflowResult,
        profile: QualityProfile,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if profile.build_context is not None:
            context = profile.build_context(result, state)
        else:
            context = self._build_default_context(result, state)
        context.setdefault("workflow_name", profile.workflow_name)
        context.setdefault("workflow_description", profile.workflow_description)
        return context

    @staticmethod
    def _build_default_context(
        result: WorkflowResult,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Default context builder; exposed for profile-specific builders."""
        params = state.get("_last_workflow_params", {})

        candidate_summaries: list[dict[str, Any]] = []
        for c in result.all_candidates:
            mb = c.metadata.get("metrics_bundle", {}) if c.metadata else {}
            candidate_summaries.append({
                "id": c.id,
                "source": c.source,
                "length": len(c.sequence) if c.sequence else 0,
                "scores": c.scores,
                "metrics": {
                    k: v for k, v in mb.items()
                    if isinstance(v, (int, float, str, bool))
                },
            })

        source_counts = Counter(c.source for c in result.all_candidates)
        source_distribution = dict(source_counts.most_common())

        previous_best_summary: dict[str, Any] | None = None
        prev_wf = state.get("_previous_workflow_result")
        if prev_wf is not None:
            prev_best = getattr(prev_wf, "best_candidate", None)
            if prev_best is not None:
                prev_meta = getattr(prev_best, "metadata", None) or {}
                prev_mb = prev_meta.get("metrics_bundle", {}) if isinstance(prev_meta, dict) else {}
                previous_best_summary = {
                    "source": getattr(prev_best, "source", "N/A"),
                    "length": len(getattr(prev_best, "sequence", "")),
                    "scores": getattr(prev_best, "scores", None),
                    "metrics": {
                        k: v for k, v in prev_mb.items()
                        if isinstance(v, (int, float, str, bool))
                    },
                }

        max_display = 5
        display_summaries: list[dict[str, Any]] = []
        seen_sources: set[str] = set()
        for s in candidate_summaries:
            if s["source"] not in seen_sources:
                display_summaries.append(s)
                seen_sources.add(s["source"])
        for s in candidate_summaries:
            if len(display_summaries) >= max_display:
                break
            if s not in display_summaries:
                display_summaries.append(s)

        return {
            "success": getattr(result, "success", False),
            "candidate_count": len(result.all_candidates),
            "best_candidate_summary": candidate_summaries[0] if candidate_summaries else None,
            "all_candidate_summaries": display_summaries,
            "source_distribution": source_distribution,
            "parameters_used": params,
            "user_text": state.get("user_text", ""),
            "previous_best_summary": previous_best_summary,
            "previous_issues": [
                d.get("issues", [])
                for d in state.get("_diagnosis_history", [])
            ],
        }

    def _build_diagnosis_prompt(
        self,
        context: dict[str, Any],
        profile: QualityProfile,
    ) -> list[tuple[str, str]]:
        return self._build_default_prompt(context, profile)

    @staticmethod
    def _build_default_prompt(
        context: dict[str, Any],
        profile: QualityProfile,
    ) -> list[tuple[str, str]]:
        system_lines = [
            "You are an expert RNA bioinformatics reviewer and quality-assurance engineer.",
            "Your job is to evaluate the output of an RNA design workflow and decide if retry is needed.",
            "",
            "## Evaluation Criteria",
            *profile.evaluation_dimensions,
            "",
            "## Adjustable Parameters (for retry recommendations)",
        ]

        for name, spec in profile.adjustable_params.items():
            hint = spec.get("hint", "")
            type_info = spec.get("type", "any")
            if type_info == "enum":
                allowed = spec.get("values", [])
                if allowed:
                    hint = f"{hint} ALLOWED VALUES ONLY: {allowed}. NEVER recommend a value outside this list."
            system_lines.append(f"- {name} ({type_info}): {hint}")

        system_lines.extend([
            "",
            "## Rules",
            "1. Analyze ALL candidates, not just the best one.",
            "2. Identify specific issues with severity (critical/warning/info).",
            "3. If retry is warranted, recommend concrete parameter_overrides.",
            "4. ONLY recommend parameters listed above in 'Adjustable Parameters'. Do NOT invent new parameters.",
            "5. For enum parameters, you MUST choose a value from the ALLOWED VALUES list.",
            "6. Do NOT set numeric parameters to null/None. Only use valid numbers within any stated min/max range.",
            "7. Consider previous issues (if any) to avoid repeating the same mistakes.",
            "8. PAY SPECIAL ATTENTION to the user's original request. Failure to meet user constraints is a CRITICAL issue.",
            "9. DEFAULT PARAMETERS ARE CAREFULLY TUNED. Only recommend parameter_overrides when you have STRONG evidence.",
            "10. If 'Previous Best Candidate Summary' is provided, you MAY compare current candidates against those exact previous metrics.",
            "11. Return your diagnosis in the EXACT JSON structure specified below.",
            "",
            "## Output Format",
            "Return a single JSON object matching this schema:",
            json.dumps(QualityReport.model_json_schema(), indent=2),
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
            "## Source Distribution",
            json.dumps(context.get('source_distribution', {}), indent=2, default=str),
            "",
            "## Candidate Summaries (source-diverse top candidates)",
            json.dumps(context['all_candidate_summaries'], indent=2, default=str),
        ]

        if context.get("previous_best_summary"):
            user_lines.extend([
                "",
                "## Previous Best Candidate Summary (from prior turn)",
                json.dumps(context["previous_best_summary"], indent=2, default=str),
            ])

        if context.get("previous_issues"):
            user_lines.extend([
                "",
                "## Previous Issues (from prior retries)",
                json.dumps(context["previous_issues"], indent=2, default=str),
            ])

        return [("system", "\n".join(system_lines)), ("user", "\n".join(user_lines))]

    def _filter_overrides(
        self,
        overrides: dict[str, Any],
        profile: QualityProfile,
        protected_params: set[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        # Only parameters declared as adjustable in the QualityProfile may be
        # overridden. This keeps the LLM diagnosis aligned with the retry
        # strategy and prevents accidental mutation of workflow internals.
        valid_keys = set(profile.adjustable_params.keys())

        filtered: dict[str, Any] = {}
        for k, v in overrides.items():
            if k not in valid_keys:
                _LOGGER.warning("QualityAgent unknown parameter: %s=%s", k, v)
                continue
            if k in protected_params:
                _LOGGER.info("QualityAgent preserving user-explicit parameter: %s", k)
                continue
            if not self._validate_override_value(k, v, profile):
                continue
            filtered[k] = v
        return filtered

    def _validate_override_value(self, name: str, value: Any, profile: QualityProfile) -> bool:
        spec = profile.adjustable_params.get(name)
        if not spec:
            return True

        ptype = spec.get("type")
        try:
            if ptype == "int":
                value = int(value)
            elif ptype == "float":
                value = float(value)
        except (TypeError, ValueError):
            _LOGGER.warning("QualityAgent non-numeric value for %s: %s", name, value)
            return False

        if ptype in ("int", "float"):
            min_v = spec.get("min")
            max_v = spec.get("max")
            if min_v is not None and value < min_v:
                return False
            if max_v is not None and value > max_v:
                return False

        if ptype == "enum":
            allowed = spec.get("values", [])
            if allowed and value not in allowed:
                return False

        return True

    @staticmethod
    def _parse_report_from_text(content: str) -> QualityReport:
        content = content.strip()

        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            if content.endswith("```"):
                content = content[:-3].strip()

        try:
            data = json.loads(content)
            return QualityReport.model_validate(data)
        except Exception:
            pass

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
                            return QualityReport.model_validate(data)
                        except Exception:
                            break

        return QualityReport(
            overall_assessment="Failed to parse LLM output",
            quality_score=0.0,
            action="abort",
            reasoning=f"Parse error on content: {content[:200]}...",
            confidence=0.0,
        )
