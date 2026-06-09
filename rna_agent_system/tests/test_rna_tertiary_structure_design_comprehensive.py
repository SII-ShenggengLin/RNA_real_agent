"""Comprehensive integration test for rna_tertiary_structure_design across all layers.

Covers:
  - Layer 0: Direct tool invocation (CPU + GPU microservices)
  - Layer 1: Capability registry with validation and writebacks
  - Layer 2: Full RnaTertiaryStructureDesignWorkflow (generate → evaluate → score → rank)
  - Layer 3: ExecutionController integration (progress callback, execution log)
  - Layer 3: Live LLM Critic diagnosis (requires --live-llm + DEEPSEEK_API_KEY)
  - Layer 3: End-to-end retry with ExecutionController + real Critic

Run:
    # All non-LLM tests (Layers 0-3 minus live LLM)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_rna_tertiary_structure_design_comprehensive.py -v

    # Include live LLM tests (Layers 3 live, requires DeepSeek API)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_rna_tertiary_structure_design_comprehensive.py -v --live-llm
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_pdb_path() -> str:
    """Path to a small RNA PDB structure for RhoDesign testing."""
    return "external_repos/RhoDesign/example/2zh6_B.pdb"


@pytest.fixture(scope="module")
def test_pdb_path_ribodiffusion() -> str:
    """Path to a small RNA PDB structure for RiboDiffusion testing."""
    return "external_repos/RiboDiffusion/example/R1107.pdb"



@pytest.fixture(scope="module")
def test_sequence_filepath():
    from agent_core.file_manager import save_sequence

    return save_sequence("GGCCCGGGGCGGUUCGAUUCCGCCUUGGGCCACC", prefix="test_tertiary")
# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation
# ═══════════════════════════════════════════════════════════════════════


class TestLayer0CpuTools:
    """Layer 0 tests for CPU-based tools."""

    def test_viennarna_fold(self, executor, test_sequence_filepath):
        """ViennaRNA fold on CPU (port 8003)."""
        result = executor.run_tool(
            "predict_rna_secondary_structure", filepath=test_sequence_filepath
        )
        assert result.success, f"ViennaRNA fold failed: {result.error}"
        r = result.artifacts.get("result", {})
        struct = r.get("structure", "")
        assert len(struct) > 0, "Empty structure from ViennaRNA"
        assert "mfe_kcal_per_mol" in r, "Missing mfe_kcal_per_mol"

    def test_gc_content(self, executor, test_sequence_filepath):
        """GC content on CPU (port 8020)."""
        result = executor.run_tool(
            "compute_rna_sequence_gc_content", filepath=test_sequence_filepath
        )
        assert result.success, f"GC content failed: {result.error}"
        gc = result.artifacts.get("result", {}).get("gc_content")
        assert gc is not None, "Missing gc_content"
        assert 0.0 <= gc <= 1.0, f"GC content out of range: {gc}"

    def test_structure_alignment(self, executor, test_pdb_path):
        """Structure alignment — pure Python / CPU (no microservice)."""
        result = executor.run_tool(
            "score_structure_alignment",
            reference_pdb_filepath=test_pdb_path,
            predicted_pdb_filepath=test_pdb_path,
            atom_type="C1'",
        )
        assert result.success, f"Structure alignment failed: {result.error}"
        r = result.artifacts.get("result", {})
        rmsd = r.get("rmsd")
        tm = r.get("tm_score")
        assert rmsd is not None, "Missing RMSD"
        assert tm is not None, "Missing TM-score"
        # Same file should align nearly perfectly
        assert rmsd < 0.1, f"RMSD too high for self-alignment: {rmsd}"
        assert tm > 0.99, f"TM-score too low for self-alignment: {tm}"


class TestLayer0GpuTools:
    """Layer 0 tests for GPU-based tools (require NVIDIA GPU + CUDA)."""

    def test_rhodesign(self, executor, test_pdb_path):
        """RhoDesign on GPU (port 8006)."""
        result = executor.run_tool(
            "design_rna_sequence_with_rhodesign",
            pdb_filepath=test_pdb_path,
            temperature=1e-5,
            timeout_seconds=120,
        )
        assert result.success, f"RhoDesign failed: {result.error}"
        r = result.artifacts.get("result", {})
        seq = r.get("predicted_sequence", "")
        assert len(seq) > 0, "Empty sequence from RhoDesign"
        assert "recovery_rate" in r, "Missing recovery_rate"
        assert "output_fasta_filepath" in r, "Missing output_fasta_filepath"

    def test_ribodiffusion(self, executor, test_pdb_path_ribodiffusion):
        """RiboDiffusion on GPU (port 8021)."""
        result = executor.run_tool(
            "design_rna_inverse_fold_with_ribodiffusion",
            pdb_filepath=test_pdb_path_ribodiffusion,
            n_samples=1,
            sampling_steps=10,
        )
        assert result.success, f"RiboDiffusion failed: {result.error}"
        r = result.artifacts.get("result", {})
        seq = r.get("predicted_sequence", "")
        assert len(seq) > 0, "Empty sequence from RiboDiffusion"

    def test_rhofold(self, executor, test_sequence_filepath):
        """RhoFold on GPU (port 8005)."""
        result = executor.run_tool(
            "predict_rna_tertiary_structure_with_rhofold",
            filepath=test_sequence_filepath,
        )
        assert result.success, f"RhoFold failed: {result.error}"
        r = result.artifacts.get("result", {})
        plddt = r.get("mean_plddt")
        assert plddt is not None, "Missing mean_plddt"
        assert plddt > 0, f"Invalid pLDDT: {plddt}"
        assert "pdb_filepath" in r, "Missing pdb_filepath"


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════


class TestLayer1Capabilities:
    """Layer 1 tests: Capability.invoke() with validation and writebacks."""

    def test_rhodesign_capability(self, registry, test_pdb_path):
        cap = registry.get("design_rna_sequence_with_rhodesign")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"pdb_filepath": test_pdb_path, "temperature": 1e-5},
            state=state,
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("predicted_sequence"), "Missing predicted_sequence"
        # Verify writeback
        assert "tool_results" in state, "Missing tool_results writeback"
        assert "design_rna_sequence_with_rhodesign" in state["tool_results"]

    def test_ribodiffusion_capability(self, registry, test_pdb_path_ribodiffusion):
        cap = registry.get("design_rna_inverse_fold_with_ribodiffusion")
        result = cap.invoke(
            {
                "pdb_filepath": test_pdb_path_ribodiffusion,
                "n_samples": 1,
                "sampling_steps": 10,
            },
            state={},
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("predicted_sequence"), "Missing predicted_sequence"

    def test_gc_capability(self, registry, test_sequence_filepath):
        cap = registry.get("compute_rna_sequence_gc_content")
        result = cap.invoke({"filepath": test_sequence_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("gc_content") is not None, "Missing gc_content"

    def test_fold_capability(self, registry, test_sequence_filepath):
        cap = registry.get("predict_rna_secondary_structure")
        result = cap.invoke({"filepath": test_sequence_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("structure"), "Missing structure"

    def test_rhofold_capability(self, registry, test_sequence_filepath):
        cap = registry.get("predict_rna_tertiary_structure_with_rhofold")
        result = cap.invoke({"filepath": test_sequence_filepath}, state={})
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("pdb_filepath"), "Missing pdb_filepath"
        assert result.output.get("mean_plddt") is not None, "Missing mean_plddt"

    def test_alignment_capability(self, registry, test_pdb_path):
        cap = registry.get("score_structure_alignment")
        result = cap.invoke(
            {
                "reference_pdb_filepath": test_pdb_path,
                "predicted_pdb_filepath": test_pdb_path,
                "atom_type": "C1'",
            },
            state={},
        )
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("rmsd") is not None, "Missing rmsd"
        assert result.output.get("tm_score") is not None, "Missing tm_score"


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow
# ═══════════════════════════════════════════════════════════════════════


class TestLayer2Workflow:
    """Layer 2 tests: RnaTertiaryStructureDesignWorkflow end-to-end."""

    @pytest.fixture(scope="class")
    def workflow(self, registry):
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignWorkflow,
        )

        # Ensure all capabilities are registered
        for name in [
            "design_rna_sequence_with_rhodesign",
            "design_rna_inverse_fold_with_ribodiffusion",
            "compute_rna_sequence_gc_content",
            "predict_rna_secondary_structure",
            "predict_rna_tertiary_structure_with_rhofold",
            "score_structure_alignment",
        ]:
            if not registry.has(name):
                registry.register(name)
        return RnaTertiaryStructureDesignWorkflow(registry)

    def test_workflow_rhodesign_only(self, workflow, test_pdb_path):
        """Run workflow with RhoDesign only (GPU)."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path,
            design_tools="rhodesign",
            n_samples_per_tool=1,
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
        assert mb.get("vienna_mfe") is not None, "Missing MFE"
        assert mb.get("rhofold_mean_plddt") is not None, "Missing RhoFold pLDDT"
        assert mb.get("alignment_rmsd") is not None, "Missing RMSD"

    def test_workflow_ribodiffusion_only(self, workflow, test_pdb_path_ribodiffusion):
        """Run workflow with RiboDiffusion only (GPU)."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path_ribodiffusion,
            design_tools="ribodiffusion",
            n_samples_per_tool=1,
            ribodiffusion_sampling_steps=10,
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) >= 1, "No candidates"
        assert result.all_candidates[0].source.startswith("ribodiffusion")

    def test_workflow_all_tools(self, workflow, test_pdb_path):
        """Run workflow with all tools (RhoDesign + RiboDiffusion, both GPU)."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path,
            design_tools="all",
            n_samples_per_tool=1,
            ribodiffusion_sampling_steps=10,
        )
        start = time.perf_counter()
        result = workflow.run(inp)
        elapsed = time.perf_counter() - start

        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        # Should have at least 2 candidates (1 from each tool)
        assert len(result.all_candidates) >= 2, (
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

    def test_workflow_progress_callback(self, workflow, test_pdb_path):
        """Workflow.run() should emit progress events via callback."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        events = []

        def callback(event: dict[str, Any]) -> None:
            events.append(event)

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path,
            design_tools="rhodesign",
            n_samples_per_tool=1,
        )
        result = workflow.run(inp, progress_callback=callback)
        assert result.success

        event_types = {e.get("event", "") for e in events}
        assert "generate_complete" in event_types, f"Missing generate_complete in {event_types}"
        assert "evaluate_progress" in event_types, f"Missing evaluate_progress in {event_types}"

    def test_workflow_state_writeback(self, workflow, test_pdb_path):
        """Verify workflow result has _state_writeback for controller."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path,
            design_tools="rhodesign",
            n_samples_per_tool=1,
        )
        result = workflow.run(inp)
        assert result.success
        assert hasattr(result, "_state_writeback"), "Missing _state_writeback"
        wb = getattr(result, "_state_writeback", {})
        assert "_workflow_params" in wb, "Missing _workflow_params in writeback"
        assert "_tertiary_design_input" in wb, "Missing _tertiary_design_input in writeback"

    def test_workflow_custom_weights(self, workflow, test_pdb_path):
        """Custom scoring weights should affect ranking."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignInput,
        )

        inp = RnaTertiaryStructureDesignInput(
            structure_filepath=test_pdb_path,
            design_tools="rhodesign",
            n_samples_per_tool=1,
            weight_rhofold=0.8,
            weight_rmsd=0.2,
        )
        result = workflow.run(inp)
        assert result.success
        assert result.best_candidate is not None
        # Verify scores reflect custom weights
        mb = result.best_candidate.metadata.get("metrics_bundle", {})
        plddt = mb.get("rhofold_mean_plddt", 0)
        rmsd = mb.get("alignment_rmsd", 5)
        expected = 0.8 * max(0, min(1, plddt / 100)) + 0.2 * max(0, min(1, 1 - rmsd / 5))
        actual = result.best_candidate.scores.get("total_score", 0)
        assert abs(actual - expected) < 0.01, f"Score mismatch: {actual} vs {expected}"


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Layer 3 — ExecutionController
# ═══════════════════════════════════════════════════════════════════════


class TestLayer3ExecutionController:
    """Layer 3 tests: ExecutionController integration."""

    @pytest.fixture(scope="class")
    def full_registry(self, registry):
        """Ensure all capabilities are registered."""
        for name in [
            "design_rna_sequence_with_rhodesign",
            "design_rna_inverse_fold_with_ribodiffusion",
            "compute_rna_sequence_gc_content",
            "predict_rna_secondary_structure",
            "predict_rna_tertiary_structure_with_rhofold",
            "score_structure_alignment",
        ]:
            if not registry.has(name):
                registry.register(name)
        return registry

    @pytest.fixture(scope="class")
    def workflow_registry(self, full_registry):
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignWorkflow,
        )

        wf = RnaTertiaryStructureDesignWorkflow(full_registry)
        return {"rna_tertiary_structure_design": wf}

    def test_controller_progress_callback(self, full_registry, workflow_registry, test_pdb_path):
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": test_pdb_path,
                        "design_tools": "rhodesign",
                        "n_samples_per_tool": 1,
                    },
                    output_key="result",
                )
            ]
        )

        events = []

        def callback(event: dict[str, Any]) -> None:
            events.append(event)

        controller = ExecutionController(
            capability_registry=full_registry,
            workflow_registry=workflow_registry,
        )
        state: dict[str, Any] = {"_llm_critic_enabled": False}
        result_state = controller.execute(plan, state, progress_callback=callback)

        assert result_state["_plan_executed"] is True
        assert len(events) > 0

        event_types = [e["event"] for e in events]
        assert "step_start" in event_types
        assert "step_done" in event_types
        assert "plan_complete" in event_types

    def test_controller_execution_log(self, full_registry, workflow_registry, test_pdb_path):
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": test_pdb_path,
                        "design_tools": "rhodesign",
                        "n_samples_per_tool": 1,
                    },
                    output_key="result",
                )
            ]
        )

        controller = ExecutionController(
            capability_registry=full_registry,
            workflow_registry=workflow_registry,
        )
        state: dict[str, Any] = {"_llm_critic_enabled": False}
        result_state = controller.execute(plan, state)

        log = result_state.get("_execution_log", [])
        assert len(log) > 0

        event_types = [e["event"] for e in log]
        assert "step_start" in event_types
        assert "step_done" in event_types
        assert "plan_complete" in event_types

        # Verify step metadata
        start_entries = [e for e in log if e["event"] == "step_start"]
        assert len(start_entries) == 1
        assert start_entries[0]["step_id"] == "design"

        done_entries = [e for e in log if e["event"] == "step_done"]
        assert len(done_entries) == 1
        assert done_entries[0]["success"] is True

    def test_controller_state_writeback_merge(self, full_registry, workflow_registry, test_pdb_path):
        """Controller should deep-merge workflow _state_writeback into outer state."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": test_pdb_path,
                        "design_tools": "rhodesign",
                        "n_samples_per_tool": 1,
                    },
                    output_key="result",
                )
            ]
        )

        controller = ExecutionController(
            capability_registry=full_registry,
            workflow_registry=workflow_registry,
        )
        # Pre-populate with some outer state
        state: dict[str, Any] = {
            "_llm_critic_enabled": False,
            "tool_results": {"some_prior_tool": {"key": "value"}},
        }
        result_state = controller.execute(plan, state)

        # Outer tool_results should be preserved
        assert "some_prior_tool" in result_state.get("tool_results", {}), (
            "Prior tool_results were overwritten"
        )
        # Workflow output should be stored
        assert "result" in result_state
        assert result_state["result"].success is True

    def test_controller_input_state_reference(self, full_registry, workflow_registry, test_pdb_path):
        """Controller should resolve $state references in input bindings."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": "$state.pdb_path",
                        "design_tools": "rhodesign",
                        "n_samples_per_tool": 1,
                    },
                    output_key="result",
                )
            ]
        )

        controller = ExecutionController(
            capability_registry=full_registry,
            workflow_registry=workflow_registry,
        )
        state: dict[str, Any] = {
            "_llm_critic_enabled": False,
            "pdb_path": test_pdb_path,
        }
        result_state = controller.execute(plan, state)
        assert result_state["_plan_executed"] is True
        assert result_state["result"].success is True


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: Live LLM Critic — Real DeepSeek API
# ═══════════════════════════════════════════════════════════════════════


def _make_low_quality_result() -> "WorkflowResult":
    """Build a WorkflowResult with deliberately poor metrics to trigger critic retry."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, (plddt, rmsd) in enumerate([(20.0, 8.0), (22.0, 7.5), (18.0, 8.5)]):
        c = Candidate(
            sequence="AUGC" * 20,
            sequence_type="rna",
            source=f"rhodesign_t{i + 1}",
            metadata={
                "metrics_bundle": {
                    "rhofold_mean_plddt": plddt,
                    "alignment_rmsd": rmsd,
                    "alignment_tm_score": 0.15,
                    "gc_content": 0.25,
                    "vienna_mfe": -5.0,
                    "recovery_rate": 0.3,
                    "sequence_length": 80,
                }
            },
        )
        c.scores = {
            "rhofold_component": max(0, min(1, plddt / 100)),
            "rmsd_component": max(0, 1 - rmsd / 5),
            "total_score": 0.5 * max(0, min(1, plddt / 100)) + 0.5 * max(0, 1 - rmsd / 5),
        }
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_low_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low quality test",
        errors=[],
    )


def _make_good_quality_result() -> "WorkflowResult":
    """Build a WorkflowResult with good metrics that should NOT trigger retry."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, (plddt, rmsd) in enumerate([(85.0, 1.5), (88.0, 1.2), (82.0, 1.8)]):
        c = Candidate(
            sequence="AUGC" * 20,
            sequence_type="rna",
            source=f"rhodesign_t{i + 1}",
            metadata={
                "metrics_bundle": {
                    "rhofold_mean_plddt": plddt,
                    "alignment_rmsd": rmsd,
                    "alignment_tm_score": 0.85,
                    "gc_content": 0.52,
                    "vienna_mfe": -25.0,
                    "recovery_rate": 0.85,
                    "sequence_length": 80,
                }
            },
        )
        c.scores = {
            "rhofold_component": max(0, min(1, plddt / 100)),
            "rmsd_component": max(0, 1 - rmsd / 5),
            "total_score": 0.5 * max(0, min(1, plddt / 100)) + 0.5 * max(0, 1 - rmsd / 5),
        }
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_good_quality",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Good quality test",
        errors=[],
    )


@pytest.mark.live_llm
class TestLiveLLMCritic:
    """Live tests using real DeepSeek API for Critic diagnosis."""

    def test_critic_diagnoses_low_quality(self):
        """Real LLM should detect poor metrics and recommend parameter changes."""
        from agent_core.planning.llm_critic import CriticDiagnosis
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {
                "structure_filepath": "test.pdb",
                "design_tools": "rhodesign",
                "n_samples_per_tool": 3,
            },
            "user_text": "Design high-quality RNA sequences that fold well into the target tertiary structure",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.5, (
            f"Expected low quality score for bad results, got {diagnosis.quality_score}"
        )
        assert len(diagnosis.issues) > 0, "Expected at least one issue"
        # Should recommend retry
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
        ), f"Expected retry action, got {diagnosis.action}"
        assert len(diagnosis.parameter_overrides) > 0, "Expected parameter overrides"

    def test_critic_should_retry_low_quality(self):
        """should_retry must return True for low-quality results."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {
                "structure_filepath": "test.pdb",
                "design_tools": "rhodesign",
                "n_samples_per_tool": 3,
            },
            "user_text": "Design high-quality RNA sequences that fold well into the target tertiary structure",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is True, "Expected should_retry=True for low quality"
        assert "_parameter_overrides" in state, "Missing _parameter_overrides"
        assert len(state["_parameter_overrides"]) > 0

    def test_critic_should_not_retry_good_quality(self):
        """should_retry should return False for good-quality results."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_good_quality_result()
        state = {
            "_last_workflow_params": {
                "structure_filepath": "test.pdb",
                "design_tools": "all",
                "n_samples_per_tool": 3,
            },
            "user_text": "Design high-quality RNA sequences",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is False, "Expected should_retry=False for good quality"

    def test_critic_prompt_contains_evaluation_dimensions(self):
        """Verify the diagnosis prompt includes domain-specific criteria."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_low_quality_result()
        ctx = critic._build_context(result, {})
        messages = critic._build_diagnosis_prompt(ctx)

        system_text = messages[0][1]  # ("system", text)
        assert "pLDDT" in system_text, "Missing pLDDT in evaluation criteria"
        assert "RMSD" in system_text, "Missing RMSD in evaluation criteria"
        assert "TM-score" in system_text, "Missing TM-score in criteria"
        assert "design_tools" in system_text, "Missing design_tools in adjustable params"

        user_text = messages[1][1]  # ("user", text)
        assert "rna_tertiary_structure_design" in user_text, "Missing workflow name"
        assert "rhodesign_t1" in user_text, "Missing candidate source"

    def test_diagnosis_records_history(self):
        """Verify diagnose appends to _diagnosis_history."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_low_quality_result()
        state: dict[str, Any] = {}

        critic.diagnose(result, state)

        assert "_diagnosis_history" in state, "Missing _diagnosis_history"
        assert len(state["_diagnosis_history"]) == 1

    def test_critic_context_has_tertiary_structure_stats(self):
        """Verify _build_context includes tertiary_structure_stats."""
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        critic = RnaTertiaryStructureDesignLLMCritic()
        result = _make_low_quality_result()
        ctx = critic._build_context(result, {})

        assert "tertiary_structure_stats" in ctx, "Missing tertiary_structure_stats"
        stats = ctx["tertiary_structure_stats"]
        assert "plddt_range" in stats, "Missing plddt_range"
        assert "rmsd_range" in stats, "Missing rmsd_range"
        assert "tm_score_range" in stats, "Missing tm_score_range"
        assert "design_tool_distribution" in stats, "Missing design_tool_distribution"
        # Verify stats are populated
        assert stats["plddt_range"]["count"] > 0, "Empty plddt stats"
        assert stats["rmsd_range"]["count"] > 0, "Empty rmsd stats"


# ═══════════════════════════════════════════════════════════════════════
# Phase 6: End-to-End Retry — ExecutionController + Real Critic
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
class TestEndToEndRetry:
    """End-to-end tests: ExecutionController + real Critic + parameter overrides."""

    def test_controller_triggers_retry_with_real_critic(self):
        """Full flow: controller executes workflow, critic triggers retry, params overridden.

        Uses a mock workflow that always returns low-quality results,
        but a REAL Critic (calling DeepSeek API) that diagnoses the problem
        and recommends parameter changes. The controller applies overrides
        and retries until max_retries is reached.
        """
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        executor = ToolExecutor(build_default_tool_registry())
        registry = CapabilityRegistry(executor)
        for name in [
            "design_rna_sequence_with_rhodesign",
            "design_rna_inverse_fold_with_ribodiffusion",
            "compute_rna_sequence_gc_content",
            "predict_rna_secondary_structure",
            "predict_rna_tertiary_structure_with_rhofold",
            "score_structure_alignment",
        ]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": "test.pdb",
                        "design_tools": "rhodesign",
                        "n_samples_per_tool": 1,
                    },
                    output_key="tertiary_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "rna_tertiary_structure_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "rna_tertiary_structure_design":
                return RnaTertiaryStructureDesignLLMCritic()
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
        # _critic_should_retry is intentionally popped at the start of each retry loop
        # so it does NOT persist in the final state. Verify retry via log instead.
        log = final_state.get("_execution_log", [])
        critic_retry_events = [e for e in log if e.get("event") == "critic_retry"]
        assert len(critic_retry_events) > 0, "No critic_retry events in log"

        # Verify parameter overrides were applied
        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) > 0, "No parameter_override events in log"

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
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        executor = ToolExecutor(build_default_tool_registry())
        registry = CapabilityRegistry(executor)
        for name in ["design_rna_sequence_with_rhodesign"]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": "test.pdb",
                        "design_tools": "rhodesign",
                    },
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "rna_tertiary_structure_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "rna_tertiary_structure_design":
                return RnaTertiaryStructureDesignLLMCritic()
            return None

        initial_state = {"_llm_critic_enabled": False}

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, initial_state)

        # Should only be called once (no retries)
        assert call_count == 1, (
            f"Expected 1 call with critic disabled, got {call_count}"
        )
        assert final_state.get("retry_count", 0) == 0

    def test_retry_parameter_override_filtering(self):
        """Critic parameter overrides should be filtered to adjustable_params only."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
        from agent_core.workflows.rna_tertiary_structure_design import (
            RnaTertiaryStructureDesignLLMCritic,
        )

        executor = ToolExecutor(build_default_tool_registry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="design",
                    type="workflow",
                    target="rna_tertiary_structure_design",
                    input_binding={
                        "structure_filepath": "test.pdb",
                        "design_tools": "rhodesign",
                    },
                    output_key="result",
                )
            ],
            max_retries=1,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            return _make_low_quality_result()

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "rna_tertiary_structure_design":
                return RnaTertiaryStructureDesignLLMCritic()
            return None

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, {})

        # Should retry once
        assert call_count == 2, f"Expected 2 calls (initial + 1 retry), got {call_count}"
        assert final_state.get("retry_count") == 1

        # Verify overrides only contain known adjustable params
        log = final_state.get("_execution_log", [])
        override_events = [e for e in log if e.get("event") == "parameter_override"]
        assert len(override_events) >= 1

        valid_keys = {
            "design_tools",
            "n_samples_per_tool",
            "rhodesign_temperature",
            "rhodesign_temperature_range",
            "ribodiffusion_sampling_steps",
            "weight_rhofold",
            "weight_rmsd",
        }
        for event in override_events:
            overrides = event.get("overrides", {})
            for key in overrides:
                assert key in valid_keys, f"Invalid override key: {key}"
