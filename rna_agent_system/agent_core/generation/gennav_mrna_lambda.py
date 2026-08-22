"""GenNav mRNA-side λ navigation core — production adaptation of the E6
machinery (2026-08-22; wired into ``MrnaCdsDesignWorkflow`` v1.2.0).

Pure functions, zero I/O, zero LLM. The navigation levers are the ones
validated by the aptamer-side campaign arc (E8 → E12 → E14: densified
lattice probe, Laplace pass-rate priors, band-gap-first mechanized
reinforcement, cycling guaranteed-repair allocation, matrix delivery),
transferred to the LinearDesign λ gear axis whose feasibility curve was
validated mRNA-side by E6 (S2 primary endpoint GO, paired McNemar
p = 1.86e-09, 30:0 discordant; evidence ``experiments/results/e6_*``).

Domain mapping (documented production defaults, NOT E6 campaign numbers —
the E6 U-score machinery was deleted per DECISIONS.md (n)):

- gear axis: LinearDesign λ. The probe lattice is E6's λ-curve
  {0, 1, 2, 4, 8, 10, 20, 50}; LinearDesign is deterministic per λ, so
  reinforcement spends budget on *interstitial* λ values (densification)
  rather than re-sampling a gear.
- delivery profiles (E6 semantics, CDS-level bands on platform metrics):
  ``expression`` (CAI-led), ``stability`` (structure-led), ``balanced``.
  The CAI floor 0.85 is anchored to E6's A1AT λ-curve pass boundary
  (λ=1 CAI 0.8377 failed, λ=2 CAI 0.8717 passed).
- λ-region affinity (allocation hint only; matrix membership is
  per-candidate): λ ≤ 2 repairs stability gaps (MFE-most-negative region),
  2 < λ < 8 repairs balanced gaps, λ ≥ 8 repairs expression gaps (CAI
  ceiling region).

Candidate representation is the driver's: dicts with ``sequence``, ``id``,
``gear`` (``{"lambda": float}``), measured fields (``cai``, ``mfe_per_nt``,
``gc``, ``max_homopolymer_run``) and ``matrix_pass`` (profile -> bool).
``tests/test_gennav_mrna_core.py`` pins this module's behavioural
invariants; ``tests/test_mrna_cds_design_workflow.py`` pins the wiring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class MrnaNavConfig:
    """λ gear lattice, constraint matrix and delivery rules of one run."""

    profiles: dict[str, dict] = field(default_factory=lambda: {
        # profile   CAI floor  MFE/nt ≤   GC window     homo
        # expression: CAI-led (E6 A1AT pass boundary ≈ 0.85)
        "expression": {"cai_lo": 0.85, "mfe_per_nt_max": None,
                       "gc_lo": 0.40, "gc_hi": 0.65, "homo": 10},
        # stability: structure-led (more negative MFE per nt)
        "stability": {"cai_lo": None, "mfe_per_nt_max": -0.25,
                      "gc_lo": 0.40, "gc_hi": 0.65, "homo": 10},
        # balanced: both, relaxed
        "balanced": {"cai_lo": 0.80, "mfe_per_nt_max": -0.20,
                     "gc_lo": 0.40, "gc_hi": 0.68, "homo": 10},
    })
    profile_order: tuple[str, ...] = ("expression", "stability", "balanced")
    delivery_size: int = 5
    # E6 λ-curve probe (feasibility); interstitial densification follows.
    probe_lambdas: tuple[float, ...] = (0.0, 1.0, 2.0, 4.0, 8.0, 10.0, 20.0, 50.0)
    refinement_lambdas: tuple[float, ...] = (0.5, 1.5, 3.0, 6.0, 12.0, 15.0, 30.0, 40.0)
    raw_budget: int = 16           # LinearDesign calls: 8 probe + ≤8 refinement
    guarantee_rate_min: float = 0.25
    # Delivery-level within-batch diversity, domain-calibrated: CDS designs at
    # adjacent λ are near-clones (edit distance 1–5% on the fresh-data IFN-γ
    # run), unlike 25–80-nt aptamers; 0.05 on a ~500-nt CDS ≈ 25 nt of codon
    # differences — proportionally the same floor as the aptamer-side 0.15.
    d1_min_pairwise: float = 0.05
    utility_gc_target: float = 0.50  # utility tie-break key: |GC − 0.50| asc

    def region_of(self, lam: float) -> Optional[str]:
        """Allocation-affinity region of a λ value (hint, not membership)."""
        if lam <= 2.0:
            return "stability"
        if lam >= 8.0:
            return "expression"
        return "balanced"


# ─────────────────────────────────────────────────────────────────────────────
# Sequence constraints (shared C3/C4; C1 CAI / C2 MFE / GC window per profile)
# ─────────────────────────────────────────────────────────────────────────────


def max_homopolymer_run(seq: str) -> int:
    """Longest homopolymer run length (nt)."""
    seq = seq.upper().replace("U", "T")
    best = cur = 0
    prev = ""
    for ch in seq:
        cur = cur + 1 if ch == prev else 1
        prev = ch
        best = max(best, cur)
    return best


def gc_fraction(seq: str) -> float:
    """GC fraction of an RNA/DNA sequence."""
    seq = seq.upper().replace("T", "U")
    if not seq:
        return 0.0
    return sum(1 for c in seq if c in "GC") / len(seq)


def evaluate_matrix(
    cai: Optional[float],
    mfe_per_nt: Optional[float],
    gc: float,
    homo: int,
    config: MrnaNavConfig,
) -> dict[str, bool]:
    """Per-profile constraint-matrix verdict for one λ candidate.

    A dimension measured as ``None`` (oracle blocked / service failure)
    evaluates as *failed* in every band that requires it — evaluation
    failure never buys matrix membership.
    """
    verdict: dict[str, bool] = {}
    for prof, spec in config.profiles.items():
        ok = spec["gc_lo"] <= gc <= spec["gc_hi"] and homo < spec["homo"]
        if ok and spec["cai_lo"] is not None:
            ok = cai is not None and cai >= spec["cai_lo"]
        if ok and spec["mfe_per_nt_max"] is not None:
            ok = mfe_per_nt is not None and mfe_per_nt <= spec["mfe_per_nt_max"]
        verdict[prof] = ok
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# Navigation allocation (E12/E14 levers on the λ axis)
# ─────────────────────────────────────────────────────────────────────────────


def deliverable_count(pool: list[dict], profile: str) -> int:
    return sum(1 for c in pool if c["matrix_pass"].get(profile))


def profile_gaps(pool: list[dict], config: MrnaNavConfig) -> dict[str, int]:
    return {
        p: max(0, config.delivery_size - deliverable_count(pool, p))
        for p in config.profile_order
    }


def laplace_pass_rate(pool: list[dict], lam: float) -> float:
    """Laplace-smoothed any-profile pass rate at *lam*: (k+1)/(n+2).

    With LinearDesign deterministic (n ≤ 1 per λ) the estimate is
    necessarily coarse; the smoothing keeps unsampled gears at the
    uninformed 0.5 prior and sampled failures at 1/3, which is enough to
    order reinforcement proposals band-gap-first.
    """
    cands = [c for c in pool if c["gear"]["lambda"] == lam]
    n = len(cands)
    k = sum(1 for c in cands if any(c["matrix_pass"].values()))
    return (k + 1) / (n + 2)


def _sampled_lambdas(gears: list[dict]) -> set[float]:
    return {g["lambda"] for g in gears}


def mechanized_proposals(
    pool: list[dict],
    gears: list[dict],
    raw_spent: int,
    config: MrnaNavConfig,
) -> tuple[list[dict], dict[str, int]]:
    """Top-3 interstitial-λ reinforcement proposals, band-gap-first.

    Ordering rule (E10 S0 lesson): serve the largest remaining gap first;
    within a region take the highest expected repair. LinearDesign is
    deterministic per λ, so proposals only name unsampled lattice values.
    """
    gaps = profile_gaps(pool, config)
    proposals: list[dict] = []
    if raw_spent >= config.raw_budget:
        return [], gaps
    sampled = _sampled_lambdas(gears)
    for lam in config.refinement_lambdas:
        if lam in sampled:
            continue
        region = config.region_of(lam)
        if region is None:
            continue
        rate = laplace_pass_rate(pool, lam)
        score = min(gaps[region], rate) if gaps[region] > 0 else 0.0
        proposals.append({
            "lambda": lam,
            "region": region,
            "laplace_rate": round(rate, 3),
            "repair_score": round(score, 3),
        })
    proposals.sort(
        key=lambda g: (
            -gaps[g["region"]], -g["repair_score"], g["laplace_rate"] is None,
            g["laplace_rate"], g["lambda"],
        )
    )
    return proposals[:3], gaps


def guarantee_round(
    pool: list[dict],
    gears: list[dict],
    raw_spent: int,
    config: MrnaNavConfig,
    guaranteed_bands: Optional[set[str]] = None,
) -> tuple[Optional[dict], set[str]]:
    """Cycling guaranteed-repair allocation (E14 decisive lever).

    Every gapped profile with an unsampled λ in its region whose Laplace
    rate clears ``guarantee_rate_min`` receives one round — in profile
    order — before any profile receives a second.
    """
    if raw_spent >= config.raw_budget:
        return None, (guaranteed_bands or set())
    guaranteed_bands = guaranteed_bands or set()
    gaps = profile_gaps(pool, config)
    sampled = _sampled_lambdas(gears)
    for prof in config.profile_order:
        if prof in guaranteed_bands or gaps[prof] == 0:
            continue
        best: Optional[dict] = None
        for lam in config.refinement_lambdas:
            if lam in sampled or config.region_of(lam) != prof:
                continue
            rate = laplace_pass_rate(pool, lam)
            if rate < config.guarantee_rate_min:
                continue
            if best is None or rate > best["laplace_rate"] or (
                rate == best["laplace_rate"] and lam < best["lambda"]
            ):
                best = {"lambda": lam, "region": prof, "laplace_rate": round(rate, 3)}
        if best is not None:
            return best, guaranteed_bands | {prof}
    if guaranteed_bands:
        return guarantee_round(pool, gears, raw_spent, config, guaranteed_bands=set())
    return None, guaranteed_bands


# ─────────────────────────────────────────────────────────────────────────────
# Delivery (mechanized; per-profile fixed utility order → D1 greedy top-N)
# ─────────────────────────────────────────────────────────────────────────────


def combined_per_nt(cand: dict) -> float:
    """Classic LinearDesign combined score per nt: (−MFE + n·log CAI)/len.

    ``-inf`` when CAI is unmeasured (missing never wins the balanced band).
    """
    cai = cand.get("cai")
    if cai is None or cai <= 0.0:
        return float("-inf")
    mfe = cand.get("mfe_per_nt")
    if mfe is None:
        return float("-inf")
    return -mfe + math.log(cai)


def utility_key(cand: dict, profile: str, config: MrnaNavConfig) -> tuple:
    """Fixed per-profile utility order (deterministic; id tie-break)."""
    gc_dev = abs(cand["gc"] - config.utility_gc_target)
    if profile == "expression":
        return (-(cand["cai"] if cand.get("cai") is not None else float("-inf")),
                gc_dev, cand["id"])
    if profile == "stability":
        return (cand["mfe_per_nt"] if cand.get("mfe_per_nt") is not None else 0.0,
                gc_dev, cand["id"])
    return (-combined_per_nt(cand), gc_dev, cand["id"])


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (0 if ca == b[j - 1] else 1))
        prev = cur
    return prev[lb]


def normalized_levenshtein(a: str, b: str) -> float:
    a, b = a.upper().replace("T", "U"), b.upper().replace("T", "U")
    denom = max(len(a), len(b))
    if denom == 0:
        return 0.0
    return _levenshtein(a, b) / denom


def deliver_profile(pool: list[dict], profile: str, config: MrnaNavConfig) -> dict:
    """Mechanized delivery for one profile: matrix-pass filter → utility
    order → D1 greedy top-N. Fewer than N delivered is an explicit degrade.
    """
    passing = [c for c in pool if c["matrix_pass"].get(profile)]
    ordered = sorted(passing, key=lambda c: utility_key(c, profile, config))
    selected: list[dict] = []
    for cand in ordered:
        if all(normalized_levenshtein(cand["sequence"], s["sequence"])
               >= config.d1_min_pairwise for s in selected):
            selected.append(cand)
        if len(selected) == config.delivery_size:
            break
    dists = [
        normalized_levenshtein(selected[i]["sequence"], selected[j]["sequence"])
        for i in range(len(selected)) for j in range(i + 1, len(selected))
    ]
    min_dist = min(dists) if dists else None
    degraded = len(selected) < config.delivery_size
    reason = (
        f"post-D1 deliverable {len(selected)}/{config.delivery_size} "
        f"({len(passing)} matrix-passing in region; "
        f"D1>={config.d1_min_pairwise} greedy keeps {len(selected)}) "
        f"after budget exhaustion"
    ) if degraded else ""
    return {
        "profile": profile,
        "ids": [c["id"] for c in selected],
        "candidates": [{
            "id": c["id"], "sequence": c["sequence"], "lambda": c["gear"]["lambda"],
            "cai": c.get("cai"), "mfe_per_nt": c.get("mfe_per_nt"), "gc": c["gc"],
            "max_homopolymer_run": c["max_homopolymer_run"],
        } for c in selected],
        "n_passing_in_region": len(passing),
        "d1_min_dist": round(min_dist, 4) if min_dist is not None else None,
        "degraded": degraded,
        "degrade_reason": reason,
    }
