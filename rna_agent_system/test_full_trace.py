"""
Test script: verify full-chain structured tracing for FullLengthMrnaDesignWorkflow
using real benchmark data (PA_003 / PA_019).

This script:
1. Loads a benchmark task (user query).
2. Runs it through AgentRunner to capture routing decisions.
3. Replaces the real workflow with a mock that returns a WorkflowResult with BMC trace.
4. Verifies every required tracing field in the final AgentState.
"""

import json
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Load benchmark data
# ---------------------------------------------------------------------------
BENCH_PATH = Path(__file__).parent / "data" / "benchmarks" / "RNA-BioBench-ProcessAware" / "task_set_for_llm_comparison.json"
with open(BENCH_PATH) as f:
    bench = json.load(f)

# Pick PA_019 (GFP full-length mRNA) — explicit params make it easy to inspect
task = next(t for t in bench["tasks"] if t["task_id"] == "PA_019")
user_query = task["user_query"]
print(f"Loaded task: {task['task_id']} → {task['workflow']}")
print(f"User query: {user_query}\n")

# ---------------------------------------------------------------------------
# 1. Build AgentRunner (real router + mock planner so no LLM call is needed)
# ---------------------------------------------------------------------------
from agent_core.planning.base import ExecutionPlan, PlanStep
from agent_core.planning.router import DeterministicRouter
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor
from agent_core.workflow_models import WorkflowResult, Candidate
from agent_core.capabilities.base import CapabilityRegistry

class FakePlanner:
    """Planner that should never be called because deterministic router handles it."""
    def plan(self, user_text, context):
        raise RuntimeError("LLMPlanner should not be invoked for deterministic matches")

class FakeExecutor:
    pass

runner = AgentRunner(
    planner=FakePlanner(),
    executor=FakeExecutor(),
    session_memory=None,
    llm_critic_enabled=True,
)

# ---------------------------------------------------------------------------
# 2. Route the query and verify routing trace
# ---------------------------------------------------------------------------
state = runner._prepare_state(user_query, session_id="trace_test_001", explicit_state=None)
plan = runner._build_plan(user_query, state)

print("=== Routing Trace ===")
print(f"_routing_method : {state.get('_routing_method')}")
print(f"Plan steps      : {len(plan.steps)}")
for s in plan.steps:
    print(f"  - {s.step_id}: {s.type} → {s.target}")
print()

assert state.get("_routing_method") == "deterministic", "Expected deterministic routing"
assert plan.steps[0].target == "full_length_mrna_design", "Expected full_length_mrna_design workflow"

# ---------------------------------------------------------------------------
# 3. Inject a mock FullLengthMrnaDesignWorkflow so no external services are needed
# ---------------------------------------------------------------------------
class MockFullLengthMrnaDesignWorkflow:
    name = "full_length_mrna_design"
    input_model = None  # not needed for mock

    def run(self, inputs, *, progress_callback=None):
        # Simulate a realistic result with BMC trace
        time.sleep(0.05)  # tiny delay so elapsed_ms > 0
        result = WorkflowResult(
            success=True,
            task_id="mock_task_001",
            summary="Mock full-length mRNA design completed",
        )
        result.all_candidates = [
            Candidate(
                sequence="AUGGGG...",
                source="mock_cds+utr",
                scores={"total_score": 0.85},
                metadata={"cds_sequence": "AUGGGG", "utr5_sequence": "GGG", "utr3_sequence": "AAA"},
            )
        ]
        result.best_candidate = result.all_candidates[0]
        result._state_writeback = {
            "_bmc_trace": [
                {
                    "round_num": 1,
                    "best_candidate_id": "cand_mock",
                    "best_total_score": 0.85,
                    "issues_found": [],
                    "feedback_dispatched": {},
                    "modules_reinvoked": [],
                    "time_elapsed_ms": 50,
                }
            ]
        }
        if progress_callback:
            progress_callback({"event": "mock_progress", "msg": "done"})
        return result

# Swap the real workflow for our mock
runner.workflow_registry["full_length_mrna_design"] = MockFullLengthMrnaDesignWorkflow()

# Inject a protein_sequence into the plan (deterministic router doesn't extract it)
plan.steps[0].input_binding = {
    "protein_sequence": "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTLSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTISFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYITADKQKNGIKANFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
    "lambda_value": 4.0,
    "utr_mode": "long",
}

# ---------------------------------------------------------------------------
# 4. Execute and collect trace
# ---------------------------------------------------------------------------
final_state = runner.controller.execute(plan, state, persist_run=False)
final_state["final_report"] = runner._format_final_report(final_state)

# ---------------------------------------------------------------------------
# 5. Verify full-chain tracing fields
# ---------------------------------------------------------------------------
print("=== Full-Chain Trace Verification ===\n")

# 5.1 User input
assert final_state.get("user_text") == user_query
assert final_state.get("session_id") == "trace_test_001"
print("✅ User input recorded (user_text, session_id, messages)")

# 5.2 Routing decision
assert "_routing_method" in final_state
assert "_execution_plan" in final_state
print(f"✅ Routing decision recorded (_routing_method={final_state['_routing_method']})")

# 5.3 Tool call trace — _execution_log
log = final_state.get("_execution_log", [])
assert len(log) > 0, "_execution_log should not be empty"
print(f"✅ _execution_log has {len(log)} events")

# Find step_start
start_events = [e for e in log if e.get("event") == "step_start"]
assert len(start_events) == 1
start = start_events[0]
assert "timestamp" in start, "step_start missing timestamp"
assert "inputs" in start, "step_start missing inputs"
assert start["inputs"].get("protein_sequence") is not None, "step_start missing protein_sequence input"
print(f"✅ step_start has timestamp + inputs (protein_sequence length={len(start['inputs']['protein_sequence'])})")

# Find step_done
done_events = [e for e in log if e.get("event") == "step_done"]
assert len(done_events) == 1
done = done_events[0]
assert "timestamp" in done, "step_done missing timestamp"
assert "elapsed_ms" in done, "step_done missing elapsed_ms"
assert done["elapsed_ms"] >= 0, "elapsed_ms should be >= 0"
assert "output_summary" in done, "step_done missing output_summary"
out_summary = done["output_summary"]
assert out_summary.get("result_type") == "WorkflowResult"
assert out_summary.get("candidate_count") == 1
assert out_summary.get("best_candidate_id") is not None
print(f"✅ step_done has timestamp + elapsed_ms({done['elapsed_ms']:.2f}ms) + output_summary")

# Verify no step_error
error_events = [e for e in log if e.get("event") == "step_error"]
assert len(error_events) == 0, f"Unexpected step_error events: {error_events}"
print("✅ No step_error events (clean execution)")

# 5.4 BMC trace merged into state
bmc_trace = final_state.get("_bmc_trace")
assert bmc_trace is not None, "_bmc_trace should be merged from workflow result"
assert len(bmc_trace) == 1
print(f"✅ BMC trace merged into state ({len(bmc_trace)} rounds)")

# 5.5 _all_workflow_params (no longer overwritten)
all_params = final_state.get("_all_workflow_params")
assert all_params is not None, "_all_workflow_params missing"
assert "step_1" in all_params
assert all_params["step_1"]["target"] == "full_length_mrna_design"
assert "params" in all_params["step_1"]
print(f"✅ _all_workflow_params preserved per step_id")

# 5.6 Critic-related state (even though mock has no critic, fields should exist)
assert "_llm_critic_enabled" in final_state
print(f"✅ Critic flag recorded (_llm_critic_enabled={final_state['_llm_critic_enabled']})")

# 5.7 Final output
assert "workflow_result" in final_state
assert "final_report" in final_state
wf_result = final_state["workflow_result"]
assert isinstance(wf_result, WorkflowResult)
assert wf_result.success is True
print(f"✅ Final output recorded (workflow_result.success={wf_result.success}, final_report length={len(final_state['final_report'])})")

# ---------------------------------------------------------------------------
# 6. Pretty-print the execution log
# ---------------------------------------------------------------------------
print("\n=== _execution_log (pretty) ===")
for entry in log:
    print(json.dumps(entry, indent=2, default=str))

print("\n=== _all_workflow_params ===")
print(json.dumps(final_state.get("_all_workflow_params"), indent=2, default=str))

print("\n" + "=" * 60)
print("ALL CHECKS PASSED — Full-chain structured tracing is working.")
print("=" * 60)
