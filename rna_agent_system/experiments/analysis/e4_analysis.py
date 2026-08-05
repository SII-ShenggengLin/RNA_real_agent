#!/usr/bin/env python3
"""E4 full-matrix analysis: dual-endpoint verdict document.

Reads the two full-matrix shard JSONLs (``e4_full_shard_a.jsonl``,
``e4_full_shard_b.jsonl``; ``--runs`` accepts comma-separated paths) and
writes the pre-registered verdict
``experiments/results/e4_full_summary.json``: pipeline integrity criteria
(c1 completion with only acceptable failures, c3 eval-count recount with 0
deviation, c4 budget-matched cell counts, c5 resume idempotency, c6 field
completeness) plus the two pre-registered full-matrix endpoints and the
GO/NO-GO decision (ANY endpoint passing → GO).

Pre-registration: ``experiments/run_e4_learning_curve.py`` docstring
(2026-08-05 full-matrix amendment). A task may appear multiple times in a
JSONL after a resumed run; the LATEST record per (seed_group, arm, target_id)
is used (``_latest_per_key``).

Endpoints (implementation of the pre-registered dual endpoints):
    Efficiency: per seed group per arm, numpy univariate regression of
    truncated best-of-pool ASF distance (y) vs cumulative eval_count (x,
    summed over successful campaigns in campaign order); memory-arm slopes
    tested vs 0 (one-sample t, one-sided less, p < 0.05) AND cumulative
    budget saving 1 - sum(mem)/sum(nomem) over paired cells >= 25%.
    Design gain: per valid cell, the budget-matched truncated pool's
    best-of-pool candidate scored on the 4 pre-registered VALIDATED metrics
    (cds_cai, full_length_mfe, junction mfe/nt mean, utr5_predicted_mrl;
    ASF and unprofiled oracles banned); per metric paired Wilcoxon with
    BH-FDR across metrics and Cliff's delta, metric passes iff
    q < 0.05 AND |delta| >= 0.3 in the favourable direction; endpoint passes
    iff >= 1 metric passes.

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/e4_analysis.py \
        [--runs experiments/results/e4_full_shard_a.jsonl,experiments/results/e4_full_shard_b.jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

from run_e4_learning_curve import (  # noqa: E402
    ARMS,
    SEED_GROUPS,
    done_key,
    eval_count,
    expected_matrix,
    is_regenerated,
    surrogate_temporal_order,
    truncate_to_budget,
)
from analysis.stats_utils import bh_fdr, cliffs_delta, wilcoxon_paired  # noqa: E402

DEFAULT_RUNS = ",".join([
    str(PROJECT_ROOT / "experiments" / "results" / "e4_full_shard_a.jsonl"),
    str(PROJECT_ROOT / "experiments" / "results" / "e4_full_shard_b.jsonl"),
])
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "e4_full_summary.json"

# Pre-registered endpoint thresholds (HANDOFF 2026-08-05 §2.4; REDESIGN §3 E4).
SIGNIFICANCE_ALPHA = 0.05
CLIFFS_DELTA_THRESHOLD = 0.3
BUDGET_SAVING_THRESHOLD = 0.25

# Pre-registered VALIDATED metrics of the design-gain endpoint.
# direction: "higher"/"lower" = which way is better (memory must beat nomem).
VALIDATED_METRICS = [
    {"key": "cds_cai", "direction": "higher", "label": "CDS CAI"},
    {"key": "full_length_mfe", "direction": "lower", "label": "full-length MFE"},
    {"key": "junction_mfe_per_nt", "direction": "lower",
     "label": "junction mfe/nt (mean of 5'UTR-CDS and CDS-3'UTR)"},
    {"key": "utr5_predicted_mrl", "direction": "higher",
     "label": "5'UTR predicted MRL (GemORNA)"},
]

# Fields the verdict document must contain (criterion ⑥).
REQUIRED_SUMMARY_KEYS = [
    "preregistration",
    "runs",
    "matrix",
    "pass_criteria",
    "campaigns",
    "cells",
    "descriptive",
    "endpoints",
    "go_no_go",
]


# ------------------------------------------------------------------ endpoints


def _slopes_by_group_arm(cells: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """Per seed group per arm: slope of truncated best-of-pool ASF vs
    cumulative eval_count (numpy univariate regression).

    x = cumulative eval_count over successful campaigns in campaign order;
    y = truncated best-of-pool ASF distance of that campaign (lower = better).
    Campaigns without a traceable best ASF (failed arms) are skipped.
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for group in SEED_GROUPS:
        out[group] = {}
        for arm in ARMS:
            pts = sorted(
                (c for c in cells
                 if c["seed_group"] == group
                 and c["eval_counts"].get(arm) is not None
                 and c["best_asf_after_truncation"].get(arm) is not None),
                key=lambda c: c["campaign_index"],
            )
            if len(pts) < 2:
                out[group][arm] = {"slope": float("nan"), "r2": float("nan"), "n": len(pts)}
                continue
            xs = np.cumsum([float(c["eval_counts"][arm]) for c in pts])
            ys = np.asarray([float(c["best_asf_after_truncation"][arm]) for c in pts])
            slope, intercept = np.polyfit(xs, ys, 1)
            yhat = slope * xs + intercept
            ss_res = float(np.sum((ys - yhat) ** 2))
            ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
            out[group][arm] = {"slope": float(slope), "r2": r2, "n": len(pts)}
    return out


def _budget_savings(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """1 - sum(memory eval_count) / sum(nomem eval_count) over paired cells
    (both arms succeeded); pre-registered 20-target cumulative saving."""
    mem_sum = nomem_sum = 0.0
    n_pairs = 0
    for c in cells:
        ec = c.get("eval_counts") or {}
        if ec.get("memory") is not None and ec.get("nomem") is not None:
            mem_sum += float(ec["memory"])
            nomem_sum += float(ec["nomem"])
            n_pairs += 1
    saving = (1.0 - mem_sum / nomem_sum) if nomem_sum > 0 else float("nan")
    return {
        "memory_total": mem_sum,
        "nomem_total": nomem_sum,
        "saving_fraction": saving,
        "n_paired_cells": n_pairs,
        "pass": bool(saving >= BUDGET_SAVING_THRESHOLD),
    }


def regression_slope_endpoint(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Efficiency endpoint: memory-arm slope significantly negative AND
    cumulative budget saving >= 25%."""
    slopes = _slopes_by_group_arm(cells)
    mem = [slopes[g]["memory"]["slope"] for g in SEED_GROUPS
           if not np.isnan(slopes[g]["memory"]["slope"])]
    nom = [slopes[g]["nomem"]["slope"] for g in SEED_GROUPS
           if not np.isnan(slopes[g]["nomem"]["slope"])]
    diff = [slopes[g]["memory"]["slope"] - slopes[g]["nomem"]["slope"]
            for g in SEED_GROUPS
            if not np.isnan(slopes[g]["memory"]["slope"])
            and not np.isnan(slopes[g]["nomem"]["slope"])]

    if len(mem) >= 2:
        t_mem, p_less = stats.ttest_1samp(mem, 0.0, alternative="less")
    else:
        t_mem = p_less = float("nan")
    if len(diff) >= 2:
        t_diff, p_diff = stats.ttest_1samp(diff, 0.0, alternative="less")
    else:
        t_diff = p_diff = float("nan")
    saving = _budget_savings(cells)

    slope_negative = bool(p_less < SIGNIFICANCE_ALPHA and all(s < 0 for s in mem))
    return {
        "slopes_by_group": slopes,
        "memory_slopes": mem,
        "nomem_slopes": nom,
        "slope_significantly_negative": slope_negative,
        "memory_slope_t": {"statistic": float(t_mem), "p_one_sided_less": float(p_less),
                           "n_groups": len(mem)},
        "paired_contrast_memory_minus_nomem": {
            "differences": diff, "statistic": float(t_diff), "p_one_sided_less": float(p_diff)},
        "cumulative_budget_saving": saving,
        "pass": bool(slope_negative and saving["pass"]),
    }


def wilcoxon_quality_endpoint(cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Design-gain endpoint: per VALIDATED metric paired Wilcoxon (BH-FDR
    across metrics) + Cliff's delta; passes iff >= 1 metric has q < 0.05 and
    |delta| >= 0.3 in the favourable (memory-better) direction."""
    results: list[dict[str, Any]] = []
    for metric in VALIDATED_METRICS:
        ms, ns = [], []
        for c in cells:
            if not c.get("valid"):
                continue
            bm = (c.get("best_validated_after_truncation") or {}).get("memory") or {}
            bn = (c.get("best_validated_after_truncation") or {}).get("nomem") or {}
            mv, nv = bm.get(metric["key"]), bn.get(metric["key"])
            if mv is None or nv is None:
                continue
            ms.append(float(mv))
            ns.append(float(nv))
        delta = cliffs_delta(ms, ns) if ms else float("nan")
        p = wilcoxon_paired(ms, ns) if ms else float("nan")
        favourable = (
            (delta >= CLIFFS_DELTA_THRESHOLD) if metric["direction"] == "higher"
            else (delta <= -CLIFFS_DELTA_THRESHOLD)
        ) if ms else False
        results.append({**metric, "n_pairs": len(ms), "p": p, "cliffs_delta": delta,
                        "favourable_direction": favourable})
    qs = bh_fdr([r["p"] for r in results])
    for r, q in zip(results, qs):
        r["q_bh"] = q
        r["pass"] = bool(q < SIGNIFICANCE_ALPHA and r["favourable_direction"])
    return {"metrics": results, "pass": any(r["pass"] for r in results)}


# -------------------------------------------------------------------- helpers


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _latest_per_key(records: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """LATEST record per done-key (a task may recur after a resumed run)."""
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for rec in records:
        if all(k in rec for k in ("seed_group", "arm", "target_id")):
            latest[done_key(rec)] = rec
    return latest


def _session_candidates(rec: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Recount leg: candidates from the persisted session artifact."""
    session_id = rec.get("session_id")
    if not session_id:
        return None
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / str(session_id)
    results_files = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not results_files:
        return None
    try:
        results = json.loads(results_files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return results.get("candidates")


def _recount_eval_count(candidates: list[dict[str, Any]]) -> int:
    """Independent reduction from the raw session artifact."""
    ordered = surrogate_temporal_order(candidates)
    n_initial = sum(1 for c in ordered if not is_regenerated(c))
    n_regenerated = sum(1 for c in ordered if is_regenerated(c))
    assert eval_count(candidates) == n_initial + n_regenerated
    return eval_count(candidates)


# --------------------------------------------------------------------- cells


def _cell_verdict(
    group: str,
    target_id: str,
    campaign_index: int,
    mem: dict[str, Any] | None,
    nomem: dict[str, Any] | None,
) -> dict[str, Any]:
    """Budget-matching truncation for one (seed_group × target) cell.

    Also records the truncated pool's best-of-pool candidate's pre-registered
    VALIDATED metrics per arm (design-gain endpoint input).
    """
    cell: dict[str, Any] = {
        "seed_group": group,
        "target_id": target_id,
        "campaign_index": campaign_index,
        "valid": False,
        "invalid_reason": None,
        "eval_counts": {},
        "truncated_counts": {},
        "counts_equal_after_truncation": None,
        "budget": None,
        "best_asf_after_truncation": {},
        "best_validated_after_truncation": {},
    }
    arms = {"memory": mem, "nomem": nomem}
    for arm, rec in arms.items():
        if rec is None:
            cell["invalid_reason"] = f"{arm}_arm_missing"
        elif not rec.get("success"):
            reason = f"{arm}_arm_failed"
            if rec.get("acceptable_failure"):
                reason += "_acceptable"
            cell["invalid_reason"] = reason
    if cell["invalid_reason"]:
        return cell

    pools: dict[str, list[dict[str, Any]]] = {}
    for arm, rec in arms.items():
        cell["eval_counts"][arm] = rec.get("eval_count")
        # Rehydrate the trimmed candidate projection stored by the driver.
        pools[arm] = [
            {
                "id": c.get("id"),
                "scores": {
                    "asf_distance": c.get("asf_distance"),
                    "cds_cai": c.get("cds_cai"),
                    "full_length_mfe": c.get("full_length_mfe"),
                    "junction_mfe_per_nt": c.get("junction_mfe_per_nt"),
                    "utr5_predicted_mrl": c.get("utr5_predicted_mrl"),
                },
                "metadata": {"bmc_regenerated": bool(c.get("bmc_regenerated"))},
            }
            for c in (rec.get("candidate_index") or [])
        ]
    if not all(pools[a] for a in arms):
        cell["invalid_reason"] = "missing_candidate_index"
        return cell

    budget = min(len(pools[a]) for a in arms)
    cell["budget"] = budget
    for arm in arms:
        truncated = truncate_to_budget(pools[arm], budget)
        cell["truncated_counts"][arm] = len(truncated)
        best = min(
            ((c["scores"]["asf_distance"]) for c in truncated
             if c["scores"]["asf_distance"] is not None),
            default=None,
        )
        cell["best_asf_after_truncation"][arm] = best
        # Best-of-pool candidate (min ASF) of the truncated pool.
        best_cand = min(
            (c for c in truncated if c["scores"]["asf_distance"] is not None),
            key=lambda c: c["scores"]["asf_distance"],
            default=None,
        )
        cell["best_validated_after_truncation"][arm] = {
            m["key"]: (best_cand["scores"][m["key"]] if best_cand else None)
            for m in VALIDATED_METRICS
        }
    cell["counts_equal_after_truncation"] = (
        len({cell["truncated_counts"][a] for a in arms}) == 1
    )
    cell["valid"] = bool(cell["counts_equal_after_truncation"])
    if not cell["valid"]:
        cell["invalid_reason"] = "counts_unequal_after_truncation"
    return cell


# ---------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", default=DEFAULT_RUNS,
                        help="comma-separated shard JSONL paths "
                             "(default: both e4_full_shard_{a,b}.jsonl)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    run_paths = []
    for chunk in str(args.runs).split(","):
        p = Path(chunk.strip())
        if not p.exists():
            print(f"warning: runs file not found: {p}", file=sys.stderr)
            continue
        run_paths.append(p)
        records.extend(_load_jsonl(p))
    if not run_paths:
        print(f"error: no runs file found under --runs={args.runs}", file=sys.stderr)
        return 1
    latest = _latest_per_key(records)
    matrix = expected_matrix()
    idx_map = {(c["seed_group"], c["target_id"]): c["campaign_index"] for c in matrix}

    # Per-campaign descriptive rows + integrity-criterion inputs.
    campaigns: list[dict[str, Any]] = []
    n_complete = n_acceptable_fail = n_unexpected_fail = n_missing = 0
    reduction_mismatches: list[dict[str, Any]] = []
    injection_stats: list[dict[str, Any]] = []
    for cell in matrix:
        key = (cell["seed_group"], cell["arm"], cell["target_id"])
        rec = latest.get(key)
        if rec is None:
            n_missing += 1
            campaigns.append({**cell, "status": "missing"})
            continue
        row: dict[str, Any] = {
            **cell,
            "status": "success" if rec.get("success") else "failed",
            "error": rec.get("error"),
            "acceptable_failure": rec.get("acceptable_failure", False),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "eval_count": rec.get("eval_count"),
            "bmc_rounds_executed": rec.get("bmc_rounds_executed"),
            "final_lambda": rec.get("final_lambda"),
            "utr_family": rec.get("utr_family"),
            "knobs_fired": (rec.get("memory_overrides") or {}).get("fired"),
            "similar_campaign_ids": rec.get("similar_campaign_ids"),
        }
        if rec.get("success"):
            n_complete += 1
            # Criterion ③: independent recount from the session artifact.
            session_candidates = _session_candidates(rec)
            if session_candidates is None:
                reduction_mismatches.append(
                    {"task_id": rec.get("task_id"), "reason": "session_artifact_unavailable"}
                )
            else:
                recounted = _recount_eval_count(session_candidates)
                if recounted != rec.get("eval_count"):
                    reduction_mismatches.append({
                        "task_id": rec.get("task_id"),
                        "driver_eval_count": rec.get("eval_count"),
                        "session_recount": recounted,
                    })
            # Descriptive injection statistics (no pass criterion at full matrix).
            if cell["arm"] == "memory" and cell["campaign_index"] > 1:
                fired = (rec.get("memory_overrides") or {}).get("fired") or []
                injection_stats.append({
                    "task_id": rec.get("task_id"),
                    "seed_group": cell["seed_group"],
                    "campaign_index": cell["campaign_index"],
                    "knobs_fired": fired,
                    "injection_fired": len(fired) > 0,
                })
        elif rec.get("acceptable_failure"):
            n_acceptable_fail += 1
        else:
            n_unexpected_fail += 1
        campaigns.append(row)

    # Criterion ④: cells.
    cells = [
        _cell_verdict(
            group,
            target_id,
            idx_map[(group, target_id)],
            latest.get((group, "memory", target_id)),
            latest.get((group, "nomem", target_id)),
        )
        for group in SEED_GROUPS
        for target_id in dict.fromkeys(c["target_id"] for c in matrix)
    ]
    n_cells_valid = sum(1 for c in cells if c["valid"])
    cells_bad = [
        c for c in cells
        if not c["valid"]
        and not (c["invalid_reason"] or "").endswith("_acceptable")
    ]

    # Criterion ⑤ (runtime leg): no duplicate completed done-keys.
    completed_keys = [done_key(r) for r in records
                      if r.get("success") and all(k in r for k in ("seed_group", "arm", "target_id"))]
    n_duplicate_done_keys = len(completed_keys) - len(set(completed_keys))

    pass_criteria = {
        "c1_all_campaigns_completed": {
            "pass": n_missing == 0 and n_unexpected_fail == 0,
            "n_success": n_complete,
            "n_acceptable_failure": n_acceptable_fail,
            "n_unexpected_failure": n_unexpected_fail,
            "n_missing": n_missing,
            "expected_campaigns": len(matrix),
        },
        "c3_eval_reduction_zero_deviation": {
            "pass": len(reduction_mismatches) == 0,
            "mismatches": reduction_mismatches,
        },
        "c4_cells_budget_matched": {
            "pass": n_cells_valid + sum(1 for c in cells
                                        if (c["invalid_reason"] or "").endswith("_acceptable")) == len(cells),
            "n_cells": len(cells),
            "n_valid": n_cells_valid,
            "n_invalid_unexpected": len(cells_bad),
        },
        "c5_resume_idempotent": {
            "pass": n_duplicate_done_keys == 0,
            "n_duplicate_done_keys": n_duplicate_done_keys,
            "unit_test": "tests/test_e4_pilot.py::TestResumeDoneKey",
        },
    }

    endpoints = {
        "efficiency": regression_slope_endpoint(cells),
        "design_gain": wilcoxon_quality_endpoint(cells),
    }
    efficiency_pass = bool(endpoints["efficiency"]["pass"])
    design_gain_pass = bool(endpoints["design_gain"]["pass"])

    summary: dict[str, Any] = {
        "preregistration": "experiments/run_e4_learning_curve.py docstring "
                           "(E4 full matrix, 2026-08-05 amendment)",
        "runs": [str(p.relative_to(PROJECT_ROOT)) if p.is_relative_to(PROJECT_ROOT) else str(p)
                 for p in run_paths],
        "matrix": {
            "targets": sorted({c["target_id"] for c in matrix}),
            "arms": list(ARMS),
            "seed_groups": SEED_GROUPS,
            "n_campaigns": len(matrix),
        },
        "pass_criteria": pass_criteria,
        "campaigns": campaigns,
        "cells": cells,
        "descriptive": {
            "injection": {
                "n_memory_campaigns_checked": len(injection_stats),
                "n_with_override": sum(1 for r in injection_stats if r["injection_fired"]),
                "detail": injection_stats,
            },
            "per_campaign_eval_counts": {
                r["task_id"] if "task_id" in r else f"{r['seed_group']}/{r['arm']}/c{r['campaign_index']}":
                r.get("eval_count") for r in campaigns
            },
            "wall_clock_seconds_total": sum(
                r.get("elapsed_seconds") or 0.0 for r in campaigns
            ),
            "wall_clock_seconds_by_arm": {
                arm: sum(r.get("elapsed_seconds") or 0.0
                         for r in campaigns if r.get("arm") == arm)
                for arm in ARMS
            },
        },
        "endpoints": endpoints,
        "go_no_go": {
            "efficiency_pass": efficiency_pass,
            "design_gain_pass": design_gain_pass,
            "go": bool(efficiency_pass or design_gain_pass),
            "rule": "ANY endpoint passing -> GO (REDESIGN §3 E4; HANDOFF 2026-08-05 §2.4)",
            "thresholds": {
                "slope_significant_negative": "one-sample t, one-sided less, p < 0.05",
                "budget_saving": f">= {BUDGET_SAVING_THRESHOLD:.0%} cumulative",
                "wilcoxon": f"q (BH-FDR across {len(VALIDATED_METRICS)} metrics) < {SIGNIFICANCE_ALPHA}",
                "cliffs_delta": f"|delta| >= {CLIFFS_DELTA_THRESHOLD} in favourable direction",
            },
        },
    }
    # Criterion ⑥: verdict completeness.
    missing_keys = [k for k in REQUIRED_SUMMARY_KEYS if k not in summary]
    pass_criteria["c6_verdict_fields_complete"] = {
        "pass": not missing_keys,
        "missing_keys": missing_keys,
        "required_keys": REQUIRED_SUMMARY_KEYS,
    }
    summary["overall_pass"] = all(c["pass"] for c in pass_criteria.values())

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str),
                           encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in pass_criteria.items()}, indent=2))
    print(f"endpoints: efficiency={efficiency_pass} design_gain={design_gain_pass}")
    print(f"go_no_go: {'GO' if summary['go_no_go']['go'] else 'NO-GO'}")
    print(f"overall_pass={summary['overall_pass']}  summary -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
