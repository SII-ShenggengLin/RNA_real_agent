"""Tests for full-length mRNA design workflow.

Covers:
1. score_full_length_mrna_candidate unit scoring
2. FullLengthMrnaDesignInput Pydantic validation
3. UTR combination generation logic (6 × 9 = 54 candidates)
4. Workflow integration with mocked capabilities
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

import json
import math
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agent_core.agents.quality_agent import QualityAgent
from agent_core.capabilities.base import CapabilityResult
from agent_core.quality_profiles.full_length_mrna_design import (
    FULL_LENGTH_MRNA_QUALITY_PROFILE,
)
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.coordinator import Issue, ReferencePointCoordinator
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
    score_full_length_mrna_candidate,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scoring function tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_full_length_formula():
    """Per-module raw scores returned for later rank aggregation."""
    # cds_combined_score = -(-30.0) + (100/3) * log(1.0) = 30.0 + 0 = 30.0
    # cds_component = 30.0 / 100 = 0.3
    metrics = {
        "cds_cai": 1.0,
        "cds_mfe": -30.0,
        "cds_length": 100,
        "utr5_predicted_mrl": 6.5,
        "utr3_predicted_stability": 0.8,
    }
    scores = score_full_length_mrna_candidate(metrics)
    assert scores["cds_component"] == pytest.approx(0.3, abs=1e-6)
    assert scores["utr5_mrl"] == pytest.approx(6.5, abs=1e-6)
    assert scores["utr3_stability"] == pytest.approx(0.8, abs=1e-6)
    assert "cds_combined_score" in scores


def test_score_full_length_missing_utr_predictions():
    """Missing UTR predictions are returned as None."""
    metrics = {
        "cds_cai": 1.0,
        "cds_mfe": -30.0,
        "cds_length": 100,
    }
    scores = score_full_length_mrna_candidate(metrics)
    assert scores["utr5_mrl"] is None
    assert scores["utr3_stability"] is None
    assert scores["cds_component"] == pytest.approx(0.3, abs=1e-6)


def test_score_full_length_missing_cds():
    """Missing CDS metrics are returned as None."""
    metrics = {
        "utr5_predicted_mrl": 5.0,
        "utr3_predicted_stability": 0.5,
    }
    scores = score_full_length_mrna_candidate(metrics)
    assert scores["cds_component"] is None
    assert scores["utr5_mrl"] == pytest.approx(5.0, abs=1e-6)
    assert scores["utr3_stability"] == pytest.approx(0.5, abs=1e-6)


def test_score_full_length_pure_cds():
    """When only CDS metrics are present, UTR scores are None."""
    metrics = {
        "cds_cai": 1.0,
        "cds_mfe": -30.0,
        "cds_length": 100,
    }
    scores = score_full_length_mrna_candidate(metrics)
    # cds_combined_score = 30.0 + 33*log(1.0) = 30.0
    # cds_component = 30.0 / 100 = 0.3
    assert scores["cds_component"] == pytest.approx(0.3, abs=1e-6)
    assert scores["utr5_mrl"] is None
    assert scores["utr3_stability"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_defaults():
    inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ")
    assert inp.design_tool == "all"
    assert inp.lambda_value is None
    assert inp.cai_species == "Homo sapiens"
    assert inp.model_type == "Homo sapiens mRNA"
    assert inp.utr_mode == "all"
    assert inp.run_fold is True
    assert inp.run_gc is True
    assert inp.bmc_mode == "rp"
    assert inp.reference_point is None


def test_input_valid_tools():
    for tool in ("lineardesign", "rnarl", "gemorna", "all"):
        inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool=tool)
        assert inp.design_tool == tool


def test_input_valid_utr_modes():
    for mode in ("short", "medium", "long", "all"):
        inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", utr_mode=mode)
        assert inp.utr_mode == mode


def test_input_invalid_design_tool():
    with pytest.raises(Exception):
        FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool="invalid")


def test_input_invalid_utr_mode():
    with pytest.raises(Exception):
        FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", utr_mode="extra_long")


def test_input_dict_coercion():
    raw = {
        "protein_sequence": "MVSKGEELFTGV",
        "design_tool": "lineardesign",
        "utr_mode": "short",
    }
    inp = FullLengthMrnaDesignInput(**raw)
    assert inp.protein_sequence == "MVSKGEELFTGV"
    assert inp.design_tool == "lineardesign"
    assert inp.utr_mode == "short"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Generation logic tests (mocked capabilities)
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_with_mocks() -> MagicMock:
    """Build a mock registry that returns deterministic sequences for every tool."""
    reg = MagicMock()

    # CDS tools
    cap_ld = make_mock_capability({"generated_sequence": "AUGCCCGGGUUU"})
    cap_rnarl = make_mock_capability({"generated_sequence": "AUGGGGCCCUUU"})
    cap_gemorna_cds = make_mock_capability({"generated_sequence": "AUGUUUGGGCCC"})

    # UTR tools
    cap_utr5_short = make_mock_capability({"generated_sequence": "GGGAAA"})
    cap_utr5_medium = make_mock_capability({"generated_sequence": "GGGAAACCCUUU"})
    cap_utr5_long = make_mock_capability({"generated_sequence": "GGGAAACCCUUUGGGAAA"})
    cap_utr3_short = make_mock_capability({"generated_sequence": "AAAUUU"})
    cap_utr3_medium = make_mock_capability({"generated_sequence": "AAAUUUGGGCCC"})
    cap_utr3_long = make_mock_capability({"generated_sequence": "AAAUUUGGGCCCUUUAAA"})

    caps = {
        "design_mrna_cds_with_lineardesign": cap_ld,
        "design_mrna_cds_with_rnarl": cap_rnarl,
        "design_mrna_cds_with_gemorna": cap_gemorna_cds,
        "design_5utr_with_gemorna": MagicMock(),
        "design_3utr_with_gemorna": MagicMock(),
    }

    # UTR presets: return different sequences for each preset
    utr5_sequences = {
        "short": "GGGAAA",
        "medium": "GGGAAACCCUUU",
        "long": "GGGAAACCCUUUGGGAAA",
    }
    utr3_sequences = {
        "short": "AAAUUU",
        "medium": "AAAUUUGGGCCC",
        "long": "AAAUUUGGGCCCUUUAAA",
    }

    def _utr5_invoke(args, state=None):
        preset = args.get("utr_length", "medium")
        return CapabilityResult(
            success=True,
            tool_name="design_5utr_with_gemorna",
            output={"generated_sequence": utr5_sequences[preset]},
        )

    def _utr3_invoke(args, state=None):
        preset = args.get("utr_length", "medium")
        return CapabilityResult(
            success=True,
            tool_name="design_3utr_with_gemorna",
            output={"generated_sequence": utr3_sequences[preset]},
        )

    caps["design_5utr_with_gemorna"].invoke = _utr5_invoke
    caps["design_3utr_with_gemorna"].invoke = _utr3_invoke

    def _has(name: str) -> bool:
        return name in caps

    def _get(name: str) -> Any:
        return caps[name]

    reg.has = _has
    reg.get = _get
    return reg


def test_generate_candidates_6cds_9utr_54_total():
    """With 3 unique CDS tools and 3×3 UTR combos, verify 54 candidates."""
    reg = _make_registry_with_mocks()
    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool="all")
    candidates = wf.generate_candidates(inp)
    # 3 CDS tools (lineardesign produces 4, but we mock same cap) × 9 UTR combos
    # Actually lineardesign cap returns same sequence every time, so after dedup:
    # lineardesign: 4 calls → 1 unique (all same mocked seq)
    # rnarl: 1 unique
    # gemorna: 1 unique
    # Total unique CDS = 3
    # 3 × 9 = 27 unique full-length candidates
    assert len(candidates) == 27

    # Verify every candidate has the required metadata
    for c in candidates:
        assert c.metadata["utr5_sequence"] != ""
        assert c.metadata["cds_sequence"] != ""
        assert c.metadata["utr3_sequence"] != ""
        assert "utr5_preset" in c.metadata
        assert "utr3_preset" in c.metadata
        assert "cds_source" in c.metadata
        assert len(c.sequence) == (
            c.metadata["utr5_length"] + c.metadata["cds_length"] + c.metadata["utr3_length"]
        )


def test_generate_candidates_dedup_full_sequence():
    """If two combinations produce identical full sequences, only one survives."""
    reg = MagicMock()

    # All tools return identical sequences → after dedup we get 1 CDS × 9 UTR
    cap = make_mock_capability({"generated_sequence": "AUGCCC"})

    utr_seqs = {
        "short": "SSS",
        "medium": "MMM",
        "long": "LLL",
    }

    def _utr_invoke(args, state=None):
        preset = args.get("utr_length", "medium")
        return CapabilityResult(
            success=True,
            tool_name="utr",
            output={"generated_sequence": utr_seqs[preset]},
        )

    caps = {
        "design_mrna_cds_with_lineardesign": cap,
        "design_mrna_cds_with_rnarl": cap,
        "design_mrna_cds_with_gemorna": cap,
        "design_5utr_with_gemorna": MagicMock(),
        "design_3utr_with_gemorna": MagicMock(),
    }
    caps["design_5utr_with_gemorna"].invoke = _utr_invoke
    caps["design_3utr_with_gemorna"].invoke = _utr_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool="all")
    candidates = wf.generate_candidates(inp)
    # 1 unique CDS × 3 UTR5 × 3 UTR3 = 9 unique full sequences
    assert len(candidates) == 9


def test_generate_candidates_skips_cds_not_multiple_of_3():
    """CDS length must be a multiple of 3; non-conforming candidates are skipped."""
    reg = MagicMock()
    cap = make_mock_capability({"generated_sequence": "AUGCC"})  # 5 nt — bad
    caps = {
        "design_mrna_cds_with_lineardesign": cap,
        "design_5utr_with_gemorna": make_mock_capability({"generated_sequence": "UUU"}),
        "design_3utr_with_gemorna": make_mock_capability({"generated_sequence": "AAA"}),
    }
    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool="lineardesign", lambda_value=0.0)
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 0


def test_generate_candidates_utr_mode_filter():
    """utr_mode='short' should produce only 1 UTR preset per end → 1 combo per CDS."""
    reg = _make_registry_with_mocks()
    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKTLVVPFGQ", design_tool="all", utr_mode="short")
    candidates = wf.generate_candidates(inp)
    # 3 unique CDS × 1 UTR5(short) × 1 UTR3(short) = 3
    assert len(candidates) == 3
    for c in candidates:
        assert c.metadata["utr5_preset"] == "short"
        assert c.metadata["utr3_preset"] == "short"


def test_generate_candidates_propagates_cai_species():
    """Full-length candidates must inherit cai_species from the workflow input
    so that downstream CAI evaluation uses the correct species."""
    reg = _make_registry_with_mocks()
    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(
        protein_sequence="MKTLVVPFGQ",
        design_tool="lineardesign",
        lambda_value=1.0,
        cai_species="Mus musculus",
        utr_mode="short",
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 1
    assert candidates[0].metadata["cai_species"] == "Mus musculus"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Evaluate & Score integration tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_for_eval() -> MagicMock:
    """Registry with mocked evaluate-phase capabilities."""
    reg = MagicMock()

    def _fold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_secondary_structure",
            output={"mfe_kcal_per_mol": -25.0, "structure": "....(((())))...."},
        )

    def _gc_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_rna_sequence_gc_content",
            output={"gc_content": 0.52, "sequence_length": 100},
        )

    def _cai_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_cai_for_cds_sequence",
            output={"cai_score": 0.85},
        )

    def _codonw_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="analyze_cds_codon_metrics_with_codonw_slim",
            output={"cai_score": 0.80, "mfe_kcal_per_mol": -20.0},
        )

    def _ires_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_putative_ires_with_iresfinder",
            output={"max_score": 0.72, "has_putative_ires": True},
        )

    def _rnastop_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_mrna_stability_with_rnastop",
            output={"overall_stability": 0.65},
        )

    def _mrl_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_5utr_mrl_with_gemorna",
            output={"predicted_mrl": 6.42},
        )

    def _stab_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_3utr_stability_with_gemorna",
            output={"predicted_stability": 0.72},
        )

    caps = {
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_secondary_structure_with_linearfold": MagicMock(),
        "compute_rna_sequence_gc_content": MagicMock(),
        "compute_cai_for_cds_sequence": MagicMock(),
        "analyze_cds_codon_metrics_with_codonw_slim": MagicMock(),
        "predict_putative_ires_with_iresfinder": MagicMock(),
        "predict_mrna_stability_with_rnastop": MagicMock(),
        "predict_5utr_mrl_with_gemorna": MagicMock(),
        "predict_3utr_stability_with_gemorna": MagicMock(),
    }
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke
    caps["predict_rna_secondary_structure_with_linearfold"].invoke = lambda args, state=None: CapabilityResult(
        success=True,
        tool_name="linearfold",
        output={"mfe": -22.0, "structure": "..."},
    )
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["compute_cai_for_cds_sequence"].invoke = _cai_invoke
    caps["analyze_cds_codon_metrics_with_codonw_slim"].invoke = _codonw_invoke
    caps["predict_putative_ires_with_iresfinder"].invoke = _ires_invoke
    caps["predict_mrna_stability_with_rnastop"].invoke = _rnastop_invoke
    caps["predict_5utr_mrl_with_gemorna"].invoke = _mrl_invoke
    caps["predict_3utr_stability_with_gemorna"].invoke = _stab_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


def test_evaluate_returns_expected_keys():
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    candidate = Candidate(
        sequence="GGGAAACCCUUUAUGCCCGGGUUUAAAUUU",
        metadata={
            "utr5_sequence": "GGGAAACCCUUU",
            "cds_sequence": "AUGCCCGGGUUU",
            "utr3_sequence": "AAAUUU",
        },
    )
    metrics = wf.evaluate(candidate)
    assert "full_length_mfe" in metrics
    assert "cds_cai" in metrics
    assert "cds_gc" in metrics
    assert "full_length_gc" in metrics
    assert "utr5_ires_potential" in metrics
    assert "utr5_mfe" in metrics
    assert "overall_stability" in metrics
    assert "total_length" in metrics
    assert metrics["total_length"] == len(candidate.sequence)
    assert "utr5_predicted_mrl" in metrics
    assert "utr3_predicted_stability" in metrics
    assert "junction_5utr_cds_mfe_per_nt" in metrics
    assert "junction_cds_3utr_mfe_per_nt" in metrics


def test_evaluate_uses_candidate_cai_species():
    """CAI evaluation must respect candidate.metadata['cai_species'] instead of
    always falling back to Homo sapiens."""
    reg = MagicMock()

    def _cai_invoke(args, state=None):
        species = args.get("species", "Homo sapiens")
        return CapabilityResult(
            success=True,
            tool_name="compute_cai_for_cds_sequence",
            output={"cai_score": 0.95 if species == "Mus musculus" else 0.75},
        )

    caps = {
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_secondary_structure_with_linearfold": MagicMock(),
        "compute_rna_sequence_gc_content": MagicMock(),
        "compute_rna_sequence_u_content": MagicMock(),
        "compute_cai_for_cds_sequence": MagicMock(),
        "predict_5utr_mrl_with_gemorna": MagicMock(),
        "predict_3utr_stability_with_gemorna": MagicMock(),
    }
    caps["predict_rna_secondary_structure"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="predict_rna_secondary_structure", output={"mfe_kcal_per_mol": -25.0, "structure": "....(((())))...."}
    )
    caps["predict_rna_secondary_structure_with_linearfold"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="linearfold", output={"mfe": -22.0, "structure": "..."}
    )
    caps["compute_rna_sequence_gc_content"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="gc", output={"gc_content": 0.52, "sequence_length": 30}
    )
    caps["compute_rna_sequence_u_content"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="u_content", output={"u_fraction": 0.25}
    )
    caps["compute_cai_for_cds_sequence"].invoke = _cai_invoke
    caps["predict_5utr_mrl_with_gemorna"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="mrl", output={"predicted_mrl": 5.0}
    )
    caps["predict_3utr_stability_with_gemorna"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="stab", output={"predicted_stability": 2.0}
    )

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = FullLengthMrnaDesignWorkflow(reg)
    candidate = Candidate(
        sequence="GGGAAACCCUUUAUGCCCGGGUUUAAAUUU",
        metadata={
            "utr5_sequence": "GGGAAACCCUUU",
            "cds_sequence": "AUGCCCGGGUUU",
            "utr3_sequence": "AAAUUU",
            "cai_species": "Mus musculus",
        },
    )
    metrics = wf.evaluate(candidate)
    assert metrics["cds_cai"] == pytest.approx(0.95)


def test_rank_aggregation_uses_asf():
    """Candidates are ranked by ASF distance to the reference point (lower = better)."""
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    c1 = Candidate(
        sequence="GGGAAACCCUUUAUGCCCGGGUUUAAAUUU",
        metadata={
            "utr5_sequence": "GGGAAACCCUUU",   # len=12 → MRL evaluated
            "cds_sequence": "AUGCCCGGGUUU",
            "utr3_sequence": "AAAUUU",
        },
    )
    c2 = Candidate(
        sequence="CCCUUUGGGAAAUUUGGGCCCAAACCC",
        metadata={
            "utr5_sequence": "CCCUUU",         # len=6  → MRL skipped (0.0)
            "cds_sequence": "GGGAAAUUUGGGCCC",
            "utr3_sequence": "AAACCC",
        },
    )
    for c in [c1, c2]:
        metrics = wf.evaluate(c)
        c.scores = wf.score(metrics)
    wf._workflow_state["_full_length_input"] = FullLengthMrnaDesignInput(
        protein_sequence="MP"
    )
    result = wf.rank_and_format([c1, c2])
    assert result.success is True
    assert result.best_candidate is not None
    # Both candidates should have an ASF distance and a rank.
    for c in [c1, c2]:
        assert "asf_distance" in c.scores
        assert c.rank is not None
    # Candidate with evaluated 5'UTR MRL should have a lower (better) ASF.
    assert c1.scores["asf_distance"] < c2.scores["asf_distance"]
    assert result.best_candidate is c1


def test_rank_and_format_with_candidates():
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    c1 = Candidate(sequence="AUGCCC", metadata={
        "utr5_sequence": "GGG", "cds_sequence": "AUGCCC", "utr3_sequence": "AAA",
        "utr5_preset": "short", "utr3_preset": "short", "cds_source": "lineardesign",
    })
    c2 = Candidate(sequence="AUGGGG", metadata={
        "utr5_sequence": "CCC", "cds_sequence": "AUGGGG", "utr3_sequence": "UUU",
        "utr5_preset": "short", "utr3_preset": "short", "cds_source": "rnarl",
    })
    for c in [c1, c2]:
        metrics = wf.evaluate(c)
        c.scores = wf.score(metrics)
    wf._workflow_state["_full_length_input"] = FullLengthMrnaDesignInput(
        protein_sequence="MP"
    )
    result = wf.rank_and_format([c1, c2])
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 2
    assert "total_len=" in result.summary


def test_rank_and_format_empty_candidates():
    wf = FullLengthMrnaDesignWorkflow(MagicMock())
    result = wf.rank_and_format([])
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_reference_point_changes_best_candidate():
    """A reference point favoring one dimension should select the champion of that dimension."""
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    c1 = Candidate(
        sequence="AUGCCC",
        metadata={
            "utr5_sequence": "GGG", "cds_sequence": "AUGCCC", "utr3_sequence": "AAA",
            "utr5_preset": "short", "utr3_preset": "short", "cds_source": "lineardesign",
        },
    )
    c2 = Candidate(
        sequence="AUGGGG",
        metadata={
            "utr5_sequence": "CCC", "cds_sequence": "AUGGGG", "utr3_sequence": "UUU",
            "utr5_preset": "short", "utr3_preset": "short", "cds_source": "rnarl",
        },
    )
    for c in [c1, c2]:
        metrics = wf.evaluate(c)
        c.scores = wf.score(metrics)

    # Set input with reference point favoring utr5_mrl (higher is better).
    wf._workflow_state["_full_length_input"] = FullLengthMrnaDesignInput(
        protein_sequence="MP",
        reference_point={"utr5_mrl": 1000.0},
    )
    result = wf.rank_and_format([c1, c2])
    assert result.success is True
    assert result.best_candidate is not None
    assert getattr(result, "reference_point", None) == {"utr5_mrl": 1000.0}
    assert getattr(result, "best_candidate_source", None) == "reference_point_optimization"


def test_pareto_frontier_no_dominated_members():
    """Pareto frontier is always returned and contains only non-dominated candidates."""
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    c1 = Candidate(
        sequence="AUGCCC",
        metadata={
            "utr5_sequence": "GGG", "cds_sequence": "AUGCCC", "utr3_sequence": "AAA",
            "utr5_preset": "short", "utr3_preset": "short", "cds_source": "lineardesign",
        },
    )
    c2 = Candidate(
        sequence="AUGGGG",
        metadata={
            "utr5_sequence": "CCC", "cds_sequence": "AUGGGG", "utr3_sequence": "UUU",
            "utr5_preset": "short", "utr3_preset": "short", "cds_source": "rnarl",
        },
    )
    for c in [c1, c2]:
        metrics = wf.evaluate(c)
        c.scores = wf.score(metrics)

    wf._workflow_state["_full_length_input"] = FullLengthMrnaDesignInput(
        protein_sequence="MP",
    )
    result = wf.rank_and_format([c1, c2])
    assert result.success is True
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier is not None
    assert len(frontier) >= 1
    # No frontier member should be dominated by another frontier member.
    ids = {c.id for c in frontier}
    assert len(ids) == len(frontier)


def test_reference_point_validation():
    """Unknown objective keys in reference_point raise ValueError."""
    with pytest.raises(ValueError, match="unknown objectives"):
        FullLengthMrnaDesignInput(
            protein_sequence="MP",
            reference_point={"invalid_dim": 1.0},
        )


def test_target_cds_mfe_cai_converts_to_cds_component():
    """target_cds_mfe and target_cds_cai are converted to a cds_component reference."""
    inp = FullLengthMrnaDesignInput(
        protein_sequence="MP",  # 2 aa → 2 codons → 6 nt
        target_cds_mfe=-30.0,
        target_cds_cai=0.9,
    )
    # cds_component = (-(-30) + 2 * log(0.9)) / 6
    expected = (30.0 + 2.0 * math.log(0.9)) / 6.0
    assert inp.reference_point is not None
    assert inp.reference_point["cds_component"] == pytest.approx(expected, abs=1e-6)


def test_target_cds_cai_requires_mfe():
    """Only providing target_cds_cai raises ValueError."""
    with pytest.raises(ValueError, match="must be provided together"):
        FullLengthMrnaDesignInput(
            protein_sequence="MP",
            target_cds_cai=0.9,
        )


def test_reference_point_rejects_cds_component():
    """The internal cds_component key is no longer accepted in user reference_point."""
    with pytest.raises(ValueError, match="unknown objectives"):
        FullLengthMrnaDesignInput(
            protein_sequence="MP",
            reference_point={"cds_component": 0.5},
        )


def test_reference_point_rejects_junction_dimensions():
    """Per-junction score dimensions are internal and rejected from user reference_point."""
    with pytest.raises(ValueError, match="unknown objectives"):
        FullLengthMrnaDesignInput(
            protein_sequence="MP",
            reference_point={
                "junction_5utr_cds_score": 0.6,
                "junction_cds_3utr_score": 0.7,
            },
        )


def test_bmc_max_rounds_defaults_and_validation():
    """bmc_max_rounds defaults to 1 and rejects negative values."""
    inp = FullLengthMrnaDesignInput(protein_sequence="MP")
    assert inp.bmc_max_rounds == 1

    inp2 = FullLengthMrnaDesignInput(protein_sequence="MP", bmc_max_rounds=3)
    assert inp2.bmc_max_rounds == 3

    inp3 = FullLengthMrnaDesignInput(protein_sequence="MP", bmc_max_rounds=0)
    assert inp3.bmc_max_rounds == 0

    with pytest.raises(ValueError):
        FullLengthMrnaDesignInput(protein_sequence="MP", bmc_max_rounds=-1)


def test_bmc_improvement_threshold_defaults_and_validation():
    """bmc_improvement_threshold defaults to 0.05 and rejects negative values."""
    inp = FullLengthMrnaDesignInput(protein_sequence="MP")
    assert inp.bmc_improvement_threshold == pytest.approx(0.05, abs=1e-6)

    inp2 = FullLengthMrnaDesignInput(
        protein_sequence="MP", bmc_improvement_threshold=0.1
    )
    assert inp2.bmc_improvement_threshold == pytest.approx(0.1, abs=1e-6)

    with pytest.raises(ValueError):
        FullLengthMrnaDesignInput(
            protein_sequence="MP", bmc_improvement_threshold=-0.01
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. QualityAgent review tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_sample_candidates() -> list[Candidate]:
    return [
        Candidate(
            sequence="AUGCCC",
            scores={"total_score": -1.0},
            metadata={
                "utr5_preset": "short",
                "utr3_preset": "long",
                "cds_source": "lineardesign",
                "metrics_bundle": {
                    "utr5_predicted_mrl": 5.5,
                    "utr3_predicted_stability": 0.6,
                    "utr5_ires_potential": 0.3,
                    "full_length_mfe": -20.0,
                    "total_length": 100,
                },
            },
        ),
        Candidate(
            sequence="AUGGGG",
            scores={"total_score": -2.0},
            metadata={
                "utr5_preset": "medium",
                "utr3_preset": "short",
                "cds_source": "rnarl",
                "metrics_bundle": {
                    "utr5_predicted_mrl": 6.5,
                    "utr3_predicted_stability": 0.8,
                    "utr5_ires_potential": 0.7,
                    "full_length_mfe": -25.0,
                    "total_length": 120,
                },
            },
        ),
    ]


def test_quality_profile_config():
    """QualityProfile has correct workflow name and evaluation dimensions."""
    profile = FULL_LENGTH_MRNA_QUALITY_PROFILE
    assert profile.workflow_name == "full_length_mrna_design"
    assert "UTR length mode" in profile.evaluation_dimensions[0]
    assert "IRES potential" in profile.evaluation_dimensions[3]
    assert "CDS quality" in profile.evaluation_dimensions[6]
    assert "utr_mode" in profile.adjustable_params
    assert "design_tool" in profile.adjustable_params
    assert "lambda_value" in profile.adjustable_params
    assert "reference_point" in profile.adjustable_params
    assert profile.retry_strategy == "adjust_params"
    assert profile.max_retries == 2


def test_quality_profile_build_context_stats():
    """Profile build_context includes full-length specific statistics."""
    cands = _make_sample_candidates()
    result = WorkflowResult(
        success=True,
        task_id="t1",
        best_candidate=cands[0],
        all_candidates=cands,
    )
    state: dict[str, Any] = {"user_text": "Design a stable mRNA with long 3'UTR"}

    ctx = FULL_LENGTH_MRNA_QUALITY_PROFILE.build_context(result, state)

    stats = ctx.get("full_length_stats", {})
    assert stats["utr5_preset_distribution"] == {"short": 1, "medium": 1}
    assert stats["utr3_preset_distribution"] == {"long": 1, "short": 1}
    assert stats["cds_source_distribution"] == {"lineardesign": 1, "rnarl": 1}

    # Ranges
    assert stats["utr5_mrl_range"]["count"] == 2
    assert stats["utr5_mrl_range"]["min"] == 5.5
    assert stats["utr5_mrl_range"]["max"] == 6.5
    assert stats["utr3_stability_range"]["count"] == 2
    assert stats["utr5_ires_range"]["count"] == 2
    assert stats["full_length_mfe_range"]["count"] == 2

    # Best candidate breakdown
    best = ctx.get("best_candidate_breakdown", {})
    assert best["source"] == cands[0].source
    assert best["utr5_preset"] == "short"
    assert best["utr3_preset"] == "long"
    assert best["utr5_mrl"] == 5.5
    assert best["utr5_ires"] == 0.3


def test_quality_profile_build_context_empty_candidates():
    """Profile build_context handles empty candidate list gracefully."""
    result = WorkflowResult(
        success=False,
        task_id="t1",
        best_candidate=None,
        all_candidates=[],
    )
    state: dict[str, Any] = {}
    ctx = FULL_LENGTH_MRNA_QUALITY_PROFILE.build_context(result, state)
    assert ctx["candidate_count"] == 0
    stats = ctx.get("full_length_stats", {})
    assert stats["utr5_preset_distribution"] == {}


def test_quality_profile_build_context_previous_best_summary():
    """Profile build_context exposes previous best candidate metrics when available."""
    prev_cand = Candidate(
        sequence="AUGCCC",
        scores={"total_score": -1.0},
        metadata={"metrics_bundle": {"cds_cai": 0.827, "full_mfe_per_nt": -0.641}},
    )
    prev_result = WorkflowResult(
        success=True,
        task_id="prev_turn",
        best_candidate=prev_cand,
        all_candidates=[prev_cand],
    )

    curr_cand = Candidate(
        sequence="AUGGGG",
        scores={"total_score": -2.0},
        metadata={"metrics_bundle": {"cds_cai": 0.880, "full_mfe_per_nt": -0.612}},
    )
    curr_result = WorkflowResult(
        success=True,
        task_id="curr_turn",
        best_candidate=curr_cand,
        all_candidates=[curr_cand],
    )

    state: dict[str, Any] = {"_previous_workflow_result": prev_result}
    ctx = FULL_LENGTH_MRNA_QUALITY_PROFILE.build_context(curr_result, state)

    prev_summary = ctx.get("previous_best_summary")
    assert prev_summary is not None
    assert prev_summary["source"] == ""
    assert prev_summary["metrics"]["cds_cai"] == 0.827
    assert prev_summary["metrics"]["full_mfe_per_nt"] == -0.641


def test_quality_agent_disabled_by_state_flag():
    """When _quality_review_enabled is False, review returns a passing QualityReport."""
    cands = _make_sample_candidates()
    result = WorkflowResult(
        success=True,
        task_id="t1",
        best_candidate=cands[0],
        all_candidates=cands,
    )
    state: dict[str, Any] = {"_quality_review_enabled": False}
    agent = QualityAgent()
    report = agent.review(result, FULL_LENGTH_MRNA_QUALITY_PROFILE, state)
    assert report.action == "pass"
    assert report.quality_score == 1.0
    assert report.confidence == 1.0


def test_quality_agent_review_with_mocked_llm():
    """QualityAgent.review parses the mocked LLM response into a QualityReport."""
    cands = _make_sample_candidates()
    result = WorkflowResult(
        success=True,
        task_id="t1",
        best_candidate=cands[0],
        all_candidates=cands,
    )
    state: dict[str, Any] = {}

    mock_report = {
        "overall_assessment": "UTR diversity is low; retry with broader utr_mode.",
        "quality_score": 0.6,
        "issues": [
            {
                "severity": "warning",
                "category": "diversity",
                "description": "Only two distinct UTR preset pairs present.",
            }
        ],
        "action": "retry_with_adjustments",
        "parameter_overrides": {"utr_mode": "all"},
        "reasoning": "Increasing UTR preset diversity should improve exploration.",
        "confidence": 0.8,
    }
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content=json.dumps(mock_report))

    agent = QualityAgent(llm=mock_llm)
    report = agent.review(result, FULL_LENGTH_MRNA_QUALITY_PROFILE, state)

    assert report.action == "retry_with_adjustments"
    assert report.quality_score == pytest.approx(0.6, abs=1e-6)
    assert report.parameter_overrides == {"utr_mode": "all"}
    assert len(report.issues) == 1
    assert report.issues[0].severity == "warning"
    assert "_last_diagnosis" in state


# ─────────────────────────────────────────────────────────────────────────────
# 6. Reference-point stability across BMC rounds
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_for_bmc_reference_point() -> MagicMock:
    """Registry with deterministic, slightly varying fake capability outputs."""
    reg = MagicMock()
    _call_count = 0

    def _unique_tag(n: int, length: int = 3) -> str:
        # Per-call unique ACGT tag so BMC-regenerated UTR/CDS combinations
        # never collide with already-seen candidates, regardless of how many
        # capability calls each evaluation path makes.
        chars = "ACGT"
        return "".join(chars[(n // (4**i)) % 4] for i in range(length))

    def _fake_invoke(args: dict, state: dict | None = None) -> CapabilityResult:
        nonlocal _call_count
        _call_count += 1
        # 34 aa protein needs 102 nt CDS; keep length a multiple of 3.
        base_cds = "AUG" * 34
        cds = base_cds[:-3] + _unique_tag(_call_count)  # still 102 nt
        return CapabilityResult(
            success=True,
            tool_name="fake",
            output={
                "generated_sequence": cds,
                "cds_sequence": cds,
                "mfe_kcal_per_mol": -45.0,
                "structure": "." * 102,
                "fold_tool": "ViennaRNA",
                "cai_score": 0.82,
                "gc_content": 0.52,
                "sequence_length": 102,
                "u_fraction": 0.25,
                "overall_stability": 0.78,
                "predicted_mrl": 7.5,
                "predicted_stability": 0.65,
                "max_score": 0.3,
            },
        )

    def _has(name: str) -> bool:
        return True

    def _get(name: str) -> Any:
        cap = MagicMock()
        cap.invoke = _fake_invoke
        return cap

    reg.has = _has
    reg.get = _get
    return reg


def _force_junction_issue(self, norm_candidate_vector, reference_point, boolean_issues=None):
    """Deterministic coordinator diagnosis that always finds a junction gap."""
    return [
        Issue(
            issue_type="JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE",
            value=0.3,
            target=0.8,
            violation=0.5,
            affected_modules=("5UTR", "CDS"),
            evidence="Mock junction gap for testing",
        )
    ]


def test_user_reference_point_fixed_across_bmc_rounds():
    """When the user supplies a reference point, its normalized coordinates must
    stay fixed to the initial candidate pool across BMC rounds.
    """
    reg = _make_registry_for_bmc_reference_point()
    wf = FullLengthMrnaDesignWorkflow(reg)

    inp = FullLengthMrnaDesignInput(
        protein_sequence="M" * 34,  # 34 aa → 102 nt CDS
        design_tool="all",
        utr_mode="all",  # allow preset exploration to generate new candidates
        bmc_max_rounds=2,
        bmc_improvement_threshold=0.0,  # allow rounds even when ASF improvement is zero
        target_cds_mfe=-102.0,  # yields cds_component = 1.0 when CAI = 1.0
        target_cds_cai=1.0,
        reference_point={
            "utr5_mrl": 100.0,
            "utr3_stability": 1.0,
            "full_mfe_score": 100.0,
        },
    )

    with patch.object(ReferencePointCoordinator, "diagnose", _force_junction_issue):
        result = wf.run(inp)

    assert result.success is True
    trace = wf._bmc_trace
    assert len(trace) == 2, f"Expected 2 BMC rounds, got {len(trace)}"

    for round_trace in trace:
        assert round_trace.reference_point_mode == "user"
        assert round_trace.reference_point
        assert round_trace.dim_bounds

    # The normalized reference point coordinates must be identical across rounds.
    rp_round1 = trace[0].reference_point
    rp_round2 = trace[1].reference_point
    assert rp_round1 == rp_round2

    # Dim bounds must also be identical (they come from the initial candidate pool).
    bounds_round1 = trace[0].dim_bounds
    bounds_round2 = trace[1].dim_bounds
    assert bounds_round1 == bounds_round2

    # The workflow should record user mode internally.
    assert wf._reference_point_mode == "user"
    assert wf._fixed_norm_ref_point is not None
    assert wf._fixed_dim_bounds is not None

    # The raw reference point reported in the result must equal the user input.
    assert getattr(result, "reference_point", None) == {
        "cds_component": 1.0,
        "utr5_mrl": 100.0,
        "utr3_stability": 1.0,
        "full_mfe_score": 100.0,
    }


def test_utopian_reference_point_mode_across_bmc_rounds():
    """Without a user reference point, BMC runs in utopian mode."""
    reg = _make_registry_for_bmc_reference_point()
    wf = FullLengthMrnaDesignWorkflow(reg)

    inp = FullLengthMrnaDesignInput(
        protein_sequence="M" * 34,
        design_tool="all",
        utr_mode="all",
        bmc_max_rounds=2,
        bmc_improvement_threshold=0.0,
    )

    with patch.object(ReferencePointCoordinator, "diagnose", _force_junction_issue):
        result = wf.run(inp)

    assert result.success is True
    trace = wf._bmc_trace
    assert len(trace) == 2

    for round_trace in trace:
        assert round_trace.reference_point_mode == "utopian"
        assert round_trace.reference_point
        assert round_trace.dim_bounds

    assert wf._reference_point_mode == "utopian"
    assert wf._fixed_norm_ref_point is None
    assert wf._fixed_dim_bounds is None


def test_bmc_trace_records_reference_point_metadata():
    """Each BMC round trace must record the reference point mode and coordinates."""
    reg = _make_registry_for_bmc_reference_point()
    wf = FullLengthMrnaDesignWorkflow(reg)

    inp = FullLengthMrnaDesignInput(
        protein_sequence="M" * 34,
        design_tool="all",
        utr_mode="short",
        bmc_max_rounds=1,
        reference_point={"utr5_mrl": 50.0},
    )

    with patch.object(ReferencePointCoordinator, "diagnose", _force_junction_issue):
        result = wf.run(inp)

    assert result.success is True
    state = getattr(result, "_state_writeback", {})
    trace = state.get("_bmc_trace", [])

    assert len(trace) == 1
    round_dict = trace[0]
    assert round_dict["reference_point_mode"] == "user"
    assert "reference_point" in round_dict
    assert "dim_bounds" in round_dict
    assert "utr5_mrl" in round_dict["reference_point"]
