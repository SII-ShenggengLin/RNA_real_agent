from __future__ import annotations

import json

import pytest

from agent_core.file_manager import PROJECT_ROOT
from agent_core.sequence_utils import build_cai_weights, compute_cai, normalize_cds_sequence
from agent_core.tools import compute_cai_for_cds_sequence


@pytest.fixture()
def cds_sample_filepath():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_cai_demo_cds.fasta"
    # A short CDS with known composition (human-optimized EF1A tag: GSKEE)
    # GGC AGC AAA GAG GAG  -> 5 codons
    (ws / name).write_text(">demo_cds\nGGCAGCAAAGAGGAG\n", encoding="utf-8")
    return f"workspace/{name}"


@pytest.fixture()
def custom_table_filepath():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_custom_codon_table.json"
    # Uniform usage: every codon gets fraction 1.0 / num_synonymous
    # For simplicity, just define a tiny table with equal fractions per aa group.
    table = {
        "UUU": {"aa": "F", "fraction": 0.5},
        "UUC": {"aa": "F", "fraction": 0.5},
        "AUG": {"aa": "M", "fraction": 1.0},
        "GGG": {"aa": "G", "fraction": 0.25},
        "GGA": {"aa": "G", "fraction": 0.25},
        "GGC": {"aa": "G", "fraction": 0.25},
        "GGU": {"aa": "G", "fraction": 0.25},
        "AGC": {"aa": "S", "fraction": 0.5},
        "UCU": {"aa": "S", "fraction": 0.5},
        "AAA": {"aa": "K", "fraction": 0.5},
        "AAG": {"aa": "K", "fraction": 0.5},
        "GAG": {"aa": "E", "fraction": 0.5},
        "GAA": {"aa": "E", "fraction": 0.5},
    }
    (ws / name).write_text(json.dumps(table), encoding="utf-8")
    return f"workspace/{name}"


def test_compute_cai_for_cds_sequence_returns_dict(cds_sample_filepath):
    out = compute_cai_for_cds_sequence.invoke(
        {"filepath": cds_sample_filepath, "species": "Homo sapiens"}
    )
    assert isinstance(out, dict)
    assert "cai_score" in out
    assert out["species"] == "Homo sapiens"
    assert out["cds_length_nt"] == 15
    assert out["codon_count"] == 5
    assert out["valid_codons"] == 5
    assert out["invalid_codons"] == 0
    assert out["stop_codons_encountered"] == 0
    assert out["model"] == "cai-kazusa"
    # CAI should be between 0 and 1
    assert 0.0 <= out["cai_score"] <= 1.0


def test_compute_cai_with_species_alias(cds_sample_filepath):
    out = compute_cai_for_cds_sequence.invoke(
        {"filepath": cds_sample_filepath, "species": "human"}
    )
    assert out["species"] == "Homo sapiens"
    assert 0.0 <= out["cai_score"] <= 1.0


def test_compute_cai_with_custom_table(cds_sample_filepath, custom_table_filepath):
    out = compute_cai_for_cds_sequence.invoke(
        {
            "filepath": cds_sample_filepath,
            "species": "custom",
            "custom_codon_table_path": custom_table_filepath,
        }
    )
    assert out["species"] == "custom"
    assert out["codon_count"] == 5
    # With uniform fractions, all weights are 1.0, so CAI should be 1.0
    assert out["cai_score"] == pytest.approx(1.0, abs=1e-6)


def test_compute_cai_invalid_cds_length_raises():
    ws = PROJECT_ROOT / "workspace"
    name = "test_cai_bad_length.fasta"
    (ws / name).write_text(">bad\nAUGCA\n", encoding="utf-8")
    with pytest.raises(ValueError, match="multiple of 3"):
        compute_cai_for_cds_sequence.invoke(
            {"filepath": f"workspace/{name}", "species": "human"}
        )


def test_compute_cai_unknown_species_raises(cds_sample_filepath):
    with pytest.raises(ValueError, match="No built-in codon table"):
        compute_cai_for_cds_sequence.invoke(
            {"filepath": cds_sample_filepath, "species": "Unknownus speciesus"}
        )


def test_normalize_cds_sequence_valid():
    assert normalize_cds_sequence(">header\nAUGGGC\n") == "AUGGGC"
    assert normalize_cds_sequence("atgggc") == "AUGGGC"


def test_normalize_cds_sequence_bad_length():
    with pytest.raises(ValueError, match="multiple of 3"):
        normalize_cds_sequence("AUGCA")


def test_build_cai_weights_uniform():
    table = {
        "UUU": {"aa": "F", "fraction": 0.5},
        "UUC": {"aa": "F", "fraction": 0.5},
        "AUG": {"aa": "M", "fraction": 1.0},
    }
    weights = build_cai_weights(table)
    assert weights["UUU"] == pytest.approx(1.0, abs=1e-6)
    assert weights["UUC"] == pytest.approx(1.0, abs=1e-6)
    assert weights["AUG"] == pytest.approx(1.0, abs=1e-6)


def test_build_cai_weights_skewed():
    table = {
        "UUU": {"aa": "F", "fraction": 0.1},
        "UUC": {"aa": "F", "fraction": 0.9},
    }
    weights = build_cai_weights(table)
    assert weights["UUC"] == pytest.approx(1.0, abs=1e-6)
    assert weights["UUU"] == pytest.approx(0.1 / 0.9, abs=1e-6)


def test_compute_cai_excludes_stop_codons():
    weights = {
        "AUG": 1.0,
        "UUU": 0.5,
        "UUC": 1.0,
        "UAA": 0.0,
        "UAG": 0.0,
        "UGA": 0.0,
    }
    # AUG UUU UAA -> 3 codons, 1 stop
    result = compute_cai("AUGUUUUAA", weights)
    assert result["codon_count"] == 3
    assert result["stop_codons_encountered"] == 1
    assert result["valid_codons"] == 2
    # CAI = sqrt(1.0 * 0.5) = ~0.7071
    assert result["cai_score"] == pytest.approx(0.7071, abs=1e-3)
