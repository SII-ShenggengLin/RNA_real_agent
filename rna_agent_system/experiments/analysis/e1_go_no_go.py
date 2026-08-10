#!/usr/bin/env python3
"""E1 oracle capability profiling — go/no-go analysis (2026-08-04).

Pre-registration: experiments/run_e1_capability_profiling.py docstring;
REDESIGN_2026-08-03_CALIBRATED_AGENT.md §3 E1 (approved 2026-08-04).

Inputs:
  - experiments/results/e1_oracle_scoring.jsonl  (Part A, 29 anchor entries)
  - experiments/results/e1_docking_power.jsonl   (Part B, 3 anchors x 21 poses)
Output: experiments/results/e1_capability_summary.json

Metrics (per oracle x target):
  ranking:   Spearman(oracle, -log10 Kd) on binders with kd_nm (report rho;
             n=5-8 per target, no p values per pre-registration)
  screening: AUROC(binder vs negative) + bootstrap 95% CI (stats_utils)
  docking:   per anchor, rank of native pose by egarps native_probability
             among the 21 poses; pass = native top-1 in >= 2/3 anchors
Go/no-go:
  screening pass for an oracle-target = AUROC > 0.8 -> unlock note;
  ranking pass = rho >= 0.6; docking pass = native top-1 >= 2/3 anchors.
  If NO oracle-target passes screening: the "no screening power" empirical
  finding stands (expected direction).
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import auroc, bootstrap_auroc_ci  # noqa: E402
from scipy import stats as _stats  # noqa: E402

_median = statistics.median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

RESULTS = PROJECT_ROOT / "experiments" / "results"
OUT_A = RESULTS / "e1_oracle_scoring.jsonl"
OUT_B = RESULTS / "e1_docking_power.jsonl"
SUMMARY = RESULTS / "e1_capability_summary.json"

ORACLES = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
TARGETS = ["Thrombin", "VEGF", "PDGF-BB"]
AUROC_PASS = 0.8
RHO_PASS = 0.6
DOCK_PASS_FRAC = 2 / 3


def latest_per_key(path: Path, key: str) -> dict:
    latest = {}
    if not path.exists():
        return latest
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("success"):
            latest[r[key]] = r  # file order: latest wins
    return latest


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    rho, _ = _stats.spearmanr(xs, ys)
    return float(rho)


def main() -> int:
    rows_a = latest_per_key(OUT_A, "id")
    rows_b = latest_per_key(OUT_B, "pose_id")

    # ── Part A: ranking + screening per oracle x target ──
    per_ot: dict = {}
    for target in TARGETS:
        trows = [r for r in rows_a.values() if r["target"] == target]
        binders_kd = [r for r in trows if r["role"] == "binder" and r.get("kd_nm") is not None]
        binders = [r for r in trows if r["role"].startswith("binder")]
        negatives = [r for r in trows if r["role"] == "negative"]
        for oracle in ORACLES:
            cell = {"n_binder_kd": len(binders_kd), "n_binder": len(binders), "n_negative": len(negatives)}
            xs = [r["raw"].get(oracle) for r in binders_kd]
            ok = [x is not None for x in xs]
            if sum(ok) >= 3:
                rho = spearman(
                    [x for x, k in zip(xs, ok) if k],
                    [-math.log10(r["kd_nm"]) for r, k in zip(binders_kd, ok) if k],
                )
                cell["ranking_spearman_rho"] = rho
                cell["ranking_pass"] = (rho is not None and rho >= RHO_PASS)
            else:
                cell["ranking_spearman_rho"] = None
                cell["ranking_pass"] = None
            pos = [r["raw"].get(oracle) for r in binders]
            neg = [r["raw"].get(oracle) for r in negatives]
            pos = [x for x in pos if x is not None]
            neg = [x for x in neg if x is not None]
            if pos and neg:
                a, lo, hi = bootstrap_auroc_ci(pos, neg)
                cell["screening_auroc"] = a
                cell["screening_auroc_ci95"] = [lo, hi]
                cell["screening_pass"] = a > AUROC_PASS
            else:
                cell["screening_auroc"] = None
                cell["screening_pass"] = None
            per_ot[f"{oracle} | {target}"] = cell

    unlocks = [k for k, c in per_ot.items() if c.get("screening_pass")]
    any_rank = [k for k, c in per_ot.items() if c.get("ranking_pass")]

    # ── Part B: docking power (native top-1 per anchor) ──
    by_anchor: dict[str, list] = {}
    for r in rows_b.values():
        by_anchor.setdefault(r["anchor"], []).append(r)
    docking = {}
    n_top1 = 0
    for anchor, recs in sorted(by_anchor.items()):
        scored = [r for r in recs if r.get("egarps_native_probability") is not None]
        native = [r for r in scored if r["kind"] == "native"]
        decoys = [r for r in scored if r["kind"] == "decoy"]
        if not native:
            docking[anchor] = {"status": "native not scored"}
            continue
        np_native = native[0]["egarps_native_probability"]
        n_better = sum(1 for d in decoys if d["egarps_native_probability"] > np_native)
        rank = 1 + n_better
        top1 = rank == 1
        n_top1 += top1
        docking[anchor] = {
            "n_poses_scored": len(scored), "native_rank": rank,
            "native_np": np_native,
            "median_decoy_np": (float(_median([d["egarps_native_probability"] for d in decoys])) if decoys else None),
            "top1": top1,
        }
    dock_frac = (n_top1 / len(docking)) if docking else None
    docking_pass = dock_frac is not None and dock_frac >= DOCK_PASS_FRAC

    decision_bits = []
    if unlocks:
        decision_bits.append(f"screening UNLOCKED for: {unlocks}")
    else:
        decision_bits.append("no oracle-target passes screening (AUROC>0.8): "
                             "'deployed oracles lack screening power for RNA-protein aptamers' stands")
    decision_bits.append(f"ranking pass cells (rho>=0.6): {any_rank or 'none'}")
    decision_bits.append(f"docking power (EGARPS native top-1): {n_top1}/{len(docking)} "
                         f"-> {'PASS' if docking_pass else 'NO PASS'}")

    summary = {
        "analysis": "E1 oracle capability profiling go/no-go",
        "date": "2026-08-04",
        "preregistration": "run_e1_capability_profiling.py docstring; REDESIGN §3 E1",
        "thresholds": {"screening_auroc_pass": AUROC_PASS, "ranking_rho_pass": RHO_PASS,
                       "docking_top1_frac_pass": DOCK_PASS_FRAC},
        "part_a_per_oracle_target": per_ot,
        "part_b_docking": docking,
        "screening_unlocks": unlocks,
        "decision_bits": decision_bits,
        "n_part_a": len(rows_a), "n_part_b": len(rows_b),
    }
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")

    print(f"Part A: {len(rows_a)} entries | Part B: {len(rows_b)} poses\n")
    for k, c in per_ot.items():
        rho = c.get("ranking_spearman_rho")
        a = c.get("screening_auroc")
        print(f"{k:45s} rho={rho if rho is None else round(rho,3)} "
              f"AUROC={a if a is None else round(a,3)} {c.get('screening_auroc_ci95','')}")
    print()
    for anchor, d in docking.items():
        print(f"docking {anchor}: {d}")
    print()
    for b in decision_bits:
        print(" *", b)
    print(f"\n-> {SUMMARY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
