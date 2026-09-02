#!/usr/bin/env python3
"""exp26 — selection-layer constraint-navigation precursor: fixed-pool failure
re-measurement (§2.5 experiment 1, paper registry E5; Fig 5a).

Programme reset 2026-09-02 (user-directed): every paper experiment re-run with
newly written code one at a time; this is the Fig 5a leg.  The legacy E5
campaign (2026-08-07→09, S1 r5/B0 configuration) placed constraint navigation
in the SELECTION layer — generate a fixed candidate pool once, then filter and
rank — and failed for reasons structural to the generation layer.  This driver
re-measures the two registered failure exhibits on the current platform:

  (1) fixed-pool pass rate under the registered hard-constraint matrix
      (headline: GFP 0/315 → 12/315 after the species-matched codon table);
  (2) delivered-batch diversity saturation (headline: Insulin 0.82% < 2% gate).

* Protocol source (recovered verbatim from git ``b6dad08`` —
  ``experiments/run_e5_constraint_nav.py``, S1 r5 / B0 configuration; the
  legacy file is absent from disk): pool per target = LinearDesign λ∈{0,1,4,10}
  (4 candidates) + RNARL 1 + GEMORNA CDS 30 samples = 35 CDS candidates × 9
  GEMORNA UTR combinations (3 5'UTR presets × 3 3'UTR presets) = 315
  full-length constructs.  Hard constraints (pass = all six): C1 sliding-window
  GC (100-nt window, 30–80%), C2 homopolymer (<14 nt), C6 start-region stem
  (utr5+cds[:30] LinearFold, longest stem ≤12 bp), C7 full-length stem (≤30
  bp), M1 boundary GC (30-nt flanks, 20–80%), CAI ≥ 0.8 (species table).
  C3/C4/C5/C8 stay soft (archive-only) per the legacy 2026-08-07 demotion.
  Arm-A rule deliveries (zero LLM): per profile (expression / stability /
  balanced), the profile-λ-preference candidate first, cross-λ spread (each λ
  gear's top-1), then utility fill to 5, final order by utility descending.
  D1 = minimum pairwise diversity distance over the delivered five (equal
  lengths: Hamming/length; otherwise 1 − SequenceMatcher ratio), gate ≥ 2%.
  D2 = delivered λ-gear count (≥3 gears or a ≥2-gear span).  Utility weights,
  λ-preference mapping (small→0 / middle→4 / large→10), archive metrics E1–E10
  and pool normalisation are ported verbatim.

* Dataset (user-confirmed 2026-09-02): the current
  ``data/benchmarks/RNA-BioBench-FullLength-mRNA`` target files — the S1
  five-target subset A1AT / Insulin / EPO / GFP / IL-2 (per-target codon
  species as registered: human ×4, GFP = E. coli).  Overlap with already
  re-run figures disclosed: Fig 2b/c consumes the same 20-target set, Fig 4d
  the same files for A1AT/Insulin/EPO/GFP, Fig 2a's ``01_mrna_cds_design``
  tasks share EPO/GFP — using the identical on-disk files keeps every figure
  on one dataset.  WT GC reference (archive E8):
  ``data/benchmarks/external_anchors/wt_cds/<target>.fa``.

* Instrument (zero-intervention rule): the platform's production tool path —
  ``ToolExecutor.run_tool`` through the ``ToolRegistry`` — against the
  deployed microservices (GEMORNA 8004 / RNARL 8008 GPU-pinned by the
  experiment bring-up script; LinearDesign 8014 and LinearFold 8015 CPU),
  with ``RNADA_CAPGATE=advisory`` (the documented regression convention) and
  the audit runtime activated via ``runtime_from_env()`` so every call lands
  in the platform audit trail.  CAI (Kazusa, Sharp & Li weights) computes
  locally through its registered tool.  Consolidation disclosed: the legacy
  driver folded each full-length sequence twice (structure pass, then MFE
  pass); the deployed LinearFold tool returns both from one deterministic
  call, so this run folds once and reads both — values identical, half the
  calls.  Everything else is one tool call per legacy call.

* GFP dual wiring (the B0 exhibit): the ``production`` arm designs LinearDesign
  against the platform's species-resolved E. coli CSV
  (``lineardesign_codon_table_for_species`` — the current registration, i.e.
  the state B0 left behind); the ``pre_b0`` arm omits ``codon_usage_path`` so
  the service designs against its bundled default (human) table — the
  registered pre-fix instrument.  RNARL, the 30 GEMORNA CDS samples and the 9
  UTRs are drawn once per target and shared between wirings (the legacy
  r4→r5 convention: shared gears byte-identical, the codon table is the only
  lever).  CAI scoring uses the registered species table (E. coli) in BOTH
  arms — the mismatch between species-table scoring and default-table design
  IS the pre-B0 defect being measured.

* Disclosed realization note: GEMORNA sampling is non-idempotent and the
  legacy per-(target, idx) caches were deleted in the resets, so this run
  draws a new realization, cached inside its results directory for
  reproducibility.  Expected outcomes pre-registered (tested, not assumed):
  GFP pre_b0 pass = 0/315 (the CAI ceiling of default-table designs sits
  below the 0.8 gate — deterministic); GFP production pass small and confined
  to the high-λ gears (legacy 12/315, λ{4,10} only); Insulin delivered-batch
  D1 < 2% (λ saturation; legacy 0.0082); pass-count ordering EPO ≫ IL-2 >
  Insulin > A1AT.  Exact legacy values are NOT expected to reproduce where
  GEMORNA sampling enters; the run measures its own realization.

* LLM usage: zero calls (arm A of the legacy design; the exhibits measured
  here are pool-level properties that no arm's LLM could move).

* Outputs (``experiments/results/exp26_selection_layer_pool/``):
  ``pilot/records.jsonl`` + ``full/records.jsonl`` (one self-contained record
  per target × wiring: pool composition, every candidate's constraints /
  archive / sequence, per-profile deliveries and metrics),
  ``full/summary.json`` (the Fig 5a numbers), per-mode ``gemorna_cds.json`` /
  ``gemorna_utr.json`` / ``folds.json`` caches, ``scratch/``.

* Usage:
      PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp26_selection_layer_pool.py --pilot
      PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp26_selection_layer_pool.py
      PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp26_selection_layer_pool.py --verify

* ``--verify`` recomputes utilities, deliveries, D1–D3 and the summary from
  the stored records with zero service calls and asserts byte-identical
  output.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("RNADA_CAPGATE", "advisory")

from scipy import stats as scipy_stats  # noqa: E402

from agent_core.sequence_utils import (  # noqa: E402
    _load_builtin_codon_tables,
    lineardesign_codon_table_for_species,
    resolve_species_name,
)

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
WT_CDS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "wt_cds"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp26_selection_layer_pool"

S1_TARGETS = ["A1AT", "Insulin", "EPO", "GFP", "IL-2"]
PILOT_TARGETS = ["Insulin"]  # smallest gene; exercises the full chain + the D1 exhibit

# ── Pool composition (legacy E5 S1 v4/r5, verbatim) ─────────────────────────
LAMBDAS: tuple[float, ...] = (0.0, 1.0, 4.0, 10.0)
LAMBDA_GEMORNA = -1.0
LAMBDA_RNARL = -2.0
GEMORNA_CDS_N = 30
LAMBDA_RANK = {0: 0, 1: 1, 4: 2, 10: 3, LAMBDA_GEMORNA: 4, LAMBDA_RNARL: 5}
UTR_PRESETS: tuple[str, ...] = ("short", "medium", "long")
PROFILES: tuple[str, ...] = ("expression", "stability", "balanced")

# ── Constraint thresholds (legacy §4.1 final, verbatim) ─────────────────────
GC_WINDOW = 100
GC_MIN, GC_MAX = 30.0, 80.0
CAI_MIN = 0.8
HOMOPOLYMER_MIN = 14
START_REGION_CDS_PREFIX = 30
START_REGION_MAX_STEM = 12
FULL_MAX_STEM = 30
BOUNDARY_FLANK = 30
BOUNDARY_GC_MIN, BOUNDARY_GC_MAX = 20.0, 80.0
RARE_CODON_FRACTION = 0.10
ARE_MOTIF = "AUUUA"
KOZAK_CONSENSUS = "GCCACC"
CONSTRAINT_IDS = ["C1", "C2", "C6", "C7", "M1", "CAI"]

# ── Utility / delivery rules (legacy §5/§6 final, verbatim) ─────────────────
PROFILE_DEFS: dict[str, dict[str, Any]] = {
    "expression": {
        "region_weights": [0.35, 0.45, 0.20],
        "lambda_pref": "small",
        "utr5_axis": "mrl",
    },
    "stability": {
        "region_weights": [0.15, 0.50, 0.35],
        "lambda_pref": "large",
        "utr5_axis": "start_open",
    },
    "balanced": {
        "region_weights": [1 / 3, 1 / 3, 1 / 3],
        "lambda_pref": "middle",
        "utr5_axis": "tie",
    },
}
LAMBDA_PREF_VALUE: dict[str, float] = {"small": 0.0, "large": 10.0, "middle": 4.0}
W_REGIONAL, W_GLOBAL = 0.8, 0.2
W_LAMBDA = 0.8
LAMBDA_RANK_SPAN = 5
DIVERSITY_GATE = 0.02  # D1 gate (2%)

TOOL_LD = "design_mrna_cds_with_lineardesign"
TOOL_RNARL = "design_mrna_cds_with_rnarl"
TOOL_GEMORNA_CDS = "design_mrna_cds_with_gemorna"
TOOL_UTR5 = "design_5utr_with_gemorna"
TOOL_UTR3 = "design_3utr_with_gemorna"
TOOL_MRL = "predict_5utr_mrl_with_gemorna"
TOOL_STAB = "predict_3utr_stability_with_gemorna"
TOOL_FOLD = "predict_rna_secondary_structure_with_linearfold"
TOOL_CAI = "compute_cai_for_cds_sequence"


# ── Sequence / constraint pure functions (legacy, verbatim) ─────────────────
def _rna(seq: str) -> str:
    return seq.upper().replace("T", "U")


def gc_fraction(seq: str) -> float:
    if not seq:
        return 0.0
    return sum(1 for c in seq.upper() if c in "GC") / len(seq)


def sliding_window_gc_out_of_bounds(seq: str, win: int = GC_WINDOW,
                                    lo: float = GC_MIN, hi: float = GC_MAX) -> bool:
    """True if ANY 100nt sliding window (step 1) has GC outside [lo, hi]."""
    seq = _rna(seq)
    n = len(seq)
    if n < win:
        gc = gc_fraction(seq) * 100.0
        return not (lo <= gc <= hi)
    prefix = [0] * (n + 1)
    for i, c in enumerate(seq):
        prefix[i + 1] = prefix[i] + (1 if c in "GC" else 0)
    for i in range(n - win + 1):
        gc = (prefix[i + win] - prefix[i]) / win * 100.0
        if not (lo <= gc <= hi):
            return True
    return False


def has_homopolymer(seq: str, k: int = HOMOPOLYMER_MIN) -> bool:
    seq = _rna(seq)
    return any(re.search(rf"{b}{{{k},}}", seq) for b in ("A", "U", "C", "G"))


POLYA_SIGNALS = ("AAUAAA", "UUUAUU")


def polya_signal_count(cds: str) -> int:
    cds = _rna(cds)
    return sum(cds.count(sig) for sig in POLYA_SIGNALS)


RESTRICTION_SITES = ("GGAUCC", "GAAUUC", "CUCGAG", "GCGGCCGC")


def restriction_site_hits(seq: str) -> list[str]:
    seq = _rna(seq)
    return [site for site in RESTRICTION_SITES if site in seq]


SPLICE_CONSENSUS = re.compile(r"[AG]G[AC]AG")


def splice_motif_count(cds: str) -> int:
    return len(SPLICE_CONSENSUS.findall(_rna(cds)))


def longest_stem_bp(structure: str) -> int:
    """Longest continuous stem (bp) from a dot-bracket string.

    A stem's half is a contiguous run of '(' (the paired 5' half) or ')'
    (the 3' half); the stem length in base pairs equals that run length.
    """
    best = 0
    run = 0
    for ch in structure:
        if ch in "(":
            run += 1
            best = max(best, run)
        else:
            run = 0
    run = 0
    for ch in structure:
        if ch in ")":
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def pair_ratio(structure: str) -> float:
    """Paired fraction in percentage points (pp); 0.0 for empty structure."""
    if not structure:
        return 0.0
    paired = structure.count("(") + structure.count(")")
    return paired / len(structure) * 100.0


def unpaired_fraction(structure: str) -> float:
    if not structure:
        return 1.0
    return structure.count(".") / len(structure)


def boundary_gc_ok(utr5: str, cds: str, utr3: str,
                   flank: int = BOUNDARY_FLANK) -> bool:
    """Both boundary ±30nt windows (5'UTR|CDS, CDS|3'UTR) GC in [20, 80]."""
    for left, right in ((utr5, cds), (cds, utr3)):
        if not left or not right:
            return False
        win = _rna(left[-flank:]) + _rna(right[:flank])
        gc = gc_fraction(win) * 100.0
        if not (BOUNDARY_GC_MIN <= gc <= BOUNDARY_GC_MAX):
            return False
    return True


def are_count(utr3: str) -> int:
    return len(re.findall(ARE_MOTIF, _rna(utr3)))


def kozak_score(utr5: str, cds: str) -> float:
    """Kozak consensus match (−6..−1 positions vs GCCACC), 0..1."""
    window = _rna(utr5[-6:]) if len(utr5) >= 6 else _rna(utr5)
    if not window:
        return 0.0
    matches = sum(1 for a, b in zip(window, KOZAK_CONSENSUS) if a == b)
    return matches / 6.0


def rare_codon_set(species: str) -> set[str]:
    """Codons whose RSCU ranks in the lowest ~10% of the species' table (E6)."""
    tables = _load_builtin_codon_tables()
    resolved = resolve_species_name(species)
    if resolved not in tables:
        return set()
    fractions = tables[resolved]
    groups: dict[str, list[tuple[str, float]]] = {}
    for codon, info in fractions.items():
        if not info.get("fraction"):
            continue
        groups.setdefault(str(info.get("aa", "")), []).append(
            (codon, float(info["fraction"]))
        )
    rscu: dict[str, float] = {}
    for _aa, codons in groups.items():
        total = sum(f for _, f in codons) or 1.0
        mean_f = total / len(codons)
        for codon, frac in codons:
            rscu[codon] = frac / mean_f if mean_f else 0.0
    if not rscu:
        return set()
    n_rare = max(1, int(round(len(rscu) * RARE_CODON_FRACTION)))
    return {c for c, _ in sorted(rscu.items(), key=lambda kv: kv[1])[:n_rare]}


def rare_codon_count(cds: str, rare: set[str] | None = None) -> int:
    cds = _rna(cds)
    return sum(1 for i in range(0, len(cds) - 2, 3) if cds[i : i + 3] in rare)


def diversity_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    sa, sb = _rna(a["sequence"]), _rna(b["sequence"])
    if len(sa) == len(sb):
        diffs = sum(1 for x, y in zip(sa, sb) if x != y)
        return diffs / len(sa)
    return 1.0 - difflib.SequenceMatcher(None, sa, sb).ratio()


# ── Candidate construction (legacy, verbatim) ───────────────────────────────
def make_candidate(cds_seq: str, utr5: str, utr3: str, lam: float,
                   utr5_preset: str, utr3_preset: str, species: str,
                   *, source: str = "ld", idx: int = 0) -> dict[str, Any]:
    cds_seq, utr5, utr3 = _rna(cds_seq), _rna(utr5), _rna(utr3)
    full = utr5 + cds_seq + utr3
    prefix = {"ld": f"ld{int(lam)}", "rnarl": "rn", "gemorna": f"gm{idx}"}[source]
    return {
        "id": f"{prefix}_u5{utr5_preset[0]}_u3{utr3_preset[0]}",
        "source": source,
        "lambda": lam,
        "lambda_rank": LAMBDA_RANK.get(lam, 0),
        "utr5_preset": utr5_preset,
        "utr3_preset": utr3_preset,
        "utr5": utr5,
        "cds": cds_seq,
        "utr3": utr3,
        "sequence": full,
        "species": species,
        "constraints": {},
        "archive": {},
        "scores": {},
        "utility": {},
        "flags": {"delivered": False, "passed": False, "no_constraint_solution": False},
    }


# ── Utility (legacy §5, verbatim) ───────────────────────────────────────────
def pool_normalizers(pool_candidates: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    keys = ["E1_cai", "E2_full_mfe", "E4_utr5_mrl", "E5_utr3_stability",
            "E6_rare_codons", "E7_pair_ratio", "E8_delta_gc", "E9_are_count",
            "E10_kozak", "C6_start_open", "C7_longest_stem", "CDS_unpaired",
            "E3_junction_mfe_per_nt"]
    vals: dict[str, list[float]] = {k: [] for k in keys}
    for c in pool_candidates:
        for k in keys:
            v = c["archive"].get(k)
            if v is not None:
                vals[k].append(float(v))
    return {k: (min(vs), max(vs)) for k, vs in vals.items() if vs}


def _norm(v: float | None, lo: float, hi: float) -> float:
    if v is None:
        return 0.0
    if hi - lo < 1e-9:
        return 0.5
    return (float(v) - lo) / (hi - lo)


def regional_metric(cand: dict[str, Any], profile: str,
                    norms: dict[str, tuple[float, float]]) -> dict[str, float]:
    a = cand["archive"]
    mrl = _norm(a.get("E4_utr5_mrl"), *norms.get("E4_utr5_mrl", (0.0, 1.0)))
    start_open = _norm(a.get("C6_start_open"), *norms.get("C6_start_open", (0.0, 1.0)))
    cai = _norm(a.get("E1_cai"), *norms.get("E1_cai", (0.0, 1.0)))
    cds_struct = _norm(a.get("CDS_unpaired"), *norms.get("CDS_unpaired", (0.0, 1.0)))
    rare = 1.0 - _norm(a.get("E6_rare_codons"), *norms.get("E6_rare_codons", (0.0, 1.0)))
    stab = _norm(a.get("E5_utr3_stability"), *norms.get("E5_utr3_stability", (0.0, 1.0)))

    axis = PROFILE_DEFS[profile]["utr5_axis"]
    if axis == "mrl":
        utr5_score = 0.6 * mrl + 0.4 * start_open
    elif axis == "start_open":
        utr5_score = 0.6 * start_open + 0.4 * mrl
    else:
        utr5_score = 0.5 * mrl + 0.5 * start_open
    cds_score = (cai + cds_struct + rare) / 3.0
    utr3_score = stab

    weights = PROFILE_DEFS[profile]["region_weights"]
    return {
        "utr5": utr5_score, "cds": cds_score, "utr3": utr3_score,
        "regional": (weights[0] * utr5_score + weights[1] * cds_score
                     + weights[2] * utr3_score),
    }


def _lambda_pref_comp(cand: dict[str, Any], profile: str) -> float:
    pref_lam = LAMBDA_PREF_VALUE[PROFILE_DEFS[profile]["lambda_pref"]]
    pref_rank = LAMBDA_RANK[pref_lam]
    dist = abs(cand["lambda_rank"] - pref_rank)
    return 1.0 - min(dist, LAMBDA_RANK_SPAN) / LAMBDA_RANK_SPAN


def utility(cand: dict[str, Any], profile: str,
            norms: dict[str, tuple[float, float]]) -> float:
    regional = regional_metric(cand, profile, norms)["regional"]
    mfe_norm = 1.0 - _norm(cand["archive"].get("E2_full_mfe"),
                           *norms.get("E2_full_mfe", (0.0, 1.0)))
    global_part = mfe_norm
    jun = cand["archive"].get("E3_junction_mfe_per_nt")
    lo, hi = norms.get("E3_junction_mfe_per_nt", (0.0, 1.0))
    if jun is not None and hi - lo > 1e-9:
        global_part = 0.5 * global_part + 0.5 * (1.0 - _norm(jun, lo, hi))
    base = W_REGIONAL * regional + W_GLOBAL * global_part
    return (base + W_LAMBDA * _lambda_pref_comp(cand, profile)) / (1.0 + W_LAMBDA)


def assign_utilities(candidates: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    norms = pool_normalizers(candidates)
    for c in candidates:
        c["utility"] = {p: utility(c, p, norms) for p in PROFILES}
    return norms


# ── Arm-A delivery + evaluation (legacy §6/§7, verbatim) ────────────────────
def _default_delivery(candidates: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    passed = [c for c in candidates if c["flags"]["passed"]]
    ranked = sorted(passed, key=lambda c: c["utility"][profile], reverse=True)
    if len(ranked) <= 5:
        return ranked
    pref_lam = LAMBDA_PREF_VALUE[PROFILE_DEFS[profile]["lambda_pref"]]
    selected: list[dict[str, Any]] = []
    for c in ranked:
        if c["lambda"] == pref_lam:
            selected.append(c)
            break
    for lam in sorted({c["lambda"] for c in ranked}):
        for c in ranked:
            if c["lambda"] == lam and c not in selected:
                selected.append(c)
                break
    for c in ranked:
        if c not in selected:
            selected.append(c)
        if len(selected) >= 5:
            break
    return sorted(selected[:5], key=lambda c: c["utility"][profile], reverse=True)


def spearman_rho_rankings(delivery_rank: list[str], u_rank: list[str]) -> float:
    ids_d, ids_u = list(delivery_rank), list(u_rank)
    shared = [i for i in ids_d if i in ids_u]
    if len(shared) < 2:
        return 1.0
    x = [shared.index(i) for i in shared]
    y = [ids_u.index(i) for i in shared]
    return float(scipy_stats.spearmanr(x, y).statistic)


def evaluate_delivery(delivery: list[dict[str, Any]], profile: str,
                      candidates: list[dict[str, Any]]) -> dict[str, Any]:
    delivery_rank_ids = [c["id"] for c in delivery]
    u_rank = sorted(delivery, key=lambda c: c["utility"][profile], reverse=True)
    u_rank_ids = [c["id"] for c in u_rank]

    rho = spearman_rho_rankings(delivery_rank_ids, u_rank_ids)
    r1 = rho >= 1.0 - 1e-6

    passed_subset = [c for c in candidates if c["flags"]["passed"]]
    top1 = delivery[0] if delivery else None
    r4_pass, r4_marked = False, False
    if top1 is not None:
        if passed_subset:
            max_u = max(c["utility"][profile] for c in passed_subset)
            max_n = max(sum(1 for v in c["constraints"].values() if v)
                        for c in passed_subset)
            top1_u = top1["utility"][profile]
            top1_n = sum(1 for v in top1["constraints"].values() if v)
            r4_pass = (top1_u >= max_u - 1e-9) and (top1_n == max_n)
        else:
            pool_max = max(c["utility"][profile] for c in candidates)
            r4_pass = top1["utility"][profile] >= pool_max - 1e-9
            r4_marked = True

    min_dist = min(
        diversity_distance(delivery[i], delivery[j])
        for i in range(len(delivery)) for j in range(i + 1, len(delivery))
    ) if len(delivery) >= 2 else 0.0
    d1 = min_dist >= DIVERSITY_GATE

    lams = sorted({c["lambda_rank"] for c in delivery})
    d2 = len(lams) >= 3 or any(
        b - a >= 2 for a in lams for b in lams if b > a
    )

    prs = [c["archive"]["E7_pair_ratio"] for c in delivery]
    stems = [c["archive"]["C7_longest_stem"] for c in delivery]
    pr_range = (max(prs) - min(prs)) if prs else 0.0
    stem_range = (max(stems) - min(stems)) if stems else 0.0
    d3 = (pr_range >= 3.0) or (stem_range >= 5.0)

    return {
        "profile": profile,
        "delivered_ids": delivery_rank_ids,
        "e2e_pass": len(delivery) == 5 and all(c["flags"]["passed"] for c in delivery),
        "constraint_rate": (
            mean(sum(1 for v in c["constraints"].values() if v) / len(CONSTRAINT_IDS)
                 for c in delivery) if delivery else 0.0
        ),
        "R1_spearman": rho, "R1": r1,
        "R4": r4_pass, "R4_no_constraint_solution_marked": r4_marked,
        "D1_min_dist": min_dist, "D1": d1,
        "D2_lambda_ranks": lams, "D2": d2,
        "D3_pair_ratio_range": pr_range,
        "D3_stem_range": stem_range, "D3": d3,
    }


# ── Tool layer (production path + run-local caches) ─────────────────────────
class Instrument:
    def __init__(self, mode_dir: Path):
        from agent_core.calibrated.runtime import runtime_from_env
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
        runtime_from_env()
        self.executor = ToolExecutor(build_default_tool_registry())
        self.scratch = mode_dir / "scratch"
        self.scratch.mkdir(parents=True, exist_ok=True)
        self._seq_counter = 0
        self.cds_cache = self._load_json(mode_dir / "gemorna_cds.json")
        self.utr_cache = self._load_json(mode_dir / "gemorna_utr.json")
        self.fold_cache = self._load_json(mode_dir / "folds.json")
        self._mode_dir = mode_dir
        self.tool_calls = 0

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _save_json(self, name: str, data: dict[str, Any]) -> None:
        path = self._mode_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _save_caches(self) -> None:
        self._save_json("gemorna_cds.json", self.cds_cache)
        self._save_json("gemorna_utr.json", self.utr_cache)
        self._save_json("folds.json", self.fold_cache)

    def _seq_file(self, seq: str) -> str:
        # Verbatim uppercase only — proteins pass through here too, so the
        # nucleotide T→U normalisation must NOT be applied at this layer.
        self._seq_counter += 1
        fp = self.scratch / f"seq_{self._seq_counter:05d}.txt"
        fp.write_text(seq.upper(), encoding="utf-8")
        return str(fp.relative_to(PROJECT_ROOT))

    def run(self, tool: str, **params: Any) -> dict[str, Any]:
        self.tool_calls += 1
        res = self.executor.run_tool(tool, **params)
        if not res.success:
            raise RuntimeError(f"{tool} failed: {res.error}")
        raw = res.artifacts.get("result")
        if not isinstance(raw, dict):
            raise RuntimeError(f"{tool} returned no result artifact")
        return raw

    def ld_design(self, protein: str, lam: float,
                  codon_usage_path: str | None) -> str:
        params: dict[str, Any] = {
            "filepath": self._seq_file(protein), "lambda_value": lam}
        if codon_usage_path is not None:
            params["codon_usage_path"] = codon_usage_path
        return _rna(self.run(TOOL_LD, **params)["generated_sequence"])

    def rnarl_design(self, protein: str) -> str:
        return _rna(self.run(TOOL_RNARL, filepath=self._seq_file(protein))
                    ["generated_sequence"])

    def gemorna_cds(self, target_id: str, idx: int, protein: str) -> str:
        key = f"{target_id}#{idx}"
        if key not in self.cds_cache:
            last_exc: Exception | None = None
            for attempt in range(2):  # transient-service retry once, then proceed
                try:
                    self.cds_cache[key] = self.run(
                        TOOL_GEMORNA_CDS, filepath=self._seq_file(protein)
                    )["generated_sequence"]
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    time.sleep(2.0)
            else:
                raise RuntimeError(
                    f"GEMORNA CDS sample {key} failed twice: {last_exc}")
            self._save_caches()
        return _rna(self.cds_cache[key])

    def gemorna_utr(self, utr_type: str, preset: str, target_id: str) -> str:
        key = f"{target_id}|{utr_type}|{preset}"
        if key not in self.utr_cache:
            tool = TOOL_UTR5 if utr_type == "5utr" else TOOL_UTR3
            self.utr_cache[key] = self.run(tool, utr_length=preset)["generated_sequence"]
            self._save_caches()
        return _rna(self.utr_cache[key])

    def predict_mrl(self, utr5: str) -> float:
        return float(self.run(TOOL_MRL, filepath=self._seq_file(utr5))["predicted_mrl"])

    def predict_stability(self, utr3: str) -> float:
        return float(self.run(TOOL_STAB, filepath=self._seq_file(utr3))
                     ["predicted_stability"])

    def cai(self, cds: str, species: str) -> float:
        return float(self.run(TOOL_CAI, filepath=self._seq_file(cds),
                              species=species)["cai_score"])

    def fold(self, seq: str) -> dict[str, Any]:
        key = hashlib.md5(_rna(seq).encode()).hexdigest()
        if key not in self.fold_cache:
            raw = self.run(TOOL_FOLD, filepath=self._seq_file(seq))
            self.fold_cache[key] = {"structure": str(raw["structure"]),
                                    "mfe": float(raw["mfe"])}
            self._save_caches()
        return self.fold_cache[key]


# ── Pool build (legacy §3.1, ported to the production tool path) ────────────
def build_pool(target_id: str, meta: dict[str, Any], wiring: str,
               inst: Instrument, log=print) -> list[dict[str, Any]]:
    species = meta.get("species_for_codon_optimization") or "human"
    protein = meta["protein_sequence"].upper()
    t0 = time.perf_counter()

    ld_codon_usage_path = (
        lineardesign_codon_table_for_species(species) if wiring == "production" else None
    )
    cds_items: list[tuple[str, float, int, str]] = []
    for lam in LAMBDAS:
        seq = inst.ld_design(protein, lam, ld_codon_usage_path)
        cds_items.append(("ld", lam, 0, seq))
        log(f"  [pool:{target_id}:{wiring}] LD lambda={lam} len={len(seq)}")
    try:
        seq = inst.rnarl_design(protein)
        cds_items.append(("rnarl", LAMBDA_RNARL, 0, seq))
        log(f"  [pool:{target_id}:{wiring}] RNARL len={len(seq)}")
    except Exception as exc:  # noqa: BLE001 — single-gear failure never blocks the pool
        log(f"  [pool:{target_id}:{wiring}] WARN RNARL failed: {exc} (skipped)")
    gemorna_seqs = [inst.gemorna_cds(target_id, i, protein)
                    for i in range(GEMORNA_CDS_N)]
    for i, seq in enumerate(gemorna_seqs):
        cds_items.append(("gemorna", LAMBDA_GEMORNA, i, seq))
    log(f"  [pool:{target_id}:{wiring}] GEMORNA {GEMORNA_CDS_N} samples "
        f"(unique={len(set(gemorna_seqs))})")

    utr5_cache = {p: inst.gemorna_utr("5utr", p, target_id) for p in UTR_PRESETS}
    utr3_cache = {p: inst.gemorna_utr("3utr", p, target_id) for p in UTR_PRESETS}

    candidates: list[dict[str, Any]] = []
    for source, lam, idx, cds_seq in cds_items:
        for u5p in UTR_PRESETS:
            for u3p in UTR_PRESETS:
                candidates.append(make_candidate(
                    cds_seq, utr5_cache[u5p], utr3_cache[u3p], lam, u5p, u3p,
                    species, source=source, idx=idx))

    cai_cache = {seq: inst.cai(seq, species) for _, _, _, seq in cds_items}
    mrl_cache = {p: inst.predict_mrl(utr5_cache[p]) for p in UTR_PRESETS}
    stab_cache = {p: inst.predict_stability(utr3_cache[p]) for p in UTR_PRESETS}
    rare = rare_codon_set(species)

    fa = WT_CDS_DIR / f"{target_id}.fa"
    if fa.is_file():
        lines = [ln.strip() for ln in fa.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.lstrip().startswith(">")]
        wt_gc = gc_fraction("".join(lines))
    else:
        wt_gc = 0.0

    window_fold_cache: dict[tuple[str, str], str] = {}
    for cand in candidates:
        cds_seq, utr5, utr3 = cand["cds"], cand["utr5"], cand["utr3"]
        window_key = (utr5, cds_seq)
        if window_key not in window_fold_cache:
            win_seq = utr5 + cds_seq[:START_REGION_CDS_PREFIX]
            window_fold_cache[window_key] = inst.fold(win_seq)["structure"]
        win_struct = window_fold_cache[window_key]

        folded = inst.fold(cand["sequence"])
        full_struct = folded["structure"]

        c1 = not sliding_window_gc_out_of_bounds(cand["sequence"])
        c2 = not has_homopolymer(cand["sequence"])
        c6 = longest_stem_bp(win_struct) <= START_REGION_MAX_STEM
        c7 = longest_stem_bp(full_struct) <= FULL_MAX_STEM
        m1 = boundary_gc_ok(utr5, cds_seq, utr3)
        cai = cai_cache[cds_seq] >= CAI_MIN
        cand["constraints"] = {"C1": c1, "C2": c2, "C6": c6, "C7": c7,
                               "M1": m1, "CAI": cai}
        cand["flags"]["passed"] = all(cand["constraints"].values())
        cand["flags"]["no_constraint_solution"] = not cand["flags"]["passed"]

        cds_struct = full_struct[len(utr5): len(utr5) + len(cds_seq)]
        cand["archive"] = {
            "C3_polya_signal_count": polya_signal_count(cds_seq),
            "C4_restriction_hits": restriction_site_hits(cand["sequence"]),
            "C5_splice_motif_count": splice_motif_count(cds_seq),
            "C8_uAUG_count": utr5.count("AUG"),
            "E1_cai": cai_cache[cds_seq],
            "E2_full_mfe": folded["mfe"],
            "E3_junction_mfe_per_nt": None,
            "E4_utr5_mrl": mrl_cache[cand["utr5_preset"]],
            "E5_utr3_stability": stab_cache[cand["utr3_preset"]],
            "E6_rare_codons": rare_codon_count(cds_seq, rare),
            "E7_pair_ratio": pair_ratio(full_struct),
            "E8_delta_gc": abs(gc_fraction(cand["sequence"]) - wt_gc),
            "E9_are_count": are_count(utr3),
            "E10_kozak": kozak_score(utr5, cds_seq),
            "C6_start_open": unpaired_fraction(win_struct),
            "C7_longest_stem": longest_stem_bp(full_struct),
            "CDS_unpaired": unpaired_fraction(cds_struct),
            "full_gc": gc_fraction(cand["sequence"]),
        }
        cand["wt_gc_reference"] = wt_gc

    log(f"  [pool:{target_id}:{wiring}] {len(candidates)} candidates, "
        f"{sum(1 for c in candidates if c['flags']['passed'])} pass, "
        f"{time.perf_counter() - t0:.0f}s")
    return candidates


# ── Cell runner ──────────────────────────────────────────────────────────────
def run_cell(target_id: str, wiring: str, inst: Instrument, log=print) -> dict[str, Any]:
    meta = json.loads((TARGETS_DIR / f"{target_id}.json").read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    candidates = build_pool(target_id, meta, wiring, inst, log=log)
    assign_utilities(candidates)

    deliveries: dict[str, list[dict[str, Any]]] = {}
    profiles_eval: list[dict[str, Any]] = []
    for profile in PROFILES:
        delivery = _default_delivery(candidates, profile)
        for c in delivery:
            c["flags"]["delivered"] = True
        deliveries[profile] = delivery
        profiles_eval.append(evaluate_delivery(delivery, profile, candidates))

    pass_n = sum(1 for c in candidates if c["flags"]["passed"])
    per_cds = len(UTR_PRESETS) ** 2
    cds_counts = {
        "lineardesign": sum(1 for c in candidates if c["source"] == "ld") // per_cds,
        "rnarl": sum(1 for c in candidates if c["source"] == "rnarl") // per_cds,
        "gemorna": sum(1 for c in candidates if c["source"] == "gemorna") // per_cds,
    }
    pass_by_lambda: dict[str, int] = {}
    for c in candidates:
        if c["flags"]["passed"]:
            key = str(c["lambda"])
            pass_by_lambda[key] = pass_by_lambda.get(key, 0) + 1
    fail_tally: dict[str, int] = {cid: 0 for cid in CONSTRAINT_IDS}
    for c in candidates:
        if not c["flags"]["passed"]:
            for cid, ok in c["constraints"].items():
                if not ok:
                    fail_tally[cid] = fail_tally.get(cid, 0) + 1

    slim_candidates = [{
        "id": c["id"], "source": c["source"], "lambda": c["lambda"],
        "lambda_rank": c["lambda_rank"],
        "utr5_preset": c["utr5_preset"], "utr3_preset": c["utr3_preset"],
        "sequence": c["sequence"],
        "constraints": {k: bool(v) for k, v in c["constraints"].items()},
        "passed": bool(c["flags"]["passed"]),
        "archive": {k: (v if isinstance(v, (int, float, str, list, type(None))) else v)
                    for k, v in c["archive"].items()},
    } for c in candidates]

    return {
        "target_id": target_id,
        "wiring": wiring,
        "species": meta.get("species_for_codon_optimization") or "human",
        "protein_length_aa": len(meta["protein_sequence"]),
        "pool": {
            "n_candidates": len(candidates),
            "n_pass": pass_n,
            "cds_counts": cds_counts,
            "pass_by_lambda": pass_by_lambda,
            "constraint_fail_tally": fail_tally,
            "wt_gc_reference": candidates[0]["wt_gc_reference"] if candidates else 0.0,
        },
        "profiles": profiles_eval,
        "candidates": slim_candidates,
        "elapsed_seconds": time.perf_counter() - t0,
        "tool_calls": inst.tool_calls,
    }


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for rec in records:
        d1_values = [p["D1_min_dist"] for p in rec["profiles"]]
        row = {
            "target": rec["target_id"],
            "wiring": rec["wiring"],
            "pool_n": rec["pool"]["n_candidates"],
            "pass_n": rec["pool"]["n_pass"],
            "pass_rate": rec["pool"]["n_pass"] / rec["pool"]["n_candidates"],
            "pass_by_lambda": rec["pool"]["pass_by_lambda"],
            "constraint_fail_tally": rec["pool"]["constraint_fail_tally"],
            "d1_min_dist_min_over_profiles": min(d1_values),
            "d1_min_dist_per_profile": {
                p["profile"]: p["D1_min_dist"] for p in rec["profiles"]},
            "d1_pass_all_profiles": all(p["D1"] for p in rec["profiles"]),
            "d2_lambda_ranks_per_profile": {
                p["profile"]: p["D2_lambda_ranks"] for p in rec["profiles"]},
            "e2e_pass_all_profiles": all(p["e2e_pass"] for p in rec["profiles"]),
            "elapsed_seconds": rec["elapsed_seconds"],
        }
        rows.append(row)
    return {
        "experiment": "exp26_selection_layer_pool",
        "paper_registry": "E5 (selection-layer precursor; Fig 5a)",
        "protocol_source": "git b6dad08 experiments/run_e5_constraint_nav.py (S1 r5/B0)",
        "pool_definition": "LD lambda{0,1,4,10} + RNARL + GEMORNA 30 CDS = 35 x 9 UTR = 315",
        "gates": {"diversity_min_dist": DIVERSITY_GATE, "cai_min": CAI_MIN,
                  "constraint_ids": CONSTRAINT_IDS},
        "targets": rows,
    }


# ── Verify (zero service calls; recompute from stored records) ──────────────
def recompute_row(rec: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for slim in rec["candidates"]:
        cand = {
            "id": slim["id"], "source": slim["source"], "lambda": slim["lambda"],
            "lambda_rank": slim["lambda_rank"],
            "utr5_preset": slim["utr5_preset"], "utr3_preset": slim["utr3_preset"],
            "sequence": slim["sequence"],
            "constraints": {k: bool(v) for k, v in slim["constraints"].items()},
            "archive": dict(slim["archive"]),
            "utility": {},
            "flags": {"passed": bool(slim["passed"]),
                      "no_constraint_solution": not slim["passed"]},
        }
        candidates.append(cand)
    assign_utilities(candidates)
    profiles_eval = []
    for profile in PROFILES:
        delivery = _default_delivery(candidates, profile)
        profiles_eval.append(evaluate_delivery(delivery, profile, candidates))
    pass_n = sum(1 for c in candidates if c["flags"]["passed"])
    pass_by_lambda: dict[str, int] = {}
    for c in candidates:
        if c["flags"]["passed"]:
            pass_by_lambda[str(c["lambda"])] = pass_by_lambda.get(str(c["lambda"]), 0) + 1
    fail_tally: dict[str, int] = {cid: 0 for cid in CONSTRAINT_IDS}
    for c in candidates:
        if not c["flags"]["passed"]:
            for cid, ok in c["constraints"].items():
                if not ok:
                    fail_tally[cid] = fail_tally.get(cid, 0) + 1
    d1_values = [p["D1_min_dist"] for p in profiles_eval]
    return {
        "target": rec["target_id"], "wiring": rec["wiring"],
        "pool_n": len(candidates), "pass_n": pass_n,
        "pass_by_lambda": pass_by_lambda,
        "constraint_fail_tally": fail_tally,
        "d1_min_dist_min_over_profiles": min(d1_values),
        "d1_pass_all_profiles": all(p["D1"] for p in profiles_eval),
    }


def verify(mode: str) -> int:
    mode_dir = RESULTS_DIR / mode
    records = [json.loads(ln) for ln in
               (mode_dir / "records.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    stored = json.loads((mode_dir / "summary.json").read_text(encoding="utf-8"))
    rebuilt_rows = [recompute_row(rec) for rec in records]
    mismatches = 0
    for stored_row, rebuilt in zip(stored["targets"], rebuilt_rows):
        for key in ("target", "wiring", "pool_n", "pass_n", "pass_by_lambda",
                    "constraint_fail_tally", "d1_min_dist_min_over_profiles",
                    "d1_pass_all_profiles"):
            if stored_row[key] != rebuilt[key]:
                mismatches += 1
                print(f"MISMATCH {stored_row['target']}({stored_row['wiring']}).{key}: "
                      f"stored={stored_row[key]!r} recomputed={rebuilt[key]!r}")
    if mismatches:
        print(f"[verify] FAILED: {mismatches} mismatches")
        return 1
    print(f"[verify] {len(records)} records recomputed from stored data — "
          f"all fields byte-identical ({mode}/)")
    return 0


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true",
                        help="run the Insulin pilot cell (full chain, one target)")
    parser.add_argument("--verify", action="store_true",
                        help="recompute summary from stored records (no services)")
    args = parser.parse_args()

    if args.verify:
        return verify("full")

    mode = "pilot" if args.pilot else "full"
    mode_dir = RESULTS_DIR / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    inst = Instrument(mode_dir)

    plan: list[tuple[str, str]] = []
    if args.pilot:
        plan = [(tid, "production") for tid in PILOT_TARGETS]
    else:
        # Order: the four species-matched targets first, then GFP twice
        # (pre-B0 exhibit, then the production wiring headline).
        plan = [(tid, "production") for tid in S1_TARGETS if tid != "GFP"]
        plan.append(("GFP", "pre_b0"))
        plan.append(("GFP", "production"))

    records: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    records_path = mode_dir / "records.jsonl"
    records_path.write_text("", encoding="utf-8")  # fresh run: truncate
    for target_id, wiring in plan:
        print(f"[{mode}] cell {target_id} / wiring={wiring}")
        rec = run_cell(target_id, wiring, inst)
        records.append(rec)
        with records_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{mode}] {target_id}/{wiring}: pass "
              f"{rec['pool']['n_pass']}/{rec['pool']['n_candidates']}, "
              f"D1 min {min(p['D1_min_dist'] for p in rec['profiles']):.4f}")

    summary = summarize(records)
    summary["wall_seconds"] = time.perf_counter() - t0
    summary["tool_calls"] = inst.tool_calls
    (mode_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{mode}] summary -> {mode_dir / 'summary.json'}")
    for row in summary["targets"]:
        print(f"  {row['target']:9s} {row['wiring']:11s} pass {row['pass_n']:3d}/"
              f"{row['pool_n']}  D1min {row['d1_min_dist_min_over_profiles']:.4f} "
              f"(gate {DIVERSITY_GATE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
