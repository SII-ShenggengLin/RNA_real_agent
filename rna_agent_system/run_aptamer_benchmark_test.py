#!/usr/bin/env python3
"""Batch test all RNA aptamer design benchmark tasks."""
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow

RESULTS_FILE = PROJECT_ROOT / "experiments" / "results" / "aptamer_benchmark_test.jsonl"
RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

def main():
    all_tasks = load_platform_tasks()
    tasks = [t for t in all_tasks if t.workflow == "rna_aptamer_design"]
    print(f"Found {len(tasks)} RNA aptamer design tasks")
    
    executor = build_default_tool_registry(include_demo=False)
    tool_executor = ToolExecutor(executor)
    cap_reg = build_default_capability_registry(tool_executor)
    
    results = []
    for idx, task in enumerate(tasks, 1):
        print(f"\n[{idx}/{len(tasks)}] Running {task.task_id} ...")
        task_start = time.perf_counter()
        
        try:
            inp = RnaAptamerDesignInput(**task.input)
            wf = RnaAptamerDesignWorkflow(cap_reg)
            result = wf.run(inp)
            elapsed = time.perf_counter() - task_start
            
            record = {
                "task_id": task.task_id,
                "success": result.success,
                "errors": result.errors or [],
                "elapsed_seconds": round(elapsed, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> success={result.success}, elapsed={elapsed:.1f}s")
            if result.errors:
                print(f"  -> errors: {result.errors[:3]}")
        except Exception as exc:
            elapsed = time.perf_counter() - task_start
            record = {
                "task_id": task.task_id,
                "success": False,
                "errors": [str(exc), traceback.format_exc()],
                "elapsed_seconds": round(elapsed, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> EXCEPTION: {exc}")
        
        results.append(record)
        with open(RESULTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"\n{'='*60}")
    print(f"Completed {len(results)} tasks")
    print(f"Success: {success_count}/{len(results)} = {100*success_count/len(results):.1f}%")
    print(f"Results saved to: {RESULTS_FILE}")

if __name__ == "__main__":
    main()
