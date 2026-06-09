#!/usr/bin/env python3
"""Smoke test: validate all aptamer tasks can reach candidate generation stage."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.benchmarks.rna_biobench_loader import load_platform_tasks
from agent_core.tool_executor import build_default_tool_registry, ToolExecutor
from agent_core.capabilities.base import build_default_capability_registry
from agent_core.workflows.rna_aptamer_design import RnaAptamerDesignInput, RnaAptamerDesignWorkflow

def main():
    all_tasks = load_platform_tasks()
    tasks = [t for t in all_tasks if t.workflow == "rna_aptamer_design"]
    print(f"Found {len(tasks)} RNA aptamer design tasks\n")
    
    executor = build_default_tool_registry(include_demo=False)
    tool_executor = ToolExecutor(executor)
    cap_reg = build_default_capability_registry(tool_executor)
    
    results = []
    for idx, task in enumerate(tasks, 1):
        errors = []
        stage = "init"
        try:
            inp = RnaAptamerDesignInput(**task.input)
            stage = "input_validation"
            
            wf = RnaAptamerDesignWorkflow(cap_reg)
            stage = "workflow_creation"
            
            # Try to prepare target (structure + hotspot) - CPU-only, relatively fast
            protein_path, hotspot, protein_seq_len = wf._prepare_target_module(inp)
            stage = "target_preparation"
            
            if not protein_path:
                errors.append("protein_structure_resolution_failed")
            if not hotspot:
                errors.append("hotspot_identification_failed")
            
            # Try to build ODesign input JSON - CPU-only, fast
            if protein_path and hotspot and protein_seq_len:
                json_result = wf._build_odesign_json(
                    protein_path=protein_path,
                    chain_id=inp.chain_id,
                    seq_len=protein_seq_len,
                    hotspot=hotspot,
                    aptamer_length=inp.aptamer_length,
                )
                stage = "odesign_json_build"
                if not json_result:
                    errors.append("odesign_json_build_failed")
            
            results.append({
                "task_id": task.task_id,
                "success": len(errors) == 0,
                "stage": stage,
                "errors": errors,
                "protein_path": protein_path,
                "hotspot": hotspot,
            })
            status = "PASS" if len(errors) == 0 else "FAIL"
            print(f"[{idx:2d}/{len(tasks)}] {task.task_id}: {status} (stage={stage})")
            if errors:
                print(f"         errors: {errors}")
                
        except Exception as exc:
            results.append({
                "task_id": task.task_id,
                "success": False,
                "stage": stage,
                "errors": [str(exc)],
                "protein_path": None,
                "hotspot": None,
            })
            print(f"[{idx:2d}/{len(tasks)}] {task.task_id}: FAIL (stage={stage})")
            print(f"         exception: {exc}")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"\n{'='*60}")
    print(f"Smoke test complete: {success_count}/{len(results)} passed")
    
    # Save results
    out_file = PROJECT_ROOT / "experiments" / "results" / "aptamer_smoke_test.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results saved to: {out_file}")

if __name__ == "__main__":
    main()
