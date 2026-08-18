"""Behavioural tests for the GenNav aptamer navigation core (E14 extraction).

The three validated levers (Laplace+S1-prior rates, band-gap-first proposals,
cycling guarantee rounds) are pinned on synthetic pools built from the E14
campaign constants.  No services, no LLM calls.
"""

from __future__ import annotations

import random

from agent_core.generation.gennav_aptamer import (
    AptamerNavConfig,
    band_of,
    deliverable_count,
    guarantee_round,
    laplace_pass_rate,
    mechanized_proposals,
    profile_gaps,
)

CONFIG = AptamerNavConfig()  # defaults mirror the E14 decisive campaign


def _synthetic_pool(rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Driver-format pool + sampled-gear table with a deterministic pattern."""
    pool: list[dict] = []
    gears: list[dict] = []
    i = 0
    for length in CONFIG.lattice_lengths:
        for seed in CONFIG.request_seeds:
            depth = rng.choice([0, 2, 8])
            if depth >= CONFIG.sampled_depth:
                gears.append({"aptamer_length": length, "seed": seed, "n_samples": depth})
            for _ in range(depth if depth else 1):
                matrix_pass = {}
                for prof in CONFIG.profile_order:
                    spec = CONFIG.profiles[prof]
                    in_band = spec["lo"] <= length <= spec["hi"]
                    matrix_pass[prof] = bool(in_band and rng.random() < 0.4)
                pool.append({
                    "id": f"cand_{i}",
                    "sequence": "".join(rng.choice("ACGU") for _ in range(length)),
                    "length": length,
                    "gc": round(rng.uniform(0.2, 0.8), 3),
                    "longest_stem_bp": rng.randint(0, 12),
                    "gear": {"aptamer_length": length, "seed": seed, "n_samples": 2},
                    "matrix_pass": matrix_pass,
                })
                i += 1
    return pool, gears


def test_band_membership_and_gaps():
    for L in CONFIG.lattice_lengths:
        band = band_of(L, CONFIG)
        assert band in CONFIG.profiles
        spec = CONFIG.profiles[band]
        assert spec["lo"] <= L <= spec["hi"]
    # inter-band lengths are not valid gears
    assert band_of(37, CONFIG) is None
    assert band_of(58, CONFIG) is None
    rng = random.Random(0)
    pool, _ = _synthetic_pool(rng)
    gaps = profile_gaps(pool, CONFIG)
    for prof in CONFIG.profile_order:
        expected = max(0, CONFIG.delivery_size - deliverable_count(pool, prof))
        assert gaps[prof] == expected


def test_laplace_rate_smoothing_and_prior_fusion():
    rng = random.Random(1)
    pool, _ = _synthetic_pool(rng)
    prior, _ = _synthetic_pool(random.Random(7))
    L = CONFIG.lattice_lengths[0]
    n = sum(1 for c in pool if c["gear"]["aptamer_length"] == L)
    k = sum(
        1
        for c in pool
        if c["gear"]["aptamer_length"] == L and any(c["matrix_pass"].values())
    )
    assert abs(laplace_pass_rate(pool, L) - (k + 1) / (n + 2)) < 1e-12
    # prior fusion strictly moves the estimate toward the prior's rate
    n2 = sum(1 for c in prior if c["gear"]["aptamer_length"] == L)
    k2 = sum(
        1
        for c in prior
        if c["gear"]["aptamer_length"] == L and any(c["matrix_pass"].values())
    )
    fused = (k + k2 + 1) / (n + n2 + 2)
    assert abs(laplace_pass_rate(pool, L, prior=prior) - fused) < 1e-12


def test_mechanized_proposals_band_gap_first():
    rng = random.Random(2)
    for _ in range(10):
        pool, gears = _synthetic_pool(rng)
        prior, _ = _synthetic_pool(random.Random(11))
        spent = rng.choice([0, 6, 12, 24, 42])
        proposals, gaps = mechanized_proposals(pool, gears, spent, CONFIG, prior=prior)
        assert len(proposals) <= 3
        prev_gap = None
        for prop in proposals:
            if prev_gap is not None:
                assert gaps[prop["band"]] <= prev_gap
            prev_gap = gaps[prop["band"]]
            # proposals never resample an already-sampled gear
            assert not any(
                g["aptamer_length"] == prop["length"]
                and g["seed"] == prop["seed"]
                and g["n_samples"] >= CONFIG.sampled_depth
                for g in gears
            )
            # budget-capped n
            assert prop["n_samples"] <= min(
                CONFIG.request_n_max, CONFIG.raw_budget_per_target - spent
            )


def _pool_at(length: int, seed: int, n: int, pass_all: bool) -> list[dict]:
    return [
        {
            "id": f"p{length}_{seed}_{i}",
            "length": length,
            "gear": {"aptamer_length": length, "seed": seed, "n_samples": 2},
            "matrix_pass": {
                prof: bool(pass_all and CONFIG.profiles[prof]["lo"] <= length <= CONFIG.profiles[prof]["hi"])
                for prof in CONFIG.profile_order
            },
        }
        for i in range(n)
    ]


def test_guarantee_round_first_pass_visits_each_band_once():
    """All bands eligible: the first pass guarantees each band exactly once."""
    pool: list[dict] = []
    for prof in CONFIG.profile_order:
        spec = CONFIG.profiles[prof]
        length = next(L for L in CONFIG.lattice_lengths if spec["lo"] <= L <= spec["hi"])
        pool.extend(_pool_at(length, CONFIG.request_seeds[0], 2, pass_all=True))
    assert all(g > 0 for g in profile_gaps(pool, CONFIG).values())
    gears: list[dict] = []
    state: set[str] = set()
    seen: list[str] = []
    for _ in range(3):
        gear, state = guarantee_round(pool, gears, 0, CONFIG, guaranteed_bands=state)
        assert gear is not None
        seen.append(gear["band"])
    assert seen == ["compact", "standard", "extended"]


def test_guarantee_round_exhausted_pass_rescans():
    """Only one viable band: an exhausted first pass clears the state and rescans."""
    pool: list[dict] = []
    comp = CONFIG.profiles["compact"]
    length = next(L for L in CONFIG.lattice_lengths if comp["lo"] <= L <= comp["hi"])
    pool.extend(_pool_at(length, CONFIG.request_seeds[0], 2, pass_all=True))
    # no live candidates and an all-fail prior (rate (0+1)/(8+2)=0.1 < 0.25)
    # at every standard/extended length → those bands are never eligible.
    prior: list[dict] = []
    for prof in ("standard", "extended"):
        spec = CONFIG.profiles[prof]
        for length in CONFIG.lattice_lengths:
            if spec["lo"] <= length <= spec["hi"]:
                prior.extend(_pool_at(length, CONFIG.request_seeds[0], 8, pass_all=False))
    gears: list[dict] = []
    state: set[str] = set()
    seen: list[str] = []
    for _ in range(3):
        gear, state = guarantee_round(pool, gears, 0, CONFIG, prior=prior, guaranteed_bands=state)
        assert gear is not None
        seen.append(gear["band"])
    # compact repeats only because the pass exhausted and reset in between
    assert seen == ["compact", "compact", "compact"]


def test_budget_exhaustion_returns_none():
    pool, gears = [], []
    assert guarantee_round(pool, gears, CONFIG.raw_budget_per_target, CONFIG) == (None, set())
    assert mechanized_proposals(pool, gears, CONFIG.raw_budget_per_target, CONFIG) == (
        [],
        {"compact": 5, "standard": 5, "extended": 5},
    )
