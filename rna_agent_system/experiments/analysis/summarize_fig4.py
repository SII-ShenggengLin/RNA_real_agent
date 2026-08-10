#!/usr/bin/env python3
"""Fig 4 summary statistics (docs/MANUSCRIPT.md §6.3).

Aggregates the Fig-4 Type-II BMC ablation JSONL shards into
`experiments/results/fig4_summary.json`:

- fixed-reference ASF recomputation from `pool_objectives` (see ASF_METHOD)
- paired Wilcoxon + Cliff's delta + BH-FDR for ASF and objective components
- exact Pareto hypervolume (3-D + three 2-D projections) per (target, seed)
  cell, BMC pools vs Serial pool (see HV_METHOD)
- BMC rounds execution rate, per-round and per-run timing
- per-target x condition mean +/- sd tables

The script degrades gracefully on partial data: targets/cells without
successful runs are reported and dropped from the affected paired tests, with
the actual n stated per test.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/summarize_fig4.py \
        [--inputs JSONL ...] [--output PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from stats_utils import bh_fdr, cliffs_delta, median_iqr, wilcoxon_paired  # noqa: E402
from agent_core.workflows.multi_objective import (  # noqa: E402
    achievement_scalarizing_function,
    normalize_value,
)

RESULTS = ROOT / "experiments" / "results"

# Objectives of RnaAptamerDesignWorkflow (AptamerCoordinator.OBJECTIVES);
# all three maximized.
OBJECTIVES = ["egarps_component", "rhofold_component", "iptm_component"]

PAIRED_METRICS = ["asf_fixed"] + OBJECTIVES

HV_2D_PROJECTIONS = [
    ("egarps_rhofold", ("egarps_component", "rhofold_component")),
    ("egarps_iptm", ("egarps_component", "iptm_component")),
    ("rhofold_iptm", ("rhofold_component", "iptm_component")),
]

CONDITIONS = [0, 1, 2, 3]
COND_LABELS = {0: "serial", 1: "bmc_x1", 2: "bmc_x2", 3: "bmc_x3"}
COMPARISONS = [(1, 0), (2, 0), (3, 0)]  # (bmc_k, serial)

ASF_METHOD = (
    "Fixed-reference ASF recomputation: per target, all `pool_objectives` "
    "points of every successful run (all conditions) are pooled; each "
    "objective dimension (egarps/rhofold/iptm_component; all maximized) is "
    "min-max normalized with bounds from that pool. The shared reference "
    "point is the per-dimension best over the target's Serial "
    "(bmc_max_rounds=0) pools ('utopian-of-Serial'), normalized with the same "
    "bounds. ASF distances of every run's best candidate are recomputed "
    "against this fixed reference with uniform weights and rho=1e-3 via "
    "agent_core.workflows.multi_objective.achievement_scalarizing_function. "
    "The stored asf_distance uses a per-run utopian reference and is NOT "
    "comparable across conditions (see multi_objective.py ANALYSIS CAVEAT), "
    "so it is never used for cross-condition tests. Targets whose runs all "
    "lack pool_objectives fall back to best-candidate vectors for bounds."
)

HV_METHOD = (
    "Exact hypervolume by recursive slicing along the first dimension "
    "(no third-party library). Per (target, seed_idx) cell the candidate "
    "pools (`pool_objectives`) of Serial and BMC x1/x2/x3 are compared; the "
    "reference point is the componentwise minimum of the merged pool across "
    "all conditions in that cell minus a 1e-6 margin. All objectives are "
    "maximized. Computed for the full 3-D objective vector and for three "
    "2-D projections (egarps-rhofold, egarps-iptm, rhofold-iptm)."
)


def load_records(paths: list[Path]) -> list[dict]:
    """Load JSONL records from all paths that exist."""
    records: list[dict] = []
    for path in paths:
        if not path.exists():
            print(f"WARNING: input not found, skipped: {path}")
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def dedupe_latest(records: list[dict]) -> dict[tuple, dict]:
    """Keep the latest record per job key (target_id, bmc_max_rounds, seed_idx).

    Duplicate keys arise from failure + retry; the record with the newest
    `timestamp` wins (missing timestamps sort oldest; ties keep the later
    line in file order).
    """
    latest: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("target_id"), r.get("bmc_max_rounds"), r.get("seed_idx"))
        prev = latest.get(key)
        if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
            latest[key] = r
    return latest


def get_best(record: dict, key: str):
    best = record.get("best") or {}
    value = best.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def pool_vectors(record: dict) -> list[dict[str, float]]:
    """Objective vectors from `pool_objectives` (rows with all dims present)."""
    vectors: list[dict[str, float]] = []
    for row in record.get("pool_objectives") or []:
        if not isinstance(row, dict):
            continue
        vec: dict[str, float] = {}
        for key in OBJECTIVES:
            value = row.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                vec[key] = float(value)
        if len(vec) == len(OBJECTIVES):
            vectors.append(vec)
    return vectors


def mean_sd(values: list[float]) -> dict:
    """Mean +/- sd summary; sd is None for n < 2 (repeat variance reported as-is)."""
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return {"n": 0, "mean": None, "sd": None}
    return {
        "n": len(vals),
        "mean": st.mean(vals),
        "sd": st.stdev(vals) if len(vals) >= 2 else None,
    }


def clean(obj):
    """Recursively convert NaN/inf floats to None for strict-JSON output."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return obj


def hypervolume(points: list[tuple[float, ...]], ref: tuple[float, ...]) -> float:
    """Exact HV of the union of boxes [ref, p] in maximization space.

    Recursive slicing along the first dimension; points not strictly above
    the reference in every dimension contribute zero volume and are dropped.
    """
    pts = [tuple(p) for p in points if all(pi > ri for pi, ri in zip(p, ref))]
    if not pts:
        return 0.0
    if len(ref) == 1:
        return max(p[0] for p in pts) - ref[0]
    pts.sort(key=lambda p: p[0], reverse=True)
    hv = 0.0
    prev = ref[0]
    # Slice from the lowest dim-0 value upward: slice [prev, pts[i][0]] is
    # covered by the projections of pts[0..i] (dim-0 >= pts[i][0]).
    for i in range(len(pts) - 1, -1, -1):
        width = pts[i][0] - prev
        if width > 0:
            hv += width * hypervolume([q[1:] for q in pts[: i + 1]], ref[1:])
        prev = pts[i][0]
    return hv


def recompute_fixed_asf(jobs: list[dict]) -> tuple[dict[tuple, float | None], dict]:
    """Recompute each successful run's best-candidate ASF against a fixed reference.

    Bounds come from the target's pooled `pool_objectives` (fallback: best
    vectors); the reference is the utopian point of the Serial pools.
    Returns ``(asf_by_job, diagnostics)``.
    """
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in jobs:
        if r.get("success"):
            by_target[r["target_id"]].append(r)

    asf_by_job: dict[tuple, float | None] = {}
    diag = {"targets_without_serial": [], "runs_missing_dims": 0, "targets_bounds_from_best": []}
    weights = {key: 1.0 / len(OBJECTIVES) for key in OBJECTIVES}

    for target, runs in sorted(by_target.items()):
        pools = [pool_vectors(r) for r in runs]  # aligned with `runs`
        all_points = [v for vecs in pools for v in vecs]
        bounds_source = "pool" if all_points else "best"
        if bounds_source == "pool":
            bounds: dict[str, tuple[float, float]] = {}
            for key in OBJECTIVES:
                vals = [p[key] for p in all_points]
                bounds[key] = (min(vals), max(vals))
        else:
            diag["targets_bounds_from_best"].append(target)
            bounds = {}
            for key in OBJECTIVES:
                vals = [get_best(r, key) for r in runs]
                vals = [v for v in vals if v is not None]
                if vals:
                    bounds[key] = (min(vals), max(vals))

        serial_runs = [r for r in runs if r.get("bmc_max_rounds") == 0]
        serial_points = [v for r, vecs in zip(runs, pools) if r.get("bmc_max_rounds") == 0 for v in vecs]
        if len(bounds) < len(OBJECTIVES) or (not serial_runs) or (
            bounds_source == "pool" and not serial_points
        ):
            diag["targets_without_serial"].append(target)
            for r in runs:
                asf_by_job[(target, r.get("bmc_max_rounds"), r.get("seed_idx"))] = None
            continue

        # Reference: utopian of Serial pools (fallback: Serial best vectors).
        norm_ref: dict[str, float] = {}
        for key in OBJECTIVES:
            lo, hi = bounds[key]
            if bounds_source == "pool":
                ref_raw = max(p[key] for p in serial_points)
            else:
                serial_vals = [get_best(r, key) for r in serial_runs]
                serial_vals = [v for v in serial_vals if v is not None]
                if not serial_vals:
                    norm_ref = {}
                    break
                ref_raw = max(serial_vals)
            norm_ref[key] = normalize_value(ref_raw, lo, hi)
        if not norm_ref:
            diag["targets_without_serial"].append(target)
            for r in runs:
                asf_by_job[(target, r.get("bmc_max_rounds"), r.get("seed_idx"))] = None
            continue

        for r in runs:
            job = (target, r.get("bmc_max_rounds"), r.get("seed_idx"))
            norm_vec: dict[str, float] = {}
            for key in OBJECTIVES:
                v = get_best(r, key)
                if v is None:
                    norm_vec = {}
                    break
                lo, hi = bounds[key]
                norm_vec[key] = normalize_value(v, lo, hi)
            if not norm_vec:
                diag["runs_missing_dims"] += 1
                asf_by_job[job] = None
                continue
            asf_by_job[job] = achievement_scalarizing_function(
                norm_vec, norm_ref, weights, rho=1e-3
            )
    return asf_by_job, diag


def cell_hypervolumes(jobs: list[dict]) -> tuple[dict, dict]:
    """Per (target, seed_idx) cell: 3-D and 2-D HV per condition.

    Returns ``(hv_by_cell, per_cell_detail)`` where ``hv_by_cell`` maps
    (target, seed_idx, cond, hv_name) -> float.
    """
    cells: dict[tuple, dict[int, list[dict[str, float]]]] = defaultdict(dict)
    for r in jobs:
        if not r.get("success"):
            continue
        cond = r.get("bmc_max_rounds")
        vecs = pool_vectors(r)
        if not vecs:
            continue
        cells[(r["target_id"], r.get("seed_idx"))][cond] = vecs

    hv_by_cell: dict[tuple, float] = {}
    detail: dict[str, dict] = defaultdict(dict)
    for (target, seed_idx), cond_pools in sorted(cells.items()):
        merged = [v for vecs in cond_pools.values() for v in vecs]
        ref3 = tuple(min(p[k] for p in merged) - 1e-6 for k in OBJECTIVES)
        cell_key = f"{target}#seed{seed_idx}"
        for cond, vecs in sorted(cond_pools.items()):
            pts3 = [tuple(p[k] for k in OBJECTIVES) for p in vecs]
            entry: dict = {
                "n_pool": len(vecs),
                "hv3d": hypervolume(pts3, ref3),
            }
            hv_by_cell[(target, seed_idx, cond, "hv3d")] = entry["hv3d"]
            for name, dims in HV_2D_PROJECTIONS:
                ref2 = tuple(min(p[k] for p in merged) - 1e-6 for k in dims)
                hv2 = hypervolume([tuple(p[k] for k in dims) for p in vecs], ref2)
                entry[f"hv2d_{name}"] = hv2
                hv_by_cell[(target, seed_idx, cond, f"hv2d_{name}")] = hv2
            detail[cell_key][COND_LABELS[cond]] = entry
        detail[cell_key]["reference_3d"] = list(ref3)
    return hv_by_cell, dict(detail)


def paired_stats(pairs: list[tuple[float, float]]) -> dict:
    """Wilcoxon + Cliff's delta for one paired comparison (x=BMC, y=Serial)."""
    if not pairs:
        return {"n": 0}
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    deltas = [x - y for x, y in pairs]
    return {
        "n": len(pairs),
        "median_serial": st.median(ys),
        "median_bmc": st.median(xs),
        "median_delta_bmc_minus_serial": st.median(deltas),
        "wilcoxon_p": wilcoxon_paired(xs, ys),
        "cliffs_delta": cliffs_delta(xs, ys),
    }


def paired_tests(
    per_target_metric: dict[str, dict[int, dict[str, float | None]]],
    hv_by_cell: dict[tuple, float],
) -> dict:
    """Component/ASF tests pair per target; HV tests pair per (target, seed) cell.

    All p-values (metrics + hypervolumes, every comparison) form ONE BH-FDR family.
    """
    results: dict[str, dict] = {"metrics": {}, "hypervolume": {}}
    flat: list[tuple[str, float]] = []  # (path, p) for BH

    for metric in PAIRED_METRICS:
        results["metrics"][metric] = {}
        for bmc, serial in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            pairs: list[tuple[float, float]] = []
            for target in sorted(per_target_metric):
                row = per_target_metric[target]
                v_serial = row.get(serial, {}).get(metric)
                v_bmc = row.get(bmc, {}).get(metric)
                if v_serial is None or v_bmc is None:
                    continue
                pairs.append((v_bmc, v_serial))
            entry = paired_stats(pairs)
            results["metrics"][metric][comp_key] = entry
            if entry.get("n"):
                flat.append((f"metrics.{metric}.{comp_key}", entry["wilcoxon_p"]))

    hv_names = ["hv3d"] + [f"hv2d_{name}" for name, _ in HV_2D_PROJECTIONS]
    cells = sorted({(t, s) for (t, s, _c, _n) in hv_by_cell})
    for hv_name in hv_names:
        results["hypervolume"][hv_name] = {}
        for bmc, serial in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            pairs = []
            for target, seed_idx in cells:
                v_serial = hv_by_cell.get((target, seed_idx, serial, hv_name))
                v_bmc = hv_by_cell.get((target, seed_idx, bmc, hv_name))
                if v_serial is None or v_bmc is None:
                    continue
                pairs.append((v_bmc, v_serial))
            entry = paired_stats(pairs)
            results["hypervolume"][hv_name][comp_key] = entry
            if entry.get("n"):
                flat.append((f"hypervolume.{hv_name}.{comp_key}", entry["wilcoxon_p"]))

    qs = bh_fdr([p for _, p in flat])
    for (path, _), q in zip(flat, qs):
        section, name, comp_key = path.split(".")
        results[section][name][comp_key]["q_bh"] = q
    return results


def rounds_and_timing(jobs: list[dict]) -> dict:
    """Rounds execution rate, per-round elapsed_ms from bmc_trace, run wall-clock."""
    exec_rates: dict[int, list[float]] = {c: [] for c in CONDITIONS if c > 0}
    exec_counts: dict[int, dict[str, int]] = {c: {"n_runs": 0, "n_completed_all": 0, "n_zero": 0}
                                              for c in CONDITIONS if c > 0}
    elapsed: dict[int, list[float]] = {c: [] for c in CONDITIONS}
    per_round_ms: list[float] = []
    n_traces = 0

    for r in jobs:
        if not r.get("success"):
            continue
        cond = r.get("bmc_max_rounds")
        if cond not in elapsed:
            continue
        if r.get("elapsed_seconds") is not None:
            elapsed[cond].append(float(r["elapsed_seconds"]))
        if cond > 0:
            executed = r.get("bmc_rounds_executed")
            if executed is not None:
                exec_rates[cond].append(float(executed) / cond)
                exec_counts[cond]["n_runs"] += 1
                if executed == cond:
                    exec_counts[cond]["n_completed_all"] += 1
                if executed == 0:
                    exec_counts[cond]["n_zero"] += 1
        trace = r.get("bmc_trace")
        if isinstance(trace, list) and trace:
            n_traces += 1
            for entry in trace:
                if isinstance(entry, dict):
                    for key in ("elapsed_ms", "time_ms", "duration_ms"):
                        if entry.get(key) is not None:
                            per_round_ms.append(float(entry[key]))
                            break

    out: dict = {"rounds_execution": {}, "elapsed_seconds": {}, "per_round": {}}
    for c in CONDITIONS:
        if c > 0:
            rates = exec_rates[c]
            out["rounds_execution"][COND_LABELS[c]] = {
                **exec_counts[c],
                "mean_rate": st.mean(rates) if rates else None,
                "median_rate": st.median(rates) if rates else None,
            }
        med, q1, q3 = median_iqr(elapsed[c])
        out["elapsed_seconds"][COND_LABELS[c]] = {
            "n": len(elapsed[c]),
            "mean": st.mean(elapsed[c]) if elapsed[c] else None,
            "median": med,
            "iqr": [q1, q3] if elapsed[c] else None,
        }
    if per_round_ms:
        med, q1, q3 = median_iqr(per_round_ms)
        out["per_round"] = {
            "n_rounds_observed": len(per_round_ms),
            "n_runs_with_trace": n_traces,
            "elapsed_ms_median": med,
            "elapsed_ms_iqr": [q1, q3],
        }
    else:
        out["per_round"] = {
            "n_rounds_observed": 0,
            "n_runs_with_trace": n_traces,
            "note": "no bmc_trace with per-round elapsed_ms in current records",
        }
    return out


def fmt(v, nd=4):
    if isinstance(v, float) and math.isnan(v):
        return "-"
    return f"{v:.{nd}g}" if isinstance(v, (int, float)) else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inputs", nargs="*", default=None,
                        help="JSONL shards (default: all existing experiments/results/fig4_type2_shard_*.jsonl)")
    parser.add_argument("--output", type=Path, default=RESULTS / "fig4_summary.json")
    args = parser.parse_args()

    inputs = [Path(p) for p in args.inputs] if args.inputs else sorted(RESULTS.glob("fig4_type2_shard_*.jsonl"))
    records = load_records(inputs)
    jobs_map = dedupe_latest(records)
    jobs = list(jobs_map.values())
    ok_jobs = [r for r in jobs if r.get("success")]

    summary: dict = {
        "generated_by": "experiments/analysis/summarize_fig4.py",
        "inputs": [str(p) for p in inputs if p.exists()],
        "asf_method": ASF_METHOD,
        "hv_method": HV_METHOD,
        "n_records_raw": len(records),
        "n_jobs_unique": len(jobs),
        "n_jobs_success": len(ok_jobs),
    }

    # ---------------- coverage ----------------
    targets_all = sorted({r["target_id"] for r in jobs if r.get("target_id")})
    targets_ok = sorted({r["target_id"] for r in ok_jobs})
    coverage: dict = {"n_targets_with_records": len(targets_all), "n_targets_with_success": len(targets_ok)}
    per_cond: dict = {}
    for c in CONDITIONS:
        runs_c = [r for r in jobs if r.get("bmc_max_rounds") == c]
        ok_c = [r for r in runs_c if r.get("success")]
        missing = sorted(set(targets_all) - {r["target_id"] for r in ok_c})
        per_cond[COND_LABELS[c]] = {
            "n_runs": len(runs_c),
            "n_success": len(ok_c),
            "n_targets_success": len(ok_c) and len({r["target_id"] for r in ok_c}) or 0,
            "targets_without_success": missing,
            "failed_jobs": [
                {"target_id": r["target_id"], "seed_idx": r.get("seed_idx"), "error": r.get("error")}
                for r in runs_c if not r.get("success")
            ][:20],
        }
    coverage["per_condition"] = per_cond
    summary["conditions"] = coverage

    # ---------------- fixed-reference ASF ----------------
    asf_by_job, asf_diag = recompute_fixed_asf(jobs)
    summary["asf_diagnostics"] = asf_diag

    # ---------------- per target x condition metric table ----------------
    run_values: dict[tuple, dict[str, float | None]] = {}
    for r in ok_jobs:
        job = (r["target_id"], r.get("bmc_max_rounds"), r.get("seed_idx"))
        vals: dict[str, float | None] = {m: get_best(r, m) for m in OBJECTIVES}
        vals["asf_fixed"] = asf_by_job.get(job)
        run_values[job] = vals

    per_target_metric: dict[str, dict[int, dict[str, float | None]]] = defaultdict(lambda: defaultdict(dict))
    per_target_table: dict[str, dict] = defaultdict(dict)
    for target in targets_ok:
        for c in CONDITIONS:
            reps_vals = [
                vals for (t, cond, _s), vals in run_values.items()
                if t == target and cond == c
            ]
            if not reps_vals:
                continue
            table_entry: dict = {}
            for metric in PAIRED_METRICS:
                col = [v.get(metric) for v in reps_vals]
                col = [v for v in col if v is not None]
                ms = mean_sd(col)
                table_entry[metric] = ms
                per_target_metric[target][c][metric] = ms["mean"] if ms["n"] else None
            per_target_table[target][COND_LABELS[c]] = table_entry
    summary["per_target"] = {t: dict(conds) for t, conds in sorted(per_target_table.items())}

    # ---------------- hypervolume ----------------
    hv_by_cell, hv_detail = cell_hypervolumes(jobs)
    summary["hypervolume"] = {"per_cell": hv_detail}

    # ---------------- paired tests ----------------
    summary["paired_tests"] = paired_tests(per_target_metric, hv_by_cell)
    n_metric_tests = len(PAIRED_METRICS) * len(COMPARISONS)
    n_hv_tests = (1 + len(HV_2D_PROJECTIONS)) * len(COMPARISONS)
    summary["paired_tests_note"] = (
        "ASF/component tests pair per target (mean over successful seed sets); "
        "hypervolume tests pair per (target, seed_idx) cell. "
        f"BH-FDR computed over one family of up to {n_metric_tests + n_hv_tests} tests "
        f"({len(PAIRED_METRICS)} metrics + {1 + len(HV_2D_PROJECTIONS)} hypervolumes, "
        "x 3 comparisons each; entries with n=0 carry no p-value)."
    )

    # ---------------- rounds & timing ----------------
    summary["rounds_execution"] = rounds_and_timing(jobs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(clean(summary), ensure_ascii=False, indent=2) + "\n")

    # ---------------- console report ----------------
    print("=== Fig 4 Type-II BMC ablation summary ===")
    print(f"inputs: {len(summary['inputs'])} file(s); raw records {len(records)} -> "
          f"{len(jobs)} unique jobs, {len(ok_jobs)} successful")
    print(f"targets with success: {len(targets_ok)} ({', '.join(targets_ok) or '-'})")
    print("\n--- condition overview ---")
    print(f"{'cond':<8} {'n_runs':>6} {'n_ok':>5} {'n_tgt':>5}  missing targets")
    for c in CONDITIONS:
        pc = per_cond[COND_LABELS[c]]
        print(f"{COND_LABELS[c]:<8} {pc['n_runs']:>6} {pc['n_success']:>5} "
              f"{pc['n_targets_success']:>5}  {', '.join(pc['targets_without_success']) or '-'}")

    print("\n--- paired tests: ASF + components (pairing unit: target) ---")
    print(f"{'metric':<20} {'comp':<16} {'n':>3} {'med_ser':>9} {'med_bmc':>9} "
          f"{'d_med':>9} {'p':>9} {'delta':>7} {'q':>9}")
    for metric in PAIRED_METRICS:
        for bmc, _s in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            e = summary["paired_tests"]["metrics"][metric][comp_key]
            if not e.get("n"):
                print(f"{metric:<20} {comp_key:<16} {0:>3}  (no paired data)")
                continue
            print(f"{metric:<20} {comp_key:<16} {e['n']:>3} "
                  f"{fmt(e['median_serial']):>9} {fmt(e['median_bmc']):>9} "
                  f"{fmt(e['median_delta_bmc_minus_serial']):>9} "
                  f"{fmt(e['wilcoxon_p']):>9} {fmt(e['cliffs_delta'], 3):>7} {fmt(e.get('q_bh')):>9}")

    print("\n--- paired tests: hypervolume (pairing unit: target x seed cell) ---")
    print(f"{'hv':<22} {'comp':<16} {'n':>3} {'med_ser':>9} {'med_bmc':>9} "
          f"{'d_med':>9} {'p':>9} {'delta':>7} {'q':>9}")
    for hv_name, e_by_comp in summary["paired_tests"]["hypervolume"].items():
        for bmc, _s in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            e = e_by_comp[comp_key]
            if not e.get("n"):
                print(f"{hv_name:<22} {comp_key:<16} {0:>3}  (no paired data)")
                continue
            print(f"{hv_name:<22} {comp_key:<16} {e['n']:>3} "
                  f"{fmt(e['median_serial']):>9} {fmt(e['median_bmc']):>9} "
                  f"{fmt(e['median_delta_bmc_minus_serial']):>9} "
                  f"{fmt(e['wilcoxon_p']):>9} {fmt(e['cliffs_delta'], 3):>7} {fmt(e.get('q_bh')):>9}")

    print("\n--- rounds execution & timing ---")
    re_out = summary["rounds_execution"]
    for c in CONDITIONS:
        if c > 0:
            e = re_out["rounds_execution"][COND_LABELS[c]]
            print(f"{COND_LABELS[c]:<8} exec rate mean {fmt(e['mean_rate'], 3)} "
                  f"(runs {e['n_runs']}, all-rounds {e['n_completed_all']}, zero-rounds {e['n_zero']})")
    for c in CONDITIONS:
        e = re_out["elapsed_seconds"][COND_LABELS[c]]
        print(f"{COND_LABELS[c]:<8} elapsed_s n={e['n']} mean={fmt(e['mean'], 1)} median={fmt(e['median'], 1)}")
    print(f"per-round: {re_out['per_round']}")

    print("\n--- per-target fixed-ASF mean +/- sd (seed sets) ---")
    print(f"{'target':<28}" + "".join(f"{COND_LABELS[c]:>22}" for c in CONDITIONS))
    for target in targets_ok:
        row = f"{target:<28}"
        for c in CONDITIONS:
            cell = per_target_table.get(target, {}).get(COND_LABELS[c], {}).get("asf_fixed")
            if cell and cell["n"]:
                sd = f"{cell['sd']:.3f}" if cell["sd"] is not None else "  -  "
                row += f"{cell['mean']:.3f}±{sd}(n={cell['n']})".rjust(22)
            else:
                row += "-".rjust(22)
        print(row)

    print(f"\n-> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
