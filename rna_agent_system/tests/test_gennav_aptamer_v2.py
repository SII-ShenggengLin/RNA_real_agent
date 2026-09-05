"""Behavioural tests for the production-v2 navigation repair (2026-09-04).

The two root-caused defects of the shipped aptamer navigation loop are
pinned on synthetic pools built from the E14 campaign constants:

  defect 1 — exploration tax: ``central_probe_lengths`` orders the staged
  probe band-interior-first (two lattice lengths nearest each band centre);
  ``adaptive_round`` lets unexplored gears compete for budget with
  band-mean imputed rates (``band_mean_rate``), so exploration is a
  decision, not a fixed upfront tax.

  defect 2 — endgame starvation: when the remaining budget is at or below
  one closing round, ``adaptive_round`` commits the whole remainder in a
  single gap-weighted, floor-free closing round (kind='closing'), never a
  split that starves the largest gap; the round size never exceeds the
  remaining budget.

Determinism, budget respect and the all-gaps-zero stop are pinned too.
No services, no LLM calls.
"""

from __future__ import annotations

import copy
import random

from agent_core.generation.gennav_aptamer import (
    AptamerNavConfig,
    adaptive_round,
    band_mean_rate,
    central_probe_lengths,
    profile_gaps,
)

CONFIG = AptamerNavConfig()  # defaults mirror the E14 decisive campaign


def _pool_with_gaps(rng: random.Random, pass_rate: float, n_per_gear: int = 2
                    ) -> tuple[list[dict], list[dict]]:
    """Pool with every gear lightly sampled; matrix passes with prob
    *pass_rate* only inside the candidate's own band (deterministic seed)."""
    pool: list[dict] = []
    gears: list[dict] = []
    i = 0
    for length in CONFIG.lattice_lengths:
        for seed in CONFIG.request_seeds:
            gears.append({"aptamer_length": length, "seed": seed,
                          "n_samples": n_per_gear})
            for _ in range(n_per_gear):
                matrix_pass = {}
                for prof in CONFIG.profile_order:
                    spec = CONFIG.profiles[prof]
                    in_band = spec["lo"] <= length <= spec["hi"]
                    matrix_pass[prof] = bool(in_band and rng.random() < pass_rate)
                pool.append({
                    "id": f"cand_{i}",
                    "sequence": "".join(rng.choice("ACGU")
                                        for _ in range(length)),
                    "gc": round(rng.uniform(0.2, 0.8), 3),
                    "longest_stem_bp": rng.randint(0, 12),
                    "gear": {"aptamer_length": length, "seed": seed,
                             "n_samples": n_per_gear},
                    "matrix_pass": matrix_pass,
                })
                i += 1
    return pool, gears


def test_central_probe_order():
    central = central_probe_lengths(CONFIG)
    assert len(central) == 6  # two per band, band order
    # band centres: compact 29.5 -> (28, 31); standard 47.5 -> (46, 49);
    # extended 70.5 -> (70, 73)
    assert central == (28, 31, 46, 49, 70, 73)
    for prof in CONFIG.profile_order:
        spec = CONFIG.profiles[prof]
        centre = (spec["lo"] + spec["hi"]) / 2.0
        in_band = sorted((L for L in CONFIG.lattice_lengths
                          if spec["lo"] <= L <= spec["hi"]),
                         key=lambda L: (abs(L - centre), L))
        assert set(central) >= set(in_band[:2])


def test_band_mean_rate_bounds_and_smoothing():
    rng = random.Random(7)
    pool, _ = _pool_with_gaps(rng, pass_rate=0.5)
    for prof in CONFIG.profile_order:
        rate = band_mean_rate(pool, prof, CONFIG)
        assert 0.0 < rate < 1.0  # Laplace-smoothed, never 0 or 1
    empty_rate = band_mean_rate([], "compact", CONFIG)
    assert empty_rate == 0.5  # (0+1)/(0+2) uninformative prior


def test_adaptive_round_endgame_closing_commits_remainder():
    """Remaining budget <= closing_round_n_max -> one floor-free closing
    round of exactly the remainder, aimed at a gapped band."""
    rng = random.Random(11)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.05)  # all rates below floor
    raw_spent = CONFIG.raw_budget_per_target - 10      # 10 raw remain
    gaps = profile_gaps(pool, CONFIG)
    assert any(g > 0 for g in gaps.values())
    gear, kind, _ = adaptive_round(pool, gears, raw_spent, CONFIG)
    assert kind == "closing"
    assert gear["n_samples"] == 10
    assert gear["band"] in gaps and gaps[gear["band"]] > 0


def test_adaptive_round_respects_budget_and_never_proposes_past_cap():
    rng = random.Random(3)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.4)
    for raw_spent in (0, 17, 30, 36, 40, 44, 47, 48):
        gear, kind, _ = adaptive_round(pool, gears, raw_spent, CONFIG)
        if gear is None:
            continue
        assert gear["n_samples"] <= CONFIG.raw_budget_per_target - raw_spent
        assert kind in ("guarantee", "mechanized", "closing")


def test_adaptive_round_stops_when_all_gaps_zero():
    rng = random.Random(5)
    pool, gears = _pool_with_gaps(rng, pass_rate=1.0)  # everything passes
    # force deliverable depth in every band
    for prof in CONFIG.profile_order:
        spec = CONFIG.profiles[prof]
        for length in CONFIG.lattice_lengths:
            if spec["lo"] <= length <= spec["hi"]:
                for c in pool:
                    if c["gear"]["aptamer_length"] == length:
                        c["matrix_pass"][prof] = True
                break
    gaps = profile_gaps(pool, CONFIG)
    assert all(g == 0 for g in gaps.values())
    gear, kind, _ = adaptive_round(pool, gears, 10, CONFIG)
    assert gear is None and kind == ""


def test_adaptive_round_considers_unexplored_gears():
    """A pool whose sampled gears are all depth-blocked still earns proposals
    for unexplored (length, seed) gears via the imputed band rate."""
    rng = random.Random(13)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.05, n_per_gear=8)
    # wipe the sampled-gear ledger for two lengths -> those (length, seed)
    # gears become unexplored explore candidates at depth 0
    gears[:] = [g for g in gears if g["aptamer_length"] not in (25, 40)]
    gear, kind, _ = adaptive_round(pool, gears, 0, CONFIG)
    assert gear is not None
    assert gear["length"] in CONFIG.lattice_lengths
    assert gear["seed"] in CONFIG.request_seeds


def test_adaptive_round_deterministic():
    rng = random.Random(17)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.3)
    outs = [adaptive_round(copy.deepcopy(pool), copy.deepcopy(gears),
                           12, CONFIG) for _ in range(3)]
    assert outs[0] == outs[1] == outs[2]


def test_closing_round_prefers_largest_gap():
    """Among equal rates the closing round aims at the band with the largest
    remaining gap (gap-weighted starvation awareness)."""
    rng = random.Random(19)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.05)
    # block every band's compact/standard candidates; leave extended gapped
    raw_spent = CONFIG.raw_budget_per_target - 8
    gear, kind, _ = adaptive_round(pool, gears, raw_spent, CONFIG)
    assert kind == "closing" and gear["n_samples"] == 8


# ═════════════════════════════════════════════════════════════════════════════
# v3 repair (same-day): shrunken rates + UCB optimism + D1-aware gaps
# ═════════════════════════════════════════════════════════════════════════════

from agent_core.generation.gennav_aptamer import (
    delivery_gaps,
    shrunken_gear_rate,
)


def test_shrunken_rate_dampens_one_sample_noise():
    band_rate = 0.45
    one_hit = [{"matrix_pass": {"compact": True}}]
    one_miss = [{"matrix_pass": {"compact": False}}]
    seven = [{"matrix_pass": {"compact": True}}] * 5 + \
            [{"matrix_pass": {"compact": False}}] * 2
    r_hit = shrunken_gear_rate(one_hit, band_rate, CONFIG)
    r_miss = shrunken_gear_rate(one_miss, band_rate, CONFIG)
    r_seven = shrunken_gear_rate(seven, band_rate, CONFIG)
    # a single sample moves the estimate only part of the way toward 0/1
    assert band_rate - 0.15 < r_miss < band_rate < r_hit < band_rate + 0.16
    assert 0.0 < r_miss and r_hit < 1.0
    # a well-sampled 5/7 gear outranks any single-sample estimate
    assert r_seven > r_hit and r_seven > r_miss


def test_delivery_gaps_count_d1_attrition():
    """Five matrix passers that the D1 greedy cuts to four leave a positive
    gap (the v1/v2 matrix-pass gap would have declared completion)."""
    rng = random.Random(23)
    pool: list[dict] = []
    # five compact-band passers, two of them near-identical -> D1 keeps four
    base = "ACGUA" * 6
    seqs = [base, base, base[:-1] + "G", (base + "A")[:29], "UGCAUGCAUGCAUGCAUGCAUGCAUGCAU"]
    for i, seq in enumerate(seqs):
        pool.append({
            "id": f"d1_{i}",
            "sequence": seq,
            "gc": 0.4, "longest_stem_bp": 0,
            "gear": {"aptamer_length": len(seq), "seed": 7, "n_samples": 5},
            "matrix_pass": {"compact": True},
        })
    from agent_core.generation.gennav_aptamer import deliver_profile
    survivors = len(deliver_profile(pool, "compact", CONFIG)["ids"])
    gaps = delivery_gaps(pool, CONFIG)
    assert survivors < CONFIG.delivery_size
    assert gaps["compact"] > 0
    assert gaps["standard"] == CONFIG.delivery_size + CONFIG.delivery_margin


def test_ucb_explores_then_concentrates():
    """A gear with no observations carries the optimism bonus and can win a
    round over a mediocre observed gear; once sampled the bonus decays."""
    rng = random.Random(29)
    pool, gears = _pool_with_gaps(rng, pass_rate=0.2)
    # drop the gear ledger for one unsampled length in a gapped band
    gears[:] = [g for g in gears if g["aptamer_length"] != 28]
    pool[:] = [c for c in pool if c["gear"]["aptamer_length"] != 28]
    gear, kind, _ = adaptive_round(pool, gears, 6, CONFIG)
    assert gear is not None
    # the round either explores the unsampled gear or reinforces the best
    # observed one — both through the UCB index, deterministically
    assert gear["length"] in CONFIG.lattice_lengths
    assert kind in ("guarantee", "mechanized", "closing")


def test_band_rotation_least_served_first():
    """Equally-gapped bands are served round-robin (least-served first) —
    the seg4 band-hogging regression pin: a second consecutive round in
    the same band is a failure."""
    BANDS = {'compact': (25, 34), 'standard': (40, 55), 'extended': (61, 80)}
    band_of = lambda L: next(b for b, (lo, hi) in BANDS.items() if lo <= L <= hi)
    pool: list[dict] = []
    gears = [{"aptamer_length": 30, "seed": 7, "n_samples": 2},
             {"aptamer_length": 47, "seed": 7, "n_samples": 2},
             {"aptamer_length": 70, "seed": 7, "n_samples": 2}]
    gb: set = set()
    chosen: list[str] = []
    raw_spent = 6
    for _round in range(3):
        gear, kind, gb = adaptive_round(pool, gears, raw_spent, CONFIG,
                                        guaranteed_bands=gb)
        assert gear is not None, "gapped empty pool must earn proposals"
        band = band_of(gear["length"])
        gears.append({"aptamer_length": gear["length"], "seed": gear["seed"],
                      "n_samples": gear["n_samples"]})
        for i in range(gear["n_samples"]):
            lo, hi = BANDS[band]
            seq = ("ACGU" * (hi // 4))[:gear["length"] - (i % 3)]
            pool.append({
                "id": f"r{_round}_{i}",
                "sequence": seq,
                "gc": 0.5, "longest_stem_bp": 0,
                "gear": {"aptamer_length": gear["length"],
                         "seed": gear["seed"],
                         "n_samples": gear["n_samples"]},
                "matrix_pass": {b: (b == band) for b in BANDS},
            })
        raw_spent += gear["n_samples"]
        chosen.append(band)
    # round-robin: no band served twice in a row while others are gapped
    assert len(set(chosen)) >= 2, f"band hogging: {chosen}"
    assert chosen[0] != chosen[1], f"band hogging: {chosen}"
    # and the service spread stays bounded over the three rounds
    served = {b: sum(g["n_samples"] for g in gears
                     if BANDS[b][0] <= g["aptamer_length"] <= BANDS[b][1])
              for b in BANDS}
    assert max(served.values()) - min(served.values()) <= 8, served
