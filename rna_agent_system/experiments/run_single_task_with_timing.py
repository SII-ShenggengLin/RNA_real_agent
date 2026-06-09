#!/usr/bin/env python3
"""Run a single full_length_mrna_design task with detailed per-phase timing."""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignInput,
    FullLengthMrnaDesignWorkflow,
)


def _build_executor() -> ToolExecutor:
    reg = build_default_tool_registry(include_demo=False)
    return ToolExecutor(reg)


def _build_capability_registry(executor: ToolExecutor):
    return build_default_capability_registry(executor)


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_single_task_with_timing.py <task_id>", file=sys.stderr)
        sys.exit(1)

    task_id = sys.argv[1]
    tasks = load_platform_tasks()
    task = next((t for t in tasks if t.task_id == task_id), None)
    if task is None:
        print(json.dumps({"error": f"Task {task_id} not found"}))
        sys.exit(1)

    executor = _build_executor()
    cap_reg = _build_capability_registry(executor)

    inp_dict = task.input
    inp_obj = FullLengthMrnaDesignInput(**inp_dict)
    wf_instance = FullLengthMrnaDesignWorkflow(cap_reg)

    timing: Dict[str, Any] = {}
    overall_start = time.perf_counter()

    # Phase 1: generate candidates
    t0 = time.perf_counter()
    try:
        candidates = wf_instance.generate_candidates(inp_obj)
    except Exception as exc:
        timing["generate_candidates_error"] = str(exc)
        candidates = []
    t1 = time.perf_counter()
    timing["generate_candidates_seconds"] = round(t1 - t0, 3)
    timing["num_candidates"] = len(candidates)

    # Phase 2: evaluate each candidate
    evaluate_times = []
    for i, cand in enumerate(candidates):
        t0 = time.perf_counter()
        try:
            metrics = wf_instance.evaluate(cand)
        except Exception as exc:
            evaluate_times.append({"index": i, "candidate_id": cand.id, "error": str(exc), "seconds": round(time.perf_counter() - t0, 3)})
            continue
        t1 = time.perf_counter()
        evaluate_times.append({
            "index": i,
            "candidate_id": cand.id,
            "seconds": round(t1 - t0, 3),
            "total_length": len(cand.sequence),
            "source": cand.source,
        })
    timing["evaluate_per_candidate"] = evaluate_times
    timing["evaluate_total_seconds"] = round(sum(e["seconds"] for e in evaluate_times if "error" not in e), 3)

    # Phase 3: score each candidate
    t0 = time.perf_counter()
    for cand in candidates:
        if "metrics_bundle" in cand.metadata:
            cand.scores = wf_instance.score(cand.metadata["metrics_bundle"])
            cand.status = "evaluated"
    t1 = time.perf_counter()
    timing["score_seconds"] = round(t1 - t0, 3)

    # Phase 4: rank
    t0 = time.perf_counter()
    result = wf_instance.rank_and_format(candidates)
    t1 = time.perf_counter()
    timing["rank_and_format_seconds"] = round(t1 - t0, 3)

    overall_elapsed = time.perf_counter() - overall_start
    timing["overall_seconds"] = round(overall_elapsed, 3)
    timing["success"] = result.success
    timing["errors"] = result.errors or []
    timing["timestamp"] = datetime.now(timezone.utc).isoformat()

    if result.best_candidate:
        best = result.best_candidate
        timing["best_candidate"] = {
            "id": best.id,
            "source": best.source,
            "total_length": len(best.sequence) if best.sequence else 0,
            "scores": best.scores,
        }

    print(json.dumps(timing, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
