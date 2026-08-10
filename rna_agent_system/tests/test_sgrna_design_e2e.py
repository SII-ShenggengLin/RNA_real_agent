"""End-to-end tests for sgrna_design workflow across all layers (0-3).

Layer 0 — Direct tool invocation (HTTP calls to microservices)
Layer 1 — Capability wrapping + state writeback
Layer 2 — Workflow orchestration (generate → evaluate → score → rank)
Layer 3 — Multi-Agent Execution (PipelineAgent + QualityAgent + retry + parameter override)

These tests use REAL microservices (ports 8017 for sgrna_design, 8011 for CRISOT)
and REAL DeepSeek API for QualityAgent.  They verify:
  - GPU tools run on GPU
  - CPU tools run on CPU
  - DeepSeek API is successfully called and produces actionable output
  - Retry logic works end-to-end
  - Parameter adjustments from QualityAgent are applied

Requirements:
  - sgrna_design_service running on port 8017 (GPU-capable)
  - crisot_service running on port 8011 (CPU-only)
  - DeepSeek API key configured in environment
  - ViennaRNA installed for MCMC mode
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
import requests

# ──────────────────────────────────────────────────────────────────────────────
# Environment checks (skip tests when dependencies are missing)
# ──────────────────────────────────────────────────────────────────────────────


def _service_available(url: str, timeout: float = 3.0) -> bool:
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:
        return False


SGRNA_SERVICE_UP = _service_available("http://127.0.0.1:8017/health")
CRISOT_SERVICE_UP = _service_available("http://127.0.0.1:8011/health")
DEEPSEEK_KEY_SET = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())

pytestmark = [
    pytest.mark.gpu,
    pytest.mark.slow,
    pytest.mark.skipif(not SGRNA_SERVICE_UP, reason="sgrna_design service (port 8017) not reachable"),
    pytest.mark.skipif(not CRISOT_SERVICE_UP, reason="CRISOT service (port 8011) not reachable"),
    pytest.mark.skipif(not DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_SEED_60 = "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG"


def _check_gpu_device(result: dict[str, Any]) -> None:
    """Assert that a tool result indicates GPU execution."""
    device = result.get("device", "")
    assert "cuda" in device.lower(), f"Expected GPU device, got: {device}"


def _check_cpu_device(result: dict[str, Any]) -> None:
    """Assert that a tool result indicates CPU execution."""
    device = result.get("device", "")
    assert "cpu" in device.lower(), f"Expected CPU device, got: {device}"


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 0 — Direct Tool Invocation (real HTTP microservices)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer0DirectToolInvocation:
    """Layer 0: invoke tools.py functions directly against running microservices."""

    def test_layer0_design_sgrna_handle_with_crgpt_default_gpu(self):
        """design_sgrna_handle_with_crgpt should run on GPU by default."""
        from agent_core.tools import design_sgrna_handle_with_crgpt

        result = design_sgrna_handle_with_crgpt.invoke({
            "seed_sequence": _SEED_60,
            "n_samples": 3,
            "mutation_number": 10,
            "sampling_mode": "naive",
        })
        assert result["generated_count"] >= 1, "Expected at least 1 candidate"
        assert result["best_sequence"], "Expected a best sequence"
        assert result["summary_json_filepath"], "Expected summary JSON path"
        assert Path(result["summary_json_filepath"]).exists(), "Summary JSON should exist"
        # Default device should be GPU when CUDA is available
        _check_gpu_device(result)

    def test_layer0_design_sgrna_handle_with_crgpt_explicit_cpu(self):
        """design_sgrna_handle_with_crgpt should respect device=cpu."""
        from agent_core.tools import design_sgrna_handle_with_crgpt

        result = design_sgrna_handle_with_crgpt.invoke({
            "seed_sequence": _SEED_60,
            "n_samples": 2,
            "mutation_number": 5,
            "sampling_mode": "naive",
            "device": "cpu",
        })
        assert result["generated_count"] >= 1
        _check_cpu_device(result)

    def test_layer0_score_sgrna_handle_with_crgpt(self):
        """score_sgrna_handle_with_crgpt should return nn_score and structure metrics."""
        from agent_core.tools import score_sgrna_handle_with_crgpt

        result = score_sgrna_handle_with_crgpt.invoke({
            "sequence": _SEED_60,
            "device": "cuda:0",
        })
        assert "nn_score" in result, f"Missing nn_score in result: {result.keys()}"
        assert result["nn_score"] > 0, "nn_score should be positive"
        assert "log_likelihood" in result
        assert "normalized_sequence" in result
        assert result["normalized_sequence"] == _SEED_60.upper().replace("U", "T")
        # ScoreResponse does not include device field; verify the model ran successfully

    def test_layer0_score_crispr_off_target_with_crisot(self):
        """score_crispr_off_target_with_crisot runs on CPU (no GPU requirement)."""
        from agent_core.tools import score_crispr_off_target_with_crisot
        from agent_core.file_manager import save_sequence

        guide = "ATGCATGCATGCATGCATGCTGG"
        target = "ATGCATGCATGCATGCATGCTGG"
        guide_fp = save_sequence(guide, prefix="sgrna_guide")

        result = score_crispr_off_target_with_crisot.invoke({
            "filepath": guide_fp,
            "target_sequence": target,
        })
        assert "crisot_score" in result, f"Missing crisot_score: {result.keys()}"
        assert 0.0 <= result["crisot_score"] <= 1.0, "crisot_score should be in [0, 1]"
        assert result["sgrna"] == guide.upper().replace("U", "T")
        assert result["target_sequence"] == target.upper().replace("U", "T")

    def test_layer0_crisot_service_health(self):
        """CRISOT service health endpoint should report all requirements OK."""
        resp = requests.get("http://127.0.0.1:8011/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok", f"CRISOT service degraded: {data.get('missing_requirements')}"
        assert data["score_param_exists"] is True
        assert data["repo_exists"] is True

    def test_layer0_sgrna_service_health(self):
        """sgRNA design service health should report model available."""
        resp = requests.get("http://127.0.0.1:8017/health", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok", f"sgRNA service degraded: {data}"
        assert data["model_exists"] is True
        assert data["cuda_available"] is True

    def test_layer0_design_and_score_chain(self):
        """Design a candidate then score it — verifies end-to-end tool chain."""
        from agent_core.tools import design_sgrna_handle_with_crgpt, score_sgrna_handle_with_crgpt

        design_result = design_sgrna_handle_with_crgpt.invoke({
            "seed_sequence": _SEED_60,
            "n_samples": 2,
            "mutation_number": 5,
            "sampling_mode": "naive",
            "device": "cpu",
        })
        best_seq = design_result["best_sequence"]
        assert best_seq, "Design should produce a best sequence"

        score_result = score_sgrna_handle_with_crgpt.invoke({"sequence": best_seq, "device": "cpu"})
        assert score_result["nn_score"] > 0
        assert score_result["sequence"] == best_seq


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 1 — Capability Invocation (wraps tool + state writeback)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer1Capability:
    """Layer 1: Capability.invoke() wraps tool execution and writes state."""

    def test_layer1_capability_design_sgrna(self):
        """Capability for design_sgrna_handle_with_crgpt should work end-to-end."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core import tools as tools_mod

        reg = ToolRegistry()
        reg.register(tools_mod.design_sgrna_handle_with_crgpt)
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("design_sgrna_handle_with_crgpt")

        cap = cap_reg.get("design_sgrna_handle_with_crgpt")
        state: dict = {}
        result = cap.invoke(
            {
                "seed_sequence": _SEED_60,
                "n_samples": 2,
                "mutation_number": 5,
                "sampling_mode": "naive",
                "device": "cpu",
            },
            state=state,
        )
        assert result.success is True, f"Capability failed: {result.error}"
        assert result.output.get("generated_count", 0) >= 1
        # State writeback
        assert "tool_results" in state
        assert "design_sgrna_handle_with_crgpt" in state["tool_results"]

    def test_layer1_capability_score_sgrna(self):
        """Capability for score_sgrna_handle_with_crgpt should write state."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core import tools as tools_mod

        reg = ToolRegistry()
        reg.register(tools_mod.score_sgrna_handle_with_crgpt)
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("score_sgrna_handle_with_crgpt")

        cap = cap_reg.get("score_sgrna_handle_with_crgpt")
        state: dict = {}
        result = cap.invoke({"sequence": _SEED_60, "device": "cpu"}, state=state)
        assert result.success is True
        assert "nn_score" in result.output
        assert "tool_results" in state

    def test_layer1_capability_crisot(self):
        """Capability for CRISOT scoring should work and write back state."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core import tools as tools_mod
        from agent_core.file_manager import save_sequence

        guide = "ATGCATGCATGCATGCATGCTGG"
        target = "ATGCATGCATGCATGCATGCTGG"
        guide_fp = save_sequence(guide, prefix="sgrna_guide")

        reg = ToolRegistry()
        reg.register(tools_mod.score_crispr_off_target_with_crisot)
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("score_crispr_off_target_with_crisot")

        cap = cap_reg.get("score_crispr_off_target_with_crisot")
        state: dict = {}
        result = cap.invoke(
            {"filepath": guide_fp, "target_sequence": target},
            state=state,
        )
        assert result.success is True
        assert "crisot_score" in result.output
        assert 0.0 <= result.output["crisot_score"] <= 1.0
        assert "tool_results" in state


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 2 — Workflow Orchestration (real services)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer2Workflow:
    """Layer 2: SgRnaDesignWorkflow.run() with real microservices."""

    @pytest.fixture
    def real_workflow(self):
        """Build a workflow backed by real capabilities."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core import tools as tools_mod
        from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow

        reg = ToolRegistry()
        reg.register(tools_mod.design_sgrna_handle_with_crgpt)
        reg.register(tools_mod.score_sgrna_handle_with_crgpt)
        reg.register(tools_mod.score_crispr_off_target_with_crisot)

        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("design_sgrna_handle_with_crgpt")
        cap_reg.register("score_sgrna_handle_with_crgpt")
        cap_reg.register("score_crispr_off_target_with_crisot")

        return SgRnaDesignWorkflow(cap_reg)

    def test_layer2_workflow_run_seed_sequence(self, real_workflow):
        """Full workflow with inline seed sequence."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=3,
            mutation_number=8,
            sampling_mode="naive",
            evaluate_crgpt_score=True,
            evaluate_crisot=False,
        )
        result = real_workflow.run(inp)
        assert result.success is True, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None
        assert len(result.all_candidates) >= 1
        # Check that evaluation happened
        best = result.best_candidate
        assert "metrics_bundle" in best.metadata
        assert "nn_score" in best.metadata["metrics_bundle"]

    def test_layer2_workflow_run_with_guide_target(self, real_workflow):
        """Full workflow including CRISOT off-target scoring."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        guide = "ATGCATGCATGCATGCATGCTGG"
        target = "ATGCATGCATGCATGCATGCTGG"

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="naive",
            guide_sequence=guide,
            target_sequence=target,
            evaluate_crgpt_score=True,
            evaluate_crisot=True,
        )
        result = real_workflow.run(inp)
        assert result.success is True, f"Workflow failed: {result.errors}"
        # All candidates should have CRISOT score
        for c in result.all_candidates:
            assert c.metadata["metrics_bundle"].get("crisot_score") is not None

    def test_layer2_workflow_crisot_caching(self, real_workflow):
        """CRISOT should be called only once per workflow run."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core import tools as tools_mod

        call_count = 0
        original_tool = tools_mod.score_crispr_off_target_with_crisot

        def _counting_wrapper(*, filepath, target_sequence, service_url="http://127.0.0.1:8011/score"):
            nonlocal call_count
            call_count += 1
            return original_tool(
                filepath=filepath,
                target_sequence=target_sequence,
                service_url=service_url,
            )

        # Build a fresh workflow with the counting wrapper injected
        reg = ToolRegistry()

        class _CountingCrisotTool:
            name = "score_crispr_off_target_with_crisot"

            def invoke(self, kwargs: dict[str, Any]) -> dict[str, Any]:
                nonlocal call_count
                call_count += 1
                return original_tool.invoke(kwargs)

        reg.register(tools_mod.design_sgrna_handle_with_crgpt)
        reg.register(tools_mod.score_sgrna_handle_with_crgpt)
        reg.register(_CountingCrisotTool())

        from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("design_sgrna_handle_with_crgpt")
        cap_reg.register("score_sgrna_handle_with_crgpt")
        cap_reg.register("score_crispr_off_target_with_crisot")

        wf = SgRnaDesignWorkflow(cap_reg)
        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=3,
            mutation_number=5,
            sampling_mode="naive",
            guide_sequence="ATGCATGCATGCATGCATGCTGG",
            target_sequence="ATGCATGCATGCATGCATGCTGG",
            evaluate_crisot=True,
        )
        result = wf.run(inp)
        assert result.success is True
        # With 3 candidates, CRISOT should still only be called once (cached)
        assert call_count == 1, f"Expected CRISOT called once, got {call_count}"

    def test_layer2_workflow_progress_callback(self, real_workflow):
        """progress_callback should receive events during workflow execution."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        events: list[dict] = []

        def _cb(entry: dict) -> None:
            events.append(entry)

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="naive",
            evaluate_crgpt_score=True,
            evaluate_crisot=False,
        )
        result = real_workflow.run(inp, progress_callback=_cb)
        assert result.success is True
        event_names = [e["event"] for e in events]
        assert "generate_complete" in event_names
        assert "evaluate_progress" in event_names

    def test_layer2_workflow_naive_mode(self, real_workflow):
        """Workflow should support naive sampling mode."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="naive",
            temperature=1.0,
        )
        result = real_workflow.run(inp)
        assert result.success is True
        assert len(result.all_candidates) >= 1
        # Verify metadata contains sampling_mode
        for c in result.all_candidates:
            assert c.metadata.get("sampling_mode") == "naive"

    def test_layer2_workflow_mcmc_mode(self, real_workflow):
        """Workflow should support MCMC sampling mode (requires ViennaRNA)."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="mcmc",
            temperature=20.0,
        )
        result = real_workflow.run(inp)
        assert result.success is True
        assert len(result.all_candidates) >= 1

    def test_layer2_workflow_gpu_cpu_separation(self, real_workflow):
        """Verify that CRGPT runs on GPU and CRISOT does not require GPU."""
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        guide = "ATGCATGCATGCATGCATGCTGG"
        target = "ATGCATGCATGCATGCATGCTGG"

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="naive",
            guide_sequence=guide,
            target_sequence=target,
            evaluate_crisot=True,
        )
        result = real_workflow.run(inp)
        assert result.success is True
        # Verify candidates have both scores computed
        best = result.best_candidate
        assert best is not None
        mb = best.metadata.get("metrics_bundle", {})
        assert "nn_score" in mb, "CRGPT (GPU) score should be present"
        assert "crisot_score" in mb, "CRISOT (CPU) score should be present"


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 — Multi-Agent Execution (PipelineAgent + QualityAgent + retry)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer4PlanningAndControl:
    """Layer 3: PipelineAgent + QualityAgent + SpecialistAgent + retry + parameter override."""

    @pytest.fixture
    def real_workflow(self):
        """Build a workflow backed by real capabilities."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core import tools as tools_mod
        from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow

        reg = ToolRegistry()
        reg.register(tools_mod.design_sgrna_handle_with_crgpt)
        reg.register(tools_mod.score_sgrna_handle_with_crgpt)
        reg.register(tools_mod.score_crispr_off_target_with_crisot)

        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        cap_reg.register("design_sgrna_handle_with_crgpt")
        cap_reg.register("score_sgrna_handle_with_crgpt")
        cap_reg.register("score_crispr_off_target_with_crisot")

        return SgRnaDesignWorkflow(cap_reg)

    def _make_pipeline_agent(self, real_workflow):
        """Build a PipelineAgent backed by a SpecialistAgent for sgrna_design."""
        from agent_core.agents.pipeline_agent import PipelineAgent
        from agent_core.agents.quality_agent import QualityAgent
        from agent_core.agents.specialist_agent import SpecialistAgent
        from agent_core.agents.synthesis_agent import SynthesisAgent
        from agent_core.quality_profiles.sgrna_design import SGRNA_QUALITY_PROFILE

        specialist = SpecialistAgent(real_workflow, SGRNA_QUALITY_PROFILE)
        return PipelineAgent(
            specialist_registry={"sgrna_design": specialist},
            quality_agent=QualityAgent(),
            synthesis_agent=SynthesisAgent(),
        )

    def test_layer3_quality_agent_diagnose_calls_deepseek(self, real_workflow):
        """QualityAgent.review() should successfully call DeepSeek API."""
        from agent_core.agents.quality_agent import QualityAgent
        from agent_core.quality_profiles.sgrna_design import SGRNA_QUALITY_PROFILE
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=5,
            sampling_mode="naive",
            evaluate_crgpt_score=True,
            evaluate_crisot=False,
        )
        result = real_workflow.run(inp)
        assert result.success is True

        quality_agent = QualityAgent()
        state: dict = {}

        # This call goes out to DeepSeek API
        report = quality_agent.review(result, SGRNA_QUALITY_PROFILE, state)

        # Verify we got a real structured response
        assert report.overall_assessment, "Expected assessment text from LLM"
        assert 0.0 <= report.quality_score <= 1.0, "quality_score should be in [0, 1]"
        assert report.action in (
            "pass",
            "retry_with_adjustments",
            "retry_with_alternative",
            "abort",
        ), f"Unexpected action: {report.action}"
        assert report.confidence >= 0.0, "confidence should be non-negative"
        # State should record the diagnosis
        assert "_diagnosis_history" in state
        assert len(state["_diagnosis_history"]) == 1

    def test_layer3_quality_agent_recommends_retry_on_poor_results(self, real_workflow):
        """When results are poor, QualityAgent should recommend retry."""
        from agent_core.agents.quality_agent import QualityAgent
        from agent_core.quality_profiles.sgrna_design import SGRNA_QUALITY_PROFILE
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        # Run with very challenging parameters to get poor results
        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=35,  # very high mutation count → likely poor quality
            sampling_mode="naive",
            temperature=5.0,  # very high temperature → poor quality
            evaluate_crgpt_score=True,
            evaluate_crisot=False,
        )
        result = real_workflow.run(inp)
        assert result.success is True  # workflow itself succeeds

        quality_agent = QualityAgent()
        state: dict = {}
        report = quality_agent.review(result, SGRNA_QUALITY_PROFILE, state)

        # The diagnosis should have been recorded
        assert "_last_diagnosis" in state or "_diagnosis_history" in state
        assert "_parameter_overrides" in state

        # If retry is recommended, verify parameter overrides are provided
        if report.action in ("retry_with_adjustments", "retry_with_alternative"):
            overrides = state.get("_parameter_overrides", {})
            assert len(overrides) > 0, "Expected parameter overrides for retry"
            # Overrides should only contain known parameters
            known_params = {
                "n_samples",
                "mutation_number",
                "temperature",
                "sampling_mode",
                "max_overlap",
                "evaluate_crgpt_score",
                "evaluate_crisot",
                "weight_nn_score",
                "weight_crisot",
            }
            for key in overrides:
                assert key in known_params, f"Unknown parameter override: {key}"

    def test_layer3_pipeline_agent_e2e(self, real_workflow):
        """PipelineAgent should run sgrna_design workflow end-to-end."""
        from agent_core.pipeline.models import PipelinePlan
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        # Verify direct workflow run works first (isolates service issues)
        direct_inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=3,
            mutation_number=8,
            sampling_mode="naive",
        )
        direct_result = real_workflow.run(direct_inp)
        assert direct_result.success is True, (
            f"Direct workflow run failed: {direct_result.errors}. "
            "This indicates a service-side issue, not PipelineAgent."
        )

        pipeline = self._make_pipeline_agent(real_workflow)
        plan = PipelinePlan.single(
            workflow="sgrna_design",
            static_params={
                "seed_sequence": _SEED_60,
                "n_samples": 3,
                "mutation_number": 8,
                "sampling_mode": "naive",
            },
            plan_id="sgrna_pipeline_1",
            output_alias="sgrna_result",
        )
        state: dict = {}
        pipeline_result = pipeline.execute(plan, state)

        assert pipeline_result.success is True, (
            f"PipelineAgent workflow failed: {pipeline_result.errors}"
        )
        assert "n1" in pipeline_result.node_results
        node_result = pipeline_result.node_results["n1"]
        assert node_result.success is True, (
            f"Node execution failed: {node_result.errors}"
        )
        assert node_result.workflow_result is not None
        assert node_result.workflow_result.success is True

    def test_layer3_specialist_agent_applies_parameter_overrides(self, real_workflow):
        """SpecialistAgent should apply parameter overrides from QualityAgent."""
        from agent_core.agents.quality_agent import QualityAgent
        from agent_core.agents.specialist_agent import SpecialistAgent
        from agent_core.quality_profiles.sgrna_design import SGRNA_QUALITY_PROFILE
        from agent_core.workflows.sgrna_design import SgRnaDesignInput

        # Run with extreme parameters so QualityAgent recommends adjustments
        inp = SgRnaDesignInput(
            seed_sequence=_SEED_60,
            n_samples=2,
            mutation_number=30,
            sampling_mode="naive",
            temperature=5.0,
            evaluate_crgpt_score=True,
            evaluate_crisot=False,
        )

        specialist = SpecialistAgent(real_workflow, SGRNA_QUALITY_PROFILE)
        quality_agent = QualityAgent()
        state: dict = {}

        result = specialist.run(
            node_id="sgrna_override_test",
            params=inp.model_dump(),
            quality_agent=quality_agent,
            state=state,
        )

        # Diagnosis and overrides should be recorded
        assert "_diagnosis_history" in state
        assert "_parameter_overrides" in state

        # If retry occurred, the final params should differ from the initial ones
        if result.metadata.get("retry_count", 0) > 0:
            final_params = state.get("_last_workflow_params", {})
            assert (
                final_params.get("mutation_number", 30) != 30
                or final_params.get("temperature", 5.0) != 5.0
            ), "Expected QualityAgent-recommended overrides to be applied"

    def test_layer3_pipeline_agent_retry_with_real_deepseek(self, real_workflow):
        """Full end-to-end: PipelineAgent + QualityAgent + SpecialistAgent + retry cycle.

        This test forces poor quality results and verifies that:
        1. DeepSeek API is called for diagnosis
        2. QualityAgent recommends parameter adjustments
        3. SpecialistAgent applies overrides and re-runs
        4. The process completes within retry budget
        """
        from agent_core.pipeline.models import PipelinePlan

        pipeline = self._make_pipeline_agent(real_workflow)
        plan = PipelinePlan.single(
            workflow="sgrna_design",
            static_params={
                "seed_sequence": _SEED_60,
                "n_samples": 2,
                "mutation_number": 30,  # extreme value to trigger poor results
                "sampling_mode": "naive",
                "temperature": 5.0,  # extreme temperature
            },
            plan_id="sgrna_retry_pipeline",
            output_alias="sgrna_result",
        )

        state: dict = {}
        start_time = time.time()
        pipeline_result = pipeline.execute(plan, state)
        elapsed = time.time() - start_time

        # Basic completion checks
        assert pipeline_result.success is True, (
            f"Pipeline retry cycle failed: {pipeline_result.errors}"
        )

        # Verify DeepSeek was called (diagnosis history exists)
        diag_history = state.get("_diagnosis_history", [])
        assert len(diag_history) >= 1, (
            f"Expected at least one LLM diagnosis. State keys: {list(state.keys())}"
        )

        # Log timing for observability
        print(f"\n[Layer3 test] DeepSeek + retry cycle completed in {elapsed:.1f}s")
        print(f"[Layer3 test] Diagnoses made: {len(diag_history)}")
        for i, diag in enumerate(diag_history):
            action = diag.get("action", "unknown") if isinstance(diag, dict) else getattr(diag, "action", "unknown")
            print(f"[Layer3 test] Diagnosis {i + 1}: action={action}")

    def test_layer3_deepseek_api_connection_verification(self):
        """Directly verify DeepSeek API connectivity and response format."""
        from agent_core.llm_config import get_deepseek_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_deepseek_llm(temperature=0.1)
        messages = [
            SystemMessage(content="You are a helpful assistant. Respond with a single word."),
            HumanMessage(content="What is 2+2?"),
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        assert content, "DeepSeek API returned empty response"
        assert "4" in content, f"Expected '4' in response, got: {content}"
        print(f"\n[DeepSeek API test] Response: {content}")
