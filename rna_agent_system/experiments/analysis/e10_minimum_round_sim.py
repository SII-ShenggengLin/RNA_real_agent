#!/usr/bin/env python3
"""E11 feasibility simulation — minimum-one-round-per-band reinforcement.

E10 S2 showed b=9/c=4 (P=0.267): mechanized allocation fixed the c=8 blowup
but the band-priority allocation starves the second-largest-gap band (usually
standard, where the rule arm's L50 grid is naturally strong) — 4 c-cells all
"single band starved". Fix candidate: guarantee >=1 reinforcement round per
band (3 rounds = compact/standard/extended each once; any extra round goes by
gap), so no band can be starved.

Modes (same 48-raw cap, same relax matrix, real E10 S2 cache):
  V1: probe 18 + probe2 4 (mechanized n2 for passers<2 lengths) + reinforce 26
      (3 rounds: one per band, gap-ordered, n=min(8, remaining))
  V2: probe 18 + reinforce 30 (4 rounds: one per band + 1 by gap)
  Both: within-band gear choice = laplace-smoothed expected passers; realized
  passers use the merged per-length pass rate (same as E9.5 sim mode B').
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
    RAW_BUDGET_PER_TARGET,
)

RUNS = PROJECT_ROOT / "experiments" / "results" / "e10_runs_s2.jsonl"


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


def simulate(t: str, by: dict, variant: str) -> dict:
    a_rec = by[(t, "A")]
    a_pass = per_band_passers(a_rec["candidates"])
    a_jcd = {p: a_pass[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}

    probe_cands = [c for c in by[(t, "C")]["candidates"]
                   if c["gear"]["seed"] == 42 and c["gear"]["n_samples"] == 2]
    pool = list(probe_cands)
    sampled = {(c["gear"]["aptamer_length"], c["gear"]["seed"]) for c in pool}
    spent = len(probe_cands)
    rate = merged_rate(t, by)

    def reinforce_band(band: str, n: int) -> None:
        """One round: best unsampled (L, seed) gear within *band* by laplace
        estimate; realized passers = merged rate x n (virtual)."""
        nonlocal spent
        spec = PROFILES[band]
        cand_gears = [
            (L, s) for L in C_LATTICE_LENGTHS for s in C_REQUEST_SEEDS
            if spec["lo"] <= L <= spec["hi"] and (L, s) not in sampled
        ]
        if not cand_gears or n <= 0:
            return
        est = {L: laplace_est(pool, L) for L, _ in cand_gears}
        best = max(cand_gears, key=lambda g: est[g[0]])
        Lg, sg = best
        realized = int(round(rate.get(Lg, 0.0) * n))
        for i in range(realized):
            pool.append({
                "length": Lg, "gc": 0.5, "max_homopolymer_run": 0,
                "longest_stem_bp": 0, "sequence": f"VIRT{t}{Lg}{sg}{i:02d}",
                "id": f"virt{Lg}s{sg}i{i:02d}",
                "matrix_pass": {
                    p: (PROFILES[p]["lo"] <= Lg <= PROFILES[p]["hi"]
                        and PROFILES[p]["gc_lo"] <= 0.5 <= PROFILES[p]["gc_hi"]
                        and 0 < PROFILES[p]["homo"]
                        and 0 <= PROFILES[p]["stem"])
                    for p in PROFILE_ORDER
                },
            })
        spent += n
        sampled.add((Lg, sg))

    # probe2 (V1 only): mechanized n2 for passers<2 lengths, budget 4 raw
    if variant == "V1":
        for prof in PROFILE_ORDER:
            if spent + 2 > RAW_BUDGET_PER_TARGET:
                break
            spec = PROFILES[prof]
            for L in C_LATTICE_LENGTHS:
                if spec["lo"] <= L <= spec["hi"]:
                    passers = sum(1 for c in pool
                                  if c.get("length") == L and _passing(c))
                    if passers < 2 and (L, 7) not in sampled:
                        realized = int(round(rate.get(L, 0.0) * 2))
                        for i in range(realized):
                            pool.append({
                                "length": L, "gc": 0.5, "max_homopolymer_run": 0,
                                "longest_stem_bp": 0,
                                "sequence": f"VIRT{t}{L}7{i:02d}",
                                "id": f"virt{L}s7i{i:02d}",
                                "matrix_pass": {
                                    p: (PROFILES[p]["lo"] <= L <= PROFILES[p]["hi"]
                                        and PROFILES[p]["gc_lo"] <= 0.5 <= PROFILES[p]["gc_hi"]
                                        and 0 < PROFILES[p]["homo"]
                                        and 0 <= PROFILES[p]["stem"])
                                    for p in PROFILE_ORDER
                                },
                            })
                        spent += 2
                        sampled.add((L, 7))
                        break  # one length per band in probe2

    # reinforcement: minimum one round per band, then extras by gap
    n_rounds = 3 if variant == "V1" else 4
    band_order = list(PROFILE_ORDER)
    for rnd in range(n_rounds):
        remaining = RAW_BUDGET_PER_TARGET - spent
        n = min(8, remaining)
        if n <= 0:
            break
        passers = per_band_passers(pool)
        gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
        # choose band: guaranteed rounds first (each band once), then by gap
        if rnd < len(band_order):
            band = band_order[rnd]
        else:
            if all(g <= 0 for g in gaps.values()):
                break
            band = max(gaps, key=gaps.get)
        reinforce_band(band, n)

    c_pass = per_band_passers(pool)
    c_jcd = {p: c_pass[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}
    return {p: (a_jcd[p], c_jcd[p]) for p in PROFILE_ORDER}


def main() -> int:
    by = load_records()
    targets = sorted({t for t, _ in by})
    for variant in ("V1", "V2"):
        b = c_ = 0
        rows = []
        for t in targets:
            res = simulate(t, by, variant)
            for p in PROFILE_ORDER:
                a_jcd, c_jcd = res[p]
                if c_jcd and not a_jcd:
                    b += 1
                elif not c_jcd and a_jcd:
                    c_ += 1
            rows.append((t, res))
        n = b + c_
        pval = (float(binomtest(min(b, c_), n, 0.5,
                                alternative="two-sided").pvalue) if n else 1.0)
        print(f"=== {variant} (min-1-round-per-band) ===")
        print(f"  b={b} c={c_} P={pval:.4f}  (decisive if P<0.05)")
        for t, res in rows:
            a = [1 if v[0] else 0 for v in res.values()]
            c = [1 if v[1] else 0 for v in res.values()]
            flags = "".join("B" if c[i] and not a[i] else ("c" if a[i] and not c[i] else ".")
                            for i in range(3))
            print(f"    {t:26s} {flags} A={a} C={c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
