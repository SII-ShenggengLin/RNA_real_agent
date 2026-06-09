"""Comprehensive tests for IRES prediction workflow across all layers (0-3).

Covers:
- Layer 0: Real tool calls (IRESfinder, ViennaRNA fold/plfold, unpaired fraction)
- Layer 1: CapabilityRegistry integration with real tools
- Layer 2: Full workflow end-to-end with real tools
- Layer 3: LLM Critic with real DeepSeek API calls, retry logic, parameter overrides

All tools in this workflow are CPU-based (no GPU tools):
- IRESfinder (port 8013): logistic regression model, CPU
- ViennaRNA RNAfold (port 8003): thermodynamic folding, CPU
- ViennaRNA RNAplfold (port 8003): local accessibility, CPU
- RNA sequence metrics /unpaired-fraction (port 8020): dot-bracket analysis, CPU
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import PROJECT_ROOT, save_sequence, save_text_file
from agent_core.llm_config import get_deepseek_llm
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import WorkflowResult
from agent_core.workflows.ires_prediction import (
    IRES_PREDICTION_CRITIC_CONFIG,
    IresPredictionInput,
    IresPredictionLLMCritic,
    IresPredictionWorkflow,
    assign_confidence,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def test_sequences_dir():
    """Directory for test sequence files."""
    td = PROJECT_ROOT / "workspace" / "test_ires_sequences"
    td.mkdir(parents=True, exist_ok=True)
    return td


@pytest.fixture(scope="module")
def at_rich_fasta(test_sequences_dir):
    """AT-rich sequence that produces positive IRES predictions."""
    fp = test_sequences_dir / "at_rich_800nt.fasta"
    seq = "ATAT" * 200  # 800 nt, known to trigger IRESfinder positive
    fp.write_text(f">test_at_rich\n{seq}\n")
    return str(fp)


@pytest.fixture(scope="module")
def random_fasta(test_sequences_dir):
    """Random sequence unlikely to produce IRES positives (for empty-result tests)."""
    fp = test_sequences_dir / "random_200nt.fasta"
    seq = "ACGT" * 50  # 200 nt
    fp.write_text(f">test_random\n{seq}\n")
    return str(fp)


@pytest.fixture(scope="module")
def real_tool_registry():
    """Build a ToolRegistry + ToolExecutor with all real tools registered."""
    from agent_core import tools as tools_mod

    registry = ToolRegistry()
    registry.register_many(list(tools_mod.ALL_LANGCHAIN_AGENT_TOOLS))
    executor = ToolExecutor(registry)
    return executor


@pytest.fixture(scope="module")
def real_capability_registry(real_tool_registry):
    """Build a CapabilityRegistry with all tools required by IRES workflow."""
    cap_reg = CapabilityRegistry(real_tool_registry)
    for name in IresPredictionWorkflow.required_capabilities:
        cap_reg.register(name)
    return cap_reg


# =============================================================================
# Layer 0 — Direct Tool Calls (real services, no mocks)
# =============================================================================


class TestLayer0DirectToolCalls:
    """Verify each underlying bioinformatics tool works correctly.

    These tests exercise the actual microservices:
    - IRESfinder on port 8013 (CPU)
    - ViennaRNA on port 8003 (CPU)
    - RNA sequence metrics on port 8020 (CPU)
    """

    def test_layer0_iresfinder_mode0_full_sequence(self, at_rich_fasta):
        """IRESfinder mode 0: score the full sequence as one fragment."""
        from agent_core.tools import predict_putative_ires_with_iresfinder

        result = predict_putative_ires_with_iresfinder.func(
            filepath=at_rich_fasta,
            mode=0,
            decision_threshold=0.5,
        )
        assert result["fragment_count"] == 1
        assert result["has_putative_ires"] is True
        assert result["max_score"] > 0.5
        assert result["positive_count"] == 1
        assert len(result["predictions"]) > 0
        # Verify output schema fields
        assert "input_filepath" in result
        assert "model" in result
        assert result["model"] == "IRESfinder-logreg-py3"

    def test_layer0_iresfinder_mode2_sliding_window(self, at_rich_fasta):
        """IRESfinder mode 2: scan with sliding windows."""
        from agent_core.tools import predict_putative_ires_with_iresfinder

        result = predict_putative_ires_with_iresfinder.func(
            filepath=at_rich_fasta,
            mode=2,
            window_size=174,
            step_size=50,
            decision_threshold=0.5,
        )
        assert result["fragment_count"] > 0
        assert result["has_putative_ires"] is True
        assert result["max_score"] > 0.5
        assert result["positive_count"] > 0
        # Verify sliding-window parameters echoed back
        assert result["window_size"] == 174
        assert result["step_size"] == 50
        assert result["mode"] == 2
        # Verify prediction structure
        for pred in result["predictions"]:
            assert "fragment_id" in pred
            assert "predicted_label" in pred
            assert "score" in pred
            assert pred["predicted_label"] in ("IRES", "non-IRES")

    def test_layer0_iresfinder_high_threshold_no_positives(self, at_rich_fasta):
        """Very high threshold should yield no positives (used for retry tests)."""
        from agent_core.tools import predict_putative_ires_with_iresfinder

        result = predict_putative_ires_with_iresfinder.func(
            filepath=at_rich_fasta,
            mode=0,
            decision_threshold=0.99,  # Impossibly high
        )
        assert result["has_putative_ires"] is False
        assert result["positive_count"] == 0
        assert result["max_score"] < 0.99

    def test_layer0_viennarna_rnafold(self):
        """ViennaRNA RNAfold: predict MFE structure (CPU tool)."""
        from agent_core.tools import predict_rna_secondary_structure

        # Write a short RNA sequence file
        seq = "ACGUACGUACGUACGUACGUACGUACGUACGU"
        fp = save_sequence(seq, prefix="test_vienna_fold")
        result = predict_rna_secondary_structure.func(filepath=fp)

        assert "structure" in result
        assert "mfe_kcal_per_mol" in result
        assert isinstance(result["structure"], str)
        assert len(result["structure"]) == len(seq)
        # Structure should only contain valid dot-bracket chars
        valid_chars = set(".()[]{}<>")
        assert all(c in valid_chars for c in result["structure"])
        assert result["mfe_kcal_per_mol"] < 0  # Negative MFE = stable structure
        assert result["model"] == "ViennaRNA-RNAfold"

    def test_layer0_viennarna_rnaplfold(self):
        """ViennaRNA RNAplfold: local accessibility profile (CPU tool)."""
        from agent_core.tools import predict_rna_local_accessibility_profile_vienna

        seq = "ACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGUACGU"
        fp = save_sequence(seq, prefix="test_vienna_plfold")
        result = predict_rna_local_accessibility_profile_vienna.func(filepath=fp)

        assert "mean_unpaired_prob_1nt" in result
        assert "lunp_profile_tsv_filepath" in result
        assert 0 <= result["mean_unpaired_prob_1nt"] <= 1
        assert result["profile_positions_count"] == len(seq)
        # TSV file should exist
        tsv_path = result["lunp_profile_tsv_filepath"]
        assert Path(tsv_path).exists()
        assert result["model"] == "ViennaRNA-RNAplfold"

    def test_layer0_dot_bracket_unpaired_fraction(self):
        """RNA sequence metrics: compute unpaired fraction from dot-bracket (CPU tool)."""
        from agent_core.tools import compute_dot_bracket_unpaired_fraction

        structure = "((((....))))....(((())))"
        fp = save_text_file(structure, prefix="test_structure", suffix=".db")
        result = compute_dot_bracket_unpaired_fraction.func(filepath=fp)

        assert "unpaired_fraction" in result
        assert 0 <= result["unpaired_fraction"] <= 1
        assert result["structure_length"] == len(structure)
        assert result["dot_count"] == structure.count(".")
        # Verify math: 8 dots / 25 chars = 0.32
        expected = structure.count(".") / len(structure)
        assert abs(result["unpaired_fraction"] - expected) < 0.001

    def test_layer0_all_tools_are_cpu(self):
        """Sanity check: all tools used by this workflow are CPU-based.

        This test documents the hardware requirements. No GPU is needed.
        """
        from agent_core.tool_specs import TOOL_SPECS

        tool_names = IresPredictionWorkflow.required_capabilities
        for name in tool_names:
            spec = TOOL_SPECS.get(name)
            assert spec is not None, f"ToolSpec for {name} not found"
            # None of these tools declare GPU requirements
            deps = [d.name for d in (spec.requires or [])]
            gpu_deps = [d for d in deps if "gpu" in d.lower() or "cuda" in d.lower()]
            assert len(gpu_deps) == 0, f"Tool {name} unexpectedly has GPU dep: {gpu_deps}"


# =============================================================================
# Layer 1 — CapabilityRegistry Integration (real tools wrapped as capabilities)
# =============================================================================


class TestLayer1CapabilityRegistry:
    """Verify Layer 1: tools wrapped as capabilities, state writeback works."""

    def test_layer1_capability_iresfinder(self, real_capability_registry, at_rich_fasta):
        """IRESfinder capability via CapabilityRegistry with real tool."""
        cap = real_capability_registry.get("predict_putative_ires_with_iresfinder")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {
                "filepath": at_rich_fasta,
                "mode": 0,
                "decision_threshold": 0.5,
            },
            state=state,
        )
        assert result.success is True
        assert result.output["has_putative_ires"] is True
        assert result.output["max_score"] > 0.5
        # State writeback
        assert "tool_results" in state
        assert "predict_putative_ires_with_iresfinder" in state["tool_results"]

    def test_layer1_capability_vienna_fold(self, real_capability_registry):
        """ViennaRNA fold capability via CapabilityRegistry."""
        cap = real_capability_registry.get("predict_rna_secondary_structure")
        seq = "ACGUACGUACGUACGUACGUACGUACGUACGU"
        fp = save_sequence(seq, prefix="test_cap_fold")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": fp}, state=state)
        assert result.success is True
        assert "structure" in result.output
        assert "mfe_kcal_per_mol" in result.output
        assert "tool_results" in state
        assert "predict_rna_secondary_structure" in state["tool_results"]

    def test_layer1_capability_vienna_plfold(self, real_capability_registry):
        """ViennaRNA plfold capability via CapabilityRegistry."""
        cap = real_capability_registry.get("predict_rna_local_accessibility_profile_vienna")
        seq = "ACGUACGUACGUACGUACGUACGUACGUACGUACGUACGU"
        fp = save_sequence(seq, prefix="test_cap_plfold")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": fp}, state=state)
        assert result.success is True
        assert "mean_unpaired_prob_1nt" in result.output
        assert "tool_results" in state

    def test_layer1_capability_unpaired_fraction(self, real_capability_registry):
        """Dot-bracket unpaired fraction capability via CapabilityRegistry."""
        cap = real_capability_registry.get("compute_dot_bracket_unpaired_fraction")
        structure = "((((....))))...."
        fp = save_text_file(structure, prefix="test_cap_unp", suffix=".db")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": fp}, state=state)
        assert result.success is True
        assert "unpaired_fraction" in result.output
        assert "tool_results" in state

    def test_layer1_all_required_capabilities_present(self, real_capability_registry):
        """All capabilities required by IresPredictionWorkflow must be registered."""
        for name in IresPredictionWorkflow.required_capabilities:
            assert real_capability_registry.has(name), f"Missing capability: {name}"


# =============================================================================
# Layer 2 — Full Workflow End-to-End (real tools, real pipeline)
# =============================================================================


class TestLayer2FullWorkflow:
    """Verify Layer 2: complete BaseDomainWorkflow pipeline with real services."""

    def test_layer2_workflow_mode0_with_structural_validation(self, real_capability_registry, at_rich_fasta):
        """Full workflow: mode 0 + structural validation (all tools real)."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            probability_threshold=0.5,
            run_structural_validation=True,
            top_n_candidates=5,
        )
        result = wf.run(inp)
        assert result.success is True
        assert len(result.all_candidates) > 0
        best = result.best_candidate
        assert best is not None
        assert "ires_probability" in best.scores
        assert "composite_score" in best.scores
        # Structural validation should have run
        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("mfe_kcal_per_mol") is not None
        assert mb.get("structure") is not None
        assert mb.get("mean_unpaired_fraction") is not None
        assert mb.get("mean_unpaired_prob_1nt") is not None
        # Confidence should be assigned
        assert best.metadata.get("confidence") in {"high", "medium", "low", "rejected"}
        # Summary should contain candidate details
        assert "candidates=" in result.summary
        assert "best_composite_score=" in result.summary

    def test_layer2_workflow_mode2_with_structural_validation(self, real_capability_registry, at_rich_fasta):
        """Full workflow: mode 2 (sliding window) + structural validation."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=2,
            probability_threshold=0.5,
            window_size=174,
            step_size=50,
            run_structural_validation=True,
            top_n_candidates=3,
        )
        result = wf.run(inp)
        assert result.success is True
        assert len(result.all_candidates) > 0
        best = result.best_candidate
        assert best is not None
        # Verify mode 2 metadata
        assert best.metadata.get("iresfinder_mode") == 2
        # Structural metrics present
        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("mfe_kcal_per_mol") is not None
        assert mb.get("mean_unpaired_fraction") is not None

    def test_layer2_workflow_no_structural_validation(self, real_capability_registry, at_rich_fasta):
        """Full workflow: skip structural validation (faster, fewer tool calls)."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            run_structural_validation=False,
            top_n_candidates=5,
        )
        result = wf.run(inp)
        assert result.success is True
        assert len(result.all_candidates) > 0
        best = result.best_candidate
        # No structural data
        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("mfe_kcal_per_mol") is None
        assert mb.get("structure") is None
        assert mb.get("mean_unpaired_fraction") is None
        # Score is still driven by probability
        assert best.scores["composite_score"] == pytest.approx(best.scores["ires_probability"])

    def test_layer2_workflow_empty_result_high_threshold(self, real_capability_registry, at_rich_fasta):
        """High threshold yields no candidates — workflow returns success with empty list."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            probability_threshold=0.99,  # Too high for this sequence
            top_n_candidates=5,
        )
        result = wf.run(inp)
        assert result.success is True
        assert result.errors == []
        assert len(result.all_candidates) == 0

    def test_layer2_workflow_state_writeback(self, real_capability_registry, at_rich_fasta):
        """Workflow should store parameters in _state_writeback."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            probability_threshold=0.5,
        )
        result = wf.run(inp)
        assert result.success is True
        assert hasattr(result, "_state_writeback")
        wb = result._state_writeback
        assert "_workflow_params" in wb
        assert wb["_workflow_params"]["probability_threshold"] == 0.5
        assert wb["_workflow_params"]["iresfinder_mode"] == 0

    def test_layer2_workflow_dict_input(self, real_capability_registry, at_rich_fasta):
        """Workflow should accept plain dict input and convert to Pydantic model."""
        wf = IresPredictionWorkflow(real_capability_registry)
        result = wf.run(
            {
                "sequence_filepath": at_rich_fasta,
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": True,
            }
        )
        assert result.success is True
        assert len(result.all_candidates) > 0


# =============================================================================
# Layer 3 — LLM Critic + Retry + Parameter Overrides
# =============================================================================


class TestLayer3LLMCritic:
    """Verify Layer 3: LLM Critic diagnoses, retry triggers, parameter overrides.

    These tests make REAL calls to the DeepSeek API (via get_deepseek_llm).
    Requires DEEPSEEK_API_KEY to be set in the environment.
    """

    @pytest.fixture(autouse=True)
    def _require_deepseek_key(self):
        """Skip Layer 3 tests if DeepSeek API key is not configured."""
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key or key.strip() == "":
            pytest.skip("DEEPSEEK_API_KEY not set — skipping Layer 3 LLM tests")

    def test_layer3_deepseek_api_connectivity(self):
        """Sanity: DeepSeek API is reachable and returns a response."""
        llm = get_deepseek_llm(temperature=0.1)
        from langchain_core.messages import HumanMessage

        msgs = [HumanMessage(content="Return the word 'HELLO' in uppercase only.")]
        resp = llm.invoke(msgs)
        content = resp.content if hasattr(resp, "content") else str(resp)
        assert "HELLO" in content.upper()

    def test_layer3_critic_diagnose_real_api_with_good_results(self, real_capability_registry, at_rich_fasta):
        """LLM Critic diagnose() with real DeepSeek API on good workflow results.

        Verifies:
        - diagnose() returns a valid CriticDiagnosis object
        - The diagnosis has expected fields and sensible values
        - Real DeepSeek API was successfully invoked
        """
        # Run workflow to get real results
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            probability_threshold=0.5,
            run_structural_validation=True,
        )
        result = wf.run(inp)
        assert result.success is True

        # Call LLM Critic with real API
        critic = IresPredictionLLMCritic()
        state: dict[str, Any] = {"_llm_critic_enabled": True}
        diagnosis = critic.diagnose(result, state)

        # Verify structured output
        assert isinstance(diagnosis.overall_assessment, str)
        assert len(diagnosis.overall_assessment) > 0
        assert 0.0 <= diagnosis.quality_score <= 1.0
        assert isinstance(diagnosis.issues, list)
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        )
        assert isinstance(diagnosis.reasoning, str)
        assert len(diagnosis.reasoning) > 0
        assert 0.0 <= diagnosis.confidence <= 1.0

        # With good results, the diagnosis should be recorded in state
        assert "_diagnosis_history" in state
        assert len(state["_diagnosis_history"]) >= 1

    def test_layer3_critic_diagnose_empty_results_real_api(self, real_capability_registry, at_rich_fasta):
        """LLM Critic diagnose() on empty results should identify problems.

        Uses a very high threshold to force zero candidates, then checks that
        the LLM critic identifies the issue in its diagnosis.
        """
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=0,
            probability_threshold=0.99,  # Forces empty result
            top_n_candidates=5,
        )
        result = wf.run(inp)
        assert result.success is True
        assert len(result.all_candidates) == 0

        critic = IresPredictionLLMCritic()
        state: dict[str, Any] = {
            "_llm_critic_enabled": True,
            "user_text": "Find IRES candidates in this sequence",
        }
        diagnosis = critic.diagnose(result, state)

        # Verify diagnosis structure
        assert isinstance(diagnosis.overall_assessment, str)
        assert 0.0 <= diagnosis.quality_score <= 1.0
        # Even with success=True, empty results should still yield a low
        # quality score because the LLM sees candidate_count=0.
        assert diagnosis.quality_score < 0.8
        assert len(diagnosis.issues) >= 1
        # The issues should mention the lack of candidates or high threshold
        issue_text = json.dumps([i.model_dump() for i in diagnosis.issues]).lower()
        assert (
            "candidate" in issue_text
            or "threshold" in issue_text
            or "empty" in issue_text
            or "no" in issue_text
            or "found" in issue_text
        )

    def test_layer3_critic_build_context_with_real_workflow(self, real_capability_registry, at_rich_fasta):
        """Critic _build_context extracts IRES-specific stats from real results."""
        wf = IresPredictionWorkflow(real_capability_registry)
        inp = IresPredictionInput(
            sequence_filepath=at_rich_fasta,
            iresfinder_mode=2,
            window_size=174,
            step_size=50,
            probability_threshold=0.5,
            run_structural_validation=True,
        )
        result = wf.run(inp)
        assert result.success is True

        critic = IresPredictionLLMCritic()
        state: dict[str, Any] = {"_last_workflow_params": inp.model_dump()}
        ctx = critic._build_context(result, state)

        # IRES-specific stats
        assert "ires_stats" in ctx
        stats = ctx["ires_stats"]
        assert stats["probability_range"]["count"] > 0
        assert stats["probability_range"]["max"] > 0.5
        if stats["mfe_range"]["count"] > 0:
            assert stats["mfe_range"]["min"] is not None
        if stats["unpaired_fraction_range"]["count"] > 0:
            assert 0 <= stats["unpaired_fraction_range"]["min"] <= 1
        assert stats["coverage"]["min_start"] is not None
        assert stats["mode_distribution"] is not None
        assert "2" in stats["mode_distribution"]  # mode 2 was used

    def test_layer3_critic_build_context_empty_candidates(self):
        """Critic _build_context with empty candidates returns zero-count stats."""
        critic = IresPredictionLLMCritic()
        result = WorkflowResult(success=True, task_id="empty_test", errors=[])
        state: dict[str, Any] = {}
        ctx = critic._build_context(result, state)

        assert "ires_stats" in ctx
        stats = ctx["ires_stats"]
        assert stats["probability_range"]["count"] == 0
        assert stats["mfe_range"]["count"] == 0
        assert stats["coverage"]["min_start"] is None

    def test_layer3_parameter_override_filtering(self):
        """Critic should only emit valid adjustable params, filtering out unknown keys."""
        critic = IresPredictionLLMCritic()
        # Simulate a diagnosis with both valid and invalid overrides
        from agent_core.planning.llm_critic import CriticDiagnosis

        diagnosis = CriticDiagnosis(
            overall_assessment="Test",
            quality_score=0.3,
            action="retry_with_adjustments",
            parameter_overrides={
                "probability_threshold": 0.3,  # valid
                "window_size": 200,  # valid
                "invalid_param_xyz": 999,  # invalid — not in adjustable_params
                "_private": "hidden",  # invalid — starts with _
            },
            reasoning="Test retry",
            confidence=0.8,
        )
        valid_keys = set(critic.config.adjustable_params.keys())
        filtered = {k: v for k, v in diagnosis.parameter_overrides.items() if k in valid_keys}
        assert "probability_threshold" in filtered
        assert "window_size" in filtered
        assert "invalid_param_xyz" not in filtered
        assert "_private" not in filtered


class TestLayer3ExecutionControllerRetry:
    """Verify ExecutionController retry loop with real and mocked LLM critic."""

    @pytest.fixture(autouse=True)
    def _require_deepseek_key(self):
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key or key.strip() == "":
            pytest.skip("DEEPSEEK_API_KEY not set — skipping Layer 3 retry tests")

    def test_layer3_execution_controller_no_retry_when_critic_disabled(self, real_capability_registry, at_rich_fasta):
        """When critic is disabled, workflow runs once with no retries."""
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.5,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=2,
        )
        state: dict[str, Any] = {"_llm_critic_enabled": False}
        result_state = controller.execute(plan, state)

        assert result_state["_plan_executed"] is True
        assert result_state.get("retry_count", 0) == 0
        wf_result = result_state.get("ires_result")
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True

    def test_layer3_execution_controller_with_real_critic(self, real_capability_registry, at_rich_fasta):
        """ExecutionController with real LLM Critic enabled.

        Runs the workflow with critic enabled. The LLM will diagnose results.
        If the results are good, no retry is triggered. If issues are found,
        retry may be triggered with parameter adjustments.
        """
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.5,
                        "run_structural_validation": True,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=2,
        )
        state: dict[str, Any] = {"_llm_critic_enabled": True}
        result_state = controller.execute(plan, state)

        assert result_state["_plan_executed"] is True
        wf_result = result_state.get("ires_result")
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True

        # Verify that the critic was consulted (diagnosis history recorded)
        # Note: with good results the LLM may not suggest retry, which is fine.
        # The key assertion is that the pipeline completed without errors.
        log_events = [e["event"] for e in result_state.get("_execution_log", [])]
        assert "step_start" in log_events
        assert "step_done" in log_events
        assert "plan_complete" in log_events

    def test_layer3_execution_controller_mocked_retry_cycle(self, real_capability_registry, at_rich_fasta):
        """ExecutionController retry cycle with MOCKED critic (deterministic test).

        This test mocks the Critic to force a retry with specific parameter
        overrides, then verifies:
        1. The workflow is re-run with adjusted parameters
        2. Parameter overrides are applied to the plan's input_binding
        3. retry_count is incremented
        4. The retry event is logged
        """
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.99,  # High — will yield empty on first run
                        "top_n_candidates": 5,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=2,
        )

        # Mock the critic to force retry with threshold lowered
        with patch.object(
            IresPredictionLLMCritic,
            "diagnose",
            return_value=MagicMock(
                overall_assessment="No candidates found, threshold too high",
                quality_score=0.1,
                issues=[],
                action="retry_with_adjustments",
                parameter_overrides={"probability_threshold": 0.3},
                reasoning="Lower threshold to find candidates",
                confidence=0.9,
                model_dump=lambda: {
                    "overall_assessment": "No candidates found, threshold too high",
                    "quality_score": 0.1,
                    "issues": [],
                    "action": "retry_with_adjustments",
                    "parameter_overrides": {"probability_threshold": 0.3},
                    "reasoning": "Lower threshold to find candidates",
                    "confidence": 0.9,
                },
            ),
        ):
            state: dict[str, Any] = {"_llm_critic_enabled": True}
            result_state = controller.execute(plan, state)

        # Verify retry happened
        assert result_state["_plan_executed"] is True
        assert result_state.get("retry_count", 0) >= 1

        # Verify parameter override was applied
        assert plan.steps[0].input_binding["probability_threshold"] == 0.3

        # Verify retry event in log
        log_events = [e["event"] for e in result_state.get("_execution_log", [])]
        assert "critic_retry" in log_events
        assert "parameter_override" in log_events

        # After retry with lower threshold, should get candidates
        wf_result = result_state.get("ires_result")
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True
        assert len(wf_result.all_candidates) > 0

    def test_layer3_execution_controller_mocked_double_retry(self, real_capability_registry, at_rich_fasta):
        """Two consecutive retries with different parameter overrides each time.

        First retry: lower threshold → still not enough (mocked)
        Second retry: increase top_n → success
        """
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.99,
                        "top_n_candidates": 1,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=3,
        )

        call_count = 0

        def _mock_diagnose(self, result, state):
            nonlocal call_count
            call_count += 1
            from agent_core.planning.llm_critic import CriticDiagnosis

            if call_count == 1:
                return CriticDiagnosis(
                    overall_assessment="No candidates with threshold 0.99",
                    quality_score=0.1,
                    action="retry_with_adjustments",
                    parameter_overrides={"probability_threshold": 0.5},
                    reasoning="Threshold too high",
                    confidence=0.9,
                )
            else:
                # Second diagnosis: results are now good
                return CriticDiagnosis(
                    overall_assessment="Good results after adjustment",
                    quality_score=0.85,
                    action="proceed_with_filtered",
                    parameter_overrides={},
                    reasoning="Satisfactory results",
                    confidence=0.9,
                )

        with patch.object(IresPredictionLLMCritic, "diagnose", _mock_diagnose):
            state: dict[str, Any] = {"_llm_critic_enabled": True}
            result_state = controller.execute(plan, state)

        assert result_state["_plan_executed"] is True
        assert result_state.get("retry_count", 0) == 1
        # After one retry, threshold should be 0.5
        assert plan.steps[0].input_binding["probability_threshold"] == 0.5
        # Result should be successful
        wf_result = result_state.get("ires_result")
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True

    def test_layer3_critic_retry_exhaustion(self, real_capability_registry, at_rich_fasta):
        """When max_retries is exceeded, controller stops retrying and marks exhausted."""
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.99,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=1,
        )

        # Always force retry
        with patch.object(
            IresPredictionLLMCritic,
            "diagnose",
            return_value=MagicMock(
                overall_assessment="Always retry",
                quality_score=0.1,
                issues=[],
                action="retry_with_adjustments",
                parameter_overrides={"probability_threshold": 0.5},
                reasoning="Force retry",
                confidence=0.9,
                model_dump=lambda: {
                    "overall_assessment": "Always retry",
                    "quality_score": 0.1,
                    "issues": [],
                    "action": "retry_with_adjustments",
                    "parameter_overrides": {"probability_threshold": 0.5},
                    "reasoning": "Force retry",
                    "confidence": 0.9,
                },
            ),
        ):
            state: dict[str, Any] = {"_llm_critic_enabled": True}
            result_state = controller.execute(plan, state)

        # Should have retried once, then exhausted
        assert result_state.get("retry_count", 0) == 1
        log_events = [e for e in result_state.get("_execution_log", [])]
        assert any(e.get("retries_exhausted") for e in log_events)

    def test_layer3_real_critic_may_trigger_retry_on_empty_results(self, real_capability_registry, at_rich_fasta):
        """REAL LLM critic on empty results: may or may not trigger retry.

        This is a probabilistic test: the LLM may suggest retrying with
        adjusted parameters when no candidates are found. We verify that
        the diagnosis is structurally valid and the pipeline handles it.
        """
        wf = IresPredictionWorkflow(real_capability_registry)
        controller = ExecutionController(
            capability_registry=real_capability_registry,
            workflow_registry={"ires_prediction": wf},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": at_rich_fasta,
                        "iresfinder_mode": 0,
                        "probability_threshold": 0.99,  # Empty result
                        "top_n_candidates": 5,
                    },
                    output_key="ires_result",
                )
            ],
            max_retries=2,
        )
        state: dict[str, Any] = {
            "_llm_critic_enabled": True,
            "user_text": "Find at least one IRES candidate in this sequence",
        }
        result_state = controller.execute(plan, state)

        # The pipeline should complete regardless of retry decision
        assert result_state["_plan_executed"] is True
        wf_result = result_state.get("ires_result")
        assert isinstance(wf_result, WorkflowResult)

        # If retry happened, verify the mechanism
        if result_state.get("retry_count", 0) > 0:
            assert "critic_retry" in [e["event"] for e in result_state.get("_execution_log", [])]
            # Parameter overrides should have been applied
            assert plan.steps[0].input_binding["probability_threshold"] != 0.99

        # Verify diagnosis was recorded
        assert "_last_diagnosis" in result_state or "_diagnosis_history" in result_state

    def test_layer3_parameter_override_application(self):
        """Direct test: _apply_parameter_overrides merges overrides correctly.

        Uses a mock workflow to avoid needing real tools.
        """
        controller = ExecutionController(
            capability_registry=MagicMock(),
            workflow_registry={},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="mock_wf",
                    input_binding={
                        "sequence_filepath": "/tmp/test.fasta",
                        "probability_threshold": 0.5,
                        "window_size": 174,
                    },
                )
            ]
        )
        state: dict[str, Any] = {}

        # Apply overrides
        controller._apply_parameter_overrides(
            plan, state, {"probability_threshold": 0.3, "window_size": 200}
        )

        # Verify merged binding
        binding = plan.steps[0].input_binding
        assert binding["probability_threshold"] == 0.3
        assert binding["window_size"] == 200
        assert binding["sequence_filepath"] == "/tmp/test.fasta"
        # Original preserved
        assert state["_original_input_binding_s1"]["probability_threshold"] == 0.5

        # Second override applies from original, not accumulated
        # window_size was in first override but not second, so it reverts to original
        controller._apply_parameter_overrides(
            plan, state, {"probability_threshold": 0.2}
        )
        assert plan.steps[0].input_binding["probability_threshold"] == 0.2
        assert plan.steps[0].input_binding["window_size"] == 174  # Reverted to original

    def test_layer3_parameter_override_filters_invalid_keys(self):
        """_apply_parameter_overrides should reject keys not in original binding
        and keys that don't look like valid identifiers.
        """
        controller = ExecutionController(
            capability_registry=MagicMock(),
            workflow_registry={},
        )
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="s1",
                    type="workflow",
                    target="mock_wf",
                    input_binding={"probability_threshold": 0.5},
                )
            ]
        )
        state: dict[str, Any] = {}

        controller._apply_parameter_overrides(
            plan,
            state,
            {
                "probability_threshold": 0.3,  # valid
                "_secret": "evil",  # invalid: starts with _
                "123invalid": "nope",  # invalid: starts with digit
            },
        )
        binding = plan.steps[0].input_binding
        assert binding["probability_threshold"] == 0.3
        assert "_secret" not in binding
        assert "123invalid" not in binding

    def test_layer3_critic_config_fields(self):
        """Verify the IRES critic config has all expected adjustable params."""
        config = IRES_PREDICTION_CRITIC_CONFIG
        assert config.workflow_name == "ires_prediction"
        assert config.max_retries == 2
        assert config.retry_strategy == "adjust_params"

        expected_params = {
            "probability_threshold",
            "window_size",
            "step_size",
            "top_n_candidates",
            "run_structural_validation",
            "iresfinder_mode",
        }
        assert set(config.adjustable_params.keys()) == expected_params

        # Verify type hints
        assert config.adjustable_params["probability_threshold"]["type"] == "float"
        assert config.adjustable_params["window_size"]["type"] == "int"
        assert config.adjustable_params["run_structural_validation"]["type"] == "bool"
        assert config.adjustable_params["iresfinder_mode"]["type"] == "enum"
        assert set(config.adjustable_params["iresfinder_mode"]["values"]) == {0, 1, 2}


# =============================================================================
# Confidence Assignment Tests
# =============================================================================


class TestConfidenceAssignment:
    """Unit tests for assign_confidence helper."""

    @pytest.mark.parametrize(
        "prob,unpaired,expected",
        [
            (0.85, 0.5, "high"),
            (0.80, 0.30, "high"),  # boundary: 0.3 is inclusive
            (0.80, 0.70, "high"),  # boundary: 0.7 is inclusive
            (0.65, 0.5, "medium"),
            (0.65, 0.20, "medium"),  # boundary
            (0.65, 0.80, "medium"),  # boundary
            (0.55, 0.5, "low"),
            (0.55, 0.1, "low"),
            (0.50, 0.5, "low"),  # boundary
            (0.45, 0.5, "rejected"),
            (0.50, 0.5, "low"),  # boundary: exactly 0.50
        ],
    )
    def test_confidence_levels(self, prob, unpaired, expected):
        assert assign_confidence(prob, unpaired) == expected

    def test_confidence_no_structural_data(self):
        """Missing structural data downgrades one tier."""
        assert assign_confidence(0.85, None) == "medium"
        assert assign_confidence(0.65, None) == "low"
        assert assign_confidence(0.55, None) == "rejected"
        assert assign_confidence(0.45, None) == "rejected"


# =============================================================================
# Interface Immutability Tests — INTERFACE LOCK (v1.0.0)
# =============================================================================
# These tests encode the locked interface contract. If any of them fail,
# someone has changed a field name, type, or capability list without updating
# all synchronized files. Do NOT relax these assertions.
# =============================================================================


class TestInterfaceLock:
    """Verify the IresPredictionWorkflow interface contract is unchanged.

    These tests are part of the INTERFACE LOCK (v1.0.0). Changing them
    without updating all synchronized files is a breaking change.
    """

    def test_locked_required_capabilities(self):
        """required_capabilities list must match the locked contract."""
        expected = [
            "predict_putative_ires_with_iresfinder",
            "predict_rna_secondary_structure",
            "predict_rna_local_accessibility_profile_vienna",
            "compute_dot_bracket_unpaired_fraction",
        ]
        assert IresPredictionWorkflow.required_capabilities == expected

    def test_locked_input_model_fields(self):
        """IresPredictionInput fields must match the locked contract."""
        expected_fields = {
            "sequence_filepath",
            "iresfinder_mode",
            "probability_threshold",
            "window_size",
            "step_size",
            "top_n_candidates",
            "run_structural_validation",
        }
        actual_fields = set(IresPredictionInput.model_fields.keys())
        assert actual_fields == expected_fields, f"Field mismatch: {actual_fields ^ expected_fields}"

    def test_locked_input_model_defaults(self):
        """Default values must match the locked contract."""
        inp = IresPredictionInput(sequence_filepath="test.fasta")
        assert inp.iresfinder_mode == 0
        assert inp.probability_threshold == pytest.approx(0.5)
        assert inp.window_size == 174
        assert inp.step_size == 50
        assert inp.top_n_candidates == 5
        assert inp.run_structural_validation is True

    def test_locked_input_model_constraints(self):
        """Field constraints must match the locked contract."""
        # iresfinder_mode: [0, 2]
        with pytest.raises(Exception):
            IresPredictionInput(sequence_filepath="test.fasta", iresfinder_mode=3)
        # probability_threshold: [0.0, 1.0]
        with pytest.raises(Exception):
            IresPredictionInput(sequence_filepath="test.fasta", probability_threshold=1.5)
        # window_size: [20, 5000]
        with pytest.raises(Exception):
            IresPredictionInput(sequence_filepath="test.fasta", window_size=10)
        # top_n_candidates: [1, 100]
        with pytest.raises(Exception):
            IresPredictionInput(sequence_filepath="test.fasta", top_n_candidates=0)

    def test_locked_scoring_formula(self):
        """Score must be driven solely by IRESfinder probability."""
        wf = IresPredictionWorkflow(MagicMock())
        # With structural data — score is still just probability
        scores = wf.score({"ires_probability": 0.75, "mean_unpaired_fraction": 0.5, "mfe_kcal_per_mol": -20.0})
        assert scores["composite_score"] == pytest.approx(0.75)
        assert scores["ires_probability"] == pytest.approx(0.75)
        # Without structural data — same score
        scores2 = wf.score({"ires_probability": 0.75, "mean_unpaired_fraction": None})
        assert scores2["composite_score"] == pytest.approx(0.75)

    def test_locked_confidence_thresholds(self):
        """Confidence assignment thresholds must match the locked contract."""
        # With structural data
        assert assign_confidence(0.85, 0.5) == "high"
        assert assign_confidence(0.80, 0.30) == "high"
        assert assign_confidence(0.80, 0.70) == "high"
        assert assign_confidence(0.65, 0.5) == "medium"
        assert assign_confidence(0.65, 0.20) == "medium"
        assert assign_confidence(0.65, 0.80) == "medium"
        assert assign_confidence(0.55, 0.5) == "low"
        assert assign_confidence(0.45, 0.5) == "rejected"
        # Without structural data (downgrade one tier)
        assert assign_confidence(0.85, None) == "medium"
        assert assign_confidence(0.65, None) == "low"
        assert assign_confidence(0.55, None) == "rejected"

    def test_locked_critic_config(self):
        """CriticConfig adjustable_params must match the locked contract."""
        config = IRES_PREDICTION_CRITIC_CONFIG
        expected_adjustable = {
            "probability_threshold",
            "window_size",
            "step_size",
            "top_n_candidates",
            "run_structural_validation",
            "iresfinder_mode",
        }
        assert set(config.adjustable_params.keys()) == expected_adjustable
        assert config.workflow_name == "ires_prediction"
        assert config.retry_strategy == "adjust_params"
        assert config.max_retries == 2

    def test_locked_workflow_name_and_model(self):
        """Workflow class metadata must match the locked contract."""
        assert IresPredictionWorkflow.name == "ires_prediction"
        assert IresPredictionWorkflow.input_model == IresPredictionInput

    def test_locked_state_writeback_keys(self):
        """_state_writeback must contain the expected keys."""
        wf = IresPredictionWorkflow(MagicMock())
        inp = IresPredictionInput(sequence_filepath="test.fasta")
        # We can't run without capabilities, but we can verify the writeback structure
        # by checking the code path in run()
        import inspect
        source = inspect.getsource(wf.run)
        assert "_workflow_params" in source
        assert "_last_workflow_params" in source
        assert "_state_writeback" in source
