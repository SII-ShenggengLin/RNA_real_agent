"""
Real-data trace test for FullLengthMrnaDesignWorkflow.
Bypasses LLM planner (avoids API issues) and directly invokes the real workflow
through ExecutionController with real external services.
"""

import json
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Load benchmark task PA_019
# ---------------------------------------------------------------------------
BENCH_PATH = Path(__file__).parent / "data" / "benchmarks" / "RNA-BioBench-ProcessAware" / "task_set_for_llm_comparison.json"
with open(BENCH_PATH) as f:
    bench = json.load(f)

task = next(t for t in bench["tasks"] if t["task_id"] == "PA_019")
user_query = task["user_query"]
print(f"Task: {task['task_id']} → {task['workflow']}")
print(f"Query: {user_query}\n")

# ---------------------------------------------------------------------------
# 1. Build real AgentRunner / ExecutionController
# ---------------------------------------------------------------------------
from agent_core.planning.base import ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.session_memory import SessionMemory

runner = AgentRunner(
    planner=None,  # not needed — we build the plan manually
    executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    session_memory=SessionMemory(),
    llm_critic_enabled=True,
)

# ---------------------------------------------------------------------------
# 2. Prepare state (records user input)
# ---------------------------------------------------------------------------
state = runner._prepare_state(user_query, session_id="real_trace_direct_001", explicit_state=None)

# Inject routing decision manually (simulating deterministic match)
state["_routing_method"] = "deterministic"
state["_execution_plan"] = {
    "steps": [
        {
            "step_id": "step_1",
            "type": "workflow",
            "target": "full_length_mrna_design",
            "input_binding": {},
            "output_key": "workflow_result",
            "description": "Deterministic routing: full_length_mrna_design",
        }
    ],
    "max_retries": 2,
    "fallback_on_error": "retry_with_alternative",
}

# ---------------------------------------------------------------------------
# 3. Build plan manually with real protein sequence
# ---------------------------------------------------------------------------
# GFP full-length sequence (238 aa) — using real benchmark intent
GFP_SEQ = (
    "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTLSYGVQCFSRY"
    "PDHMKQHDFFKSAMPEGYVQERTISFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHN"
    "VYITADKQKNGIKANFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK"
)

plan = ExecutionPlan(
    steps=[
        PlanStep(
            step_id="step_1",
            type="workflow",
            target="full_length_mrna_design",
            input_binding={
                "protein_sequence": GFP_SEQ,
                "lambda_value": 4.0,
                "utr_mode": "long",
                "design_tool": "lineardesign",
            },
            output_key="workflow_result",
            description="Design full-length mRNA for GFP (benchmark PA_019)",
        )
    ],
    max_retries=2,
    fallback_on_error="retry_with_alternative",
)

print("=== Plan ===")
print(f"Target: {plan.steps[0].target}")
print(f"Input keys: {list(plan.steps[0].input_binding.keys())}")
print(f"Protein length: {len(GFP_SEQ)} aa\n")

# ---------------------------------------------------------------------------
# 4. Execute with real services
# ---------------------------------------------------------------------------
print("=== Executing real workflow (may take 1–3 min) ===\n")
start = time.time()

try:
    final_state = runner.controller.execute(plan, state, persist_run=False)
    final_state["final_report"] = runner._format_final_report(final_state)
    success = True
except Exception as exc:
    final_state = state  # state was mutated up to the point of failure
    final_state["final_report"] = f"Execution failed: {type(exc).__name__}: {exc}"
    success = False
    print(f"Workflow failed: {type(exc).__name__}: {exc}\n")

elapsed = time.time() - start
print(f"Completed in {elapsed:.1f}s (success={success})\n")

# ---------------------------------------------------------------------------
# 5. Verify & dump trace
# ---------------------------------------------------------------------------
log = final_state.get("_execution_log", [])
print(f"=== _execution_log ({len(log)} events) ===")
for entry in log:
    ev = entry.get("event")
    if ev in ("step_start", "step_done", "step_error"):
        print(
            f"  {ev:12s} target={entry.get('target', ''):30s} "
            f"ts={entry.get('timestamp', 'N/A')} "
            f"elapsed={entry.get('elapsed_ms', 'N/A')}ms "
            f"error={entry.get('error_type', '')}"
        )
    else:
        print(f"  {ev:12s} {entry}")

print("\n=== State Trace Fields ===")
print(f"_routing_method        : {final_state.get('_routing_method')}")
print(f"_all_workflow_params   : {list(final_state.get('_all_workflow_params', {}).keys())}")
print(f"_bmc_trace rounds      : {len(final_state.get('_bmc_trace', []))}")
print(f"_diagnosis_history     : {len(final_state.get('_diagnosis_history', []))}")
print(f"retry_count            : {final_state.get('retry_count', 0)}")

wf = final_state.get("workflow_result")
if wf is not None:
    print(f"\nworkflow_result")
    print(f"  success         : {wf.success}")
    print(f"  task_id         : {wf.task_id}")
    print(f"  candidates      : {len(wf.all_candidates)}")
    print(f"  summary         : {wf.summary[:120] if wf.summary else ''}")
    if wf.all_candidates:
        best = wf.best_candidate
        print(f"  best source     : {best.source if best else 'N/A'}")
        print(f"  best scores     : {best.scores if best else 'N/A'}")
        print(f"  best seq len    : {len(best.sequence) if best else 0}")
else:
    print("\nworkflow_result: None")

# Persist trace for inspection
trace_file = Path("workspace/real_trace_direct.json")
trace_payload = {
    "task_id": task["task_id"],
    "user_query": user_query,
    "routing_method": final_state.get("_routing_method"),
    "_execution_log": final_state.get("_execution_log", []),
    "_all_workflow_params": final_state.get("_all_workflow_params"),
    "_bmc_trace": final_state.get("_bmc_trace"),
    "_diagnosis_history": final_state.get("_diagnosis_history"),
    "workflow_result": {
        "success": wf.success if wf else None,
        "task_id": wf.task_id if wf else None,
        "candidate_count": len(wf.all_candidates) if wf else 0,
        "summary": wf.summary if wf else None,
    } if wf else None,
    "final_report_preview": final_state.get("final_report", "")[:500],
}
with open(trace_file, "w") as f:
    json.dump(trace_payload, f, ensure_ascii=False, indent=2, default=str)

print(f"\nTrace saved to: {trace_file}")
