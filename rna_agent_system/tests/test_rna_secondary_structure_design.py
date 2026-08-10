"""Tests for RNA secondary-structure-guided sequence design workflow.

Covers:
1. score_secondary_structure_design_candidate unit scoring
2. RnaSecondaryStructureDesignInput Pydantic validation
3. Workflow integration with mocked capabilities
"""

from __future__ import annotations


from unittest.mock import MagicMock

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.rna_secondary_structure_design import (
    RnaSecondaryStructureDesignInput,
    RnaSecondaryStructureDesignWorkflow,
    score_secondary_structure_design_candidate,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Scoring function tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_secondary_perfect_metrics():
    """Perfect match: distance_ratio = 0, mfe = raw value."""
    metrics = {
        "sequence_length": 100,
        "structure_distance": 0,
        "vienna_mfe": -30.0,
    }
    scores = score_secondary_structure_design_candidate(metrics)
    assert scores["structure_distance_ratio"] == pytest.approx(0.0, abs=1e-6)
    assert scores["mfe"] == pytest.approx(-30.0, abs=1e-6)
    # total_score is driven solely by structure fidelity (smaller = better)
    assert scores["total_score"] == pytest.approx(0.0, abs=1e-6)


def test_score_secondary_missing_metrics():
    """Missing mfe should omit the key; missing distance defaults to 1.0."""
    metrics = {"sequence_length": 100, "structure_distance": 5}
    scores = score_secondary_structure_design_candidate(metrics)
    assert scores["structure_distance_ratio"] == pytest.approx(0.05, abs=1e-6)
    assert "mfe" not in scores


def test_score_secondary_mfe_raw():
    """MFE is returned as raw value without normalization."""
    strong = {"sequence_length": 100, "vienna_mfe": -30.0}
    assert score_secondary_structure_design_candidate(strong)["mfe"] == pytest.approx(-30.0)

    weak = {"sequence_length": 100, "vienna_mfe": -5.0}
    assert score_secondary_structure_design_candidate(weak)["mfe"] == pytest.approx(-5.0)


def test_score_secondary_structure_distance():
    """Structure distance ratio = distance / length (smaller = better)."""
    dist10 = {"sequence_length": 100, "structure_distance": 10}
    assert score_secondary_structure_design_candidate(dist10)[
        "structure_distance_ratio"
    ] == pytest.approx(0.10, abs=1e-6)

    dist100 = {"sequence_length": 100, "structure_distance": 100}
    assert score_secondary_structure_design_candidate(dist100)[
        "structure_distance_ratio"
    ] == pytest.approx(1.0, abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_defaults():
    inp = RnaSecondaryStructureDesignInput(target_structure="(((...)))")
    assert inp.repeats == 10
    assert inp.num_invocations == 3
    assert inp.temp_c == 37.0
    assert inp.function_mode == "m"


def test_input_dict_coercion():
    raw = {
        "target_structure": "((((....))))",
        "repeats": 50,
        "num_invocations": 5,
        "temp_c": 25.0,
        "function_mode": "mp",
    }
    inp = RnaSecondaryStructureDesignInput(**raw)
    assert inp.repeats == 50
    assert inp.num_invocations == 5
    assert inp.temp_c == 25.0
    assert inp.function_mode == "mp"


def test_input_invalid_function_mode():
    with pytest.raises(Exception):
        RnaSecondaryStructureDesignInput(target_structure="(((...)))", function_mode="x")


def test_input_invalid_repeats_too_low():
    with pytest.raises(Exception):
        RnaSecondaryStructureDesignInput(target_structure="(((...)))", repeats=0)


def test_input_invalid_repeats_too_high():
    with pytest.raises(Exception):
        RnaSecondaryStructureDesignInput(target_structure="(((...)))", repeats=501)


def test_input_invalid_num_invocations_too_high():
    with pytest.raises(Exception):
        RnaSecondaryStructureDesignInput(target_structure="(((...)))", num_invocations=11)


def test_input_start_sequence_length_mismatch():
    """Start sequence with mismatched length is accepted by Pydantic but caught at runtime."""
    inp = RnaSecondaryStructureDesignInput(
        target_structure="(((...)))", start_sequence="AUGC"
    )
    assert inp.start_sequence == "AUGC"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workflow integration tests (mocked capabilities)
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_for_generation(num_unique: int = 2) -> MagicMock:
    """Registry with mocked inverse-fold capability returning deterministic sequences."""
    reg = MagicMock()

    # Produce slightly different sequences per invocation so deduplication is tested
    base_seqs = ["AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC", "GCAUGCAUGCAUGCAUGCAUGCAUGCAUGC"]

    def _inverse_invoke(args, state=None):
        invocation = args.get("repeats", 10)
        # Use repeats value to pick a sequence so different calls can return different results
        seq = base_seqs[invocation % len(base_seqs)]
        return CapabilityResult(
            success=True,
            tool_name="inverse_fold_rna_secondary_structure_vienna",
            output={
                "best_sequence": seq,
                "hamming_distance": 2,
                "partition_probability": 0.85,
                "target_structure": "((((....))))....((((....))))",
            },
        )

    cap_inverse = MagicMock()
    cap_inverse.invoke = _inverse_invoke

    caps = {
        "inverse_fold_rna_secondary_structure_vienna": cap_inverse,
    }

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


def _make_registry_for_evaluation() -> MagicMock:
    """Registry with mocked evaluation-phase capabilities."""
    reg = MagicMock()

    def _gc_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_rna_sequence_gc_content",
            output={"gc_content": 0.48, "sequence_length": 30},
        )

    def _fold_invoke(args, state=None):
        # Return the exact target structure for perfect structure_distance_ratio
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_secondary_structure",
            output={
                "structure": "((((....))))....((((....))))",
                "mfe_kcal_per_mol": -15.5,
                "backend": "ViennaRNA",
            },
        )

    caps = {
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


def test_generate_candidates():
    """Generate candidates from inverse fold with multiple invocations."""
    reg = _make_registry_for_generation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    inp = RnaSecondaryStructureDesignInput(
        target_structure="((((....))))....((((....))))",
        num_invocations=3,
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) >= 1
    assert all(c.source.startswith("vienna_inverse_") for c in candidates)


def test_generate_candidates_empty_target():
    """Empty target structure should yield empty candidates."""
    reg = _make_registry_for_generation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    inp = RnaSecondaryStructureDesignInput(target_structure="   ")
    candidates = wf.generate_candidates(inp)
    assert candidates == []


def test_generate_candidates_start_sequence_mismatch():
    """Mismatched start sequence length should yield empty candidates."""
    reg = _make_registry_for_generation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    inp = RnaSecondaryStructureDesignInput(
        target_structure="((((....))))....((((....))))",
        start_sequence="AUGC",  # too short
    )
    candidates = wf.generate_candidates(inp)
    assert candidates == []


def test_generate_candidates_capability_missing():
    """If capabilities are missing, generation should gracefully return empty."""
    reg = MagicMock()
    reg.has.return_value = False
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    inp = RnaSecondaryStructureDesignInput(target_structure="(((...)))")
    candidates = wf.generate_candidates(inp)
    assert candidates == []


def test_evaluate_candidate():
    """Evaluate a single candidate with mocked tools."""
    reg = _make_registry_for_evaluation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    candidate = Candidate(
        sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        sequence_type="rna",
        source="vienna_inverse_0",
        metadata={
            "target_structure": "((((....))))....((((....))))",
            "tool_metadata": {"hamming_distance": 2},
        },
    )
    metrics = wf.evaluate(candidate)
    assert metrics["gc_content"] == pytest.approx(0.48)
    assert metrics["vienna_mfe"] == pytest.approx(-15.5)
    assert metrics["folded_structure"] == "((((....))))....((((....))))"
    assert metrics["structure_distance"] == 0  # exact match
    assert metrics["hamming_distance"] == 2


def test_score_candidate():
    """Score raw metrics into components (smaller total_score = better)."""
    reg = _make_registry_for_evaluation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    wf._workflow_state["_secondary_design_input"] = RnaSecondaryStructureDesignInput(
        target_structure="(((...)))"
    )
    metrics = {
        "sequence_length": 100,
        "structure_distance": 0,
        "vienna_mfe": -20.0,
    }
    scores = wf.score(metrics)
    assert scores["structure_distance_ratio"] == pytest.approx(0.0)
    assert scores["mfe"] == pytest.approx(-20.0)
    assert scores["total_score"] == pytest.approx(0.0, abs=1e-6)


def test_rank_and_format():
    """Rank candidates and build a WorkflowResult (smaller total_score = better)."""
    reg = _make_registry_for_evaluation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    candidates = [
        Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            sequence_type="rna",
            source="vienna_inverse_0",
            scores={"total_score": 0.0},
            metadata={
                "metrics_bundle": {"gc_content": 0.48, "vienna_mfe": -15.5, "structure_distance": 0}
            },
        ),
        Candidate(
            sequence="GCAUGCAUGCAUGCAUGCAUGCAUGCAUGC",
            sequence_type="rna",
            source="vienna_inverse_1",
            scores={"total_score": 0.067},
            metadata={
                "metrics_bundle": {"gc_content": 0.52, "vienna_mfe": -12.0, "structure_distance": 2}
            },
        ),
    ]
    result = wf.rank_and_format(candidates)
    assert result.success is True
    assert result.best_candidate is not None
    assert result.best_candidate.source == "vienna_inverse_0"
    assert len(result.all_candidates) == 2
    assert "candidates=2" in result.summary


def test_rank_and_format_empty():
    """Empty candidates should produce a failed WorkflowResult."""
    reg = _make_registry_for_evaluation()
    wf = RnaSecondaryStructureDesignWorkflow(reg)
    result = wf.rank_and_format([])
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_full_pipeline_mocked():
    """Run the full workflow with mocked generation + evaluation."""
    reg = MagicMock()

    # Combine generation + evaluation mocks
    gen_caps = _make_registry_for_generation()
    eval_caps = _make_registry_for_evaluation()

    all_caps = {}
    all_caps["inverse_fold_rna_secondary_structure_vienna"] = gen_caps.get(
        "inverse_fold_rna_secondary_structure_vienna"
    )
    for name in ["compute_rna_sequence_gc_content", "predict_rna_secondary_structure"]:
        all_caps[name] = eval_caps.get(name)

    reg.has = lambda name: name in all_caps
    reg.get = lambda name: all_caps[name]

    wf = RnaSecondaryStructureDesignWorkflow(reg)
    inp = RnaSecondaryStructureDesignInput(
        target_structure="((((....))))....((((....))))",
        num_invocations=2,
    )
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) >= 1
    assert result.best_candidate.scores.get("total_score") is not None


