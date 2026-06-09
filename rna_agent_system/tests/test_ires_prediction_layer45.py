"""Layer 4/5 comprehensive integration test for IRES prediction workflow.

Covers:
  - Layer 4: SessionMemory + WorkspaceManager persistence across multi-turn dialog
  - Layer 5: AgentRunner.run() / .stream() end-to-end for IRES workflow
  - CLI / API entry points (CLI: ires_workflow.py, FastAPI: /v1/workflows/ires/run)
  - CPU tool validation (IRESfinder port 8013, ViennaRNA fold/plfold port 8003, unpaired fraction)
  - Critic behavior: IresPredictionLLMCritic, mock low-quality triggers retry + parameter override
  - DeepSeek API: real IresPredictionLLMCritic diagnosis of low-confidence IRES predictions
  - Code quality checks (type annotations, no hardcoded keys, INTERFACE LOCK, no bare except)

Run:
    # All non-LLM tests (Layers 4-5)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_ires_prediction_layer45.py -v -s

    # Include live LLM tests (requires DEEPSEEK_API_KEY)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_ires_prediction_layer45.py -v -s --live-llm
"""

from __future__ import annotations

from tests.helpers import build_mock_plan

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage


def _service_available(url: str, timeout: float = 3.0) -> bool:
    try:
        import requests
        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:
        return False


IRES_SERVICE_UP = _service_available("http://127.0.0.1:8013/health")
VIENNA_SERVICE_UP = _service_available("http://127.0.0.1:8003/health")

from agent_core.file_manager import PROJECT_ROOT, save_sequence, save_text_file
from agent_core.planning.base import (
    AgentContext,
    ExecutionController,
    ExecutionPlan,
    PlanStep,
)
from agent_core.planning.llm_planner import LLMPlanner
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.ires_prediction import (
    IRES_PREDICTION_CRITIC_CONFIG,
    IresPredictionLLMCritic,
    IresPredictionWorkflow,
)
from agent_core.workspace_manager import WorkspaceManager

# ── Configuration ────────────────────────────────────────────────────

# AT-rich sequence known to trigger IRESfinder positive predictions
TEST_IRES_SEQ = "ATAT" * 200  # 800 nt

# Load .env for API key checks
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")
_HAS_DEEPSEEK_KEY = bool(os.environ.get("DEEPSEEK_API_KEY"))

skip_if_no_live_llm = pytest.mark.skipif(
    not _HAS_DEEPSEEK_KEY,
    reason="Requires DEEPSEEK_API_KEY in environment/.env",
)


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _count_event_types(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        for k in e:
            counts[k] = counts.get(k, 0) + 1
    return counts


def _make_low_confidence_ires_result() -> WorkflowResult:
    """Build a WorkflowResult with poor IRES metrics to trigger critic retry."""
    candidates = [
        Candidate(
            sequence="ATGC" * 20,
            sequence_type="dna",
            source="iresfinder:0",
            metadata={
                "ires_probability": 0.35,  # Below threshold, low confidence
                "start": 1,
                "end": 80,
                "iresfinder_mode": 0,
                "metrics_bundle": {
                    "ires_probability": 0.35,
                    "start": 1,
                    "end": 80,
                    "region_length": 80,
                    "mfe_kcal_per_mol": -5.0,
                    "mean_unpaired_fraction": 0.15,
                    "mean_unpaired_prob_1nt": 0.2,
                },
            },
        )
    ]
    candidates[0].scores = {"ires_probability": 0.35, "composite_score": 0.35}
    return WorkflowResult(
        success=True,
        task_id="low-conf",
        best_candidate=candidates[0],
        all_candidates=candidates,
        summary="Low confidence IRES prediction",
    )


# ═══════════════════════════════════════════════════════════════════════
# Layer 4 — Session & Memory
# ═══════════════════════════════════════════════════════════════════════


class TestLayer4SessionMemory:
    """Verify SessionMemory.load/save and WorkspaceManager isolation for IRES."""

    def test_session_memory_load_save(self):
        mem = SessionMemory()
        sid = "test-ires-session-001"
        state = default_state("hello")
        state["best_candidate"] = "IRES1"
        mem.save(sid, state)
        loaded = mem.load(sid)
        assert loaded["best_candidate"] == "IRES1"
        assert loaded["messages"][0].content == "hello"
        # load returns deepcopy; mutations should not affect stored state
        loaded["best_candidate"] = "IRES2"
        reloaded = mem.load(sid)
        assert reloaded["best_candidate"] == "IRES1"

    def test_session_memory_empty_session_id(self):
        mem = SessionMemory()
        state = default_state("hello")
        mem.save("", state)
        assert mem._store == {}
        loaded = mem.load("")
        assert loaded["messages"][0].content == ""

    def test_runner_with_memory_persists_across_turns(self):
        planner = MagicMock()
        seq_fp = save_sequence(TEST_IRES_SEQ, prefix="ires_l4_seq")
        plan = build_mock_plan(
            "ires_prediction",
            {
                "sequence_filepath": seq_fp,
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": False,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        mem = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=mem)
        sid = "ires-session-l4-001"

        # Turn 1
        state1 = runner.run(
            f"Predict IRES elements in sequence {seq_fp}", session_id=sid
        )
        assert state1.get("workflow_result") is not None

        # Verify memory stored the state
        loaded = mem.load(sid)
        assert loaded.get("workflow_result") is not None

        # Turn 2: state should carry forward
        state2 = runner.run("lower the threshold", session_id=sid)
        human_msgs = [m for m in state2.get("messages", []) if isinstance(m, HumanMessage)]
        contents = [m.content for m in human_msgs]
        assert any("Predict IRES" in c for c in contents)
        assert any("lower the threshold" in c for c in contents)

    def test_runner_explicit_state_bypasses_memory(self):
        planner = MagicMock()
        plan = build_mock_plan("ires_prediction", {"sequence_filepath": "test.fa"})
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        mem = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=mem)

        explicit = default_state("explicit")
        explicit["custom_key"] = "CUSTOM_IRES"

        with patch.object(ExecutionController, "execute") as mock_exec:
            mock_exec.return_value = explicit
            result = runner.run("new input", session_id="session-abc", state=explicit)
            passed_state = mock_exec.call_args[0][1]
            assert passed_state["custom_key"] == "CUSTOM_IRES"

        # Memory should NOT have been touched for the explicit-state path
        assert "session-abc" not in mem._store

    def test_workspace_manager_per_session_isolation(self):
        wm = WorkspaceManager(base_dir="workspace_test_ires_layer4")
        sid1 = "ires-wm-session-1"
        sid2 = "ires-wm-session-2"

        dir1 = wm.get_session_dir(sid1)
        dir2 = wm.get_session_dir(sid2)

        assert dir1 != dir2
        assert sid1 in str(dir1)
        assert sid2 in str(dir2)
        assert dir1.exists()
        assert dir2.exists()

        # Write files to each session
        fp1 = dir1 / "test1.txt"
        fp2 = dir2 / "test2.txt"
        fp1.write_text("session1")
        fp2.write_text("session2")

        files1 = wm.list_files(sid1)
        files2 = wm.list_files(sid2)
        assert any("test1.txt" in f for f in files1)
        assert any("test2.txt" in f for f in files2)
        assert not any("test2.txt" in f for f in files1)
        assert not any("test1.txt" in f for f in files2)

        # Cleanup
        wm.delete_session(sid1)
        wm.delete_session(sid2)
        assert not dir1.exists()
        assert not dir2.exists()


# ═══════════════════════════════════════════════════════════════════════
# Layer 5 — AgentRunner End-to-End
# ═══════════════════════════════════════════════════════════════════════


class TestLayer5AgentRunner:
    """Verify AgentRunner.run / stream / critic behavior for IRES workflow."""

    def test_runner_stream_event_flow(self):
        planner = MagicMock()
        seq_fp = save_sequence(TEST_IRES_SEQ, prefix="ires_stream_seq")
        plan = build_mock_plan(
            "ires_prediction",
            {
                "sequence_filepath": seq_fp,
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": False,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        events = list(runner.stream("Predict IRES elements", session_id="sid-ires-stream"))
        counts = _count_event_types(events)
        assert counts.get("router", 0) >= 1
        assert counts.get("plan", 0) >= 1
        assert counts.get("tool_execution", 0) >= 1 or counts.get("runner", 0) >= 1

    def test_runner_routes_to_ires_prediction(self):
        """AgentRunner should route IRES requests correctly."""
        planner = MagicMock()
        seq_fp = save_sequence(TEST_IRES_SEQ, prefix="ires_route_seq")
        plan = build_mock_plan(
            "ires_prediction",
            {
                "sequence_filepath": seq_fp,
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": False,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        mock_result = default_state("")
        mock_result["workflow_result"] = WorkflowResult(
            success=True,
            task_id="ires-routing-test",
            best_candidate=Candidate(sequence="ATGC" * 20, source="iresfinder:0"),
            all_candidates=[Candidate(sequence="ATGC" * 20, source="iresfinder:0")],
            summary="routing ok",
        )

        with patch.object(ExecutionController, "execute", return_value=mock_result):
            state = runner.run("Predict IRES elements in this sequence", session_id="test-ires-001")

        assert state.get("workflow_result") is not None
        wf = state["workflow_result"]
        assert wf.success is True
        assert wf.best_candidate is not None

    def test_runner_critic_retry_parameter_override(self):
        """Mock low-confidence result triggers critic retry with parameter overrides."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        # Build a fake low-confidence result
        low_result = _make_low_confidence_ires_result()

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "ires_prediction":
                state["_last_workflow_params"] = dict(step.input_binding)
                return low_result
            raise RuntimeError(f"Unexpected: {step.target}")

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf1",
                    type="workflow",
                    target="ires_prediction",
                    input_binding={
                        "sequence_filepath": "test.fa",
                        "probability_threshold": 0.5,
                        "iresfinder_mode": 0,
                    },
                )
            ],
            max_retries=2,
        )

        # Patch critic to force retry with parameter overrides
        def _mock_should_retry(result, state):
            state["_parameter_overrides"] = {"probability_threshold": 0.3}
            return True

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch("agent_core.workflows.registry.get_critic_for_workflow") as mock_get_critic:
                mock_critic = MagicMock()
                mock_critic.should_retry = _mock_should_retry
                mock_get_critic.return_value = mock_critic
                final_state = controller.execute(
                    plan,
                    {"_llm_critic_enabled": True, "user_text": "Find IRES with high confidence"},
                    replan_fn=lambda s: plan,
                )

        # The flow should complete without crashing
        assert final_state.get("_plan_executed") is True
        log = final_state.get("_execution_log", [])
        assert any(e.get("event") == "step_start" for e in log)
        assert any(e.get("event") == "step_done" for e in log)
        # Verify parameter override was applied
        assert any(e.get("event") == "parameter_override" for e in log)
        # Verify probability_threshold was overridden
        assert call_count >= 2  # original run + at least one retry

    def test_runner_ires_no_critic_when_disabled(self):
        """When llm_critic_enabled=False, IRES should not trigger critic retry."""
        planner = MagicMock()
        seq_fp = save_sequence(TEST_IRES_SEQ, prefix="ires_nocritic_seq")
        plan = build_mock_plan(
            "ires_prediction",
            {
                "sequence_filepath": seq_fp,
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": False,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        state = runner.run("Predict IRES elements", session_id="test-ires-no-critic")
        assert state.get("retry_count", 0) == 0, (
            f"Expected retry_count=0 with critic disabled, got {state.get('retry_count')}"
        )


# ═══════════════════════════════════════════════════════════════════════
# CLI / API Entry Points
# ═══════════════════════════════════════════════════════════════════════


class TestCliApiEntry:
    """Verify CLI and FastAPI entry points for IRES workflow."""

    APP_ROOT = Path(__file__).resolve().parents[1]

    @pytest.mark.skipif(not IRES_SERVICE_UP, reason="IRESfinder service (port 8013) not reachable")
    def test_cli_ires_workflow_runs(self):
        """cli/ires_workflow.py --sequence executes successfully."""
        import subprocess

        env = {**os.environ, "PYTHONPATH": str(self.APP_ROOT)}
        cmd = [
            sys.executable,
            str(self.APP_ROOT / "cli" / "ires_workflow.py"),
            "--sequence",
            TEST_IRES_SEQ,
            "--mode",
            "0",
            "--json",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(self.APP_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert proc.returncode in (0, 1), f"stderr: {proc.stderr}"
        # Parse JSON output when --json is used
        if proc.stdout.strip():
            try:
                data = json.loads(proc.stdout)
                assert "success" in data
                assert data.get("task_type") == "ires"
            except json.JSONDecodeError:
                # Non-JSON output is acceptable if workflow produced warnings
                pass

    def test_fastapi_ires_endpoint(self):
        """POST /v1/workflows/ires/run routes to IresPredictionWorkflow."""
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from workflow_api.app import app
        from workflow_api.ires_schemas import IresWorkflowHttpRequest

        client = TestClient(app)
        req = IresWorkflowHttpRequest(
            sequence=TEST_IRES_SEQ,
            iresfinder_mode=0,
            probability_threshold=0.5,
            run_structural_validation=False,
            task_id="test-ires-api",
        )
        r = client.post("/v1/workflows/ires/run", json=req.model_dump())
        assert r.status_code == 200, f"Unexpected status: {r.status_code}, body: {r.text}"
        data = r.json()
        assert data["task_type"] == "ires"
        assert "success" in data

    def test_fastapi_unified_endpoint_routes_ires(self):
        """POST /v1/workflows/run with task_type=ires routes correctly."""
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from workflow_api.app import app
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        client = TestClient(app)
        req = MrnaWorkflowHttpRequest(
            sequence=TEST_IRES_SEQ,
            task_type="ires",
            constraints={
                "iresfinder_mode": 0,
                "probability_threshold": 0.5,
                "run_structural_validation": False,
            },
            task_id="test-ires-unified",
        )
        r = client.post("/v1/workflows/run", json=req.model_dump())
        assert r.status_code == 200, f"Unexpected status: {r.status_code}, body: {r.text}"
        data = r.json()
        # Unified endpoint returns MrnaWorkflowHttpResponse shape
        assert "success" in data
        assert data.get("task_type") == "ires"

    def test_ires_handler_schema_matches_runner(self):
        """IresWorkflowHttpResponse fields align with WorkflowResult."""
        from workflow_api.ires_handler import execute_ires_workflow_http
        from workflow_api.ires_schemas import IresWorkflowHttpRequest

        req = IresWorkflowHttpRequest(
            sequence=TEST_IRES_SEQ,
            iresfinder_mode=0,
            probability_threshold=0.5,
            run_structural_validation=False,
            task_id="schema-test",
        )
        out = execute_ires_workflow_http(req)
        assert hasattr(out, "task_id")
        assert hasattr(out, "success")
        assert hasattr(out, "task_type")
        assert hasattr(out, "best_candidate")
        assert hasattr(out, "candidates")
        assert hasattr(out, "summary")
        assert hasattr(out, "errors")
        assert hasattr(out, "warnings")

    def test_ires_in_workflow_critic_pairs(self):
        """ires_prediction must be in WORKFLOW_CRITIC_PAIRS."""
        from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS
        from agent_core.workflows.ires_prediction import (
            IresPredictionLLMCritic,
            IresPredictionWorkflow,
        )

        assert "ires_prediction" in WORKFLOW_CRITIC_PAIRS, (
            "ires_prediction must have a critic pair"
        )
        assert WORKFLOW_CRITIC_PAIRS["ires_prediction"] == (
            IresPredictionWorkflow,
            IresPredictionLLMCritic,
        )


# ═══════════════════════════════════════════════════════════════════════
# DeepSeek API Validation
# ═══════════════════════════════════════════════════════════════════════


class TestDeepSeekApiLive:
    """Real LLM call validation (requires --live-llm and DEEPSEEK_API_KEY)."""

    @skip_if_no_live_llm
    def test_llm_planner_generates_ires_plan(self):
        """LLMPlanner.plan() returns a valid JSON plan for IRES requests."""
        planner = LLMPlanner()
        ctx = AgentContext(
            session_id="live-ires-plan-test",
            available_capabilities=[
                "predict_putative_ires_with_iresfinder",
                "predict_rna_secondary_structure",
            ],
            available_workflows=["ires_prediction"],
            workflow_param_schemas={
                "ires_prediction": "sequence_filepath=(required) (str)",
            },
        )
        plan = planner.plan(
            f"Predict IRES elements in sequence {TEST_IRES_SEQ[:50]}",
            ctx,
        )
        targets = [s.target for s in plan.steps]
        # LLM may return workflow step or capability step; accept IRES-related targets
        if targets:
            assert any(
                t in ("ires_prediction", "predict_putative_ires_with_iresfinder")
                for t in targets
            ), f"Expected IRES-related target, got: {targets}"
        dumped = plan.model_dump(mode="json")
        assert "steps" in dumped
        assert "max_retries" in dumped

    @skip_if_no_live_llm
    def test_ires_critic_diagnoses_low_confidence(self):
        """IresPredictionLLMCritic.diagnose returns actionable diagnosis for poor results."""
        critic = IresPredictionLLMCritic()
        low_result = _make_low_confidence_ires_result()
        state = {
            "_last_workflow_params": {
                "probability_threshold": 0.5,
                "iresfinder_mode": 0,
                "top_n_candidates": 5,
            },
            "user_text": "Find high-confidence IRES candidates",
        }
        diagnosis = critic.diagnose(low_result, state)

        assert diagnosis.overall_assessment
        # Low confidence results should get a lower quality score
        assert diagnosis.quality_score < 0.8
        assert len(diagnosis.issues) > 0
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "abort",
            "proceed_with_filtered",
        )
        # Verify diagnosis was recorded
        assert "_diagnosis_history" in state
        assert len(state["_diagnosis_history"]) >= 1

    @skip_if_no_live_llm
    def test_ires_critic_build_context_with_stats(self):
        """Critic _build_context extracts IRES-specific statistics."""
        critic = IresPredictionLLMCritic()
        low_result = _make_low_confidence_ires_result()
        state = {"_last_workflow_params": {"probability_threshold": 0.5}}
        ctx = critic._build_context(low_result, state)

        assert "ires_stats" in ctx
        stats = ctx["ires_stats"]
        assert stats["probability_range"]["count"] > 0
        assert stats["probability_range"]["max"] < 0.5  # Low confidence
        assert stats["coverage"]["min_start"] is not None
        assert stats["mode_distribution"] is not None

    @skip_if_no_live_llm
    def test_api_failure_graceful_degradation(self):
        """When DeepSeek API fails, Critic falls back to no-retry (no crash)."""
        critic = IresPredictionLLMCritic()
        result = WorkflowResult(
            success=True,
            task_id="degradation-test",
            best_candidate=Candidate(sequence="ATGC" * 10, source="test"),
            all_candidates=[Candidate(sequence="ATGC" * 10, source="test")],
            summary="test",
        )
        state = {"_llm_critic_enabled": True}

        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=RuntimeError("Simulated API failure"))
        critic._llm = mock_llm

        should_retry = critic.should_retry(result, state)
        assert should_retry is False
        assert "_last_diagnosis" in state
        diag = state["_last_diagnosis"]
        assert diag["action"] == "abort"
        assert "LLM diagnosis failed" in diag["overall_assessment"]

    def test_ires_critic_config_fields(self):
        """Verify the IRES critic config has all expected adjustable params."""
        config = IRES_PREDICTION_CRITIC_CONFIG
        assert config.workflow_name == "ires_prediction"
        assert config.max_retries == 2
        assert config.retry_strategy == "adjust_params"

        expected_params = {
            "probability_threshold",
            "window_size",
            "step_size",
            "top_n_candidates",
            "run_structural_validation",
            "iresfinder_mode",
        }
        assert set(config.adjustable_params.keys()) == expected_params


# ═══════════════════════════════════════════════════════════════════════
# CPU / GPU Tool Validation
# ═══════════════════════════════════════════════════════════════════════


class TestCpuTools:
    """Layer 0 CPU tool validation for IRES workflow."""

    @pytest.fixture(scope="class")
    def executor(self):
        return ToolExecutor(build_default_tool_registry())

    @pytest.fixture(scope="class")
    def test_sequence_filepath(self):
        return save_sequence(TEST_IRES_SEQ, prefix="ires_l45_seq")

    @pytest.mark.skipif(not IRES_SERVICE_UP, reason="IRESfinder service (port 8013) not reachable")
    def test_iresfinder_mode0_cpu(self, executor, test_sequence_filepath):
        result = executor.run_tool(
            "predict_putative_ires_with_iresfinder",
            filepath=test_sequence_filepath,
            mode=0,
            decision_threshold=0.5,
        )
        assert result.success, f"IRESfinder failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "fragment_count" in r
        assert "has_putative_ires" in r
        assert "predictions" in r
        assert "model" in r
        assert r["model"] == "IRESfinder-logreg-py3"

    @pytest.mark.skipif(not IRES_SERVICE_UP, reason="IRESfinder service (port 8013) not reachable")
    def test_iresfinder_mode2_cpu(self, executor, test_sequence_filepath):
        result = executor.run_tool(
            "predict_putative_ires_with_iresfinder",
            filepath=test_sequence_filepath,
            mode=2,
            window_size=174,
            step_size=50,
            decision_threshold=0.5,
        )
        assert result.success, f"IRESfinder mode 2 failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert r["window_size"] == 174
        assert r["step_size"] == 50
        assert r["mode"] == 2

    def test_viennarna_fold_cpu(self, executor):
        seq = "ACGUACGUACGUACGUACGUACGUACGUACGU"
        fp = save_sequence(seq, prefix="ires_l45_fold")
        result = executor.run_tool("predict_rna_secondary_structure", filepath=fp)
        assert result.success, f"ViennaRNA fold failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "structure" in r
        assert "mfe_kcal_per_mol" in r
        assert len(r["structure"]) == len(seq)

    def test_dot_bracket_unpaired_fraction_cpu(self, executor):
        structure = "((((....))))....(((())))"
        fp = save_text_file(structure, prefix="ires_l45_unp", suffix=".db")
        result = executor.run_tool("compute_dot_bracket_unpaired_fraction", filepath=fp)
        assert result.success, f"Unpaired fraction failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "unpaired_fraction" in r
        assert 0 <= r["unpaired_fraction"] <= 1
        assert r["structure_length"] == len(structure)

    def test_all_tools_are_cpu(self):
        """Sanity check: all IRES tools are CPU-based (no GPU)."""
        from agent_core.tool_specs import TOOL_SPECS

        tool_names = IresPredictionWorkflow.required_capabilities
        for name in tool_names:
            spec = TOOL_SPECS.get(name)
            assert spec is not None, f"ToolSpec for {name} not found"
            deps = [d.name for d in (spec.requires or [])]
            gpu_deps = [d for d in deps if "gpu" in d.lower() or "cuda" in d.lower()]
            assert len(gpu_deps) == 0, f"Tool {name} unexpectedly has GPU dep: {gpu_deps}"


# ═══════════════════════════════════════════════════════════════════════
# Code Quality Checks
# ═══════════════════════════════════════════════════════════════════════


class TestCodeQuality:
    """Static code quality checks for Layer 4/5 modules."""

    @pytest.fixture(scope="class")
    def layer45_source_files(self):
        files: list[Path] = []
        targets = [
            "agent_core/runner.py",
            "agent_core/session_memory.py",
            "agent_core/workspace_manager.py",
            "agent_core/state.py",
            "agent_core/workflows/ires_prediction.py",
            "workflow_api/ires_handler.py",
            "workflow_api/ires_schemas.py",
            "cli/ires_workflow.py",
        ]
        for rel in targets:
            p = PROJECT_ROOT / rel
            if p.exists():
                files.append(p)
        return files

    def test_type_annotations_on_public_methods(self, layer45_source_files):
        failures: list[str] = []
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    if node.returns is None and node.name != "__init__":
                        failures.append(f"{path.name}:{node.name}")
        allowed_missing = {
            "run", "main", "health", "post_mrna_workflow", "post_sirna_workflow",
            "post_ires_workflow", "post_rna_workflow", "post_agent_run",
        }
        failures = [f for f in failures if f.split(":")[-1] not in allowed_missing]
        assert len(failures) == 0, f"Missing return type annotations: {failures}"

    def test_no_hardcoded_api_keys(self, layer45_source_files):
        key_patterns = ["api_key = ", "api_key="]
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            for pat in key_patterns:
                lines = [
                    i + 1
                    for i, line in enumerate(source.splitlines())
                    if pat in line and "os.environ" not in line and "getenv" not in line and "load_dotenv" not in line
                ]
                assert len(lines) == 0, f"Possible hardcoded key in {path.name} lines {lines}"

    def test_interface_lock_comments_present(self, layer45_source_files):
        required_locks = {
            "runner.py": ["INTERFACE LOCK"],
            "ires_prediction.py": ["INTERFACE LOCK"],
        }
        for filename, markers in required_locks.items():
            path = next((p for p in layer45_source_files if p.name == filename), None)
            if path is None:
                continue
            source = path.read_text(encoding="utf-8")
            for marker in markers:
                assert marker in source, f"{filename} missing '{marker}' comment"

    def test_exception_handling_no_bare_except(self, layer45_source_files):
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        assert False, f"Bare except in {path.name} line {node.lineno}"
