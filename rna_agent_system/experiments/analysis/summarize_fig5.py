#!/usr/bin/env python3
"""Summarize Fig 5 mechanism-ablation runs -> experiments/results/fig5_summary.json.

Panels (MANUSCRIPT §7; driver experiments/run_bmc_mechanism_ablations.py):
- b: source-aware vs pool-average feedback (Type-II, 9 targets x 2 modes x 3
  seed sets; Ferritin cells are a confirmed ODesign boundary, see driver NOTE).
- c: utopian vs fixed-threshold reference point (same 9 targets).
- d: bounded adjustment under an extreme start (lambda_value=18, 3 targets x
  BMC x1, 3 reps): lambda trajectories through the [0, 20] clamp (descriptive).
- e_type1: Type-I negative control (3 small proteins, utr_mode=short,
  serial vs BMC x1, 3 reps) — expect no significant difference.
- e_type2: Type-II negative control (explicit known hotspots; Thrombin cells
  only — SARS-CoV-2_Nucleocapsid e2 cells are a confirmed boundary, see
  driver NOTE) — expect no significant difference.

Conventions (§13): paired Wilcoxon + Cliff's delta, ONE BH-FDR family across
all tests. Cross-arm ASF uses a fixed reference per target (the per-run
utopian `asf_distance` is NOT comparable across arms — see
agent_core/workflows/multi_objective.py ANALYSIS CAVEAT): per target the
`pool_objectives` of both arms are merged, each objective is min-max
normalized with the merged bounds, and the shared reference is the
per-dimension best of the merged pool ('utopian-of-pool'), ASF recomputed
with uniform weights and rho=1e-3.

Usage (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/summarize_fig5.py
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
DEFAULT_INPUT = RESULTS / "fig5_ablations.jsonl"
DEFAULT_OUTPUT = RESULTS / "fig5_summary.json"

# Type-II objectives (all maximized).
OBJECTIVES_T2 = ["egarps_component", "rhofold_component", "iptm_component"]
# Type-I panel-e1 comparison metrics (descriptive; see E1_METHOD caveat).
METRICS_E1 = ["asf_distance", "cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"]

ASF_METHOD = (
    "Fixed-reference ASF recomputation (panels b/c): per target, all "
    "`pool_objectives` points of BOTH arms are pooled; each objective "
    "dimension (egarps/rhofold/iptm_component; all maximized) is min-max "
    "normalized with bounds from that merged pool. The shared reference "
    "point is the per-dimension best over the merged pool "
    "('utopian-of-pool'), normalized with the same bounds. ASF distances of "
    "every run's best candidate are recomputed against this fixed reference "
    "with uniform weights and rho=1e-3 via "
    "agent_core.workflows.multi_objective.achievement_scalarizing_function. "
    "The stored asf_distance uses a per-run utopian reference and is NOT "
    "comparable across arms, so it is never used for cross-arm tests."
)

E1_METHOD = (
    "Panel e_type1 is a NEGATIVE control (utr_mode=short removes the "
    "junction-coupling conflict the BMC is designed to resolve), so the "
    "expectation is 'no significant difference'. Raw best-candidate "
    "components (cds_component / utr5_mrl / utr3_stability / full_mfe_score) "
    "are compared per (target, rep) pair; the stored utopian asf_distance is "
    "shown descriptively only (per-run reference, see multi_objective.py "
    "ANALYSIS CAVEAT) — inference rests on the components."
)

BOUNDARY_NOTE = (
    "Confirmed boundaries (deterministic, not retried; see driver NOTEs): "
    "(1) Ferritin (1FHA) panels b/c — ODesign produced zero sequences in all "
    "Fig-4 cells + 3 retries and in all six fig5b cells "
    "(`no_sequences_extracted_from_odesign_output`); (2) "
    "SARS-CoV-2_Nucleocapsid (6M3M) panel e_type2 — the explicit "
    "hotspot_residues A/44-48 are all missing from the chain-A structure "
    "(fig4kav hotspot_recovery: known_missing_in_structure), ODesign found "
    "no valid target region in all 6 cells."
)


# --------------------------------------------------------------------------- io


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def dedupe_latest(records: list[dict]) -> dict[str, dict]:
    """Keep the latest record per task_id (timestamp wins; ties keep file order)."""
    latest: dict[str, dict] = {}
    for r in records:
        tid = r.get("task_id")
        prev = latest.get(tid)
        if prev is None or str(r.get("timestamp") or "") >= str(prev.get("timestamp") or ""):
            latest[tid] = r
    return latest


def get_best(record: dict, key: str):
    best = record.get("best") or {}
    value = best.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def pool_vectors(record: dict) -> list[dict[str, float]]:
    """Objective vectors from `pool_objectives` (rows with all dims present)."""
    vecs: list[dict[str, float]] = []
    for row in record.get("pool_objectives") or []:
        if not isinstance(row, dict):
            continue
        try:
            vecs.append({k: float(row[k]) for k in OBJECTIVES_T2})
        except (KeyError, TypeError, ValueError):
            continue
    return vecs


# ------------------------------------------------------------------ fixed ASF


def recompute_fixed_asf(records: list[dict], panels: tuple[str, ...]) -> dict[str, float | None]:
    """Best-candidate ASF vs the per-target utopian-of-pool reference.

    Covers panels b and c records (they share the same 9 targets, so bounds
    and references are computed per target over the panel's two arms).
    Returns ``{task_id: asf or None}``.
    """
    by_target: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("success") and r.get("panel") in panels:
            by_target[r["target_id"]].append(r)

    weights = {key: 1.0 / len(OBJECTIVES_T2) for key in OBJECTIVES_T2}
    asf: dict[str, float | None] = {}
    for target, runs in sorted(by_target.items()):
        all_points = [v for r in runs for v in pool_vectors(r)]
        if not all_points:
            for r in runs:
                asf[r["task_id"]] = None
            continue
        bounds = {}
        for key in OBJECTIVES_T2:
            vals = [p[key] for p in all_points]
            bounds[key] = (min(vals), max(vals))
        norm_ref = {
            key: normalize_value(max(p[key] for p in all_points), *bounds[key])
            for key in OBJECTIVES_T2
        }
        for r in runs:
            norm_vec: dict[str, float] = {}
            for key in OBJECTIVES_T2:
                v = get_best(r, key)
                if v is None:
                    norm_vec = {}
                    break
                norm_vec[key] = normalize_value(v, *bounds[key])
            asf[r["task_id"]] = (
                achievement_scalarizing_function(norm_vec, norm_ref, weights, rho=1e-3)
                if norm_vec else None
            )
    return asf


# -------------------------------------------------------------------- stats


def paired_stats(pairs: list[tuple[float, float]], x_name: str, y_name: str) -> dict:
    """Wilcoxon + Cliff's delta for one paired comparison (x vs y)."""
    if not pairs:
        return {"n": 0}
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    deltas = [x - y for x, y in pairs]
    return {
        "n": len(pairs),
        f"median_{y_name}": st.median(ys),
        f"median_{x_name}": st.median(xs),
        f"median_delta_{x_name}_minus_{y_name}": st.median(deltas),
        "wilcoxon_p": wilcoxon_paired(xs, ys),
        "cliffs_delta": cliffs_delta(xs, ys),
    }


def panel_bc_tests(records: list[dict], panel: str, arms: tuple[str, str],
                   asf: dict[str, float | None]) -> dict:
    """Paired tests per (target, seed_idx) for one Type-II panel.

    `arms` = (treatment, control). Metrics: asf_fixed + the three components.
    """
    treatment, control = arms
    cells: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in records:
        if r.get("success") and r.get("panel") == panel:
            cells[(r["target_id"], r.get("seed_idx"))][r["condition"]] = r

    metrics = ["asf_fixed"] + OBJECTIVES_T2
    out: dict[str, dict] = {}
    for metric in metrics:
        pairs: list[tuple[float, float]] = []
        for (_target, _seed), cell in sorted(cells.items()):
            rt, rc = cell.get(treatment), cell.get(control)
            if not rt or not rc:
                continue
            if metric == "asf_fixed":
                vt, vc = asf.get(rt["task_id"]), asf.get(rc["task_id"])
            else:
                vt, vc = get_best(rt, metric), get_best(rc, metric)
            if vt is None or vc is None:
                continue
            pairs.append((vt, vc))
        out[metric] = paired_stats(pairs, treatment, control)
    return out


def panel_e_tests(records: list[dict], panel: str, metrics: list[str]) -> dict:
    """Paired tests per (target, rep/seed_idx) for negative-control panels.

    Compares bmc1 (rounds=1) vs serial (rounds=0).
    """
    cells: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in records:
        if r.get("success") and r.get("panel") == panel:
            rep = r.get("rep", r.get("seed_idx"))
            cells[(r["target_id"], rep)][r["condition"]] = r

    out: dict[str, dict] = {}
    for metric in metrics:
        pairs: list[tuple[float, float]] = []
        for (_target, _rep), cell in sorted(cells.items()):
            rt, rc = cell.get("bmc1"), cell.get("serial")
            if not rt or not rc:
                continue
            vt, vc = get_best(rt, metric), get_best(rc, metric)
            if vt is None or vc is None:
                continue
            pairs.append((vt, vc))
        out[metric] = paired_stats(pairs, "bmc1", "serial")
    return out


# ------------------------------------------------------------------ panel d


def panel_d_summary(records: list[dict]) -> dict:
    """Boundedness demonstration: lambda trajectories under an extreme start."""
    runs = [r for r in records if r.get("success") and r.get("panel") == "d"]
    per_run: list[dict] = []
    all_initial: list[float] = []
    all_final: list[float] = []
    for r in sorted(runs, key=lambda x: x["task_id"]):
        traj = r.get("lambda_trajectory") or []
        entry = {
            "task_id": r["task_id"],
            "target_id": r["target_id"],
            "lambda_trajectory": traj,
            "bmc_rounds_executed": r.get("bmc_rounds_executed"),
            "elapsed_seconds": r.get("elapsed_seconds"),
            "best_asf_distance": get_best(r, "asf_distance"),
            "best_cds_cai": get_best(r, "cds_cai"),
        }
        if traj:
            entry["lambda_initial"] = traj[0]
            entry["lambda_final"] = traj[-1]
            entry["lambda_max_observed"] = max(t for t in traj if t is not None)
            all_initial.append(traj[0])
            all_final.append(traj[-1])
        per_run.append(entry)
    return {
        "n_runs": len(runs),
        "clamp_interval": [0, 20],
        "lambda_initial_unique": sorted(set(all_initial)),
        "lambda_final_median": st.median(all_final) if all_final else None,
        "lambda_final_range": [min(all_final), max(all_final)] if all_final else None,
        "all_trajectories_within_clamp": all(
            t is not None and 0 <= t <= 20
            for r in per_run for t in (r.get("lambda_trajectory") or [])
        ),
        "runs": per_run,
        "note": (
            "Extreme start lambda_value=18 (of the [0,20] clamp interval); "
            "trajectories reconstructed from `_bmc_trace` ParamAdjustments "
            "replayed through the workflow's clamp (driver-side "
            "_reconstruct_lambda_trajectory). Boundedness = adjustments never "
            "leave the clamp interval and pull the extreme start back toward "
            "the sane design region."
        ),
    }


# -------------------------------------------------------------------- misc


def timing_summary(records: list[dict]) -> dict:
    out: dict[str, dict] = {}
    by_panel: dict[str, list[float]] = defaultdict(list)
    for r in records:
        if r.get("success") and r.get("elapsed_seconds") is not None:
            by_panel[r["panel"]].append(float(r["elapsed_seconds"]))
    for panel, vals in sorted(by_panel.items()):
        med, q1, q3 = median_iqr(vals)
        out[panel] = {"n": len(vals), "median_s": med, "iqr_s": [q1, q3]}
    return out


def fmt(v, nd=4):
    if isinstance(v, float) and math.isnan(v):
        return "-"
    return f"{v:.{nd}g}" if isinstance(v, (int, float)) else "-"


# -------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = load_records(args.input)
    latest = dedupe_latest(records)
    jobs = list(latest.values())
    ok_jobs = [r for r in jobs if r.get("success")]
    failed = {k: r for k, r in latest.items() if not r.get("success")}

    boundary = {
        "ferritin_panel_bc": sorted(k for k in failed if "Ferritin" in k),
        "nucleocapsid_e2": sorted(k for k in failed if "Nucleocapsid" in k),
        "note": BOUNDARY_NOTE,
    }
    unexpected_failures = sorted(
        k for k in failed if "Ferritin" not in k and "Nucleocapsid" not in k
    )

    # Panel b/c fixed-reference ASF (shared targets; reference per target).
    asf = recompute_fixed_asf(ok_jobs, panels=("b", "c"))

    tests: dict[str, dict] = {
        "panel_b_source_aware_vs_pool_average": panel_bc_tests(
            ok_jobs, "b", ("source_aware", "pool_average"), asf),
        "panel_c_utopian_vs_fixed_reference": panel_bc_tests(
            ok_jobs, "c", ("utopian", "fixed_reference"), asf),
        "panel_e1_bmc1_vs_serial": panel_e_tests(ok_jobs, "e_type1", METRICS_E1),
        "panel_e2_bmc1_vs_serial": panel_e_tests(ok_jobs, "e_type2", OBJECTIVES_T2),
    }

    # ONE BH-FDR family across every test.
    flat: list[tuple[str, float]] = []
    for section, metrics in tests.items():
        for metric, entry in metrics.items():
            if entry.get("n"):
                flat.append((f"{section}.{metric}", entry["wilcoxon_p"]))
    qs = bh_fdr([p for _, p in flat])
    for (path, _), q in zip(flat, qs):
        section, metric = path.split(".")
        tests[section][metric]["q_bh"] = q

    summary: dict = {
        "generated_by": "experiments/analysis/summarize_fig5.py",
        "input": str(args.input),
        "asf_method": ASF_METHOD,
        "e1_method": E1_METHOD,
        "boundary": boundary,
        "n_records_raw": len(records),
        "n_jobs_unique": len(jobs),
        "n_jobs_success": len(ok_jobs),
        "unexpected_failures": unexpected_failures,
        "panels": {
            "b": {"design": "9 targets x {source_aware, pool_average} x 3 seed sets, BMC x1",
                  "tests": tests["panel_b_source_aware_vs_pool_average"]},
            "c": {"design": "9 targets x {utopian, fixed_reference} x 3 seed sets, BMC x1",
                  "tests": tests["panel_c_utopian_vs_fixed_reference"]},
            "d": {"design": "3 targets x lambda=18 extreme start x 3 reps, BMC x1",
                  "boundedness": panel_d_summary(ok_jobs)},
            "e_type1": {"design": "3 small proteins x {serial, bmc1} x 3 reps, utr_mode=short",
                        "tests": tests["panel_e1_bmc1_vs_serial"]},
            "e_type2": {"design": "explicit known hotspots x {serial, bmc1} x 3 seeds "
                                  "(Thrombin only; Nucleocapsid = boundary)",
                        "tests": tests["panel_e2_bmc1_vs_serial"]},
        },
        "timing": timing_summary(ok_jobs),
    }

    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Console digest.
    print(f"jobs: {len(jobs)} unique, {len(ok_jobs)} success, {len(failed)} failed "
          f"(boundary: {len(boundary['ferritin_panel_bc'])} Ferritin + "
          f"{len(boundary['nucleocapsid_e2'])} Nucleocapsid-e2; "
          f"unexpected: {len(unexpected_failures)})")
    for section, metrics in tests.items():
        print(f"\n[{section}]")
        for metric, entry in metrics.items():
            if not entry.get("n"):
                print(f"  {metric}: n=0")
                continue
                # reachable only when n>0
            keys = [k for k in entry if k.startswith("median_delta")]
            md = entry[keys[0]] if keys else None
            print(f"  {metric}: n={entry['n']} median_delta={fmt(md)} "
                  f"p={fmt(entry['wilcoxon_p'])} q={fmt(entry.get('q_bh'))} "
                  f"cliff={fmt(entry['cliffs_delta'])}")
    d = summary["panels"]["d"]["boundedness"]
    print(f"\n[panel d] n={d['n_runs']} lambda init={d['lambda_initial_unique']} "
          f"final median={fmt(d['lambda_final_median'])} range={d['lambda_final_range']} "
          f"within_clamp={d['all_trajectories_within_clamp']}")
    print(f"\nsummary -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
