"""Literature-grounded UTR admission rules and the benchmark UTR pool for
full-length mRNA design (DECISIONS (bb), 2026-09-07 wet-lab-preparation
redesign).

Every rule below carries an explicit, citable literature threshold. Rules
proposed during the design review that have NO established quantitative
threshold in the literature were deliberately not implemented (registered in
DECISIONS (bb)):

* overall U-content caps and GU-rich TLR7/8 motif counts — Vaidyanathan et
  al. 2018 (Mol Ther Nucleic Acids 10:61) reduced global U content 15.5% ->
  12.6% by synonymous recoding and publish no per-sequence motif threshold;
* internal AAUAAA hexamer screens — a delivered exogenous mRNA never meets
  the nuclear cleavage/polyadenylation machinery, and the clinically
  validated BNT162b2 5'UTR itself contains a cap-proximal AAUAAA hexamer.

Rules (deterministic, zero LLM):

U1  5'UTR upstream AUG — reject a 5'UTR containing AUG.
    Basis: the scanning model of eukaryotic initiation (upstream AUGs divert
    initiating ribosomes; Kozak 1986 Nature 320:335, Kozak 1989 MCB 9:5134)
    and the Sample et al. 2019 MPRA (uAUG/uORF features are the strongest
    negative predictors of mean ribosome loading; Nat Biotechnol 37:803) —
    the same assay family that certifies the ``gemorna_5utr_mrl`` oracle
    (Exp 14).

U2  3'UTR Class-II AU-rich element — reject overlapping/tandem AUUUA
    repeats (the Chen & Shyu 1995 Trends Biochem Sci 20:477 Class-II
    signature, e.g. AUUUAUUUA — the most destabilizing ARE class, exemplified
    by GM-CSF/TNF-alpha/IL-2 3'UTRs). Scattered (Class-I) AUUUA copies are
    counted and reported (``are_auuua_count``), never rejected.

U3  Cap-entry structure — reject when the 5'-terminal 60-nt window of the
    assembled construct folds at <= -30 kcal/mol.
    Basis: Kozak 1989 (MCB 9:5134): a -30 kcal/mol stem-loop placed 12 nt
    from the cap prevented 40S subunit engagement, while the same hairpin
    repositioned 52 nt from the cap had no deleterious effect. The rule is
    deliberately cap-proximal only; 60 nt is the smallest window that can
    physically realize Kozak's ~47-nt -30 kcal/mol hairpin.

U4  Scanning-path stall — reject when any 150-nt window spanning the
    construct 5' end through AUG+15 folds at <= -61 kcal/mol.
    Basis: Kozak 1989 hp7 (delta G = -61 kcal/mol, 72 nt from the cap)
    stalled the scanning 40S subunit on the 5' side of the hairpin; moderate
    mid-UTR structure is tolerated by the same study and is NOT gated.

The benchmark pool (assertion-checked asset, ``agent_core/data/
utr_benchmarks/utr_benchmarks_v1.json``): the template-verified BNT162b2
UTR pair (51-nt alpha-globin-derived 5'UTR + 94-nt AES-mtRNR1 3'UTR), the
LinearDesign-paper COVID-construct 5'UTR, and the natural human HBA1 UTR
pair. These are the references GEMORNA's Science 2025 paper used when
pairing CDS-only baselines with BNT162b2 UTRs, and the exact 3'UTR
LinearDesign's unmodified-nucleotide spike wet-lab validation used.

``tests/test_utr_pool.py`` pins the rule boundaries and the asset integrity;
the full-length workflow wiring is pinned in
``tests/test_full_length_mrna_design.py``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

_LOGGER = logging.getLogger("agent_core.generation.utr_pool")

# ── GEMORNA screening-scale draw counts (GEMORNA Science 2025 evaluated 12
# designed 5'UTRs and 10 designed 3'UTRs per target before full-length
# assembly; DECISIONS (bb) matches that scale) ──────────────────────────────
GEMORNA_5UTR_DRAWS_PER_PRESET: int = 4          # x {short, medium, long} = 12
GEMORNA_3UTR_DRAWS_PER_PRESET: dict[str, int] = {"short": 4, "medium": 3, "long": 3}   # = 10

# Shortlist caps for the assembled-combination stage (compute cap, not a
# ranking; DECISIONS (bb)). The 5'UTR shortlist is ordered by the certified
# MRL oracle; the 3'UTR shortlist is admission-survival order (benchmarks
# first, then GEMORNA generation order) — utr3 ranking is not oracle-driven.
UTR5_SHORTLIST_MAX: int = 6
UTR3_SHORTLIST_MAX: int = 6

# ── Kozak 1989 thresholds (kcal/mol) ───────────────────────────────────────
KOZAK_CAP_WINDOW_NT: int = 60
KOZAK_CAP_MFE_MAX: float = -30.0     # -30 hairpin 12 nt from cap blocked 40S entry
KOZAK_STALL_WINDOW_NT: int = 150
KOZAK_STALL_MFE_MAX: float = -61.0   # hp7 (-61) stalled the scanning 40S
KOZAK_STALL_STEP_NT: int = 25
KOZAK_AUG_DOWNSTREAM_NT: int = 15    # scanning path covers the AUG context

_ASSET_PATH = Path(__file__).resolve().parent.parent / "data" / "utr_benchmarks" / "utr_benchmarks_v1.json"


# ── Pure sequence rules ────────────────────────────────────────────────────

def utr5_has_upstream_aug(utr5_seq: str) -> bool:
    """U1: True when the 5'UTR contains an AUG triplet (case-insensitive, T->U)."""
    return "AUG" in utr5_seq.upper().replace("T", "U")


def _auuua_positions(utr3_seq: str) -> list[int]:
    seq = utr3_seq.upper().replace("T", "U")
    return [i for i in range(len(seq) - 4) if seq[i : i + 5] == "AUUUA"]


def utr3_are_auuua_count(utr3_seq: str) -> int:
    """Total scattered AUUUA pentamers (reported diagnostic, U2 context)."""
    return len(_auuua_positions(utr3_seq))


def utr3_are_class2(utr3_seq: str) -> bool:
    """U2: True when AUUUA repeats are overlapping/tandem (Class-II ARE).

    Chen & Shyu 1995 Class II = tandem/overlapping AUUUA repeats such as
    AUUUAUUUA; operationalized as a next occurrence starting fewer than 5 nt
    after the previous start (strictly overlapping pentamers).
    """
    pos = _auuua_positions(utr3_seq)
    return any(b - a < 5 for a, b in zip(pos, pos[1:]))


def admit_utr5(utr5_seq: str) -> dict[str, Any]:
    """Apply U1 to a 5'UTR. Returns an admission verdict dict."""
    has_uaug = utr5_has_upstream_aug(utr5_seq)
    return {
        "ok": not has_uaug,
        "rule": "U1_no_upstream_aug",
        "detail": {"upstream_aug": has_uaug},
    }


def admit_utr3(utr3_seq: str) -> dict[str, Any]:
    """Apply U2 to a 3'UTR. Returns an admission verdict dict."""
    class2 = utr3_are_class2(utr3_seq)
    return {
        "ok": not class2,
        "rule": "U2_no_class2_are",
        "detail": {"are_class2": class2, "are_auuua_count": utr3_are_auuua_count(utr3_seq)},
    }


# ── Assembled-construct Kozak rules (U3/U4) ────────────────────────────────

FoldMfe = Callable[[str], Optional[float]]


def check_cap_entry(full_seq: str, fold_mfe: FoldMfe) -> dict[str, Any]:
    """U3: cap-proximal 60-nt window must not fold at <= -30 kcal/mol.

    A fold failure (``fold_mfe`` returning None) is recorded as
    ``"unverified"`` — admission rejects on evidence, never on measurement
    outage.
    """
    window = full_seq[:KOZAK_CAP_WINDOW_NT]
    if len(window) < KOZAK_CAP_WINDOW_NT:
        detail = {"window_nt": len(window), "mfe": None}
        return {"ok": True, "rule": "U3_cap_entry", "status": "unverified", "detail": detail}
    mfe = fold_mfe(window)
    if mfe is None:
        return {"ok": True, "rule": "U3_cap_entry", "status": "unverified",
                "detail": {"window_nt": len(window), "mfe": None}}
    ok = mfe > KOZAK_CAP_MFE_MAX
    return {"ok": ok, "rule": "U3_cap_entry", "status": "verified",
            "detail": {"window_nt": len(window), "mfe": round(float(mfe), 3),
                       "threshold": KOZAK_CAP_MFE_MAX}}


def check_scanning_path(full_seq: str, cds_start: int, fold_mfe: FoldMfe) -> dict[str, Any]:
    """U4: no 150-nt window from the 5' end through AUG+15 may fold at <= -61.

    Windows that fail to fold are skipped (``unverified_windows`` count);
    rejection requires at least one verified violation.
    """
    span_end = min(len(full_seq), cds_start + 3 + KOZAK_AUG_DOWNSTREAM_NT)
    worst_mfe: Optional[float] = None
    unverified = 0
    windows = 0
    start = 0
    while start < span_end - 1:
        window = full_seq[start : start + KOZAK_STALL_WINDOW_NT]
        mfe = fold_mfe(window)
        if mfe is None:
            unverified += 1
        else:
            windows += 1
            if worst_mfe is None or mfe < worst_mfe:
                worst_mfe = float(mfe)
        if start + KOZAK_STALL_WINDOW_NT >= span_end:
            break
        start += KOZAK_STALL_STEP_NT
    if worst_mfe is None:
        return {"ok": True, "rule": "U4_scanning_path", "status": "unverified",
                "detail": {"windows_verified": 0, "windows_unverified": unverified}}
    ok = worst_mfe > KOZAK_STALL_MFE_MAX
    return {"ok": ok, "rule": "U4_scanning_path", "status": "verified",
            "detail": {"windows_verified": windows, "windows_unverified": unverified,
                       "worst_mfe": round(worst_mfe, 3), "threshold": KOZAK_STALL_MFE_MAX}}


# ── Benchmark asset (assertion-first, docs/ANCHORS.md pattern) ─────────────

_BENCHMARK_CACHE: Optional[list[dict[str, Any]]] = None


def load_utr_benchmarks(path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Load and verify the benchmark UTR asset.

    Verification at load time (assertion-first curation): md5 and length of
    every entry, ACGU purity, id uniqueness, exactly one 3'UTR benchmark
    appearing in both the BNT162b2 pair and as the LinearDesign-paper 3'UTR
    (asset invariant), and — critically — every benchmark 5'UTR passes U1 and
    every benchmark 3'UTR passes U2, so the pool can never be emptied by the
    admission layer. Raises on any violation; never returns a partial pool.
    """
    global _BENCHMARK_CACHE
    if path is None and _BENCHMARK_CACHE is not None:
        return [dict(e) for e in _BENCHMARK_CACHE]
    asset_path = path or _ASSET_PATH
    with open(asset_path) as fh:
        asset = json.load(fh)
    entries = asset["entries"]
    assert entries, "utr benchmark asset is empty"
    seen_ids: set[str] = set()
    for e in entries:
        seq = e["sequence"].upper()
        assert e["id"] not in seen_ids, f"duplicate benchmark id {e['id']}"
        seen_ids.add(e["id"])
        assert set(seq) <= set("ACGU"), f"{e['id']} is not pure ACGU"
        assert len(seq) == e["length_nt"], f"{e['id']} length mismatch"
        assert hashlib.md5(seq.encode()).hexdigest() == e["md5"], f"{e['id']} md5 mismatch"
        assert e["side"] in ("5utr", "3utr"), f"{e['id']} unknown side"
        if e["side"] == "5utr":
            assert admit_utr5(seq)["ok"], f"benchmark {e['id']} fails U1"
        else:
            assert admit_utr3(seq)["ok"], f"benchmark {e['id']} fails U2"
    ids = {e["id"] for e in entries}
    assert "bnt162b2_3utr" in ids and "hba1_5utr" in ids and "hba1_3utr" in ids, (
        "utr benchmark asset is missing required entries"
    )
    if path is None:
        _BENCHMARK_CACHE = entries
    return [dict(e) for e in entries]
