#!/usr/bin/env python3
"""Debug script: run rna_aptamer_design task 002 directly with verbose logging."""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

from data.benchmarks.rna_biobench_loader import load_platform_tasks
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow

print("Loading tasks...")
tasks = load_platform_tasks()
task = next((t for t in tasks if t.task_id == '08_rna_aptamer_design_002_nucleocapsid'), None)
if not task:
    print("Task not found!")
    sys.exit(1)

print(f"Task: {task.task_id}")
print(f"Input: {json.dumps(task.input, indent=2)}")

print("\nBuilding executor...")
executor = build_default_tool_registry(include_demo=False)
tool_exec = ToolExecutor(executor)

print("Building capability registry...")
cap_reg = build_default_capability_registry(tool_exec)

print("\nCreating input object...")
inp_obj = RnaAptamerDesignInput(**task.input)

print("Creating workflow...")
wf = RnaAptamerDesignWorkflow(cap_reg)

print("\nRunning workflow...")
try:
    result = wf.run(inp_obj)
    print(f"\n=== RESULT ===")
    print(f"success: {result.success}")
    print(f"errors: {result.errors}")
    print(f"candidates: {len(result.all_candidates)}")
    for i, cand in enumerate(result.all_candidates):
        print(f"  Candidate {i}: {cand.sequence[:50]}...")
except Exception as e:
    print(f"\n=== EXCEPTION ===")
    import traceback
    traceback.print_exc()
