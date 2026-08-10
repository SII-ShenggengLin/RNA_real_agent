#!/usr/bin/env python3
"""Pilot P3 go/no-go analysis (2026-08-03): guided (bmc_x1) vs unguided_2pass.

Pre-registered in experiments/run_p3_guided_vs_unguided.py docstring:
  - Pair per (target, seed_idx) cell: egarps_component best-of-pool of
    guided bmc_x1 (fig4_type2_shard_{a,b}.jsonl, bmc_max_rounds=1) vs
    unguided_2pass (p3_guided_vs_unguided.jsonl). Both arms use identical
    two-pass mechanics and total budget 16; only the diagnosis content
    differs.
  - GO: Cliff's delta >= 0.3 in favour of guided across the 12 cells.
  - NO-GO: delta < 0.3 -> diagnosis content unsupported; BMC's defensible
    value = adaptive budget allocation + resampling mechanics.
  - Secondary: budget spent per arm (guided may stop at pool 8 on round-0
    convergence; unguided always 16).

CAVEAT (pre-registered): the egarps objective failed P2 calibration
(rho=0.40, AUROC=0.356); this verdict is about the mechanism under the
current objective.

Usage (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/p3_go_no_go.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import cliffs_delta, median_iqr, wilcoxon_paired  # noqa: E402

PILOT_TARGETS = ["BSA", "Lysozyme", "Thrombin", "VEGF"]
SEED_IDXS = [0, 1, 2]
GO_THRESHOLD = 0.3
EXPECTED_CELLS = 12
SUMMARY_OUT = RESULTS / "p3_guided_vs_unguided_summary.json"


def _latest(records: list[dict]) -> dict:
    return max(records, key=lambda r: r.get("timestamp", ""))


def load_guided() -> dict[tuple, dict]:
    cells: dict[tuple, list[dict]] = {}
    for name in ("fig4_type2_shard_a.jsonl", "fig4_type2_shard_b.jsonl"):
        path = RESULTS / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("success") or r.get("bmc_max_rounds") != 1:
                continue
            if r["target_id"] not in PILOT_TARGETS or r["seed_idx"] not in SEED_IDXS:
                continue
            cells.setdefault((r["target_id"], r["seed_idx"]), []).append(r)
    return {k: _latest(v) for k, v in cells.items()}


def load_unguided() -> dict[tuple, dict]:
    cells: dict[tuple, list[dict]] = {}
    path = RESULTS / "p3_guided_vs_unguided.jsonl"
    if not path.exists():
        return {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("success") or r.get("condition") != "unguided_2pass":
            continue
        cells.setdefault((r["target_id"], r["seed_idx"]), []).append(r)
    return {k: _latest(v) for k, v in cells.items()}


def main() -> int:
    guided = load_guided()
    unguided = load_unguided()
    cells = []
    missing = []
    for target in PILOT_TARGETS:
        for seed_idx in SEED_IDXS:
            key = (target, seed_idx)
            g, u = guided.get(key), unguided.get(key)
            if g is None or u is None:
                missing.append({"target_id": target, "seed_idx": seed_idx,
                                "has_guided": g is not None, "has_unguided": u is not None})
                continue
            cells.append({
                "target_id": target,
                "seed_idx": seed_idx,
                "guided_egarps_best": g["best"]["egarps_component"],
                "unguided_egarps_best": u["best"]["egarps_component"],
                "guided_pool": g.get("candidate_count"),
                "unguided_pool": u.get("candidate_count"),
                "guided_rounds_executed": g.get("bmc_rounds_executed"),
            })

    x = [c["guided_egarps_best"] for c in cells]
    y = [c["unguided_egarps_best"] for c in cells]
    delta = cliffs_delta(x, y) if cells else None
    wilcoxon_p = wilcoxon_paired(x, y) if len(cells) >= 5 else None
    wins = sum(1 for a, b in zip(x, y) if a > b)

    # Secondary: budget spent (guided can stop at 8 when round-0 converges).
    guided_budgets = [c["guided_pool"] for c in cells]
    unguided_budgets = [c["unguided_pool"] for c in cells]

    if delta is None or missing:
        verdict = "INCOMPLETE"
    elif delta >= GO_THRESHOLD:
        verdict = "GO"
    else:
        verdict = "NO-GO"

    summary = {
        "pilot": "P3_guided_vs_unguided",
        "date": "2026-08-03",
        "metric": "egarps_component best-of-pool",
        "comparison": "guided bmc_x1 vs unguided_2pass (identical mechanics, budget 16; "
                      "only diagnosis content differs)",
        "n_cells": len(cells),
        "missing_cells": missing,
        "cells": cells,
        "cliffs_delta": delta,
        "go_threshold": GO_THRESHOLD,
        "wilcoxon_paired_p": wilcoxon_p,
        "guided_median_iqr": median_iqr(x) if x else None,
        "unguided_median_iqr": median_iqr(y) if y else None,
        "guided_wins": wins,
        "guided_budgets": guided_budgets,
        "unguided_budgets": unguided_budgets,
        "verdict": verdict,
        "verdict_meaning": (
            "GO: diagnosis content carries measurable value beyond budget and mechanics"
            if verdict == "GO" else
            "NO-GO: diagnosis content unsupported at pilot scale; BMC value reduces to "
            "adaptive budget allocation + resampling mechanics"
            if verdict == "NO-GO" else
            "INCOMPLETE: cells missing, rerun driver with --resume"
        ),
        "caveat": "egarps objective failed P2 calibration (rho=0.40, AUROC=0.356); "
                  "verdict is about the mechanism under the current objective",
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in
                      ("n_cells", "cliffs_delta", "wilcoxon_paired_p",
                       "guided_median_iqr", "unguided_median_iqr",
                       "guided_wins", "guided_budgets", "unguided_budgets",
                       "verdict")}, indent=2))
    if missing:
        print("MISSING CELLS:", json.dumps(missing))
    print(f"summary -> {SUMMARY_OUT}")
    return 0 if verdict != "INCOMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
