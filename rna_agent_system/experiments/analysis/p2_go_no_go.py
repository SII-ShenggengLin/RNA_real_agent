#!/usr/bin/env python3
"""Pilot P2 go/no-go analysis (2026-08-03): ranking fidelity of the
RhoFold -> ProteinX -> EGARPS scoring chain on the known-aptamer calibration set.

Pre-registered in experiments/run_aptamer_calibration.py docstring:
  - Thrombin series (role=binder, target=Thrombin, kd_nm present, n=4):
    Spearman rho between egarps_native_probability and -log10(Kd). Report rho
    only (n too small for a meaningful p-value).
  - Pooled binder-vs-negative AUROC across all targets (bootstrap 95% CI).
  - GO: rho >= 0.6 AND AUROC > 0.8 -> objective is rank-faithful, Fig-4
    optimization claims stand as-is.
  - NO-GO: per-target calibration gating; optimization claims restricted to
    relative (same-target, same-campaign) comparisons; calibration result
    reported as a method boundary finding.

Same-job dedupe: latest record per id wins.

Usage (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/p2_go_no_go.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import auroc, bootstrap_auroc_ci  # noqa: E402

INPUT = RESULTS / "p2_aptamer_calibration.jsonl"
SUMMARY_OUT = RESULTS / "p2_aptamer_calibration_summary.json"
EXPECTED_N = 15
RHO_THRESHOLD = 0.6
AUROC_THRESHOLD = 0.8


def load_records() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for line in INPUT.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("success"):
            continue
        key = r["id"]
        if key not in latest or r.get("timestamp", "") >= latest[key].get("timestamp", ""):
            latest[key] = r
    return latest


def main() -> int:
    records = load_records()
    n_success = len(records)

    def np_score(r: dict) -> float:
        return r["raw"]["egarps_native_probability"]

    # Thrombin series: binders with a measured Kd gradient.
    thrombin = [r for r in records.values()
                if r.get("role") == "binder" and r.get("target") == "Thrombin"
                and r.get("kd_nm") is not None]
    thrombin.sort(key=lambda r: r["kd_nm"])
    rho = None
    thrombin_points = []
    if thrombin:
        xs = [np_score(r) for r in thrombin]
        ys = [-math.log10(r["kd_nm"]) for r in thrombin]
        rho = float(stats.spearmanr(xs, ys).statistic) if len(thrombin) >= 2 else None
        thrombin_points = [
            {"id": r["id"], "kd_nm": r["kd_nm"], "native_probability": np_score(r)}
            for r in thrombin
        ]

    # Pooled binder-vs-negative AUROC.
    pos = [np_score(r) for r in records.values() if r.get("role") == "binder"]
    neg = [np_score(r) for r in records.values() if r.get("role") == "negative"]
    auc, auc_lo, auc_hi = bootstrap_auroc_ci(pos, neg) if pos and neg else (float("nan"),) * 3

    if n_success < EXPECTED_N or rho is None:
        verdict = "INCOMPLETE"
    elif rho >= RHO_THRESHOLD and auc > AUROC_THRESHOLD:
        verdict = "GO"
    else:
        verdict = "NO-GO"

    summary = {
        "pilot": "P2_aptamer_calibration",
        "date": "2026-08-03",
        "n_success": n_success,
        "expected_n": EXPECTED_N,
        "thrombin_series": {
            "n": len(thrombin_points),
            "points": thrombin_points,
            "spearman_rho_native_probability_vs_neglogKd": rho,
            "note": "n=4, rho reported without p-value per pre-registration",
        },
        "binder_vs_negative": {
            "n_binders": len(pos),
            "n_negatives": len(neg),
            "auroc": auc,
            "auroc_ci95": [auc_lo, auc_hi],
        },
        "thresholds": {"rho": RHO_THRESHOLD, "auroc": AUROC_THRESHOLD},
        "verdict": verdict,
        "verdict_meaning": (
            "GO: objective is rank-faithful; Fig-4 optimization claims stand as-is"
            if verdict == "GO" else
            "NO-GO: add per-target calibration gating; optimization claims restricted to "
            "relative same-target comparisons; calibration reported as method boundary finding"
            if verdict == "NO-GO" else
            "INCOMPLETE: rerun driver with --resume"
        ),
        "records": {k: {"target": v["target"], "role": v["role"],
                        "kd_nm": v.get("kd_nm"),
                        "native_probability": np_score(v),
                        "proteinx_ipTM": v["raw"].get("proteinx_ipTM"),
                        "rhofold_mean_plddt": v["raw"].get("rhofold_mean_plddt")}
                    for k, v in sorted(records.items())},
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({
        "n_success": n_success,
        "thrombin_n": len(thrombin_points),
        "spearman_rho": rho,
        "auroc": auc,
        "auroc_ci95": [auc_lo, auc_hi],
        "n_binders": len(pos),
        "n_negatives": len(neg),
        "verdict": verdict,
    }, indent=2))
    print(f"summary -> {SUMMARY_OUT}")
    return 0 if verdict != "INCOMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
