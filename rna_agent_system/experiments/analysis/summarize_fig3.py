#!/usr/bin/env python3
"""Fig 3 summary statistics (docs/MANUSCRIPT.md §5.5).

Aggregates the Fig-3 Type-I BMC ablation JSONL shards into
`experiments/results/fig3_summary.json`:

- fixed-reference ASF recomputation (see ASF_METHOD note below)
- paired Wilcoxon + Cliff's delta + BH-FDR (Serial vs BMC x1/x2/x3)
- AUG/Kozak burial event counts per condition
- BMC rounds execution rate, per-round and per-run timing
- per-target x condition mean +/- sd tables

The script degrades gracefully on partial data: targets/conditions without
successful runs are reported and dropped from the affected paired tests, with
the actual n stated per test.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/summarize_fig3.py \
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

# User-facing objectives of FullLengthMrnaDesignWorkflow
# (ReferencePointCoordinator.USER_FACING_OBJECTIVES); all maximized.
OBJECTIVES = ["cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"]

# Paired-test metrics: recomputed ASF, objective components, junction MFE
# (raw and per-nt) and junction GC diffs.
PAIRED_METRICS = [
    "asf_fixed",
    "cds_component",
    "utr5_mrl",
    "utr3_stability",
    "full_mfe_score",
    "junction_5utr_cds_mfe",
    "junction_cds_3utr_mfe",
    "junction_5utr_cds_mfe_per_nt",
    "junction_cds_3utr_mfe_per_nt",
    "junction_5utr_cds_gc_diff",
    "junction_cds_3utr_gc_diff",
]

# Metrics shown in the per-target mean +/- sd table.
TABLE_METRICS = [
    "asf_fixed",
    "cds_component",
    "utr5_mrl",
    "utr3_stability",
    "full_mfe_score",
    "junction_5utr_cds_mfe_per_nt",
    "junction_cds_3utr_mfe_per_nt",
]

# Burial flags as stored by the driver (BEST_SCORE_KEYS); the
# cds_3utr kozak alias is checked defensively for older records.
BURIAL_FLAGS = {
    "junction_5utr_cds_aug_buried": ["junction_5utr_cds_aug_buried"],
    "junction_5utr_cds_kozak_buried": [
        "junction_5utr_cds_kozak_buried",
        "junction_cds_3utr_kozak_buried",
    ],
}

CONDITIONS = [0, 1, 2, 3]
COND_LABELS = {0: "serial", 1: "bmc_x1", 2: "bmc_x2", 3: "bmc_x3"}
COMPARISONS = [(1, 0), (2, 0), (3, 0)]  # (bmc_k, serial)

ASF_METHOD = (
    "Fixed-reference ASF recomputation: per target, each objective dimension "
    "(cds_component, utr5_mrl, utr3_stability, full_mfe_score; all maximized) "
    "is min-max normalized with bounds pooled across ALL successful runs of "
    "that target (every condition). The shared reference point is the "
    "per-dimension best among the target's Serial (bmc_max_rounds=0) best "
    "candidates ('utopian-of-Serial'), normalized with the same bounds. ASF "
    "distances of every run's best candidate are recomputed against this "
    "fixed reference with uniform weights and rho=1e-3 via "
    "agent_core.workflows.multi_objective.achievement_scalarizing_function. "
    "The stored asf_distance uses a per-run utopian reference and is NOT "
    "comparable across conditions (see multi_objective.py ANALYSIS CAVEAT), "
    "so it is never used for cross-condition tests."
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
    """Keep the latest record per job key (target_id, bmc_max_rounds, rep).

    Duplicate keys arise from failure + retry; the record with the newest
    `timestamp` wins (missing timestamps sort oldest; ties keep the later
    line in file order).
    """
    latest: dict[tuple, dict] = {}
    for r in records:
        key = (r.get("target_id"), r.get("bmc_max_rounds"), r.get("rep"))
        prev = latest.get(key)
        if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
            latest[key] = r
    return latest


def as_bool(value) -> bool:
    """Coerce a burial flag (bool / 0-1 / string) to bool."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in ("true", "1", "yes")


def get_best(record: dict, key: str):
    best = record.get("best") or {}
    value = best.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


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


def recompute_fixed_asf(jobs: list[dict]) -> tuple[dict[tuple, float | None], dict]:
    """Recompute each successful run's best-candidate ASF against a fixed reference.

    Returns ``(asf_by_job, diagnostics)`` where ``asf_by_job`` maps
    (target_id, rounds, rep) -> ASF distance (None when not computable).
    """
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in jobs:
        if r.get("success"):
            by_target[r["target_id"]].append(r)

    asf_by_job: dict[tuple, float | None] = {}
    diag = {"targets_without_serial": [], "runs_missing_dims": 0}
    weights = {key: 1.0 / len(OBJECTIVES) for key in OBJECTIVES}

    for target, runs in sorted(by_target.items()):
        # Pool bounds across ALL conditions of this target (maximization space).
        bounds: dict[str, tuple[float, float]] = {}
        for key in OBJECTIVES:
            vals = [get_best(r, key) for r in runs]
            vals = [v for v in vals if v is not None]
            if vals:
                bounds[key] = (min(vals), max(vals))

        serial_runs = [r for r in runs if r.get("bmc_max_rounds") == 0]
        if not serial_runs or len(bounds) < len(OBJECTIVES):
            diag["targets_without_serial"].append(target)
            for r in runs:
                asf_by_job[(target, r.get("bmc_max_rounds"), r.get("rep"))] = None
            continue

        # Reference: utopian of the Serial best candidates, normalized.
        norm_ref: dict[str, float] = {}
        for key in OBJECTIVES:
            lo, hi = bounds[key]
            serial_vals = [get_best(r, key) for r in serial_runs]
            serial_vals = [v for v in serial_vals if v is not None]
            if not serial_vals:
                norm_ref = {}
                break
            norm_ref[key] = normalize_value(max(serial_vals), lo, hi)
        if not norm_ref:
            diag["targets_without_serial"].append(target)
            for r in runs:
                asf_by_job[(target, r.get("bmc_max_rounds"), r.get("rep"))] = None
            continue

        for r in runs:
            job = (target, r.get("bmc_max_rounds"), r.get("rep"))
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


def paired_tests(
    per_target_metric: dict[str, dict[int, dict[str, float | None]]],
) -> dict:
    """Wilcoxon + Cliff's delta per metric per BMC-vs-Serial comparison.

    ``per_target_metric[target][cond][metric]`` holds per-target condition means.
    All p-values across every metric x comparison form ONE BH-FDR family.
    """
    results: dict[str, dict] = {}
    flat: list[tuple[str, str, float]] = []  # (metric, comp_key, p) for BH
    for metric in PAIRED_METRICS:
        results[metric] = {}
        for bmc, serial in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            xs: list[float] = []  # BMC values
            ys: list[float] = []  # Serial values
            for target in sorted(per_target_metric):
                row = per_target_metric[target]
                v_serial = row.get(serial, {}).get(metric)
                v_bmc = row.get(bmc, {}).get(metric)
                if v_serial is None or v_bmc is None:
                    continue
                xs.append(v_bmc)
                ys.append(v_serial)
            n = len(xs)
            if n == 0:
                results[metric][comp_key] = {"n": 0}
                continue
            deltas = [x - y for x, y in zip(xs, ys)]
            p = wilcoxon_paired(xs, ys)
            entry = {
                "n": n,
                "median_serial": st.median(ys),
                "median_bmc": st.median(xs),
                "median_delta_bmc_minus_serial": st.median(deltas),
                "wilcoxon_p": p,
                "cliffs_delta": cliffs_delta(xs, ys),
            }
            results[metric][comp_key] = entry
            flat.append((metric, comp_key, p))
    qs = bh_fdr([p for _, _, p in flat])
    for (metric, comp_key, _), q in zip(flat, qs):
        results[metric][comp_key]["q_bh"] = q
    return results


def burial_summary(jobs: list[dict]) -> dict:
    """Burial event counts/proportions per condition + per-target repair view."""
    per_cond: dict[int, dict[str, dict[str, int]]] = {
        c: {flag: {"n_true": 0, "n_total": 0} for flag in BURIAL_FLAGS} for c in CONDITIONS
    }
    any_cond: dict[int, dict[str, int]] = {c: {"n_true": 0, "n_total": 0} for c in CONDITIONS}
    # per target x condition: any-burial across reps
    target_cond_buried: dict[str, dict[int, bool]] = defaultdict(dict)

    for r in jobs:
        if not r.get("success"):
            continue
        cond = r.get("bmc_max_rounds")
        if cond not in per_cond:
            continue
        best = r.get("best") or {}
        any_buried = False
        for flag, aliases in BURIAL_FLAGS.items():
            value = None
            for alias in aliases:
                if alias in best:
                    value = best[alias]
                    break
            if value is None:
                continue
            per_cond[cond][flag]["n_total"] += 1
            if as_bool(value):
                per_cond[cond][flag]["n_true"] += 1
                any_buried = True
        any_cond[cond]["n_total"] += 1
        if any_buried:
            any_cond[cond]["n_true"] += 1
        target = r["target_id"]
        target_cond_buried[target][cond] = target_cond_buried[target].get(cond, False) or any_buried

    out: dict = {"per_condition": {}, "per_target_repair": {}}
    for c in CONDITIONS:
        label = COND_LABELS[c]
        out["per_condition"][label] = {}
        for flag in list(BURIAL_FLAGS) + ["any"]:
            counts = per_cond[c][flag] if flag != "any" else any_cond[c]
            n_t, n_n = counts["n_true"], counts["n_total"]
            out["per_condition"][label][flag] = {
                "n_buried": n_t,
                "n_runs": n_n,
                "proportion": (n_t / n_n) if n_n else None,
            }
    # Repair view: targets where Serial had any burial — did BMC clear it?
    for bmc, serial in COMPARISONS:
        comp_key = f"bmc{bmc}_vs_serial"
        buried_serial = clean_bmc = still_buried = 0
        paired_targets = 0
        for target, conds in sorted(target_cond_buried.items()):
            if serial not in conds or bmc not in conds:
                continue
            paired_targets += 1
            if conds[serial]:
                buried_serial += 1
                if conds[bmc]:
                    still_buried += 1
                else:
                    clean_bmc += 1
        out["per_target_repair"][comp_key] = {
            "n_targets_paired": paired_targets,
            "n_targets_serial_buried": buried_serial,
            "n_targets_bmc_clean": clean_bmc,
            "n_targets_still_buried": still_buried,
        }
    return out


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
                        help="JSONL shards (default: all existing experiments/results/fig3_type1_shard_*.jsonl)")
    parser.add_argument("--output", type=Path, default=RESULTS / "fig3_summary.json")
    args = parser.parse_args()

    inputs = [Path(p) for p in args.inputs] if args.inputs else sorted(RESULTS.glob("fig3_type1_shard_*.jsonl"))
    records = load_records(inputs)
    jobs_map = dedupe_latest(records)
    jobs = list(jobs_map.values())
    ok_jobs = [r for r in jobs if r.get("success")]

    summary: dict = {
        "generated_by": "experiments/analysis/summarize_fig3.py",
        "inputs": [str(p) for p in inputs if p.exists()],
        "asf_method": ASF_METHOD,
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
                {"target_id": r["target_id"], "rep": r.get("rep"), "error": r.get("error")}
                for r in runs_c if not r.get("success")
            ][:20],
        }
    coverage["per_condition"] = per_cond
    summary["conditions"] = coverage

    # ---------------- fixed-reference ASF ----------------
    asf_by_job, asf_diag = recompute_fixed_asf(jobs)
    summary["asf_diagnostics"] = asf_diag

    # ---------------- per target x condition metric table ----------------
    # run-level metric values: best scores + recomputed ASF
    run_values: dict[tuple, dict[str, float | None]] = {}
    for r in ok_jobs:
        job = (r["target_id"], r.get("bmc_max_rounds"), r.get("rep"))
        vals: dict[str, float | None] = {m: get_best(r, m) for m in PAIRED_METRICS if m != "asf_fixed"}
        vals["asf_fixed"] = asf_by_job.get(job)
        run_values[job] = vals

    # per target x condition: mean over reps
    per_target_metric: dict[str, dict[int, dict[str, float | None]]] = defaultdict(lambda: defaultdict(dict))
    per_target_table: dict[str, dict] = defaultdict(dict)
    for target in targets_ok:
        for c in CONDITIONS:
            reps_vals = [
                vals for (t, cond, _rep), vals in run_values.items()
                if t == target and cond == c
            ]
            if not reps_vals:
                continue
            table_entry: dict = {}
            for metric in TABLE_METRICS + [m for m in PAIRED_METRICS if m not in TABLE_METRICS]:
                col = [v.get(metric) for v in reps_vals]
                col = [v for v in col if v is not None]
                ms = mean_sd(col)
                table_entry[metric] = ms
                per_target_metric[target][c][metric] = ms["mean"] if ms["n"] else None
            per_target_table[target][COND_LABELS[c]] = table_entry
    summary["per_target"] = {t: dict(conds) for t, conds in sorted(per_target_table.items())}

    # ---------------- paired tests ----------------
    summary["paired_tests"] = paired_tests(per_target_metric)
    summary["paired_tests_note"] = (
        "Unit of pairing: target (per-target mean over successful reps). "
        f"BH-FDR computed over one family of "
        f"{len(PAIRED_METRICS) * len(COMPARISONS)} tests "
        "(11 metrics x 3 comparisons)."
    )

    # ---------------- burial ----------------
    summary["burial"] = burial_summary(jobs)

    # ---------------- rounds & timing ----------------
    summary["rounds_execution"] = rounds_and_timing(jobs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(clean(summary), ensure_ascii=False, indent=2) + "\n")

    # ---------------- console report ----------------
    print("=== Fig 3 Type-I BMC ablation summary ===")
    print(f"inputs: {len(summary['inputs'])} file(s); raw records {len(records)} -> "
          f"{len(jobs)} unique jobs, {len(ok_jobs)} successful")
    print(f"targets with success: {len(targets_ok)} ({', '.join(targets_ok) or '-'})")
    print("\n--- condition overview ---")
    print(f"{'cond':<8} {'n_runs':>6} {'n_ok':>5} {'n_tgt':>5}  missing targets")
    for c in CONDITIONS:
        pc = per_cond[COND_LABELS[c]]
        print(f"{COND_LABELS[c]:<8} {pc['n_runs']:>6} {pc['n_success']:>5} "
              f"{pc['n_targets_success']:>5}  {', '.join(pc['targets_without_success']) or '-'}")

    print("\n--- paired tests (Wilcoxon signed-rank, BMC minus Serial; BH-FDR over all tests) ---")
    print(f"{'metric':<32} {'comp':<16} {'n':>3} {'med_ser':>9} {'med_bmc':>9} "
          f"{'d_med':>9} {'p':>9} {'delta':>7} {'q':>9}")
    for metric in PAIRED_METRICS:
        for bmc, _s in COMPARISONS:
            comp_key = f"bmc{bmc}_vs_serial"
            e = summary["paired_tests"][metric][comp_key]
            if not e.get("n"):
                print(f"{metric:<32} {comp_key:<16} {0:>3}  (no paired data)")
                continue
            print(f"{metric:<32} {comp_key:<16} {e['n']:>3} "
                  f"{fmt(e['median_serial']):>9} {fmt(e['median_bmc']):>9} "
                  f"{fmt(e['median_delta_bmc_minus_serial']):>9} "
                  f"{fmt(e['wilcoxon_p']):>9} {fmt(e['cliffs_delta'], 3):>7} {fmt(e.get('q_bh')):>9}")

    print("\n--- burial events (any flag) ---")
    print(f"{'cond':<8} {'n_buried/n_runs':>18} {'proportion':>11}")
    for c in CONDITIONS:
        b = summary["burial"]["per_condition"][COND_LABELS[c]]["any"]
        print(f"{COND_LABELS[c]:<8} {str(b['n_buried']) + '/' + str(b['n_runs']):>18} "
              f"{fmt(b['proportion'], 3):>11}")
    print("per-target repair (Serial buried -> BMC clean): "
          + "; ".join(
              f"{k}: {v['n_targets_bmc_clean']}/{v['n_targets_serial_buried']} of {v['n_targets_paired']} paired"
              for k, v in summary["burial"]["per_target_repair"].items()))

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

    print("\n--- per-target fixed-ASF mean +/- sd (reps) ---")
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
