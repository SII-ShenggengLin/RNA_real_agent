#!/usr/bin/env python3
"""Real-data end-to-end test for RnaTertiaryStructureDesignWorkflow trace audit."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.capabilities.base import CapabilityRegistry
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignWorkflow,
    RnaTertiaryStructureDesignInput,
)


def main():
    pdb_path = "/tmp/1ehz.pdb"
    if not Path(pdb_path).exists():
        print(f"ERROR: PDB file not found at {pdb_path}")
        sys.exit(1)

    print("=" * 60)
    print("RNA Tertiary Structure Design – Real Data Trace Test")
    print("=" * 60)
    print(f"Input PDB: {pdb_path}")

    # Build registry & workflow
    registry = build_default_tool_registry()
    executor = ToolExecutor(registry)
    cap_registry = CapabilityRegistry(executor)
    for name in registry.list_names():
        cap_registry.register(name)

    wf = RnaTertiaryStructureDesignWorkflow(cap_registry)

    inp = RnaTertiaryStructureDesignInput(
        structure_filepath=pdb_path,
        design_tools="ribodiffusion",  # Use ribodiffusion (RhoDesign has issues with 1ehz)
        n_samples_per_tool=2,
        ribodiffusion_sampling_steps=50,
    )

    print(f"Design tools: {inp.design_tools}")
    print(f"Samples per tool: {inp.n_samples_per_tool}")
    print(f"RiboDiffusion sampling steps: {inp.ribodiffusion_sampling_steps}")
    print("-" * 60)

    started = time.time()
    result = wf.run(inp)
    elapsed = time.time() - started

    print(f"\nWorkflow completed in {elapsed:.1f}s")
    print(f"Success: {result.success}")
    print(f"Task ID: {result.task_id}")
    print(f"Candidates: {len(result.all_candidates)}")
    print(f"Errors: {result.errors}")
    if result.best_candidate:
        bc = result.best_candidate
        print(f"\nBest candidate:")
        print(f"  Source: {bc.source}")
        print(f"  Length: {len(bc.sequence)} nt")
        print(f"  Scores: {bc.scores}")
        mb = bc.metadata.get("metrics_bundle", {})
        print(f"  GC: {mb.get('gc_content')}")
        print(f"  MFE: {mb.get('vienna_mfe')}")
        print(f"  RhoFold pLDDT: {mb.get('rhofold_mean_plddt')}")
        print(f"  RMSD: {mb.get('alignment_rmsd')}")
        print(f"  TM-score: {mb.get('alignment_tm_score')}")

    # ── Trace audit verification ──
    print("\n" + "=" * 60)
    print("TRACE AUDIT REPORT")
    print("=" * 60)

    print(f"\nTotal trace records in WorkflowResult: {len(result.trace)}")
    for i, rec in enumerate(result.trace, 1):
        print(f"  [{i}] step={rec.step_name} tool={rec.tool_name} success={rec.success} elapsed={rec.elapsed_time:.2f}s")

    # Categorize
    workflow_level = [r for r in result.trace if r.step_name.startswith("generate_")]
    candidate_level = [r for r in result.trace if not r.step_name.startswith("generate_")]

    print(f"\n  Workflow-level records (generation): {len(workflow_level)}")
    for r in workflow_level:
        print(f"    - {r.tool_name}: success={r.success}")

    print(f"\n  Candidate-level records (evaluation): {len(candidate_level)}")
    for r in candidate_level:
        print(f"    - {r.step_name}: tool={r.tool_name} success={r.success}")

    # Verify expected tools were traced
    # Generation tools depend on input; evaluation tools should always be traced when candidates exist
    expected_eval_tools = {
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure",
        "predict_rna_tertiary_structure_with_rhofold",
        "score_structure_alignment",
    }
    actual_tools = {r.tool_name for r in result.trace}
    missing_eval = expected_eval_tools - actual_tools
    if missing_eval:
        print(f"\n  WARNING: Missing expected evaluation tool traces: {missing_eval}")
    else:
        print(f"\n  All expected evaluation tools traced.")

    has_generation = any(
        r.tool_name in ("design_rna_sequence_with_rhodesign", "design_rna_inverse_fold_with_ribodiffusion")
        for r in result.trace
    )
    if not has_generation:
        print("  WARNING: No generation tool trace found.")

    # Per-candidate audit
    print("\n" + "-" * 60)
    print("PER-CANDIDATE TOOL RECORDS")
    print("-" * 60)
    for c in result.all_candidates:
        print(f"\n  Candidate {c.id} (source={c.source}):")
        print(f"    Tool records: {len(c.tool_records)}")
        for r in c.tool_records:
            print(f"      - {r.step_name}: {r.tool_name} success={r.success}")

    # Persist result for inspection
    out_path = Path("workspace/test_tertiary_real_trace_result.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": result.task_id,
        "success": result.success,
        "trace_count": len(result.trace),
        "trace": [rec.model_dump(mode="json") for rec in result.trace],
        "candidates": [
            {
                "id": c.id,
                "source": c.source,
                "sequence_len": len(c.sequence),
                "tool_records_count": len(c.tool_records),
                "tool_records": [rec.model_dump(mode="json") for rec in c.tool_records],
            }
            for c in result.all_candidates
        ],
        "elapsed_seconds": elapsed,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetailed trace written to: {out_path}")

    # Final verdict
    print("\n" + "=" * 60)
    verdict_pass = (
        result.success
        and len(result.trace) > 0
        and has_generation
        and not missing_eval
    )
    if verdict_pass:
        print("VERDICT: PASS – Full-chain structured trace is working with real data.")
    else:
        print("VERDICT: FAIL – Trace is incomplete or workflow failed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
