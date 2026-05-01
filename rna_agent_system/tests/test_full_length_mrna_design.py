"""Tests for full-length mRNA design workflow.

Covers:
1. score_full_length_mrna_candidate unit scoring
2. FullLengthMrnaDesignInput Pydantic validation
3. UTR combination generation logic (6 × 9 = 54 candidates)
4. Workflow integration with mocked capabilities
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaCritic,
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
    inp = FullLengthMrnaDesignInput(protein_sequence="MKT")
    assert inp.design_tool == "all"
    assert inp.lambda_value == 0.0
    assert inp.model_type == "Homo sapiens mRNA"
    assert inp.utr_mode == "all"
    assert inp.run_fold is True
    assert inp.run_gc is True
    assert inp.run_fold is True
    assert inp.run_gc is True


def test_input_valid_tools():
    for tool in ("lineardesign", "rnarl", "gemorna", "all"):
        inp = FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool=tool)
        assert inp.design_tool == tool


def test_input_valid_utr_modes():
    for mode in ("short", "medium", "long", "all"):
        inp = FullLengthMrnaDesignInput(protein_sequence="MKT", utr_mode=mode)
        assert inp.utr_mode == mode


def test_input_invalid_design_tool():
    with pytest.raises(Exception):
        FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool="invalid")


def test_input_invalid_utr_mode():
    with pytest.raises(Exception):
        FullLengthMrnaDesignInput(protein_sequence="MKT", utr_mode="extra_long")


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


def _make_mock_capability(output: dict[str, Any]) -> MagicMock:
    cap = MagicMock()
    cap.invoke.return_value = CapabilityResult(
        success=True,
        tool_name="mock",
        output=output,
    )
    return cap


def _make_registry_with_mocks() -> MagicMock:
    """Build a mock registry that returns deterministic sequences for every tool."""
    reg = MagicMock()

    # CDS tools
    cap_ld = _make_mock_capability({"generated_sequence": "AUGCCCGGGUUU"})
    cap_rnarl = _make_mock_capability({"generated_sequence": "AUGGGGCCCUUU"})
    cap_gemorna_cds = _make_mock_capability({"generated_sequence": "AUGUUUGGGCCC"})

    # UTR tools
    cap_utr5_short = _make_mock_capability({"generated_sequence": "GGGAAA"})
    cap_utr5_medium = _make_mock_capability({"generated_sequence": "GGGAAACCCUUU"})
    cap_utr5_long = _make_mock_capability({"generated_sequence": "GGGAAACCCUUUGGGAAA"})
    cap_utr3_short = _make_mock_capability({"generated_sequence": "AAAUUU"})
    cap_utr3_medium = _make_mock_capability({"generated_sequence": "AAAUUUGGGCCC"})
    cap_utr3_long = _make_mock_capability({"generated_sequence": "AAAUUUGGGCCCUUUAAA"})

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
    inp = FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool="all")
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
    cap = _make_mock_capability({"generated_sequence": "AUGCCC"})

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
    inp = FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool="all")
    candidates = wf.generate_candidates(inp)
    # 1 unique CDS × 3 UTR5 × 3 UTR3 = 9 unique full sequences
    assert len(candidates) == 9


def test_generate_candidates_skips_cds_not_multiple_of_3():
    """CDS length must be a multiple of 3; non-conforming candidates are skipped."""
    reg = MagicMock()
    cap = _make_mock_capability({"generated_sequence": "AUGCC"})  # 5 nt — bad
    caps = {
        "design_mrna_cds_with_lineardesign": cap,
        "design_5utr_with_gemorna": _make_mock_capability({"generated_sequence": "UUU"}),
        "design_3utr_with_gemorna": _make_mock_capability({"generated_sequence": "AAA"}),
    }
    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]

    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool="lineardesign")
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 0


def test_generate_candidates_utr_mode_filter():
    """utr_mode='short' should produce only 1 UTR preset per end → 1 combo per CDS."""
    reg = _make_registry_with_mocks()
    wf = FullLengthMrnaDesignWorkflow(reg)
    inp = FullLengthMrnaDesignInput(protein_sequence="MKT", design_tool="all", utr_mode="short")
    candidates = wf.generate_candidates(inp)
    # 3 unique CDS × 1 UTR5(short) × 1 UTR3(short) = 3
    assert len(candidates) == 3
    for c in candidates:
        assert c.metadata["utr5_preset"] == "short"
        assert c.metadata["utr3_preset"] == "short"


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
    assert "utr5_ires_potential" in metrics
    assert "utr5_mfe" in metrics
    assert "overall_stability" in metrics
    assert "total_length" in metrics
    assert metrics["total_length"] == len(candidate.sequence)
    assert "utr5_predicted_mrl" in metrics
    assert "utr3_predicted_stability" in metrics


def test_rank_aggregation_produces_total_rank():
    """Rank aggregation (Borda count): each module sorted independently,
    ranks summed, candidates ordered by total_rank."""
    reg = _make_registry_for_eval()
    wf = FullLengthMrnaDesignWorkflow(reg)
    c1 = Candidate(
        sequence="GGGAAACCCUUUAUGCCCGGGUUUAAAUUU",
        metadata={
            "utr5_sequence": "GGGAAACCCUUU",
            "cds_sequence": "AUGCCCGGGUUU",
            "utr3_sequence": "AAAUUU",
        },
    )
    c2 = Candidate(
        sequence="CCCUUUGGGAAAUUUGGGCCCAAACCC",
        metadata={
            "utr5_sequence": "CCCUUU",
            "cds_sequence": "GGGAAAUUUGGGCCC",
            "utr3_sequence": "AAACCC",
        },
    )
    for c in [c1, c2]:
        metrics = wf.evaluate(c)
        c.scores = wf.score(metrics)
    result = wf.rank_and_format([c1, c2])
    # With identical mock values, stable sort gives c1 rank=1 in each
    # module, c2 rank=2 → total_rank c1=3, c2=6
    assert result.success is True
    assert result.best_candidate is c1
    assert c1.scores["total_rank"] == 3
    assert c2.scores["total_rank"] == 6
    assert c1.scores["cds_rank"] == 1
    assert c2.scores["cds_rank"] == 2


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


# ─────────────────────────────────────────────────────────────────────────────
# 5. Critic tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_candidates(good: int, bad: int, missing: int = 0) -> list[Candidate]:
    """Helper to build candidate lists for critic tests.

    good  → IRES potential = 0.3 (below threshold)
    bad   → IRES potential = 0.8 (above threshold)
    missing → no utr5_ires_potential key at all
    """
    cands: list[Candidate] = []
    for i in range(good):
        cands.append(Candidate(
            sequence=f"GOOD{i}", scores={},
            metadata={"metrics_bundle": {"utr5_ires_potential": 0.3}},
        ))
    for i in range(bad):
        cands.append(Candidate(
            sequence=f"BAD{i}", scores={},
            metadata={"metrics_bundle": {"utr5_ires_potential": 0.8}},
        ))
    for i in range(missing):
        cands.append(Candidate(
            sequence=f"MISS{i}", scores={},
            metadata={"metrics_bundle": {}},
        ))
    return cands


def test_critic_no_retry_when_remaining_sufficient():
    """7 good + 3 bad → 7 remain ≥ 5 → no retry."""
    critic = FullLengthMrnaCritic()
    cands = _make_candidates(good=7, bad=3)
    result = WorkflowResult(
        success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False
    assert "next_constraints" not in state


def test_critic_retry_when_remaining_below_threshold():
    """3 good + 7 bad → 3 remain < 5 → retry."""
    critic = FullLengthMrnaCritic()
    cands = _make_candidates(good=3, bad=7)
    result = WorkflowResult(
        success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is True
    assert state["next_constraints"]["avoid_ires_in_5utr"] is True


def test_critic_no_retry_when_remaining_equals_min():
    """5 good + 5 bad → 5 remain == 5 → no retry."""
    critic = FullLengthMrnaCritic()
    cands = _make_candidates(good=5, bad=5)
    result = WorkflowResult(
        success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False


def test_critic_retry_when_all_ires_missing_and_total_below_min():
    """4 candidates all missing IRES → 4 remain < 5 → retry."""
    critic = FullLengthMrnaCritic()
    cands = _make_candidates(good=0, bad=0, missing=4)
    result = WorkflowResult(
        success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is True
    assert state["next_constraints"]["avoid_ires_in_5utr"] is True


def test_critic_no_retry_when_all_ires_missing_but_total_sufficient():
    """6 candidates all missing IRES → 6 remain ≥ 5 → no retry."""
    critic = FullLengthMrnaCritic()
    cands = _make_candidates(good=0, bad=0, missing=6)
    result = WorkflowResult(
        success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands
    )
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False


def test_critic_no_best_candidate():
    """Empty candidate list → no retry."""
    critic = FullLengthMrnaCritic()
    result = WorkflowResult(success=False, task_id="t1", best_candidate=None, all_candidates=[])
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False
