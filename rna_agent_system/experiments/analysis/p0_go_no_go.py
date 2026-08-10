#!/usr/bin/env python3
"""Pilot P0 go/no-go analysis (2026-08-03): bmc_x1 vs budget-matched serial_ext16.

Pre-registered in experiments/run_budget_matched_control.py docstring:
  - Pair per (target, seed_idx) cell: egarps_component best-of-pool of
    bmc_x1 (fig4_type2_shard_{a,b}.jsonl, bmc_max_rounds=1) vs serial_ext16
    (fig4_budget_matched.jsonl, condition='serial_ext16').
  - GO: Cliff's delta >= 0.3 in favour of bmc_x1 across the 12 cells.
  - NO-GO: delta ~ 0 -> budget explains the Fig-4 Type-II main effect.

Conventions (HANDOFF_PROMPT.md §5.6): same-job dedupe keeps the latest record;
shard records keyed by (target_id, bmc_max_rounds, seed_idx); budget-matched
records keyed by (target_id, condition, seed_idx).

Usage (from rna_agent_system/):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/analysis/p0_go_no_go.py
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
SUMMARY_OUT = RESULTS / "p0_budget_matched_summary.json"


def _latest(records: list[dict]) -> dict:
    """Same-job dedupe: latest timestamp wins."""
    return max(records, key=lambda r: r.get("timestamp", ""))


def load_bmc_x1() -> dict[tuple, dict]:
    cells: dict[tuple, list[dict]] = {}
    for name in ("fig4_type2_shard_a.jsonl", "fig4_type2_shard_b.jsonl"):
        path = RESULTS / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("success"):
                continue
            if r.get("bmc_max_rounds") != 1:
                continue
            if r["target_id"] not in PILOT_TARGETS or r["seed_idx"] not in SEED_IDXS:
                continue
            cells.setdefault((r["target_id"], r["seed_idx"]), []).append(r)
    return {k: _latest(v) for k, v in cells.items()}


def load_serial_ext16() -> dict[tuple, dict]:
    cells: dict[tuple, list[dict]] = {}
    path = RESULTS / "fig4_budget_matched.jsonl"
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("success"):
            continue
        if r.get("condition") != "serial_ext16":
            continue
        cells.setdefault((r["target_id"], r["seed_idx"]), []).append(r)
    return {k: _latest(v) for k, v in cells.items()}


def main() -> int:
    bmc = load_bmc_x1()
    ext = load_serial_ext16()
    cells = []
    missing = []
    for target in PILOT_TARGETS:
        for seed_idx in SEED_IDXS:
            key = (target, seed_idx)
            b, e = bmc.get(key), ext.get(key)
            if b is None or e is None:
                missing.append({"target_id": target, "seed_idx": seed_idx,
                                "has_bmc_x1": b is not None, "has_serial_ext16": e is not None})
                continue
            cells.append({
                "target_id": target,
                "seed_idx": seed_idx,
                "bmc_x1_egarps_best": b["best"]["egarps_component"],
                "serial_ext16_egarps_best": e["best"]["egarps_component"],
                "bmc_x1_pool": b.get("candidate_count"),
                "serial_ext16_pool": e.get("candidate_count"),
            })

    x = [c["bmc_x1_egarps_best"] for c in cells]
    y = [c["serial_ext16_egarps_best"] for c in cells]
    delta = cliffs_delta(x, y) if cells else None
    wilcoxon_p = wilcoxon_paired(x, y) if len(cells) >= 5 else None
    med_x = median_iqr(x) if x else None
    med_y = median_iqr(y) if y else None
    wins = sum(1 for a, b in zip(x, y) if a > b)

    if delta is None or missing:
        verdict = "INCOMPLETE"
    elif delta >= GO_THRESHOLD:
        verdict = "GO"
    else:
        verdict = "NO-GO"

    summary = {
        "pilot": "P0_budget_matched_control",
        "date": "2026-08-03",
        "metric": "egarps_component best-of-pool",
        "comparison": "bmc_x1 vs serial_ext16 (budget-matched, 16 generated each)",
        "n_cells": len(cells),
        "missing_cells": missing,
        "cells": cells,
        "cliffs_delta": delta,
        "go_threshold": GO_THRESHOLD,
        "wilcoxon_paired_p": wilcoxon_p,
        "bmc_x1_median_iqr": med_x,
        "serial_ext16_median_iqr": med_y,
        "bmc_x1_wins": wins,
        "verdict": verdict,
        "verdict_meaning": (
            "GO: coordination has value beyond sampling budget"
            if verdict == "GO" else
            "NO-GO: budget explains the Fig-4 Type-II main effect; pivot to adaptive budget allocation (P3)"
            if verdict == "NO-GO" else
            "INCOMPLETE: cells missing, rerun drivers with --resume"
        ),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in
                      ("n_cells", "cliffs_delta", "wilcoxon_paired_p",
                       "bmc_x1_median_iqr", "serial_ext16_median_iqr",
                       "bmc_x1_wins", "verdict")}, indent=2))
    if missing:
        print("MISSING CELLS:", json.dumps(missing))
    print(f"summary -> {SUMMARY_OUT}")
    return 0 if verdict != "INCOMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
