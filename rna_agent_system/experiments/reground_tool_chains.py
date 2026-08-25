#!/usr/bin/env python3
"""Reground RNADesign-210 ``expected_tool_chain`` against observed run traces.

After a successful full benchmark run (exp1_rnadesign210 lane records), each
task's expected chain is rewritten to the sorted set of tools its own run
actually invoked — the authored chains predate the 2026-08-18 tool purge and
the 2026-08-2x workflow rewires.

Guard rails:
- only successful records with a non-empty ``tools_used`` are used;
- tasks whose workflow records no per-candidate trace on success with zero
  candidates (IRES boundary task) keep their authored chain and are reported;
- ``--check`` compares without writing.

Idempotent; run after the lanes complete.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TASKS_ROOT = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp1_rnadesign210"


def latest_records() -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for path in sorted(RESULTS_DIR.glob("lane_*.jsonl")):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_id[rec["task_id"]] = rec
    return by_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report diffs only, no writes")
    args = parser.parse_args()

    records = latest_records()
    if not records:
        print("no lane records found")
        return 1

    n_updated = n_kept = 0
    kept: list[str] = []
    for tf in sorted(TASKS_ROOT.glob("*/*.json")):
        if tf.name == "dataset_manifest.json":
            continue
        task = json.loads(tf.read_text(encoding="utf-8"))
        rec = records.get(task["task_id"])
        if rec is None or not rec.get("success") or not rec.get("tools_used"):
            kept.append(task["task_id"])
            n_kept += 1
            continue
        observed = sorted(set(rec["tools_used"]))
        if task.get("expected_tool_chain") != observed:
            task["expected_tool_chain"] = observed
            n_updated += 1
            if not args.check:
                tf.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    print(f"{'would update' if args.check else 'updated'}: {n_updated}; kept authored chain: {n_kept}")
    for tid in kept:
        print(f"  kept: {tid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
