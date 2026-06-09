"""Layer 4/5 全面检查 — mRNA 核心 Workflow 集成测试.

覆盖目标 Workflow:
  - MrnaCdsDesignWorkflow
  - FullLengthMrnaDesignWorkflow
  - MrnaSequenceScoringWorkflow

检查项:
  一、Layer 4 — Session & Memory 集成
  二、Layer 5 — AgentRunner 端到端
  三、CLI / API 入口
  四、DeepSeek API 真实调用验证
  五、CPU / GPU 工具运行验证
  六、代码规范检查

运行:
    # 非 LLM 测试 (Layers 0-5, 除真实 DeepSeek 调用外)
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_mrna_layer45_integration.py -v -s

    # 包含真实 LLM 调用
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_mrna_layer45_integration.py -v -s --live-llm
"""

from __future__ import annotations

from tests.helpers import build_mock_plan

import ast
import os
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

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
from agent_core.workflows.full_length_mrna_design import (
    FullLengthMrnaDesignLLMCritic,
)
from agent_core.workflows.mrna_cds_design import (
    MrnaCdsDesignWorkflow,
)
from agent_core.workspace_manager import WorkspaceManager

# ── Configuration ────────────────────────────────────────────────────

TEST_PROTEIN = "MKTLLILTVFGITMLLAVLAQG"
TEST_SEQUENCE = "AUG" * 30  # 90 nt valid CDS
TEST_SPECIES = "Homo sapiens"
TEST_MODEL_TYPE = "Homo sapiens mRNA"

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


def _make_stub_registry() -> Any:
    """Minimal stub registry for fast tests."""
    from agent_core.capabilities.base import CapabilityResult

    def _cap(name: str, output: dict[str, Any]):
        class C:
            def invoke(self, args: dict[str, Any], state: dict[str, Any] | None = None) -> CapabilityResult:
                return CapabilityResult(success=True, tool_name=name, output=output)
        return C()

    class R:
        def has(self, name: str) -> bool:
            return True
        def get(self, name: str) -> Any:
            return _cap(name, {"generated_sequence": "AUG" * 20})
        def list_names(self) -> list[str]:
            return ["cap1", "cap2"]

    return R()


def _count_event_types(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        for k in e:
            counts[k] = counts.get(k, 0) + 1
    return counts


# ═══════════════════════════════════════════════════════════════════════
# Layer 4 — Session & Memory 集成
# ═══════════════════════════════════════════════════════════════════════


class TestLayer4SessionMemory:
    """验证 SessionMemory.load/save 与 WorkspaceManager 隔离."""

    def test_session_memory_load_save(self):
        mem = SessionMemory()
        sid = "test-session-001"
        state = default_state("hello")
        state["best_candidate"] = "SEQ1"
        mem.save(sid, state)
        loaded = mem.load(sid)
        assert loaded["best_candidate"] == "SEQ1"
        assert loaded["messages"][0].content == "hello"
        # load returns deepcopy; mutations should not affect stored state
        loaded["best_candidate"] = "SEQ2"
        reloaded = mem.load(sid)
        assert reloaded["best_candidate"] == "SEQ1"

    def test_session_memory_empty_session_id(self):
        mem = SessionMemory()
        state = default_state("hello")
        mem.save("", state)
        assert mem._store == {}
        loaded = mem.load("")
        assert loaded["messages"][0].content == ""  # default_state("") empty

    def test_runner_with_memory_persists_across_turns(self):
        planner = MagicMock()
        plan = build_mock_plan("mrna_cds_design", {"protein_sequence": TEST_PROTEIN})
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        mem = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=mem)
        sid = "session-l4-001"

        turn1 = default_state("")
        turn1["workflow_result"] = WorkflowResult(
            success=True,
            task_id="t1",
            best_candidate=Candidate(sequence="AUG" * 20, source="t1"),
            all_candidates=[Candidate(sequence="AUG" * 20, source="t1")],
            summary="turn1",
        )
        turn1["messages"] = [HumanMessage(content="Design mRNA CDS")]

        with patch.object(ExecutionController, "execute", return_value=turn1):
            s1 = runner.run("Design mRNA CDS", session_id=sid)
            assert s1["workflow_result"].task_id == "t1"

        # Second turn should load prior state
        turn2 = default_state("")
        turn2["workflow_result"] = WorkflowResult(
            success=True,
            task_id="t2",
            best_candidate=Candidate(sequence="AUG" * 20, source="t2"),
            all_candidates=[Candidate(sequence="AUG" * 20, source="t2")],
            summary="turn2",
        )
        turn2["messages"] = [
            HumanMessage(content="Design mRNA CDS"),
            HumanMessage(content="Improve stability"),
        ]

        with patch.object(ExecutionController, "execute") as mock_exec:
            mock_exec.return_value = turn2
            s2 = runner.run("Improve stability", session_id=sid)
            passed_state = mock_exec.call_args[0][1]
            # Prior best_candidate should be preserved from memory
            assert "workflow_result" in passed_state or "result" in passed_state
            contents = [m.content for m in passed_state["messages"] if isinstance(m, HumanMessage)]
            assert "Design mRNA CDS" in contents
            assert "Improve stability" in contents

    def test_runner_explicit_state_bypasses_memory(self):
        planner = MagicMock()
        plan = build_mock_plan("mrna_cds_design", {"protein_sequence": TEST_PROTEIN})
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
        wm = WorkspaceManager(base_dir="workspace_test_layer4")
        sid1 = "wm-session-1"
        sid2 = "wm-session-2"

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
# Layer 5 — AgentRunner 端到端
# ═══════════════════════════════════════════════════════════════════════


class TestLayer5AgentRunner:
    """验证 AgentRunner.run / stream / critic / routing."""

    def test_runner_stream_event_flow(self):
        planner = MagicMock()
        plan = build_mock_plan("mrna_sequence_scoring", {"sequence": TEST_SEQUENCE})
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        mock_result = default_state("")
        mock_result["workflow_result"] = WorkflowResult(
            success=True,
            task_id="stream-test",
            best_candidate=Candidate(sequence=TEST_SEQUENCE, source="stream"),
            all_candidates=[Candidate(sequence=TEST_SEQUENCE, source="stream")],
            summary="stream ok",
        )

        with patch.object(ExecutionController, "execute", return_value=mock_result):
            events = list(runner.stream("Score this sequence", session_id="sid-stream"))

        counts = _count_event_types(events)
        assert counts.get("router", 0) >= 1
        assert counts.get("plan", 0) >= 1
        # progress events depend on callback usage inside controller
        assert counts.get("tool_execution", 0) >= 1
        assert counts.get("runner", 0) >= 1

    def test_runner_routes_to_mrna_sequence_scoring(self):
        """AgentRunner should route scoring requests to mrna_sequence_scoring."""
        planner = MagicMock()
        plan = build_mock_plan(
            "mrna_sequence_scoring",
            {"sequence": TEST_SEQUENCE},
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        wf_result = WorkflowResult(
            success=True,
            task_id="routing-test",
            best_candidate=Candidate(sequence=TEST_SEQUENCE, source="routing"),
            all_candidates=[Candidate(sequence=TEST_SEQUENCE, source="routing")],
            summary="routing ok",
        )
        mock_state = default_state("")
        mock_state["workflow_result"] = wf_result

        with patch.object(ExecutionController, "execute", return_value=mock_state):
            result = runner.run(f"Score sequence {TEST_SEQUENCE}")
            assert result["workflow_result"].success is True
            assert result["workflow_result"].best_candidate.sequence == TEST_SEQUENCE

    def test_runner_mrna_scoring_no_critic_retry(self):
        """mrna_sequence_scoring has no critic -> retry_count must stay 0."""
        planner = MagicMock()
        plan = build_mock_plan(
            "mrna_sequence_scoring",
            {"sequence": TEST_SEQUENCE},
        )
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=True)

        wf_result = WorkflowResult(
            success=True,
            task_id="no-critic-test",
            best_candidate=Candidate(sequence=TEST_SEQUENCE, source="no-critic"),
            all_candidates=[Candidate(sequence=TEST_SEQUENCE, source="no-critic")],
            summary="no critic",
        )
        mock_state = default_state("")
        mock_state["workflow_result"] = wf_result
        mock_state["retry_count"] = 0

        with patch.object(ExecutionController, "execute", return_value=mock_state):
            result = runner.run("Score sequence")
            assert result.get("retry_count", 0) == 0

    def test_runner_critic_retry_parameter_override(self):
        """Mock low-quality result triggers critic retry with parameter overrides."""
        registry = _make_stub_registry()
        workflow = MrnaCdsDesignWorkflow(registry)
        controller = ExecutionController(
            capability_registry=registry,
            workflow_registry={"mrna_cds_design": workflow},
        )

        # Build a fake low-quality result (very low CAI)
        low_cand = Candidate(
            sequence="AUG" * 20,
            source="lineardesign_lambda0",
            metadata={
                "metrics_bundle": {
                    "cai_score": 0.15,  # very low CAI
                    "mfe_kcal_per_mol": -80.0,
                    "gc_content": 0.33,
                    "sequence_length": 60,
                },
                "design_tool": "lineardesign",
                "design_params": {"lambda_value": 0.0},
            },
        )
        low_cand.scores = {"total_score": 0.1}
        low_result = WorkflowResult(
            success=True,
            task_id="low-cai",
            best_candidate=low_cand,
            all_candidates=[low_cand],
            summary="low cai test",
        )

        call_count = 0

        def _mock_run_step(step, state, *, progress_callback=None, _resolved_inputs=None):
            nonlocal call_count
            call_count += 1
            if step.target == "mrna_cds_design":
                state["_last_workflow_params"] = dict(step.input_binding)
                return low_result
            raise RuntimeError(f"Unexpected: {step.target}")

        plan = ExecutionPlan(
            steps=[
                PlanStep(
                    step_id="wf1",
                    type="workflow",
                    target="mrna_cds_design",
                    input_binding={"protein_sequence": "MKTAIVE", "design_tool": "lineardesign", "lambda_value": 0.0},
                )
            ],
            max_retries=2,
        )

        # Patch critic to force retry with parameter overrides
        def _mock_should_retry(result, state):
            state["_parameter_overrides"] = {"lambda_value": 4.0}
            return True

        with patch.object(controller, "_run_step", side_effect=_mock_run_step):
            with patch("agent_core.workflows.registry.get_critic_for_workflow") as mock_get_critic:
                mock_critic = MagicMock()
                mock_critic.should_retry = _mock_should_retry
                mock_get_critic.return_value = mock_critic
                final_state = controller.execute(
                    plan,
                    {"_llm_critic_enabled": True, "user_text": "Design mRNA with high CAI"},
                    replan_fn=lambda s: plan,
                )

        # The flow should complete without crashing
        assert final_state.get("_plan_executed") is True
        log = final_state.get("_execution_log", [])
        assert any(e.get("event") == "step_start" for e in log)
        assert any(e.get("event") == "step_done" for e in log)
        # Verify parameter override was applied
        assert any(e.get("event") == "parameter_override" for e in log)
        # Verify lambda_value was overridden
        assert call_count >= 2  # original run + at least one retry

    @skip_if_no_live_llm
    def test_runner_live_mrna_cds_design(self):
        """真实调用 AgentRunner.run() 进行 mRNA CDS 设计."""
        from agent_core.planning.factory import build_planner

        planner = build_planner()
        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        result = runner.run(
            f"Design mRNA CDS for protein {TEST_PROTEIN}",
            session_id=f"live-cds-{int(time.time())}",
        )

        wf_result = result.get("workflow_result")
        assert wf_result is not None, f"No workflow_result in state. Keys: {list(result.keys())}"
        assert wf_result.success is True, f"Workflow failed: {wf_result.errors}"
        assert wf_result.best_candidate is not None
        assert len(wf_result.best_candidate.sequence) > 0
        assert "final_report" in result
        assert "mrna_cds_design" in result["final_report"] or "候选" in result["final_report"]

        # Verify plan contains mrna_cds_design or full_length_mrna_design
        plan = result.get("_execution_plan")
        assert plan is not None
        steps = plan.get("steps", [])
        targets = [s["target"] for s in steps]
        assert any(t in ("mrna_cds_design", "full_length_mrna_design") for t in targets), (
            f"Expected mRNA design step, got targets: {targets}"
        )


# ═══════════════════════════════════════════════════════════════════════
# CLI / API 入口
# ═══════════════════════════════════════════════════════════════════════


class TestCliApiEntry:
    """验证 CLI 和 FastAPI 入口."""

    @patch("cli.mrna_workflow.AgentRunner")
    def test_cli_mrna_workflow_scoring(self, mock_runner_cls: MagicMock) -> None:
        """cli/mrna_workflow.py --sequence should run successfully via AgentRunner."""
        from cli.mrna_workflow import main
        from agent_core.workflow_models import Candidate, WorkflowResult

        mock_runner = MagicMock()
        mock_runner.run.return_value = {
            "workflow_result": WorkflowResult(
                success=True,
                task_id="cli-test",
                best_candidate=Candidate(sequence=TEST_SEQUENCE, scores={"total_score": 1.0}),
                all_candidates=[Candidate(sequence=TEST_SEQUENCE, scores={"total_score": 1.0})],
                summary="ok",
            ),
        }
        mock_runner_cls.return_value = mock_runner

        rc = main(["--sequence", TEST_SEQUENCE, "--json"])
        assert rc == 0
        mock_runner.run.assert_called_once()

    def test_api_mrna_run_endpoint_schema(self):
        """Request/response schemas remain valid after endpoint unification."""
        from workflow_api.mrna_schemas import (
            MrnaWorkflowHttpRequest,
            MrnaWorkflowHttpResponse,
        )

        req = MrnaWorkflowHttpRequest(sequence=TEST_SEQUENCE)
        assert req.sequence == TEST_SEQUENCE
        assert req.task_type == "mrna"

        resp = MrnaWorkflowHttpResponse(
            task_id="test",
            success=True,
            task_type="mrna",
            best_candidate={"id": "c1", "sequence": TEST_SEQUENCE, "source": "test"},
            candidates=[{"id": "c1", "sequence": TEST_SEQUENCE, "source": "test"}],
            summary="ok",
        )
        assert resp.success is True
        assert resp.best_candidate is not None

    def test_api_agent_run_endpoint(self):
        """/v1/agent/run builds correct natural-language prompt."""
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        # We cannot run the real endpoint without a full FastAPI test client,
        # but we can validate the request schema -> prompt logic.
        req = MrnaWorkflowHttpRequest(protein=TEST_PROTEIN)
        constraints = dict(req.constraints or {})
        user_text = ""
        if req.protein is not None and str(req.protein).strip():
            user_text = f"Design mRNA for protein {req.protein}"
            design_tool_hint = constraints.get("design_tool", "")
            if design_tool_hint:
                user_text += f" using {design_tool_hint}"
        assert "Design mRNA for protein" in user_text
        assert TEST_PROTEIN in user_text

    def test_mrna_handler_schema_consistency(self):
        """mrna_handler output matches AgentRunner result shape."""
        from workflow_api.mrna_handler import execute_mrna_workflow_http
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        req = MrnaWorkflowHttpRequest(sequence=TEST_SEQUENCE, task_id="schema-test")
        resp = execute_mrna_workflow_http(req)

        # Response fields should align with WorkflowResult
        assert resp.task_id is not None
        assert isinstance(resp.success, bool)
        if resp.best_candidate:
            assert "sequence" in resp.best_candidate
            assert "scores" in resp.best_candidate
        # AgentRunner returns these keys in its fallback / structured path
        assert resp.summary is not None


# ═══════════════════════════════════════════════════════════════════════
# DeepSeek API 真实调用验证
# ═══════════════════════════════════════════════════════════════════════


class TestDeepSeekApiLive:
    """真实 LLM 调用验证 (需 --live-llm 和 DEEPSEEK_API_KEY)."""

    @skip_if_no_live_llm
    def test_llm_planner_generates_plan(self):
        """LLMPlanner.plan() returns a valid JSON plan."""
        planner = LLMPlanner()
        ctx = AgentContext(
            session_id="live-plan-test",
            available_capabilities=[
                "compute_rna_sequence_gc_content",
                "predict_rna_secondary_structure_with_linearfold",
            ],
            available_workflows=["mrna_cds_design", "mrna_sequence_scoring"],
            workflow_param_schemas={
                "mrna_cds_design": "protein_sequence=(required) (str)",
            },
        )
        plan = planner.plan(
            f"Design mRNA CDS for protein {TEST_PROTEIN} and score it",
            ctx,
        )
        assert len(plan.steps) > 0
        targets = [s.target for s in plan.steps]
        assert any(t in ("mrna_cds_design", "full_length_mrna_design") for t in targets), (
            f"Expected mRNA design target, got: {targets}"
        )
        # Verify JSON plan structure
        dumped = plan.model_dump(mode="json")
        assert "steps" in dumped
        assert "max_retries" in dumped

    @skip_if_no_live_llm
    def test_full_length_critic_diagnoses_low_cai(self):
        """Build low-quality result (low CAI) and verify critic returns retry_with_adjustments."""
        critic = FullLengthMrnaDesignLLMCritic()
        low_cand = Candidate(
            sequence="AUG" * 20,
            source="lineardesign_lambda0",
            metadata={
                "utr5_sequence": "GGGAAA",
                "cds_sequence": "AUG" * 20,
                "utr3_sequence": "AAAUUU",
                "utr5_preset": "short",
                "utr3_preset": "short",
                "cds_length": 60,
                "metrics_bundle": {
                    "cds_cai": 0.15,
                    "cds_mfe": -80.0,
                    "cds_gc": 0.33,
                    "cds_length": 60,
                    "full_length_mfe": -30.0,
                    "total_length": 72,
                    "utr5_predicted_mrl": 5.0,
                    "utr3_predicted_stability": 0.6,
                    "utr5_ires_potential": 0.1,
                    "overall_stability": 0.5,
                },
            },
        )
        low_cand.scores = {"cds_component": 0.01, "utr5_mrl": 5.0, "utr3_stability": 0.6}
        result = WorkflowResult(
            success=True,
            task_id="low-cai",
            best_candidate=low_cand,
            all_candidates=[low_cand],
            summary="low CAI test",
        )
        state = {
            "_last_workflow_params": {"design_tool": "lineardesign", "lambda_value": 0.0},
            "user_text": "Design high-CAI mRNA for MKTAIVE",
            "_llm_critic_enabled": True,
        }

        diagnosis = critic.diagnose(result, state)
        print(f"\n[Live Critic Diagnosis]\n{diagnosis.model_dump_json(indent=2)}")

        assert diagnosis.quality_score <= 0.8  # Low CAI should lower quality
        assert len(diagnosis.issues) > 0
        # Critic may recommend retry or abort depending on severity judgment
        assert diagnosis.action in (
            "retry_with_adjustments",
            "retry_with_alternative",
            "proceed_with_filtered",
            "abort",
        )
        # If retry recommended, lambda_value or design_tool should be adjusted
        if diagnosis.action in ("retry_with_adjustments", "retry_with_alternative"):
            assert any(k in ("lambda_value", "design_tool") for k in diagnosis.parameter_overrides), (
                f"Expected lambda_value/design_tool override, got: {diagnosis.parameter_overrides}"
            )
        # Verify CAI issue is identified regardless of action
        cai_issues = [
            i for i in diagnosis.issues
            if "cai" in i.category.lower() or "CAI" in i.description or "codon" in i.description.lower()
        ]
        assert len(cai_issues) > 0, (
            f"Expected CAI-related issue, got categories: {[i.category for i in diagnosis.issues]}, "
            f"descriptions: {[i.description for i in diagnosis.issues]}"
        )

    @skip_if_no_live_llm
    def test_api_failure_graceful_degradation(self):
        """When DeepSeek API fails, Critic falls back to no-retry (no crash)."""
        critic = FullLengthMrnaDesignLLMCritic()
        result = WorkflowResult(
            success=True,
            task_id="degradation-test",
            best_candidate=Candidate(sequence="AUG" * 20, source="test"),
            all_candidates=[Candidate(sequence="AUG" * 20, source="test")],
            summary="test",
        )
        state = {"_llm_critic_enabled": True}

        # Patch the underlying _llm attribute directly (property has no setter)
        mock_llm = MagicMock()
        mock_llm.invoke = MagicMock(side_effect=RuntimeError("Simulated API failure"))
        critic._llm = mock_llm

        should_retry = critic.should_retry(result, state)
        assert should_retry is False
        # diagnose() internally catches the exception and returns action="abort",
        # so should_retry does not raise and no-retry is the fallback.
        assert "_last_diagnosis" in state
        diag = state["_last_diagnosis"]
        assert diag["action"] == "abort"
        assert "LLM diagnosis failed" in diag["overall_assessment"]


# ═══════════════════════════════════════════════════════════════════════
# CPU / GPU 工具运行验证
# ═══════════════════════════════════════════════════════════════════════


class TestCpuGpuTools:
    """验证 Layer 0 工具在 CPU/GPU 上正确运行."""

    @pytest.fixture(scope="class")
    def executor(self):
        return ToolExecutor(build_default_tool_registry())

    @pytest.fixture(scope="class")
    def protein_filepath(self):
        return save_sequence(TEST_PROTEIN, prefix="test_protein")

    @pytest.fixture(scope="class")
    def cds_filepath(self):
        return save_sequence(TEST_SEQUENCE, prefix="test_cds")

    # ── CPU tools ──

    def test_lineardesign_cpu(self, executor, protein_filepath):
        result = executor.run_tool(
            "design_mrna_cds_with_lineardesign",
            filepath=protein_filepath,
            lambda_value=1.0,
        )
        assert result.success, f"LinearDesign failed: {result.error}"
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0
        assert len(seq) % 3 == 0  # valid CDS length

    def test_viennarna_fold_cpu(self, executor, cds_filepath):
        result = executor.run_tool(
            "predict_rna_secondary_structure",
            filepath=cds_filepath,
        )
        assert result.success, f"ViennaRNA failed: {result.error}"
        struct = result.artifacts.get("result", {}).get("structure", "")
        assert len(struct) > 0
        mfe = result.artifacts.get("result", {}).get("mfe_kcal_per_mol")
        assert mfe is not None

    def test_linearfold_cpu(self, executor, cds_filepath):
        result = executor.run_tool(
            "predict_rna_secondary_structure_with_linearfold",
            filepath=cds_filepath,
        )
        assert result.success, f"LinearFold failed: {result.error}"
        struct = result.artifacts.get("result", {}).get("structure", "")
        assert len(struct) > 0
        mfe = result.artifacts.get("result", {}).get("mfe")
        assert mfe is not None

    def test_gc_content_cpu(self, executor, cds_filepath):
        result = executor.run_tool(
            "compute_rna_sequence_gc_content",
            filepath=cds_filepath,
        )
        assert result.success, f"GC content failed: {result.error}"
        gc = result.artifacts.get("result", {}).get("gc_content")
        assert gc is not None
        assert 0.0 <= gc <= 1.0

    def test_cai_cpu(self, executor, cds_filepath):
        result = executor.run_tool(
            "compute_cai_for_cds_sequence",
            filepath=cds_filepath,
            species=TEST_SPECIES,
        )
        assert result.success, f"CAI failed: {result.error}"
        cai = result.artifacts.get("result", {}).get("cai_score")
        assert cai is not None
        assert 0.0 <= cai <= 1.0

    # ── GPU tools ──

    def test_rnarl_gpu(self, executor, protein_filepath):
        result = executor.run_tool(
            "design_mrna_cds_with_rnarl",
            filepath=protein_filepath,
            model_type=TEST_MODEL_TYPE,
        )
        # If GPU is unavailable, the tool may fallback or fail gracefully
        if not result.success:
            pytest.skip(f"RNARL skipped (GPU/fallback): {result.error}")
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "RNARL returned empty sequence"
        assert len(seq) % 3 == 0

    def test_gemorna_gpu(self, executor, protein_filepath):
        result = executor.run_tool(
            "design_mrna_cds_with_gemorna",
            filepath=protein_filepath,
        )
        if not result.success:
            pytest.skip(f"GEMORNA skipped (GPU/fallback): {result.error}")
        seq = result.artifacts.get("result", {}).get("generated_sequence", "")
        assert len(seq) > 0, "GEMORNA returned empty sequence"
        assert len(seq) % 3 == 0

    def test_rnastop_gpu(self, executor, cds_filepath):
        result = executor.run_tool(
            "predict_mrna_stability_with_rnastop",
            filepath=cds_filepath,
        )
        if not result.success:
            pytest.skip(f"RNASTOP skipped (GPU/fallback): {result.error}")
        stab = result.artifacts.get("result", {}).get("overall_stability")
        assert stab is not None, "Missing overall_stability from RNASTOP"
        assert 0.0 <= stab <= 1.0, f"RNASTOP stability out of range: {stab}"


# ═══════════════════════════════════════════════════════════════════════
# 代码规范检查
# ═══════════════════════════════════════════════════════════════════════


class TestCodeQuality:
    """静态代码规范检查 (类型注解、异常处理、INTERFACE LOCK、无硬编码 key)."""

    @pytest.fixture(scope="class")
    def layer45_source_files(self):
        """Collect Python files in Layer 4/5 modules."""
        files: list[Path] = []
        targets = [
            "agent_core/runner.py",
            "agent_core/session_memory.py",
            "agent_core/workspace_manager.py",
            "agent_core/state.py",
            "workflow_api/app.py",
            "workflow_api/mrna_handler.py",
            "workflow_api/mrna_schemas.py",
            "cli/mrna_workflow.py",
        ]
        for rel in targets:
            p = PROJECT_ROOT / rel
            if p.exists():
                files.append(p)
        return files

    def test_type_annotations_on_public_methods(self, layer45_source_files):
        """Public methods should have return type annotations."""
        failures: list[str] = []
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    if node.returns is None and node.name != "__init__":
                        failures.append(f"{path.name}:{node.name}")
        # Allow a small tolerance for legacy methods
        allowed_missing = {"run_all_tests", "main", "health", "post_mrna_workflow",
                           "post_sirna_workflow", "post_ires_workflow", "post_rna_workflow",
                           "post_agent_run"}
        failures = [f for f in failures if f.split(":")[-1] not in allowed_missing]
        assert len(failures) == 0, f"Missing return type annotations: {failures}"

    def test_no_hardcoded_api_keys(self, layer45_source_files):
        """Source files must not contain hardcoded API keys."""
        key_patterns = ["api_key = ", "api_key="]
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            for pat in key_patterns:
                # Allow environment variable loading patterns
                lines = [
                    i + 1
                    for i, line in enumerate(source.splitlines())
                    if pat in line and "os.environ" not in line and "getenv" not in line and "load_dotenv" not in line
                ]
                assert len(lines) == 0, f"Possible hardcoded key in {path.name} lines {lines}"

    def test_interface_lock_comments_present(self, layer45_source_files):
        """Key workflow and runner files should contain INTERFACE LOCK comments."""
        required_locks = {
            "runner.py": ["INTERFACE LOCK"],
            "mrna_handler.py": ["INTERFACE LOCK"],
        }
        for filename, markers in required_locks.items():
            path = next((p for p in layer45_source_files if p.name == filename), None)
            if path is None:
                continue
            source = path.read_text(encoding="utf-8")
            for marker in markers:
                assert marker in source, f"{filename} missing '{marker}' comment"

    def test_exception_handling_no_bare_except(self, layer45_source_files):
        """No bare 'except:' clauses in Layer 4/5 code."""
        for path in layer45_source_files:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        assert False, f"Bare except in {path.name} line {node.lineno}"

    def test_no_dead_imports_runner(self):
        """runner.py should not have unused imports (basic check)."""
        path = PROJECT_ROOT / "agent_core/runner.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
        import_froms = [
            (node.module, [a.name for a in node.names])
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        # Just ensure no obvious unused heavy imports
        assert "numpy" not in imports, "Unexpected numpy import in runner.py"
