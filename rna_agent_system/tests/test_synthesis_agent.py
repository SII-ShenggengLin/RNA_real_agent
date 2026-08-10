"""Unit tests for SynthesisAgent."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_core.agents.base import AgentResult
from agent_core.agents.quality_agent import QualityIssue, QualityReport
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.pipeline.models import PipelineEdge, PipelineNode, PipelinePlan
from agent_core.workflow_models import Candidate, WorkflowResult


class TestSynthesisAgent:
    def _make_plan(self, node_count: int = 1) -> PipelinePlan:
        nodes = [
            PipelineNode(
                node_id=f"n{i}",
                workflow=f"wf{i}",
                static_params={},
                output_alias=f"alias{i}",
            )
            for i in range(node_count)
        ]
        edges = [
            PipelineEdge(source=f"n{i}", target=f"n{i + 1}")
            for i in range(node_count - 1)
        ]
        return PipelinePlan(plan_id="test_plan", nodes=nodes, edges=edges)

    def _make_result(
        self,
        node_id: str,
        workflow: str,
        summary: str = "summary",
        success: bool = True,
    ) -> AgentResult:
        return AgentResult(
            node_id=node_id,
            workflow=workflow,
            success=success,
            workflow_result=WorkflowResult(
                success=success,
                task_id="t1",
                summary=summary,
                best_candidate=Candidate(sequence="AAAA", sequence_type="rna"),
            ),
            summary=summary,
        )

    def _make_report(self, action: str = "pass", issues: list[QualityIssue] | None = None) -> QualityReport:
        return QualityReport(
            overall_assessment="ok",
            quality_score=0.9,
            action=action,  # type: ignore[arg-type]
            issues=issues or [],
        )

    def test_single_node_pass_through_no_llm(self):
        """Single-node pipelines pass through the result summary without calling LLM."""
        agent = SynthesisAgent(llm=MagicMock(), enable_llm=True)
        plan = self._make_plan(1)
        node_results = {"n0": self._make_result("n0", "wf0", "designed mRNA")}
        quality_reports = {"n0": self._make_report("pass")}

        report = agent.synthesize(plan, node_results, quality_reports)

        assert "designed mRNA" in report
        agent.llm.invoke.assert_not_called()

    def test_single_node_includes_quality_notes(self):
        """Single-node report appends quality issues when present."""
        agent = SynthesisAgent(llm=MagicMock())
        plan = self._make_plan(1)
        node_results = {"n0": self._make_result("n0", "wf0", "designed mRNA")}
        quality_reports = {
            "n0": self._make_report(
                "retry_with_adjustments",
                [QualityIssue(severity="warning", category="GC", description="GC too high")],
            )
        }

        report = agent.synthesize(plan, node_results, quality_reports)

        assert "designed mRNA" in report
        assert "Quality notes" in report
        assert "GC too high" in report

    def test_multi_node_deterministic_when_llm_disabled(self):
        """Multi-node pipelines use deterministic report when enable_llm=False."""
        agent = SynthesisAgent(llm=MagicMock(), enable_llm=False)
        plan = self._make_plan(2)
        node_results = {
            "n0": self._make_result("n0", "wf0", "designed CDS"),
            "n1": self._make_result("n1", "wf1", "folded structure"),
        }
        quality_reports = {
            "n0": self._make_report("pass"),
            "n1": self._make_report("retry_with_adjustments"),
        }

        report = agent.synthesize(plan, node_results, quality_reports)

        assert "Pipeline Report: test_plan" in report
        assert "designed CDS" in report
        assert "folded structure" in report
        assert "Quality action: retry_with_adjustments" in report
        agent.llm.invoke.assert_not_called()

    def test_multi_node_llm_success(self):
        """Multi-node pipelines call LLM when enabled and available."""
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="LLM synthesized report")
        agent = SynthesisAgent(llm=llm, enable_llm=True)
        plan = self._make_plan(2)
        node_results = {
            "n0": self._make_result("n0", "wf0", "designed CDS"),
            "n1": self._make_result("n1", "wf1", "folded structure"),
        }
        quality_reports = {
            "n0": self._make_report("pass"),
            "n1": self._make_report("pass"),
        }

        report = agent.synthesize(plan, node_results, quality_reports)

        assert report == "LLM synthesized report"
        llm.invoke.assert_called_once()

    def test_multi_node_llm_failure_falls_back(self):
        """LLM failures fall back to deterministic report."""
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM unavailable")
        agent = SynthesisAgent(llm=llm, enable_llm=True)
        plan = self._make_plan(2)
        node_results = {
            "n0": self._make_result("n0", "wf0", "designed CDS"),
            "n1": self._make_result("n1", "wf1", "folded structure"),
        }
        quality_reports = {
            "n0": self._make_report("pass"),
            "n1": self._make_report("pass"),
        }

        report = agent.synthesize(plan, node_results, quality_reports)

        assert "Pipeline Report: test_plan" in report
        assert "designed CDS" in report

    def test_missing_result_handled_gracefully(self):
        """Missing node results are reported gracefully."""
        agent = SynthesisAgent(llm=MagicMock())
        plan = self._make_plan(1)
        node_results: dict[str, AgentResult] = {}
        quality_reports: dict[str, QualityReport] = {}

        report = agent.synthesize(plan, node_results, quality_reports)

        assert "did not produce a result" in report
