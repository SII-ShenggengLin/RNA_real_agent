"""Comprehensive integration test for full_length_mrna_design across all layers.

Covers:
  - Layer 0: Direct tool invocation (CPU + GPU microservices)
  - Layer 1: Capability registry with validation and writebacks
  - Layer 2: Full FullLengthMrnaDesignWorkflow (generate → evaluate → score → rank)
  - Layer 3: ExecutionController + live LLMPlanner + live FullLengthMrnaDesignLLMCritic
  - Layer 3: End-to-end retry with real Critic

Run:
    # All non-LLM tests (Layers 0-2)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_full_length_mrna_design_comprehensive.py -v

    # Include live LLM tests (Layers 3, requires DeepSeek API)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_full_length_mrna_design_comprehensive.py -v --live-llm
"""

from __future__ import annotations

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
def test_utr5_sequence() -> str:
    return "AUGC" * 15  # 60 nt UTR5 for IRESfinder test


@pytest.fixture(scope="module")
def test_utr3_sequence() -> str:
    return "CGUA" * 15  # 60 nt UTR3



@pytest.fixture(scope="module")
def protein_filepath(test_protein_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_protein_sequence, prefix="test_protein")


@pytest.fixture(scope="module")
def cds_filepath(test_cds_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_cds_sequence, prefix="test_cds")


@pytest.fixture(scope="module")
def utr5_filepath(test_utr5_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_utr5_sequence, prefix="test_utr5")


@pytest.fixture(scope="module")
def utr3_filepath(test_utr3_sequence):
    from agent_core.file_manager import save_sequence

    return save_sequence(test_utr3_sequence, prefix="test_utr3")
# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Layer 0 — Direct tool invocation
# ═══════════════════════════════════════════════════════════════════════


class TestLayer0CpuTools:
    """Layer 0 tests for CPU-based tools used by full-length mRNA workflow."""

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
    def test_iresfinder(self, executor, utr5_filepath):
        """IRESfinder on CPU (port 8013). Requires UTR >= 30 nt."""
        result = executor.run_tool(
            "predict_putative_ires_with_iresfinder", filepath=utr5_filepath
        )
        assert result.success, f"IRESfinder failed: {result.error}"
        out = result.artifacts.get("result", {})
        assert "max_score" in out, f"Missing max_score in IRES result: {out}"

    def test_lineardesign(self, executor, protein_filepath):
        """LinearDesign on CPU (port 8014) — used by CDS sub-workflow."""
        result = executor.run_tool(
            "design_mrna_cds_with_lineardesign",
            filepath=protein_filepath,
            lambda_value=1.0,
        )
        assert result.success, f"LinearDesign failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from LinearDesign"
        assert "cai_score" in result.artifacts.get("result", {})


@pytest.mark.integration
class TestLayer0GpuTools:
    """Layer 0 tests for GPU-based tools used by full-length mRNA workflow."""

    def test_gemorna_design_5utr(self, executor):
        """GEMORNA 5'UTR design on GPU (port 8004)."""
        result = executor.run_tool(
            "design_5utr_with_gemorna", utr_length="short"
        )
        assert result.success, f"GEMORNA 5'UTR design failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from GEMORNA 5'UTR"

    def test_gemorna_design_3utr(self, executor):
        """GEMORNA 3'UTR design on GPU (port 8004)."""
        result = executor.run_tool(
            "design_3utr_with_gemorna", utr_length="medium"
        )
        assert result.success, f"GEMORNA 3'UTR design failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from GEMORNA 3'UTR"

    def test_gemorna_predict_5utr_mrl(self, executor, utr5_filepath):
        """GEMORNA 5'UTR MRL prediction on GPU (port 8004)."""
        result = executor.run_tool(
            "predict_5utr_mrl_with_gemorna", filepath=utr5_filepath
        )
        assert result.success, f"GEMORNA 5'UTR MRL failed: {result.error}"
        mrl = result.artifacts.get("result", {}).get("predicted_mrl")
        assert mrl is not None, "Missing predicted_mrl"

    def test_gemorna_predict_3utr_stability(self, executor, utr3_filepath):
        """GEMORNA 3'UTR stability prediction on GPU (port 8004)."""
        result = executor.run_tool(
            "predict_3utr_stability_with_gemorna", filepath=utr3_filepath
        )
        assert result.success, f"GEMORNA 3'UTR stability failed: {result.error}"
        stab = result.artifacts.get("result", {}).get("predicted_stability")
        assert stab is not None, "Missing predicted_stability"

    def test_rnastop(self, executor, cds_filepath):
        """RNASTOP on GPU (port 8009)."""
        result = executor.run_tool(
            "predict_mrna_stability_with_rnastop", filepath=cds_filepath
        )
        assert result.success, f"RNASTOP failed: {result.error}"
        stab = result.artifacts.get("result", {}).get("overall_stability")
        assert stab is not None, "Missing overall_stability"
        assert 0.0 <= stab <= 1.0, f"Stability out of range: {stab}"

    def test_rnarl(self, executor, protein_filepath):
        """RNARL on GPU (port 8008) — used by CDS sub-workflow."""
        result = executor.run_tool(
            "design_mrna_cds_with_rnarl",
            filepath=protein_filepath,
            model_type="Homo sapiens mRNA",
        )
        assert result.success, f"RNARL failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from RNARL"

    def test_gemorna_cds(self, executor, protein_filepath):
        """GEMORNA CDS design on GPU (port 8004) — used by CDS sub-workflow."""
        result = executor.run_tool(
            "design_mrna_cds_with_gemorna", filepath=protein_filepath
        )
        assert result.success, f"GEMORNA CDS failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "Empty sequence from GEMORNA CDS"


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Layer 1 — Capability integration
# ═══════════════════════════════════════════════════════════════════════


class TestLayer1Capabilities:
    """Layer 1 tests: Capability.invoke() with validation and writebacks."""

    def test_viennarna_fold_capability(self, registry, cds_filepath):
        cap = registry.get("predict_rna_secondary_structure")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": cds_filepath}, state=state)
        assert result.success, f"Capability failed: {result.error}"
        assert result.output.get("structure"), "Missing structure"
        assert "tool_results" in state
        assert "predict_rna_secondary_structure" in state["tool_results"]

    def test_linearfold_capability(self, registry, cds_filepath):
        cap = registry.get("predict_rna_secondary_structure_with_linearfold")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": cds_filepath}, state=state)
        assert result.success
        assert result.output.get("structure")

    def test_gc_capability(self, registry, cds_filepath):
        cap = registry.get("compute_rna_sequence_gc_content")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": cds_filepath}, state=state)
        assert result.success
        assert result.output.get("gc_content") is not None
        assert "compute_rna_sequence_gc_content" in state["tool_results"]

    def test_cai_capability(self, registry, cds_filepath):
        cap = registry.get("compute_cai_for_cds_sequence")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"filepath": cds_filepath, "species": "Homo sapiens"}, state=state
        )
        assert result.success
        assert result.output.get("cai_score") is not None

    def test_u_content_capability(self, registry, cds_filepath):
        cap = registry.get("compute_rna_sequence_u_content")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": cds_filepath}, state=state)
        assert result.success
        assert result.output.get("u_fraction") is not None
        assert result.output.get("u_count") is not None

    @pytest.mark.integration
    def test_ires_capability(self, registry, utr5_filepath):
        cap = registry.get("predict_putative_ires_with_iresfinder")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": utr5_filepath}, state=state)
        assert result.success
        assert result.output.get("max_score") is not None

    @pytest.mark.integration
    def test_gemorna_5utr_design_capability(self, registry):
        cap = registry.get("design_5utr_with_gemorna")
        state: dict[str, Any] = {}
        result = cap.invoke({"utr_length": "short"}, state=state)
        assert result.success
        assert result.output.get("generated_sequence")
        assert "design_5utr_with_gemorna" in state["tool_results"]

    @pytest.mark.integration
    def test_gemorna_3utr_design_capability(self, registry):
        cap = registry.get("design_3utr_with_gemorna")
        state: dict[str, Any] = {}
        result = cap.invoke({"utr_length": "medium"}, state=state)
        assert result.success
        assert result.output.get("generated_sequence")

    @pytest.mark.integration
    def test_gemorna_5utr_mrl_capability(self, registry, utr5_filepath):
        cap = registry.get("predict_5utr_mrl_with_gemorna")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": utr5_filepath}, state=state)
        assert result.success
        assert result.output.get("predicted_mrl") is not None

    @pytest.mark.integration
    def test_gemorna_3utr_stability_capability(self, registry, utr3_filepath):
        cap = registry.get("predict_3utr_stability_with_gemorna")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": utr3_filepath}, state=state)
        assert result.success
        assert result.output.get("predicted_stability") is not None

    @pytest.mark.integration
    def test_rnastop_capability(self, registry, cds_filepath):
        cap = registry.get("predict_mrna_stability_with_rnastop")
        state: dict[str, Any] = {}
        result = cap.invoke({"filepath": cds_filepath}, state=state)
        assert result.success
        assert result.output.get("overall_stability") is not None

    def test_lineardesign_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_lineardesign")
        state: dict[str, Any] = {}
        result = cap.invoke(
            {"filepath": protein_filepath, "lambda_value": 1.0}, state=state
        )
        assert result.success
        assert result.output.get("generated_sequence")
        assert "design_mrna_cds_with_lineardesign" in state["tool_results"]

    @pytest.mark.integration
    def test_rnarl_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_rnarl")
        result = cap.invoke(
            {"filepath": protein_filepath, "model_type": "Homo sapiens mRNA"},
            state={},
        )
        assert result.success
        assert result.output.get("generated_sequence")

    @pytest.mark.integration
    def test_gemorna_cds_capability(self, registry, protein_filepath):
        cap = registry.get("design_mrna_cds_with_gemorna")
        result = cap.invoke({"filepath": protein_filepath}, state={})
        assert result.success
        assert result.output.get("generated_sequence")


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Layer 2 — Full workflow
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestLayer2Workflow:
    """Layer 2 tests: FullLengthMrnaDesignWorkflow end-to-end with real tools."""

    @pytest.fixture(scope="class")
    def workflow(self, registry):
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignWorkflow,
        )

        return FullLengthMrnaDesignWorkflow(registry)

    def test_workflow_lineardesign_only_short_utr(self, workflow, test_protein_sequence):
        """Run workflow with LinearDesign only + short UTR (fast, mostly CPU)."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
        )

        inp = FullLengthMrnaDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="lineardesign",
            lambda_value=1.0,
            utr_mode="short",
            cai_species="Homo sapiens",
        )
        result = workflow.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        assert len(result.all_candidates) >= 1, "No candidates produced"

        best = result.best_candidate
        assert len(best.sequence) > 0, "Empty best sequence"
        assert "utr5_sequence" in best.metadata, "Missing utr5_sequence"
        assert "cds_sequence" in best.metadata, "Missing cds_sequence"
        assert "utr3_sequence" in best.metadata, "Missing utr3_sequence"

        mb = best.metadata.get("metrics_bundle", {})
        assert mb.get("full_length_mfe") is not None, "Missing full_length_mfe"
        assert mb.get("cds_cai") is not None, "Missing cds_cai"
        assert mb.get("cds_u_fraction") is not None, "Missing cds_u_fraction"
        assert mb.get("full_u_fraction") is not None, "Missing full_u_fraction"
        assert mb.get("utr5_predicted_mrl") is not None, "Missing utr5_predicted_mrl"
        assert mb.get("utr3_predicted_stability") is not None, "Missing utr3_predicted_stability"

    def test_workflow_all_tools_all_utr(self, workflow, test_protein_sequence):
        """Run workflow with all tools + all UTR modes (CPU + GPU)."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
        )

        inp = FullLengthMrnaDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="all",
            utr_mode="all",
            cai_species="Homo sapiens",
        )
        start = time.perf_counter()
        result = workflow.run(inp)
        elapsed = time.perf_counter() - start

        assert result.success, f"Workflow failed: {result.errors}"
        assert result.best_candidate is not None, "No best candidate"
        # Should have multiple candidates (up to 6 CDS × 9 UTR combos)
        assert len(result.all_candidates) >= 3, (
            f"Too few candidates: {len(result.all_candidates)}"
        )

        # Verify ranking: candidates sorted by total_rank ascending
        ranks = [c.scores.get("total_rank", 999) for c in result.all_candidates]
        for i in range(len(ranks) - 1):
            assert ranks[i] <= ranks[i + 1], "Candidates not sorted by rank"

        # Verify summary
        assert result.summary, "Empty summary"
        assert "candidates=" in result.summary

        # Verify every candidate has UTR+CDS metadata
        for c in result.all_candidates:
            assert "utr5_sequence" in c.metadata
            assert "cds_sequence" in c.metadata
            assert "utr3_sequence" in c.metadata
            assert "utr5_preset" in c.metadata
            assert "utr3_preset" in c.metadata

        print(f"\n    Workflow 'all' completed in {elapsed:.1f}s")
        print(f"    Candidates: {len(result.all_candidates)}")
        print(f"    Best rank: {result.best_candidate.scores.get('total_rank')}")

    def test_workflow_different_utr_modes(self, workflow, test_protein_sequence):
        """Test each UTR mode produces appropriate preset combinations."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
        )

        for mode in ("short", "medium", "long"):
            inp = FullLengthMrnaDesignInput(
                protein_sequence=test_protein_sequence,
                design_tool="lineardesign",
                lambda_value=1.0,
                utr_mode=mode,
            )
            result = workflow.run(inp)
            assert result.success, f"Workflow failed for utr_mode={mode}: {result.errors}"
            assert len(result.all_candidates) >= 1
            # All candidates should use the requested preset for both UTRs
            for c in result.all_candidates:
                assert c.metadata.get("utr5_preset") == mode
                assert c.metadata.get("utr3_preset") == mode

    def test_workflow_state_writeback(self, workflow, test_protein_sequence):
        """Verify workflow result has _state_writeback for controller."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
        )

        inp = FullLengthMrnaDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="lineardesign",
            lambda_value=1.0,
            utr_mode="short",
        )
        result = workflow.run(inp)
        assert result.success
        assert hasattr(result, "_state_writeback"), "Missing _state_writeback"
        wb = getattr(result, "_state_writeback", {})
        assert "_workflow_params" in wb, "Missing _workflow_params in writeback"
        # CDS sub-workflow tools should be merged in
        assert "tool_results" in wb, "Missing tool_results in writeback"

    def test_workflow_rnarl_only(self, registry, test_protein_sequence):
        """Run workflow with RNARL only for CDS (GPU)."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
            FullLengthMrnaDesignWorkflow,
        )

        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="rnarl",
            model_type="Homo sapiens mRNA",
            utr_mode="short",
        )
        result = wf.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) >= 1, "No candidates"

    def test_workflow_gemorna_only(self, registry, test_protein_sequence):
        """Run workflow with GEMORNA only for CDS (GPU)."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignInput,
            FullLengthMrnaDesignWorkflow,
        )

        wf = FullLengthMrnaDesignWorkflow(registry)
        inp = FullLengthMrnaDesignInput(
            protein_sequence=test_protein_sequence,
            design_tool="gemorna",
            utr_mode="short",
        )
        result = wf.run(inp)
        assert result.success, f"Workflow failed: {result.errors}"
        assert len(result.all_candidates) >= 1, "No candidates"


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Layer 3 — ExecutionController integration
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestLayer3ExecutionController:
    """Layer 3 tests: ExecutionController + FullLengthMrnaDesignWorkflow."""

    def test_controller_runs_full_workflow(self, registry, test_protein_sequence):
        """ExecutionController drives the full workflow end-to-end."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflow_models import WorkflowResult
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignWorkflow,
        )

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
                        "protein_sequence": test_protein_sequence,
                        "design_tool": "lineardesign",
                        "lambda_value": 1.0,
                        "utr_mode": "short",
                    },
                    output_key="result",
                )
            ],
            max_retries=2,
        )

        state: dict[str, Any] = {"_llm_critic_enabled": False}
        result_state = controller.execute(plan, state)

        assert "result" in result_state
        wf_result = result_state["result"]
        assert isinstance(wf_result, WorkflowResult)
        assert wf_result.success is True
        assert len(wf_result.all_candidates) > 0
        assert wf_result.best_candidate is not None

        # Verify candidates have UTR + CDS metadata
        best = wf_result.best_candidate
        assert "utr5_sequence" in best.metadata
        assert "cds_sequence" in best.metadata
        assert "utr3_sequence" in best.metadata

        # State writeback merged
        tool_results = result_state.get("tool_results", {})
        assert "design_5utr_with_gemorna" in tool_results
        assert "design_3utr_with_gemorna" in tool_results
        assert "design_mrna_cds_with_lineardesign" in tool_results

        # No retry when critic disabled
        assert result_state.get("retry_count", 0) == 0

    def test_controller_progress_callback(self, registry, test_protein_sequence):
        """Progress callback receives events during execution."""
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignWorkflow,
        )

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
                        "protein_sequence": test_protein_sequence,
                        "design_tool": "lineardesign",
                        "lambda_value": 1.0,
                        "utr_mode": "short",
                    },
                )
            ],
        )

        events: list[dict[str, Any]] = []

        def _cb(evt: dict[str, Any]) -> None:
            events.append(evt)

        controller.execute(plan, {"_llm_critic_enabled": False}, progress_callback=_cb)

        assert any(e.get("event") == "step_start" for e in events)
        assert any(e.get("event") == "step_done" for e in events)
        assert any(e.get("event") == "plan_complete" for e in events)


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: Live LLM Critic — Real DeepSeek API
# ═══════════════════════════════════════════════════════════════════════


def _make_low_quality_result() -> "WorkflowResult":
    """Build a WorkflowResult with deliberately poor metrics to trigger critic retry."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, (mrl, stab) in enumerate([(2.0, 0.2), (2.1, 0.25), (2.2, 0.3)]):
        c = Candidate(
            sequence="GGGAAA" + "AUG" * 40 + "AAAUUU",
            sequence_type="mrna",
            source=f"test:utr5_short:utr3_short",
            metadata={
                "utr5_sequence": "GGGAAA",
                "cds_sequence": "AUG" * 40,
                "utr3_sequence": "AAAUUU",
                "utr5_preset": "short",
                "utr3_preset": "short",
                "cds_length": 120,
                "cds_source": "lineardesign",
                "metrics_bundle": {
                    "cds_cai": 0.3,
                    "cds_mfe": -150.0,
                    "cds_gc": 0.52,
                    "cds_length": 120,
                    "utr5_predicted_mrl": mrl,
                    "utr3_predicted_stability": stab,
                    "utr5_ires_potential": 0.1,
                    "full_length_mfe": -80.0,
                    "total_length": 132,
                    "overall_stability": 0.3,
                },
            },
        )
        c.scores = {
            "cds_component": 0.3,
            "utr5_mrl": mrl,
            "utr3_stability": stab,
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


def _make_high_ires_result() -> "WorkflowResult":
    """Build a WorkflowResult with high IRES to trigger critic retry."""
    from agent_core.workflow_models import Candidate, WorkflowResult

    candidates: list[Candidate] = []
    for i, ires in enumerate([0.85, 0.90, 0.88]):
        c = Candidate(
            sequence="GGGAAA" + "AUG" * 40 + "AAAUUU",
            sequence_type="mrna",
            source=f"test:utr5_short:utr3_short",
            metadata={
                "utr5_sequence": "GGGAAA",
                "cds_sequence": "AUG" * 40,
                "utr3_sequence": "AAAUUU",
                "utr5_preset": "short",
                "utr3_preset": "short",
                "cds_length": 120,
                "cds_source": "lineardesign",
                "metrics_bundle": {
                    "cds_cai": 0.82,
                    "cds_mfe": -50.0,
                    "cds_gc": 0.52,
                    "cds_length": 120,
                    "utr5_predicted_mrl": 6.0,
                    "utr3_predicted_stability": 0.75,
                    "utr5_ires_potential": ires,
                    "full_length_mfe": -30.0,
                    "total_length": 132,
                    "overall_stability": 0.65,
                },
            },
        )
        c.scores = {
            "cds_component": 0.82,
            "utr5_mrl": 6.0,
            "utr3_stability": 0.75,
        }
        candidates.append(c)

    return WorkflowResult(
        success=True,
        task_id="test_high_ires",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="High IRES test",
        errors=[],
    )


@pytest.mark.live_llm
class TestLiveLLMCritic:
    """Live tests using real DeepSeek API for FullLengthMrnaDesignLLMCritic."""

    def test_critic_diagnoses_low_mrl(self):
        """Real LLM should detect low MRL and recommend parameter changes."""
        from agent_core.planning.llm_critic import CriticDiagnosis
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        critic = FullLengthMrnaDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {"design_tool": "lineardesign", "utr_mode": "short"},
            "user_text": "Design high-expression full-length mRNA for human expression",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert diagnosis.quality_score < 0.7, (
            f"Expected low quality score for bad results, got {diagnosis.quality_score}"
        )
        assert len(diagnosis.issues) > 0, "Expected at least one issue"
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        )

    def test_critic_diagnoses_high_ires(self):
        """Real LLM should flag high IRES for standard mRNA."""
        from agent_core.planning.llm_critic import CriticDiagnosis
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        critic = FullLengthMrnaDesignLLMCritic()
        result = _make_high_ires_result()
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design standard cap-dependent mRNA for human expression",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        assert len(diagnosis.issues) > 0, "Expected at least one issue"
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        )

    def test_critic_should_retry_low_quality(self):
        """should_retry must return True for low-quality full-length results."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        critic = FullLengthMrnaDesignLLMCritic()
        result = _make_low_quality_result()
        state = {
            "_last_workflow_params": {"design_tool": "lineardesign", "utr_mode": "short"},
            "user_text": "Design high-expression full-length mRNA for human expression",
        }

        should_retry = critic.should_retry(result, state)
        assert should_retry is True, "Expected should_retry=True for low quality"
        assert "_parameter_overrides" in state, "Missing _parameter_overrides"
        assert len(state["_parameter_overrides"]) > 0

    def test_critic_prompt_contains_full_length_dimensions(self):
        """Verify the diagnosis prompt includes full-length-specific criteria."""
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        critic = FullLengthMrnaDesignLLMCritic()
        result = _make_low_quality_result()
        ctx = critic._build_context(result, {})
        messages = critic._build_diagnosis_prompt(ctx)

        system_text = messages[0][1]
        assert "UTR length mode" in system_text, "Missing UTR length mode"
        assert "MRL" in system_text, "Missing MRL in criteria"
        assert "IRES" in system_text, "Missing IRES in criteria"
        assert "utr_mode" in system_text, "Missing utr_mode in params"
        assert "design_tool" in system_text, "Missing design_tool in params"

    def test_critic_respects_user_ires_intent(self):
        """When user wants IRES, critic should not flag high IRES as critical."""
        from agent_core.planning.llm_critic import CriticDiagnosis
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        critic = FullLengthMrnaDesignLLMCritic()
        result = _make_high_ires_result()
        state = {
            "_last_workflow_params": {"design_tool": "all", "utr_mode": "all"},
            "user_text": "Design IRES-driven mRNA with strong IRES in 5'UTR",
        }

        diagnosis = critic.diagnose(result, state)

        assert isinstance(diagnosis, CriticDiagnosis)
        critical_ires = [
            i for i in diagnosis.issues
            if i.severity == "critical" and ("ires" in i.category.lower() or "IRES" in i.description)
        ]
        assert len(critical_ires) == 0, (
            f"Expected no critical IRES issue when user wants IRES, got: {critical_ires}"
        )


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
        and recommends parameter changes. The controller then applies the
        overrides and retries until max_retries is reached.
        """
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

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
            "design_5utr_with_gemorna",
            "design_3utr_with_gemorna",
            "predict_5utr_mrl_with_gemorna",
            "predict_3utr_stability_with_gemorna",
            "predict_putative_ires_with_iresfinder",
        ]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf",
                    type="workflow",
                    target="full_length_mrna_design",
                    input_binding={
                        "protein_sequence": "MKTLLILTVFGITMLLAVLAQG",
                        "design_tool": "lineardesign",
                        "lambda_value": 0.0,
                        "utr_mode": "short",
                    },
                    output_key="result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "full_length_mrna_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected step: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "full_length_mrna_design":
                return FullLengthMrnaDesignLLMCritic()
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
        from agent_core.workflows.full_length_mrna_design import (
            FullLengthMrnaDesignLLMCritic,
        )

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        for name in ["design_mrna_cds_with_lineardesign"]:
            registry.register(name)

        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf",
                    type="workflow",
                    target="full_length_mrna_design",
                    input_binding={
                        "protein_sequence": "MKLTEST",
                        "design_tool": "lineardesign",
                        "lambda_value": 0.0,
                    },
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "full_length_mrna_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return _make_low_quality_result()
            raise RuntimeError(f"Unexpected: {step.target}")

        def _mock_resolve_critic(step, get_critic_fn):
            if step.target == "full_length_mrna_design":
                return FullLengthMrnaDesignLLMCritic()
            return None

        initial_state = {"_llm_critic_enabled": False}

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch.object(
                controller, "_resolve_critic", side_effect=_mock_resolve_critic
            ):
                final_state = controller.execute(plan, initial_state)

        # Should only be called once (no retries)
        assert call_count == 1, f"Expected 1 call with critic disabled, got {call_count}"
        assert final_state.get("retry_count", 0) == 0
