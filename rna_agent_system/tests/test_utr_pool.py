"""Tests for the UTR admission rules and the benchmark UTR asset
(agent_core/generation/utr_pool.py, DECISIONS (bb)).

Rule boundaries pin the literature thresholds verbatim:

- U1 no-upstream-AUG (Kozak 1986/1989 scanning model; Sample et al. 2019)
- U2 no-Class-II ARE (Chen & Shyu 1995: overlapping/tandem AUUUA repeats)
- U3 cap-entry (Kozak 1989: -30 kcal/mol hairpin 12 nt from the cap blocked
  40S engagement; the same hairpin 52 nt from the cap did not)
- U4 scanning-path stall (Kozak 1989 hp7: -61 kcal/mol stalled the 40S)

Rules deliberately NOT implemented (no citable quantitative threshold) are
asserted absent: no U-content cap, no GU-rich motif counter, no AAUAAA
screen anywhere in the module.
"""

from __future__ import annotations

import importlib

import pytest

from agent_core.generation import utr_pool


# ── U1: upstream AUG ────────────────────────────────────────────────────────

def test_u1_rejects_upstream_aug():
    assert utr_pool.admit_utr5("GGGAAACCCAUGGGGUUU")["ok"] is False


def test_u1_accepts_aug_free_utr():
    v = utr_pool.admit_utr5("GGGAAACCCUUUGGGAAA")
    assert v["ok"] is True
    assert v["detail"]["upstream_aug"] is False


def test_u1_dna_t_is_normalized():
    # T->U normalization: ATG in a DNA-typed string still counts as AUG
    assert utr_pool.utr5_has_upstream_aug("GGGAAACCCATGGGGTTT") is True


# ── U2: Class-II ARE ────────────────────────────────────────────────────────

def test_u2_rejects_overlapping_auuua():
    # Chen & Shyu 1995 Class II: AUUUAUUUA (two overlapping pentamers)
    v = utr_pool.admit_utr3("CCCGGG" + "AUUUAUUUA" + "CCC")
    assert v["ok"] is False
    assert v["detail"]["are_class2"] is True
    assert v["detail"]["are_auuua_count"] == 2


def test_u2_allows_scattered_class1_auuua():
    # scattered (Class I) copies never reject, only report
    seq = "CCCGGG" + "AUUUA" + "GGGCCCCGGG" + "AUUUA" + "CCC"
    v = utr_pool.admit_utr3(seq)
    assert v["ok"] is True
    assert v["detail"]["are_auuua_count"] == 2


def test_u2_tandem_with_single_gap_allowed():
    # AUUUA + 1 nt gap: next start distance is 6 >= 5 -> NOT overlapping
    assert utr_pool.utr3_are_class2("CCCAUUUAGAUUUACCC") is False


def test_u2_counts_only_auuua_pentamers():
    assert utr_pool.utr3_are_auuua_count("AUUCAGAUUCAG") == 0
    assert utr_pool.utr3_are_auuua_count("AUUUAGAUUUAG") == 2


# ── U3/U4: Kozak structure gates ────────────────────────────────────────────

def test_u3_rejects_at_threshold_exactly():
    # -30.0 kcal/mol == threshold -> reject (rule is <= -30)
    verdict = utr_pool.check_cap_entry("G" * 60, lambda seq: -30.0)
    assert verdict["ok"] is False
    assert verdict["status"] == "verified"
    assert verdict["detail"]["threshold"] == utr_pool.KOZAK_CAP_MFE_MAX


def test_u3_allows_just_above_threshold():
    verdict = utr_pool.check_cap_entry("G" * 60, lambda seq: -29.99)
    assert verdict["ok"] is True


def test_u3_short_window_is_unverified_pass():
    # a <60-nt construct cannot physically realize Kozak's ~47-nt -30 hairpin
    verdict = utr_pool.check_cap_entry("GGGAAA", lambda seq: -99.0)
    assert verdict["ok"] is True
    assert verdict["status"] == "unverified"


def test_u3_fold_outage_is_unverified_pass():
    verdict = utr_pool.check_cap_entry("G" * 60, lambda seq: None)
    assert verdict["ok"] is True
    assert verdict["status"] == "unverified"


def test_u4_rejects_hp7_scale_stall():
    # -61.0 kcal/mol == threshold -> reject (rule is <= -61)
    verdict = utr_pool.check_scanning_path("G" * 200, 150, lambda seq: -61.0)
    assert verdict["ok"] is False
    assert verdict["detail"]["worst_mfe"] == -61.0


def test_u4_allows_moderate_structure():
    # Kozak 1989: -30 hairpin 52 nt from the cap had no deleterious effect —
    # moderate mid-UTR structure must NOT be gated
    verdict = utr_pool.check_scanning_path("A" * 60 + "G" * 90, 60, lambda seq: -30.0)
    assert verdict["ok"] is True


def test_u4_windows_cover_aug_context():
    calls: list[str] = []
    def fold(seq):
        calls.append(seq)
        return -10.0
    utr_pool.check_scanning_path("A" * 400, 120, fold)
    assert calls and all(len(w) <= utr_pool.KOZAK_STALL_WINDOW_NT for w in calls)
    assert max(len(w) for w in calls) == utr_pool.KOZAK_STALL_WINDOW_NT


# ── Screening-scale constants ───────────────────────────────────────────────

def test_gemorna_screening_scale_matches_paper():
    # GEMORNA Science 2025 screened 12 designed 5'UTRs and 10 designed 3'UTRs
    assert (
        utr_pool.GEMORNA_5UTR_DRAWS_PER_PRESET * 3 == 12
    )
    assert sum(utr_pool.GEMORNA_3UTR_DRAWS_PER_PRESET.values()) == 10


# ── Benchmark asset integrity (assertion-first curation) ────────────────────

def test_benchmark_asset_loads_and_passes_admission():
    entries = utr_pool.load_utr_benchmarks()
    assert len(entries) == 5
    ids = {e["id"] for e in entries}
    assert ids == {
        "bnt162b2_5utr",
        "bnt162b2_3utr",
        "lineardesign_paper_5utr",
        "hba1_5utr",
        "hba1_3utr",
    }
    for e in entries:
        if e["side"] == "5utr":
            assert "AUG" not in e["sequence"]
        else:
            assert not utr_pool.utr3_are_class2(e["sequence"])
        assert e["sources"], f"{e['id']} must cite its sources"


def test_benchmark_asset_bnt162b2_pair_kozak_and_split_utr_invariants():
    entries = {e["id"]: e for e in utr_pool.load_utr_benchmarks()}
    # alpha-globin-derived BNT 5'UTR ends in the GCCACC Kozak (Xia & Lim 2021)
    assert entries["bnt162b2_5utr"]["sequence"].endswith("GCCACC")
    # the natural HBA1 5'UTR keeps the weak (non-GCCACC) Kozak context
    assert entries["hba1_5utr"]["sequence"].endswith("CCCACC")
    # the AES-mtRNR1 3'UTR is the LinearDesign-supplement verbatim form and
    # carries the AES-derived GC-rich head
    assert entries["bnt162b2_3utr"]["sequence"].startswith("GCUGCCUUCUGCGGGGCUUGCCUUCUGG")
    # lengths as published
    assert entries["bnt162b2_5utr"]["length_nt"] == 51
    assert entries["bnt162b2_3utr"]["length_nt"] == 94
    assert entries["lineardesign_paper_5utr"]["length_nt"] == 43
    assert entries["hba1_5utr"]["length_nt"] == 37   # Xia & Lim 2021: 37-nt
    assert entries["hba1_3utr"]["length_nt"] == 111


def test_benchmark_asset_tamper_detection(tmp_path, monkeypatch):
    import hashlib
    import json

    entries = utr_pool.load_utr_benchmarks()

    # case 1: sequence substituted with the md5 left untouched -> md5 mismatch
    bad = [dict(e) for e in entries]
    bad[0]["sequence"] = bad[0]["sequence"].replace("A", "G", 1)
    p1 = tmp_path / "bad_md5.json"
    p1.write_text(json.dumps({"entries": bad}))
    with pytest.raises(AssertionError):
        utr_pool.load_utr_benchmarks(path=p1)

    # case 2: sequence truncated with the md5 recomputed -> length mismatch
    bad = [dict(e) for e in entries]
    bad[0]["sequence"] = bad[0]["sequence"][:-1]
    bad[0]["md5"] = hashlib.md5(bad[0]["sequence"].encode()).hexdigest()
    p2 = tmp_path / "bad_len.json"
    p2.write_text(json.dumps({"entries": bad}))
    with pytest.raises(AssertionError):
        utr_pool.load_utr_benchmarks(path=p2)

    monkeypatch.setattr(utr_pool, "_BENCHMARK_CACHE", None)


def test_module_registers_deliberately_unimplemented_rules():
    """Rules without a citable quantitative threshold are documented as NOT
    implemented (DECISIONS (bb)) — the module must not grow hidden screens."""
    src = importlib.reload(utr_pool).__doc__ or ""
    for concept in ("U-content", "GU-rich", "AAUAAA"):
        assert concept in src
    # no hidden implementation of the unregistered screens
    public = [n for n in dir(utr_pool) if not n.startswith("_")]
    for forbidden in ("u_content_cap", "gu_rich_motifs", "internal_polya_signal"):
        assert forbidden not in public
