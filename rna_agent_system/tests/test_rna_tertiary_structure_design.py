"""Tests for RNA tertiary-structure-guided sequence design workflow.

Covers:
1. score_tertiary_structure_design_candidate unit scoring
2. RnaTertiaryStructureDesignInput Pydantic validation
3. Workflow integration with mocked capabilities
4. Critic retry logic (pLDDT threshold + hard retry limit)
"""

from __future__ import annotations

from tests.helpers import make_mock_capability

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignInput,
    RnaTertiaryStructureDesignWorkflow,
    score_tertiary_structure_design_candidate,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Scoring function tests
# ─────────────────────────────────────────────────────────────────────────────


def test_score_perfect_metrics():
    """Ideal pLDDT and RMSD should produce a high total score."""
    metrics = {
        "rhofold_mean_plddt": 95.0,
        "alignment_rmsd": 1.0,
    }
    scores = score_tertiary_structure_design_candidate(metrics)
    assert scores["rhofold_component"] == pytest.approx(0.95, abs=1e-6)
    assert scores["rmsd_component"] == pytest.approx(1.0 - 1.0 / 5.0, abs=1e-6)
    expected_total = 0.5 * 0.95 + 0.5 * (1.0 - 1.0 / 5.0)
    assert scores["total_score"] == pytest.approx(expected_total, abs=1e-6)


def test_score_missing_metrics():
    """Missing metrics should contribute 0.0 for that component."""
    metrics = {"rhofold_mean_plddt": 50.0}
    scores = score_tertiary_structure_design_candidate(metrics)
    assert scores["rhofold_component"] == pytest.approx(0.50, abs=1e-6)
    assert scores["rmsd_component"] == 0.0
    assert scores["total_score"] == pytest.approx(0.25, abs=1e-6)


def test_score_rmsd_edges():
    """RMSD component should be 0 at >=5 Å and 1 at 0 Å."""
    perfect = {"alignment_rmsd": 0.0}
    assert score_tertiary_structure_design_candidate(perfect)["rmsd_component"] == pytest.approx(1.0)

    poor = {"alignment_rmsd": 10.0}
    assert score_tertiary_structure_design_candidate(poor)["rmsd_component"] == pytest.approx(0.0)

    mid = {"alignment_rmsd": 2.5}
    assert score_tertiary_structure_design_candidate(mid)["rmsd_component"] == pytest.approx(0.5)


def test_score_custom_weights():
    """Custom weights should be respected."""
    metrics = {"rhofold_mean_plddt": 100.0, "alignment_rmsd": 0.0}
    scores = score_tertiary_structure_design_candidate(
        metrics, weight_rhofold=0.8, weight_rmsd=0.2
    )
    assert scores["total_score"] == pytest.approx(1.0, abs=1e-6)

    scores2 = score_tertiary_structure_design_candidate(
        metrics, weight_rhofold=0.2, weight_rmsd=0.8
    )
    assert scores2["total_score"] == pytest.approx(1.0, abs=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pydantic input validation tests
# ─────────────────────────────────────────────────────────────────────────────


def test_input_defaults():
    inp = RnaTertiaryStructureDesignInput(structure_filepath="test.pdb")
    assert inp.design_tools == "all"
    assert inp.n_samples_per_tool == 3
    assert inp.rhodesign_temperature == 0.1
    assert inp.rhodesign_temperature_range == 0.05
    assert inp.ribodiffusion_sampling_steps == 50


def test_input_dict_coercion():
    raw = {
        "structure_filepath": "test.cif",
        "design_tools": "rhodesign",
        "n_samples_per_tool": 5,
        "rhodesign_temperature": 0.5,
    }
    inp = RnaTertiaryStructureDesignInput(**raw)
    assert inp.design_tools == "rhodesign"
    assert inp.n_samples_per_tool == 5
    assert inp.rhodesign_temperature == 0.5


def test_input_invalid_tool():
    with pytest.raises(Exception):
        RnaTertiaryStructureDesignInput(structure_filepath="test.pdb", design_tools="unknown")


def test_input_invalid_n_samples_too_low():
    with pytest.raises(Exception):
        RnaTertiaryStructureDesignInput(structure_filepath="test.pdb", n_samples_per_tool=0)


def test_input_invalid_n_samples_too_high():
    with pytest.raises(Exception):
        RnaTertiaryStructureDesignInput(structure_filepath="test.pdb", n_samples_per_tool=25)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workflow integration tests (mocked capabilities)
# ─────────────────────────────────────────────────────────────────────────────


def _make_registry_for_generation() -> MagicMock:
    """Registry with mocked generation-phase capabilities."""
    reg = MagicMock()

    # RhoDesign: return a different sequence on each call so dedup keeps them all
    _rhodesign_call_count = 0
    _rhodesign_seqs = [
        "AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        "AUGCAUGCAUGCAUGCAUGCAUGCAUGCAU",
        "GGCCAUUGGCCAUUGGCCAUUGGCCAUUGG",
    ]

    def _rhodesign_invoke(args, state=None):
        nonlocal _rhodesign_call_count
        seq = _rhodesign_seqs[_rhodesign_call_count % len(_rhodesign_seqs)]
        _rhodesign_call_count += 1
        return CapabilityResult(
            success=True,
            tool_name="design_rna_sequence_with_rhodesign",
            output={
                "predicted_sequence": seq,
                "recovery_rate": 0.85,
                "output_fasta_filepath": "workspace/rhodesign_out.fasta",
                "input_pdb_filepath": "/tmp/test_structure.pdb",
            },
        )

    cap_rhodesign = MagicMock()
    cap_rhodesign.invoke = _rhodesign_invoke

    cap_ribodiffusion = make_mock_capability({
        "predicted_sequence": "CCGAUCCGAUCCGAUCCGAUCCGAUCCGAU",
        "generated_sequences": ["CCGAUCCGAUCCGAUCCGAUCCGAUCCGAU", "UUAGCUUAGCUUAGCUUAGCUUAGCUUAGC"],
        "recovery_rate": 0.72,
        "output_fasta_filepaths": ["workspace/ribodiffusion_0.fasta", "workspace/ribodiffusion_1.fasta"],
        "input_pdb_filepath": "/tmp/test_structure.pdb",
    })

    caps = {
        "design_rna_sequence_with_rhodesign": cap_rhodesign,
        "design_rna_inverse_fold_with_ribodiffusion": cap_ribodiffusion,
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
            output={
                "structure": "((((....))))....((((....))))",
                "mfe_kcal_per_mol": -15.5,
                "backend": "ViennaRNA",
            },
        )

    def _rhofold_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="predict_rna_tertiary_structure_with_rhofold",
            output={"pdb_filepath": "workspace/rhofold_test.pdb", "mean_plddt": 85.0},
        )

    def _alignment_invoke(args, state=None):
        return CapabilityResult(
            success=True,
            tool_name="score_structure_alignment",
            output={
                "rmsd": 2.1,
                "tm_score": 0.88,
                "aligned_residue_count": 30,
            },
        )

    caps = {
        "compute_rna_sequence_gc_content": MagicMock(),
        "predict_rna_secondary_structure": MagicMock(),
        "predict_rna_tertiary_structure_with_rhofold": MagicMock(),
        "score_structure_alignment": MagicMock(),
    }
    caps["compute_rna_sequence_gc_content"].invoke = _gc_invoke
    caps["predict_rna_secondary_structure"].invoke = _fold_invoke
    caps["predict_rna_tertiary_structure_with_rhofold"].invoke = _rhofold_invoke
    caps["score_structure_alignment"].invoke = _alignment_invoke

    reg.has = lambda name: name in caps
    reg.get = lambda name: caps[name]
    return reg


# Use a real temporary PDB file for generation tests
_TMP_PDB_PATH = "/tmp/test_structure.pdb"


def _ensure_tmp_pdb() -> None:
    import os
    if not os.path.exists(_TMP_PDB_PATH):
        with open(_TMP_PDB_PATH, "w") as fh:
            fh.write("ATOM    1  N   A   A   1      10.000  10.000  10.000  1.00  0.00           N\n")


def test_generate_candidates_all_tools():
    """Generate candidates from both RhoDesign and RiboDiffusion."""
    _ensure_tmp_pdb()
    reg = _make_registry_for_generation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(
        structure_filepath=_TMP_PDB_PATH,
        design_tools="all",
        n_samples_per_tool=2,
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) >= 2
    sources = {c.source for c in candidates}
    assert any("rhodesign" in s for s in sources)
    assert any("ribodiffusion" in s for s in sources)


def test_generate_candidates_counts_logged():
    """Generation should produce countable sequences per tool."""
    _ensure_tmp_pdb()
    reg = _make_registry_for_generation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(
        structure_filepath=_TMP_PDB_PATH,
        design_tools="all",
        n_samples_per_tool=3,
    )
    candidates = wf.generate_candidates(inp)
    # RhoDesign: 3 calls, each returns 1 predicted_sequence → 3 rhodesign sequences
    # RiboDiffusion: 1 call, returns 1 primary + 2 generated_sequences (1 dup skipped) → 2 unique
    # Total 5 unique after dedup
    rhodesign_cands = [c for c in candidates if c.source.startswith("rhodesign")]
    ribodiffusion_cands = [c for c in candidates if c.source.startswith("ribodiffusion")]
    assert len(rhodesign_cands) == 3
    assert len(ribodiffusion_cands) == 2


def test_generate_candidates_passes_distinct_temperatures():
    """Each RhoDesign call should receive a distinct temperature."""
    _ensure_tmp_pdb()
    reg = _make_registry_for_generation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(
        structure_filepath=_TMP_PDB_PATH,
        design_tools="rhodesign",
        n_samples_per_tool=3,
    )
    captured_temps = []
    original_invoke = reg.get("design_rna_sequence_with_rhodesign").invoke

    def _wrapped_invoke(args, state=None):
        captured_temps.append(args.get("temperature"))
        return original_invoke(args, state=state)

    reg.get("design_rna_sequence_with_rhodesign").invoke = _wrapped_invoke
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 3
    assert len(captured_temps) == 3
    assert len(set(captured_temps)) == 3
    assert all(isinstance(t, float) for t in captured_temps)


def test_generate_candidates_rhodesign_only():
    """Generate candidates from RhoDesign only."""
    _ensure_tmp_pdb()
    reg = _make_registry_for_generation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(
        structure_filepath=_TMP_PDB_PATH,
        design_tools="rhodesign",
        n_samples_per_tool=2,
    )
    candidates = wf.generate_candidates(inp)
    assert len(candidates) == 2
    assert all(c.source.startswith("rhodesign") for c in candidates)


def test_generate_candidates_missing_structure():
    """Missing structure file should yield empty candidates."""
    reg = _make_registry_for_generation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(structure_filepath="/nonexistent/path.pdb")
    candidates = wf.generate_candidates(inp)
    assert candidates == []


def test_resolve_structure_filepath():
    """resolve_project_path should locate benchmark structure files."""
    from agent_core.file_manager import resolve_project_path
    resolved = resolve_project_path("data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/structures/1ehz_clean.pdb")
    assert resolved is not None
    assert resolved.endswith("1ehz_clean.pdb")
    assert Path(resolved).exists()


def test_resolve_secondary_structure_filepath():
    """resolve_project_path should locate secondary-structure contact maps."""
    from agent_core.file_manager import resolve_project_path
    resolved = resolve_project_path("data/benchmarks/RNA-BioBench-Platform/tasks/07_rna_tertiary_structure/structures/1ehz_contact_map.npy")
    assert resolved is not None
    assert resolved.endswith("1ehz_contact_map.npy")
    assert Path(resolved).exists()


def test_generate_candidates_capability_missing():
    """If capabilities are missing, generation should gracefully return empty."""
    _ensure_tmp_pdb()
    reg = MagicMock()
    reg.has.return_value = False
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(structure_filepath=_TMP_PDB_PATH, design_tools="all")
    candidates = wf.generate_candidates(inp)
    assert candidates == []


def test_evaluate_candidate():
    """Evaluate a single candidate with mocked tools."""
    reg = _make_registry_for_evaluation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    candidate = Candidate(
        sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
        sequence_type="rna",
        source="rhodesign_t1",
        metadata={
            "input_structure_filepath": _TMP_PDB_PATH,
            "tool_metadata": {"recovery_rate": 0.85},
        },
    )
    metrics = wf.evaluate(candidate)
    assert metrics["gc_content"] == pytest.approx(0.48)
    assert metrics["vienna_mfe"] == pytest.approx(-15.5)
    assert metrics["rhofold_mean_plddt"] == pytest.approx(85.0)
    assert metrics["alignment_rmsd"] == pytest.approx(2.1)
    assert metrics["alignment_tm_score"] == pytest.approx(0.88)
    assert metrics["recovery_rate"] == pytest.approx(0.85)
    assert candidate.metadata["rhofold_pdb_path"] == "workspace/rhofold_test.pdb"


def test_score_candidate():
    """Score raw metrics into normalized components."""
    reg = _make_registry_for_evaluation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    # Prime workflow state with input so weights are read correctly
    wf._workflow_state["_tertiary_design_input"] = RnaTertiaryStructureDesignInput(
        structure_filepath="test.pdb"
    )
    metrics = {
        "rhofold_mean_plddt": 80.0,
        "alignment_rmsd": 1.5,
    }
    scores = wf.score(metrics)
    assert scores["rhofold_component"] == pytest.approx(0.80)
    assert scores["rmsd_component"] == pytest.approx(1.0 - 1.5 / 5.0)
    expected_total = 0.5 * 0.80 + 0.5 * (1.0 - 1.5 / 5.0)
    assert scores["total_score"] == pytest.approx(expected_total, abs=1e-6)
    # Other components should not exist in scores dict
    assert "tm_score_component" not in scores
    assert "gc_component" not in scores


def test_rank_and_format():
    """Rank candidates and build a WorkflowResult."""
    reg = _make_registry_for_evaluation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    candidates = [
        Candidate(
            sequence="AUGCGCAUGCGCAUGCGCAUGCGCAUGCGC",
            sequence_type="rna",
            source="rhodesign_t1",
            scores={"total_score": 0.85},
            metadata={
                "metrics_bundle": {
                    "gc_content": 0.48,
                    "vienna_mfe": -15.5,
                    "rhofold_mean_plddt": 85.0,
                    "alignment_rmsd": 2.1,
                }
            },
        ),
        Candidate(
            sequence="AUGCAUGCAUGCAUGCAUGCAUGCAUGCAU",
            sequence_type="rna",
            source="ribodiffusion",
            scores={"total_score": 0.75},
            metadata={
                "metrics_bundle": {
                    "gc_content": 0.52,
                    "vienna_mfe": -12.0,
                    "rhofold_mean_plddt": 80.0,
                    "alignment_rmsd": 3.0,
                }
            },
        ),
    ]
    result = wf.rank_and_format(candidates)
    assert result.success is True
    assert result.best_candidate is not None
    assert result.best_candidate.source == "rhodesign_t1"
    assert len(result.all_candidates) == 2
    assert "candidates=2" in result.summary


def test_rank_and_format_empty():
    """Empty candidates should produce a failed WorkflowResult."""
    reg = _make_registry_for_evaluation()
    wf = RnaTertiaryStructureDesignWorkflow(reg)
    result = wf.rank_and_format([])
    assert result.success is False
    assert "empty_candidate_list" in result.errors


def test_full_pipeline_mocked():
    """Run the full workflow with mocked generation + evaluation."""
    _ensure_tmp_pdb()
    reg = MagicMock()

    # Combine generation + evaluation mocks
    gen_caps = _make_registry_for_generation()
    eval_caps = _make_registry_for_evaluation()

    all_caps = {}
    for name in ["design_rna_sequence_with_rhodesign", "design_rna_inverse_fold_with_ribodiffusion"]:
        all_caps[name] = gen_caps.get(name)
    for name in [
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure",
        "predict_rna_tertiary_structure_with_rhofold",
        "score_structure_alignment",
    ]:
        all_caps[name] = eval_caps.get(name)

    reg.has = lambda name: name in all_caps
    reg.get = lambda name: all_caps[name]

    wf = RnaTertiaryStructureDesignWorkflow(reg)
    inp = RnaTertiaryStructureDesignInput(structure_filepath=_TMP_PDB_PATH, design_tools="all")
    result = wf.run(inp)
    assert result.success is True
    assert result.best_candidate is not None
    assert len(result.all_candidates) >= 1
    assert result.best_candidate.scores.get("total_score", 0.0) > 0.0
