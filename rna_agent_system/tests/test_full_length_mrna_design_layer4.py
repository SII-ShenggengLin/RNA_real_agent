"""Layer-3 integration tests for FullLengthMrnaDesignWorkflow via multi-agent execution.

Covers:
- Workflow invocation through PipelineAgent + SpecialistAgent
- Progress callback propagation from the workflow
- QualityAgent integration with FULL_LENGTH_MRNA_QUALITY_PROFILE
"""

from __future__ import annotations

from typing import Any, Optional

from agent_core.agents import (
    PipelineAgent,
    QualityAgent,
    QualityReport,
    SpecialistAgent,
    SynthesisAgent,
)
from agent_core.capabilities.base import CapabilityResult
from agent_core.pipeline.models import PipelinePlan, PipelineResult
from agent_core.quality_profiles.full_length_mrna_design import (
    FULL_LENGTH_MRNA_QUALITY_PROFILE,
)
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignWorkflow


class _StubCapability:
    """Minimal capability stub for unit tests."""

    def __init__(self, name: str, output: dict[str, Any]) -> None:
        self._name = name
        self._output = output

    @property
    def name(self) -> str:
        return self._name

    def _build_output(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        return dict(self._output)

    def invoke(
        self,
        tool_args: dict[str, Any],
        state: Optional[dict[str, Any]] = None,
    ) -> CapabilityResult:
        output = self._build_output(tool_args)
        result = CapabilityResult(
            success=True,
            tool_name=self._name,
            output=output,
        )
        # Mirror Capability._writeback behaviour
        if state is not None:
            state.setdefault("tool_results", {})
            state["tool_results"][self._name] = output
        return result


class _StubLinearDesign(_StubCapability):
    """Returns distinct sequences per lambda so deduplication yields multiple candidates."""

    def _build_output(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        lam = float(tool_args.get("lambda_value", 0.0))
        repeats = 30 + int(lam) * 5
        seq = "AUG" * repeats
        return {
            "generated_sequence": seq,
            "structure": "." * len(seq),
            "mfe": -10.0 - lam,
            "cai_score": 0.8,
        }


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


class _MockLLM:
    """Deterministic LLM stub for QualityAgent tests."""

    def __init__(self, response_content: str) -> None:
        self.response_content = response_content
        self.last_messages: list[tuple[str, str]] = []

    def invoke(self, messages: list[Any]) -> Any:
        # messages are langchain Message objects; extract role/content for inspection.
        role_map = {
            "SystemMessage": "system",
            "HumanMessage": "user",
        }
        self.last_messages = [
            (role_map.get(type(m).__name__, "unknown"), getattr(m, "content", str(m)))
            for m in messages
        ]

        class _Response:
            pass

        resp = _Response()
        resp.content = self.response_content
        return resp


def _pass_report_json() -> str:
    return QualityReport(
        overall_assessment="All quality checks passed.",
        quality_score=1.0,
        action="pass",
        reasoning="Mocked deterministic pass.",
        confidence=1.0,
    ).model_dump_json()


def _build_full_registry(ires_score: float = 0.1) -> _StubRegistry:
    """Registry with all capabilities required by FullLengthMrnaDesignWorkflow."""
    caps: dict[str, _StubCapability] = {
        # CDS design tools (reused by internal MrnaCdsDesignWorkflow)
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
        # Fold & eval tools (reused by internal CDS workflow + full-length)
        "predict_rna_secondary_structure": _StubCapability(
            "predict_rna_secondary_structure",
            {
                "structure": "." * 300,
                "mfe_kcal_per_mol": -60.0,
            },
        ),
        "predict_rna_secondary_structure_with_linearfold": _StubCapability(
            "predict_rna_secondary_structure_with_linearfold",
            {
                "structure": "." * 300,
                "mfe": -55.0,
            },
        ),
        "compute_rna_sequence_gc_content": _StubCapability(
            "compute_rna_sequence_gc_content",
            {"gc_content": 0.5, "sequence_length": 300},
        ),
        "compute_dot_bracket_unpaired_fraction": _StubCapability(
            "compute_dot_bracket_unpaired_fraction",
            {"unpaired_fraction": 0.5, "structure_length": 300, "dot_count": 150},
        ),
        "predict_mrna_stability_with_rnastop": _StubCapability(
            "predict_mrna_stability_with_rnastop",
            {"overall_stability": 0.5},
        ),
        "compute_cai_for_cds_sequence": _StubCapability(
            "compute_cai_for_cds_sequence",
            {"cai_score": 0.85, "species": "Homo sapiens"},
        ),
        # UTR design tools
        "design_5utr_with_gemorna": _StubCapability(
            "design_5utr_with_gemorna",
            {"generated_sequence": "AUGC" * 15},  # 60 nt
        ),
        "design_3utr_with_gemorna": _StubCapability(
            "design_3utr_with_gemorna",
            {"generated_sequence": "AUGC" * 15},  # 60 nt
        ),
        # UTR prediction tools
        "predict_5utr_mrl_with_gemorna": _StubCapability(
            "predict_5utr_mrl_with_gemorna",
            {"predicted_mrl": 5.0},
        ),
        "predict_3utr_stability_with_gemorna": _StubCapability(
            "predict_3utr_stability_with_gemorna",
            {"predicted_stability": 0.8},
        ),
        # IRES prediction (configurable score for critic testing)
        "predict_putative_ires_with_iresfinder": _StubCapability(
            "predict_putative_ires_with_iresfinder",
            {"max_score": ires_score},
        ),
    }
    return _StubRegistry(caps)


def _build_pipeline_agent(
    ires_score: float = 0.1,
    quality_llm: Any | None = None,
) -> tuple[PipelineAgent, FullLengthMrnaDesignWorkflow]:
    """Build a PipelineAgent wired for full_length_mrna_design."""
    registry = _build_full_registry(ires_score=ires_score)
    workflow = FullLengthMrnaDesignWorkflow(registry)
    specialist = SpecialistAgent(workflow, FULL_LENGTH_MRNA_QUALITY_PROFILE)
    quality_agent = QualityAgent(llm=quality_llm)
    synthesis_agent = SynthesisAgent(enable_llm=False)
    pipeline_agent = PipelineAgent(
        specialist_registry={"full_length_mrna_design": specialist},
        quality_agent=quality_agent,
        synthesis_agent=synthesis_agent,
    )
    return pipeline_agent, workflow


def test_full_length_mrna_design_via_pipeline_agent():
    """FullLengthMrnaDesignWorkflow executes end-to-end through PipelineAgent."""
    pipeline_agent, _workflow = _build_pipeline_agent(ires_score=0.1)

    plan = PipelinePlan.single(
        workflow="full_length_mrna_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "utr_mode": "short",
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline_agent.execute(plan, state)

    assert isinstance(result, PipelineResult)
    assert result.success is True
    assert "n1" in result.node_results

    node_result = result.node_results["n1"]
    wf_result = node_result.workflow_result
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True
    assert len(wf_result.all_candidates) > 0
    assert wf_result.best_candidate is not None

    # Full-length candidates should contain UTR and CDS metadata
    best = wf_result.best_candidate
    assert best is not None
    assert "utr5_sequence" in best.metadata
    assert "cds_sequence" in best.metadata
    assert "utr3_sequence" in best.metadata

    # No critic retry when disabled
    assert node_result.metadata.get("retry_count", 0) == 0


def test_full_length_mrna_design_progress_callback():
    """Progress callback receives workflow events from the full-length run."""
    pipeline_agent, _workflow = _build_pipeline_agent(ires_score=0.1)

    plan = PipelinePlan.single(
        workflow="full_length_mrna_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "utr_mode": "short",
        },
    )

    events: list[dict[str, Any]] = []

    def _cb(evt: dict[str, Any]) -> None:
        events.append(evt)

    pipeline_agent.execute(plan, {"_quality_review_enabled": False}, progress_callback=_cb)

    assert any(e.get("event") == "generate_complete" for e in events)
    assert any(e.get("event") == "evaluate_progress" for e in events)


def test_quality_agent_disabled_returns_pass():
    """QualityAgent returns a pass report when LLM critic is disabled."""
    pipeline_agent, _workflow = _build_pipeline_agent(ires_score=0.8)
    plan = PipelinePlan.single(
        workflow="full_length_mrna_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "utr_mode": "short",
        },
    )

    state: dict[str, Any] = {"_quality_review_enabled": False}
    result = pipeline_agent.execute(plan, state)

    assert result.success is True
    node_result = result.node_results["n1"]
    report = node_result.metadata.get("quality_report")
    assert report is not None
    assert report.action == "pass"
    assert node_result.metadata.get("retry_count", 0) == 0


def test_quality_agent_builds_full_length_context():
    """FULL_LENGTH_MRNA_QUALITY_PROFILE builds the full-length context correctly."""
    pipeline_agent, _workflow = _build_pipeline_agent(ires_score=0.1)
    plan = PipelinePlan.single(
        workflow="full_length_mrna_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "utr_mode": "short",
        },
    )

    state: dict[str, Any] = {
        "user_text": "Design a stable mRNA with short UTRs",
        "_quality_review_enabled": False,
    }
    result = pipeline_agent.execute(plan, state)

    wf_result = result.node_results["n1"].workflow_result
    assert isinstance(wf_result, WorkflowResult)
    assert wf_result.success is True

    # Verify profile-specific context builder populates full-length stats
    ctx = FULL_LENGTH_MRNA_QUALITY_PROFILE.build_context(wf_result, state)
    assert "full_length_stats" in ctx
    stats = ctx["full_length_stats"]
    assert "utr5_preset_distribution" in stats
    assert "utr3_preset_distribution" in stats
    assert "cds_source_distribution" in stats
    assert "utr5_mrl_range" in stats
    assert "utr3_stability_range" in stats

    # Best candidate breakdown should exist since we have candidates
    best_breakdown = ctx.get("best_candidate_breakdown")
    assert best_breakdown is not None
    assert best_breakdown.get("utr5_preset") == "short"
    assert best_breakdown.get("utr3_preset") == "short"


def test_quality_agent_review_with_mocked_llm():
    """QualityAgent can review a full-length result with a deterministic mocked LLM."""
    pipeline_agent, _workflow = _build_pipeline_agent(ires_score=0.1)
    plan = PipelinePlan.single(
        workflow="full_length_mrna_design",
        static_params={
            "protein_sequence": "MKTAIVE",
            "design_tool": "lineardesign",
            "lambda_value": 0.0,
            "utr_mode": "short",
        },
    )

    # Run with critic disabled just to obtain a real WorkflowResult.
    state: dict[str, Any] = {"_quality_review_enabled": False}
    pipeline_result = pipeline_agent.execute(plan, state)
    wf_result = pipeline_result.node_results["n1"].workflow_result
    assert isinstance(wf_result, WorkflowResult)

    mock_llm = _MockLLM(_pass_report_json())
    quality_agent = QualityAgent(llm=mock_llm)
    review_state = {"user_text": "Design a stable mRNA", "_quality_review_enabled": True}
    report = quality_agent.review(
        wf_result,
        FULL_LENGTH_MRNA_QUALITY_PROFILE,
        review_state,
    )

    assert report.action == "pass"
    assert report.quality_score == 1.0
    # The prompt should have been constructed and sent to the mocked LLM.
    assert len(mock_llm.last_messages) == 2
    roles = [role for role, _ in mock_llm.last_messages]
    assert "system" in roles
    assert "user" in roles
