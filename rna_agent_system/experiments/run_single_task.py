#!/usr/bin/env python3
"""Run a single platform coverage task and print JSON result to stdout."""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks, PlatformTask
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from experiments.run_platform_coverage import _check_tool_correctness
import os

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


def _build_executor() -> ToolExecutor:
    reg = build_default_tool_registry(include_demo=False)
    return ToolExecutor(reg)


def _build_capability_registry(executor: ToolExecutor):
    return build_default_capability_registry(executor)


def _extract_invoked_tools(result) -> Set[str]:
    """Extract all tool names that were actually invoked across all trace sources."""
    invoked: Set[str] = set()

    # Source 1: direct trace (ToolCallRecord list)
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

    # Source 3: candidate metadata and tool_records
    for cand in (result.all_candidates or []):
        meta = getattr(cand, "metadata", None) or {}
        if isinstance(meta, dict):
            src = meta.get("source", "")
            if isinstance(src, str):
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
        # Direct tool_records on candidate
        tool_records = getattr(cand, "tool_records", None) or []
        for rec in tool_records:
            tool_name = getattr(rec, "tool_name", None)
            if tool_name:
                invoked.add(tool_name)

    return invoked


def _classify_trace_completeness(result, expected_chain: List[str]) -> Dict[str, Any]:
    """Classify trace completeness for observability (Panel e).

    Returns dict with:
        - trace_length: total number of recorded tool steps
        - trace_completeness: "complete" | "partial" | "none"
        - recorded_tools: list of recorded tool names
        - expected_tools: list of expected tool names
    """
    invoked = _extract_invoked_tools(result)

    # Best-effort match: expected tool names may be shorter aliases
    matched = set()
    for exp in expected_chain:
        if any(exp in inv or inv in exp for inv in invoked):
            matched.add(exp)

    if not invoked:
        trace_completeness = "none"
    elif len(matched) >= len(expected_chain):
        trace_completeness = "complete"
    elif len(matched) > 0:
        trace_completeness = "partial"
    else:
        trace_completeness = "none"

    return {
        "trace_length": len(result.trace) if result.trace else len(invoked),
        "trace_completeness": trace_completeness,
        "recorded_tools": sorted(invoked),
        "expected_tools": expected_chain,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_single_task.py <task_id>", file=sys.stderr)
        sys.exit(1)

    task_id = sys.argv[1]
    tasks = load_platform_tasks()
    task = next((t for t in tasks if t.task_id == task_id), None)
    if task is None:
        print(json.dumps({"error": f"Task {task_id} not found"}))
        sys.exit(1)

    executor = _build_executor()
    cap_reg = _build_capability_registry(executor)

    workflow = task.workflow
    inp_dict = task.input
    result = None
    task_start = time.perf_counter()

    try:
        if workflow == "mrna_cds_design":
            inp_obj = MrnaCdsDesignInput(**inp_dict)
            wf_instance = MrnaCdsDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "full_length_mrna_design":
            inp_obj = FullLengthMrnaDesignInput(**inp_dict)
            wf_instance = FullLengthMrnaDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "mrna_sequence_scoring":
            inp_obj = MrnaSequenceScoringInput(**inp_dict)
            result = run_mrna_sequence_scoring(inp_obj, executor=executor, task_id=task.task_id)
        elif workflow == "sirna_design":
            inp_obj = SirnaDesignInput(**inp_dict)
            wf_instance = SirnaDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "sgrna_design":
            inp_obj = SgRnaDesignInput(**inp_dict)
            wf_instance = SgRnaDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "rna_secondary_structure_design":
            inp_obj = RnaSecondaryStructureDesignInput(**inp_dict)
            wf_instance = RnaSecondaryStructureDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "rna_tertiary_structure_design":
            inp_obj = RnaTertiaryStructureDesignInput(**inp_dict)
            wf_instance = RnaTertiaryStructureDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "rna_aptamer_design":
            inp_obj = RnaAptamerDesignInput(**inp_dict)
            wf_instance = RnaAptamerDesignWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "rna_small_molecule_interaction":
            inp_obj = RnaSmallMoleculeInteractionInput(**inp_dict)
            wf_instance = RnaSmallMoleculeInteractionWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "aso_target_screening":
            inp_obj = AsoScreeningInput(**inp_dict)
            wf_instance = AsoTargetScreeningWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        elif workflow == "ires_prediction":
            inp_obj = IresPredictionInput(**inp_dict)
            wf_instance = IresPredictionWorkflow(cap_reg)
            result = wf_instance.run(inp_obj)
        else:
            raise ValueError(f"Unknown workflow: {workflow}")

        elapsed = time.perf_counter() - task_start
        tc = _check_tool_correctness(result, task.expected_tool_chain)
        tr = _classify_trace_completeness(result, task.expected_tool_chain)
        record = {
            "task_id": task.task_id,
            "workflow": workflow,
            "category": task.category,
            "success": result.success,
            "errors": result.errors or [],
            "elapsed_seconds": round(elapsed, 3),
            "tool_correctness": tc["correct"],
            "tool_missing": tc["missing"],
            "trace_length": tr["trace_length"],
            "trace_completeness": tr["trace_completeness"],
            "recorded_tools": tr["recorded_tools"],
            "expected_tools": tr["expected_tools"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - task_start
        record = {
            "task_id": task.task_id,
            "workflow": workflow,
            "category": task.category,
            "success": False,
            "errors": [str(exc), traceback.format_exc()],
            "elapsed_seconds": round(elapsed, 3),
            "tool_correctness": False,
            "tool_missing": task.expected_tool_chain,
            "trace_length": 0,
            "trace_completeness": "none",
            "recorded_tools": [],
            "expected_tools": task.expected_tool_chain,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
