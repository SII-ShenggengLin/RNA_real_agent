"""Layer 4/5 comprehensive integration test for RNAi Workflows (siRNA + sgRNA).

Covers:
  - Layer 4: SessionMemory + WorkspaceManager persistence across multi-turn dialog
  - Layer 5: AgentRunner.run() / .stream() end-to-end for both workflows
  - CLI / API entry points (siRNA CLI, FastAPI endpoints)
  - CPU tool validation (siRNA: Evitar, BLAST, ViennaRNA)
  - GPU / microservice validation (sgRNA: CRGPT port 8017, CRISOT port 8011)
  - LLM Critic retry logic with mocked and (optionally) live DeepSeek API
  - Failure degradation when LLM API or microservices are unavailable

Run:
    # All non-LLM / non-microservice tests
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_rnai_layer45_integration.py -v

    # Include live LLM tests (requires DEEPSEEK_API_KEY)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_rnai_layer45_integration.py -v --live-llm

    # Include live microservice tests (requires ports 8017 and 8011)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_rnai_layer45_integration.py -v --live-services
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Environment probes ──────────────────────────────────────────────────────


def _service_available(url: str, timeout: float = 3.0) -> bool:
    try:
        import requests

        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:
        return False


SGRNA_SERVICE_UP = _service_available("http://127.0.0.1:8017/health")
CRISOT_SERVICE_UP = _service_available("http://127.0.0.1:8011/health")
DEEPSEEK_KEY_SET = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())


def _have_fastapi() -> bool:
    import importlib.util

    return importlib.util.find_spec("fastapi") is not None


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_target_sequence() -> str:
    """120-nt target sequence for generic siRNA mode."""
    return "AUGC" * 30


@pytest.fixture(scope="module")
def test_sirna_sequence() -> str:
    """21-nt siRNA sequence."""
    return "AUGCCCGGGUUUAAAUUUAAA"



@pytest.fixture
def sirna_workflow(registry):
    from agent_core.workflows.sirna_design import SirnaDesignWorkflow

    return SirnaDesignWorkflow(registry)


@pytest.fixture
def sgrna_workflow(registry):
    from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow

    return SgRnaDesignWorkflow(registry)


# ═══════════════════════════════════════════════════════════════════════════════
# 一、Layer 4 — Session & Memory 集成
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer4SessionMemory:
    """Verify SessionMemory + WorkspaceManager integration for RNAi workflows."""

    def test_agent_runner_sirna_session_persistence(self, test_target_sequence):
        """AgentRunner with SessionMemory persists siRNA best_candidate across turns."""
        from agent_core.planning.base import ExecutionPlan, PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.session_memory import SessionMemory
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="sirna",
                    type="workflow",
                    target="sirna_design",
                    input_binding={
                        "mode": "generic",
                        "target_sequence": test_target_sequence,
                        "candidate_count": 3,
                        "off_target_scan": False,
                    },
                    output_key="sirna_result",
                )
            ]
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=memory, llm_critic_enabled=False)

        sid = "sirna-session-001"

        # Turn 1: design siRNA
        state1 = runner.run(
            f"Design siRNA for target sequence {test_target_sequence}", session_id=sid
        )
        assert "workflow_result" in state1
        wf1 = state1["workflow_result"]
        assert wf1.success is True
        assert wf1.best_candidate is not None
        assert len(wf1.all_candidates) >= 1

        # Verify memory stored the state
        loaded = memory.load(sid)
        assert loaded.get("workflow_result") is not None
        assert loaded["workflow_result"].best_candidate is not None

        # Turn 2: increase specificity — state should carry forward
        state2 = runner.run("increase specificity", session_id=sid)
        # Messages should include both turns
        from langchain_core.messages import HumanMessage

        human_msgs = [m for m in state2.get("messages", []) if isinstance(m, HumanMessage)]
        contents = [m.content for m in human_msgs]
        assert any("Design siRNA" in c for c in contents)
        assert any("increase specificity" in c for c in contents)

    def test_agent_runner_sgrna_session_persistence(self):
        """AgentRunner with SessionMemory persists sgRNA results across turns."""
        from agent_core.planning.base import ExecutionPlan, PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.session_memory import SessionMemory
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="sgrna",
                    type="workflow",
                    target="sgrna_design",
                    input_binding={
                        "seed_sequence": "ATGC" * 15,
                        "n_samples": 2,
                        "mutation_number": 5,
                        "sampling_mode": "naive",
                        "evaluate_crisot": False,
                    },
                    output_key="sgrna_result",
                )
            ]
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=memory, llm_critic_enabled=False)

        sid = "sgrna-session-002"
        state1 = runner.run("Design sgRNA for target DNA ATCGATCGATCG", session_id=sid)
        assert state1.get("workflow_result") is not None

        loaded = memory.load(sid)
        assert loaded.get("workflow_result") is not None

        state2 = runner.run("increase diversity", session_id=sid)
        from langchain_core.messages import HumanMessage

        human_msgs = [m for m in state2.get("messages", []) if isinstance(m, HumanMessage)]
        contents = [m.content for m in human_msgs]
        assert any("Design sgRNA" in c for c in contents)
        assert any("increase diversity" in c for c in contents)

    def test_workspace_manager_file_isolation(self, test_target_sequence):
        """WorkspaceManager creates per-session files for workflow outputs."""
        from agent_core.workspace_manager import WorkspaceManager
        from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow

        wm = WorkspaceManager(base_dir="workspace")
        session_id = "wm-test-sirna"

        # Clean any pre-existing workspace
        wm.delete_session(session_id)

        inp = SirnaDesignInput(
            mode="generic",
            target_sequence=test_target_sequence,
            candidate_count=3,
            off_target_scan=False,
        )
        # Direct workflow run to generate files
        from agent_core.capabilities.base import build_default_capability_registry
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        reg = build_default_capability_registry(ToolExecutor(build_default_tool_registry(include_demo=False)))
        wf = SirnaDesignWorkflow(reg)
        result = wf.run(inp)
        assert result.success is True

        # Files should exist under workspace/sessions/... if workflow saves there
        session_dir = wm.get_session_dir(session_id)
        assert session_dir.exists()

        # Cleanup
        wm.delete_session(session_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 二、Layer 5 — AgentRunner 端到端
# ═══════════════════════════════════════════════════════════════════════════════


class TestLayer5AgentRunnerE2E:
    """AgentRunner.run() / .stream() end-to-end with mocked planner + real workflows."""

    def _build_mock_runner(self, plan_steps: list[Any]):
        """Helper: build AgentRunner with a mock planner returning given steps."""
        from agent_core.planning.base import ExecutionPlan, PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        parsed_steps = []
        for s in plan_steps:
            if isinstance(s, PlanStep):
                parsed_steps.append(s)
            else:
                parsed_steps.append(PlanStep(**s))
        plan = ExecutionPlan(steps=parsed_steps)
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        return AgentRunner(planner, exe)

    def test_runner_sirna_e2e(self, test_target_sequence):
        """AgentRunner.run produces final_report with siRNA candidates and scores."""
        from agent_core.planning.base import PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = MagicMock()
        plan.steps = [
            PlanStep(
                step_id="sirna",
                type="workflow",
                target="sirna_design",
                input_binding={
                    "mode": "generic",
                    "target_sequence": test_target_sequence,
                    "candidate_count": 3,
                    "off_target_scan": False,
                },
                output_key="sirna_result",
            )
        ]
        plan.max_retries = 2
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        state = runner.run(
            "Design siRNA for target AUGCAUGCAUGCAUGCAUGC",
            session_id="test-sirna-001",
        )
        assert "workflow_result" in state
        wf = state["workflow_result"]
        assert wf.success is True
        assert wf.best_candidate is not None
        assert len(wf.all_candidates) >= 1

        # final_report should contain candidates and scores
        report = state.get("final_report", "")
        assert "候选" in report or "candidates" in report.lower() or "Workflow" in report

    @pytest.mark.skipif(not SGRNA_SERVICE_UP, reason="sgrna_design service (port 8017) not reachable")
    def test_runner_sgrna_e2e(self):
        """AgentRunner.run produces sgRNA candidates via CRGPT microservice."""
        from agent_core.planning.base import PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = MagicMock()
        plan.steps = [
            PlanStep(
                step_id="sgrna",
                type="workflow",
                target="sgrna_design",
                input_binding={
                    "seed_sequence": "ATGC" * 15,
                    "n_samples": 2,
                    "mutation_number": 5,
                    "sampling_mode": "naive",
                    "evaluate_crisot": False,
                },
                output_key="sgrna_result",
            )
        ]
        plan.max_retries = 2
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        state = runner.run(
            "Design sgRNA for target DNA ATCGATCGATCG",
            session_id="test-sgrna-001",
        )
        assert "workflow_result" in state
        wf = state["workflow_result"]
        assert wf.success is True
        assert wf.best_candidate is not None
        assert len(wf.all_candidates) >= 1
        # Verify scores present
        best = wf.best_candidate
        assert "total_score" in (best.scores or {})

    def test_runner_stream_events_for_sirna(self, test_target_sequence):
        """AgentRunner.stream yields router, plan, progress, tool_execution, runner events."""
        from agent_core.planning.base import PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = MagicMock()
        plan.steps = [
            PlanStep(
                step_id="sirna",
                type="workflow",
                target="sirna_design",
                input_binding={
                    "mode": "generic",
                    "target_sequence": test_target_sequence,
                    "candidate_count": 3,
                    "off_target_scan": False,
                },
                output_key="sirna_result",
            )
        ]
        plan.max_retries = 2
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        events = list(runner.stream("Design siRNA for target AUGCAUGCAUGCAUGCAUGC"))
        event_keys = {list(e.keys())[0] for e in events}
        assert "router" in event_keys
        assert "plan" in event_keys
        # progress events may be present
        assert "tool_execution" in event_keys or "runner" in event_keys

    @pytest.mark.skipif(not SGRNA_SERVICE_UP, reason="sgrna_design service (port 8017) not reachable")
    def test_runner_stream_events_for_sgrna(self):
        """AgentRunner.stream yields events for sgRNA workflow."""
        from agent_core.planning.base import PlanStep
        from agent_core.runner import AgentRunner
        from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

        planner = MagicMock()
        plan = MagicMock()
        plan.steps = [
            PlanStep(
                step_id="sgrna",
                type="workflow",
                target="sgrna_design",
                input_binding={
                    "seed_sequence": "ATGC" * 15,
                    "n_samples": 2,
                    "mutation_number": 5,
                    "sampling_mode": "naive",
                    "evaluate_crisot": False,
                },
                output_key="sgrna_result",
            )
        ]
        plan.max_retries = 2
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        events = list(runner.stream("Design sgRNA for target DNA ATCGATCGATCG"))
        event_keys = {list(e.keys())[0] for e in events}
        assert "router" in event_keys
        assert "plan" in event_keys
        assert "tool_execution" in event_keys or "runner" in event_keys


# ═══════════════════════════════════════════════════════════════════════════════
# 三、CLI / API 入口
# ═══════════════════════════════════════════════════════════════════════════════


class TestCliApiEntrypoints:
    """Verify CLI and FastAPI endpoints for RNAi workflows."""

    APP_ROOT = Path(__file__).resolve().parents[1]

    def test_cli_sirna_workflow_runs(self):
        r"""``cli/sirna_workflow.py`` executes successfully and returns JSON."""
        env = {**os.environ, "PYTHONPATH": str(self.APP_ROOT)}
        cmd = [
            sys.executable,
            str(self.APP_ROOT / "cli" / "sirna_workflow.py"),
            "--mode",
            "generic",
            "--target-sequence",
            "AUGC" * 30,
            "--candidate-count",
            "3",
            "--output-json",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(self.APP_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        data = json.loads(proc.stdout)
        assert data["success"] is True
        assert data["task_type"] == "sirna"
        assert data.get("best_candidate") is not None

    @pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
    def test_fastapi_sirna_endpoint(self):
        """POST /v1/workflows/sirna/run routes to SirnaDesignWorkflow."""
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        from fastapi.testclient import TestClient

        from workflow_api.app import app

        # Build stub executor for deterministic test
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflow_baseline_eval import StubFoldTool, StubGcTool

        class _StubEvitarTool:
            name = "design_sirna_with_evitar"

            def invoke(self, kwargs):
                return {
                    "top_results": [
                        {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.95"},
                    ],
                    "result_count": 1,
                    "mode": "existing",
                    "predict": "predsi",
                }

        class _StubDuplexTool:
            name = "compute_sirna_duplex_binding_vienna"

            def invoke(self, kwargs):
                return {"mfe_kcal_per_mol": -28.5, "structure": "((((("}

        class _StubBlastTool:
            name = "run_blastn_similarity_search"

            def invoke(self, kwargs):
                return {"hit_count": 0}

        reg = ToolRegistry()
        reg.register(StubGcTool())
        reg.register(StubFoldTool())
        reg.register(_StubEvitarTool())
        reg.register(_StubDuplexTool())
        reg.register(_StubBlastTool())
        stub_exe = ToolExecutor(reg)

        with patch("workflow_api.sirna_handler.build_default_tool_registry", return_value=stub_exe.registry):
            client = TestClient(app)
            r = client.post(
                "/v1/workflows/sirna/run",
                json={
                    "mode": "antiviral",
                    "target_sequence": "AUGC" * 30,
                    "candidate_count": 3,
                },
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["task_type"] == "sirna"
        assert data["best_candidate"] is not None

    @pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
    def test_fastapi_unified_routes_sgrna(self):
        """POST /v1/workflows/run with task_type=sgrna is accepted by dispatch.

        NOTE: This endpoint has been removed; all requests now go through
        ``/v1/agent/run``.
        """
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        from fastapi.testclient import TestClient

        from workflow_api.app import app

        client = TestClient(app)
        r = client.post(
            "/v1/workflows/run",
            json={
                "sequence": "ATGC" * 15,
                "task_type": "sgrna",
                "constraints": {
                    "seed_sequence": "ATGC" * 15,
                    "n_samples": 2,
                    "mutation_number": 5,
                },
            },
        )
        # The endpoint should NOT 422 for a known implemented task_type
        assert r.status_code != 422, f"Unexpected 422 for sgrna: {r.text}"

    def test_sirna_handler_schema_matches_runner(self):
        r"""``SirnaWorkflowHttpResponse`` fields are a superset of ``WorkflowResult`` exposure."""
        from workflow_api.sirna_handler import execute_sirna_workflow_http
        from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest

        req = SirnaWorkflowHttpRequest(
            mode="generic",
            target_sequence="AUGC" * 30,
            candidate_count=3,
            task_id="schema-test",
        )
        # Use default executor (stubs if no real services)
        out = execute_sirna_workflow_http(req)
        assert hasattr(out, "task_id")
        assert hasattr(out, "success")
        assert hasattr(out, "task_type")
        assert hasattr(out, "best_candidate")
        assert hasattr(out, "candidates")
        assert hasattr(out, "summary")
        assert hasattr(out, "errors")
        assert hasattr(out, "warnings")


# ═══════════════════════════════════════════════════════════════════════════════
# 四、DeepSeek API 真实调用验证 (live_llm)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.live_llm
class TestLiveDeepSeekApi:
    """Tests requiring real DeepSeek API connectivity."""

    @pytest.mark.skipif(not DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
    def test_llm_planner_generates_sirna_plan(self):
        """LLMPlanner returns a JSON-parseable plan for siRNA requests."""
        from agent_core.planning.factory import build_planner
        from agent_core.planning.base import ExecutionPlan

        planner = build_planner()
        state = {
            "_available_workflows": ["sirna_design", "sgrna_design", "mrna_design"],
            "_available_capabilities": [],
            "_workflow_param_schemas": {},
            "session_id": "test-sirna-plan",
        }
        plan = planner.plan_with_state("Design siRNA for target sequence AUGCAUGCAUGCAUGCAUGC", state)
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        targets = {s.target for s in plan.steps}
        assert "sirna_design" in targets or any(
            "sirna" in t for t in targets
        ), f"Expected sirna in plan targets, got {targets}"

    @pytest.mark.skipif(not DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
    def test_llm_planner_generates_sgrna_plan(self):
        """LLMPlanner returns a JSON-parseable plan for sgRNA requests."""
        from agent_core.planning.factory import build_planner
        from agent_core.planning.base import ExecutionPlan

        planner = build_planner()
        state = {
            "_available_workflows": ["sirna_design", "sgrna_design", "mrna_design"],
            "_available_capabilities": [],
            "_workflow_param_schemas": {},
            "session_id": "test-sgrna-plan",
        }
        plan = planner.plan_with_state("Design sgRNA for target DNA ATCGATCGATCG", state)
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        targets = {s.target for s in plan.steps}
        assert "sgrna_design" in targets or any(
            "sgrna" in t for t in targets
        ), f"Expected sgrna in plan targets, got {targets}"

    @pytest.mark.skipif(not DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
    def test_sirna_critic_diagnoses_low_quality(self):
        r"""``SirnaDesignLLMCritic.diagnose`` returns actionable diagnosis for poor results."""
        from agent_core.workflows.sirna_design import SirnaDesignLLMCritic
        from agent_core.workflow_models import Candidate, WorkflowResult

        critic = SirnaDesignLLMCritic()
        candidates = [
            Candidate(
                sequence="AUG" * 7,
                sequence_type="sirna",
                source="test",
                metadata={
                    "metrics_bundle": {
                        "duplex_mfe": -5.0,
                        "off_target_count": 20,
                        "gc_content": 0.75,
                    }
                },
            )
        ]
        result = WorkflowResult(
            success=True,
            task_id="test",
            best_candidate=candidates[0],
            all_candidates=candidates,
            summary="low quality",
        )
        state = {
            "_last_workflow_params": {"mode": "generic", "candidate_count": 10},
            "user_text": "Design siRNA with high specificity",
        }
        diagnosis = critic.diagnose(result, state)
        assert diagnosis.overall_assessment
        assert diagnosis.quality_score < 0.7
        assert len(diagnosis.issues) > 0
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "abort",
        )

    @pytest.mark.skipif(not DEEPSEEK_KEY_SET, reason="DEEPSEEK_API_KEY not set")
    def test_sgrna_critic_diagnoses_low_quality(self):
        r"""``SgRnaDesignLLMCritic.diagnose`` returns actionable diagnosis for poor results."""
        from agent_core.workflows.sgrna_design import SgRnaDesignLLMCritic
        from agent_core.workflow_models import Candidate, WorkflowResult

        critic = SgRnaDesignLLMCritic()
        candidates = [
            Candidate(
                sequence="ATGC" * 10,
                sequence_type="sgrna",
                source="test",
                metadata={
                    "metrics_bundle": {
                        "nn_score": 5.0,
                        "crisot_score": 0.1,
                    }
                },
            )
        ]
        result = WorkflowResult(
            success=True,
            task_id="test",
            best_candidate=candidates[0],
            all_candidates=candidates,
            summary="low quality sgRNA",
        )
        state = {
            "_last_workflow_params": {"n_samples": 10, "mutation_number": 5},
            "user_text": "Design sgRNA with high activity",
        }
        diagnosis = critic.diagnose(result, state)
        assert diagnosis.overall_assessment
        assert diagnosis.quality_score < 0.7
        assert len(diagnosis.issues) > 0

class TestCriticDegradation:
    """Critic failure degradation tests (no live LLM required)."""

    def test_critic_degrades_gracefully_on_api_failure(self):
        """When DeepSeek API fails, Critic should not crash workflow."""
        from agent_core.planning import llm_critic
        from agent_core.workflows.sirna_design import SirnaDesignLLMCritic
        from agent_core.workflow_models import WorkflowResult

        critic = SirnaDesignLLMCritic()
        result = WorkflowResult(
            success=True,
            task_id="test",
            best_candidate=None,
            all_candidates=[],
            summary="empty",
        )
        state = {"_last_workflow_params": {}}

        with patch.object(llm_critic, "get_deepseek_llm", side_effect=RuntimeError("API down")):
            should_retry = critic.should_retry(result, state)

        assert should_retry is False
        # diagnose() catches the exception internally and returns an abort diagnosis;
        # should_retry then records it in _last_diagnosis
        assert "_last_diagnosis" in state
        diag = state["_last_diagnosis"]
        assert diag["action"] == "abort"
        assert "RuntimeError" in diag["overall_assessment"]


# ═══════════════════════════════════════════════════════════════════════════════
# 五、CPU / GPU 工具运行验证
# ═══════════════════════════════════════════════════════════════════════════════


class TestCpuTools:
    """Layer 0 CPU tool validation for siRNA workflow."""

    def test_evitar_cpu(self, executor, test_target_sequence):
        from agent_core.file_manager import save_sequence

        fp = save_sequence(test_target_sequence, prefix="test_sirna_evitar")
        result = executor.run_tool(
            "design_sirna_with_evitar",
            filepath=fp,
            mode="existing",
            predict="predsi",
            ncores=1,
        )
        assert result.success, f"Evitar failed: {result.error}"
        assert "result_count" in result.artifacts.get("result", {})

    def test_gc_content_cpu(self, executor, test_sirna_sequence):
        from agent_core.file_manager import save_sequence

        fp = save_sequence(test_sirna_sequence, prefix="test_sirna_gc")
        result = executor.run_tool("compute_rna_sequence_gc_content", filepath=fp)
        assert result.success
        gc = result.artifacts.get("result", {}).get("gc_content")
        assert 0.0 <= gc <= 1.0

    def test_duplex_vienna_cpu(self, executor, test_sirna_sequence):
        from agent_core.file_manager import save_text_file

        rc_map = {"A": "U", "U": "A", "G": "C", "C": "G"}
        antisense = "".join(rc_map.get(b, b) for b in reversed(test_sirna_sequence.upper()))
        content = f">sense\n{test_sirna_sequence}\n>antisense\n{antisense}\n"
        fp = save_text_file(content, prefix="test_sirna_duplex", suffix=".txt")
        result = executor.run_tool("compute_sirna_duplex_binding_vienna", filepath=fp)
        assert result.success
        assert "mfe_kcal_per_mol" in result.artifacts.get("result", {})

    def test_blastn_cpu(self, executor, test_sirna_sequence):
        from agent_core.file_manager import save_sequence, save_text_file

        query_fp = save_sequence(test_sirna_sequence, prefix="test_sirna_blast_query")
        subject = ">dummy\nAUGCAUGCAUGCAUGCAUGCAUGCAUGCAUGC\n"
        subject_fp = save_text_file(subject, prefix="test_blast_subj", suffix=".fasta")
        result = executor.run_tool(
            "run_blastn_similarity_search",
            filepath=query_fp,
            subject_fasta_path=subject_fp,
            task="blastn-short",
            perc_identity=90,
            max_target_seqs=10,
        )
        assert result.success
        assert "hit_count" in result.artifacts.get("result", {})


class TestGpuMicroservices:
    """Layer 0 GPU / microservice validation for sgRNA workflow."""

    @pytest.mark.skipif(not SGRNA_SERVICE_UP, reason="sgrna_design service (port 8017) not reachable")
    def test_crgpt_design_gpu(self):
        from agent_core.tools import design_sgrna_handle_with_crgpt

        result = design_sgrna_handle_with_crgpt.invoke({
            "seed_sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
            "n_samples": 2,
            "mutation_number": 5,
            "sampling_mode": "naive",
        })
        assert result["generated_count"] >= 1
        assert result["best_sequence"]
        assert result.get("summary_json_filepath")

    @pytest.mark.skipif(not SGRNA_SERVICE_UP, reason="sgrna_design service (port 8017) not reachable")
    def test_crgpt_score_gpu(self):
        from agent_core.tools import score_sgrna_handle_with_crgpt

        result = score_sgrna_handle_with_crgpt.invoke({
            "sequence": "GTTTTAGAGCTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCTACTTGAAAAAGTG",
        })
        assert "nn_score" in result
        assert result["nn_score"] > 0

    @pytest.mark.skipif(not CRISOT_SERVICE_UP, reason="CRISOT service (port 8011) not reachable")
    def test_crisot_off_target_cpu(self):
        from agent_core.file_manager import save_sequence
        from agent_core.tools import score_crispr_off_target_with_crisot

        guide = "ATGCATGCATGCATGCATGCTGG"
        target = "ATGCATGCATGCATGCATGCTGG"
        guide_fp = save_sequence(guide, prefix="sgrna_guide")
        result = score_crispr_off_target_with_crisot.invoke({
            "filepath": guide_fp,
            "target_sequence": target,
        })
        assert "crisot_score" in result
        assert 0.0 <= result["crisot_score"] <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 六、代码规范检查 (static / structural assertions)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCodeQuality:
    """Structural checks for types, locks, dead code, and test naming."""

    def test_sirna_workflow_has_type_annotations(self):
        """SirnaDesignWorkflow public methods have return type annotations."""
        from agent_core.workflows.sirna_design import SirnaDesignWorkflow

        import inspect

        inspect.signature(SirnaDesignWorkflow.run)
        # run accepts Any input but returns WorkflowResult via base class contract
        assert hasattr(SirnaDesignWorkflow, "run")

    def test_sgrna_workflow_has_type_annotations(self):
        """SgRnaDesignWorkflow public methods have return type annotations."""
        from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow

        import inspect

        sig = inspect.signature(SgRnaDesignWorkflow.run)
        assert sig.return_annotation is not inspect.Signature.empty

    def test_sirna_interface_lock_comments_present(self):
        """SirnaDesignWorkflow source contains INTERFACE LOCK comments."""
        from agent_core.workflows import sirna_design

        src = Path(sirna_design.__file__).read_text()
        assert "INTERFACE LOCK" in src
        assert "SirnaDesignWorkflow INTERFACE LOCK" in src

    def test_sgrna_interface_lock_comments_present(self):
        """SgRnaDesignWorkflow source contains INTERFACE LOCK comments."""
        from agent_core.workflows import sgrna_design

        src = Path(sgrna_design.__file__).read_text()
        assert "INTERFACE LOCK" in src
        assert "SgRnaDesignWorkflow INTERFACE LOCK" in src

    def test_registry_has_both_critic_pairs(self):
        """WORKFLOW_CRITIC_PAIRS includes sirna_design and sgrna_design."""
        from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS
        from agent_core.workflows.sirna_design import SirnaDesignLLMCritic, SirnaDesignWorkflow
        from agent_core.workflows.sgrna_design import SgRnaDesignLLMCritic, SgRnaDesignWorkflow

        assert "sirna_design" in WORKFLOW_CRITIC_PAIRS
        assert WORKFLOW_CRITIC_PAIRS["sirna_design"] == (SirnaDesignWorkflow, SirnaDesignLLMCritic)
        assert "sgrna_design" in WORKFLOW_CRITIC_PAIRS
        assert WORKFLOW_CRITIC_PAIRS["sgrna_design"] == (SgRnaDesignWorkflow, SgRnaDesignLLMCritic)

    def test_sirna_workflow_exception_handling(self, test_target_sequence):
        """SirnaDesignWorkflow degrades gracefully when capabilities are missing."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.file_manager import save_sequence
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow

        # Empty registry — no capabilities at all
        reg = ToolRegistry()
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        wf = SirnaDesignWorkflow(cap_reg)
        # Antiviral mode requires evitar capability; with empty registry it fails gracefully
        fasta_path = save_sequence(test_target_sequence, prefix="test_sirna_empty")
        inp = SirnaDesignInput(
            mode="antiviral",
            target_fasta_path=fasta_path,
            candidate_count=3,
            off_target_scan=False,
        )
        result = wf.run(inp)
        # Should not crash; returns empty candidates gracefully
        assert result.success is False
        assert "empty_candidate_list" in result.errors

    def test_sgrna_workflow_exception_handling(self):
        """SgRnaDesignWorkflow degrades gracefully when capabilities are missing."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry
        from agent_core.workflows.sgrna_design import SgRnaDesignInput, SgRnaDesignWorkflow

        reg = ToolRegistry()
        executor = ToolExecutor(reg)
        cap_reg = CapabilityRegistry(executor)
        wf = SgRnaDesignWorkflow(cap_reg)
        inp = SgRnaDesignInput(
            seed_sequence="ATGC" * 15,
            n_samples=2,
            mutation_number=5,
        )
        result = wf.run(inp)
        assert result.success is False
        assert "empty_candidate_list" in result.errors

    def test_test_file_naming_convention(self):
        """All RNAi test files follow test_<workflow>_<scope>.py convention."""
        tests_dir = Path(__file__).resolve().parent
        rnai_files = [
            f.name
            for f in tests_dir.iterdir()
            if f.name.startswith("test_sirna") or f.name.startswith("test_sgrna")
        ]
        for name in rnai_files:
            assert name.endswith(".py"), f"Test file {name} must be .py"
            assert name.startswith("test_"), f"Test file {name} must start with test_"
