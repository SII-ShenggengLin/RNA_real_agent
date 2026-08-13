#!/usr/bin/env python3
"""E9.5 pre-registration feasibility simulation — mechanized gear allocation.

Question: can GenNav be decisive on aptamers WITHOUT lowering any standard
(same matrix, same 48-raw budget cap both arms, same per-profile JCD McNemar
endpoint) by replacing the LLM's free-form request_generate choices with a
deterministic allocation (gap-weighted, expected-passers-ranked; LLM only
arbitrates)? Mirrors E6's "ranking is mechanized; LLM arbitrates ties only".

Data: real E9 S2 run records (relax v1 matrix, 10 targets). Modes:
  A (conservative): reinforcement rounds may only use gears that EXIST in the
    E9 cache — the mechanized policy restricted to the LLM-chosen gear set
    (lower bound; identical gear space as E9's LLM).
  B' (realistic): pass-rate ESTIMATE from the probe only (laplace-smoothed
    n2 per length); virtual reinforcement gears drawn fresh at expected
    passers = estimate x n, but their realized passers use the MERGED
    per-length rate (a per-length average of what fresh seeds actually
    produced). D1 is modeled optimistically: deliverable when passers >= 5.
  B (upper bound): like B' but the estimate IS the merged per-length rate.

Truth for E10 sits between A and B': the mechanized policy generates fresh
gears (not in cache) guided by probe estimates; seed-level variation (n2
probe 0/2 vs fresh seed 5/8 for the same length, e.g. VEGF L65, Trypsin L70)
is the main uncertainty. Pre-registration note: simulation only; the E10
judgement book must be written before any fresh generation.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scipy.stats import binomtest  # noqa: E402

from experiments.run_e9_gennav_aptamer import (  # noqa: E402
    PROFILES,
    PROFILE_ORDER,
    C_LATTICE_LENGTHS,
    DELIVERY_SIZE,
    C_REQUEST_SEEDS,
    RAW_BUDGET_PER_TARGET,
)

RUNS = PROJECT_ROOT / "experiments" / "results" / "e9_runs_s2.jsonl"


def load_records() -> dict[tuple[str, str], dict]:
    out = {}
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["target_id"], r["arm"])] = r
    return out


def _passing(c: dict) -> bool:
    return any(c["matrix_pass"].values())


def pass_rate_by_length(t: str, by: dict) -> dict[int, float]:
    """Merged-pool per-length pass rate (any profile) — 'true' realized rate."""
    cands = [c for r in (by[(t, "A")], by[(t, "C")]) for c in r["candidates"]]
    per: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for c in cands:
        L = c["gear"]["aptamer_length"]
        per[L][1] += 1
        if _passing(c):
            per[L][0] += 1
    return {L: n / max(tot, 1) for L, (n, tot) in per.items()}


def probe_estimate(t: str, by: dict) -> dict[int, float]:
    """Laplace-smoothed pass-rate estimate from the probe (L, s42, n2) only."""
    probe = [c for c in by[(t, "C")]["candidates"]
             if c["gear"]["seed"] == 42 and c["gear"]["n_samples"] == 2]
    per: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for c in probe:
        L = c["gear"]["aptamer_length"]
        per[L][1] += 1
        if _passing(c):
            per[L][0] += 1
    return {L: (k + 1) / (n + 2) for L, (k, n) in per.items()}


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


def simulate(t: str, by: dict, mode: str) -> dict:
    a_rec = by[(t, "A")]
    a_pass = per_band_passers(a_rec["candidates"])
    a_jcd = {p: a_pass[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}

    # probe pool (real)
    probe_cands = [c for c in by[(t, "C")]["candidates"]
                   if c["gear"]["seed"] == 42 and c["gear"]["n_samples"] == 2]
    pool = list(probe_cands)
    sampled = {(c["gear"]["aptamer_length"], c["gear"]["seed"]) for c in pool}
    spent = len(probe_cands)

    merged_rate = pass_rate_by_length(t, by)
    est_rate = probe_estimate(t, by)

    for _round in range(4):
        passers = per_band_passers(pool)
        gaps = {p: DELIVERY_SIZE - passers[p] for p in PROFILE_ORDER}
        if all(g <= 0 for g in gaps.values()):
            break
        n = min(8, RAW_BUDGET_PER_TARGET - spent)
        if n <= 0:
            break
        # candidate gears: any unsampled (L, seed in {7,99})
        cand_gears = [(L, s) for L in C_LATTICE_LENGTHS for s in C_REQUEST_SEEDS
                      if (L, s) not in sampled]
        if not cand_gears:
            break

        def score(gear: tuple[int, int]) -> float:
            """Gap-weighted expected repair: sum over profiles of
            min(gap, expected new passers contributed by this gear)."""
            Lg, _sg = gear
            est = est_rate.get(Lg, 0.0) if mode != "B" else merged_rate.get(Lg, 0.0)
            exp_new = est * n
            s = 0.0
            for p, spec in PROFILES.items():
                if spec["lo"] <= Lg <= spec["hi"]:
                    s += min(gaps[p], exp_new)
            return s

        best = max(cand_gears, key=score)
        Lg, sg = best
        if mode == "A":
            real = [c for c in by[(t, "C")]["candidates"]
                    if c["gear"]["aptamer_length"] == Lg
                    and c["gear"]["seed"] == sg]
            if not real:
                break
            pool.extend(real)
            spent += len(real)
        else:
            realized = merged_rate.get(Lg, 0.0) * n  # what fresh seeds produce
            est = est_rate.get(Lg, 0.0) if mode != "B" else merged_rate.get(Lg, 0.0)
            n_pass = int(round(realized))
            for i in range(n_pass):
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

    c_pass = per_band_passers(pool)
    c_jcd = {p: c_pass[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}
    return {p: (a_jcd[p], c_jcd[p]) for p in PROFILE_ORDER}


def main() -> int:
    by = load_records()
    targets = sorted({t for t, _ in by})
    for mode in ("A", "Bp", "B"):
        m = "B'" if mode == "Bp" else mode
        b = c_ = 0
        rows = []
        for t in targets:
            res = simulate(t, by, mode)
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
        print(f"=== Mode {m} (mechanized allocation) ===")
        print(f"  b={b} c={c_} P={pval:.4f}  (decisive if b>=9, c<=1)")
        for t, res in rows:
            a = [1 if v[0] else 0 for v in res.values()]
            c = [1 if v[1] else 0 for v in res.values()]
            print(f"    {t:26s} A={a} C={c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
