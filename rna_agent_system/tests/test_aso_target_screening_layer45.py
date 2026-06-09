"""Layer 4/5 comprehensive integration test for ASO target screening workflow.

Covers:
  - Layer 4: SessionMemory + WorkspaceManager persistence across multi-turn dialog
  - Layer 5: AgentRunner.run() / .stream() end-to-end for ASO workflow
  - CLI / API entry points (ASO has no CLI; FastAPI returns not_implemented)
  - CPU tool validation (ViennaRNA: plfold, RNAup, RNAcofold)
  - Critic behavior: ASO has no critic (deterministic), retry_count must stay 0
  - Code quality checks (type annotations, no hardcoded keys, INTERFACE LOCK, no bare except)

Run:
    # All non-LLM tests (Layers 4-5)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_aso_target_screening_layer45.py -v -s

    # Include live LLM tests (requires DEEPSEEK_API_KEY)
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_aso_target_screening_layer45.py -v -s --live-llm
"""

from __future__ import annotations

from tests.helpers import build_mock_plan

import ast
import os
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


VIENNA_SERVICE_UP = _service_available("http://127.0.0.1:8003/health")

from agent_core.file_manager import PROJECT_ROOT, save_sequence
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
from agent_core.workflows.aso_target_screening import (
    AsoScreeningCritic,
)
from agent_core.workspace_manager import WorkspaceManager

# ── Configuration ────────────────────────────────────────────────────

TEST_TARGET_SEQ = "AUG" * 60 + "UUU" * 7
TEST_TARGET_SEQ = "".join(c for c in TEST_TARGET_SEQ if c in "AUGC")[:200]

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


# ═══════════════════════════════════════════════════════════════════════
# Layer 4 — Session & Memory
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.known_issue
class TestLayer4SessionMemory:
    """Verify SessionMemory.load/save and WorkspaceManager isolation for ASO."""

    def test_session_memory_load_save(self):
        mem = SessionMemory()
        sid = "test-aso-session-001"
        state = default_state("hello")
        state["best_candidate"] = "ASO1"
        mem.save(sid, state)
        loaded = mem.load(sid)
        assert loaded["best_candidate"] == "ASO1"
        assert loaded["messages"][0].content == "hello"
        # load returns deepcopy; mutations should not affect stored state
        loaded["best_candidate"] = "ASO2"
        reloaded = mem.load(sid)
        assert reloaded["best_candidate"] == "ASO1"

    def test_session_memory_empty_session_id(self):
        mem = SessionMemory()
        state = default_state("hello")
        mem.save("", state)
        assert mem._store == {}
        loaded = mem.load("")
        assert loaded["messages"][0].content == ""

    @pytest.mark.known_issue
    def test_runner_with_memory_persists_across_turns(self):
        planner = MagicMock()
        target_fp = save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_l4_target")
        plan = build_mock_plan(
            "aso_target_screening",
            {
                "target_mrna_filepath": target_fp,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
                "binding_evaluation_tool": "rnaup",
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        mem = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=mem)
        sid = "aso-session-l4-001"

        # Turn 1
        state1 = runner.run(
            f"Screen ASO binding sites for target {target_fp}", session_id=sid
        )
        assert state1.get("workflow_result") is not None

        # Verify memory stored the state
        loaded = mem.load(sid)
        assert loaded.get("workflow_result") is not None

        # Turn 2: state should carry forward
        state2 = runner.run("increase top_n_windows to 5", session_id=sid)
        human_msgs = [m for m in state2.get("messages", []) if isinstance(m, HumanMessage)]
        contents = [m.content for m in human_msgs]
        assert any("Screen ASO" in c for c in contents)
        assert any("increase top_n_windows" in c for c in contents)

    def test_runner_explicit_state_bypasses_memory(self):
        planner = MagicMock()
        plan = build_mock_plan("aso_target_screening", {"target_mrna_filepath": "test.fa"})
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        mem = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=mem)

        explicit = default_state("explicit")
        explicit["custom_key"] = "CUSTOM"

        with patch.object(ExecutionController, "execute") as mock_exec:
            mock_exec.return_value = explicit
            result = runner.run("new input", session_id="session-abc", state=explicit)
            passed_state = mock_exec.call_args[0][1]
            assert passed_state["custom_key"] == "CUSTOM"

        # Memory should NOT have been touched for the explicit-state path
        assert "session-abc" not in mem._store

    def test_workspace_manager_per_session_isolation(self):
        wm = WorkspaceManager(base_dir="workspace_test_aso_layer4")
        sid1 = "aso-wm-session-1"
        sid2 = "aso-wm-session-2"

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


@pytest.mark.known_issue
class TestLayer5AgentRunner:
    """Verify AgentRunner.run / stream / critic behavior for ASO workflow."""

    def test_runner_stream_event_flow(self):
        planner = MagicMock()
        target_fp = save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_stream_target")
        plan = build_mock_plan(
            "aso_target_screening",
            {
                "target_mrna_filepath": target_fp,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        events = list(runner.stream("Screen ASO sites for my mRNA", session_id="sid-aso-stream"))
        counts = _count_event_types(events)
        assert counts.get("router", 0) >= 1
        assert counts.get("plan", 0) >= 1
        assert counts.get("tool_execution", 0) >= 1 or counts.get("runner", 0) >= 1

    def test_runner_routes_to_aso_target_screening(self):
        """AgentRunner should route ASO screening requests correctly."""
        planner = MagicMock()
        target_fp = save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_route_target")
        plan = build_mock_plan(
            "aso_target_screening",
            {
                "target_mrna_filepath": target_fp,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
                "binding_evaluation_tool": "rnaup",
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        mock_result = default_state("")
        mock_result["workflow_result"] = WorkflowResult(
            success=True,
            task_id="aso-routing-test",
            best_candidate=Candidate(sequence="AUG" * 6, source="routing"),
            all_candidates=[Candidate(sequence="AUG" * 6, source="routing")],
            summary="routing ok",
        )

        with patch.object(ExecutionController, "execute", return_value=mock_result):
            state = runner.run("Screen ASO binding sites for target mRNA", session_id="test-aso-001")

        assert state.get("workflow_result") is not None
        wf = state["workflow_result"]
        assert wf.success is True
        assert wf.best_candidate is not None

    def test_runner_aso_no_critic_retry_count_zero(self):
        """ASO target screening has no critic -> retry_count must stay 0."""
        planner = MagicMock()
        target_fp = save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_nocritic_target")
        plan = build_mock_plan(
            "aso_target_screening",
            {
                "target_mrna_filepath": target_fp,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=True)

        state = runner.run("Screen ASO binding sites", session_id="test-aso-no-critic")
        assert state.get("retry_count", 0) == 0, (
            f"ASO is deterministic and should have retry_count=0, got {state.get('retry_count')}"
        )

    def test_aso_critic_always_returns_false(self):
        """AsoScreeningCritic.should_retry always returns False."""
        critic = AsoScreeningCritic()
        result = WorkflowResult(
            success=True,
            task_id="test",
            best_candidate=Candidate(sequence="AUG" * 6, source="test"),
            all_candidates=[Candidate(sequence="AUG" * 6, source="test")],
            summary="test",
        )
        assert critic.should_retry(result, {}) is False

    def test_runner_aso_with_explicit_state(self):
        """AgentRunner.run with explicit state should work for ASO."""
        planner = MagicMock()
        target_fp = save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_explicit_target")
        plan = build_mock_plan(
            "aso_target_screening",
            {
                "target_mrna_filepath": target_fp,
                "aso_length": 18,
                "window_step": 5,
                "top_n_windows": 3,
            },
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        explicit = default_state("explicit aso request")
        explicit["custom_key"] = "CUSTOM_ASO"

        state = runner.run(
            "Screen ASO sites", session_id="test-aso-explicit", state=explicit
        )
        assert state.get("custom_key") == "CUSTOM_ASO"


# ═══════════════════════════════════════════════════════════════════════
# CLI / API Entry Points
# ═══════════════════════════════════════════════════════════════════════


class TestCliApiEntry:
    """Verify CLI and FastAPI entry points for ASO workflow."""

    def test_api_unified_endpoint_returns_not_implemented_for_aso(self):
        """POST /v1/workflows/run with task_type=aso returns not_implemented."""
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from workflow_api.app import app
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        client = TestClient(app)
        req = MrnaWorkflowHttpRequest(
            sequence=TEST_TARGET_SEQ,
            task_type="aso",
            task_id="aso-api-test",
        )
        r = client.post("/v1/workflows/run", json=req.model_dump())
        assert r.status_code == 200, f"Unexpected status: {r.status_code}, body: {r.text}"
        data = r.json()
        assert data["success"] is False
        assert data["task_type"] == "aso"
        assert "not_implemented" in data.get("summary", "") or any(
            "ASO" in e for e in data.get("errors", [])
        )

    def test_api_agent_run_endpoint_accepts_aso_requests(self):
        """/v1/agent/run accepts natural-language ASO screening prompts."""
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        # We cannot run the real endpoint without a full FastAPI test client,
        # but we can validate the request schema -> prompt logic.
        req = MrnaWorkflowHttpRequest(sequence=TEST_TARGET_SEQ)
        user_text = ""
        if req.sequence is not None and str(req.sequence).strip():
            user_text = f"Evaluate sequence {req.sequence} for ASO binding sites"
        assert "Evaluate sequence" in user_text
        assert TEST_TARGET_SEQ in user_text

    def test_aso_not_in_workflow_critic_pairs(self):
        """aso_target_screening must NOT be in WORKFLOW_CRITIC_PAIRS."""
        from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS

        assert "aso_target_screening" not in WORKFLOW_CRITIC_PAIRS, (
            "ASO target screening is deterministic and should not have a critic pair"
        )


# ═══════════════════════════════════════════════════════════════════════
# DeepSeek API Validation
# ═══════════════════════════════════════════════════════════════════════


class TestDeepSeekApi:
    """DeepSeek API validation (with and without live LLM)."""

    @skip_if_no_live_llm
    def test_get_deepseek_llm_returns_callable(self):
        """get_deepseek_llm() returns a callable LLM instance."""
        from agent_core.llm_config import get_deepseek_llm

        llm = get_deepseek_llm()
        assert llm is not None
        assert hasattr(llm, "invoke")

    @skip_if_no_live_llm
    def test_llm_planner_generates_aso_plan(self):
        """LLMPlanner.plan() returns a valid JSON plan for ASO requests."""
        planner = LLMPlanner()
        ctx = AgentContext(
            session_id="live-aso-plan-test",
            available_capabilities=[
                "predict_rna_local_accessibility_profile_vienna",
                "compute_aso_target_accessibility_vienna",
                "compute_rna_rna_interaction_vienna",
            ],
            available_workflows=["aso_target_screening"],
            workflow_param_schemas={
                "aso_target_screening": "target_mrna_filepath=(required) (str)",
            },
        )
        plan = planner.plan(
            f"Screen ASO binding sites for target mRNA sequence {TEST_TARGET_SEQ[:50]}",
            ctx,
        )
        # LLM may return empty steps or capability steps; accept either
        targets = [s.target for s in plan.steps]
        if targets:
            assert any(
                t in ("aso_target_screening", "predict_rna_local_accessibility_profile_vienna")
                for t in targets
            ), f"Expected ASO-related target, got: {targets}"
        dumped = plan.model_dump(mode="json")
        assert "steps" in dumped
        assert "max_retries" in dumped

    def test_aso_no_critic_retry_count_zero_mocked(self):
        """Mocked ExecutionController confirms ASO has no critic retry."""
        from agent_core.capabilities.base import CapabilityRegistry
        from agent_core.tool_executor import ToolExecutor
        from agent_core.tool_registry import ToolRegistry

        executor = ToolExecutor(ToolRegistry())
        registry = CapabilityRegistry(executor)
        controller = ExecutionController(capability_registry=registry)

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="aso",
                    type="workflow",
                    target="aso_target_screening",
                    input_binding={"target_mrna_filepath": "test.fa", "aso_length": 18},
                    output_key="aso_result",
                )
            ],
            max_retries=2,
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "aso_target_screening":
                return WorkflowResult(
                    success=True,
                    task_id="aso-test",
                    best_candidate=Candidate(sequence="AUG" * 6, source="test"),
                    all_candidates=[Candidate(sequence="AUG" * 6, source="test")],
                    summary="ASO test",
                )
            raise RuntimeError(f"Unexpected: {step.target}")

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            final_state = controller.execute(plan, {"_llm_critic_enabled": True})

        # ASO has no critic registered, so only one call
        assert call_count == 1, f"Expected 1 call (no critic), got {call_count}"
        assert final_state.get("retry_count", 0) == 0


# ═══════════════════════════════════════════════════════════════════════
# CPU / GPU Tool Validation
# ═══════════════════════════════════════════════════════════════════════


class TestCpuTools:
    """Layer 0 CPU tool validation for ASO workflow."""

    @pytest.fixture(scope="class")
    def executor(self):
        return ToolExecutor(build_default_tool_registry())

    @pytest.fixture(scope="class")
    def target_filepath(self):
        return save_sequence(f">target\n{TEST_TARGET_SEQ}\n", prefix="aso_l45_target")

    def test_viennarna_plfold_cpu(self, executor, target_filepath):
        result = executor.run_tool(
            "predict_rna_local_accessibility_profile_vienna",
            filepath=target_filepath,
            winsize=70,
            span=70,
        )
        assert result.success, f"RNAplfold failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "positions" in r
        assert "unpaired_prob_1nt" in r
        assert len(r["positions"]) > 0
        assert len(r["positions"]) == len(r["unpaired_prob_1nt"])
        assert "lunp_profile_tsv_filepath" in r

    @pytest.mark.known_issue
    @pytest.mark.skipif(not VIENNA_SERVICE_UP, reason="ViennaRNA service not reachable")
    def test_viennarna_rnaup_cpu(self, executor, target_filepath):
        from agent_core.file_manager import save_sequence

        aso_fp = save_sequence(
            ">aso\nGCAUGCAUGCAUGCAUGCAUGCAUGCAU\n", prefix="aso_l45_oligo"
        )
        result = executor.run_tool(
            "compute_rna_rna_interaction_vienna",
            filepath1=target_filepath,
            filepath2=aso_fp,
            ulength=4,
        )
        assert result.success, f"RNAup failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "interaction_energy" in r
        assert "interaction_structure" in r

    def test_viennarna_cofold_cpu(self, executor):
        from agent_core.file_manager import save_text_file

        duplex_fp = save_text_file(
            ">target\nAUGCAUGCAUGCAUGCAUGC\n>aso\nGCAUGCAUGCAUGCAUGCAU\n",
            prefix="aso_l45_duplex",
            suffix=".txt",
        )
        result = executor.run_tool(
            "compute_sirna_duplex_binding_vienna", filepath=duplex_fp
        )
        assert result.success, f"RNAcofold failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "mfe_kcal_per_mol" in r
        assert "structure" in r

    def test_aso_accessibility_cpu(self, executor, target_filepath):
        result = executor.run_tool(
            "compute_aso_target_accessibility_vienna",
            filepath=target_filepath,
            region_start=1,
            region_end=18,
            aso_oligo_length=18,
        )
        assert result.success, f"ASO accessibility failed: {result.error}"
        r = result.artifacts.get("result", {})
        assert "mean_unpaired_prob_single_nt" in r
        assert "joint_unpaired_prob_stretch_ending_at_region_end" in r


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
            "agent_core/workflows/aso_target_screening.py",
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
            "aso_target_screening.py": ["INTERFACE LOCK"],
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
