"""Comprehensive integration test for mrna_cds_design across all layers.

Covers:
  - Layer 0: Direct tool invocation (CPU + GPU microservices)
  - Layer 1: Capability registry with validation and writebacks
  - Layer 2: Full MrnaCdsDesignWorkflow (generate → evaluate → score → rank)
  - Layer 3: Live LLM Critic diagnosis (requires --live-llm + DEEPSEEK_API_KEY)
  - Layer 3: End-to-end retry with ExecutionController + real Critic

Run:
    # All non-LLM tests (Layers 0-2)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_mrna_cds_design_comprehensive.py -v

    # Include live LLM tests (Layers 3, requires DeepSeek API)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_mrna_cds_design_comprehensive.py -v --live-llm
"""

from __future__ import annotations

import math
import time
from typing import Any
from unittest.mock import patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_protein_sequence() -> str:
    return "MKTLLILTVFGITMLLAVLAQG"  # 22 aa ≈ 66 nt CDS


@pytest.fixture(scope="module")
def test_cds_sequence() -> str:
    return "AUG" * 30  # 90 nt, valid CDS



@pytest.fixture(scope="module")
def protein_filepath(test_protein_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_protein_sequence, prefix="test_protein")


@pytest.fixture(scope="module")
def cds_filepath(test_cds_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_cds_sequence, prefix="test_cds")
# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation
# ═══════════════════════════════════════════════════════════════════════


class TestLayer0CpuTools:
    """Layer 0 tests for CPU-based tools."""

    def test_lineardesign(self, executor, protein_filepath):
        """LinearDesign on CPU (port 8014)."""
        result = executor.run_tool(
            "design_mrna_cds_with_lineardesign",
            filepath=protein_filepath,
            lambda_value=1.0,
        )
        assert result.success, f"LinearDesign failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from LinearDesign"
        assert "cai_score" in result.artifacts.get("result", {})

    def test_viennarna_fold(self, executor, cds_filepath):
        """ViennaRNA fold on CPU (port 8003)."""
        result = executor.run_tool(
            "predict_rna_secondary_structure", filepath=cds_filepath
        )
        assert result.success, f"ViennaRNA fold failed: {result.error}"
        struct = result.artifacts.get("result", {}).get("structure", "")
        assert len(struct) > 0, "Empty structure from ViennaRNA"
        assert "mfe_kcal_per_mol" in result.artifacts.get("result", {})

    def test_linearfold(self, executor, cds_filepath):
        """LinearFold fallback on CPU (port 8015)."""
        result = executor.run_tool(
            "predict_rna_secondary_structure_with_linearfold",
            filepath=cds_filepath,
        )
        assert result.success, f"LinearFold failed: {result.error}"
        struct = result.artifacts.get("result", {}).get("structure", "")
        assert len(struct) > 0, "Empty structure from LinearFold"
        assert "mfe" in result.artifacts.get("result", {})

    def test_gc_content(self, executor, cds_filepath):
        """GC content on CPU (port 8020)."""
        result = executor.run_tool(
            "compute_rna_sequence_gc_content", filepath=cds_filepath
        )
        assert result.success, f"GC content failed: {result.error}"
        gc = result.artifacts.get("result", {}).get("gc_content")
        assert gc is not None, "Missing gc_content"
        assert 0.0 <= gc <= 1.0, f"GC content out of range: {gc}"

    def test_unpaired_fraction(self, executor):
        """Dot-bracket unpaired fraction on CPU (port 8020)."""
        from agent_core.file_manager import save_text_file

        struct_fp = save_text_file("(((...)))" * 10, prefix="test_struct", suffix=".db")
        result = executor.run_tool(
            "compute_dot_bracket_unpaired_fraction", filepath=struct_fp
        )
        assert result.success, f"Unpaired fraction failed: {result.error}"
        uf = result.artifacts.get("result", {}).get("unpaired_fraction")
        assert uf is not None, "Missing unpaired_fraction"
        assert 0.0 <= uf <= 1.0, f"Unpaired fraction out of range: {uf}"

    def test_cai(self, executor, cds_filepath):
        """CAI computation — pure Python, no microservice."""
        result = executor.run_tool(
            "compute_cai_for_cds_sequence",
            filepath=cds_filepath,
            species="Homo sapiens",
        )
        assert result.success, f"CAI failed: {result.error}"
        cai = result.artifacts.get("result", {}).get("cai_score")
        assert cai is not None, "Missing cai_score"
        assert 0.0 <= cai <= 1.0, f"CAI out of range: {cai}"


@pytest.mark.integration
class TestLayer0GpuTools:
    """Layer 0 tests for GPU-based tools (require NVIDIA GPU + CUDA)."""

    def test_rnarl(self, executor, protein_filepath):
        """RNARL on GPU (port 8008)."""
        result = executor.run_tool(
            "design_mrna_cds_with_rnarl",
            filepath=protein_filepath,
            model_type="Homo sapiens mRNA",
        )
        assert result.success, f"RNARL failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from RNARL"

    def test_gemorna(self, executor, protein_filepath):
        """GEMORNA on GPU (port 8004)."""
        result = executor.run_tool(
            "design_mrna_cds_with_gemorna", filepath=protein_filepath
        )
        assert result.success, f"GEMORNA failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from GEMORNA"

    def test_rnastop(self, executor, cds_filepath):
        """RNASTOP on GPU (port 8009)."""
        result = executor.run_tool(
            "predict_mrna_stability_with_rnastop", filepath=cds_filepath
        )
        assert result.success, f"RNASTOP failed: {result.error}"
        stab = result.artifacts.get("result", {}).get("overall_stability")
        assert stab is not None, "Missing overall_stability"
        assert 0.0 <= stab <= 1.0, f"Stability out of range: {stab}"


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════


class TestLayer1Capabilities:
    """Layer 1 tests: Capability.invoke() with validation and writebacks."""

    def test_lineardesign_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_lineardesign")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"filepath": protein_filepath, "lambda_value": 1.0}, state=state
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("generated_sequence"), "Missing generated_sequence"
        # Verify writeback
        assert "tool_results" in state, "Missing tool_results writeback"
        assert "design_mrna_cds_with_lineardesign" in state["tool_results"]

    @pytest.mark.integration
    def test_rnarl_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_rnarl")
        result = cap.invoke(
            {"filepath": protein_filepath, "model_type": "Homo sapiens mRNA"},
            state={},
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("generated_sequence"), "Missing generated_sequence"

    @pytest.mark.integration
    def test_gemorna_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_gemorna")
        result = cap.invoke({"filepath": protein_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("generated_sequence"), "Missing generated_sequence"

    def test_gc_capability(self, registry, cds_filepath):
        cap = registry.get("compute_rna_sequence_gc_content")
        result = cap.invoke({"filepath": cds_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("gc_content") is not None, "Missing gc_content"

    def test_fold_capability(self, registry, cds_filepath):
        cap = registry.get("predict_rna_secondary_structure")
        result = cap.invoke({"filepath": cds_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("structure"), "Missing structure"

    @pytest.mark.integration
    def test_rnastop_capability(self, registry, cds_filepath):
        cap = registry.get("predict_mrna_stability_with_rnastop")
        result = cap.invoke({"filepath": cds_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("overall_stability") is not None, (
            "Missing overall_stability"
        )

    def test_cai_capability(self, registry, cds_filepath):
        cap = registry.get("compute_cai_for_cds_sequence")
        result = cap.invoke(
            {"filepath": cds_filepath, "species": "Homo sapiens"}, state={}
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("cai_score") is not None, "Missing cai_score"

    def test_u_content_capability(self, registry, cds_filepath):
        cap = registry.get("compute_rna_sequence_u_content")
        result = cap.invoke({"filepath": cds_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("u_fraction") is not None, "Missing u_fraction"
        assert result.output.get("u_count") is not None, "Missing u_count"


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestLayer2Workflow:
    """Layer 2 tests: MrnaCdsDesignWorkflow end-to-end."""

    @pytest.fixture(scope="class")
    def workflow(self, registry):
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignWorkflow

        return MrnaCdsDesignWorkflow(registry)

    def test_workflow_lineardesign_only(self, workflow, test_protein_sequence):
        """Run workflow with LinearDesign only (fast, CPU)."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="lineardesign",
            lambda_value=1.0,
            cai_species="Homo sapiens",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        assert len(result.all_candidates) >= 1, "No candidates produced"

        best = result.best_candidate
        assert len(best.sequence) > 0, "Empty best sequence"
        assert "total_score" in best.scores, "Missing total_score"

        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("gc_content") is not None, "Missing GC"
        assert mb.get("u_fraction") is not None, "Missing U fraction"
        assert mb.get("mfe_kcal_per_mol") is not None, "Missing MFE"
        assert mb.get("cai_score") is not None, "Missing CAI"

    def test_workflow_all_tools(self, workflow, test_protein_sequence):
        """Run workflow with all tools (CPU + GPU)."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="all",
            cai_species="Homo sapiens",
        )
        start = time.perf_counter()
        result = workflow.run(inp)
        elapsed = time.perf_counter() - start

        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        # Should have up to 6 candidates (4 LinearDesign + 1 RNARL + 1 GEMORNA)
        assert len(result.all_candidates) >= 3, (
            f"Too few candidates: {len(result.all_candidates)}"
        )

        # Verify ranking: candidates sorted by total_score descending
        scores = [c.scores.get("total_score", 0) for c in result.all_candidates]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], "Candidates not sorted by score"

        # Verify summary
        assert result.summary, "Empty summary"
        assert "candidates=" in result.summary

        print(f"\n    Workflow 'all' completed in {elapsed:.1f}s")
        print(f"    Candidates: {len(result.all_candidates)}")
        print(f"    Best score: {result.best_candidate.scores.get('total_score')}")

    def test_workflow_rnarl_only(self, workflow, test_protein_sequence):
        """Run workflow with RNARL only (GPU)."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="rnarl",
            model_type="Homo sapiens mRNA",
            cai_species="Homo sapiens",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) >= 1, "No candidates"
        assert result.all_candidates[0].source.startswith("cds_design:rnarl")

    def test_workflow_gemorna_only(self, workflow, test_protein_sequence):
        """Run workflow with GEMORNA only (GPU)."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="gemorna",
            cai_species="Homo sapiens",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) >= 1, "No candidates"
        assert result.all_candidates[0].source.startswith("cds_design:gemorna")

    def test_workflow_different_species(self, workflow, test_protein_sequence):
        """Run workflow with a different CAI species."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="lineardesign",
            lambda_value=1.0,
            cai_species="ecoli",  # built-in alias for Escherichia coli K-12
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None
        mb = result.best_candidate.metadata.get("metrics_bundle", {})
        assert mb.get("cai_score") is not None

    def test_workflow_state_writeback(self, workflow, test_protein_sequence):
        """Verify workflow result has _state_writeback for controller."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput

        inp = MrnaCdsDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="lineardesign",
            lambda_value=1.0,
        )
        result = workflow.run(inp)
        assert result.success
        assert hasattr(result, "_state_writeback"), "Missing _state_writeback"
        wb = getattr(result, "_state_writeback", {})
        assert "_workflow_params" in wb, "Missing _workflow_params in writeback"


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Live LLM Critic — Real DeepSeek API
# ═══════════════════════════════════════════════════════════════════════


def _make_low_quality_result() -> "WorkflowResult":
    """Build a WorkflowResult with deliberately poor CAI to trigger critic retry."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, cai in enumerate([0.28, 0.30, 0.32]):
        c = Candidate(
            sequence="AUG" * 50,
            sequence_type="mrna",
            source=f"lineardesign_lambda{i}",
            metadata={
                "metrics_bundle": {
                    "cai_score": cai,
                    "mfe_kcal_per_mol": -150.0,
                    "gc_content": 0.52,
                    "sequence_length": 150,
                    "mfe_per_nt": -1.0,
                    "unpaired_fraction": 0.3,
                }
            },
        )
        c.scores = {"total_score": -150.0 + 50 * math.log(cai)}
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_low_cai",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low CAI test",
        errors=[],
    )


def _make_good_quality_result() -> "WorkflowResult":
    """Build a WorkflowResult with good CAI."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, cai in enumerate([0.82, 0.85, 0.88]):
        c = Candidate(
            sequence="AUG" * 50,
            sequence_type="mrna",
            source=f"lineardesign_lambda{i}",
            metadata={
                "metrics_bundle": {
                    "cai_score": cai,
                    "mfe_kcal_per_mol": -80.0,
                    "gc_content": 0.52,
                    "sequence_length": 150,
                    "mfe_per_nt": -0.53,
                    "unpaired_fraction": 0.4,
                }
            },
        )
        c.scores = {"total_score": -80.0 + 50 * math.log(cai)}
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_good_cai",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Good CAI test",
        errors=[],
    )


@pytest.mark.live_llm
class TestLiveLLMCritic:
    """Live tests using real DeepSeek API for Critic diagnosis."""

    def test_critic_diagnoses_low_cai(self):
        """Real LLM should detect low CAI and recommend parameter changes."""
        from agent_core.planning.llm_critic import CriticDiagnosis
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        critic = MrnaCdsDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0},
            "user_text": "Design mRNA CDS for human expression with high CAI",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.5, (
            f"Expected low quality score for bad results, got {diagnosis.quality_score}"
        )
        assert len(diagnosis.issues) > 0, "Expected at least one issue"
        # At least one issue should mention CAI
        cai_issues = [
            i
            for i in diagnosis.issues
            if "cai" in i.category.lower() or "CAI" in i.description.upper()
        ]
        assert len(cai_issues) > 0, "Expected CAI-related issue"
        # Should recommend retry
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
        ), f"Expected retry action, got {diagnosis.action}"
        assert len(diagnosis.parameter_overrides) > 0, "Expected parameter overrides"

    def test_critic_should_retry_low_cai(self):
        """should_retry must return True for low-quality results."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        critic = MrnaCdsDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {"design_tool": "all", "lambda_value": 0.0},
            "user_text": "Design mRNA CDS for human expression with high CAI",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is True, "Expected should_retry=True for low CAI"
        assert "_parameter_overrides" in state, "Missing _parameter_overrides"
        assert len(state["_parameter_overrides"]) > 0

    def test_critic_prompt_contains_evaluation_dimensions(self):
        """Verify the diagnosis prompt includes domain-specific criteria."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        critic = MrnaCdsDesignLLMCritic()
        result = _make_low_quality_result()
        ctx = critic._build_context(result, {})
        messages = critic._build_diagnosis_prompt(ctx)

        system_text = messages[0][1]  # ("system", text)
        assert "CAI" in system_text, "Missing CAI in evaluation criteria"
        assert "MFE" in system_text, "Missing MFE in evaluation criteria"
        assert "lambda" in system_text.lower(), "Missing lambda in criteria"
        assert "design_tool" in system_text, "Missing design_tool in adjustable params"

        user_text = messages[1][1]  # ("user", text)
        assert "mrna_cds_design" in user_text, "Missing workflow name"
        assert "lineardesign_lambda0" in user_text, "Missing candidate source"

    def test_diagnosis_records_history(self):
        """Verify diagnose appends to _diagnosis_history."""
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        critic = MrnaCdsDesignLLMCritic()
        result = _make_low_quality_result()
        state: dict[str, Any] = {}

        critic.diagnose(result, state)

        assert "_diagnosis_history" in state, "Missing _diagnosis_history"
        assert len(state["_diagnosis_history"]) == 1


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: End-to-End Retry — ExecutionController + Real Critic
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
class TestEndToEndRetry:
    """End-to-end tests: ExecutionController + real Critic + parameter overrides."""

    def test_controller_triggers_retry_with_real_critic(self):
        """Full flow: controller executes workflow, critic triggers retry, params overridden.

        This test uses a mock workflow that always returns low-CAI results,
        but a REAL Critic (calling DeepSeek API) that diagnoses the problem
        and recommends parameter changes. The controller then applies the
        overrides and retries until max_retries is reached.
        """
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        for name in [
            "design_mrna_cds_with_lineardesign",
            "design_mrna_cds_with_rnarl",
            "design_mrna_cds_with_gemorna",
            "predict_rna_secondary_structure",
            "predict_rna_secondary_structure_with_linearfold",
            "compute_rna_sequence_gc_content",
            "compute_dot_bracket_unpaired_fraction",
            "predict_mrna_stability_with_rnastop",
            "compute_cai_for_cds_sequence",
        ]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="cds",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={
                        "protein_sequence": "MKTLLILTVFGITMLLAVLAQG",
                        "design_tool": "all",
                    },
                    output_key="cds_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "mrna_cds_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "mrna_cds_design":
                return MrnaCdsDesignLLMCritic()
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        # Should have been called 3 times: initial + 2 retries
        assert call_count == 3, f"Expected 3 calls, got {call_count}"
        assert final_state.get("retry_count") == 2, (
            f"Expected retry_count=2, got {final_state.get('retry_count')}"
        )
        assert "_critic_should_retry" in final_state

        # Verify parameter overrides were applied
        log = final_state.get("_execution_log", [])
        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) > 0, "No parameter_override events in log"

        # Verify plan's input_binding was modified
        final_binding = plan.steps[0].input_binding
        assert "protein_sequence" in final_binding, "Missing protein_sequence"
        # At least one new parameter should have been added by critic
        assert len(final_binding) >= 2, f"Expected more params, got {final_binding}"

        # Verify retries_exhausted is recorded
        complete_events = [e for e in log if e.get("event") == "plan_complete"]
        assert len(complete_events) > 0, "No plan_complete events"
        assert any(
            e.get("retries_exhausted") for e in complete_events
        ), "Expected retries_exhausted flag"

    def test_critic_disabled_flag_respected(self):
        """When _llm_critic_enabled=False, critic should not trigger retry."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflows.mrna_cds_design import MrnaCdsDesignLLMCritic

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        for name in ["design_mrna_cds_with_lineardesign"]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="cds",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKLTEST"},
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "mrna_cds_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "mrna_cds_design":
                return MrnaCdsDesignLLMCritic()
            return None

        # Critic disabled via state flag
        initial_state = {"_llm_critic_enabled": False}

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, initial_state)

        # Should only be called once (no retries)
        assert call_count == 1, f"Expected 1 call with critic disabled, got {call_count}"
        assert final_state.get("retry_count", 0) == 0
