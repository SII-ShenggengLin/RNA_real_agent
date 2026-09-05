"""Layer-3 integration tests for MrnaCdsDesignWorkflow via multi-agent execution.

Covers:
- Workflow invocation through PipelineAgent / SpecialistAgent
- Single-node PipelinePlan execution
- QualityAgent review (LLM critic disabled for unit tests)
- Progress callback propagation from the workflow
- Failure handling (empty candidates)
- Workflow-specific parameter handling (truncate_n_terminal)
"""

from __future__ import annotations

from typing import Any, Optional

from agent_core.agents import (
    PipelineAgent,
    QualityAgent,
    SpecialistAgent,
    SynthesisAgent,
)
from agent_core.capabilities.base import CapabilityResult
from agent_core.pipeline.models import PipelinePlan
from agent_core.quality_profiles.mrna_cds_design import MRNA_CDS_QUALITY_PROFILE
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow


class _StubCapability:
    """Minimal capability stub for unit tests."""

    def __init__(self, name: str, output: dict[str, Any]) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        result = CapabilityResult(
            success=True,
            tool_name=self._name,
            output=dict(self._output),
        )
        # Mirror real Capability._writeback behaviour for layer-3 state tests
        if state is not None:
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"][self._name] = result.output
        return result


class _StubLinearDesign(_StubCapability):
    """Returns distinct sequences per lambda so deduplication yields multiple candidates."""

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        lam = float(tool_args.get("lambda_value", 0.0))
        # Vary length with lambda so candidates are distinct
        repeats = 30 + int(lam) * 5
        seq = "AUG" * repeats
        output = {
            "generated_sequence": seq,
            "structure": "." * (len(seq)),
            "mfe": -10.0 - lam,
            "cai_score": 0.8,
        }
        if state is not None:
            if "tool_results" not in state:
                state["tool_results"] = {}
            state["tool_results"][self._name] = output
        return CapabilityResult(
            success=True,
            tool_name=self._name,
            output=output,
        )


class _StubRegistry:
    """Duck-typed registry satisfying CapabilityRegistry interface."""

    def __init__(self, caps: dict[str, _StubCapability]) -> None:
        self._caps = caps

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> _StubCapability:
        return self._caps[name]

    def list_names(self) -> list[str]:
        return sorted(self._caps.keys())


def _build_cds_registry() -> _StubRegistry:
    """Registry with all capabilities required by MrnaCdsDesignWorkflow."""
    caps: dict[str, _StubCapability] = {
        "design_mrna_cds_with_lineardesign": _StubLinearDesign(
            "design_mrna_cds_with_lineardesign", {}
        ),
        "design_mrna_cds_with_rnarl": _StubCapability(
            "design_mrna_cds_with_rnarl",
            {"generated_sequence": "AUG" * 35},
        ),
        "design_mrna_cds_with_gemorna": _StubCapability(
            "design_mrna_cds_with_gemorna",
            {"generated_sequence": "AUG" * 40},
        ),
        "predict_rna_secondary_structure": _StubCapability(
            "predict_rna_secondary_structure",
            {
                "structure": "." * 200,
                "mfe_kcal_per_mol": -50.0,
            },
        ),
        "predict_rna_secondary_structure_with_linearfold": _StubCapability(
            "predict_rna_secondary_structure_with_linearfold",
            {
                "structure": "." * 200,
                "mfe": -45.0,
            },
        ),
        "compute_rna_sequence_gc_content": _StubCapability(
            "compute_rna_sequence_gc_content",
            {"gc_content": 0.5, "sequence_length": 200},
        ),
        "compute_dot_bracket_unpaired_fraction": _StubCapability(
            "compute_dot_bracket_unpaired_fraction",
            {"unpaired_fraction": 0.5, "structure_length": 200, "dot_count": 100},
        ),
        "predict_mrna_stability_with_rnastop": _StubCapability(
            "predict_mrna_stability_with_rnastop",
            {"overall_stability": 0.5},
        ),
        "compute_cai_for_cds_sequence": _StubCapability(
            "compute_cai_for_cds_sequence",
            {"cai_score": 0.85, "species": "Homo sapiens"},
        ),
    }
    return _StubRegistry(caps)


def _build_pipeline_agent(registry: _StubRegistry) -> PipelineAgent:
    """Build a PipelineAgent with a SpecialistAgent for mrna_cds_design."""
    workflow = MrnaCdsDesignWorkflow(registry)
    specialist = SpecialistAgent(workflow, MRNA_CDS_QUALITY_PROFILE)
    quality_agent = QualityAgent()
    synthesis_agent = SynthesisAgent(enable_llm=False)
    return PipelineAgent(
        specialist_registry={"mrna_cds_design": specialist},
        quality_agent=quality_agent,
        synthesis_agent=synthesis_agent,
    )


def test_mrna_cds_design_via_pipeline_agent():
    """MrnaCdsDesignWorkflow executes end-to-end through PipelineAgent."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
        },
        output_alias="cds_result",
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.success is True

    wf_result = node_result.workflow_result
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
    assert wf_result.best_candidate is not None

    # Quality review should be present and recommend pass for the successful run.
    quality_report = result.quality_reports["n1"]
    assert quality_report.action == "pass"

    # Tool results are captured in the workflow's state writeback on the result.
    state_writeback = getattr(wf_result, "_state_writeback", {})
    tool_results = state_writeback.get("tool_results", {})
    assert "design_mrna_cds_with_lineardesign" in tool_results
    assert "compute_rna_sequence_gc_content" in tool_results
    assert "predict_rna_secondary_structure_with_linearfold" in tool_results


def test_mrna_cds_design_progress_callback():
    """Progress callback receives workflow-level generate and evaluate events."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
        },
    )

    events: list[dict[str, Any]] = []

    def _cb(evt: dict[str, Any]) -> None:
        events.append(evt)

    pipeline.execute(plan, {"_quality_review_enabled": False}, progress_callback=_cb)

    assert any(e.get("event") == "generate_complete" for e in events)
    assert any(e.get("event") == "evaluate_progress" for e in events)


def test_mrna_cds_design_empty_candidates_graceful():
    """If all design tools fail, workflow returns success=False with empty list."""
    # Registry with NO design capabilities
    registry = _StubRegistry({})
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "all",
            "navigation": False,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    # Pipeline reports failure because the only critical node failed.
    assert result.success is False
    node_result = result.node_results["n1"]
    assert node_result.success is False

    wf_result = node_result.workflow_result
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is False
    assert "empty_candidate_list" in wf_result.errors


def test_mrna_cds_design_no_critic_retry():
    """With critic disabled, QualityAgent passes and retry is never triggered."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    node_result = result.node_results["n1"]
    assert node_result.metadata.get("retry_count", 0) == 0
    assert node_result.metadata["quality_report"].action == "pass"


def test_mrna_cds_design_truncation_n_terminal():
    """truncate_n_terminal uses only the first N amino acids for design."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    full_seq = "M" * 100  # 100 aa
    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": full_seq,
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "truncate_n_terminal": 30,
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    assert result.success is True
    wf_result = result.node_results["n1"].workflow_result
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
    best = wf_result.best_candidate
    assert best is not None
    # StubLinearDesign returns AUG * (30 + lambda*5); lambda=0 -> 90 nt = 30 aa CDS
    assert len(best.sequence) == 90
    assert best.metadata.get("protein_sequence_used") == "M" * 30
    assert best.metadata.get("protein_sequence") == full_seq


def test_mrna_cds_design_unsupported_cai_species_fails_fast_for_lineardesign():
    """Species-correct design contract (2026-08-25 fix): LinearDesign with an
    unresolvable cai_species fails at the input layer instead of silently
    designing against the service's default human table."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "cai_species": "unsupported_species_xyz",
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    assert result.success is False
    node = result.node_results["n1"]
    assert node.success is False
    assert any("No codon-usage table" in e for e in node.errors)


def test_mrna_cds_design_unsupported_cai_species_still_runs_without_lineardesign():
    """Without LinearDesign (gemorna engine) an unknown CAI species does not
    fail the run up front — the CAI evaluator surfaces it per candidate."""
    registry = _build_cds_registry()
    pipeline = _build_pipeline_agent(registry)

    plan = PipelinePlan.single(
        workflow="mrna_cds_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "gemorna",
            "cai_species": "unsupported_species_xyz",
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline.execute(plan, state)

    assert result.success is True
    wf_result = result.node_results["n1"].workflow_result
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
