"""Layer 3 integration tests for RNA secondary structure design workflow.

Covers:
1. PipelineAgent -> workflow progress_callback forwarding
2. PipelineResult structure and quality review metadata
3. QualityAgent retry loop via SpecialistAgent
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from agent_core.agents import (
    PipelineAgent,
    QualityAgent,
    QualityReport,
    SpecialistAgent,
    SynthesisAgent,
)
from agent_core.capabilities.base import CapabilityResult
from agent_core.pipeline.models import PipelinePlan
from agent_core.quality_profiles.rna_secondary_structure_design import (
    RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
)
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignWorkflow,
)


def _make_full_registry():
    """Registry with all mocked capabilities for secondary structure workflow."""
    reg = MagicMock()

    # Generation mock
    base_seqs = ["AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC", "GCAUGCAUGCAUGCAUGCAUGCAUGCAUGC"]

    def _inverse_invoke(args, state=None):
        invocation = args.get("repeats", 10)
        seq = base_seqs[invocation % len(base_seqs)]
        return CapabilityResult(
            success=True,
            tool_name="inverse_fold_rna_secondary_structure_vienna",
            output={
                "best_sequence": seq,
                "hamming_distance": 2,
                "partition_probability": 0.85,
                "target_structure": "((((....))))....((((....))))",
            },
        )

    cap_inverse = MagicMock()
    cap_inverse.invoke = _inverse_invoke

    # Evaluation mocks
    def _gc_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_rna_sequence_gc_content",
            output={"gc_content": 0.48, "sequence_length": 30},
        )

    def _fold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_secondary_structure",
            output={
                "structure": "((((....))))....((((....))))",
                "mfe_kcal_per_mol": -15.5,
                "backend": "ViennaRNA",
            },
        )

    caps = {
        "inverse_fold_rna_secondary_structure_vienna": cap_inverse,
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


def _make_pipeline_agent(reg, quality_review_enabled: bool = False):
    """Build a PipelineAgent with a SpecialistAgent for the secondary-structure workflow."""
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE)
    quality_agent = QualityAgent()
    synthesis_agent = SynthesisAgent(enable_llm=False)
    return PipelineAgent(
        specialist_registry={wf.name: specialist},
        quality_agent=quality_agent,
        synthesis_agent=synthesis_agent,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. PipelineAgent + progress_callback
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_agent_progress_callback():
    """PipelineAgent should forward progress_callback to the workflow run."""
    reg = _make_full_registry()
    agent = _make_pipeline_agent(reg)

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    events = []

    def callback(event: dict[str, Any]) -> None:
        events.append(event)

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = agent.execute(plan, state, progress_callback=callback)

    assert result.success is True
    assert "n1" in result.node_results
    assert result.node_results["n1"].workflow_result is not None
    assert result.node_results["n1"].workflow_result.success is True

    assert len(events) > 0
    event_types = [e["event"] for e in events]
    assert "generate_complete" in event_types
    assert "evaluate_progress" in event_types


def test_pipeline_agent_no_callback():
    """PipelineAgent should execute successfully without a progress_callback."""
    reg = _make_full_registry()
    agent = _make_pipeline_agent(reg)

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = agent.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.success is True
    assert node_result.workflow_result is not None
    assert len(node_result.workflow_result.all_candidates) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. PipelineResult structure and quality metadata
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_result_structure():
    """PipelineResult should expose node results, quality reports, and final report."""
    reg = _make_full_registry()
    agent = _make_pipeline_agent(reg)

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = agent.execute(plan, state)

    assert isinstance(result.success, bool)
    assert result.success is True
    assert "n1" in result.node_results
    assert "n1" in result.quality_reports

    node_result = result.node_results["n1"]
    assert node_result.node_id == "n1"
    assert node_result.workflow == "rna_secondary_structure_design"
    assert node_result.workflow_result is not None
    assert node_result.metadata["retry_count"] == 0

    quality_report = result.quality_reports["n1"]
    assert quality_report.action == "pass"

    assert result.final_report


# ─────────────────────────────────────────────────────────────────────────────
# 3. QualityAgent retry path
# ─────────────────────────────────────────────────────────────────────────────


class _OneTimeRetryQualityAgent(QualityAgent):
    """QualityAgent that requests retry exactly once, then passes."""

    def __init__(self):
        super().__init__(llm=None)
        self.review_count = 0

    def review(self, result, profile, state):
        self.review_count += 1
        if self.review_count == 1:
            return QualityReport(
                overall_assessment="Retry requested",
                quality_score=0.5,
                action="retry_with_adjustments",
                parameter_overrides={"repeats": 20},
                reasoning="Increase search repeats for better structural fidelity.",
            )
        return QualityReport(
            overall_assessment="Pass",
            quality_score=1.0,
            action="pass",
            reasoning="Acceptable after retry.",
        )


def test_quality_agent_retry_once():
    """A retry recommendation from QualityAgent should trigger one workflow rerun."""
    reg = _make_full_registry()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE)
    quality_agent = _OneTimeRetryQualityAgent()
    synthesis_agent = SynthesisAgent(enable_llm=False)
    agent = PipelineAgent(
        specialist_registry={wf.name: specialist},
        quality_agent=quality_agent,
        synthesis_agent=synthesis_agent,
    )

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": True, "_quality_auto_retry": True}
    result = agent.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.workflow_result is not None
    assert node_result.metadata["retry_count"] == 1


class _AlwaysRetryQualityAgent(QualityAgent):
    """QualityAgent that always recommends retry with a changing override."""

    def __init__(self):
        super().__init__(llm=None)

    def review(self, result, profile, state):
        params = state.get("_last_workflow_params", {})
        current_repeats = params.get("repeats", 10)
        return QualityReport(
            overall_assessment="Retry requested",
            quality_score=0.3,
            action="retry_with_adjustments",
            parameter_overrides={"repeats": current_repeats + 1},
            reasoning="Keep increasing repeats.",
        )


def test_quality_agent_max_retries_exhausted():
    """SpecialistAgent should stop retrying once the QualityProfile max_retries is reached."""
    reg = _make_full_registry()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    specialist = SpecialistAgent(wf, RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE)
    quality_agent = _AlwaysRetryQualityAgent()
    synthesis_agent = SynthesisAgent(enable_llm=False)
    agent = PipelineAgent(
        specialist_registry={wf.name: specialist},
        quality_agent=quality_agent,
        synthesis_agent=synthesis_agent,
    )

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": True, "_quality_auto_retry": True}
    result = agent.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.metadata["retry_count"] == RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE.max_retries


def test_quality_agent_disabled_no_retry():
    """With the critic disabled, QualityAgent should pass and no retry occurs."""
    reg = _make_full_registry()
    agent = _make_pipeline_agent(reg, quality_review_enabled=False)

    plan = PipelinePlan.single(
        workflow="rna_secondary_structure_design",
        static_params={
            "target_structure": "((((....))))....((((....))))",
            "num_invocations": 1,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = agent.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.metadata["retry_count"] == 0
    assert result.quality_reports["n1"].action == "pass"


def test_workflow_run_signature_has_progress_callback():
    """RnaSecondaryStructureDesignWorkflow.run() must accept progress_callback."""
    import inspect

    sig = inspect.signature(RnaSecondaryStructureDesignWorkflow.run)
    assert "progress_callback" in sig.parameters
    param = sig.parameters["progress_callback"]
    assert param.default is None
