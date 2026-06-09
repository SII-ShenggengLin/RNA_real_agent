"""Verify AgentRunner-path full-chain auditability for mrna_sequence_scoring.

Checks:
1. routing_decision event exists in _execution_log
2. critic_skipped event exists in _execution_log
3. workflow_result carries _workflow_input and _execution_log
4. persisted result.json contains _execution_log (when persist_run=True)
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_core.planning.base import ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflow_baseline_eval import StubCaiTool, StubFoldTool, StubGcTool
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringWorkflow


def _build_mock_plan():
    return ExecutionPlan(
        steps=[
            PlanStep(
                step_id="score_1",
                type="workflow",
                target="mrna_sequence_scoring",
                input_binding={
                    "sequence": "AUGCAUGCAUGCAUGCAU",
                    "run_gc_tool": True,
                    "run_fold_tool": True,
                },
                output_key="workflow_result",
                description="Score mRNA sequence",
            )
        ],
        max_retries=2,
    )


class TestAuditTrailFix:
    def test_agent_runner_produces_full_audit_trail(self):
        registry = ToolRegistry()
        registry.register(StubGcTool())
        registry.register(StubFoldTool())
        registry.register(StubCaiTool())
        executor = ToolExecutor(registry)

        planner = MagicMock()
        planner.plan_with_state = MagicMock(return_value=_build_mock_plan())

        runner = AgentRunner(planner, executor, persist_run=False)
        state = runner.run("Score my mRNA sequence AUGCAUGCAUGCAUGCAU")

        # 1. routing_decision must be in _execution_log
        execution_log = state.get("_execution_log", [])
        routing_events = [e for e in execution_log if e.get("event") == "routing_decision"]
        assert len(routing_events) >= 1, f"No routing_decision in log: {execution_log}"
        assert routing_events[0].get("method") in ("deterministic", "llm")

        # 2. critic_skipped must be in _execution_log (mrna_sequence_scoring has no critic)
        skipped_events = [e for e in execution_log if e.get("event") == "critic_skipped"]
        assert len(skipped_events) >= 1, f"No critic_skipped in log: {execution_log}"
        assert skipped_events[0].get("reason") == "no_critic_registered"

        # 3. workflow_result must carry _workflow_input and _execution_log
        wf_result = state.get("workflow_result")
        assert wf_result is not None, "workflow_result missing from state"
        assert getattr(wf_result, "_workflow_input", None) is not None, \
            "workflow_result missing _workflow_input"
        assert getattr(wf_result, "_execution_log", None) is not None, \
            "workflow_result missing _execution_log"
        # _workflow_input may be empty when deterministic router does not extract params;
        # the key point is that the audit metadata attachment mechanism works.
        assert isinstance(wf_result._workflow_input, dict)
        assert any(e.get("event") == "routing_decision" for e in wf_result._execution_log)
        assert any(e.get("event") == "critic_skipped" for e in wf_result._execution_log)

        # 4. step_start and step_done should also be present
        assert any(e.get("event") == "step_start" for e in execution_log)
        assert any(e.get("event") == "step_done" for e in execution_log)
        assert any(e.get("event") == "plan_complete" for e in execution_log)

    def test_persisted_result_contains_execution_log(self):
        registry = ToolRegistry()
        registry.register(StubGcTool())
        registry.register(StubFoldTool())
        registry.register(StubCaiTool())
        executor = ToolExecutor(registry)

        planner = MagicMock()
        planner.plan_with_state = MagicMock(return_value=_build_mock_plan())

        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = Path(tmpdir) / "workflow_runs"
            os.environ["WORKFLOW_RUNS_PARENT"] = str(runs_dir)

            runner = AgentRunner(planner, executor, persist_run=True)
            state = runner.run("Score my mRNA sequence AUGCAUGCAUGCAUGCAU")

            wf_result = state["workflow_result"]
            assert wf_result.run_result_json_path is not None, "result.json path not set"

            result_path = Path(__file__).parent.parent / wf_result.run_result_json_path
            assert result_path.exists(), f"persisted result.json not found at {result_path}"

            with open(result_path, "r", encoding="utf-8") as f:
                doc = json.load(f)

            assert "_execution_log" in doc, "_execution_log missing from persisted result.json"
            assert doc["_execution_log"] is not None
            assert any(e.get("event") == "routing_decision" for e in doc["_execution_log"])
            assert any(e.get("event") == "critic_skipped" for e in doc["_execution_log"])
            assert doc.get("workflow_input") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
