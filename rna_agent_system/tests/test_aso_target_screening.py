"""Tests for ASO target screening workflow.

Uses stub capabilities to avoid needing live ViennaRNA microservices.

AsoTargetScreeningWorkflow INTERFACE LOCK (v1.0.0):
关联文件清单见 agent_core/workflows/aso_target_screening.py 顶部的
INTERFACE LOCK 注释。修改 workflow 接口必须同步更新全部关联文件并重新跑通测试。
"""

from __future__ import annotations

from typing import Any

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.workflows.aso_target_screening import (
    AsoScreeningCritic,
    AsoScreeningInput,
    AsoTargetScreeningWorkflow,
    _reverse_complement,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stub tools
# ═══════════════════════════════════════════════════════════════════════════════


class _StubPlfoldProfileTool:
    name = "predict_rna_local_accessibility_profile_vienna"

    def invoke(self, kwargs, state=None):
        # Return a synthetic accessibility profile: 200 nt, random-ish probabilities
        # Higher accessibility at positions 50-70 and 120-140
        positions = list(range(1, 201))
        probs: list[float] = []
        for pos in positions:
            if 50 <= pos <= 70:
                probs.append(0.75 + (pos % 5) * 0.01)
            elif 120 <= pos <= 140:
                probs.append(0.70 + (pos % 7) * 0.01)
            else:
                probs.append(0.20 + (pos % 10) * 0.01)
        return {
            "positions": positions,
            "unpaired_prob_1nt": probs,
            "sequence_length": 200,
            "mean_unpaired_prob_1nt": sum(probs) / len(probs),
            "min_unpaired_prob_1nt": min(probs),
            "max_unpaired_prob_1nt": max(probs),
            "lunp_profile_tsv_filepath": "workspace/stub_plfold.tsv",
            "backend": "RNAplfold-cli",
        }


class _StubPlfoldProfileFailTool:
    name = "predict_rna_local_accessibility_profile_vienna"

    def invoke(self, kwargs, state=None):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "plfold down"},
        )


class _StubAsoAccessibilityTool:
    name = "compute_aso_target_accessibility_vienna"

    def invoke(self, kwargs, state=None):
        region_start = kwargs.get("region_start", 1)
        region_end = kwargs.get("region_end", 18)
        region_end - region_start + 1
        # Synthetic mean prob based on start position
        mean_prob = 0.30 + (region_start % 50) / 100.0
        return {
            "sequence_length": 200,
            "region_start": region_start,
            "region_end": region_end,
            "mean_unpaired_prob_single_nt": round(mean_prob, 4),
            "joint_unpaired_prob_stretch_ending_at_region_end": round(mean_prob * 0.9, 4),
            "aso_oligo_length_used": kwargs.get("aso_oligo_length", 18),
            "backend": "RNAplfold-cli",
        }


class _StubRnaupTool:
    name = "compute_rna_rna_interaction_vienna"

    def invoke(self, kwargs, state=None):
        # Return synthetic binding energy; more negative = stronger
        return {
            "interaction_energy": -12.5,
            "interaction_structure": "((((....))))",
            "raw_stdout": "test",
            "backend": "RNAup-cli",
        }


class _StubCofoldTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs, state=None):
        return {
            "mfe_kcal_per_mol": -15.0,
            "structure": "((((((((....))))))))",
            "sense": "AUGC",
            "antisense": "CGUA",
            "backend": "RNAcofold-cli",
        }


class _StubGcTool:
    name = "compute_rna_sequence_gc_content"

    def invoke(self, kwargs, state=None):
        seq = kwargs.get("filepath", "")
        pseudo = hash(seq) % 100 / 100.0
        gc = 0.30 + pseudo * 0.30
        return {
            "gc_content": round(gc, 3),
            "sequence_length": 21,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


def _build_stub_registry(*, plfold_tool=None) -> CapabilityRegistry:
    reg = ToolRegistry()
    reg.register(plfold_tool or _StubPlfoldProfileTool())
    reg.register(_StubAsoAccessibilityTool())
    reg.register(_StubRnaupTool())
    reg.register(_StubCofoldTool())
    reg.register(_StubGcTool())
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "predict_rna_local_accessibility_profile_vienna",
        "compute_aso_target_accessibility_vienna",
        "compute_rna_rna_interaction_vienna",
        "compute_sirna_duplex_binding_vienna",
        "compute_rna_sequence_gc_content",
    ):
        cap_reg.register(name)
    return cap_reg


def _build_controller_with_aso(*, plfold_tool=None) -> tuple[ExecutionController, CapabilityRegistry]:
    cap_reg = _build_stub_registry(plfold_tool=plfold_tool)
    # Also register GC capability for downstream binding-resolution tests
    if not cap_reg.has("compute_rna_sequence_gc_content"):
        cap_reg.register("compute_rna_sequence_gc_content")
    wf = AsoTargetScreeningWorkflow(cap_reg)
    controller = ExecutionController(
        capability_registry=cap_reg,
        workflow_registry={"aso_target_screening": wf},
    )
    return controller, cap_reg


@pytest.fixture
def target_fasta_path() -> str:
    """Create a synthetic 200-nt target mRNA and return its workspace path."""
    seq = "AUG" * 60 + "UUU" * 7  # 200 nt (roughly)
    seq = "".join(c for c in seq if c in "AUGC")[:200]
    fp = save_sequence(f">target_mrna\n{seq}\n", prefix="aso_test_target")
    return fp


# ═══════════════════════════════════════════════════════════════════════════════
# Unit tests for helpers
# ═══════════════════════════════════════════════════════════════════════════════


def test_reverse_complement():
    assert _reverse_complement("AUGC") == "GCAU"
    assert _reverse_complement("AAAA") == "UUUU"
    assert _reverse_complement("") == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_aso_workflow_rnaup(target_fasta_path: str):
    reg = _build_stub_registry()
    wf = AsoTargetScreeningWorkflow(reg)
    inp = AsoScreeningInput(
        target_mrna_filepath=target_fasta_path,
        aso_length=18,
        window_step=3,
        top_n_windows=5,
        binding_evaluation_tool="rnaup",
    )
    result = wf.run(inp)

    assert result.success is True
    assert len(result.all_candidates) > 0
    assert len(result.all_candidates) <= 5
    best = result.best_candidate
    assert best is not None
    assert "composite_score" in best.scores
    # Rank-based scoring: composite_score is the final rank, 1 = best
    assert best.scores["composite_score"] == pytest.approx(1.0, abs=0.1)
    assert "accessibility_rank" in best.scores
    assert "binding_rank" in best.scores
    assert "sum_rank" in best.scores
    # Best candidate should come from high-accessibility region (50-70 or 120-140)
    start = best.metadata.get("target_start", 0)
    assert start > 0


def test_aso_workflow_cofold(target_fasta_path: str):
    reg = _build_stub_registry()
    wf = AsoTargetScreeningWorkflow(reg)
    inp = AsoScreeningInput(
        target_mrna_filepath=target_fasta_path,
        aso_length=18,
        window_step=3,
        top_n_windows=5,
        binding_evaluation_tool="rnacofold",
    )
    result = wf.run(inp)

    assert result.success is True
    assert len(result.all_candidates) > 0
    best = result.best_candidate
    assert best is not None
    mb = best.metadata.get("metrics_bundle", {})
    # Cofold should populate duplex_mfe
    assert mb.get("duplex_mfe_kcal_per_mol") is not None


def test_aso_workflow_empty_target():
    reg = _build_stub_registry()
    wf = AsoTargetScreeningWorkflow(reg)
    # Use a non-existent path
    inp = AsoScreeningInput(
        target_mrna_filepath="workspace/nonexistent_aso_target.fa",
        aso_length=18,
        top_n_windows=5,
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_aso_workflow_dict_input(target_fasta_path: str):
    """Ensure workflow accepts plain dict (API compatibility)."""
    reg = _build_stub_registry()
    wf = AsoTargetScreeningWorkflow(reg)
    result = wf.run({
        "target_mrna_filepath": target_fasta_path,
        "aso_length": 18,
        "window_step": 3,
        "top_n_windows": 3,
        "binding_evaluation_tool": "rnaup",
    })
    assert result.success is True
    assert len(result.all_candidates) <= 3


# ═══════════════════════════════════════════════════════════════════════════════
# Critic tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_aso_critic_never_retries():
    """ASO screening critic is an empty interface and never triggers retry."""
    critic = AsoScreeningCritic()
    # Build a fake result with mixed-quality candidates
    from agent_core.workflow_models import Candidate, WorkflowResult

    cands = [
        Candidate(
            sequence="A" * 18,
            sequence_type="aso",
            metadata={"metrics_bundle": {"binding_dg_kcal_per_mol": -12.0, "mean_unpaired_prob": 0.8}},
            scores={"composite_score": 1.0},
        ),
        Candidate(
            sequence="G" * 18,
            sequence_type="aso",
            metadata={"metrics_bundle": {"binding_dg_kcal_per_mol": -3.0, "mean_unpaired_prob": 0.2}},
            scores={"composite_score": 2.0},
        ),
    ]
    wf_result = WorkflowResult(
        success=True,
        task_id="test",
        all_candidates=cands,
        summary="test",
        errors=[],
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(wf_result, state) is False
    # Critic must not mutate state (empty interface)
    assert state == {}


# ═══════════════════════════════════════════════════════════════════════════════
# Layer 3 integration tests — ExecutionController + ASO workflow
# ═══════════════════════════════════════════════════════════════════════════════


def test_execution_controller_aso_no_retry(target_fasta_path: str):
    """ASO workflow executed by ExecutionController never triggers critic retry."""
    controller, _ = _build_controller_with_aso()
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="aso_target_screening",
                input_binding={
                    "target_mrna_filepath": target_fasta_path,
                    "aso_length": 18,
                    "window_step": 3,
                    "top_n_windows": 5,
                    "binding_evaluation_tool": "rnaup",
                },
                output_key="aso_result",
            )
        ],
        max_retries=2,
    )
    state: dict[str, Any] = {}
    final_state = controller.execute(plan, state)

    # Workflow succeeded
    assert final_state.get("workflow_result") is not None
    assert final_state["workflow_result"].success is True
    assert len(final_state["workflow_result"].all_candidates) > 0

    # No retry should have occurred
    assert final_state.get("retry_count", 0) == 0
    log = final_state["_execution_log"]
    assert not any(e.get("event") == "critic_retry" for e in log)
    assert not any(e.get("retries_exhausted") for e in log)

    # Step output key and workflow_result both present
    assert "aso_result" in final_state
    assert "workflow_result" in final_state

    # State writeback from workflow internal state should be merged
    assert "_aso_input" in final_state
    assert "target_filepath" in final_state


def test_execution_controller_aso_dict_input(target_fasta_path: str):
    """ExecutionController passes dict input binding through to the workflow."""
    controller, _ = _build_controller_with_aso()
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="aso_target_screening",
                input_binding={
                    "target_mrna_filepath": target_fasta_path,
                    "aso_length": 18,
                    "top_n_windows": 3,
                    "binding_evaluation_tool": "rnaup",
                },
                output_key="aso_result",
            )
        ],
        max_retries=2,
    )
    state: dict[str, Any] = {}
    final_state = controller.execute(plan, state)

    assert final_state["aso_result"].success is True
    assert len(final_state["aso_result"].all_candidates) <= 3
    assert final_state.get("retry_count", 0) == 0


def test_execution_controller_aso_binding_resolution(target_fasta_path: str):
    """ExecutionController resolves $state bindings for downstream capability steps."""
    controller, _ = _build_controller_with_aso()
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="step_1",
                type="workflow",
                target="aso_target_screening",
                input_binding={
                    "target_mrna_filepath": target_fasta_path,
                    "aso_length": 18,
                    "window_step": 3,
                    "top_n_windows": 2,
                    "binding_evaluation_tool": "rnaup",
                },
                output_key="aso_result",
            ),
            PlanStep(
                step_id="step_2",
                type="capability",
                target="compute_rna_sequence_gc_content",
                input_binding={
                    "filepath": "$state.target_filepath",
                },
                output_key="gc_check",
            ),
        ],
        max_retries=2,
    )
    state: dict[str, Any] = {}
    final_state = controller.execute(plan, state)

    # Step 1 output
    assert "aso_result" in final_state
    # Step 2 should have resolved $state.target_filepath
    assert "gc_check" in final_state
    assert final_state["gc_check"].success is True
    assert "gc_content" in final_state["gc_check"].output
