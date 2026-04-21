#!/usr/bin/env python3
"""Minimal runnable demo: save a test sequence, run workflow RNA GC tool, optional Candidate trace.

Requires ``rna_sequence_metrics_service`` on port 8020 (see microservices/rna_sequence_metrics_service).

Usage from repo root::
    python rna_agent_system/examples/workflow_gc_content_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import Candidate, TaskState
from agent_core.workflow_tools import create_workflow_rna_gc_content_tool


def main() -> int:
    rel_path = save_sequence("AUGCAU" * 20, prefix="demo_gc")
    registry = ToolRegistry()
    create_wf = create_workflow_rna_gc_content_tool()
    registry.register(create_wf)
    executor = ToolExecutor(registry)

    task = TaskState(task_type="demo_gc", input_payload={"note": "workflow_gc_content_demo"})
    candidate = Candidate(sequence="(from file)", sequence_type="mrna", source="demo")

    result = executor.run_tool_for_workflow(
        "workflow_rna_gc_content",
        task=task,
        candidate=candidate,
        step_name="gc_content",
        filepath=rel_path,
    )
    print("success:", result.success)
    print("metrics:", result.metrics)
    print("artifacts keys:", list(result.artifacts.keys()))
    if result.error:
        print("error:", result.error)
    print("candidate tool_records:", len(candidate.tool_records))
    print("task logs:", len(task.logs))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
