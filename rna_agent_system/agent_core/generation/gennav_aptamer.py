"""GenNav aptamer-side navigation core — platform extraction of the E14
machinery (W2, 2026-08-18).

Pure functions, zero I/O, zero LLM: the three levers validated by the
aptamer-side campaign arc (E8 → E12 → E14, primary endpoint GO 14:3,
P = 0.0127) in their production-ready form:

- ``laplace_pass_rate`` — smoothed per-length pass-rate estimate fusing the
  live pool with the S1 probe prior (E12 lever: measured priors);
- ``mechanized_proposals`` — band-gap-first expected-repair reinforcement
  proposals (the LLM may only arbitrate ties; E12 lever);
- ``guarantee_round`` — cycling guaranteed-repair allocation: one round for
  every repairable delivery band before any band receives a second
  (E14 lever: starvation eliminated).

The pre-registered E8–E15 drivers and their cached run data live under
``experiments/results/`` (verdicts: ``e14_verdict_s2.json`` GO, ``e15``
boundary).  ``tests/test_gennav_aptamer_core.py`` pins this module's
behavioural invariants on synthetic pools built from the E14 constants.

Candidate representation is the driver's: dicts with ``gear`` (``aptamer_length``,
``seed``, ``n_samples``), ``matrix_pass`` (profile -> bool) and ``id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class AptamerNavConfig:
    """Gear lattice + delivery matrix of one navigation campaign.

    Defaults mirror the E14 decisive campaign exactly (17-length densified
    lattice, 2 seeds, 48-raw budget, 4x6 reinforcement rounds, delivery 5,
    guarantee rate >= 0.25); nothing here is workflow-stateful.
    """

    profiles: dict[str, dict] = field(default_factory=lambda: {
        "compact": {"lo": 25, "hi": 34},
        "standard": {"lo": 40, "hi": 55},
        "extended": {"lo": 61, "hi": 80},
    })
    profile_order: tuple[str, ...] = ("compact", "standard", "extended")
    delivery_size: int = 5
    lattice_lengths: tuple[int, ...] = (25, 28, 31, 34, 40, 43, 46, 49, 52, 55, 61, 64, 67, 70, 73, 76, 80)
    request_seeds: tuple[int, ...] = (7, 99)
    raw_budget_per_target: int = 48
    request_n_max: int = 6
    guarantee_rate_min: float = 0.25
    sampled_depth: int = 8  # a gear counts as sampled only at >= this depth


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
    return any(
        g["aptamer_length"] == length and g["seed"] == seed and g["n_samples"] >= config.sampled_depth
        for g in gears
    )


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
