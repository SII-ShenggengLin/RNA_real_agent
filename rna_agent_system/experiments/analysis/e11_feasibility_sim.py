#!/usr/bin/env python3
"""E11 feasibility simulation — cap 48->64, A-arm lattice variants, C-arm 6 rounds.

E10 S2 (cap 48) ended NO-GO: b=9, c=4, P=0.267. Boundary: under a 48-raw cap the
c-reversal bands (pass rate <20%) need 2+ reinforcement rounds, unreachable in 3
rounds; floor-round variants are worse (b=7-9, c=5-6) — E10's band-priority 3
rounds is the Pareto front at 48 raw. E11 raises the pre-registered budget cap to
64 on BOTH arms (parameter re-preregistration, not a criterion change: P<0.05 AND
C e2e>=0.8 unchanged).

This simulation (criteria-book development artifact, no services, real E10 S2
cache) estimates the primary endpoint for the E11 protocol at cap 64:
  C arm: probe 18 (9 lengths x s42 x n2, unchanged) + probe2 <=8 (mechanized n2
          for passers<2 lengths, s7, unchanged) + 6 gap-priority reinforcement
          rounds (38 raw), gear = laplace-smoothed expected passers, realized
          passers = merged per-length rate x n (same realization as
          e10_minimum_round_sim.py).
  A arm: lattice VARIANTS (all pre-registration candidates):
    F1 = {30,50,80} x {42,123,7} x n7 = 63 (uniform 3x3; old cells re-sampled,
          truncated from cache n8 to n7)
    F2 = {30,50,80} x {42,123} x n8 (48, cache-reusable) + {25,40,65} x {7} x n5
          = 63 (each band: anchor + C-lattice min uncovered length; per-band 21)
    F3 = {30,50,80} x {42,123} x n8 + {25,65} x {7} x n8 = 64 (per-band 24/16/24)
  Virtual A-arm cells: realized passers = merged per-length rate x n; all virtual
  sequences distinct (D1 satisfied trivially, same as the E10 sims).

Panel = E10 S2's 12 targets (10 old + CAII + Pepsin), the conservative case:
E11's A lattice is a superset of E10's, so new-target A-fail densities are
non-increasing; the E10 S1 measurement (frac 0.6 >= 0.3) gates a 12-target panel,
any fresh-measurement drift toward 15 targets would be C-favorable and is
excluded by design (conservative against C).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy.stats import binomtest  # noqa: E402

from experiments.run_e10_gennav_aptamer import (  # noqa: E402
    PROFILES,
    PROFILE_ORDER,
    C_LATTICE_LENGTHS,
    DELIVERY_SIZE,
    C_REQUEST_SEEDS,
    C_PROBE2_SEED,
)

RUNS = PROJECT_ROOT / "experiments" / "results" / "e10_runs_s2.jsonl"

RAW_BUDGET_E11 = 64
C_ROUNDS_E11 = 6
C_PROBE2_BUDGET = 8

# A-arm lattice variants: [(length, seed, n_samples), ...]
# A0 = E10 lattice unchanged (48 raw) — the ASYMMETRIC-cap variant (A 48 vs
#      C 64): quantifies the "lower the bar" option for the user's judgment.
# F1b = third seed at the SAME anchor lengths (no truncation of cached n8 cells;
#      new cells are (30/50/80, 7, n5) — new cache keys, old cells untouched).
A_CELLS = {
    "F1": [(L, s, 7) for L in (30, 50, 80) for s in (42, 123, 7)],
    "F1b": [(30, 42, 8), (30, 123, 8), (50, 42, 8), (50, 123, 8), (80, 42, 8),
            (80, 123, 8), (30, 7, 5), (50, 7, 5), (80, 7, 5)],
    "F2": [(30, 42, 8), (30, 123, 8), (50, 42, 8), (50, 123, 8), (80, 42, 8),
           (80, 123, 8), (25, 7, 5), (40, 7, 5), (65, 7, 5)],
    "F3": [(30, 42, 8), (30, 123, 8), (50, 42, 8), (50, 123, 8), (80, 42, 8),
           (80, 123, 8), (25, 7, 8), (65, 7, 8)],
    "A0": [],  # E10 static lattice only (48 raw)
}
A_TOTAL = {k: sum(n for _, _, n in cells) for k, cells in A_CELLS.items()}
for k, tot in A_TOTAL.items():
    assert tot <= RAW_BUDGET_E11, f"A-arm lattice {k} exceeds 64-raw cap: {tot}"


def load_records() -> dict[tuple[str, str], dict]:
    out = {}
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["target_id"], r["arm"])] = r
    return out


def _passing(c: dict) -> bool:
    return any(c["matrix_pass"].values())


def per_band_passers(pool: list[dict]) -> dict[str, int]:
    out = {}
    for p, spec in PROFILES.items():
        out[p] = sum(
            1 for c in pool
            if spec["lo"] <= c["length"] <= spec["hi"]
            and spec["gc_lo"] <= c["gc"] <= spec["gc_hi"]
            and c["max_homopolymer_run"] < spec["homo"]
            and c["longest_stem_bp"] <= spec["stem"]
        )
    return out


def merged_rate(t: str, by: dict) -> dict[int, float]:
    """Merged per-length pass rate over the real E10 A+C pools (realization)."""
    cands = [c for r in (by[(t, "A")], by[(t, "C")]) for c in r["candidates"]]
    per: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for c in cands:
        L = c["gear"]["aptamer_length"]
        per[L][1] += 1
        if _passing(c):
            per[L][0] += 1
    return {L: n / max(tot, 1) for L, (n, tot) in per.items()}


def laplace_est(pool: list[dict], L: int) -> float:
    cands = [c for c in pool if c.get("length") == L]
    n = len(cands)
    k = sum(1 for c in cands if _passing(c))
    return (k + 1) / (n + 2)


def virtual_cell(pool: list[dict], t: str, L: int, s: int, n: int,
                 rate: dict[int, float]) -> None:
    """Append `n` virtual candidates for gear (L, s): realized passers from the
    merged rate; all distinct ids (D1 trivially satisfied)."""
    realized = int(round(rate.get(L, 0.0) * n))
    for i in range(realized):
        pool.append({
            "length": L, "gc": 0.5, "max_homopolymer_run": 0,
            "longest_stem_bp": 0, "sequence": f"VIRT{t}{L}s{s}i{i:02d}",
            "id": f"virt{L}s{s}i{i:02d}",
            "matrix_pass": {
                p: (PROFILES[p]["lo"] <= L <= PROFILES[p]["hi"]
                    and PROFILES[p]["gc_lo"] <= 0.5 <= PROFILES[p]["gc_hi"]
                    and 0 < PROFILES[p]["homo"] and 0 <= PROFILES[p]["stem"])
                for p in PROFILE_ORDER
            },
        })


def arm_a_sim(t: str, by: dict, variant: str) -> dict[str, bool]:
    """E11 A arm: real E10 A pool (cache-reusable cells) + virtual new cells."""
    a_rec = by[(t, "A")]
    pool = [c for c in a_rec["candidates"]]
    sampled = {(c["gear"]["aptamer_length"], c["gear"]["seed"]) for c in pool}
    rate = merged_rate(t, by)
    for L, s, n in A_CELLS[variant]:
        if (L, s) not in sampled:
            virtual_cell(pool, t, L, s, n, rate)
    passers = per_band_passers(pool)
    return {p: passers[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}


def _band_zero_passers(pool: list[dict], prof: str) -> bool:
    """Degrade condition (arbitration prompt): every in-band length with samples
    has zero matrix passers -> band declared unservable by the LLM."""
    spec = PROFILES[prof]
    in_band = [c for c in pool
               if spec["lo"] <= c.get("length", 0) <= spec["hi"]]
    return bool(in_band) and not any(_passing(c) for c in in_band)


def arm_c_sim(t: str, by: dict, min_round: bool = False,
              degrade_aware: bool = False) -> dict[str, bool]:
    """E11 C arm at cap 64: real probe + re-simulated probe2 + 6 rounds of
    mechanized reinforcement (LLM arbitration approximated by the top-ranked
    proposal). min_round=True: rounds 1-3 one per band, rounds 4-6 by gap
    (floor-round variant at 64 — the 48-cap floor-round sim was worse).
    degrade_aware=True: bands with zero passers across all in-band lengths are
    excluded from gap consideration (LLM degrade declaration; rounds flow to
    fixable bands — the BSA-type budget sink is removed)."""
    c_rec = by[(t, "C")]
    probe = [c for c in c_rec["candidates"]
             if c["gear"]["seed"] == 42 and c["gear"]["n_samples"] == 2]
    pool = list(probe)
    sampled = {(c["gear"]["aptamer_length"], c["gear"]["seed"]) for c in pool}
    spent = len(probe)
    rate = merged_rate(t, by)

    # probe2 (mechanized, <=8 raw): gap>0 bands, passers<2 lengths, s7 x n2
    for prof in PROFILE_ORDER:
        if spent + 2 > RAW_BUDGET_E11:
            break
        spec = PROFILES[prof]
        for L in C_LATTICE_LENGTHS:
            if spec["lo"] <= L <= spec["hi"]:
                passers_L = sum(1 for c in pool if c.get("length") == L
                                and _passing(c))
                if passers_L < 2 and (L, C_PROBE2_SEED) not in sampled:
                    virtual_cell(pool, t, L, C_PROBE2_SEED, 2, rate)
                    spent += 2
                    sampled.add((L, C_PROBE2_SEED))
                    break  # one length per band in probe2 (driver logic)

    # reinforcement: 6 rounds; band = gap-priority (or one-per-band first)
    for rnd in range(C_ROUNDS_E11):
        remaining = RAW_BUDGET_E11 - spent
        n = min(8, remaining)
        if n <= 0:
            break
        passers = per_band_passers(pool)
        gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
        if degrade_aware:
            for p in PROFILE_ORDER:
                if gaps[p] > 0 and _band_zero_passers(pool, p):
                    gaps[p] = 0  # LLM degrade declaration frees the band
        if all(g <= 0 for g in gaps.values()):
            break
        if min_round and rnd < len(PROFILE_ORDER):
            band = PROFILE_ORDER[rnd]  # guaranteed one round per band
        else:
            band = max(gaps, key=gaps.get)  # band-priority (E10 mechanism)
        spec = PROFILES[band]
        cand_gears = [
            (L, s) for L in C_LATTICE_LENGTHS for s in C_REQUEST_SEEDS
            if spec["lo"] <= L <= spec["hi"] and (L, s) not in sampled
        ]
        if not cand_gears:
            break
        est = {L: laplace_est(pool, L) for L, _ in cand_gears}
        Lg, sg = max(cand_gears, key=lambda g: est[g[0]])
        virtual_cell(pool, t, Lg, sg, n, rate)
        spent += n
        sampled.add((Lg, sg))

    passers = per_band_passers(pool)
    return {p: passers[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}


def main() -> int:
    by = load_records()
    targets = sorted({t for t, _ in by})
    print(f"E11 feasibility (cap 64): {len(targets)} targets, "
          f"A-arm totals {A_TOTAL}, C-arm probe18+probe2<=8+{C_ROUNDS_E11} rounds")
    # grid: A-lattice x C-round mode
    modes = [("gap", False, False), ("min-round", True, False),
             ("degrade-aware", False, True)]
    for variant in ("A0", "F1", "F1b", "F2", "F3"):
        for mode_label, min_round, degrade_aware in modes:
            b = c_ = 0
            rows = []
            for t in targets:
                a_jcd = arm_a_sim(t, by, variant)
                c_jcd = arm_c_sim(t, by, min_round=min_round,
                                  degrade_aware=degrade_aware)
                for p in PROFILE_ORDER:
                    if c_jcd[p] and not a_jcd[p]:
                        b += 1
                    elif a_jcd[p] and not c_jcd[p]:
                        c_ += 1
                rows.append((t, a_jcd, c_jcd))
            n = b + c_
            pval = (float(binomtest(min(b, c_), n, 0.5,
                                    alternative="two-sided").pvalue) if n else 1.0)
            print(f"=== A lattice {variant} (raw {A_TOTAL[variant]}) / "
                  f"C {mode_label} ===")
            print(f"  b={b} c={c_} P={pval:.4f}  (decisive if P<0.05; "
                  f"E10 was b=9 c=4 P=0.267)")
            for t, a, c_ in rows:
                flags = "".join("B" if c_[p] and not a[p]
                                else ("c" if a[p] and not c_[p] else ".")
                                for p in PROFILE_ORDER)
                print(f"    {t:26s} {flags} "
                      f"A={[int(a[p]) for p in PROFILE_ORDER]} "
                      f"C={[int(c_[p]) for p in PROFILE_ORDER]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
