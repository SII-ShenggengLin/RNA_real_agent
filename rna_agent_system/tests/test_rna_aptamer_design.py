"""Tests for RNA aptamer design workflow.

Covers:
1. score_aptamer_candidate unit scoring
2. RnaAptamerDesignInput Pydantic validation
3. Workflow integration with mocked capabilities
4. Critic retry logic
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.rna_aptamer_design import (
    RnaAptamerCritic,
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
    score_aptamer_candidate,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scoring function tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_aptamer_perfect_metrics():
    """All ideal metrics should produce a high total score."""
    metrics = {
        "gc_content": 0.50,
        "mfe_kcal_per_mol": -50.0,
        "rhofold_mean_plddt": 95.0,
        "egarps_native_probability": 0.90,
        "unpaired_fraction": 0.30,
    }
    scores = score_aptamer_candidate(metrics)
    assert scores["egarps_component"] == pytest.approx(0.90, abs=1e-6)
    assert scores["rhofold_component"] == pytest.approx(0.95, abs=1e-6)
    assert scores["mfe_component"] > 0.95  # sigmoid(-50) ≈ 0.997
    assert scores["gc_component"] == pytest.approx(1.0, abs=1e-6)
    assert scores["unpaired_component"] == pytest.approx(1.0, abs=1e-6)
    assert scores["total_score"] > 0.90


def test_score_aptamer_missing_metrics():
    """Missing metrics should contribute 0.0 for that component."""
    metrics = {
        "gc_content": 0.50,
        "mfe_kcal_per_mol": -20.0,
    }
    scores = score_aptamer_candidate(metrics)
    assert scores["egarps_component"] == 0.0
    assert scores["rhofold_component"] == 0.0
    assert scores["unpaired_component"] == 0.0
    assert scores["gc_component"] == pytest.approx(1.0, abs=1e-6)
    assert scores["mfe_component"] > 0.0


def test_score_aptamer_bad_gc():
    """GC far from 50% should penalise the score."""
    metrics = {"gc_content": 0.90}
    scores = score_aptamer_candidate(metrics)
    assert scores["gc_component"] < 0.1


def test_score_aptamer_unstable_mfe():
    """Positive MFE (unstable) should produce a low MFE component."""
    metrics = {"mfe_kcal_per_mol": 5.0}
    scores = score_aptamer_candidate(metrics)
    assert scores["mfe_component"] < 0.1


def test_score_aptamer_custom_weights():
    """Custom weights should shift the total score."""
    metrics = {
        "gc_content": 0.50,
        "mfe_kcal_per_mol": -20.0,
        "rhofold_mean_plddt": 50.0,
        "egarps_native_probability": 0.0,
        "unpaired_fraction": 0.30,
    }
    # With default weights, total is moderate
    default_scores = score_aptamer_candidate(metrics)
    # With high EGARPS weight but 0 EGARPS score, total should be lower
    low_egarps_scores = score_aptamer_candidate(
        metrics, weight_egarps=0.8, weight_rhofold=0.05, weight_mfe=0.05, weight_gc=0.05, weight_unpaired=0.05
    )
    assert low_egarps_scores["total_score"] < default_scores["total_score"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_defaults():
    inp = RnaAptamerDesignInput(protein_structure_path="test.pdb")
    assert inp.chain_id == "A"
    assert inp.aptamer_length == 30
    assert inp.n_odesign_samples == 5
    assert inp.odesign_seeds == [42]
    assert inp.weight_egarps == 0.35


def test_input_dict_coercion():
    raw = {
        "protein_structure_path": "test.pdb",
        "chain_id": "B",
        "aptamer_length": 45,
        "hotspot_residues": "B/10,B/20",
    }
    inp = RnaAptamerDesignInput(**raw)
    assert inp.chain_id == "B"
    assert inp.aptamer_length == 45
    assert inp.hotspot_residues == "B/10,B/20"


def test_input_invalid_aptamer_length_too_short():
    with pytest.raises(Exception):
        RnaAptamerDesignInput(protein_structure_path="test.pdb", aptamer_length=5)


def test_input_invalid_aptamer_length_too_long():
    with pytest.raises(Exception):
        RnaAptamerDesignInput(protein_structure_path="test.pdb", aptamer_length=250)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workflow integration tests (mocked capabilities)
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_capability(output: dict[str, Any]) -> MagicMock:
    cap = MagicMock()
    cap.invoke.return_value = CapabilityResult(
        success=True,
        tool_name="mock",
        output=output,
    )
    return cap


def _make_registry_for_generation() -> MagicMock:
    """Registry with mocked generation-phase capabilities."""
    reg = MagicMock()

    cap_hotspot = _make_mock_capability({
        "hotspot_residues": "A/18,A/90,A/79,A/49",
        "hotspot_patch_size": 4,
    })
    cap_json = _make_mock_capability({
        "input_json_filepath": "workspace/odesign_aptamer_input_test.json",
        "design_config": [],
    })
    cap_odesign = _make_mock_capability({
        "output_dir": "workspace/odesign_out",
        "prediction_filepaths": [
            "workspace/odesign_out/sample_0.cif",
            "workspace/odesign_out/sample_1.cif",
        ],
        "prediction_count": 2,
    })
    cap_extract = _make_mock_capability({
        "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        "chain_id": "B",
        "residue_count": 30,
    })

    caps = {
        "identify_protein_binding_hotspots": cap_hotspot,
        "build_odesign_aptamer_input_json": cap_json,
        "run_odesign_inference": cap_odesign,
        "extract_rna_sequence_from_cif": cap_extract,
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
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_secondary_structure",
            output={"mfe_kcal_per_mol": -25.0, "structure": "....(((())))...."},
        )

    def _unpaired_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="compute_dot_bracket_unpaired_fraction",
            output={"unpaired_fraction": 0.25, "structure_length": 16, "dot_count": 4},
        )

    def _rhofold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_tertiary_structure_with_rhofold",
            output={"pdb_filepath": "workspace/rhofold_test.pdb", "mean_plddt": 85.0},
        )

    def _egarps_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="score_rna_protein_complex_with_egarps",
            output={"native_probability": 0.72, "complex_id": "test"},
        )

    caps = {
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_secondary_structure_with_linearfold": MagicMock(),
        "compute_dot_bracket_unpaired_fraction": MagicMock(),
        "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
        "score_rna_protein_complex_with_egarps": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke
    caps["predict_rna_secondary_structure_with_linearfold"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="linearfold", output={"mfe": -22.0, "structure": "..."}
    )
    caps["compute_dot_bracket_unpaired_fraction"].invoke = _unpaired_invoke
    caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
    caps["score_rna_protein_complex_with_egarps"].invoke = _egarps_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


# Use a real temporary PDB file for generation tests
_TMP_PDB_PATH = "/tmp/test_protein.pdb"


def test_generate_candidates_with_mocked_odesign():
    """Mocked ODesign should produce candidates from prediction files."""
    reg = _make_registry_for_generation()
    wf = RnaAptamerDesignWorkflow(reg)
    inp = RnaAptamerDesignInput(
        protein_structure_path=_TMP_PDB_PATH,
        chain_id="A",
        aptamer_length=30,
    )
    candidates = wf.generate_candidates(inp)
    # extract_rna_sequence_from_cif returns same sequence for both files,
    # so after dedup we get 1 candidate
    assert len(candidates) == 1
    assert candidates[0].sequence == "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC"
    assert candidates[0].metadata["hotspot_residues"] == "A/18,A/90,A/79,A/49"


def test_generate_candidates_explicit_hotspot():
    """Explicit hotspot should skip auto-identification."""
    reg = _make_registry_for_generation()
    wf = RnaAptamerDesignWorkflow(reg)
    inp = RnaAptamerDesignInput(
        protein_structure_path=_TMP_PDB_PATH,
        hotspot_residues="C/100,C/200",
        aptamer_length=30,
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 1
    assert candidates[0].metadata["hotspot_residues"] == "C/100,C/200"


def test_generate_candidates_no_structure():
    """No structure path and no sequence should return empty list."""
    reg = _make_registry_for_generation()
    wf = RnaAptamerDesignWorkflow(reg)
    inp = RnaAptamerDesignInput(aptamer_length=30)
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 0


def test_evaluate_returns_expected_keys():
    reg = _make_registry_for_evaluation()
    wf = RnaAptamerDesignWorkflow(reg)
    candidate = Candidate(
        sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        metadata={"odesign_prediction_path": "workspace/test.pdb"},
    )
    metrics = wf.evaluate(candidate)
    assert "gc_content" in metrics
    assert "mfe_kcal_per_mol" in metrics
    assert "unpaired_fraction" in metrics
    assert "rhofold_mean_plddt" in metrics
    assert "egarps_native_probability" in metrics
    assert metrics["gc_content"] == pytest.approx(0.48, abs=1e-6)
    assert metrics["mfe_kcal_per_mol"] == pytest.approx(-25.0, abs=1e-6)
    assert metrics["rhofold_mean_plddt"] == pytest.approx(85.0, abs=1e-6)
    assert metrics["egarps_native_probability"] == pytest.approx(0.72, abs=1e-6)


def test_score_and_rank_pipeline():
    """Full pipeline: generate → evaluate → score → rank."""
    # Use a combined registry for both generation and evaluation
    reg = MagicMock()

    # Generation mocks
    gen_caps = {
        "identify_protein_binding_hotspots": _make_mock_capability({
            "hotspot_residues": "A/18,A/90",
            "hotspot_patch_size": 2,
        }),
        "build_odesign_aptamer_input_json": _make_mock_capability({
            "input_json_filepath": "workspace/odesign_input.json",
        }),
        "run_odesign_inference": _make_mock_capability({
            "prediction_filepaths": ["workspace/pred_0.cif"],
        }),
        "extract_rna_sequence_from_cif": _make_mock_capability({
            "sequence": "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        }),
    }

    # Evaluation mocks
    def _gc_invoke(args, state=None):
        return CapabilityResult(success=True, tool_name="gc", output={"gc_content": 0.48})
    def _fold_invoke(args, state=None):
        return CapabilityResult(success=True, tool_name="fold", output={"mfe_kcal_per_mol": -25.0, "structure": "((..))"})
    def _unpaired_invoke(args, state=None):
        return CapabilityResult(success=True, tool_name="unp", output={"unpaired_fraction": 0.25})
    def _rhofold_invoke(args, state=None):
        return CapabilityResult(success=True, tool_name="rho", output={"mean_plddt": 85.0, "pdb_filepath": "workspace/rho.pdb"})

    eval_caps = {
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_secondary_structure_with_linearfold": MagicMock(),
        "compute_dot_bracket_unpaired_fraction": MagicMock(),
        "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
        "score_rna_protein_complex_with_egarps": MagicMock(),
    }
    eval_caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    eval_caps["predict_rna_secondary_structure"].invoke = _fold_invoke
    eval_caps["predict_rna_secondary_structure_with_linearfold"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="lf", output={"mfe": -22.0, "structure": "..."}
    )
    eval_caps["compute_dot_bracket_unpaired_fraction"].invoke = _unpaired_invoke
    eval_caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
    eval_caps["score_rna_protein_complex_with_egarps"].invoke = lambda args, state=None: CapabilityResult(
        success=True, tool_name="egarps", output={"native_probability": 0.65}
    )

    all_caps = {**gen_caps, **eval_caps}
    reg.has = lambda name: name in all_caps
    reg.get = lambda name: all_caps[name]

    wf = RnaAptamerDesignWorkflow(reg)
    inp = RnaAptamerDesignInput(protein_structure_path=_TMP_PDB_PATH, aptamer_length=30)
    result = wf.run(inp)

    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) == 1
    assert result.best_candidate.scores["total_score"] > 0.0
    assert "EGARPS=" in result.summary or "RhoFold=" in result.summary


def test_rank_and_format_empty_candidates():
    wf = RnaAptamerDesignWorkflow(MagicMock())
    result = wf.rank_and_format([])
    assert result.success is False
    assert "empty_candidate_list" in result.errors


# ─────────────────────────────────────────────────────────────────────────────
# 4. Critic tests
# ─────────────────────────────────────────────────────────────────────────────


def _make_aptamer_candidates(
    gc_values: list[float],
    egarps_values: list[Optional[float]] = None,
) -> list[Candidate]:
    egarps_values = egarps_values or [None] * len(gc_values)
    cands: list[Candidate] = []
    for i, (gc, ep) in enumerate(zip(gc_values, egarps_values)):
        mb: dict[str, Any] = {"gc_content": gc}
        if ep is not None:
            mb["egarps_native_probability"] = ep
        cands.append(Candidate(
            sequence=f"SEQ{i}", scores={},
            metadata={"metrics_bundle": mb},
        ))
    return cands


def test_critic_retry_when_too_few_gc_ok():
    """Only 2 candidates with GC in [0.2, 0.8] → retry."""
    critic = RnaAptamerCritic()
    cands = _make_aptamer_candidates([0.15, 0.25, 0.90])
    result = WorkflowResult(success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands)
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is True
    assert state["next_constraints"]["adjust_aptamer_length"] is True


def test_critic_no_retry_when_gc_ok_sufficient():
    """3 candidates with GC in [0.2, 0.8] → no retry."""
    critic = RnaAptamerCritic()
    cands = _make_aptamer_candidates([0.25, 0.50, 0.75])
    result = WorkflowResult(success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands)
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False


def test_critic_retry_when_all_egarps_poor():
    """All EGARPS scores < 0.3 → retry (needs ≥3 candidates to pass GC filter first)."""
    critic = RnaAptamerCritic()
    cands = _make_aptamer_candidates(
        [0.50, 0.50, 0.50], egarps_values=[0.20, 0.25, 0.10]
    )
    result = WorkflowResult(success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands)
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is True
    assert state["next_constraints"]["expand_hotspot_region"] is True


def test_critic_no_retry_when_some_egarps_good():
    """At least one EGARPS score ≥ 0.3 → no retry."""
    critic = RnaAptamerCritic()
    cands = _make_aptamer_candidates(
        [0.50, 0.50, 0.50], egarps_values=[0.20, 0.50, 0.10]
    )
    result = WorkflowResult(success=True, task_id="t1", best_candidate=cands[0], all_candidates=cands)
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False


def test_critic_no_retry_empty_candidates():
    """Empty candidate list → no retry."""
    critic = RnaAptamerCritic()
    result = WorkflowResult(success=False, task_id="t1", best_candidate=None, all_candidates=[])
    state: dict[str, Any] = {}
    assert critic.should_retry(result, state) is False
