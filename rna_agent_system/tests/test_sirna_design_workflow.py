from __future__ import annotations


import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.tool_executor import ToolExecutor, ToolResult
from agent_core.tool_registry import ToolRegistry
from agent_core.workflows.sirna_design import (
    SirnaDesignInput,
    SirnaDesignWorkflow,
    score_sirna_candidate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stub tools
# ═══════════════════════════════════════════════════════════════════════════════


class _StubEvitarTool:
    name = "design_sirna_with_evitar"

    def invoke(self, kwargs):
        return {
            "top_results": [
                {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.95"},
                {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.85"},
                {"siRNA": "GGGCCCAUUAAAUUUAAAUUU", "score": "0.75"},
                {"siRNA": "CCCAUUAAAUUUAAAUUUGGG", "score": "0.65"},
            ],
            "result_count": 4,
            "mode": kwargs.get("mode", "existing"),
            "predict": kwargs.get("predict", "predsi"),
            "off_target": False,
        }


class _StubEvitarEmptyTool:
    name = "design_sirna_with_evitar"

    def invoke(self, kwargs):
        return {"top_results": [], "result_count": 0}


class _StubGcTool:
    name = "compute_rna_sequence_gc_content"

    def invoke(self, kwargs):
        seq = kwargs.get("filepath", "")
        pseudo = hash(seq) % 100 / 100.0
        gc = 0.30 + pseudo * 0.30
        return {
            "gc_content": round(gc, 3),
            "sequence_length": 21,
        }


class _StubDuplexTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -28.5,
            "sense": "AUGCCC",
            "antisense": "UUUGGG",
            "structure": "((((((",
        }


class _StubFoldTool:
    name = "predict_rna_secondary_structure"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -15.2,
            "structure": "(((...)))",
        }


class _StubBlastZeroTool:
    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 0, "subject_mode": "fasta"}


class _StubBlastHitTool:
    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 4, "subject_mode": "fasta"}


class _FailDuplexTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "duplex down"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _build_registry_with(*tools):
    reg = ToolRegistry()
    for t in tools:
        reg.register(t)
    return reg


def _build_workflow(*tools):
    reg = _build_registry_with(*tools)
    ex = ToolExecutor(reg)
    cap_reg = CapabilityRegistry(ex)
    for name in (
        "design_sirna_with_evitar",
        "compute_rna_sequence_gc_content",
        "compute_sirna_duplex_binding_vienna",
        "predict_rna_secondary_structure",
        "run_blastn_similarity_search",
    ):
        cap_reg.register(name)
    return SirnaDesignWorkflow(cap_reg)


class _StubBlastAllHitsThenZeroTool:
    """First 3 calls (one workflow run) return high hits; subsequent calls return zero."""

    name = "run_blastn_similarity_search"

    def __init__(self):
        self._call_count = 0

    def invoke(self, kwargs):
        self._call_count += 1
        if self._call_count <= 3:
            return {"hit_count": 10, "subject_mode": "fasta"}
        return {"hit_count": 0, "subject_mode": "fasta"}


class _StubBlastHighHitTool:
    """Always returns a high off-target hit count that exceeds even relaxed thresholds."""

    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 10, "subject_mode": "fasta"}


_LONG_SEQ = "AUGC" * 30  # 120 nt


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_antiviral_mode_end_to_end():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
        candidate_count=10,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 3  # 4 raw - 1 duplicate
    assert result.best_candidate.rank == 1
    assert result.best_candidate.scores["total_rank"] <= result.all_candidates[-1].scores["total_rank"]


def test_generic_mode_sliding_window():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="generic",
        target_sequence=_LONG_SEQ,
        candidate_count=5,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    # 120 nt -> 100 windows; filtered down to max_keep=10
    assert len(result.all_candidates) <= 10
    assert all(c.source.startswith("sliding_window") for c in result.all_candidates)


def test_empty_candidates_antiviral():
    wf = _build_workflow(
        _StubEvitarEmptyTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_empty_candidates_generic_too_short():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _StubDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="generic",
        target_sequence="AUGCAUGCAUGC",  # 12 nt < 40
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_tool_failure_graceful():
    wf = _build_workflow(
        _StubEvitarTool(),
        _StubGcTool(),
        _FailDuplexTool(),
        _StubFoldTool(),
        _StubBlastZeroTool(),
    )
    inp = SirnaDesignInput(
        mode="antiviral",
        target_sequence=_LONG_SEQ,
        candidate_count=3,
    )
    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    # Duplex failed -> all candidates get poor MFE ranks (inf sorted last)
    assert "rank_mfe" in best.scores
    assert "rank_offtarget" in best.scores
    # Total rank is rank sum (lower = better)
    assert "total_rank" in best.scores


def test_score_sirna_candidate_formula():
    # Perfect candidate: duplex=-40, off_target=0
    scores = score_sirna_candidate({"duplex_mfe": -40.0, "off_target_count": 0})
    assert scores["efficiency_component"] == 1.0
    assert scores["specificity_component"] == 1.0
    assert scores["total_score"] == pytest.approx(1.0, abs=0.01)

    # Worst candidate: duplex=0, off_target=9
    scores2 = score_sirna_candidate({"duplex_mfe": 0.0, "off_target_count": 9})
    assert scores2["efficiency_component"] == 0.0
    assert scores2["specificity_component"] == 0.1
    assert scores2["total_score"] < scores["total_score"]





def test_rank_and_format_ranks_full_pool_before_truncation():
    """Rank-then-truncate (2026-08-20 follow-up): a candidate beyond position
    ``candidate_count`` in generation order must still surface as #1 when it
    is the pool's best — the pre-fix truncate-then-rank order silently
    dropped it."""
    from types import SimpleNamespace

    from agent_core.workflow_models import Candidate

    wf = _build_workflow()
    inp = SimpleNamespace(candidate_count=10, mingc=0.0, maxgc=1.0)
    wf._workflow_state["_sirna_input"] = inp

    candidates = []
    for i in range(15):
        is_best = i == 11  # pool champion sits beyond the truncation point
        candidates.append(
            Candidate(
                sequence=f"ACGUACGUACGUACGUACG{i:02d}",
                sequence_type="sirna",
                source=f"window_{i}",
                scores={},
                metadata={
                    "metrics_bundle": {
                        "gc_content": 0.5,
                        # duplex MFE: the best (most negative) is at window 11
                        "duplex_mfe": -41.0 if is_best else -20.0 - (i % 5),
                        "off_target_count": 0 if is_best else 1 + (i % 3),
                    }
                },
            )
        )

    result = wf.rank_and_format(candidates)

    assert result.success
    assert len(result.all_candidates) == inp.candidate_count
    # The pool champion (window 11, both dimensions best) must rank #1.
    assert result.best_candidate is not None
    assert result.best_candidate.source == "window_11"
    assert result.all_candidates[0].source == "window_11"
    assert result.best_candidate.scores.get("asf_distance") == 0.0
