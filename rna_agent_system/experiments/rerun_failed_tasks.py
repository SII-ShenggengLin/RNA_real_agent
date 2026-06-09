#!/usr/bin/env python3
"""Serial rerun of failed non-aptamer tasks with 600s timeout each."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks

RESULTS_PATH = PROJECT_ROOT / "experiments" / "results" / "platform_coverage.jsonl"
TASK_TIMEOUT = 600

# Task IDs to rerun (all non-aptamer failures)
FAILED_TASK_IDS = {
    # aso_target_screening
    "10_aso_target_screening_002_real_transcript",
    # full_length_mrna_design
    "02_full_length_mrna_design_002_vaccine_spike",
    "02_full_length_mrna_design_004_reporter_gfp",
    "02_full_length_mrna_design_006_betagal",
    "02_full_length_mrna_design_009_ovalbumin",
    "02_full_length_mrna_design_017_zebrafish_cai",
    "02_full_length_mrna_design_022_fly_cai",
    # ires_prediction
    "11_ires_prediction_002_mode0_structural",
    "11_ires_prediction_006_mode1_structural",
    # mrna_cds_design
    "01_mrna_cds_design_003",
    "01_mrna_cds_design_005",
    "01_mrna_cds_design_009",
    "01_mrna_cds_design_019",
    # rna_secondary_structure_design
    "06_rna_secondary_structure_014_function_mode_p",
    "06_rna_secondary_structure_015_function_mode_mp",
    "06_rna_secondary_structure_019_repeats_max_boundary",
    # rna_small_molecule_interaction
    "09_rna_small_molecule_002_multi_tool",
    # rna_tertiary_structure_design
    "07_rna_tertiary_structure_005_rhodesign_low_temp",
    "07_rna_tertiary_structure_006_dual_equal",
    "07_rna_tertiary_structure_010_all_tools",
    "07_rna_tertiary_structure_016_max_samples",
    # sirna_design
    "04_sirna_design_020_antiviral_predesign_crispr",
}


def main():
    all_tasks = {t.task_id: t for t in load_platform_tasks()}

    # Filter to requested tasks that exist
    tasks_to_run = [all_tasks[tid] for tid in FAILED_TASK_IDS if tid in all_tasks]
    print(f"Rerunning {len(tasks_to_run)} failed tasks serially with {TASK_TIMEOUT}s timeout each")

    # Remove old failed records from JSONL
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        kept = []
        removed = 0
        for line in lines:
            d = json.loads(line)
            if d["task_id"] in FAILED_TASK_IDS:
                removed += 1
                continue
            kept.append(line)
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            f.writelines(kept)
        print(f"Removed {removed} old failed records")

    results = []
    for idx, task in enumerate(tasks_to_run, 1):
        print(f"\n[{idx}/{len(tasks_to_run)}] {task.task_id} ({task.workflow})")
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
                print(f"  -> success={record['success']}, elapsed={elapsed:.1f}s, tool_correct={record['tool_correctness']}")
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
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    success_count = sum(1 for r in results if r.get("tool_correctness", False))
    print(f"\n{'='*60}")
    print(f"Completed {len(results)} tasks, {success_count} succeeded")
    print(f"Results appended to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
