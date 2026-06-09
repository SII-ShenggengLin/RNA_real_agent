#!/usr/bin/env python3
"""
Platform Coverage Experiment Runner — Multiprocessing version.

Uses multiprocessing for reliable per-task timeout (ThreadPoolExecutor
 cannot interrupt blocking system calls such as socket I/O).

Outputs:
    rna_agent_system/experiments/results/platform_coverage.jsonl

Usage:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_platform_coverage_mp.py
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks, PlatformTask
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from experiments.run_platform_coverage import _check_tool_correctness

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = RESULTS_DIR / "platform_coverage.jsonl"

TASK_TIMEOUT = 7200  # seconds per task (2h; matches run_platform_coverage.py)


def _build_executor() -> ToolExecutor:
    reg = build_default_tool_registry(include_demo=False)
    return ToolExecutor(reg)


def _build_capability_registry(executor: ToolExecutor):
    return build_default_capability_registry(executor)


def _run_task_worker(task_dict: dict[str, Any]) -> dict[str, Any]:
    """Worker function that runs inside a separate process."""
    # Rebuild everything inside the child process
    from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
    from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignInput, FullLengthMrnaDesignWorkflow
    from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringInput, MrnaSequenceScoringWorkflow, run_mrna_sequence_scoring
    from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow
    from agent_core.workflows.sgrna_design import SgRnaDesignInput, SgRnaDesignWorkflow
    from agent_core.workflows.rna_secondary_structure_design import RnaSecondaryStructureDesignInput, RnaSecondaryStructureDesignWorkflow
    from agent_core.workflows.rna_tertiary_structure_design import RnaTertiaryStructureDesignInput, RnaTertiaryStructureDesignWorkflow
    from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow
    from agent_core.workflows.rna_small_molecule_interaction import RnaSmallMoleculeInteractionInput, RnaSmallMoleculeInteractionWorkflow
    from agent_core.workflows.aso_target_screening import AsoScreeningInput, AsoTargetScreeningWorkflow
    from agent_core.workflows.ires_prediction import IresPredictionInput, IresPredictionWorkflow

    executor = _build_executor()
    cap_reg = _build_capability_registry(executor)

    task = PlatformTask(**task_dict)
    workflow = task.workflow
    inp_dict = task.input

    wf_instance = None
    inp_obj = None

    try:
        if workflow == "mrna_cds_design":
            inp_obj = MrnaCdsDesignInput(**inp_dict)
            wf_instance = MrnaCdsDesignWorkflow(cap_reg)
        elif workflow == "full_length_mrna_design":
            inp_obj = FullLengthMrnaDesignInput(**inp_dict)
            wf_instance = FullLengthMrnaDesignWorkflow(cap_reg)
        elif workflow == "mrna_sequence_scoring":
            inp_obj = MrnaSequenceScoringInput(**inp_dict)
            result = run_mrna_sequence_scoring(inp_obj, executor=executor, task_id=task.task_id)
            tc = _check_tool_correctness(result, task.expected_tool_chain)
            return {
                "task_id": task.task_id,
                "workflow": workflow,
                "category": task.category,
                "success": result.success,
                "errors": result.errors or [],
                "elapsed_seconds": 0.0,
                "tool_correctness": tc["correct"],
                "tool_missing": tc["missing"],
                "trace_length": len(result.trace) if result.trace else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        elif workflow == "sirna_design":
            inp_obj = SirnaDesignInput(**inp_dict)
            wf_instance = SirnaDesignWorkflow(cap_reg)
        elif workflow == "sgrna_design":
            inp_obj = SgRnaDesignInput(**inp_dict)
            wf_instance = SgRnaDesignWorkflow(cap_reg)
        elif workflow == "rna_secondary_structure_design":
            inp_obj = RnaSecondaryStructureDesignInput(**inp_dict)
            wf_instance = RnaSecondaryStructureDesignWorkflow(cap_reg)
        elif workflow == "rna_tertiary_structure_design":
            inp_obj = RnaTertiaryStructureDesignInput(**inp_dict)
            wf_instance = RnaTertiaryStructureDesignWorkflow(cap_reg)
        elif workflow == "rna_aptamer_design":
            inp_obj = RnaAptamerDesignInput(**inp_dict)
            wf_instance = RnaAptamerDesignWorkflow(cap_reg)
        elif workflow == "rna_small_molecule_interaction":
            inp_obj = RnaSmallMoleculeInteractionInput(**inp_dict)
            wf_instance = RnaSmallMoleculeInteractionWorkflow(cap_reg)
        elif workflow == "aso_target_screening":
            inp_obj = AsoScreeningInput(**inp_dict)
            wf_instance = AsoTargetScreeningWorkflow(cap_reg)
        elif workflow == "ires_prediction":
            inp_obj = IresPredictionInput(**inp_dict)
            wf_instance = IresPredictionWorkflow(cap_reg)
        else:
            raise ValueError(f"Unknown workflow: {workflow}")

        task_start = time.perf_counter()
        result = wf_instance.run(inp_obj)
        elapsed = time.perf_counter() - task_start
        tc = _check_tool_correctness(result, task.expected_tool_chain)

        return {
            "task_id": task.task_id,
            "workflow": workflow,
            "category": task.category,
            "success": result.success,
            "errors": result.errors or [],
            "elapsed_seconds": round(elapsed, 3),
            "tool_correctness": tc["correct"],
            "tool_missing": tc["missing"],
            "trace_length": len(result.trace) if result.trace else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "task_id": task.task_id,
            "workflow": workflow,
            "category": task.category,
            "success": False,
            "errors": [str(exc), traceback.format_exc()],
            "elapsed_seconds": 0.0,
            "tool_correctness": False,
            "tool_missing": task.expected_tool_chain,
            "trace_length": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def main():
    print("=" * 60)
    print("RNA-BioBench-Platform Coverage Runner (multiprocessing)")
    print("=" * 60)

    tasks = load_platform_tasks()
    print(f"Loaded {len(tasks)} benchmark tasks")

    wf_counts = Counter(t.workflow for t in tasks)
    for wf, cnt in sorted(wf_counts.items()):
        print(f"  {wf}: {cnt}")

    # Convert tasks to plain dicts for pickling
    task_dicts = [
        {
            "task_id": t.task_id,
            "workflow": t.workflow,
            "category": t.category,
            "description": t.description,
            "input": t.input,
            "expected_tool_chain": t.expected_tool_chain,
            "evaluation_rubric": t.evaluation_rubric,
            "source": t.source,
            "paper_reference": t.paper_reference,
        }
        for t in tasks
    ]

    results: List[Dict[str, Any]] = []
    start_global = time.perf_counter()

    for idx, td in enumerate(task_dicts, 1):
        print(f"\n[{idx}/{len(task_dicts)}] {td['task_id']} ({td['workflow']} / {td['category']})")
        task_start = time.perf_counter()

        proc = mp.Process(target=_run_task_worker, args=(td,))
        proc.start()
        proc.join(timeout=TASK_TIMEOUT)

        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            if proc.is_alive():
                proc.kill()
                proc.join()

            elapsed = time.perf_counter() - task_start
            record = {
                "task_id": td["task_id"],
                "workflow": td["workflow"],
                "category": td["category"],
                "success": False,
                "errors": [f"timeout_after_{TASK_TIMEOUT}s"],
                "elapsed_seconds": round(elapsed, 3),
                "tool_correctness": False,
                "tool_missing": td["expected_tool_chain"],
                "trace_length": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  -> TIMEOUT after {TASK_TIMEOUT}s")
        else:
            elapsed = time.perf_counter() - task_start
            # Child exited; exit code 0 means success, anything else means exception
            if proc.exitcode == 0:
                # Unfortunately we can't get the return value from a Process easily
                # without Queue/Pipe.  For simplicity, re-run in main thread for
                # tasks that clearly finished quickly (elapsed < timeout).
                if elapsed < TASK_TIMEOUT - 1:
                    record = _run_task_worker(td)
                    record["elapsed_seconds"] = round(elapsed, 3)
                    print(f"  -> success={record['success']}, elapsed={elapsed:.2f}s, tool_correct={record['tool_correctness']}")
                    if record["errors"]:
                        print(f"  -> errors: {record['errors'][:3]}")
                else:
                    record = {
                        "task_id": td["task_id"],
                        "workflow": td["workflow"],
                        "category": td["category"],
                        "success": False,
                        "errors": [f"timeout_after_{TASK_TIMEOUT}s"],
                        "elapsed_seconds": round(elapsed, 3),
                        "tool_correctness": False,
                        "tool_missing": td["expected_tool_chain"],
                        "trace_length": 0,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    print(f"  -> TIMEOUT after ~{TASK_TIMEOUT}s")
            else:
                record = {
                    "task_id": td["task_id"],
                    "workflow": td["workflow"],
                    "category": td["category"],
                    "success": False,
                    "errors": [f"worker_crash_exitcode_{proc.exitcode}"],
                    "elapsed_seconds": round(elapsed, 3),
                    "tool_correctness": False,
                    "tool_missing": td["expected_tool_chain"],
                    "trace_length": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                print(f"  -> WORKER CRASH (exitcode={proc.exitcode})")

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
    mp.set_start_method("spawn", force=True)
    main()
