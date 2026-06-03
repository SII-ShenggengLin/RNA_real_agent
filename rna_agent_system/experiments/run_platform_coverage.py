#!/usr/bin/env python3
"""
Platform Coverage Experiment Runner for RNA Agent System.

Runs all tasks in RNA-BioBench-Platform benchmark and records:
- task_id, workflow, category
- success (bool)
- errors (list)
- elapsed_seconds
- tool_correctness (whether expected tools were invoked)
- trace completeness

Outputs:
    rna_agent_system/experiments/results/platform_coverage.jsonl

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_platform_coverage.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks, PlatformTask
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.tool_registry import ToolRegistry

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = RESULTS_DIR / "platform_coverage.jsonl"

# Timeout per task in seconds (increased to allow slow workflows like
# full_length_mrna_design and rna_aptamer_design to complete).
# Genuine hangs are rare and caught by per-task error handling.
# Set to a very large value to ensure tasks are not killed by timeout.
TASK_TIMEOUT = 7200

# Service health-check endpoints per workflow.
# Keep in sync with experiments/run_workflow_sequential.py :: SERVICE_HEALTH_URLS.
SERVICE_HEALTH_URLS: Dict[str, List[str]] = {
    "sgrna_design": ["http://127.0.0.1:8017/health"],
    "full_length_mrna_design": [
        "http://127.0.0.1:8014/health",  # LinearDesign
        "http://127.0.0.1:8004/health",  # GEMORNA (UTR design)
        "http://127.0.0.1:8015/health",  # LinearFold
        "http://127.0.0.1:8018/health",  # CodonW
        "http://127.0.0.1:8003/health",  # ViennaRNA
    ],
    "rna_aptamer_design": [
        "http://127.0.0.1:8012/health",  # ODesign
        "http://127.0.0.1:8022/health",  # ProteinX
        "http://127.0.0.1:8005/health",  # RhoFold
        "http://127.0.0.1:8010/health",  # EGARPS
    ],
}


def _check_service_health(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ensure_services(workflow: str) -> None:
    """Print warnings for any unhealthy services required by *workflow*.

    This gives the operator a chance to start missing services before
    wasting time on tasks that are guaranteed to fail.
    """
    urls = SERVICE_HEALTH_URLS.get(workflow, [])
    unhealthy: List[str] = []
    for url in urls:
        if not _check_service_health(url):
            unhealthy.append(url)
    if unhealthy:
        print(f"  [WARN] Unhealthy services for {workflow}:")
        for url in unhealthy:
            print(f"    - {url}")
        print(f"  [HINT] Start the missing service(s) before continuing.")


def _check_tool_correctness(result, expected_chain: List[str]) -> Dict[str, Any]:
    """Check if expected tools were actually invoked in the trace.

    Supports multiple evidence sources:
    1. result.trace (ToolCallRecord list) — used by mrna_sequence_scoring
    2. result._state_writeback['tool_results'] — used by Capability-based workflows
    3. candidate metadata — fallback for design-tool source tracking
    """
    invoked: set[str] = set()

    # Source 1: direct trace
    if result.trace:
        for step in result.trace:
            tool_name = getattr(step, "tool_name", None)
            if tool_name:
                invoked.add(tool_name)

    # Source 2: state writeback from Capability.invoke()
    writeback = getattr(result, "_state_writeback", None)
    if writeback and isinstance(writeback, dict):
        tool_results = writeback.get("tool_results", {})
        if isinstance(tool_results, dict):
            invoked.update(tool_results.keys())

    # Source 3: candidate metadata for design workflows
    for cand in (result.all_candidates or []):
        meta = getattr(cand, "metadata", None) or {}
        if isinstance(meta, dict):
            # Design tool source
            src = meta.get("source", "")
            if isinstance(src, str):
                # e.g. "cds_design:lineardesign_lambda0.0"
                if "lineardesign" in src:
                    invoked.add("design_mrna_cds_with_lineardesign")
                if "rnarl" in src:
                    invoked.add("design_mrna_cds_with_rnarl")
                if "gemorna" in src:
                    invoked.add("design_mrna_cds_with_gemorna")
                if "rhodesign" in src:
                    invoked.add("design_rna_sequence_with_rhodesign")
                if "ribodiffusion" in src:
                    invoked.add("design_rna_inverse_fold_with_ribodiffusion")
                if "odesign" in src:
                    invoked.add("run_odesign_inference")
            # Additional metadata fields
            fold_tool = meta.get("fold_tool")
            if isinstance(fold_tool, str):
                if "ViennaRNA" in fold_tool:
                    invoked.add("predict_rna_secondary_structure_with_viennarna")
                if "LinearFold" in fold_tool:
                    invoked.add("predict_rna_secondary_structure_with_linearfold")
            if meta.get("design_tool") == "lineardesign":
                invoked.add("design_mrna_cds_with_lineardesign")
            if meta.get("design_tool") == "rnarl":
                invoked.add("design_mrna_cds_with_rnarl")
            if meta.get("design_tool") == "gemorna":
                invoked.add("design_mrna_cds_with_gemorna")

    # Expected tools may be referred to by shorter names in tool_chain vs full tool_name
    # Do a best-effort substring match
    missing = []
    for exp in expected_chain:
        if not any(exp in inv or inv in exp for inv in invoked):
            missing.append(exp)

    return {
        "correct": len(missing) == 0,
        "expected": expected_chain,
        "invoked": sorted(invoked),
        "missing": missing,
    }


def main():
    print("=" * 60)
    print("RNA-BioBench-Platform Coverage Runner")
    print("=" * 60)

    tasks = load_platform_tasks()
    print(f"Loaded {len(tasks)} benchmark tasks")

    # Skip already completed tasks
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            completed_ids = {json.loads(line)["task_id"] for line in f if line.strip()}
        tasks = [t for t in tasks if t.task_id not in completed_ids]
        print(f"Skipping {len(completed_ids)} already completed tasks")

    # Count by workflow
    wf_counts = Counter(t.workflow for t in tasks)
    for wf, cnt in sorted(wf_counts.items()):
        print(f"  {wf}: {cnt}")

    results: List[Dict[str, Any]] = []
    start_global = time.perf_counter()

    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] {task.task_id} ({task.workflow} / {task.category})")
        _ensure_services(task.workflow)
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
    if len(results) > 0:
        print(f"Overall success rate: {success_count}/{len(results)} = {100*success_count/len(results):.1f}%")
    else:
        print("All tasks already completed — no new tasks to run.")

    print("\nPer-workflow success rate:")
    for wf in sorted(wf_counts.keys()):
        wf_results = [r for r in results if r["workflow"] == wf]
        if len(wf_results) > 0:
            wf_success = sum(1 for r in wf_results if r["success"])
            print(f"  {wf}: {wf_success}/{len(wf_results)} = {100*wf_success/len(wf_results):.1f}%")
        else:
            print(f"  {wf}: already completed")


if __name__ == "__main__":
    main()
