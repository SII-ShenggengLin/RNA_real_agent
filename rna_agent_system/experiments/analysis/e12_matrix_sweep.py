#!/usr/bin/env python3
"""E12 pre-registration gate (analysis only) — constraint-matrix parameterization
sweep over cached pools, hunting the "moderate-rate scarcity" regime.

E10 relaxed-v1 matrix: A-fail 14/36 with 5 HER2 cells spanning 4 targets ->
C e2e ceiling 0.667 < 0.8 (see FIX appendix H/I). The E12 win recipe needs a
matrix v3 with: A-fail high (b supply), navigability high (>= ~0.75 of
A-fail cells fixable by some lattice length), HER2-class targets <= 2 (e2e
ceiling >= 0.833). Scarcity must sit in the MODERATE-rate regime (per-length
pass rates ~0.2-0.5) — near-zero-rate bands produce HER2 cells that no arm
can fix.

Method (zero services; ODesign sequences are matrix-independent, and the run
records carry the physical features gc / max_homopolymer_run / longest_stem_bp
evaluated under relax-v1 — those are matrix-independent properties, so every
swept matrix is re-evaluated over the same sequences):
  1. Load candidates from e10_runs_s2.jsonl (12 targets, full A+C pools) +
     e10_runs_s1.jsonl (3 probes, A-only pools).
  2. For each matrix variant: re-evaluate matrix_pass per band per candidate;
     compute per-target A-fail (A-grid gears only, deliver_profile D1-greedy),
     navigability (merged pool, best lattice length), HER2 cells;
  3. Protocol simulation (E10 18/3 split, gap-priority, laplace) under the
     swept matrix -> b/c/P/C-e2e over the full pool.

The selected v3 parameterization is locked in the E12 criteria book BEFORE
any new experiment runs.
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy.stats import binomtest  # noqa: E402

from experiments.run_e10_gennav_aptamer import (  # noqa: E402
    PROFILE_ORDER,
    C_LATTICE_LENGTHS,
    DELIVERY_SIZE,
    C_REQUEST_SEEDS,
    C_PROBE2_SEED,
    deliver_profile,
)

RESULTS = PROJECT_ROOT / "experiments" / "results"
RAW_BUDGET = 48
S2_RUNS = RESULTS / "e10_runs_s2.jsonl"
S1_RUNS = RESULTS / "e10_runs_s1.jsonl"
# A-grid gears (static rule arm): (length, seed, n)
A_GEARS = {(30, 42), (30, 123), (50, 42), (50, 123), (80, 42), (80, 123)}
# Probe targets with A-only pools (Cyto/Myo/Papain were A+C-probe in E10 S1,
# but their C-probe candidates were not written to run records).
PROBE_TARGETS = {"Cytochrome_c", "Myoglobin", "Papain"}

STEM_SETS = [
    (8, 10, 12),   # relax v1 (baseline)
    (7, 9, 11), (6, 9, 11), (7, 8, 11), (6, 8, 10),
    (7, 9, 12), (6, 10, 12), (8, 9, 12), (7, 10, 12),
    (8, 9, 11), (6, 8, 11), (8, 10, 11),
]
GC_SHIFTS = [0.00, -0.02, 0.02]   # -0.02 = looser windows, +0.02 = tighter
HOMO_SETS = [(5, 5, 6), (4, 5, 6), (4, 4, 6)]
BANDS = ["base", "tight_ext", "wide_std"]


def load_pools() -> dict[str, dict[str, list[dict]]]:
    """target_id -> {"A": [candidates], "C": [candidates]} (C absent for probes)."""
    out: dict[str, dict[str, list[dict]]] = {}
    for path in (S2_RUNS, S1_RUNS):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            t, arm = r["target_id"], r["arm"]
            if not r.get("success"):
                continue
            out.setdefault(t, {})[arm] = r["candidates"]
    return out


def evaluate_matrix(cands: list[dict], profiles: dict) -> None:
    """Re-evaluate matrix_pass for every profile under a swept matrix (in place)."""
    for c in cands:
        L, gc, homo, stem = (c["length"], c["gc"], c["max_homopolymer_run"],
                             c["longest_stem_bp"])
        c["matrix_pass"] = {
            p: (spec["lo"] <= L <= spec["hi"]
                and spec["gc_lo"] <= gc <= spec["gc_hi"]
                and homo < spec["homo"] and stem <= spec["stem"])
            for p, spec in profiles.items()
        }


def grid_pool(pools: dict[str, list[dict]]) -> list[dict]:
    return [c for c in pools.get("A", [])
            if (c["gear"]["aptamer_length"], c["gear"]["seed"]) in A_GEARS]


def merged_pool(pools: dict[str, list[dict]]) -> list[dict]:
    return pools.get("A", []) + pools.get("C", [])


def per_target_cells(pools: dict[str, list[dict]], profiles: dict) -> dict:
    """A-fail / navigable / her2 classification per (target, profile)."""
    a_grid = grid_pool(pools)
    merged = merged_pool(pools)
    cells = {}
    for prof in PROFILE_ORDER:
        a_del = len(deliver_profile(a_grid, prof)["ids"])
        best, best_L = 0, None
        for L in C_LATTICE_LENGTHS:
            d = len(deliver_profile(
                [c for c in merged if c["gear"]["aptamer_length"] == L],
                prof)["ids"])
            if d > best:
                best, best_L = d, L
        cells[prof] = {"a_deliverable": a_del, "navigable": best >= DELIVERY_SIZE,
                       "best_length": best_L}
    return cells


def merged_rate(pools: dict[str, list[dict]], t: str) -> dict[int, float]:
    per: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for c in merged_pool(pools):
        L = c["gear"]["aptamer_length"]
        per[L][1] += 1
        if any(c["matrix_pass"].values()):
            per[L][0] += 1
    return {L: n / max(tot, 1) for L, (n, tot) in per.items()}


def laplace_est(pool: list[dict], L: int) -> float:
    cands = [c for c in pool if c.get("length") == L]
    n = len(cands)
    k = sum(1 for c in cands if any(c["matrix_pass"].values()))
    return (k + 1) / (n + 2)


def virtual_cell(pool: list[dict], t: str, L: int, s: int, n: int,
                 rate: dict[int, float], profiles: dict) -> None:
    realized = int(round(rate.get(L, 0.0) * n))
    for i in range(realized):
        pool.append({
            "length": L, "gc": 0.5, "max_homopolymer_run": 0,
            "longest_stem_bp": 0, "sequence": f"VIRT{t}{L}s{s}i{i:02d}",
            "id": f"virt{L}s{s}i{i:02d}",
            "matrix_pass": {
                p: (spec["lo"] <= L <= spec["hi"]
                    and spec["gc_lo"] <= 0.5 <= spec["gc_hi"]
                    and 0 < spec["homo"] and 0 <= spec["stem"])
                for p, spec in profiles.items()
            },
        })


def _passing(c: dict) -> bool:
    return any(c["matrix_pass"].values())


def per_band_passers(pool: list[dict], profiles: dict) -> dict[str, int]:
    return {p: sum(1 for c in pool if c["matrix_pass"][p])
            for p in PROFILE_ORDER}


def arm_c_sim(t: str, by: dict, profiles: dict) -> dict[str, bool]:
    """E10 protocol (probe 18 / probe2 <=8 / 3 gap-priority rounds) under a
    swept matrix; realization = merged per-length rate (same model as
    e11/e12 protocol sims, which matched E10's b exactly)."""
    pool: list[dict] = []
    sampled = set()
    spent = 0
    rate = merged_rate(by[t], t)
    for L in C_LATTICE_LENGTHS:
        virtual_cell(pool, t, L, 42, 2, rate, profiles)
        spent += 2
        sampled.add((L, 42))
    for prof in PROFILE_ORDER:
        if spent + 2 > RAW_BUDGET:
            break
        spec = profiles[prof]
        for L in C_LATTICE_LENGTHS:
            if spec["lo"] <= L <= spec["hi"]:
                passers_L = sum(1 for c in pool if c.get("length") == L
                                and _passing(c))
                if passers_L < 2 and (L, C_PROBE2_SEED) not in sampled:
                    virtual_cell(pool, t, L, C_PROBE2_SEED, 2, rate, profiles)
                    spent += 2
                    sampled.add((L, C_PROBE2_SEED))
                    break
    for _rnd in range(3):
        remaining = RAW_BUDGET - spent
        n = min(8, remaining)
        if n <= 0:
            break
        passers = per_band_passers(pool, profiles)
        gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
        if all(g <= 0 for g in gaps.values()):
            break
        band = max(gaps, key=gaps.get)
        spec = profiles[band]
        cand_gears = [
            (L, s) for L in C_LATTICE_LENGTHS for s in C_REQUEST_SEEDS
            if spec["lo"] <= L <= spec["hi"] and (L, s) not in sampled
        ]
        if not cand_gears:
            break
        est = {L: laplace_est(pool, L) for L, _ in cand_gears}
        Lg, sg = max(cand_gears, key=lambda g: est[g[0]])
        virtual_cell(pool, t, Lg, sg, n, rate, profiles)
        spent += n
        sampled.add((Lg, sg))
    passers = per_band_passers(pool, profiles)
    return {p: passers[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}


def make_profiles(band: str, stems: tuple, gc_shift: float,
                  homos: tuple) -> dict:
    base = {
        "compact": {"lo": 25, "hi": 34, "gc_lo": 0.42, "gc_hi": 0.62,
                    "homo": 5, "stem": 8},
        "standard": {"lo": 40, "hi": 55, "gc_lo": 0.40, "gc_hi": 0.65,
                     "homo": 5, "stem": 10},
        "extended": {"lo": 61, "hi": 80, "gc_lo": 0.35, "gc_hi": 0.60,
                     "homo": 6, "stem": 12},
    }
    # band-boundary variants: shift extended lo / standard hi slightly
    if band == "tight_ext":
        base["extended"]["lo"] = 65
        base["compact"]["hi"] = 30
        base["standard"]["lo"] = 40
        base["standard"]["hi"] = 60
    elif band == "wide_std":
        base["standard"]["lo"] = 40
        base["standard"]["hi"] = 60
    elif band == "tight_all":
        base["compact"]["hi"] = 30
        base["extended"]["lo"] = 65
    for i, p in enumerate(PROFILE_ORDER):
        base[p]["stem"] = stems[i]
        base[p]["gc_lo"] = max(0.0, base[p]["gc_lo"] + gc_shift)
        base[p]["gc_hi"] = min(1.0, base[p]["gc_hi"] - gc_shift)
        base[p]["homo"] = homos[i]
    return base


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-only", action="store_true",
                        help="restrict to the 12 full A+C pools (drop the 3 "
                             "thin A-only probe pools that inflate her2)")
    args = parser.parse_args()
    pools = load_pools()
    targets = sorted(t for t in pools
                     if not args.full_only or "C" in pools[t])
    print(f"pools: {len(targets)} targets "
          f"({sum('C' in pools[t] for t in targets)} full A+C, "
          f"{sum('C' not in pools[t] for t in targets)} A-only probes)")

    rows = []
    for band, stems, gc_shift, homos in itertools.product(
            BANDS, STEM_SETS, GC_SHIFTS, HOMO_SETS):
        profiles = make_profiles(band, stems, gc_shift, homos)
        # re-evaluate all pools under this matrix
        for t in targets:
            for arm in ("A", "C"):
                if arm in pools[t]:
                    evaluate_matrix(pools[t][arm], profiles)
        # per-target cell classification
        tot_af = tot_nav = tot_her2 = 0
        her2_targets = set()
        for t in targets:
            cells = per_target_cells(pools[t], profiles)
            for p in PROFILE_ORDER:
                if cells[p]["a_deliverable"] < DELIVERY_SIZE:
                    tot_af += 1
                    if cells[p]["navigable"]:
                        tot_nav += 1
                    else:
                        tot_her2 += 1
                        her2_targets.add(t)
        # protocol simulation (full pools; A-only probes still sim)
        b = c_ = 0
        c_e2e = 0
        for t in targets:
            a_cands = [c for c in pools[t].get("A", [])]
            a_pass = per_band_passers(a_cands, profiles)
            a_jcd = {p: a_pass[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}
            c_jcd = arm_c_sim(t, pools, profiles)
            c_e2e += all(c_jcd[p] for p in PROFILE_ORDER)
            for p in PROFILE_ORDER:
                if c_jcd[p] and not a_jcd[p]:
                    b += 1
                elif a_jcd[p] and not c_jcd[p]:
                    c_ += 1
        n = b + c_
        pval = (float(binomtest(min(b, c_), n, 0.5,
                                alternative="two-sided").pvalue) if n else 1.0)
        nav_frac = tot_nav / tot_af if tot_af else 1.0
        rows.append({
            "band": band, "stems": stems, "gc": gc_shift, "homos": homos,
            "a_fail": tot_af, "navigable": tot_nav, "her2": tot_her2,
            "nav_frac": round(nav_frac, 3), "her2_targets": len(her2_targets),
            "b": b, "c": c_, "p": pval, "c_e2e": round(c_e2e / len(targets), 3),
        })

    # rank: prefer decisive + high b + low c + low her2 + high nav
    rows.sort(key=lambda r: (r["p"] < 0.05, r["b"], -r["c"], -r["her2"],
                             r["nav_frac"], r["a_fail"]), reverse=True)
    print(f"\n{'band':9s} {'stems':12s} {'gc':>4s} {'homo':>10s} | "
          f"{'A-fail':>6s} {'nav':>3s} {'her2':>4s} {'nav%':>5s} "
          f"{'hT':>3s} | {'b':>2s} {'c':>2s} {'P':>7s} {'Ce2e':>5s}")
    for r in rows[:30]:
        print(f"{r['band']:9s} {str(r['stems']):12s} {r['gc']:>4.2f} "
              f"{str(r['homos']):>10s} | {r['a_fail']:>6d} {r['navigable']:>3d} "
              f"{r['her2']:>4d} {r['nav_frac']:>5.3f} {r['her2_targets']:>3d} | "
              f"{r['b']:>2d} {r['c']:>2d} {r['p']:>7.4f} {r['c_e2e']:>5.3f}")
    print(f"\ntotal variants: {len(rows)}; decisive (P<0.05 & e2e>=0.8): "
          f"{sum(1 for r in rows if r['p'] < 0.05 and r['c_e2e'] >= 0.8)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
