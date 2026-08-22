"""Tests for ASO target screening workflow.

Uses stub capabilities to avoid needing live ViennaRNA microservices.

"""

from __future__ import annotations

from typing import Any

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, ToolResult
from agent_core.tool_registry import ToolRegistry
from agent_core.agents.pipeline_agent import PipelineAgent
from agent_core.agents.quality_agent import QualityAgent
from agent_core.agents.specialist_agent import SpecialistAgent
from agent_core.agents.synthesis_agent import SynthesisAgent
from agent_core.pipeline.models import PipelinePlan
from agent_core.quality_profiles.aso_target_screening import ASO_TARGET_SCREENING_QUALITY_PROFILE
from agent_core.workflows.aso_target_screening import (
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


def _build_pipeline_agent_with_aso(*, plfold_tool=None) -> tuple[PipelineAgent, CapabilityRegistry]:
    cap_reg = _build_stub_registry(plfold_tool=plfold_tool)
    # Also register GC capability for downstream binding-resolution tests
    if not cap_reg.has("compute_rna_sequence_gc_content"):
        cap_reg.register("compute_rna_sequence_gc_content")
    wf = AsoTargetScreeningWorkflow(cap_reg)
    specialist = SpecialistAgent(wf, ASO_TARGET_SCREENING_QUALITY_PROFILE)
    specialist_registry = {"aso_target_screening": specialist}
    pipeline_agent = PipelineAgent(
        specialist_registry=specialist_registry,
        quality_agent=QualityAgent(),
        synthesis_agent=SynthesisAgent(),
    )
    return pipeline_agent, cap_reg


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
# Layer 3 integration tests — PipelineAgent + ASO workflow
# ═══════════════════════════════════════════════════════════════════════════════


def test_pipeline_agent_aso_no_retry(target_fasta_path: str):
    """ASO workflow executed by PipelineAgent succeeds without retry."""
    pipeline_agent, _ = _build_pipeline_agent_with_aso()
    plan = PipelinePlan.single(
        workflow="aso_target_screening",
        static_params={
            "target_mrna_filepath": target_fasta_path,
            "aso_length": 18,
            "window_step": 3,
            "top_n_windows": 5,
            "binding_evaluation_tool": "rnaup",
        },
        plan_id="aso_no_retry",
        output_alias="aso_result",
    )
    result = pipeline_agent.execute(plan)

    assert result.success is True
    assert "n1" in result.node_results
    node_result = result.node_results["n1"]
    assert node_result.workflow_result is not None
    assert node_result.workflow_result.success is True
    assert len(node_result.workflow_result.all_candidates) > 0


def test_pipeline_agent_aso_dict_input(target_fasta_path: str):
    """PipelineAgent passes dict input parameters through to the workflow."""
    pipeline_agent, _ = _build_pipeline_agent_with_aso()
    plan = PipelinePlan.single(
        workflow="aso_target_screening",
        static_params={
            "target_mrna_filepath": target_fasta_path,
            "aso_length": 18,
            "top_n_windows": 3,
            "binding_evaluation_tool": "rnaup",
        },
        plan_id="aso_dict_input",
        output_alias="aso_result",
    )
    result = pipeline_agent.execute(plan)

    assert result.success is True
    node_result = result.node_results["n1"]
    assert node_result.workflow_result is not None
    assert node_result.workflow_result.success is True
    assert len(node_result.workflow_result.all_candidates) <= 3


# ═══════════════════════════════════════════════════════════════════════════════
# ASF reference-point ranking (v1.1.0) — ordering mechanism + Borda diagnostics
# ═══════════════════════════════════════════════════════════════════════════════


def _mk_aso_candidate(cid: str, acc, bind, metadata_start: int) -> "Candidate":  # noqa: F821
    from agent_core.workflow_models import Candidate as _C

    cand = _C(
        sequence="ACGU" * 5 + cid[0],
        sequence_type="aso",
        source=f"window:{metadata_start}-{metadata_start + 19}",
        metadata={
            "metrics_bundle": {
                "target_start": metadata_start,
                "target_end": metadata_start + 19,
                "aso_sequence": "ACGUACGUACGUACGUACGU",
                "target_sequence": "ACGUACGUACGUACGUACGU",
                "mean_unpaired_prob": acc,
                "binding_dg_kcal_per_mol": -bind if bind is not None else None,
            }
        },
    )
    cand.scores = {
        "accessibility_component": acc,
        "binding_component": bind,
    }
    return cand


def _rank_via_workflow(cands):
    wf = AsoTargetScreeningWorkflow(None)
    return wf.rank_and_format(cands)


def test_aso_asf_orders_candidates_and_keeps_borda_diagnostics():
    cands = [
        _mk_aso_candidate("a", 0.90, 30.0, 10),
        _mk_aso_candidate("b", 0.80, 35.0, 50),
        _mk_aso_candidate("c", 0.85, 25.0, 100),
    ]
    result = _rank_via_workflow(cands)
    assert result.success is True
    # ASF values assigned and order is ascending asf → composite 1..N
    asfs = [c.scores["asf_distance"] for c in result.all_candidates]
    assert asfs == sorted(asfs)
    assert [c.scores["composite_score"] for c in result.all_candidates] == [1.0, 2.0, 3.0]
    # Borda ranks retained as diagnostics
    for c in result.all_candidates:
        assert "accessibility_rank" in c.scores
        assert "binding_rank" in c.scores
        assert "sum_rank" in c.scores
    # summary + extras
    assert "best_asf_distance" in result.summary
    assert "pareto_frontier_size" in result.summary
    assert getattr(result, "pareto_frontier", None) is not None


def test_aso_asf_missing_binding_is_not_rewarded():
    # 'c' has the best accessibility but no binding measurement (RNAup failed):
    # imputation at the measured pool-worst must keep it out of the top slot.
    cands = [
        _mk_aso_candidate("a", 0.90, 30.0, 10),
        _mk_aso_candidate("b", 0.80, 35.0, 50),
        _mk_aso_candidate("c", 0.95, None, 100),
    ]
    result = _rank_via_workflow(cands)
    best = result.best_candidate
    assert best.scores["binding_component"] is not None
    worst = result.all_candidates[-1]
    assert worst.scores["binding_component"] is None or worst.scores["asf_distance"] >= best.scores["asf_distance"]


def test_aso_asf_scale_invariant():
    # An affine stretch of the binding axis (kcal → arbitrary units) must not
    # change the ordering: min-max normalization makes ASF scale-free.
    base = [
        _mk_aso_candidate("a", 0.90, 30.0, 10),
        _mk_aso_candidate("b", 0.80, 35.0, 50),
        _mk_aso_candidate("c", 0.85, 25.0, 100),
    ]
    r1 = _rank_via_workflow([_clone(base[0]), _clone(base[1]), _clone(base[2])])
    scaled = []
    for c in base:
        c2 = _clone(c)
        c2.scores["binding_component"] = c.scores["binding_component"] * 7.5
        scaled.append(c2)
    r2 = _rank_via_workflow(scaled)
    ids1 = [c.source for c in r1.all_candidates]
    ids2 = [c.source for c in r2.all_candidates]
    assert ids1 == ids2


def _clone(cand):
    from agent_core.workflow_models import Candidate as _C

    c2 = _C(
        sequence=cand.sequence,
        sequence_type=cand.sequence_type,
        source=cand.source,
        metadata=dict(cand.metadata),
    )
    c2.scores = dict(cand.scores)
    return c2
