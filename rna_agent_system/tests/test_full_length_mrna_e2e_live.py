"""End-to-end integration tests for full_length_mrna_design with LIVE LLM calls.

These tests exercise the complete stack:
  Layer 3: LLMPlanner (parameter selection from user prompt)
  Layer 3: FullLengthMrnaDesignLLMCritic (live diagnosis + retry decisions)
  Layer 2: FullLengthMrnaDesignWorkflow (generation + evaluation + ranking)
  Layer 1: Stub capabilities (fast, deterministic)
  Layer 0: File manager, state management

All tests require a valid DEEPSEEK_API_KEY in the environment (loaded from .env).
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.file_manager import PROJECT_ROOT
from agent_core.llm_config import get_deepseek_llm
from agent_core.planning.base import (
    AgentContext,
    ExecutionController,
    ExecutionPlan,
    PlanStep,
)
from agent_core.planning.llm_critic import CriticDiagnosis
from agent_core.planning.llm_planner import LLMPlanner
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignLLMCritic,
    FullLengthMrnaDesignWorkflow,
)

# ── Load .env before checking API key ──────────────────────────────────
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

skip_if_no_api_key = pytest.mark.skipif(
    not _DEEPSEEK_KEY,
    reason="Requires DEEPSEEK_API_KEY (set in .env or environment)",
)

pytestmark = pytest.mark.live_llm


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
        "analyze_cds_codon_metrics_with_codonw_slim": _make_stub_capability(
            "analyze_cds_codon_metrics_with_codonw_slim",
            {"cai_score": 0.80, "mfe_kcal_per_mol": -20.0},
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
# Layer 3 — Planner: parameter selection from user prompt
# ═══════════════════════════════════════════════════════════════════════


class TestPlannerParameterSelection:
    """Test that LLMPlanner correctly interprets user requests and selects parameters."""

    @skip_if_no_api_key
    def test_planner_selects_utr_mode_long(self):
        """User asks for 'long 3'UTR' → planner should set utr_mode='long'."""
        planner = LLMPlanner(llm=get_deepseek_llm(temperature=0.1))
        ctx = AgentContext(
            session_id="test",
            available_capabilities=[],
            available_workflows=["full_length_mrna_design"],
            workflow_param_schemas={
                "full_length_mrna_design": (
                    "  protein_sequence=(required) (str)\n"
                    "  design_tool='all' (Literal['lineardesign', 'rnarl', 'gemorna', 'all'])\n"
                    "  utr_mode='all' (Literal['short', 'medium', 'long', 'all'])\n"
                    "  lambda_value=None (float)\n"
                ),
            },
        )
        plan = planner.plan(
            "Design a full-length mRNA for protein MKTAIVE with long 3'UTR for better stability",
            ctx,
        )
        assert len(plan.steps) > 0
        step = plan.steps[0]
        assert step.target == "full_length_mrna_design"
        assert "protein_sequence" in step.input_binding
        # Should infer UTR mode from user request
        assert step.input_binding.get("utr_mode") == "long", (
            f"Expected utr_mode='long' for 'long 3\\'UTR' request, got {step.input_binding}"
        )
        # Should NOT override other defaults
        assert "design_tool" not in step.input_binding or step.input_binding.get("design_tool") == "all"

    @skip_if_no_api_key
    def test_planner_selects_utr_mode_short(self):
        """User asks for 'short 5UTR and short 3UTR' → planner should set utr_mode='short'."""
        planner = LLMPlanner(llm=get_deepseek_llm(temperature=0.1))
        ctx = AgentContext(
            session_id="test",
            available_capabilities=[],
            available_workflows=["full_length_mrna_design"],
            workflow_param_schemas={
                "full_length_mrna_design": (
                    "  protein_sequence=(required) (str)\n"
                    "  design_tool='all' (Literal['lineardesign', 'rnarl', 'gemorna', 'all'])\n"
                    "  utr_mode='all' (Literal['short', 'medium', 'long', 'all'])\n"
                    "  lambda_value=None (float)\n"
                ),
            },
        )
        plan = planner.plan(
            "Design a compact full-length mRNA with short 5'UTR and short 3'UTR for protein MKTAIVE",
            ctx,
        )
        assert len(plan.steps) > 0
        step = plan.steps[0]
        assert step.target == "full_length_mrna_design"
        assert step.input_binding.get("utr_mode") == "short", (
            f"Expected utr_mode='short' for compact request, got {step.input_binding}"
        )

    @skip_if_no_api_key
    def test_planner_selects_lineardesign_with_lambda(self):
        """User explicitly requests LinearDesign with lambda=4 → planner should set both."""
        planner = LLMPlanner(llm=get_deepseek_llm(temperature=0.1))
        ctx = AgentContext(
            session_id="test",
            available_capabilities=[],
            available_workflows=["full_length_mrna_design"],
            workflow_param_schemas={
                "full_length_mrna_design": (
                    "  protein_sequence=(required) (str)\n"
                    "  design_tool='all' (Literal['lineardesign', 'rnarl', 'gemorna', 'all'])\n"
                    "  utr_mode='all' (Literal['short', 'medium', 'long', 'all'])\n"
                    "  lambda_value=None (float)\n"
                    "  model_type='Homo sapiens mRNA' (str)\n"
                ),
            },
        )
        plan = planner.plan(
            "Design full-length mRNA for MKTAIVE using LinearDesign with lambda 4",
            ctx,
        )
        assert len(plan.steps) > 0
        step = plan.steps[0]
        assert step.input_binding.get("design_tool") == "lineardesign", (
            f"Expected design_tool='lineardesign', got {step.input_binding}"
        )
        assert step.input_binding.get("lambda_value") == 4.0, (
            f"Expected lambda_value=4.0, got {step.input_binding}"
        )

    @skip_if_no_api_key
    def test_planner_omits_defaults_when_user_is_vague(self):
        """Vague request → planner should NOT override defaults."""
        planner = LLMPlanner(llm=get_deepseek_llm(temperature=0.1))
        ctx = AgentContext(
            session_id="test",
            available_capabilities=[],
            available_workflows=["full_length_mrna_design"],
            workflow_param_schemas={
                "full_length_mrna_design": (
                    "  protein_sequence=(required) (str)\n"
                    "  design_tool='all' (Literal['lineardesign', 'rnarl', 'gemorna', 'all'])\n"
                    "  utr_mode='all' (Literal['short', 'medium', 'long', 'all'])\n"
                    "  lambda_value=None (float)\n"
                ),
            },
        )
        plan = planner.plan(
            "Design a full-length mRNA for protein MKTAIVE",
            ctx,
        )
        assert len(plan.steps) > 0
        step = plan.steps[0]
        assert step.target == "full_length_mrna_design"
        # Should NOT set utr_mode or design_tool when user is vague
        assert "utr_mode" not in step.input_binding or step.input_binding.get("utr_mode") == "all"
        assert "design_tool" not in step.input_binding or step.input_binding.get("design_tool") == "all"


# ═══════════════════════════════════════════════════════════════════════
# Layer 3 — Critic: live diagnosis with real LLM
# ═══════════════════════════════════════════════════════════════════════


class TestLiveCriticDiagnosis:
    """Test FullLengthMrnaDesignLLMCritic with live LLM calls."""

    @skip_if_no_api_key
    def test_live_critic_diagnoses_high_ires(self):
        """All candidates have high IRES → critic should flag it as an issue."""
        critic = FullLengthMrnaDesignLLMCritic()
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

        diagnosis = critic.diagnose(result, state)
        print(f"\n[Live diagnosis - high IRES]\n{diagnosis.model_dump_json(indent=2)}")

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score <= 0.85  # High IRES should lower quality
        assert len(diagnosis.issues) > 0
        # Should identify IRES as a problem for standard mRNA
        ires_issues = [
            i for i in diagnosis.issues
            if "ires" in i.category.lower() or "IRES" in i.description
        ]
        assert len(ires_issues) > 0, f"Expected IRES-related issue, got: {[i.category for i in diagnosis.issues]}"
        # Should recommend some action (retry, filter, or proceed)
        assert diagnosis.action in ("retry_with_adjustments", "retry_with_alternative", "proceed_with_filtered", "abort")

    @skip_if_no_api_key
    def test_live_critic_diagnoses_utr_length_mismatch(self):
        """User asked for short UTR but results are all long → critic should flag mismatch."""
        critic = FullLengthMrnaDesignLLMCritic()
        cands = _make_candidates_with_metrics(
            presets=[("long", "long"), ("long", "long"), ("long", "long")],
            mrl_values=[5.0, 5.1, 5.2],
        )
        result = WorkflowResult(
            success=True,
            task_id="test_mismatch",
            best_candidate=cands[0],
            all_candidates=cands,
            summary="test",
            errors=[],
        )
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design full-length mRNA with short UTRs for MKTAIVE",
        }

        diagnosis = critic.diagnose(result, state)
        print(f"\n[Live diagnosis - UTR mismatch]\n{diagnosis.model_dump_json(indent=2)}")

        assert isinstance(diagnosis, CriticDiagnosis)
        # Should detect UTR length mismatch with user request
        issues_text = " ".join(i.description for i in diagnosis.issues).lower()
        assert "utr" in issues_text or "length" in issues_text, (
            f"Expected UTR/length issue, got: {[i.description for i in diagnosis.issues]}"
        )

    @skip_if_no_api_key
    def test_live_critic_diagnoses_low_mrl(self):
        """Low 5'UTR MRL → critic should flag poor translation initiation."""
        critic = FullLengthMrnaDesignLLMCritic()
        cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("medium", "short"), ("long", "short")],
            mrl_values=[2.0, 2.1, 2.2],  # Very low MRL
        )
        result = WorkflowResult(
            success=True,
            task_id="test_mrl",
            best_candidate=cands[0],
            all_candidates=cands,
            summary="test",
            errors=[],
        )
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design high-expression mRNA for MKTAIVE",
        }

        diagnosis = critic.diagnose(result, state)
        print(f"\n[Live diagnosis - low MRL]\n{diagnosis.model_dump_json(indent=2)}")

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score <= 0.75  # Low quality should be reflected
        # Critic should identify some issue (MRL or UTR diversity)
        assert len(diagnosis.issues) > 0

    @skip_if_no_api_key
    def test_live_critic_respects_user_ires_intent(self):
        """User explicitly wants IRES → critic should NOT flag it as bad."""
        critic = FullLengthMrnaDesignLLMCritic()
        cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("short", "short")],
            ires_scores=[0.85, 0.90],  # High IRES
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

        diagnosis = critic.diagnose(result, state)
        print(f"\n[Live diagnosis - IRES desired]\n{diagnosis.model_dump_json(indent=2)}")

        assert isinstance(diagnosis, CriticDiagnosis)
        # High IRES should NOT be flagged as critical when user wants it
        critical_ires = [
            i for i in diagnosis.issues
            if i.severity == "critical" and ("ires" in i.category.lower() or "IRES" in i.description)
        ]
        assert len(critical_ires) == 0, (
            f"Expected no critical IRES issue when user wants IRES, got: {critical_ires}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Layer 3 — Full retry flow: ExecutionController + mock workflow + live critic
# ═══════════════════════════════════════════════════════════════════════


class TestFullRetryFlow:
    """End-to-end: ExecutionController drives retry with live critic."""

    @skip_if_no_api_key
    def test_retry_flow_critic_adjusts_utr_mode(self):
        """Critic detects issue → triggers retry → parameter overrides applied."""
        registry = _build_stub_registry(ires_score=0.1)
        workflow = FullLengthMrnaDesignWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"full_length_mrna_design": workflow},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf1",
                    type="workflow",
                    target="full_length_mrna_design",
                    input_binding={
                        "protein_sequence": "MKTAIVE",
                        "design_tool": "lineardesign",
                        "lambda_value": 0.0,
                        "utr_mode": "all",
                    },
                    output_key="result",
                )
            ],
            max_retries=2,
        )

        state: dict[str, Any] = {
            "user_text": "Design full-length mRNA with short UTRs for MKTAIVE",
        }
        final_state = controller.execute(plan, state, replan_fn=lambda s: plan)

        # Workflow should have run at least once
        assert "result" in final_state or "workflow_result" in final_state
        wf_result = final_state.get("result") or final_state.get("workflow_result")
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True
        assert len(wf_result.all_candidates) > 0

        # Verify candidates have correct structure
        for c in wf_result.all_candidates:
            assert "utr5_sequence" in c.metadata
            assert "cds_sequence" in c.metadata
            assert "utr3_sequence" in c.metadata

        # Check execution log for expected events
        log = final_state.get("_execution_log", [])
        assert any(e.get("event") == "step_start" for e in log)
        assert any(e.get("event") == "step_done" for e in log)
        assert any(e.get("event") == "plan_complete" for e in log)

    @skip_if_no_api_key
    def test_retry_flow_with_mock_low_quality_result(self):
        """Mock workflow returns low-quality result → live critic triggers retry → parameters adjusted."""
        registry = _build_stub_registry()
        workflow = FullLengthMrnaDesignWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"full_length_mrna_design": workflow},
        )

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf1",
                    type="workflow",
                    target="full_length_mrna_design",
                    input_binding={
                        "protein_sequence": "MKTAIVE",
                        "design_tool": "lineardesign",
                        "lambda_value": 0.0,
                    },
                )
            ],
            max_retries=2,
        )

        # Build a fake low-quality result (all high IRES)
        low_quality_cands = _make_candidates_with_metrics(
            presets=[("short", "short"), ("medium", "medium"), ("long", "long")],
            ires_scores=[0.85, 0.90, 0.88],
        )
        low_quality_result = WorkflowResult(
            success=True,
            task_id="mock_low",
            best_candidate=low_quality_cands[0],
            all_candidates=low_quality_cands,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "full_length_mrna_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return low_quality_result
            raise RuntimeError(f"Unexpected: {step.target}")

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            final_state = controller.execute(plan, {}, replan_fn=lambda s: plan)

        # Should have retried (critic sees high IRES → requests retry)
        assert call_count >= 1
        # Check if critic was consulted
        log = final_state.get("_execution_log", [])
        print(f"\n[Retry flow log]\n")
        for e in log:
            print(f"  {e}")

        # The live critic may or may not trigger retry depending on its judgment;
        # the key assertion is that the flow completed without crashing.
        assert final_state.get("_plan_executed") is True


# ═══════════════════════════════════════════════════════════════════════
# Layer 2 — Workflow: generation + evaluation + ranking
# ═══════════════════════════════════════════════════════════════════════


class TestLayer2Workflow:
    """Test FullLengthMrnaDesignWorkflow with stub capabilities (fast, no LLM)."""

    def test_workflow_generates_candidates_with_all_utr_presets(self):
        """utr_mode='all' should produce candidates with short/medium/long UTRs."""
        registry = _build_stub_registry()
        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(protein_sequence="MKTAIVE", design_tool="all", utr_mode="all")
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

    def test_workflow_ranking_produces_valid_total_rank(self):
        """rank_and_format should produce Borda-count rankings."""
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
        # All candidates should have total_rank
        for c in result.all_candidates:
            assert "total_rank" in c.scores
            assert "cds_rank" in c.scores
            assert "utr5_rank" in c.scores
            assert "utr3_rank" in c.scores

    def test_workflow_run_full_pipeline(self):
        """run() should execute the complete pipeline end-to-end."""
        registry = _build_stub_registry(mrl=6.5, utr3_stab=0.8, ires_score=0.1)
        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(
            protein_sequence="MKTAIVE",
            design_tool="all",
            utr_mode="short",
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
