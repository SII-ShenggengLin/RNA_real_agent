#!/usr/bin/env python3
"""
Platform Coverage Experiment Runner — Subprocess version.

Uses subprocess.run(timeout=...) for reliable per-task timeout.
Each task runs in a completely separate Python process that can be
killed by the OS when the timeout expires.

Outputs:
    rna_agent_system/experiments/results/platform_coverage.jsonl

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_platform_coverage_subprocess.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = RESULTS_DIR / "platform_coverage.jsonl"

TASK_TIMEOUT = 7200  # seconds per task (2h; matches run_platform_coverage.py)


def main():
    print("=" * 60)
    print("RNA-BioBench-Platform Coverage Runner (subprocess)")
    print("=" * 60)

    tasks = load_platform_tasks()
    print(f"Loaded {len(tasks)} benchmark tasks")

    wf_counts = Counter(t.workflow for t in tasks)
    for wf, cnt in sorted(wf_counts.items()):
        print(f"  {wf}: {cnt}")

    results: List[Dict[str, Any]] = []
    start_global = time.perf_counter()

    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] {task.task_id} ({task.workflow} / {task.category})")
        task_start = time.perf_counter()

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "experiments" / "run_single_task.py"),
            task.task_id,
        ]
        env = dict(os.environ) if "os" in sys.modules else {}
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TASK_TIMEOUT,
                env=env,
            )
            elapsed = time.perf_counter() - task_start

            if proc.returncode == 0:
                record = json.loads(proc.stdout.strip().splitlines()[-1])
                record["elapsed_seconds"] = round(elapsed, 3)
                print(f"  -> success={record['success']}, elapsed={elapsed:.2f}s, tool_correct={record['tool_correctness']}")
                if record["errors"]:
                    print(f"  -> errors: {record['errors'][:3]}")
            else:
                record = {
                    "task_id": task.task_id,
                    "workflow": task.workflow,
                    "category": task.category,
                    "success": False,
                    "errors": [f"worker_exitcode_{proc.returncode}", proc.stderr[:500]],
                    "elapsed_seconds": round(elapsed, 3),
                    "tool_correctness": False,
                    "tool_missing": task.expected_tool_chain,
                    "trace_length": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print(f"  -> WORKER ERROR (exitcode={proc.returncode})")

        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - task_start
            record = {
                "task_id": task.task_id,
                "workflow": task.workflow,
                "category": task.category,
                "success": False,
                "errors": [f"timeout_after_{TASK_TIMEOUT}s"],
                "elapsed_seconds": round(elapsed, 3),
                "tool_correctness": False,
                "tool_missing": task.expected_tool_chain,
                "trace_length": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> TIMEOUT after {TASK_TIMEOUT}s")

        except Exception as exc:
            elapsed = time.perf_counter() - task_start
            record = {
                "task_id": task.task_id,
                "workflow": task.workflow,
                "category": task.category,
                "success": False,
                "errors": [str(exc)],
                "elapsed_seconds": round(elapsed, 3),
                "tool_correctness": False,
                "tool_missing": task.expected_tool_chain,
                "trace_length": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> EXCEPTION: {exc}")

        results.append(record)

        with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    total_elapsed = time.perf_counter() - start_global
    print(f"\n{'=' * 60}")
    print(f"Completed {len(results)} tasks in {total_elapsed:.1f}s")
    print(f"Results saved to: {OUTPUT_PATH}")

    success_count = sum(1 for r in results if r["success"])
    print(f"Overall success rate: {success_count}/{len(results)} = {100*success_count/len(results):.1f}%")

    print("\nPer-workflow success rate:")
    for wf in sorted(wf_counts.keys()):
        wf_results = [r for r in results if r["workflow"] == wf]
        wf_success = sum(1 for r in wf_results if r["success"])
        print(f"  {wf}: {wf_success}/{len(wf_results)} = {100*wf_success/len(wf_results):.1f}%")


if __name__ == "__main__":
    import os
    main()
