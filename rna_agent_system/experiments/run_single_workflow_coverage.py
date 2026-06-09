#!/usr/bin/env python3
"""
Single-workflow coverage runner for RNA-BioBench-Platform benchmark.

Runs all tasks for a specified workflow, records per-task metrics,
and writes results incrementally to workflow-specific directories.

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_single_workflow_coverage.py --workflow mrna_cds_design
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Per-task timeout (seconds).  Must be large enough to avoid killing slow
# but legitimate tasks.
TASK_TIMEOUT = 7200

# Concurrency limits by workflow type.
# CPU-only workflows (including those that call lineardesign) → max 5.
# GPU workflows → 1 (sequential).
CPU_WORKFLOWS = {
    "mrna_cds_design",
    "mrna_sequence_scoring",
    "sirna_design",
    "sgrna_design",
    "rna_secondary_structure_design",
    "aso_target_screening",
    "ires_prediction",
}
GPU_WORKFLOWS = {
    "rna_aptamer_design",
    "rna_tertiary_structure_design",
    "full_length_mrna_design",
    "rna_small_molecule_interaction",
}

SERVICE_HEALTH_URLS: Dict[str, List[str]] = {
    "mrna_cds_design": [
        "http://127.0.0.1:8014/health",  # LinearDesign
        "http://127.0.0.1:8008/health",  # RNARL
        "http://127.0.0.1:8004/health",  # GEMORNA
        "http://127.0.0.1:8003/health",  # ViennaRNA
        "http://127.0.0.1:8015/health",  # LinearFold
        "http://127.0.0.1:8018/health",  # CodonW
        "http://127.0.0.1:8020/health",  # RNA sequence metrics
        "http://127.0.0.1:8009/health",  # RNASTOP
    ],
    "full_length_mrna_design": [
        "http://127.0.0.1:8014/health",
        "http://127.0.0.1:8004/health",
        "http://127.0.0.1:8015/health",
        "http://127.0.0.1:8018/health",
        "http://127.0.0.1:8003/health",
    ],
    "rna_aptamer_design": [
        "http://127.0.0.1:8012/health",
        "http://127.0.0.1:8022/health",
        "http://127.0.0.1:8005/health",
        "http://127.0.0.1:8023/health",
    ],
    "sirna_design": [
        "http://127.0.0.1:8003/health",  # ViennaRNA
        "http://127.0.0.1:8016/health",  # Evitar
        "http://127.0.0.1:8019/health",  # BLAST
    ],
    "sgrna_design": [
        "http://127.0.0.1:8017/health",
        "http://127.0.0.1:8011/health",
    ],
    "rna_secondary_structure_design": [
        "http://127.0.0.1:8003/health",
        "http://127.0.0.1:8015/health",
    ],
    "rna_tertiary_structure_design": [
        "http://127.0.0.1:8005/health",  # RhoFold
        "http://127.0.0.1:8006/health",  # RhoDesign
        "http://127.0.0.1:8021/health",  # RiboDiffusion
        "http://127.0.0.1:8003/health",  # ViennaRNA
        "http://127.0.0.1:8020/health",  # RNA sequence metrics
    ],
    "rna_small_molecule_interaction": [
        "http://127.0.0.1:8007/health",  # RNAsmol
        "http://127.0.0.1:8010/health",  # GerNA-Bind
    ],
    "mrna_sequence_scoring": [
        "http://127.0.0.1:8003/health",
        "http://127.0.0.1:8015/health",
        "http://127.0.0.1:8009/health",
        "http://127.0.0.1:8020/health",
        "http://127.0.0.1:8018/health",
    ],
    "aso_target_screening": [
        "http://127.0.0.1:8003/health",
    ],
    "ires_prediction": [
        "http://127.0.0.1:8013/health",  # IRESfinder
        "http://127.0.0.1:8015/health",  # LinearFold
        "http://127.0.0.1:8003/health",  # ViennaRNA
        "http://127.0.0.1:8020/health",  # RNA sequence metrics
    ],
}


def _check_service_health(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _check_services(workflow: str) -> List[str]:
    urls = SERVICE_HEALTH_URLS.get(workflow, [])
    unhealthy: List[str] = []
    for url in urls:
        if not _check_service_health(url):
            unhealthy.append(url)
    return unhealthy


def _workflow_to_dirname(workflow: str) -> str:
    """Map workflow name to benchmark task directory name."""
    mapping = {
        "mrna_cds_design": "01_mrna_cds_design",
        "full_length_mrna_design": "02_full_length_mrna_design",
        "mrna_sequence_scoring": "03_mrna_sequence_scoring",
        "sirna_design": "04_sirna_design",
        "sgrna_design": "05_sgrna_design",
        "rna_secondary_structure_design": "06_rna_secondary_structure",
        "rna_tertiary_structure_design": "07_rna_tertiary_structure",
        "rna_aptamer_design": "08_rna_aptamer_design",
        "rna_small_molecule_interaction": "09_rna_small_molecule",
        "aso_target_screening": "10_aso_target_screening",
        "ires_prediction": "11_ires_prediction",
    }
    return mapping.get(workflow, workflow)


def _load_workflow_tasks(workflow: str):
    """Load only tasks belonging to the specified workflow."""
    all_tasks = load_platform_tasks()
    tasks = [t for t in all_tasks if t.workflow == workflow]
    return tasks


def _run_task_subprocess(task, env: Dict[str, str]) -> Dict[str, Any]:
    """Run a single task via run_single_task.py subprocess."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "experiments" / "run_single_task.py"),
        task.task_id,
    ]
    task_start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=TASK_TIMEOUT,
        env=env,
    )
    elapsed = round(time.perf_counter() - task_start, 3)
    if proc.returncode == 0:
        try:
            record = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:
            record = {
                "task_id": task.task_id,
                "workflow": task.workflow,
                "category": task.category,
                "success": False,
                "errors": ["invalid_json_from_worker", proc.stdout[-500:]],
                "elapsed_seconds": elapsed,
                "tool_correctness": False,
                "tool_missing": task.expected_tool_chain,
                "trace_length": 0,
                "trace_completeness": "none",
                "recorded_tools": [],
                "expected_tools": task.expected_tool_chain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    else:
        record = {
            "task_id": task.task_id,
            "workflow": task.workflow,
            "category": task.category,
            "success": False,
            "errors": [f"worker_exitcode_{proc.returncode}", proc.stderr[:500]],
            "elapsed_seconds": elapsed,
            "tool_correctness": False,
            "tool_missing": task.expected_tool_chain,
            "trace_length": 0,
            "trace_completeness": "none",
            "recorded_tools": [],
            "expected_tools": task.expected_tool_chain,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    record["runner_exit_code"] = proc.returncode
    return record


def _concurrent_run(tasks, max_workers: int, env: Dict[str, str], raw_path: Path, log_file):
    """Run tasks with bounded concurrency using subprocess + thread pool."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    completed = 0
    total = len(tasks)
    lock = __import__("threading").Lock()

    def _run_one(task):
        task_start = time.perf_counter()
        try:
            record = _run_task_subprocess(task, env)
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
                "trace_completeness": "none",
                "recorded_tools": [],
                "expected_tools": task.expected_tool_chain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runner_exit_code": -1,
            }
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
                "trace_completeness": "none",
                "recorded_tools": [],
                "expected_tools": task.expected_tool_chain,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "runner_exit_code": -1,
            }
        elapsed = time.perf_counter() - task_start
        record["runner_elapsed_seconds"] = round(elapsed, 3)
        return record

    def _write(record):
        with lock:
            with open(raw_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()

    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for task in tasks:
            future = executor.submit(_run_one, task)
            futures[future] = task

        for future in as_completed(futures):
            task = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "task_id": task.task_id,
                    "workflow": task.workflow,
                    "category": task.category,
                    "success": False,
                    "errors": [f"future_exception: {exc}"],
                    "elapsed_seconds": 0.0,
                    "tool_correctness": False,
                    "tool_missing": task.expected_tool_chain,
                    "trace_length": 0,
                    "trace_completeness": "none",
                    "recorded_tools": [],
                    "expected_tools": task.expected_tool_chain,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "runner_exit_code": -1,
                    "runner_elapsed_seconds": 0.0,
                }
            _write(record)
            completed += 1
            msg = (
                f"[{completed}/{total}] {task.task_id} "
                f"success={record['success']} "
                f"elapsed={record.get('elapsed_seconds', 0):.2f}s "
                f"tool_correct={record.get('tool_correctness', False)}"
            )
            if record.get("errors"):
                msg += f" errors={record['errors'][:2]}"
            print(msg)
            log_file.write(msg + "\n")
            log_file.flush()


def main():
    parser = argparse.ArgumentParser(description="Run a single workflow from RNA-BioBench-Platform")
    parser.add_argument("--workflow", required=True, help="Workflow name, e.g. mrna_cds_design")
    parser.add_argument("--max-workers", type=int, default=None, help="Override concurrency limit")
    parser.add_argument("--dry-run", action="store_true", help="List tasks without running")
    parser.add_argument("--task-ids", type=str, default=None, help="Comma-separated list of task IDs to run (e.g. task1,task2). If not set, all tasks for the workflow are run.")
    parser.add_argument("--force", action="store_true", help="Force rerun even if tasks were previously successful. Old records are removed from the raw JSONL before running.")
    args = parser.parse_args()

    workflow = args.workflow
    print("=" * 60)
    print(f"Single-workflow runner: {workflow}")
    print("=" * 60)

    # ── Service health check ──────────────────────────────────────────────
    unhealthy = _check_services(workflow)
    if unhealthy:
        print(f"[WARN] Unhealthy services for {workflow}:")
        for url in unhealthy:
            print(f"  - {url}")
        print("[HINT] Start missing services before continuing.")
        # Do not abort — some workflows may tolerate missing optional services.
    else:
        print(f"[OK] All registered services for {workflow} are healthy.")

    # ── Task loading ──────────────────────────────────────────────────────
    tasks = _load_workflow_tasks(workflow)
    if not tasks:
        print(f"[ERROR] No tasks found for workflow '{workflow}'")
        sys.exit(1)

    # Filter by explicit task IDs if provided
    target_task_ids: set[str] = set()
    if args.task_ids:
        target_task_ids = {tid.strip() for tid in args.task_ids.split(",") if tid.strip()}
        tasks = [t for t in tasks if t.task_id in target_task_ids]
        if not tasks:
            print(f"[ERROR] None of the specified task IDs were found for workflow '{workflow}'")
            sys.exit(1)
        missing = target_task_ids - {t.task_id for t in tasks}
        if missing:
            print(f"[WARN] The following task IDs were not found: {sorted(missing)}")

    # Sort tasks: basic first, then full, then edge (optional deterministic order)
    def _sort_key(t):
        order = {"basic": 0, "full": 1, "edge": 2}
        return (order.get(t.category, 99), t.task_id)

    tasks = sorted(tasks, key=_sort_key)
    print(f"Loaded {len(tasks)} tasks for {workflow}")
    for t in tasks:
        print(f"  {t.task_id} ({t.category})")

    if args.dry_run:
        print("\nDry-run mode — exiting without execution.")
        sys.exit(0)

    # ── Determine concurrency ─────────────────────────────────────────────
    if args.max_workers is not None:
        max_workers = args.max_workers
    elif workflow in CPU_WORKFLOWS:
        max_workers = 5
    elif workflow in GPU_WORKFLOWS:
        max_workers = 1
    else:
        max_workers = 1
    print(f"Concurrency: {max_workers} worker(s)")

    # ── Result directories ────────────────────────────────────────────────
    base_dir = (
        PROJECT_ROOT
        / "experiments"
        / "results"
        / "platform_coverage_by_workflow"
        / workflow
    )
    raw_dir = base_dir / "raw"
    logs_dir = base_dir / "logs"
    summary_dir = base_dir / "summary"
    for d in (raw_dir, logs_dir, summary_dir):
        d.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"platform_coverage_{workflow}.jsonl"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"run_{workflow}_{timestamp}.log"

    # ── Handle force rerun / skip logic ───────────────────────────────────
    # If --force is set, remove old records for the target tasks from raw JSONL
    # so they will be rerun and overwritten.
    if args.force and target_task_ids and raw_path.exists():
        kept_lines = []
        removed_count = 0
        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        if rec.get("task_id") in target_task_ids:
                            removed_count += 1
                            continue
                    except Exception:
                        pass
                kept_lines.append(line)
        if removed_count:
            with open(raw_path, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
            print(f"[FORCE] Removed {removed_count} old record(s) for specified task IDs from raw JSONL.")

    # Skip already successfully completed tasks (unless forced)
    completed_ids = set()
    failed_ids = set()
    if raw_path.exists():
        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        tid = rec["task_id"]
                        if rec.get("success"):
                            completed_ids.add(tid)
                        else:
                            failed_ids.add(tid)
                    except Exception:
                        pass
        if completed_ids:
            print(f"Skipping {len(completed_ids)} already successfully completed tasks")
        if failed_ids:
            print(f"Will rerun {len(failed_ids)} previously failed tasks")
        tasks = [t for t in tasks if t.task_id not in completed_ids]

    if not tasks:
        print("All tasks already successfully completed.")
        sys.exit(0)

    # ── Environment ───────────────────────────────────────────────────────
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    # ── Run ───────────────────────────────────────────────────────────────
    start_global = time.perf_counter()
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"Workflow: {workflow}\n")
        log_file.write(f"Tasks: {len(tasks)}\n")
        log_file.write(f"Concurrency: {max_workers}\n")
        log_file.write(f"Start: {datetime.now(timezone.utc).isoformat()}\n")
        log_file.write("=" * 60 + "\n")
        log_file.flush()

        _concurrent_run(tasks, max_workers, env, raw_path, log_file)

        total_elapsed = time.perf_counter() - start_global
        log_file.write("\n" + "=" * 60 + "\n")
        log_file.write(f"Finished in {total_elapsed:.1f}s\n")
        log_file.flush()

    print(f"\n{'=' * 60}")
    print(f"Results: {raw_path}")
    print(f"Log:     {log_path}")
    print(f"Total elapsed: {total_elapsed:.1f}s")

    # ── Summary generation ────────────────────────────────────────────────
    _generate_summary(workflow, raw_path, summary_dir, log_path)


def _generate_summary(workflow: str, raw_path: Path, summary_dir: Path, log_path: Path):
    """Generate summary JSON from raw results."""
    if not raw_path.exists():
        print("[WARN] No raw results found, skipping summary.")
        return

    records: list[dict[str, Any]] = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if not records:
        print("[WARN] No valid records found, skipping summary.")
        return

    total = len(records)
    success_count = sum(1 for r in records if r.get("success"))
    failure_count = total - success_count
    success_rate = success_count / total if total > 0 else 0.0

    # Per-category breakdown
    category_stats: dict[str, dict[str, Any]] = {}
    for r in records:
        cat = r.get("category", "unknown")
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "success": 0}
        category_stats[cat]["total"] += 1
        if r.get("success"):
            category_stats[cat]["success"] += 1

    category_summary = {}
    for cat, stats in sorted(category_stats.items()):
        cat_total = stats["total"]
        cat_success = stats["success"]
        category_summary[cat] = {
            "total": cat_total,
            "success": cat_success,
            "failure": cat_total - cat_success,
            "success_rate": round(cat_success / cat_total, 4) if cat_total > 0 else 0.0,
        }

    # Error type distribution (for failures)
    error_counter: dict[str, int] = {}
    for r in records:
        if not r.get("success"):
            errors = r.get("errors", [])
            if errors:
                # Use first error prefix as key
                first_err = str(errors[0])
                if len(first_err) > 100:
                    first_err = first_err[:100] + "..."
                error_counter[first_err] = error_counter.get(first_err, 0) + 1
            else:
                error_counter["unknown_error"] = error_counter.get("unknown_error", 0) + 1

    # Timing stats
    elapsed_times = [r.get("elapsed_seconds", 0.0) for r in records]
    elapsed_times_sorted = sorted(elapsed_times)
    n = len(elapsed_times_sorted)
    median_time = (
        elapsed_times_sorted[n // 2]
        if n % 2 == 1
        else (elapsed_times_sorted[n // 2 - 1] + elapsed_times_sorted[n // 2]) / 2
    )

    # Tool correctness
    tool_correct_count = sum(1 for r in records if r.get("tool_correctness"))
    tool_correct_rate = tool_correct_count / total if total > 0 else 0.0

    # Trace completeness distribution
    trace_dist: dict[str, int] = {}
    for r in records:
        tc = r.get("trace_completeness", "unknown")
        trace_dist[tc] = trace_dist.get(tc, 0) + 1

    summary = {
        "workflow": workflow,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": total,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": round(success_rate, 4),
        "category_breakdown": category_summary,
        "error_distribution": error_counter,
        "timing_seconds": {
            "mean": round(sum(elapsed_times) / n, 3) if n > 0 else 0.0,
            "median": round(median_time, 3),
            "max": round(max(elapsed_times), 3) if elapsed_times else 0.0,
            "min": round(min(elapsed_times), 3) if elapsed_times else 0.0,
        },
        "tool_correctness_rate": round(tool_correct_rate, 4),
        "trace_completeness_distribution": trace_dist,
        "raw_results_path": str(raw_path),
        "log_path": str(log_path),
    }

    summary_path = summary_dir / f"summary_{workflow}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
