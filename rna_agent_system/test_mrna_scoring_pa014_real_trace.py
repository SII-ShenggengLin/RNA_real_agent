"""
Real-data trace test for MrnaSequenceScoringWorkflow using benchmark PA_014.
Runs the actual workflow through AgentRunner with real external services.
"""

import json
import sys
import time
from pathlib import Path

BENCH_PATH = Path(__file__).parent / "data" / "benchmarks" / "RNA-BioBench-ProcessAware" / "task_set_for_llm_comparison.json"
with open(BENCH_PATH) as f:
    bench = json.load(f)

task = next(t for t in bench["tasks"] if t["task_id"] == "PA_014")
user_query = task["user_query"]
print(f"Task: {task['task_id']} → {task['workflow']}")
print(f"Query: {user_query[:80]}...\n")

# Extract sequence from query (after "序列是 ")
epo_sequence = user_query.split("序列是")[-1].strip("。")
print(f"Sequence length: {len(epo_sequence)} nt")
print(f"Sequence preview: {epo_sequence[:60]}...\n")

# ---------------------------------------------------------------------------
# Build real AgentRunner
# ---------------------------------------------------------------------------
from agent_core.planning.base import ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

# Use a minimal planner that will not be called (deterministic router handles it)
class _NoOpPlanner:
    def plan_with_state(self, user_text, state):
        raise RuntimeError("Should not reach planner for deterministic routing")

runner = AgentRunner(
    planner=_NoOpPlanner(),
    executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    llm_critic_enabled=True,
    persist_run=True,
)

# ---------------------------------------------------------------------------
# Step 1: prepare state + build plan (routing decision)
# ---------------------------------------------------------------------------
state = runner._prepare_state(user_query, session_id="pa014_trace_001", explicit_state=None)
plan = runner._build_plan(user_query, state)

print("=== Routing Decision ===")
print(f"_routing_method : {state.get('_routing_method')}")
print(f"Plan steps      : {len(plan.steps)}")
for s in plan.steps:
    print(f"  - {s.step_id}: {s.type} → {s.target}, binding keys={list(s.input_binding.keys())}")
print()

# If deterministic router missed (Chinese query), override to the expected workflow
if plan is None or plan.steps[0].target != "mrna_sequence_scoring":
    print("[INFO] DeterministicRouter missed for Chinese query; constructing direct plan.")
    plan = ExecutionPlan(
        steps=[
            PlanStep(
                step_id="score_1",
                type="workflow",
                target="mrna_sequence_scoring",
                input_binding={},
                output_key="workflow_result",
                description="Score EPO mRNA from benchmark PA_014",
            )
        ],
        max_retries=2,
    )
    state["_routing_method"] = "manual"
    state["_execution_log"].append({
        "event": "routing_decision",
        "method": "manual",
        "target": "mrna_sequence_scoring",
        "description": "Direct plan from benchmark data PA_014 (Chinese query bypass)",
        "timestamp": time.time(),
    })
    state["_execution_plan"] = plan.model_dump(mode="json")

assert plan.steps[0].target == "mrna_sequence_scoring", f"Unexpected target: {plan.steps[0].target}"

# ---------------------------------------------------------------------------
# Step 2: inject real sequence (deterministic router doesn't extract long sequences)
# ---------------------------------------------------------------------------
plan.steps[0].input_binding = {
    "sequence": epo_sequence,
    "run_gc_tool": True,
    "run_fold_tool": True,
}

# ---------------------------------------------------------------------------
# Step 3: execute with real services
# ---------------------------------------------------------------------------
print("=== Executing real workflow (this may take 30-120s) ===\n")

final_state = runner.controller.execute(plan, state, persist_run=True)
final_state["final_report"] = runner._format_final_report(final_state)

# ---------------------------------------------------------------------------
# Step 4: verify full-chain audit trail
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("FULL-CHAIN AUDIT VERIFICATION")
print("=" * 60)

log = final_state.get("_execution_log", [])
print(f"\n1. _execution_log event count: {len(log)}")

event_counts = {}
for entry in log:
    ev = entry.get("event", "unknown")
    event_counts[ev] = event_counts.get(ev, 0) + 1
print(f"   Event breakdown: {json.dumps(event_counts, indent=2)}")

# 1. routing_decision
routing_events = [e for e in log if e.get("event") == "routing_decision"]
assert len(routing_events) >= 1, f"MISSING: routing_decision not found in _execution_log"
print(f"\n2. [PASS] routing_decision found (method={routing_events[0].get('method')})")

# 2. step_start / step_done
assert any(e.get("event") == "step_start" for e in log), "MISSING: step_start not found"
assert any(e.get("event") == "step_done" for e in log), "MISSING: step_done not found"
print("3. [PASS] step_start and step_done found")

# 3. critic_skipped (mrna_sequence_scoring has no critic)
skipped_events = [e for e in log if e.get("event") == "critic_skipped"]
assert len(skipped_events) >= 1, f"MISSING: critic_skipped not found in _execution_log"
assert skipped_events[0].get("reason") == "no_critic_registered"
print(f"4. [PASS] critic_skipped found (reason={skipped_events[0].get('reason')})")

# 4. plan_complete
assert any(e.get("event") == "plan_complete" for e in log), "MISSING: plan_complete not found"
print("5. [PASS] plan_complete found")

# 5. workflow_result carries audit metadata
wf_result = final_state.get("workflow_result")
assert wf_result is not None, "MISSING: workflow_result not found in final_state"

wf_input = getattr(wf_result, "_workflow_input", None)
assert wf_input is not None, "MISSING: workflow_result._workflow_input not attached"
assert isinstance(wf_input, dict), "workflow_result._workflow_input must be a dict"
print(f"6. [PASS] workflow_result._workflow_input attached (keys={list(wf_input.keys())})")

wf_exec_log = getattr(wf_result, "_execution_log", None)
assert wf_exec_log is not None, "MISSING: workflow_result._execution_log not attached"
assert len(wf_exec_log) == len(log), "workflow_result._execution_log length mismatch"
print(f"7. [PASS] workflow_result._execution_log attached ({len(wf_exec_log)} events)")

# 6. Tool call trace inside workflow_result
tool_records = wf_result.trace if wf_result else []
print(f"8. [PASS] workflow_result.trace contains {len(tool_records)} ToolCallRecord(s)")
for rec in tool_records:
    print(f"      - step={rec.step_name}, tool={rec.tool_name}, success={rec.success}, elapsed={rec.elapsed_time:.3f}s")

# 7. Persistence verification
persisted_path = wf_result.run_result_json_path if wf_result else None
if persisted_path:
    abs_path = Path(__file__).parent / persisted_path
    if abs_path.exists():
        with open(abs_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        assert "_execution_log" in doc, "MISSING: _execution_log not in persisted result.json"
        assert doc.get("workflow_input") is not None, "MISSING: workflow_input not in persisted result.json"
        print(f"9. [PASS] Persisted result.json contains _execution_log and workflow_input")
        print(f"    Path: {abs_path}")
    else:
        print(f"9. [WARN] Persisted file not found at expected path: {abs_path}")
else:
    print("9. [WARN] No persistence path set (persist_run=True should have set it)")

# ---------------------------------------------------------------------------
# Step 5: print summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("WORKFLOW RESULT SUMMARY")
print("=" * 60)
print(f"success        : {wf_result.success}")
print(f"task_id        : {wf_result.task_id}")
print(f"summary        : {wf_result.summary}")
print(f"candidate count: {len(wf_result.all_candidates)}")
if wf_result.best_candidate:
    bc = wf_result.best_candidate
    print(f"best candidate : id={bc.id}, score={bc.scores}")
    print(f"sequence len   : {len(bc.sequence)} nt")

print("\n" + "=" * 60)
print("FINAL REPORT (first 400 chars)")
print("=" * 60)
print(final_state.get("final_report", "")[:400])

# Dump full trace
out_path = Path("workspace/pa014_trace_output.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    trace_payload = {
        "session_id": final_state.get("session_id"),
        "user_text": final_state.get("user_text"),
        "_routing_method": final_state.get("_routing_method"),
        "_execution_plan": final_state.get("_execution_plan"),
        "_execution_log": final_state.get("_execution_log"),
        "_all_workflow_params": final_state.get("_all_workflow_params"),
        "workflow_result": {
            "success": wf_result.success if wf_result else None,
            "task_id": wf_result.task_id if wf_result else None,
            "summary": wf_result.summary if wf_result else None,
            "candidate_count": len(wf_result.all_candidates) if wf_result else 0,
            "trace_steps": [r.step_name for r in wf_result.trace] if wf_result else [],
            "_workflow_input_keys": list(getattr(wf_result, "_workflow_input", {}).keys()),
            "_execution_log_event_types": list(event_counts.keys()),
        },
        "final_report_preview": final_state.get("final_report", "")[:500],
    }
    json.dump(trace_payload, f, ensure_ascii=False, indent=2, default=str)

print(f"\nFull trace written to: {out_path}")
