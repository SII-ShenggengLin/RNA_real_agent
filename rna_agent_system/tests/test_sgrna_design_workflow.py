from __future__ import annotations

import json
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, ToolResult
from agent_core.tool_registry import ToolRegistry
from agent_core.workflows.sgrna_design import (
    SgRnaDesignInput,
    SgRnaDesignWorkflow,
    score_sgrna_candidate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Stub tools
# ═══════════════════════════════════════════════════════════════════════════════


_CANDIDATES_DATA = [
    {
        "name": "gen_0",
        "sequence": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCTTAA",
        "nn_score": 1.20,
        "mutation_count": 5,
        "log_likelihood": -2.5,
        "structure_distance": 3,
        "mfe": -15.2,
    },
    {
        "name": "gen_1",
        "sequence": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCCCGG",
        "nn_score": 1.50,
        "mutation_count": 8,
        "log_likelihood": -3.1,
        "structure_distance": 5,
        "mfe": -12.0,
    },
    {
        "name": "gen_2",
        "sequence": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC",
        "nn_score": 1.80,
        "mutation_count": 10,
        "log_likelihood": -3.8,
        "structure_distance": 7,
        "mfe": -10.5,
    },
]


class _StubDesignTool:
    name = "design_sgrna_handle_with_crgpt"

    def invoke(self, kwargs):
        summary = json.dumps({"candidates": _CANDIDATES_DATA})
        summary_fp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        summary_fp.write(summary)
        summary_fp.close()
        return {
            "generated_count": 3,
            "output_fasta_path": "/tmp/sgrna_design_result.fasta",
            "summary_json_filepath": summary_fp.name,
            "normalized_seed": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC",
            "best_sequence": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCTTAA",
            "best_nn_score": 1.20,
            "best_mutation_count": 5,
            "sampling_mode": kwargs.get("sampling_mode", "mcmc"),
            "model": "sgrna_design_crgpt",
        }


class _StubDesignEmptyTool:
    name = "design_sgrna_handle_with_crgpt"

    def invoke(self, kwargs):
        summary = json.dumps({"candidates": []})
        summary_fp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        summary_fp.write(summary)
        summary_fp.close()
        return {
            "generated_count": 0,
            "output_fasta_path": "",
            "summary_json_filepath": summary_fp.name,
            "normalized_seed": "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC",
            "best_sequence": "",
            "best_nn_score": 0.0,
            "best_mutation_count": 0,
            "model": "sgrna_design_crgpt",
        }


class _StubScoreTool:
    name = "score_sgrna_handle_with_crgpt"

    def invoke(self, kwargs):
        seq = kwargs.get("sequence", "")
        # Deterministic fake perplexity based on sequence hash
        # Range ~1.0-2.0 (lower perplexity = better)
        base = hash(seq) % 100 / 100.0
        return {
            "sequence": seq,
            "normalized_sequence": seq.upper().replace("U", "T"),
            "nn_score": round(1.0 + base * 1.0, 4),
            "log_likelihood": round(-4.0 + base * 2.0, 4),
            "structure_distance": 3,
            "mfe": -15.0,
            "constraint_mutation_count": 5,
            "model": "sgrna_design_crgpt",
        }


class _StubScoreLowTool:
    name = "score_sgrna_handle_with_crgpt"

    def invoke(self, kwargs):
        seq = kwargs.get("sequence", "")
        return {
            "sequence": seq,
            "normalized_sequence": seq.upper().replace("U", "T"),
            "nn_score": 3.0,
            "log_likelihood": -5.0,
            "structure_distance": 8,
            "mfe": -8.0,
            "constraint_mutation_count": 12,
            "model": "sgrna_design_crgpt",
        }


class _StubCrisotTool:
    name = "score_crispr_off_target_with_crisot"

    def __init__(self, score: float = 0.85):
        self._score = score

    def invoke(self, kwargs):
        return {
            "input_filepath": kwargs.get("filepath", ""),
            "sgrna": "ATGCATGCATGCATGCATGCTGG",
            "target_sequence": kwargs.get("target_sequence", ""),
            "crisot_score": self._score,
            "model": "CRISOT-Score",
        }


class _FailScoreTool:
    name = "score_sgrna_handle_with_crgpt"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "score service down"},
        )


class _FailCrisotTool:
    name = "score_crispr_off_target_with_crisot"

    def invoke(self, kwargs):
        return ToolResult(
            success=False,
            tool_name=self.name,
            error={"type": "stub", "message": "crisot service down"},
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
        "design_sgrna_handle_with_crgpt",
        "score_sgrna_handle_with_crgpt",
        "score_crispr_off_target_with_crisot",
    ):
        cap_reg.register(name)
    return SgRnaDesignWorkflow(cap_reg)


_SEED = "ATGCATGCATGCATGCATGCATGCATGCATGCATGCATGC"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_design_with_seed_sequence():
    wf = _build_workflow(
        _StubDesignTool(),
        _StubScoreTool(),
        _StubCrisotTool(score=0.85),
    )
    inp = SgRnaDesignInput(
        seed_sequence=_SEED,
        n_samples=5,
        guide_sequence="ATGCATGCATGCATGCATGCTGG",
        target_sequence="ATGCATGCATGCATGCATGCTGG",
        evaluate_crisot=True,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 3
    # All candidates should have CRISOT score because guide+target provided
    for c in result.all_candidates:
        assert c.metadata["metrics_bundle"]["crisot_score"] is not None


def test_design_with_seed_filepath():
    seed_fp = save_sequence(_SEED, prefix="sgrna_seed")
    wf = _build_workflow(
        _StubDesignTool(),
        _StubScoreTool(),
        _StubCrisotTool(score=0.85),
    )
    inp = SgRnaDesignInput(
        seed_filepath=seed_fp,
        n_samples=5,
        guide_sequence="ATGCATGCATGCATGCATGCTGG",
        target_sequence="ATGCATGCATGCATGCATGCTGG",
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None


def test_design_empty_results():
    wf = _build_workflow(
        _StubDesignEmptyTool(),
        _StubScoreTool(),
        _StubCrisotTool(),
    )
    inp = SgRnaDesignInput(
        seed_sequence=_SEED,
        n_samples=5,
    )
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_design_no_seed_error():
    wf = _build_workflow(
        _StubDesignTool(),
        _StubScoreTool(),
        _StubCrisotTool(),
    )
    inp = SgRnaDesignInput(n_samples=5)
    result = wf.run(inp)
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_tool_failure_graceful():
    wf = _build_workflow(
        _StubDesignTool(),
        _FailScoreTool(),
        _StubCrisotTool(),
    )
    inp = SgRnaDesignInput(
        seed_sequence=_SEED,
        n_samples=5,
    )
    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    # Score failed -> fallback to design-time nn_score
    mb = best.metadata.get("metrics_bundle", {})
    assert mb.get("nn_score") is not None or mb.get("design_nn_score") is not None


def test_crisot_failure_graceful():
    wf = _build_workflow(
        _StubDesignTool(),
        _StubScoreTool(),
        _FailCrisotTool(),
    )
    inp = SgRnaDesignInput(
        seed_sequence=_SEED,
        n_samples=5,
        guide_sequence="ATGCATGCATGCATGCATGCTGG",
        target_sequence="ATGCATGCATGCATGCATGCTGG",
        evaluate_crisot=True,
    )
    result = wf.run(inp)
    assert result.success is True
    best = result.best_candidate
    assert best is not None
    # CRISOT failed -> crisot_score should be None
    for c in result.all_candidates:
        assert c.metadata["metrics_bundle"].get("crisot_score") is None


def test_crisot_caching():
    """CRISOT score should be computed only once per run and reused for all candidates."""
    call_count = 0

    class _CountingCrisotTool:
        name = "score_crispr_off_target_with_crisot"

        def invoke(self, kwargs):
            nonlocal call_count
            call_count += 1
            return {
                "input_filepath": kwargs.get("filepath", ""),
                "sgrna": "ATGCATGCATGCATGCATGCTGG",
                "target_sequence": kwargs.get("target_sequence", ""),
                "crisot_score": 0.80,
                "model": "CRISOT-Score",
            }

    wf = _build_workflow(
        _StubDesignTool(),
        _StubScoreTool(),
        _CountingCrisotTool(),
    )
    inp = SgRnaDesignInput(
        seed_sequence=_SEED,
        n_samples=5,
        guide_sequence="ATGCATGCATGCATGCATGCTGG",
        target_sequence="ATGCATGCATGCATGCATGCTGG",
        evaluate_crisot=True,
    )
    result = wf.run(inp)
    assert result.success is True
    # 3 candidates but CRISOT should be called only once because it is cached
    assert call_count == 1


def test_score_sgrna_candidate_formula():
    # Perfect candidate (nn_score = perplexity 1.0)
    scores = score_sgrna_candidate(
        {"nn_score": 1.0, "crisot_score": 0.9},
        {"nn": 0.5, "crisot": 0.5},
    )
    # nn_component = 1/1.0 = 1.0; crisot_component = 0.9
    assert scores["nn_component"] == pytest.approx(1.0, abs=0.01)
    assert scores["crisot_component"] == pytest.approx(0.9, abs=0.01)
    assert scores["total_score"] == pytest.approx(0.95, abs=0.01)

    # Missing CRISOT -> crisot_component is 0.0 but still weighted
    scores2 = score_sgrna_candidate(
        {"nn_score": 1.0},
        {"nn": 0.5, "crisot": 0.5},
    )
    assert scores2["nn_component"] == pytest.approx(1.0, abs=0.01)
    assert scores2["crisot_component"] == 0.0
    assert scores2["total_score"] == pytest.approx(0.5, abs=0.01)

    # All missing -> total_score 0.0 (no active components)
    scores3 = score_sgrna_candidate({}, {"nn": 0.5, "crisot": 0.5})
    assert scores3["total_score"] == 0.0



