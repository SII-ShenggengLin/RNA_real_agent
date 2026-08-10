#!/usr/bin/env python3
"""E1 EXTENSION go/no-go + robustness analysis (2026-08-04, W3-4 milestone).

Pre-registration: experiments/run_e1_capability_profiling.py docstring,
"E1 EXTENSION PRE-REGISTRATION (2026-08-04)" section. Rigor patches vs the
pilot analysis (e1_go_no_go.py), all pre-registered:

  1. Threshold sensitivity grid: pass/fail at AUROC in {0.6,0.7,0.8,0.9} and
     rho in {0.4,0.5,0.6,0.7} reported for every oracle x target cell.
     Headline criterion unchanged (AUROC > 0.8, rho >= 0.6).
  2. Enrichment factor: EF@top-3 (primary small-n metric) and EF@25%
     (secondary) = (binder fraction in top-k oracle-ranked entries of the
     target) / (binder base rate of the target).
  3. Wording discipline: conclusions are stated as "no oracle shows RELIABLE
     screening/ranking power ACROSS TARGETS"; a single borderline cell whose
     95% CI covers chance does not count as an unlock.

Ranking is restricted to anchor-set entries flagged ranking_eligible
(within-assay Kd comparability). Screening uses all binders vs negatives.

Inputs:
  --anchor-set  data/benchmarks/external_anchors/aptamers/e1_anchor_set_v2.json
  --scoring     pilot + extension Part A jsonl (merged by id, latest wins)
  --docking     pilot + extension Part B jsonl (merged by pose_id, latest wins)
Output: experiments/results/e1_capability_summary_v2.json
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import auroc, bootstrap_auroc_ci  # noqa: E402, F401
from scipy import stats as _stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

ORACLES = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
AUROC_PASS = 0.8
RHO_PASS = 0.6
DOCK_PASS_FRAC = 2 / 3
AUROC_GRID = [0.6, 0.7, 0.8, 0.9]
RHO_GRID = [0.4, 0.5, 0.6, 0.7]
EF_TOP_K = 3
EF_FRAC = 0.25

_median = statistics.median


def merged_rows(paths: list[Path], key: str) -> dict:
    latest: dict = {}
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                latest[r[key]] = r  # later files / lines win
    return latest


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    rho, _ = _stats.spearmanr(xs, ys)
    return float(rho)


def enrichment_factor(scores: list[float], is_binder: list[bool], k: int) -> float | None:
    """(binder fraction among top-k by score) / (binder base rate)."""
    n = len(scores)
    if n == 0 or not any(is_binder):
        return None
    k = min(k, n)
    order = sorted(range(n), key=lambda i: scores[i], reverse=True)[:k]
    top_frac = sum(1 for i in order if is_binder[i]) / k
    base = sum(is_binder) / n
    return top_frac / base if base > 0 else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anchor-set", type=Path, required=True)
    ap.add_argument("--scoring", type=Path, nargs="+", required=True)
    ap.add_argument("--docking", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    meta = json.loads(args.anchor_set.read_text())
    entry_meta = {e["id"]: e for e in meta["entries"]}
    targets: list[str] = []
    for e in meta["entries"]:
        if e["target"] not in targets:
            targets.append(e["target"])

    rows_a = merged_rows(args.scoring, "id")
    rows_b = merged_rows(args.docking, "pose_id")

    # ── Part A: ranking + screening + EF + threshold grid, per oracle x target ──
    per_ot: dict = {}
    for target in targets:
        ids = [i for i, m in entry_meta.items() if m["target"] == target]
        trows = [rows_a[i] for i in ids if i in rows_a]
        binders = [r for r in trows if entry_meta[r["id"]]["role"].startswith("binder")]
        negatives = [r for r in trows if entry_meta[r["id"]]["role"] == "negative"]
        rank_rows = [r for r in binders
                     if entry_meta[r["id"]].get("kd_nm") is not None
                     and entry_meta[r["id"]].get("ranking_eligible", True)]
        for oracle in ORACLES:
            cell = {"n_binder": len(binders), "n_negative": len(negatives),
                    "n_ranking_eligible": len(rank_rows)}
            xs = [r["raw"].get(oracle) for r in rank_rows]
            ok = [x is not None for x in xs]
            if sum(ok) >= 3:
                rho = spearman(
                    [x for x, k in zip(xs, ok) if k],
                    [-math.log10(entry_meta[r["id"]]["kd_nm"]) for r, x, k in zip(rank_rows, xs, ok) if k],
                )
                cell["ranking_spearman_rho"] = rho
                cell["ranking_pass"] = (rho is not None and rho >= RHO_PASS)
                cell["ranking_pass_grid"] = {str(t): (rho is not None and rho >= t) for t in RHO_GRID}
            else:
                cell.update(ranking_spearman_rho=None, ranking_pass=None, ranking_pass_grid=None)
            pos = [r["raw"].get(oracle) for r in binders]
            neg = [r["raw"].get(oracle) for r in negatives]
            pos = [x for x in pos if x is not None]
            neg = [x for x in neg if x is not None]
            if pos and neg:
                a, lo, hi = bootstrap_auroc_ci(pos, neg)
                cell["screening_auroc"] = a
                cell["screening_auroc_ci95"] = [lo, hi]
                cell["screening_ci_covers_chance"] = lo <= 0.5 <= hi
                cell["screening_pass"] = a > AUROC_PASS
                cell["screening_pass_grid"] = {str(t): a > t for t in AUROC_GRID}
                scores = pos + neg
                flags = [True] * len(pos) + [False] * len(neg)
                cell["ef_top3"] = enrichment_factor(scores, flags, EF_TOP_K)
                cell["ef_25pct"] = enrichment_factor(scores, flags, max(1, round(len(scores) * EF_FRAC)))
            else:
                cell.update(screening_auroc=None, screening_auroc_ci95=None,
                            screening_ci_covers_chance=None, screening_pass=None,
                            screening_pass_grid=None, ef_top3=None, ef_25pct=None)
            per_ot[f"{oracle} | {target}"] = cell

    unlocks = [k for k, c in per_ot.items() if c.get("screening_pass")]
    reliable_unlocks = [k for k in unlocks if not per_ot[k].get("screening_ci_covers_chance")]
    any_rank = [k for k, c in per_ot.items() if c.get("ranking_pass")]

    # ── Part B: docking power (merged anchors, overall + per target) ──
    anchor_target = {a["aptamer_entry"]: a.get("target") for a in meta.get("docking_anchors", [])}
    by_anchor: dict[str, list] = {}
    for r in rows_b.values():
        by_anchor.setdefault(r["anchor"], []).append(r)
    docking: dict = {}
    n_top1 = 0
    for anchor, recs in sorted(by_anchor.items()):
        scored = [r for r in recs if r.get("egarps_native_probability") is not None]
        native = [r for r in scored if r["kind"] == "native"]
        decoys = [r for r in scored if r["kind"] == "decoy"]
        if not native:
            docking[anchor] = {"status": "native not scored", "target": anchor_target.get(anchor)}
            continue
        np_native = native[0]["egarps_native_probability"]
        rank = 1 + sum(1 for d in decoys if d["egarps_native_probability"] > np_native)
        top1 = rank == 1
        n_top1 += top1
        docking[anchor] = {
            "target": anchor_target.get(anchor),
            "n_poses_scored": len(scored), "native_rank": rank,
            "native_np": np_native,
            "median_decoy_np": (float(_median([d["egarps_native_probability"] for d in decoys])) if decoys else None),
            "top1": top1,
        }
    n_scored_anchors = sum(1 for d in docking.values() if "native_rank" in d)
    dock_frac = (n_top1 / n_scored_anchors) if n_scored_anchors else None
    docking_pass = dock_frac is not None and dock_frac >= DOCK_PASS_FRAC
    per_target_dock: dict = {}
    for anchor, d in docking.items():
        t = d.get("target")
        if t and "native_rank" in d:
            agg = per_target_dock.setdefault(t, {"n": 0, "top1": 0})
            agg["n"] += 1
            agg["top1"] += int(d["top1"])

    decision_bits = []
    if reliable_unlocks:
        decision_bits.append(f"screening UNLOCKED (AUROC>0.8, CI excludes chance): {reliable_unlocks}")
    elif unlocks:
        decision_bits.append(f"borderline screening cells (AUROC>0.8 but CI covers chance, NOT unlocks): {unlocks}")
    else:
        decision_bits.append("no oracle-target passes screening (AUROC>0.8): 'no oracle shows reliable "
                             "screening power for RNA-protein aptamers across targets' stands")
    grid_09 = [k for k, c in per_ot.items() if (c.get("screening_pass_grid") or {}).get("0.9")]
    grid_06 = [k for k, c in per_ot.items() if (c.get("screening_pass_grid") or {}).get("0.6")]
    decision_bits.append(f"threshold sensitivity: cells passing AUROC>0.6: {len(grid_06)}; "
                         f"AUROC>0.9: {len(grid_09)} (of {len(per_ot)})")
    decision_bits.append(f"ranking pass cells (rho>=0.6, ranking-eligible subsets): {any_rank or 'none'}")
    decision_bits.append(f"docking power (EGARPS native top-1): {n_top1}/{n_scored_anchors} "
                         f"-> {'PASS' if docking_pass else 'NO PASS'}; per target: {per_target_dock}")

    summary = {
        "analysis": "E1 oracle capability profiling EXTENSION go/no-go + robustness",
        "date": "2026-08-04",
        "preregistration": "run_e1_capability_profiling.py docstring, E1 EXTENSION PRE-REGISTRATION section",
        "thresholds": {"screening_auroc_pass": AUROC_PASS, "ranking_rho_pass": RHO_PASS,
                       "docking_top1_frac_pass": DOCK_PASS_FRAC},
        "sensitivity_grids": {"auroc": AUROC_GRID, "rho": RHO_GRID},
        "ef_params": {"ef_top_k": EF_TOP_K, "ef_frac": EF_FRAC},
        "targets": targets,
        "part_a_per_oracle_target": per_ot,
        "part_b_docking": docking,
        "screening_unlocks": unlocks,
        "screening_unlocks_reliable": reliable_unlocks,
        "decision_bits": decision_bits,
        "n_part_a": len(rows_a), "n_part_b": len(rows_b),
    }
    args.out.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")

    print(f"Part A: {len(rows_a)} entries | Part B: {len(rows_b)} poses | targets: {targets}\n")
    for k, c in per_ot.items():
        rho = c.get("ranking_spearman_rho")
        a = c.get("screening_auroc")
        print(f"{k:45s} rho={rho if rho is None else round(rho, 3)} "
              f"AUROC={a if a is None else round(a, 3)} {c.get('screening_auroc_ci95', '')} "
              f"EF3={None if c.get('ef_top3') is None else round(c['ef_top3'], 2)}")
    print()
    for anchor, d in docking.items():
        print(f"docking {anchor}: {d}")
    print()
    for b in decision_bits:
        print(" *", b)
    print(f"\n-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
