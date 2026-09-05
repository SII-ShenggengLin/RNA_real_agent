"""GenNav aptamer-side navigation core — platform extraction of the E14
machinery (W2, 2026-08-18; production-wired into ``RnaAptamerDesignWorkflow``
2026-08-19).

Pure functions, zero I/O, zero LLM: the levers validated by the aptamer-side
campaign arc (E8 → E12 → E14, primary endpoint GO 14:3, P = 0.0127) in their
production form:

- the pre-registered constraint matrix v3 (per-profile length band, GC
  window, homopolymer cap, stem cap) and its evaluation;
- ``laplace_pass_rate`` — smoothed per-length pass-rate estimate fusing the
  live pool with the S1 probe prior (E12 lever: measured priors);
- ``mechanized_proposals`` — band-gap-first expected-repair reinforcement
  proposals (the LLM may only arbitrate ties; E12 lever);
- ``guarantee_round`` — cycling guaranteed-repair allocation: one round for
  every repairable delivery band before any band receives a second
  (E14 lever: starvation eliminated);
- ``deliver_profile`` — mechanized delivery: matrix-pass filter → fixed
  utility order → D1 greedy top-5 (the delivery rule shared by both arms
  of every campaign).

The pre-registered E8–E15 drivers and their cached run data live under
``experiments/results/`` (verdicts: ``e14_verdict_s2.json`` GO, ``e15``
boundary).  ``tests/test_gennav_aptamer_core.py`` pins this module's
behavioural invariants on synthetic pools built from the E14 constants;
``tests/test_rna_aptamer_gennav.py`` pins the workflow wiring.

Candidate representation is the driver's: dicts with ``sequence``, ``id``,
``gear`` (``aptamer_length``, ``seed``, ``n_samples``), per-candidate
constraint fields (``gc``, ``longest_stem_bp``, ``max_homopolymer_run``)
and ``matrix_pass`` (profile -> bool).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class AptamerNavConfig:
    """Gear lattice, constraint matrix and delivery rules of one navigation run.

    Defaults mirror the E14 decisive campaign exactly (matrix v3, 17-length
    densified lattice, 2 request seeds, 48-raw budget, delivery 5, cycling
    guarantee rate >= 0.25); nothing here is workflow-stateful.
    """

    profiles: dict[str, dict] = field(default_factory=lambda: {
        # E12 matrix v3 (e12_matrix_sweep.py selected; FIX 附录 J):
        #   profile   length band  GC window    homo  stem
        #   compact   25–34 nt     [0.42, 0.62] < 5   ≤ 7
        #   standard  40–55 nt     [0.40, 0.65] < 5   ≤ 9
        #   extended  61–80 nt     [0.35, 0.60] < 6   ≤ 12
        "compact": {"lo": 25, "hi": 34, "gc_lo": 0.42, "gc_hi": 0.62,
                    "homo": 5, "stem": 7},
        "standard": {"lo": 40, "hi": 55, "gc_lo": 0.40, "gc_hi": 0.65,
                     "homo": 5, "stem": 9},
        "extended": {"lo": 61, "hi": 80, "gc_lo": 0.35, "gc_hi": 0.60,
                     "homo": 6, "stem": 12},
    })
    profile_order: tuple[str, ...] = ("compact", "standard", "extended")
    delivery_size: int = 5
    lattice_lengths: tuple[int, ...] = (25, 28, 31, 34, 40, 43, 46, 49, 52, 55, 61, 64, 67, 70, 73, 76, 80)
    probe_seed: int = 42            # S2 lattice probe seed (E12/E13/E14)
    request_seeds: tuple[int, ...] = (7, 99)
    raw_budget_per_target: int = 48
    request_n_max: int = 6
    guarantee_rate_min: float = 0.25
    sampled_depth: int = 8  # a gear counts as sampled only at >= this depth
    d1_min_pairwise: float = 0.15   # delivery-level within-batch diversity
    utility_gc_target: float = 0.55  # utility key: |GC − 0.55| ascending
    # ── production v2 repair (2026-09-04; defects root-caused on the Exp-29
    #    decisive panel — see the module addendum below) ──
    closing_round_n_max: int = 12  # endgame round may commit the remainder
    # ── production v3 repair (2026-09-04, same day; the measured signal
    #    behind it: a single probe sample carries +15pp of true rate
    #    information, per-target length rates spread >= 0.4 in half the
    #    (target, band) groups — but raw 1-2-sample Laplace ranks are
    #    noise-dominated, so v2 allocated ~randomly and tied the static
    #    grid's centre lottery) ──
    rate_shrinkage_m: float = 2.5  # gear rate = (k + m*band_rate)/(n + m)
    ucb_c: float = 0.15            # optimism bonus ucb_c/sqrt(n_gear + 1)
    delivery_margin: int = 0       # gap = delivery_size + margin - D1
                                    # survivors (the v1/v2 matrix-pass count
                                    # declared false completion when D1
                                    # attrition left 4 of 5; margin 0 is
                                    # exact — 5 survivors IS full delivery)


# ─────────────────────────────────────────────────────────────────────────────
# Sequence constraints (C2/C3/C4; C1 is the band membership itself)
# ─────────────────────────────────────────────────────────────────────────────


def gc_fraction(seq: str) -> float:
    """GC fraction of an RNA/DNA sequence (uppercase-insensitive)."""
    seq = seq.upper().replace("T", "U")
    if not seq:
        return 0.0
    return sum(1 for c in seq if c in "GC") / len(seq)


def max_homopolymer_run(seq: str) -> int:
    """Longest homopolymer run length (nt)."""
    seq = seq.upper().replace("T", "U")
    best = cur = 0
    prev = ""
    for ch in seq:
        cur = cur + 1 if ch == prev else 1
        prev = ch
        best = max(best, cur)
    return best


def longest_stem_bp(structure: str) -> int:
    """Longest continuous stem (bp) from a dot-bracket string.

    A stem's half is a contiguous run of '(' (the paired 5' half) or ')'
    (the 3' half); the stem length in base pairs equals that run length.
    """
    best = 0
    for half in ("(", ")"):
        run = 0
        for ch in structure:
            if ch == half:
                run += 1
                best = max(best, run)
            else:
                run = 0
    return best


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
    """Normalized edit distance = levenshtein / max(len)."""
    a, b = a.upper().replace("T", "U"), b.upper().replace("T", "U")
    denom = max(len(a), len(b))
    if denom == 0:
        return 0.0
    return _levenshtein(a, b) / denom


def evaluate_matrix(
    seq: str,
    gc: float,
    longest_stem: int,
    config: AptamerNavConfig,
) -> dict[str, bool]:
    """Per-profile constraint-matrix verdict for one candidate (matrix v3).

    C1 length band ∧ C2 band GC window ∧ C3 band homopolymer cap ∧ C4 band
    stem cap, evaluated independently per profile (E9 band independence).
    """
    n = len(seq)
    homo = max_homopolymer_run(seq)
    return {
        prof: (spec["lo"] <= n <= spec["hi"]
               and spec["gc_lo"] <= gc <= spec["gc_hi"]
               and homo < spec["homo"] and longest_stem <= spec["stem"])
        for prof, spec in config.profiles.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Navigation allocation (E10/E12/E14 levers)
# ─────────────────────────────────────────────────────────────────────────────


def band_of(length: int, config: AptamerNavConfig) -> Optional[str]:
    """The delivery band a lattice length belongs to (None in inter-band gaps)."""
    for prof in config.profile_order:
        spec = config.profiles[prof]
        if spec["lo"] <= length <= spec["hi"]:
            return prof
    return None


def deliverable_count(pool: list[dict], profile: str) -> int:
    """Candidates whose delivery matrix passes *profile* (pre-D1 count)."""
    return sum(1 for c in pool if c["matrix_pass"].get(profile))


def profile_gaps(pool: list[dict], config: AptamerNavConfig) -> dict[str, int]:
    """Per-profile remaining shortfall against the delivery size."""
    return {
        p: max(0, config.delivery_size - deliverable_count(pool, p))
        for p in config.profile_order
    }


def laplace_pass_rate(
    pool: list[dict],
    length: int,
    prior: Optional[list[dict]] = None,
) -> float:
    """Laplace-smoothed any-band pass rate at *length*: (k+1)/(n+2).

    Fuses the live S2 pool with the S1 probe prior (same protocol as E12) at
    no extra budget.  "Pass" means the candidate passes at least one profile
    of its matrix.
    """
    def _count(cands: Iterable[dict]) -> tuple[int, int]:
        cands = list(cands)
        n = len(cands)
        k = sum(1 for c in cands if any(c["matrix_pass"].values()))
        return n, k

    n, k = _count(c for c in pool if c["gear"]["aptamer_length"] == length)
    if prior:
        n2, k2 = _count(c for c in prior if c["gear"]["aptamer_length"] == length)
        n += n2
        k += k2
    return (k + 1) / (n + 2)


def _gear_sampled(gears: list[dict], length: int, seed: int, config: AptamerNavConfig) -> bool:
    """A gear is sampled once its *cumulative* depth reaches ``sampled_depth``.

    E14 addendum v2 semantics: shallow probe occupancy must not block a
    high-rate guarantee gear — only real depth counts.
    """
    depth = sum(
        g["n_samples"] for g in gears
        if g["aptamer_length"] == length and g["seed"] == seed
    )
    return depth >= config.sampled_depth


def mechanized_proposals(
    pool: list[dict],
    gears: list[dict],
    raw_spent: int,
    config: AptamerNavConfig,
    prior: Optional[list[dict]] = None,
) -> tuple[list[dict], dict[str, int]]:
    """Top-3 reinforcement proposals, ranked band-gap-first.

    Ordering rule (E10 S0 lesson): serve the largest remaining gap first;
    within a band take the highest expected repair — comparing raw expected
    values across bands drains budget into high-expectation bands and starves
    high-gap / low-rate bands.  Returns (proposals, gaps).
    """
    gaps = profile_gaps(pool, config)
    proposals: list[dict] = []
    n = min(config.request_n_max, config.raw_budget_per_target - raw_spent)
    if n <= 0:
        return [], gaps
    for length in config.lattice_lengths:
        band = band_of(length, config)
        if band is None:
            continue  # inter-band lattice gaps are not valid reinforcement gears
        for seed in config.request_seeds:
            if _gear_sampled(gears, length, seed, config):
                continue
            rate = laplace_pass_rate(pool, length, prior=prior)
            expected_new = rate * n
            score = 0.0
            for prof in config.profile_order:
                spec = config.profiles[prof]
                if spec["lo"] <= length <= spec["hi"]:
                    score += min(gaps[prof], expected_new)
            proposals.append({
                "length": length,
                "seed": seed,
                "n_samples": n,
                "expected_passers": round(expected_new, 2),
                "repair_score": round(score, 2),
                "band": band,
            })
    proposals.sort(
        key=lambda g: (-gaps[g["band"]], -g["repair_score"], -g["expected_passers"], g["length"], g["seed"])
    )
    return proposals[:3], gaps


def guarantee_round(
    pool: list[dict],
    gears: list[dict],
    raw_spent: int,
    config: AptamerNavConfig,
    prior: Optional[list[dict]] = None,
    guaranteed_bands: Optional[set[str]] = None,
) -> tuple[Optional[dict], set[str]]:
    """Cycling guaranteed-repair allocation (E14 decisive lever).

    Every gapped band with an unsampled gear whose Laplace rate clears
    ``guarantee_rate_min`` receives one round — in profile order — before any
    band receives a second.  ``guaranteed_bands`` is the caller-maintained
    cross-round state; an exhausted first pass clears it and rescans.
    Returns (gear | None, updated guaranteed_bands).
    """
    n = min(config.request_n_max, config.raw_budget_per_target - raw_spent)
    if n <= 0:
        return None, (guaranteed_bands or set())
    guaranteed_bands = guaranteed_bands or set()
    gaps = profile_gaps(pool, config)
    for prof in config.profile_order:
        if prof in guaranteed_bands or gaps[prof] == 0:
            continue
        spec = config.profiles[prof]
        best: Optional[dict] = None
        best_rate = 0.0
        for length in config.lattice_lengths:
            if not (spec["lo"] <= length <= spec["hi"]):
                continue
            for seed in config.request_seeds:
                if _gear_sampled(gears, length, seed, config):
                    continue
                rate = laplace_pass_rate(pool, length, prior=prior)
                if rate < config.guarantee_rate_min:
                    continue
                if rate > best_rate:
                    best_rate = rate
                    best = {
                        "length": length,
                        "seed": seed,
                        "n_samples": n,
                        "band": prof,
                        "laplace_rate": round(rate, 3),
                    }
        if best is not None:
            return best, guaranteed_bands | {prof}
    if guaranteed_bands:
        return guarantee_round(pool, gears, raw_spent, config, prior=prior, guaranteed_bands=set())
    return None, guaranteed_bands


# ─────────────────────────────────────────────────────────────────────────────
# Production v2 repair (2026-09-04) — two root-caused defects of the shipped
# navigation loop, measured on the Exp-29 decisive panel:
#
#   defect 1 (exploration tax): the shipped mode probes ALL 17 lattice
#   lengths before any reinforcement — 35% of the 48 budget spent learning
#   what a sensible default order already knows (band-interior lengths pass
#   more often).  Fix: a staged central probe (the lattice lengths nearest
#   each band centre first) plus a unified explore/exploit round in which
#   unexplored gears compete for budget using band-mean imputed rates.
#
#   defect 2 (endgame starvation): with all bands gapped, guarantee rounds
#   cycle near-uniformly and leave bands at 4-of-5 delivered with the
#   budget fully spent (8 of 9 measured losses were exactly one candidate
#   short, diversity healthy).  Fix: a closing round — once less than a
#   full standard round remains (or cycling and the mechanized pass find
#   nothing), the remainder is committed in one round of up to
#   ``closing_round_n_max`` samples to the gear with the highest expected
#   marginal repair, with no rate floor (unspent budget has no value).
#
# The E8–E14-era functions above (mechanized_proposals, guarantee_round)
# are left byte-identical: they remain the registered semantics of the
# era-reconstruction arms and of the pinned unit tests.
# ─────────────────────────────────────────────────────────────────────────────


def central_probe_lengths(config: AptamerNavConfig) -> tuple[int, ...]:
    """The staged probe order (defect-1 fix): the two lattice lengths
    nearest each band's centre, band order, innermost first."""
    out: list[int] = []
    for prof in config.profile_order:
        spec = config.profiles[prof]
        centre = (spec["lo"] + spec["hi"]) / 2.0
        in_band = [L for L in config.lattice_lengths
                   if spec["lo"] <= L <= spec["hi"]]
        in_band.sort(key=lambda L: (abs(L - centre), L))
        out.extend(in_band[:2])
    return tuple(out)


def band_mean_rate(pool: list[dict], profile: str,
                   config: AptamerNavConfig) -> float:
    """Laplace-smoothed any-band pass rate pooled over *profile*'s band:
    (k + 1) / (n + 2).  Used to impute a rate for unexplored gears so that
    exploration competes with exploitation on the same scale."""
    spec = config.profiles[profile]
    n = k = 0
    for cand in pool:
        if spec["lo"] <= cand["gear"]["aptamer_length"] <= spec["hi"]:
            n += 1
            k += 1 if any(cand["matrix_pass"].values()) else 0
    return (k + 1) / (n + 2)


def delivery_gaps(pool: list[dict], config: AptamerNavConfig) -> dict[str, int]:
    """Delivery-aware gaps (v3): ``delivery_size + margin`` minus the D1
    greedy survivors of the actual delivery rule.  The v1/v2 matrix-pass
    gap declared false completion whenever D1 attrition left 4 of 5 —
    measured as a direct cause of one-short cells on the decisive panel."""
    gaps: dict[str, int] = {}
    for profile in config.profile_order:
        survivors = len(deliver_profile(pool, profile, config)["ids"])
        gaps[profile] = max(
            0, config.delivery_size + config.delivery_margin - survivors)
    return gaps


def shrunken_gear_rate(observed: list[dict], band_rate: float,
                       config: AptamerNavConfig) -> float:
    """Shrinkage gear rate (v3): (k + m*band_rate) / (n + m) — a 1-sample
    estimate no longer outranks a 7-sample estimate on noise."""
    n = len(observed)
    k = sum(1 for c in observed if any(c["matrix_pass"].values()))
    m = config.rate_shrinkage_m
    return (k + m * band_rate) / (n + m)


def adaptive_round(
    pool: list[dict],
    gears: list[dict],
    raw_spent: int,
    config: AptamerNavConfig,
    prior: Optional[list[dict]] = None,
    guaranteed_bands: Optional[set[str]] = None,
) -> tuple[Optional[dict], str, set[str]]:
    """One production-v3 navigation round.  Deterministic, zero LLM.

    v2 defects fixed here (2026-09-04, both measured on the decisive
    panel): the matrix-pass gap ignored D1 attrition (false completion —
    now ``delivery_gaps`` with a safety margin), and reinforcement ranked
    gears by raw 1-2-sample Laplace rates, which is noise-dominated
    (allocation degenerated to the static grid's expectation).  v3 scores
    every candidate gear by a shrunken rate plus a UCB optimism bonus
    (ucb_c/sqrt(n+1)) — unsampled gears get explored exactly while their
    uncertainty could change the decision, then the budget concentrates on
    the measured-best gears; endgame remains the floor-free closing round.

    Returns (gear | None, kind, guaranteed_bands) with kind one of
    'guarantee' | 'mechanized' | 'closing' | '' (no proposal).
    """
    remaining = config.raw_budget_per_target - raw_spent
    if remaining <= 0:
        return None, "", (guaranteed_bands or set())
    gaps = delivery_gaps(pool, config)
    if all(g == 0 for g in gaps.values()):
        return None, "", (guaranteed_bands or set())

    # candidate gears scored by shrunken rate + UCB optimism bonus
    def _candidates(n_round: int) -> list[dict]:
        out: list[dict] = []
        for profile in config.profile_order:
            spec = config.profiles[profile]
            band_rate = band_mean_rate(pool, profile, config)
            for length in config.lattice_lengths:
                if not (spec["lo"] <= length <= spec["hi"]):
                    continue
                for seed in config.request_seeds:
                    depth = sum(
                        g["n_samples"] for g in gears
                        if g["aptamer_length"] == length and g["seed"] == seed
                    )
                    if depth >= config.sampled_depth:
                        continue
                    observed = [
                        c for c in pool
                        if c["gear"]["aptamer_length"] == length
                        and c["gear"]["seed"] == seed
                    ]
                    n_obs = len(observed)
                    if n_obs:
                        rate = shrunken_gear_rate(observed, band_rate, config)
                    else:
                        rate = band_rate
                    index = rate + config.ucb_c / ((n_obs + 1) ** 0.5)
                    expected_new = index * n_round
                    score = min(gaps[profile], expected_new)
                    if score > 0:
                        out.append({
                            "length": length, "seed": seed,
                            "n_samples": n_round, "band": profile,
                            "rate": round(rate, 3),
                            "ucb_index": round(index, 3),
                            "repair_score": round(score, 2),
                            "expected_passers": round(expected_new, 2),
                        })
        out.sort(key=lambda g: (-g["repair_score"], -g["ucb_index"],
                                g["length"], g["seed"]))
        return out

    # endgame first: the remaining budget is below one closing round —
    # commit the whole remainder in a single gap-weighted, floor-free
    # closing round (split rounds starve the largest gap)
    if remaining <= config.closing_round_n_max:
        proposals = _candidates(min(config.closing_round_n_max, remaining))
        if proposals:
            best = proposals[0]
            best["n_samples"] = remaining
            return best, "closing", guaranteed_bands
        return None, "", guaranteed_bands

    # standard rounds: anti-starvation band cycling (each gapped band
    # receives its first allocation before any band a second — the E14
    # semantics) with the gear WITHIN the band chosen by the v3 UCB index.
    # The shipped guarantee_round chose that gear by raw 1-2-sample Laplace
    # — noise-dominated, which degenerated allocation to the static grid's
    # expectation (measured on the decisive panel: guarantee rounds made
    # every decision and the repaired estimators never fired).
    proposals = _candidates(min(config.request_n_max, remaining))
    if not proposals:
        return None, "", guaranteed_bands
    # band choice: least-served-first among gapped bands (stateless — the
    # per-band sample count derives from the gears table; deterministic and
    # resume-safe).  Pure score ranking lets repair-score ties (every band
    # capped at the same gap) collapse onto one lucky gear and starve the
    # rest — the seg4 regression: bands at 4-of-5 with 26 samples in a
    # sibling band and 8 in theirs).
    def _served(profile: str) -> int:
        spec = config.profiles[profile]
        return sum(g["n_samples"] for g in gears
                   if spec["lo"] <= g["aptamer_length"] <= spec["hi"])
    gapped = [p for p in config.profile_order if gaps[p] > 0]
    if gapped:
        band = min(gapped, key=lambda prof: (_served(prof),
                                             config.profile_order.index(prof)))
        in_band = [p for p in proposals if p["band"] == band]
        if in_band:
            guaranteed_bands = (guaranteed_bands or set()) | {band}
            return in_band[0], "guarantee", guaranteed_bands
    return proposals[0], "mechanized", guaranteed_bands


# ─────────────────────────────────────────────────────────────────────────────
# Delivery (the shared A/C-arm rule of every campaign)
# ─────────────────────────────────────────────────────────────────────────────


def utility_key(cand: dict, config: AptamerNavConfig) -> tuple:
    """Fixed utility order: longest stem asc → |GC − target| asc → id asc.

    Deterministic tie-break by candidate id (E12 rule).
    """
    return (cand["longest_stem_bp"],
            abs(cand["gc"] - config.utility_gc_target), cand["id"])


def deliver_profile(
    pool: list[dict],
    profile: str,
    config: AptamerNavConfig,
) -> dict:
    """Mechanized delivery for one profile: matrix-pass filter → utility
    order → D1 greedy top-N.  Fewer than N delivered is an explicit degrade.

    Returns the delivery record (ids, candidate summaries, diversity
    distance, ``degraded`` flag with reason).
    """
    passing = [c for c in pool if c["matrix_pass"].get(profile)]
    ordered = sorted(passing, key=lambda c: utility_key(c, config))
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
    spec = config.profiles[profile]
    degraded = len(selected) < config.delivery_size
    reason = (
        f"post-D1 deliverable {len(selected)}/{config.delivery_size} "
        f"({len(passing)} matrix-passing in band {spec['lo']}-{spec['hi']}; "
        f"D1>={config.d1_min_pairwise} greedy keeps {len(selected)}) "
        f"after budget exhaustion"
    ) if degraded else ""
    return {
        "profile": profile,
        "ids": [c["id"] for c in selected],
        "candidates": [{
            "id": c["id"], "sequence": c["sequence"], "length": len(c["sequence"]),
            "gc": c["gc"], "longest_stem_bp": c["longest_stem_bp"],
            "abs_gc_dev": round(abs(c["gc"] - config.utility_gc_target), 4),
        } for c in selected],
        "n_passing_in_band": len(passing),
        "d1_min_dist": round(min_dist, 4) if min_dist is not None else None,
        "degraded": degraded,
        "degrade_reason": reason,
    }
