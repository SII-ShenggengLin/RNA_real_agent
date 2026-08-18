"""SynthesisAgent: combine pipeline node results into a final report."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent_core.agents.base import AgentResult, BaseAgent
from agent_core.agents.quality_agent import QualityReport
from agent_core.calibrated.models import Claim, ClaimDependency
from agent_core.llm_config import get_deepseek_llm

_LOGGER = logging.getLogger(__name__)


class SynthesisAgent(BaseAgent):
    """Lightweight LLM agent for result synthesis.

    - Single-node pipeline: passes through the workflow result summary (no LLM).
    - Multi-node pipeline: generates a concise synthesis report explaining the
      relationship between workflow results.
    """

    def __init__(self, llm: Any | None = None, enable_llm: bool = True) -> None:
        self._llm = llm
        self.enable_llm = enable_llm

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = get_deepseek_llm(temperature=0.3)
        return self._llm

    def synthesize(
        self,
        plan: PipelinePlan,
        node_results: dict[str, AgentResult],
        quality_reports: dict[str, QualityReport],
    ) -> str:
        """Generate the final pipeline report."""
        if len(plan.nodes) == 1:
            return self._single_node_report(plan, node_results, quality_reports)
        return self._multi_node_report(plan, node_results, quality_reports)

    def _single_node_report(
        self,
        plan: PipelinePlan,
        node_results: dict[str, AgentResult],
        quality_reports: dict[str, QualityReport],
    ) -> str:
        node = plan.nodes[0]
        result = node_results.get(node.node_id)
        if result is None:
            return "Pipeline execution did not produce a result."
        report = quality_reports.get(node.node_id)
        parts = [result.summary or "No summary available."]
        if report and report.issues:
            parts.append("\nQuality notes:")
            for issue in report.issues:
                parts.append(f"- [{issue.severity}] {issue.category}: {issue.description}")
        return "\n".join(parts)

    def _multi_node_report(
        self,
        plan: PipelinePlan,
        node_results: dict[str, AgentResult],
        quality_reports: dict[str, QualityReport],
    ) -> str:
        if not self.enable_llm:
            return self._deterministic_multi_node_report(plan, node_results, quality_reports)

        try:
            return self._llm_multi_node_report(plan, node_results, quality_reports)
        except Exception as exc:
            _LOGGER.warning("SynthesisAgent LLM call failed: %s. Falling back to deterministic.", exc)
            return self._deterministic_multi_node_report(plan, node_results, quality_reports)

    def _deterministic_multi_node_report(
        self,
        plan: PipelinePlan,
        node_results: dict[str, AgentResult],
        quality_reports: dict[str, QualityReport],
    ) -> str:
        lines = [f"# Pipeline Report: {plan.plan_id}", ""]
        for node_id in plan.topological_order():
            result = node_results.get(node_id)
            report = quality_reports.get(node_id)
            node = plan.get_node(node_id)
            lines.append(f"## {node_id} ({node.workflow})")
            lines.append(result.summary if result else "Did not execute.")
            if report and report.action != "pass":
                lines.append(f"Quality action: {report.action}")
            lines.append("")
        return "\n".join(lines)

    def _llm_multi_node_report(
        self,
        plan: PipelinePlan,
        node_results: dict[str, AgentResult],
        quality_reports: dict[str, QualityReport],
    ) -> str:
        summaries: list[dict[str, Any]] = []
        for node_id in plan.topological_order():
            result = node_results.get(node_id)
            report = quality_reports.get(node_id)
            node = plan.get_node(node_id)
            wf_result = result.workflow_result if result else None
            summaries.append({
                "node_id": node_id,
                "workflow": node.workflow,
                "alias": node.output_alias,
                "success": result.success if result else False,
                "summary": result.summary if result else "",
                "best_candidate_sequence": (
                    wf_result.best_candidate.sequence
                    if wf_result and wf_result.best_candidate
                    else None
                ),
                "quality_action": report.action if report else "unknown",
                "quality_assessment": report.overall_assessment if report else "",
            })

        system = (
            "You are a scientific reporting assistant. Summarize the following "
            "multi-step RNA design pipeline results in a concise, structured report. "
            "Explain how each step contributes to the final outcome and highlight "
            "any quality concerns or retry actions. Keep the report under 400 words."
        )
        user = (
            f"Pipeline plan_id: {plan.plan_id}\n"
            f"Nodes (in execution order):\n{json.dumps(summaries, indent=2, default=str)}"
        )

        from langchain_core.messages import HumanMessage, SystemMessage

        raw = self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = raw.content if hasattr(raw, "content") else str(raw)
        return self._gate_report_claims(str(content))

    def _gate_report_claims(self, report: str) -> str:
        """Run headline claims of the report through the ClaimGate when active.

        Claim extraction is the only LLM step; adjudication is deterministic.
        Extraction or parse failure leaves the report unchanged (best-effort,
        recorded as an audit event) — gating can never destroy a report.
        """
        from agent_core.calibrated.runtime import CalibratedRuntime

        runtime = CalibratedRuntime.instance()
        if runtime is None:
            return report

        from langchain_core.messages import HumanMessage, SystemMessage

        extract_system = (
            "Extract the checkable scientific claims from the report below. "
            "Return ONLY a JSON array; each element: {\"text\": str, "
            "\"claim_type\": \"ranking\"|\"screening\"|\"optimization\"|\"descriptive\", "
            "\"scope\": \"absolute\"|\"within_target_relative\"|\"trend_only\", "
            "\"dependencies\": [{\"oracle\": str, \"capability\": "
            "\"scoring\"|\"screening\"|\"ranking\"|\"docking\"}]}. Dependencies name "
            "the predictive oracle each claim relies on (for example "
            "gemorna_5utr_mrl, egarps_native_probability, rnasmol); use [] for "
            "claims grounded only in deterministic computation. Max 6 claims."
        )
        try:
            raw = self.llm.invoke([
                SystemMessage(content=extract_system),
                HumanMessage(content=report),
            ])
            text = raw.content if hasattr(raw, "content") else str(raw)
            text = text.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:]
            payload = json.loads(text)
            claims = [
                Claim(
                    claim_id=f"claim_{i}",
                    text=str(item["text"]),
                    claim_type=str(item.get("claim_type", "optimization")),
                    scope=str(item.get("scope", "absolute")),
                    dependencies=[
                        ClaimDependency(
                            oracle=str(d["oracle"]),
                            capability=str(d["capability"]),
                        )
                        for d in item.get("dependencies", [])
                    ],
                )
                for i, item in enumerate(payload)
            ]
        except Exception as exc:  # noqa: BLE001 - claim pass is best-effort
            _LOGGER.warning("claim extraction failed; report left ungated: %s", exc)
            runtime.audit.record(
                "claim_verdict",
                {"claim_id": "_extraction_failed", "verdict": "skip", "reason": str(exc)},
            )
            return report

        verdicts = runtime.gate_claims(claims, task_type="pipeline_synthesis")
        lines = [report, "", "Gated claims (ClaimGate):"]
        for claim, verdict in zip(claims, verdicts):
            if verdict.verdict == "pass":
                lines.append(f"- PASS: {claim.text}")
            elif verdict.verdict == "downgrade":
                lines.append(f"- {verdict.rewritten_text or claim.text}")
            else:
                lines.append(f"- [REJECTED: {verdict.reason}] {claim.text}")
        return "\n".join(lines)
