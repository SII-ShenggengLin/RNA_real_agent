#!/usr/bin/env python3
"""Pure-function unit tests for experiments/run_known_aptamer_validation.py.

No workflow runs, no microservice calls, no GPU: only string/set helpers,
structure parsing on local benchmark PDBs, and plan construction.

Run (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python -m pytest experiments/test_known_aptamer_validation.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

EXPERIMENTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXPERIMENTS_DIR.parent
sys.path.insert(0, str(EXPERIMENTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import run_known_aptamer_validation as kav  # noqa: E402

STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"

TBA_DNA = "GGTTGGTGTGGTTGG"
TBA_RNA = "GGUUGGUGUGGUUGG"
N_RNA = "AGGGGAGUGGAGGUUGGUUU"
THROMBIN_KNOWN = ["H/46", "H/67", "H/70", "H/72", "H/97"]
NUC_KNOWN = ["A/44", "A/45", "A/46", "A/47", "A/48"]


def _mini_complex_pdb(tmp_path: Path) -> Path:
    """Two-chain PDB: chain A = 2 ALA (protein), chain B = 2 U (RNA)."""
    lines = []
    serial = 1
    for chain, residues in (("A", [("ALA", 1), ("ALA", 2)]), ("B", [("U", 1), ("U", 2)])):
        for resname, resnum in residues:
            atom = "CA" if resname == "ALA" else "C1'"
            lines.append(
                f"ATOM  {serial:5d} {atom:^4s} {resname:>3s} {chain}{resnum:4d}    "
                f"{serial * 3.0:8.3f}{0.0:8.3f}{0.0:8.3f}{1.00:6.2f}{20.00:6.2f}          {'C':>2s}  "
            )
            serial += 1
    lines.append("END")
    p = tmp_path / "mini.pdb"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


# --- dna_to_rna -------------------------------------------------------------


def test_dna_to_rna_converts_thymine():
    assert kav.dna_to_rna(TBA_DNA) == TBA_RNA


def test_dna_to_rna_leaves_rna_untouched():
    assert kav.dna_to_rna(N_RNA) == N_RNA


def test_dna_to_rna_normalises_case_and_whitespace():
    assert kav.dna_to_rna(" ggttgg\ntgtggttgg ") == TBA_RNA


# --- parse_hotspot_string ---------------------------------------------------


def test_parse_hotspot_chain_num():
    assert kav.parse_hotspot_string("H/46,H/67,H/70") == ["H/46", "H/67", "H/70"]


def test_parse_hotspot_bare_numbers_use_default_chain():
    assert kav.parse_hotspot_string("46, 67", default_chain="H") == ["H/46", "H/67"]


def test_parse_hotspot_empty_and_garbage():
    assert kav.parse_hotspot_string(None) == []
    assert kav.parse_hotspot_string("") == []
    assert kav.parse_hotspot_string("H/46,,H/abc,H/067") == ["H/46", "H/67"]


# --- jaccard ----------------------------------------------------------------


def test_jaccard_values():
    assert kav.jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert kav.jaccard({"a"}, {"b"}) == 0.0
    assert kav.jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert kav.jaccard(set(), set()) == 1.0
    assert kav.jaccard({"a"}, set()) == 0.0


# --- extract_hotspot_from_results -------------------------------------------


def test_extract_hotspot_from_trace():
    results = {
        "trace": [
            {"tool_name": "compute_rna_sequence_gc_content", "success": True,
             "output_summary": "{'gc_content': 0.5}"},
            {"tool_name": "identify_protein_binding_hotspots", "success": True,
             "output_summary": "{'hotspot_residues': 'H/36,H/73,H/97', 'hotspot_patch_size': 3}"},
        ]
    }
    hotspot, source = kav.extract_hotspot_from_results(results)
    assert hotspot == "H/36,H/73,H/97"
    assert source == "trace:identify_protein_binding_hotspots"


def test_extract_hotspot_falls_back_to_candidate_metadata():
    results = {
        "trace": [],
        "candidates": [
            {"metadata": {"bmc_round": 0, "hotspot_residues": "A/1,A/2"}},
        ],
    }
    hotspot, source = kav.extract_hotspot_from_results(results)
    assert hotspot == "A/1,A/2"
    assert source == "candidate_metadata"


def test_extract_hotspot_prefers_hotspot_before_expansion():
    results = {
        "trace": [],
        "candidates": [
            {"metadata": {"bmc_round": 0,
                          "hotspot_before": "H/97",
                          "hotspot_residues": "H/94,H/95,H/96,H/97,H/98"}},
        ],
    }
    hotspot, _ = kav.extract_hotspot_from_results(results)
    assert hotspot == "H/97"


def test_extract_hotspot_returns_none_when_absent():
    assert kav.extract_hotspot_from_results({}) == (None, None)


def test_extract_hotspot_from_truncated_trace_summary():
    # workflow_results trace summaries are truncated at 500 chars; the
    # hotspot value near the head must still be recovered verbatim.
    value = "A/20,A/41,A/59,A/76,A/81,A/93,A/105,A/127"
    summary = ("{'hotspot_residues': '" + value + "', 'hotspot_patch_size': 8, "
               "'patch_center_coords': [40.53813171386719, 18.9193")
    assert len(summary) < 500
    summary = summary + "x" * (500 - len(summary))  # simulate truncation boundary
    results = {"trace": [{"tool_name": "identify_protein_binding_hotspots",
                          "success": True, "output_summary": summary}]}
    hotspot, source = kav.extract_hotspot_from_results(results)
    assert hotspot == value
    assert source == "trace:identify_protein_binding_hotspots"


def test_extract_hotspot_truncated_value_drops_last_entry():
    summary = "{'hotspot_residues': 'H/36,H/73,H/9"  # cut mid-value, no closing quote
    results = {"trace": [{"tool_name": "identify_protein_binding_hotspots",
                          "success": True, "output_summary": summary}]}
    hotspot, source = kav.extract_hotspot_from_results(results)
    assert hotspot == "H/36,H/73"  # cut tail entry 'H/9' dropped
    assert source.endswith("|truncated")


# --- structural overlap on the real benchmark PDBs --------------------------


def test_structural_overlap_self_is_perfect_on_1hao():
    pdb = STRUCT_DIR / "1hao.pdb"
    out = kav.structural_contact_overlap(pdb, THROMBIN_KNOWN, THROMBIN_KNOWN)
    assert out["known_recovery_frac"] == 1.0
    assert out["identified_precision_frac"] == 1.0
    assert out["known_missing_in_structure"] == []
    assert out["identified_missing_in_structure"] == []


def test_structural_overlap_flags_6m3m_numbering_gap():
    # 6M3M chain A starts at residue 49; the curated A/44-A/48 (full-length
    # N-protein numbering, RBD aa 44-174) are absent from the construct.
    pdb = STRUCT_DIR / "6m3m.pdb"
    out = kav.structural_contact_overlap(pdb, NUC_KNOWN, NUC_KNOWN)
    assert out["known_missing_in_structure"] == NUC_KNOWN
    assert out["known_recovery_frac"] is None
    assert out["identified_precision_frac"] is None


def test_structural_overlap_partial_hit():
    pdb = STRUCT_DIR / "1hao.pdb"
    out = kav.structural_contact_overlap(pdb, ["H/46"], THROMBIN_KNOWN, cutoff=10.0)
    assert "H/46" in out["known_recovered_min_distances"]
    assert out["known_recovery_count"] >= 1


# --- protein sequence extraction --------------------------------------------


def test_extract_protein_sequence_target_chain_1hao():
    seq, src = kav.extract_protein_sequence(STRUCT_DIR / "1hao.pdb", "H")
    assert len(seq) > 200 and src == "chain:H"


def test_extract_protein_sequence_first_chain_mirrors_workflow_quirk():
    # 1HAO chain D is the bound DNA aptamer: first-chain extraction (what the
    # workflow does) yields no amino acids, explaining iptm_component=0 runs.
    seq, src = kav.extract_protein_sequence(STRUCT_DIR / "1hao.pdb", None)
    assert seq == "" and src == "chain:D"
    # 6M3M chain A is protein -> workflow and this driver agree there.
    seq6, src6 = kav.extract_protein_sequence(STRUCT_DIR / "6m3m.pdb", None)
    assert len(seq6) > 100 and src6 == "chain:A"


# --- chain detection on a synthetic complex ---------------------------------


def test_detect_chains_in_pdb(tmp_path):
    pdb = _mini_complex_pdb(tmp_path)
    assert kav.detect_chains_in_pdb(pdb) == ("A", "B")


# --- plan construction (also what --dry-run prints) --------------------------


def test_plan_blocks_cover_matrix():
    plan = kav.plan_blocks(kav.ALL_TARGETS)
    keys = [(b["block"], b["target_id"]) for b in plan]
    assert keys == [
        ("workflow_run", "Thrombin"),
        ("known_aptamer_score", "Thrombin"),
        ("hotspot_recovery", "Thrombin"),
        ("workflow_run", "SARS-CoV-2_Nucleocapsid"),
        ("known_aptamer_score", "SARS-CoV-2_Nucleocapsid"),
        ("hotspot_recovery", "SARS-CoV-2_Nucleocapsid"),
        ("vegf_case", "VEGF"),
    ]
    by_key = dict(zip(keys, plan))
    assert by_key[("workflow_run", "Thrombin")]["params"]["bmc_max_rounds"] == 1
    assert by_key[("workflow_run", "Thrombin")]["params"]["odesign_seeds"] == [42, 123]
    assert by_key[("known_aptamer_score", "Thrombin")]["sequence_rna"] == TBA_RNA
    assert by_key[("hotspot_recovery", "Thrombin")]["known_hotspot_residues"] == THROMBIN_KNOWN
    vegf = by_key[("vegf_case", "VEGF")]
    assert vegf["pegaptanib_data_gap"] is True
    assert vegf["pegaptanib_sequence_rna"] == "CGGAAUCAGUGAAUGCUUAUACAUCCG"
    for b in plan:
        if b["block"] in {"workflow_run", "vegf_case"}:
            assert b["params"] is not None and Path(PROJECT_ROOT / b["structure"]).exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
