#!/usr/bin/env python3
"""E12 pre-registration-gate analysis (NOT sanctioned — analysis only).

Question: can GenNav win on the aptamer side at EQUAL budget (48 raw, both
arms — the user's standard)? E11 closed the budget-rescale and panel-expansion
escape routes. This sim tests the third axis that E11 did not: the C-arm
PROTOCOL's probe-vs-reinforcement split at the same 48-raw cap. Real E10 S2
cache; A arm = E10 static grid unchanged (48 raw).

Protocol variants (all at cap 48, A arm identical):
  V0 = E10 protocol: probe 9 lengths x s42 x n2 (18) + probe2 <=8 + 3 rounds
       (sanity check: must reproduce E10's b=9 c=4)
  V1 = probe anchors {25,40,65} x s42 x n2 (6) + probe2 <=8 + 4 rounds
       (probe cost 18->6 frees 12 raw for a 4th reinforcement round)
  V2 = probe 9 lengths x s42 x n1 (9) + probe2 <=8 + up to 4 rounds
  V3 = probe anchors n2 (6) + probe2 <=8 + up to 5 rounds
Realization: same merged per-length pass-rate model as e11_feasibility_sim.py
(trusted for the E10/E11 boundary conclusions).

Also prints the per-(target,length) merged pass rates of the four E10 c-cells,
to classify each c-band as fixable (moderate rate) vs structural (near zero),
and the e2e ceiling implied by HER2-class targets (unfixable cells).
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
from experiments.analysis.e11_feasibility_sim import (  # noqa: E402
    arm_a_sim,
    _passing,
    virtual_cell,
    per_band_passers,
    merged_rate,
    laplace_est,
)

RUNS = PROJECT_ROOT / "experiments" / "results" / "e10_runs_s2.jsonl"
RAW_BUDGET = 48  # E10 cap — equal-budget analysis


def load_records() -> dict[tuple[str, str], dict]:
    out = {}
    for line in RUNS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["target_id"], r["arm"])] = r
    return out


def arm_c_sim(t: str, by: dict, probe_lengths: tuple, probe_n: int,
              max_rounds: int, a_prior: bool = False) -> dict[str, bool]:
    """C arm at cap 48 with a parameterized probe / round split.

    a_prior=True: laplace estimates additionally read the A arm's static-grid
    samples (the driver already runs arm A first, so A's real candidates are
    available to C's allocator — a protocol change fusing A-pool pass rates
    into the estimator without spending C's budget)."""
    c_rec = by[(t, "C")]
    pool = []
    sampled = set()
    spent = 0
    rate = merged_rate(t, by)
    est_pool = pool
    if a_prior:
        est_pool = pool + [c for c in by[(t, "A")]["candidates"]]
    for L in probe_lengths:
        virtual_cell(pool, t, L, 42, probe_n, rate)
        spent += probe_n
        sampled.add((L, 42))
    # probe2 (mechanized, <=8 raw): gap>0 bands, passers<2 lengths, s7 x n2
    for prof in PROFILE_ORDER:
        if spent + 2 > RAW_BUDGET:
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
                    break
    # reinforcement: gap-priority rounds (E10 mechanism, no LLM arbitration sim)
    for _rnd in range(max_rounds):
        remaining = RAW_BUDGET - spent
        n = min(8, remaining)
        if n <= 0:
            break
        passers = per_band_passers(pool)
        gaps = {p: max(0, DELIVERY_SIZE - passers[p]) for p in PROFILE_ORDER}
        if all(g <= 0 for g in gaps.values()):
            break
        band = max(gaps, key=gaps.get)
        spec = PROFILES[band]
        cand_gears = [
            (L, s) for L in C_LATTICE_LENGTHS for s in C_REQUEST_SEEDS
            if spec["lo"] <= L <= spec["hi"] and (L, s) not in sampled
        ]
        if not cand_gears:
            break
        est = {L: laplace_est(est_pool, L) for L, _ in cand_gears}
        Lg, sg = max(cand_gears, key=lambda g: est[g[0]])
        virtual_cell(pool, t, Lg, sg, n, rate)
        spent += n
        sampled.add((Lg, sg))
    passers = per_band_passers(pool)
    return {p: passers[p] >= DELIVERY_SIZE for p in PROFILE_ORDER}


def main() -> int:
    by = load_records()
    targets = sorted({t for t, _ in by})

    # e2e ceiling from HER2-class (unfixable) cells, E10 S2 verdict
    verdict = json.load(open(
        PROJECT_ROOT / "experiments" / "results" / "e10_verdict_s2.json",
        encoding="utf-8"))
    her2 = verdict["matrix_lock"]["her2_class_cells"]
    her2_targets = {c.split("/")[0] for c in her2}
    ceiling = (len(targets) - len(her2_targets)) / len(targets)
    print(f"HER2-class cells: {her2}")
    print(f"HER2 targets: {len(her2_targets)} of {len(targets)} -> "
          f"max possible C e2e = {ceiling:.3f} (criterion >= 0.8 -> "
          f"{'UNREACHABLE on this panel' if ceiling < 0.8 else 'reachable'})")

    # c-cell rate classification (E10 c-cells: A pass / C fail)
    print("\nc-cell fixability (merged per-length pass rate on real E10 pools):")
    for pr in verdict["pairs"]:
        if pr["A_jcd"] and not pr["C_jcd"]:
            t = pr["target_id"]
            prof = pr["profile"]
            spec = PROFILES[prof]
            lens = [L for L in C_LATTICE_LENGTHS if spec["lo"] <= L <= spec["hi"]]
            rates = merged_rate(t, by)
            row = ", ".join(f"L{L}:{rates.get(L, 0.0):.2f}" for L in lens)
            print(f"  {t}/{prof}: {row}")

    variants = [
        ("V0 E10 probe18/n2/3r", C_LATTICE_LENGTHS, 2, 3, False),
        ("V1 probe anchors6/n2/4r", (25, 40, 65), 2, 4, False),
        ("V2 probe9/n1/4r", C_LATTICE_LENGTHS, 1, 4, False),
        ("V3 probe anchors6/n2/5r", (25, 40, 65), 2, 5, False),
        ("V4 probe18/n2/3r + A-prior", C_LATTICE_LENGTHS, 2, 3, True),
        ("V5 probe anchors6/n2/4r + A-prior", (25, 40, 65), 2, 4, True),
    ]
    print(f"\nEqual-budget protocol grid (cap {RAW_BUDGET}, A arm = E10 grid):")
    for label, probe_lens, probe_n, rounds, a_prior in variants:
        b = c_ = 0
        c_e2e = 0
        rows = []
        for t in targets:
            a_jcd = arm_a_sim(t, by, "A0")
            c_jcd = arm_c_sim(t, by, probe_lens, probe_n, rounds,
                              a_prior=a_prior)
            c_e2e += all(c_jcd[p] for p in PROFILE_ORDER)
            for p in PROFILE_ORDER:
                if c_jcd[p] and not a_jcd[p]:
                    b += 1
                elif a_jcd[p] and not c_jcd[p]:
                    c_ += 1
            rows.append((t, a_jcd, c_jcd))
        n = b + c_
        pval = (float(binomtest(min(b, c_), n, 0.5,
                                alternative="two-sided").pvalue) if n else 1.0)
        c_e2e_rate = c_e2e / len(targets)
        hit = "  <-- DECISIVE" if (pval < 0.05 and c_e2e_rate >= 0.8) else ""
        print(f"  {label}: b={b} c={c_} P={pval:.4f} C_e2e={c_e2e_rate:.3f}"
              f"{hit}  (E10: b=9 c=4 P=0.267 C_e2e=0.50; e2e ceiling {ceiling:.3f})")
        for t, a, c_ in rows:
            flags = "".join("B" if c_[p] and not a[p]
                            else ("c" if a[p] and not c_[p] else ".")
                            for p in PROFILE_ORDER)
            print(f"      {t:26s} {flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
