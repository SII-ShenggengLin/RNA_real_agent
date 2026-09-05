"""End-to-end integration tests for full_length_mrna_design.

These tests exercise the complete stack:
  Layer 3: QualityAgent (quality review; mocked in most tests below)
  Layer 3: PipelineAgent / SpecialistAgent (multi-agent execution)
  Layer 2: FullLengthMrnaDesignWorkflow (generation + evaluation + ranking)
  Layer 1: Stub capabilities (fast, deterministic)
  Layer 0: File manager, state management
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agent_core.agents import (
    PipelineAgent,
    QualityAgent,
    QualityReport,
    SpecialistAgent,
    SynthesisAgent,
)
from agent_core.capabilities.base import CapabilityResult
from agent_core.pipeline.models import PipelinePlan
from agent_core.quality_profiles.full_length_mrna_design import (
    FULL_LENGTH_MRNA_QUALITY_PROFILE,
)
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
)

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _make_stub_capability(cap_name: str, output: dict[str, Any]) -> Any:
    """Minimal capability stub."""
    class StubCap:
        _cap_name = cap_name

        @property
        def name(self) -> str:
            return self._cap_name

        def invoke(self, tool_args: dict[str, Any], state: dict[str, Any] | None = None) -> CapabilityResult:
            return CapabilityResult(
                success=True,
                tool_name=cap_name,
                output=dict(output),
            )
    return StubCap()


def _build_stub_registry(
    *,
    ires_score: float = 0.1,
    mrl: float = 6.0,
    utr3_stab: float = 0.75,
    full_mfe: float = -30.0,
) -> Any:
    """Build a deterministic stub registry for fast integration tests."""
    utr5_seqs = {"short": "GGGAAA", "medium": "GGGAAACCCUUU", "long": "GGGAAACCCUUUGGGAAA"}
    utr3_seqs = {"short": "AAAUUU", "medium": "AAAUUUGGGCCC", "long": "AAAUUUGGGCCCUUUAAA"}

    def _utr_invoke(utr_type: str):
        def fn(args: dict[str, Any], state: dict[str, Any] | None = None) -> CapabilityResult:
            preset = args.get("utr_length", "medium")
            seqs = utr5_seqs if utr_type == "5utr" else utr3_seqs
            return CapabilityResult(
                success=True,
                tool_name=f"design_{utr_type}_with_gemorna",
                output={"generated_sequence": seqs.get(preset, "GGGAAA")},
            )
        return fn

    caps = {
        # CDS tools
        "design_mrna_cds_with_lineardesign": _make_stub_capability(
            "design_mrna_cds_with_lineardesign",
            {"generated_sequence": "AUG" * 40, "mfe": -50.0, "cai_score": 0.8},
        ),
        "design_mrna_cds_with_rnarl": _make_stub_capability(
            "design_mrna_cds_with_rnarl",
            {"generated_sequence": "AUG" * 35},
        ),
        "design_mrna_cds_with_gemorna": _make_stub_capability(
            "design_mrna_cds_with_gemorna",
            {"generated_sequence": "AUG" * 42},
        ),
        # UTR design
        "design_5utr_with_gemorna": _make_stub_capability("design_5utr_with_gemorna", {}),
        "design_3utr_with_gemorna": _make_stub_capability("design_3utr_with_gemorna", {}),
        # Folding
        "predict_rna_secondary_structure": _make_stub_capability(
            "predict_rna_secondary_structure",
            {"mfe_kcal_per_mol": full_mfe, "structure": "." * 300},
        ),
        "predict_rna_secondary_structure_with_linearfold": _make_stub_capability(
            "predict_rna_secondary_structure_with_linearfold",
            {"mfe": full_mfe + 5, "structure": "." * 300},
        ),
        # Eval
        "compute_rna_sequence_gc_content": _make_stub_capability(
            "compute_rna_sequence_gc_content",
            {"gc_content": 0.52, "sequence_length": 300},
        ),
        "compute_cai_for_cds_sequence": _make_stub_capability(
            "compute_cai_for_cds_sequence",
            {"cai_score": 0.85, "species": "Homo sapiens"},
        ),
        "predict_mrna_stability_with_rnastop": _make_stub_capability(
            "predict_mrna_stability_with_rnastop",
            {"overall_stability": 0.65},
        ),
        # UTR-specific
        "predict_5utr_mrl_with_gemorna": _make_stub_capability(
            "predict_5utr_mrl_with_gemorna",
            {"predicted_mrl": mrl},
        ),
        "predict_3utr_stability_with_gemorna": _make_stub_capability(
            "predict_3utr_stability_with_gemorna",
            {"predicted_stability": utr3_stab},
        ),
        # IRES
        "predict_putative_ires_with_iresfinder": _make_stub_capability(
            "predict_putative_ires_with_iresfinder",
            {"max_score": ires_score, "has_putative_ires": ires_score > 0.5},
        ),
    }

    # Wire UTR invokers
    caps["design_5utr_with_gemorna"].invoke = _utr_invoke("5utr")
    caps["design_3utr_with_gemorna"].invoke = _utr_invoke("3utr")

    class StubRegistry:
        def has(self, name: str) -> bool:
            return name in caps

        def get(self, name: str) -> Any:
            return caps[name]

        def list_names(self) -> list[str]:
            return sorted(caps.keys())

    return StubRegistry()


def _make_candidates_with_metrics(
    presets: list[tuple[str, str]],
    ires_scores: list[float] | None = None,
    mrl_values: list[float] | None = None,
    utr3_stab_values: list[float] | None = None,
    cds_cai: float = 0.85,
) -> list[Candidate]:
    """Build candidates with specified UTR presets and metrics."""
    cands: list[Candidate] = []
    ires_scores = ires_scores or [0.1] * len(presets)
    mrl_values = mrl_values or [6.0] * len(presets)
    utr3_stab_values = utr3_stab_values or [0.75] * len(presets)

    utr5_lens = {"short": 6, "medium": 12, "long": 18}
    utr3_lens = {"short": 6, "medium": 12, "long": 18}
    utr5_seqs = {"short": "GGGAAA", "medium": "GGGAAACCCUUU", "long": "GGGAAACCCUUUGGGAAA"}
    utr3_seqs = {"short": "AAAUUU", "medium": "AAAUUUGGGCCC", "long": "AAAUUUGGGCCCUUUAAA"}

    for i, (p5, p3) in enumerate(presets):
        cds_seq = "AUG" * 40
        full_seq = utr5_seqs[p5] + cds_seq + utr3_seqs[p3]
        c = Candidate(
            sequence=full_seq,
            sequence_type="mrna",
            source=f"test:utr5_{p5}:utr3_{p3}",
            metadata={
                "utr5_sequence": utr5_seqs[p5],
                "cds_sequence": cds_seq,
                "utr3_sequence": utr3_seqs[p3],
                "utr5_preset": p5,
                "utr3_preset": p3,
                "utr5_length": utr5_lens[p5],
                "utr3_length": utr3_lens[p3],
                "cds_length": len(cds_seq),
                "cds_source": "lineardesign",
                "protein_sequence": "MKTAIVE",
                "metrics_bundle": {
                    "cds_cai": cds_cai,
                    "cds_mfe": -50.0,
                    "cds_gc": 0.52,
                    "cds_length": len(cds_seq),
                    "utr5_predicted_mrl": mrl_values[i],
                    "utr3_predicted_stability": utr3_stab_values[i],
                    "utr5_ires_potential": ires_scores[i],
                    "full_length_mfe": -30.0,
                    "total_length": len(full_seq),
                    "overall_stability": 0.65,
                },
            },
        )
        c.scores = {
            "cds_component": cds_cai,
            "utr5_mrl": mrl_values[i],
            "utr3_stability": utr3_stab_values[i],
        }
        cands.append(c)
    return cands


# ═══════════════════════════════════════════════════════════════════════
# Layer 3 — QualityAgent: structured diagnosis (mocked LLM)
# ═══════════════════════════════════════════════════════════════════════


class TestQualityAgent:
    """Test QualityAgent for full_length_mrna_design with a mocked LLM."""

    @staticmethod
    def _mock_llm(*responses: str) -> Any:
        """Return a mock LLM that cycles through the supplied response strings."""
        class _MockLLM:
            def __init__(self, replies: tuple[str, ...]) -> None:
                self._replies = list(replies)
                self._idx = 0

            def invoke(self, messages: Any) -> Any:
                reply = self._replies[self._idx]
                if self._idx < len(self._replies) - 1:
                    self._idx += 1
                return type("MockResponse", (), {"content": reply})()
        return _MockLLM(responses)

    @staticmethod
    def _report_json(**kwargs: Any) -> str:
        """Build a valid QualityReport JSON string for mocking."""
        report = {
            "overall_assessment": kwargs.get("overall_assessment", "mock assessment"),
            "quality_score": kwargs.get("quality_score", 0.9),
            "issues": kwargs.get("issues", []),
            "action": kwargs.get("action", "pass"),
            "parameter_overrides": kwargs.get("parameter_overrides", {}),
            "reasoning": kwargs.get("reasoning", "mock reasoning"),
            "confidence": kwargs.get("confidence", 0.9),
        }
        return json.dumps(report)

    def test_quality_agent_diagnoses_high_ires(self):
        """High IRES candidates should produce a QualityReport with retry advice."""
        cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("medium", "medium"), ("long", "long")],
            ires_scores=[0.85, 0.90, 0.88],
            mrl_values=[6.0, 6.5, 7.0],
        )
        result = WorkflowResult(
            success=True,
            task_id="test_ires",
            best_candidate=cands[0],
            all_candidates=cands,
            summary="test",
            errors=[],
        )
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design standard mRNA for MKTAIVE",
        }

        report_json = self._report_json(
            quality_score=0.65,
            issues=[{
                "severity": "warning",
                "category": "IRES potential",
                "description": "High IRES scores may conflict with cap-dependent expression intent.",
                "metric_value": 0.88,
                "threshold": 0.5,
            }],
            action="retry_with_adjustments",
            parameter_overrides={"utr_mode": "short"},
        )
        qa = QualityAgent(llm=self._mock_llm(report_json))
        diagnosis = qa.review(result, FULL_LENGTH_MRNA_QUALITY_PROFILE, state)

        assert isinstance(diagnosis, QualityReport)
        assert diagnosis.quality_score <= 0.85
        assert len(diagnosis.issues) > 0
        assert diagnosis.action in ("retry_with_adjustments", "retry_with_alternative", "abort", "pass")

    def test_quality_agent_respects_user_ires_intent(self):
        """When the user wants IRES, a mocked pass report is returned unchanged."""
        cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("short", "short")],
            ires_scores=[0.85, 0.90],
        )
        result = WorkflowResult(
            success=True,
            task_id="test_ires_desired",
            best_candidate=cands[0],
            all_candidates=cands,
            summary="test",
            errors=[],
        )
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design IRES-driven mRNA for MKTAIVE with strong IRES in 5'UTR",
        }

        report_json = self._report_json(
            quality_score=0.95,
            issues=[],
            action="pass",
        )
        qa = QualityAgent(llm=self._mock_llm(report_json))
        diagnosis = qa.review(result, FULL_LENGTH_MRNA_QUALITY_PROFILE, state)

        assert isinstance(diagnosis, QualityReport)
        assert diagnosis.action == "pass"


# ═══════════════════════════════════════════════════════════════════════
# Layer 3 — Full retry flow: PipelineAgent + SpecialistAgent
# ═══════════════════════════════════════════════════════════════════════


class TestFullRetryFlow:
    """End-to-end: PipelineAgent drives full_length_mrna_design with mocked QualityAgent."""

    @staticmethod
    def _mock_llm(*responses: str) -> Any:
        class _MockLLM:
            def __init__(self, replies: tuple[str, ...]) -> None:
                self._replies = list(replies)
                self._idx = 0

            def invoke(self, messages: Any) -> Any:
                reply = self._replies[self._idx]
                if self._idx < len(self._replies) - 1:
                    self._idx += 1
                return type("MockResponse", (), {"content": reply})()
        return _MockLLM(responses)

    @staticmethod
    def _report_json(**kwargs: Any) -> str:
        report = {
            "overall_assessment": kwargs.get("overall_assessment", "mock assessment"),
            "quality_score": kwargs.get("quality_score", 0.9),
            "issues": kwargs.get("issues", []),
            "action": kwargs.get("action", "pass"),
            "parameter_overrides": kwargs.get("parameter_overrides", {}),
            "reasoning": kwargs.get("reasoning", "mock reasoning"),
            "confidence": kwargs.get("confidence", 0.9),
        }
        return json.dumps(report)

    def _build_pipeline(self, mock_llm: Any) -> PipelineAgent:
        """Assemble a PipelineAgent for full_length_mrna_design."""
        registry = _build_stub_registry(ires_score=0.1)
        workflow = FullLengthMrnaDesignWorkflow(registry)
        specialist = SpecialistAgent(workflow, FULL_LENGTH_MRNA_QUALITY_PROFILE)
        quality_agent = QualityAgent(llm=mock_llm)
        synthesis_agent = SynthesisAgent(enable_llm=False)
        return PipelineAgent(
            specialist_registry={"full_length_mrna_design": specialist},
            quality_agent=quality_agent,
            synthesis_agent=synthesis_agent,
        )

    def test_pipeline_runs_full_length_workflow(self):
        """PipelineAgent executes the workflow and returns a successful result."""
        report_json = self._report_json(action="pass", quality_score=0.95)
        pipeline_agent = self._build_pipeline(self._mock_llm(report_json))

        plan = PipelinePlan.single(
            workflow="full_length_mrna_design",
            static_params={
                "protein_sequence": "MKTAIVE",
                "design_tool": "lineardesign",
                "lambda_value": 0.0,
            },
            output_alias="result",
        )
        state = {"user_text": "Design full-length mRNA for MKTAIVE"}

        result = pipeline_agent.execute(plan, state)

        assert result.success is True
        assert "n1" in result.node_results
        agent_result = result.node_results["n1"]
        assert agent_result.success is True
        wf_result = agent_result.workflow_result
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True
        assert len(wf_result.all_candidates) > 0

        for c in wf_result.all_candidates:
            assert "utr5_sequence" in c.metadata
            assert "cds_sequence" in c.metadata
            assert "utr3_sequence" in c.metadata

    def test_pipeline_retries_on_quality_feedback(self):
        """QualityAgent recommends retry → SpecialistAgent reruns with adjusted params."""
        report_json_retry = self._report_json(
            action="retry_with_adjustments",
            quality_score=0.6,
            issues=[{
                "severity": "warning",
                "category": "UTR length diversity",
                "description": "User requested compact mRNA; recommend short UTR presets.",
            }],
            parameter_overrides={"utr_mode": "short"},
        )
        report_json_pass = self._report_json(action="pass", quality_score=0.95)
        pipeline_agent = self._build_pipeline(self._mock_llm(report_json_retry, report_json_pass))

        plan = PipelinePlan.single(
            workflow="full_length_mrna_design",
            static_params={
                "protein_sequence": "MKTAIVE",
                "design_tool": "lineardesign",
                "lambda_value": 0.0,
            },
            output_alias="result",
        )
        state = {
            "user_text": "Design compact full-length mRNA for MKTAIVE",
            "_quality_auto_retry": True,
        }

        result = pipeline_agent.execute(plan, state)

        assert result.success is True
        agent_result = result.node_results["n1"]
        assert agent_result.success is True
        assert agent_result.metadata.get("retry_count", 0) > 0
        wf_result = agent_result.workflow_result
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True
        assert len(wf_result.all_candidates) > 0


# ═══════════════════════════════════════════════════════════════════════
# Layer 2 — Workflow: generation + evaluation + ranking
# ═══════════════════════════════════════════════════════════════════════


class TestLayer2Workflow:
    """Test FullLengthMrnaDesignWorkflow with stub capabilities (fast, no LLM)."""

    def test_workflow_generates_candidates_with_all_utr_presets(self):
        """utr_mode='all' should produce candidates with short/medium/long UTRs
        (static recipe path — navigation=False; the default recipe navigates)."""
        registry = _build_stub_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(
            protein_sequence="MKTAIVE", design_tool="all", utr_mode="all",
            navigation=False,
        )
        cands = wf.generate_candidates(inp)
        assert len(cands) > 0

        # Should have diverse UTR presets
        utr5_presets = {c.metadata.get("utr5_preset") for c in cands}
        utr3_presets = {c.metadata.get("utr3_preset") for c in cands}
        assert "short" in utr5_presets
        assert "long" in utr5_presets
        assert "short" in utr3_presets
        assert "long" in utr3_presets

    def test_workflow_evaluates_full_length_metrics(self):
        """evaluate() should compute full-length and UTR-specific metrics."""
        registry = _build_stub_registry(mrl=5.5, utr3_stab=0.8, ires_score=0.2)
        wf = FullLengthMrnaDesignWorkflow(registry)
        c = Candidate(
            sequence="GGGAAACCCUUUAUG" * 10 + "AAAUUU",
            metadata={
                "utr5_sequence": "GGGAAACCCUUU",
                "cds_sequence": "AUG" * 40,
                "utr3_sequence": "AAAUUU",
                "utr5_preset": "short",
                "utr3_preset": "short",
            },
        )
        metrics = wf.evaluate(c)
        assert "full_length_mfe" in metrics
        assert "utr5_predicted_mrl" in metrics
        assert "utr3_predicted_stability" in metrics
        assert "utr5_ires_potential" in metrics
        assert "overall_stability" in metrics
        assert metrics["utr5_predicted_mrl"] == 5.5
        assert metrics["utr3_predicted_stability"] == 0.8

    def test_workflow_ranking_produces_valid_asf(self):
        """rank_and_format should produce ASF-based rankings."""
        registry = _build_stub_registry(mrl=6.0, utr3_stab=0.75)
        wf = FullLengthMrnaDesignWorkflow(registry)
        cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("medium", "medium"), ("long", "long")],
        )
        for c in cands:
            c.scores = wf.score(c.metadata["metrics_bundle"])
        result = wf.rank_and_format(cands)
        assert result.success is True
        assert len(result.all_candidates) == 3
        assert result.best_candidate is not None
        # All candidates should have an ASF distance and a rank.
        for c in result.all_candidates:
            assert "asf_distance" in c.scores
            assert c.rank is not None

    def test_workflow_run_full_pipeline(self):
        """run() should execute the complete pipeline end-to-end
        (static recipe path — navigation=False)."""
        registry = _build_stub_registry(mrl=6.5, utr3_stab=0.8, ires_score=0.1)
        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(
            protein_sequence="MKTAIVE",
            design_tool="all",
            utr_mode="short",
            navigation=False,
        )
        result = wf.run(inp)
        assert result.success is True
        assert result.best_candidate is not None
        assert len(result.all_candidates) > 0
        # Summary should contain key info
        assert "short" in result.summary or "total_len" in result.summary


# ═══════════════════════════════════════════════════════════════════════
# Layer 0/1 — File manager + capabilities
# ═══════════════════════════════════════════════════════════════════════


class TestLayer0And1:
    """Smoke tests for Layer 0 (infra) and Layer 1 (capabilities)."""

    def test_file_manager_save_sequence(self):
        """Layer 0: save_sequence should write to workspace."""
        from pathlib import Path
        from agent_core.file_manager import save_sequence
        fp = Path(save_sequence("AUGCCC", prefix="test_layer0"))
        assert fp.exists()
        content = fp.read_text()
        assert "AUGCCC" in content

    def test_stub_registry_lists_capabilities(self):
        """Layer 1: Stub registry lists its capabilities correctly."""
        registry = _build_stub_registry()
        names = registry.list_names()
        assert len(names) > 0
        assert "design_mrna_cds_with_lineardesign" in names
        assert "design_5utr_with_gemorna" in names
        assert "predict_5utr_mrl_with_gemorna" in names

    def test_stub_capability_invoke(self):
        """Layer 1: Stub capability returns deterministic CapabilityResult."""
        cap = _make_stub_capability("test_cap", {"result": 42})
        result = cap.invoke({"x": 1})
        assert result.success is True
        assert result.output["result"] == 42
        assert result.tool_name == "test_cap"
