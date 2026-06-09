#!/usr/bin/env python3
"""Run RNA aptamer design for Lysozyme (real benchmark target)."""
from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)-50s | %(message)s",
    datefmt="%H:%M:%S.%f",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

from data.benchmarks.rna_biobench_loader import load_platform_tasks
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow


def _build_executor() -> ToolExecutor:
    reg = build_default_tool_registry(include_demo=False)
    return ToolExecutor(reg)


def main():
    task_id = "08_rna_aptamer_design_005_lysozyme"
    tasks = load_platform_tasks()
    task = next((t for t in tasks if t.task_id == task_id), None)
    if task is None:
        print(json.dumps({"error": f"Task {task_id} not found"}))
        sys.exit(1)

    print(f"Task: {task_id}")
    print(f"Input: {json.dumps(task.input, indent=2)}")
    print("="*80)

    executor = _build_executor()
    cap_reg = build_default_capability_registry(executor)

    inp_dict = task.input
    inp_obj = RnaAptamerDesignInput(**inp_dict)
    wf_instance = RnaAptamerDesignWorkflow(cap_reg)

    task_start = time.perf_counter()
    result = None
    try:
        result = wf_instance.run(inp_obj)
    except Exception as exc:
        elapsed = time.perf_counter() - task_start
        print(f"\n{'='*80}")
        print(f"WORKFLOW CRASHED after {elapsed:.3f}s")
        print(f"Exception: {exc}")
        print(traceback.format_exc())
        sys.exit(1)

    elapsed = time.perf_counter() - task_start
    print(f"\n{'='*80}")
    print(f"TASK SUMMARY")
    print(f"{'='*80}")
    print(f"Task ID        : {task_id}")
    print(f"Total elapsed  : {elapsed:.3f}s")
    print(f"Success        : {result.success}")
    print(f"Errors         : {result.errors}")
    print(f"Summary        : {result.summary}")
    print(f"Candidates     : {len(result.all_candidates) if result.all_candidates else 0}")
    if result.best_candidate:
        bc = result.best_candidate
        print(f"Best candidate : {bc.id}")
        print(f"Best scores    : {bc.scores}")
        print(f"Best metadata  : {bc.metadata}")
    print(f"{'='*80}")

    # Print BMC trace if any
    writeback = getattr(result, "_state_writeback", None) or {}
    bmc_trace = writeback.get("_bmc_trace", [])
    if bmc_trace:
        print(f"\nBMC TRACE ({len(bmc_trace)} rounds):")
        for r in bmc_trace:
            print(f"  Round {r.get('round_num')}: best={r.get('best_candidate_id')} score={r.get('best_total_score'):.4f} "
                  f"issues={len(r.get('issues_found', []))} modules={r.get('modules_reinvoked')} "
                  f"time={r.get('time_elapsed_ms', 0):.1f}ms")


if __name__ == "__main__":
    main()
