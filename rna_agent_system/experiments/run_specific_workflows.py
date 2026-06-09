#!/usr/bin/env python3
"""Run platform coverage for specific workflows with custom timeout."""
from __future__ import annotations

import json
import os
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
OUTPUT_PATH = RESULTS_DIR / "platform_coverage.jsonl"


def run_workflows(workflows: List[str], timeout: int) -> None:
    tasks = load_platform_tasks()
    tasks = [t for t in tasks if t.workflow in workflows]

    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            completed_ids = {json.loads(line)["task_id"] for line in f if line.strip()}
        tasks = [t for t in tasks if t.task_id not in completed_ids]
        print(f"Skipping {len(completed_ids)} already completed tasks")

    print(f"Running {len(tasks)} tasks for workflows: {workflows} with timeout={timeout}s")

    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] {task.task_id} ({task.workflow} / {task.category})")
        task_start = time.perf_counter()

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "experiments" / "run_single_task.py"),
            task.task_id,
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            elapsed = time.perf_counter() - task_start

            if proc.returncode == 0:
                stdout_lines = proc.stdout.strip().splitlines()
                if stdout_lines:
                    try:
                        record = json.loads(stdout_lines[-1])
                        record["elapsed_seconds"] = round(elapsed, 3)
                        print(f"  -> success={record['success']}, elapsed={elapsed:.2f}s, tool_correct={record['tool_correctness']}")
                    except Exception as parse_exc:
                        record = {
                            "task_id": task.task_id,
                            "workflow": task.workflow,
                            "category": task.category,
                            "success": False,
                            "errors": [f"stdout_parse_error: {parse_exc}", proc.stdout[:500]],
                            "elapsed_seconds": round(elapsed, 3),
                            "tool_correctness": False,
                            "tool_missing": task.expected_tool_chain,
                            "trace_length": 0,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        print(f"  -> PARSE ERROR: {parse_exc}")
                else:
                    record = {
                        "task_id": task.task_id,
                        "workflow": task.workflow,
                        "category": task.category,
                        "success": False,
                        "errors": ["empty_stdout"],
                        "elapsed_seconds": round(elapsed, 3),
                        "tool_correctness": False,
                        "tool_missing": task.expected_tool_chain,
                        "trace_length": 0,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    print(f"  -> EMPTY STDOUT")
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
                "errors": [f"timeout_after_{timeout}s"],
                "elapsed_seconds": round(elapsed, 3),
                "tool_correctness": False,
                "tool_missing": task.expected_tool_chain,
                "trace_length": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> TIMEOUT after {timeout}s")

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

        with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflows", nargs="+", required=True, help="Workflow names to run")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per task in seconds")
    args = parser.parse_args()
    run_workflows(args.workflows, args.timeout)
