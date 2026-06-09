#!/usr/bin/env python3
"""
Sequential runner for a single workflow with generous timeout and GPU monitoring.

Results are written to a workflow-specific temporary file first, then merged
into the main platform_coverage.jsonl at the end to avoid race conditions.

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_workflow_sequential.py <workflow_name>

Example:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_workflow_sequential.py sgrna_design
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_workflow_sequential.py full_length_mrna_design
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_workflow_sequential.py rna_aptamer_design
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks, PlatformTask
from experiments.run_platform_coverage import _check_tool_correctness

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = RESULTS_DIR / "platform_coverage.jsonl"

# No global timeout — let each task run to natural completion
TASK_TIMEOUT = 14400  # 2 hours as a safety net (should never be hit for healthy tasks)

# Service health-check endpoints per workflow
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
        "http://127.0.0.1:8023/health",  # EGARPS
    ],
}

# Auto-restart commands for services (optional)
SERVICE_RESTART_COMMANDS: Dict[str, List[str]] = {
    "sgrna_design": [
        "bash", "-c",
        "cd /inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/rna_agent_system/microservices/sgrna_design_service && "
        "source \"$(conda info --base)/etc/profile.d/conda.sh\" && conda activate sgrna_design_service_env && "
        "nohup python -m uvicorn main:app --host 0.0.0.0 --port 8017 > /tmp/sgrna_service.log 2>&1 &"
    ],
}


def _check_service_health(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ensure_services(workflow: str) -> None:
    urls = SERVICE_HEALTH_URLS.get(workflow, [])
    for url in urls:
        if not _check_service_health(url):
            print(f"  [WARN] Service unhealthy: {url}")
            # Try to restart if known
            restart_cmd = SERVICE_RESTART_COMMANDS.get(workflow)
            if restart_cmd:
                print(f"  [INFO] Attempting auto-restart...")
                try:
                    subprocess.Popen(restart_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(12)
                    if _check_service_health(url):
                        print(f"  [INFO] Service recovered: {url}")
                    else:
                        print(f"  [WARN] Service still down after restart: {url}")
                except Exception as exc:
                    print(f"  [WARN] Restart failed: {exc}")
            else:
                print(f"  [WARN] No restart command configured for this workflow")


def _gpu_memory_mb() -> List[int]:
    """Return per-GPU memory usage in MiB."""
    try:
        import torch
        if not torch.cuda.is_available():
            return []
        return [torch.cuda.memory_allocated(i) // (1024 * 1024) for i in range(torch.cuda.device_count())]
    except Exception:
        return []


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_workflow_sequential.py <workflow_name>", file=sys.stderr)
        sys.exit(1)

    target_workflow = sys.argv[1]
    all_tasks = load_platform_tasks()
    tasks = [t for t in all_tasks if t.workflow == target_workflow]

    if not tasks:
        print(f"No tasks found for workflow: {target_workflow}")
        sys.exit(1)

    # Skip already completed tasks in the main output file
    completed_ids: set[str] = set()
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    if rec.get("workflow") == target_workflow:
                        completed_ids.add(rec["task_id"])

    tasks = [t for t in tasks if t.task_id not in completed_ids]
    print(f"Workflow: {target_workflow}")
    print(f"Total tasks: {len(all_tasks)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(tasks)}")

    if not tasks:
        print("All tasks already completed.")
        return

    # Write to a temporary file first to avoid corrupting the main file
    temp_path = RESULTS_DIR / f"platform_coverage_{target_workflow}.jsonl"
    temp_records: List[str] = []

    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] {task.task_id} ({task.category})")

        # Ensure required services are up before each task
        _ensure_services(target_workflow)

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

        temp_records.append(json.dumps(record, ensure_ascii=False) + "\n")
        # Flush to temp file after each task for durability
        with open(temp_path, "a", encoding="utf-8") as f:
            f.write(temp_records[-1])

        # GPU cooldown between tasks
        time.sleep(5)
        gpu_mem = _gpu_memory_mb()
        if gpu_mem:
            print(f"  -> GPU memory (MiB): {gpu_mem}")

    # Merge temp file into main output file
    print(f"\nMerging {len(temp_records)} records into {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for line in temp_records:
            f.write(line)
    print(f"Merged successfully. Removing temp file: {temp_path}")
    temp_path.unlink(missing_ok=True)
    print(f"Completed sequential run for {target_workflow}")


if __name__ == "__main__":
    main()
