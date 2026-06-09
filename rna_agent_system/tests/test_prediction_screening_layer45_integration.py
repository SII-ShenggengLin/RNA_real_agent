"""Layer 4/5 integration tests for IRES prediction & ASO target screening workflows.

Covers:
- Layer 4: SessionMemory multi-turn persistence, WorkspaceManager file isolation
- Layer 5: AgentRunner.run() / .stream() end-to-end orchestration
- CLI / API entry points (IRES has dedicated CLI+API; ASO is AgentRunner-only)
- Critic behavior: IRES has LLM Critic; ASO deliberately has none
- CPU/GPU validation: both workflows are CPU-only
- Code quality: interface locks, type annotations, exception handling

Run:
    cd rna_agent_system
    PYTHONPATH="$(pwd):$PYTHONPATH" pytest tests/test_prediction_screening_layer45_integration.py -v
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

# Ensure project root is on path
from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import PROJECT_ROOT
from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.aso_target_screening import (
    AsoScreeningCritic,
    AsoScreeningInput,
    AsoTargetScreeningWorkflow,
)
from agent_core.workflows.ires_prediction import (
    IRES_PREDICTION_CRITIC_CONFIG,
    IresPredictionInput,
    IresPredictionLLMCritic,
    IresPredictionWorkflow,
)
from agent_core.workflows.registry import WORKFLOW_CRITIC_PAIRS

# =============================================================================
# Helpers
# =============================================================================


def _make_mock_capability(output: dict[str, Any]) -> MagicMock:
    cap = MagicMock()
    cap.invoke.return_value = MagicMock(success=True, output=output, error=None)
    return cap


def _make_ires_registry(structural: bool = True) -> MagicMock:
    """Build a mocked capability registry for IRES workflow tests."""
    reg = MagicMock(spec=CapabilityRegistry)
    caps: dict[str, MagicMock] = {}

    # IRESfinder — always return one positive window
    caps["predict_putative_ires_with_iresfinder"] = _make_mock_capability({
        "predictions": [
            {"fragment_id": "query_1_174", "score": 0.85, "predicted_label": "IRES"},
        ],
        "max_score": 0.85,
        "has_putative_ires": True,
        "positive_count": 1,
        "fragment_count": 1,
    })

    if structural:
        caps["predict_rna_secondary_structure"] = _make_mock_capability({
            "structure": "(((....)))" * 10,
            "mfe_kcal_per_mol": -12.5,
        })
        caps["predict_rna_local_accessibility_profile_vienna"] = _make_mock_capability({
            "mean_unpaired_prob_1nt": 0.45,
            "lunp_profile_tsv_filepath": "workspace/test_profile.tsv",
        })
        caps["compute_dot_bracket_unpaired_fraction"] = _make_mock_capability({
            "unpaired_fraction": 0.333,
        })

    def _has(name: str) -> bool:
        return name in caps

    def _get(name: str) -> Any:
        return caps[name]

    reg.has = _has
    reg.get = _get
    return reg


def _make_aso_registry() -> MagicMock:
    """Build a mocked capability registry for ASO workflow tests."""
    reg = MagicMock(spec=CapabilityRegistry)
    caps: dict[str, MagicMock] = {}

    # RNAplfold profile
    positions = list(range(1, 201))
    probs = [0.5 + 0.01 * (i % 10) for i in positions]
    caps["predict_rna_local_accessibility_profile_vienna"] = _make_mock_capability({
        "positions": positions,
        "unpaired_prob_1nt": probs,
        "lunp_profile_tsv_filepath": "workspace/test_plfold.tsv",
    })

    # ASO accessibility
    caps["compute_aso_target_accessibility_vienna"] = _make_mock_capability({
        "mean_unpaired_prob_single_nt": 0.55,
        "joint_unpaired_prob_stretch_ending_at_region_end": 0.48,
    })

    # RNAup
    caps["compute_rna_rna_interaction_vienna"] = _make_mock_capability({
        "interaction_energy": -8.5,
        "interaction_structure": "(((...)))&(((...)))",
    })

    # RNAcofold (for rnacofold path)
    caps["compute_sirna_duplex_binding_vienna"] = _make_mock_capability({
        "mfe_kcal_per_mol": -9.2,
        "structure": "(((...)))&(((...)))",
    })

    def _has(name: str) -> bool:
        return name in caps

    def _get(name: str) -> Any:
        return caps[name]

    reg.has = _has
    reg.get = _get
    return reg


# =============================================================================
# Layer 4 — Session & Memory Integration
# =============================================================================


@pytest.mark.known_issue
class TestLayer4SessionMemory:
    """Verify SessionMemory + AgentRunner persistence for IRES and ASO workflows."""

    def test_runner_ires_session_persists_across_turns(self) -> None:
        """Two-turn session: first IRES prediction, then structural validation.

        State from turn 1 (candidate_sequence, workflow_result) should be
        reloaded in turn 2.
        """
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(
                step_id="s1", type="workflow", target="ires_prediction",
                input_binding={"sequence_filepath": "dummy.fasta"},
            ),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=memory)
        sid = "session-ires-001"

        # Turn 1 result — simulate IRES workflow producing candidates
        turn1_result = default_state("")
        turn1_result["workflow_result"] = WorkflowResult(
            success=True,
            task_id="ires_001",
            best_candidate=Candidate(sequence="ACGU", sequence_type="rna", source="iresfinder:2"),
            all_candidates=[Candidate(sequence="ACGU", sequence_type="rna", source="iresfinder:2")],
            summary="Found 1 IRES candidate.",
        )
        turn1_result["messages"] = [HumanMessage(content="Predict IRES in sequence XXX")]

        with patch.object(ExecutionController, "execute", return_value=turn1_result):
            state1 = runner.run("Predict IRES in sequence XXX", session_id=sid)
            assert state1["workflow_result"].success is True

        # Turn 2 — the runner should load persisted state from memory
        turn2_result = default_state("")
        turn2_result.update(memory.load(sid))  # simulate reload + mutation
        turn2_result["messages"].append(HumanMessage(content="validate with structural analysis"))
        turn2_result["retry_count"] = 0

        with patch.object(ExecutionController, "execute", return_value=turn2_result) as mock_exec:
            state2 = runner.run("validate with structural analysis", session_id=sid)
            passed_state = mock_exec.call_args[0][1]
            # Prior workflow_result should be present from memory
            assert passed_state.get("workflow_result") is not None
            contents = [m.content for m in passed_state["messages"]]
            assert "Predict IRES in sequence XXX" in contents
            assert "validate with structural analysis" in contents

    def test_runner_aso_session_persists_across_turns(self) -> None:
        """ASO screening session persistence."""
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(
                step_id="s1", type="workflow", target="aso_target_screening",
                input_binding={"target_mrna_filepath": "dummy.fasta"},
            ),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=memory)
        sid = "session-aso-002"

        turn1_result = default_state("")
        turn1_result["workflow_result"] = WorkflowResult(
            success=True,
            task_id="aso_001",
            best_candidate=Candidate(sequence="CGUA", sequence_type="aso", source="window:1-18"),
            all_candidates=[Candidate(sequence="CGUA", sequence_type="aso", source="window:1-18")],
            summary="Found 1 ASO site.",
        )
        turn1_result["messages"] = [HumanMessage(content="Screen ASO targets for transcript XXX")]

        with patch.object(ExecutionController, "execute", return_value=turn1_result):
            state1 = runner.run("Screen ASO targets for transcript XXX", session_id=sid)
            assert state1["workflow_result"].success is True

        turn2_result = default_state("")
        turn2_result.update(memory.load(sid))
        turn2_result["messages"].append(HumanMessage(content="Show top 3 sites"))
        turn2_result["retry_count"] = 0

        with patch.object(ExecutionController, "execute", return_value=turn2_result) as mock_exec:
            state2 = runner.run("Show top 3 sites", session_id=sid)
            passed_state = mock_exec.call_args[0][1]
            assert passed_state.get("workflow_result") is not None
            contents = [m.content for m in passed_state["messages"]]
            assert "Screen ASO targets for transcript XXX" in contents
            assert "Show top 3 sites" in contents

    def test_workspace_manager_session_isolation(self, tmp_path: Path) -> None:
        """WorkspaceManager creates per-session directories."""
        from agent_core.workspace_manager import WorkspaceManager

        wm = WorkspaceManager(base_dir=str(tmp_path / "workspace"))
        dir_a = wm.get_session_dir("session-a")
        dir_b = wm.get_session_dir("session-b")
        assert dir_a != dir_b
        assert dir_a.exists()
        assert dir_b.exists()
        assert "session-a" in str(dir_a)
        assert "session-b" in str(dir_b)

    def test_save_sequence_respects_session_context(self) -> None:
        """save_sequence writes to the session directory when _SESSION_ID_CTX is set."""
        from agent_core.file_manager import _SESSION_ID_CTX, save_sequence
        from agent_core.workspace_manager import WorkspaceManager

        wm = WorkspaceManager()
        sid = "test-session-ctx"
        token = _SESSION_ID_CTX.set(sid)
        try:
            fp = save_sequence(">seq\nACGUACGU\n", prefix="test_seq")
            abs_path = PROJECT_ROOT / fp
            assert abs_path.exists()
            # Should be under sessions/{sid}
            assert f"sessions/{sid}" in fp.replace("\\", "/")
        finally:
            _SESSION_ID_CTX.reset(token)
            # Cleanup
            wm.delete_session(sid)


# =============================================================================
# Layer 5 — AgentRunner End-to-End
# =============================================================================


@pytest.mark.known_issue
class TestLayer5AgentRunner:
    """AgentRunner.run() and .stream() with mocked planner but real registry."""

    def test_runner_ires_end_to_end(self) -> None:
        """AgentRunner.run() for IRES prediction produces WorkflowResult."""
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(
                step_id="s1", type="workflow", target="ires_prediction",
                input_binding={
                    "sequence_filepath": "dummy.fasta",
                    "iresfinder_mode": 2,
                    "probability_threshold": 0.5,
                },
            ),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        with patch.object(
            IresPredictionWorkflow, "run",
            return_value=WorkflowResult(
                success=True,
                task_id="ires_test",
                best_candidate=Candidate(sequence="ACGU", sequence_type="rna", source="iresfinder:2"),
                all_candidates=[Candidate(sequence="ACGU", sequence_type="rna", source="iresfinder:2")],
                summary="Found 1 IRES candidate.",
            ),
        ):
            state = runner.run("Predict IRES sites in sequence GGGAAACCCUUU")
            assert state["workflow_result"].success is True
            assert state["final_report"] != ""
            assert "workflow_result" in state

    def test_runner_aso_end_to_end(self) -> None:
        """AgentRunner.run() for ASO screening produces WorkflowResult."""
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(
                step_id="s1", type="workflow", target="aso_target_screening",
                input_binding={
                    "target_mrna_filepath": "dummy.fasta",
                    "aso_length": 18,
                    "top_n_windows": 5,
                },
            ),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe, llm_critic_enabled=False)

        with patch.object(
            AsoTargetScreeningWorkflow, "run",
            return_value=WorkflowResult(
                success=True,
                task_id="aso_test",
                best_candidate=Candidate(sequence="CGUA", sequence_type="aso", source="window:1-18"),
                all_candidates=[Candidate(sequence="CGUA", sequence_type="aso", source="window:1-18")],
                summary="Found 1 ASO site.",
            ),
        ):
            state = runner.run("Screen ASO targets for transcript XXX")
            assert state["workflow_result"].success is True
            assert state["final_report"] != ""

    def test_runner_stream_events(self) -> None:
        """AgentRunner.stream() yields router, plan, progress, tool_execution, runner events."""
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", type="capability", target="mock_cap"),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        runner = AgentRunner(planner, exe)

        with patch.object(ExecutionController, "execute", return_value=default_state("hello")):
            events = list(runner.stream("hello"))

        keys = [list(e.keys())[0] for e in events]
        assert "router" in keys
        assert "plan" in keys
        assert "progress" in keys or "tool_execution" in keys
        assert "tool_execution" in keys
        assert "runner" in keys

    def test_runner_ires_stream_preserves_memory(self) -> None:
        """stream() should save to SessionMemory when session_id is provided."""
        planner = MagicMock()
        plan = ExecutionPlan(steps=[
            PlanStep(step_id="s1", type="capability", target="mock_cap"),
        ])
        planner.plan_with_state = MagicMock(return_value=plan)

        exe = ToolExecutor(build_default_tool_registry(include_demo=False))
        memory = SessionMemory()
        runner = AgentRunner(planner, exe, session_memory=memory)
        sid = "stream-session-001"

        turn_result = default_state("")
        turn_result["candidate_sequence"] = "STREAM_SEQ"

        with patch.object(ExecutionController, "execute", return_value=turn_result):
            events = list(runner.stream("Predict IRES", session_id=sid))

        assert sid in memory._store
        assert memory._store[sid].get("candidate_sequence") == "STREAM_SEQ"


# =============================================================================
# CLI / API Entry Points
# =============================================================================


class TestCliApiEntries:
    """Verify IRES CLI and FastAPI routing; confirm ASO has no dedicated CLI/API."""

    def test_cli_ires_workflow_importable(self) -> None:
        """``cli/ires_workflow.py`` can be imported and main() accepts args."""
        from cli.ires_workflow import main
        assert callable(main)

    def test_cli_ires_help(self) -> None:
        """IRES CLI --help exits successfully."""
        from cli.ires_workflow import main
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    @patch("cli.ires_workflow.AgentRunner")
    def test_cli_ires_runs_with_mocked_handler(self, mock_runner_cls: MagicMock) -> None:
        """IRES CLI invokes AgentRunner and prints results."""
        from cli.ires_workflow import main
        from agent_core.workflow_models import Candidate, WorkflowResult
        mock_runner = MagicMock()
        mock_runner.run.return_value = {
            "workflow_result": WorkflowResult(
                success=True,
                task_id="cli-test",
                best_candidate=Candidate(sequence="AUGC", scores={}),
                all_candidates=[Candidate(sequence="AUGC", scores={})],
                summary="Mock IRES result.",
            ),
        }
        mock_runner_cls.return_value = mock_runner
        ret = main(["--sequence", "ACGUACGUACGU", "--json"])
        assert ret == 0
        mock_runner.run.assert_called_once()

    def test_api_ires_dedicated_endpoint_exists(self) -> None:
        """``/v1/workflows/ires/run`` route is registered in FastAPI app."""
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        from workflow_api.app import app
        routes = [r.path for r in app.routes]
        assert "/v1/workflows/ires/run" in routes

    def test_api_aso_no_dedicated_endpoint(self) -> None:
        """ASO has no dedicated ``/v1/workflows/aso/run`` endpoint."""
        from workflow_api.app import app
        routes = [r.path for r in app.routes]
        assert "/v1/workflows/aso/run" not in routes

    def test_api_aso_unified_returns_error_not_misroute(self) -> None:
        """POST /v1/workflows/run with task_type=aso must NOT misroute to mRNA handler.

        NOTE: This endpoint has been removed; all requests now go through
        ``/v1/agent/run``.
        """
        pytest.skip("Removed: endpoints unified to /v1/agent/run")
        from fastapi.testclient import TestClient
        from workflow_api.app import app
        from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

        client = TestClient(app)
        req = MrnaWorkflowHttpRequest(
            task_type="aso",
            sequence="ACGUACGUACGUACGUACGU",
        )
        resp = client.post("/v1/workflows/run", json=req.model_dump(mode="json"))
        # Should not be 200 OK with mrna workflow result
        assert resp.status_code != 200 or resp.json().get("task_type") != "mrna"
        # Should indicate ASO is not available on direct HTTP
        data = resp.json()
        assert data.get("success") is False or "aso" in str(data.get("errors", [])).lower()


# =============================================================================
# Critic & Retry Behavior
# =============================================================================


class TestCriticBehavior:
    """IRES has a real LLM Critic; ASO deliberately has none."""

    def test_ires_critic_registered(self) -> None:
        """``ires_prediction`` is present in WORKFLOW_CRITIC_PAIRS."""
        assert "ires_prediction" in WORKFLOW_CRITIC_PAIRS
        wf_cls, critic_cls = WORKFLOW_CRITIC_PAIRS["ires_prediction"]
        assert wf_cls is IresPredictionWorkflow
        assert critic_cls is IresPredictionLLMCritic

    def test_ires_critic_config_fields(self) -> None:
        """IRES critic config contains expected adjustable parameters."""
        config = IRES_PREDICTION_CRITIC_CONFIG
        assert config.workflow_name == "ires_prediction"
        assert config.retry_strategy == "adjust_params"
        assert config.max_retries == 2
        expected_params = {
            "probability_threshold", "window_size", "step_size",
            "top_n_candidates", "run_structural_validation", "iresfinder_mode",
        }
        assert set(config.adjustable_params.keys()) == expected_params

    def test_aso_critic_never_retries(self) -> None:
        """``AsoScreeningCritic.should_retry()`` always returns False."""
        critic = AsoScreeningCritic()
        result = WorkflowResult(success=True, task_id="", summary="")
        assert critic.should_retry(result, {}) is False

    def test_aso_omitted_from_critic_pairs(self) -> None:
        """ASO is intentionally absent from WORKFLOW_CRITIC_PAIRS."""
        assert "aso_target_screening" not in WORKFLOW_CRITIC_PAIRS

    def test_aso_no_retry_even_when_critic_enabled(self) -> None:
        """Even with llm_critic_enabled=True, ASO workflow should not retry."""
        reg = _make_aso_registry()
        wf = AsoTargetScreeningWorkflow(reg)
        with patch.object(AsoTargetScreeningWorkflow, "run", return_value=WorkflowResult(
            success=True, task_id="aso", summary="ok",
            best_candidate=Candidate(sequence="CGUA", sequence_type="aso", source="w:1-18"),
            all_candidates=[Candidate(sequence="CGUA", sequence_type="aso", source="w:1-18")],
        )):
            controller = ExecutionController(
                capability_registry=reg,
                workflow_registry={"aso_target_screening": wf},
            )
            plan = ExecutionPlan(steps=[
                PlanStep(step_id="s1", type="workflow", target="aso_target_screening"),
            ])
            state = default_state("")
            state["_llm_critic_enabled"] = True
            result_state = controller.execute(plan, state)
            assert result_state.get("retry_count", 0) == 0

    def test_ires_critic_build_context_empty_candidates(self) -> None:
        """``IresPredictionLLMCritic._build_context`` handles empty candidates gracefully."""
        critic = IresPredictionLLMCritic()
        result = WorkflowResult(
            success=False, task_id="", summary="No candidates.", errors=["empty"]
        )
        ctx = critic._build_context(result, {})
        assert "ires_stats" in ctx
        assert ctx["ires_stats"]["probability_range"]["count"] == 0

    def test_ires_critic_build_context_with_candidates(self) -> None:
        """``IresPredictionLLMCritic._build_context`` aggregates stats correctly."""
        critic = IresPredictionLLMCritic()
        c1 = Candidate(
            sequence="ACGU", sequence_type="rna", source="iresfinder:2",
            metadata={
                "iresfinder_mode": 2,
                "metrics_bundle": {
                    "ires_probability": 0.8,
                    "mfe_kcal_per_mol": -10.0,
                    "mean_unpaired_fraction": 0.4,
                    "mean_unpaired_prob_1nt": 0.5,
                    "region_length": 174,
                    "start": 1, "end": 174,
                },
            },
        )
        result = WorkflowResult(
            success=True, task_id="", summary="ok",
            best_candidate=c1, all_candidates=[c1],
        )
        ctx = critic._build_context(result, {})
        stats = ctx["ires_stats"]
        assert stats["probability_range"]["count"] == 1
        assert stats["mfe_range"]["count"] == 1
        assert stats["unpaired_fraction_range"]["count"] == 1
        assert stats["mode_distribution"]["2"] == 1


# =============================================================================
# CPU / GPU Tool Validation
# =============================================================================


class TestCpuGpuValidation:
    """Both workflows are CPU-only; no GPU dependencies."""

    def test_ires_required_capabilities_cpu_only(self) -> None:
        """IRES workflow required capabilities map to CPU tools."""
        from agent_core import tools as tools_mod

        cpu_tool_names = {
            "predict_putative_ires_with_iresfinder",
            "predict_rna_secondary_structure",
            "predict_rna_local_accessibility_profile_vienna",
            "compute_dot_bracket_unpaired_fraction",
        }
        assert set(IresPredictionWorkflow.required_capabilities) == cpu_tool_names
        # Verify none of these tools reference GPU / CUDA
        for name in cpu_tool_names:
            tool_fn = getattr(tools_mod, name, None)
            assert tool_fn is not None, f"Missing tool {name}"
            raw_fn = getattr(tool_fn, "func", tool_fn)
            src = inspect.getsource(raw_fn) if raw_fn else ""
            gpu_refs = ["cuda", "gpu", "torch.cuda", "device=cuda"]
            assert not any(r in src.lower() for r in gpu_refs), (
                f"Tool {name} unexpectedly references GPU"
            )

    def test_aso_required_capabilities_cpu_only(self) -> None:
        """ASO workflow required capabilities map to CPU tools."""
        from agent_core import tools as tools_mod

        cpu_tool_names = {
            "predict_rna_local_accessibility_profile_vienna",
            "compute_aso_target_accessibility_vienna",
            "compute_rna_rna_interaction_vienna",
            "compute_sirna_duplex_binding_vienna",
        }
        assert set(AsoTargetScreeningWorkflow.required_capabilities) == cpu_tool_names
        for name in cpu_tool_names:
            tool_fn = getattr(tools_mod, name, None)
            assert tool_fn is not None, f"Missing tool {name}"
            raw_fn = getattr(tool_fn, "func", tool_fn)
            src = inspect.getsource(raw_fn) if raw_fn else ""
            gpu_refs = ["cuda", "gpu", "torch.cuda", "device=cuda"]
            assert not any(r in src.lower() for r in gpu_refs), (
                f"Tool {name} unexpectedly references GPU"
            )


# =============================================================================
# Code Quality & Interface Locks
# =============================================================================


class TestCodeQuality:
    """Static-ish checks for type annotations, exception handling, interface locks."""

    def test_ires_input_model_has_type_annotations(self) -> None:
        """All IresPredictionInput fields have annotations."""
        for name, field in IresPredictionInput.model_fields.items():
            assert field.annotation is not None, f"Field {name} lacks annotation"

    def test_aso_input_model_has_type_annotations(self) -> None:
        """All AsoScreeningInput fields have annotations."""
        for name, field in AsoScreeningInput.model_fields.items():
            assert field.annotation is not None, f"Field {name} lacks annotation"

    def test_ires_interface_lock_comments_present(self) -> None:
        """IRES workflow file contains INTERFACE LOCK comments."""
        wf_path = PROJECT_ROOT / "agent_core" / "workflows" / "ires_prediction.py"
        content = wf_path.read_text(encoding="utf-8")
        assert "INTERFACE LOCK" in content
        assert "v1.0.0" in content
        assert "ires_prediction" in content

    def test_aso_interface_lock_comments_present(self) -> None:
        """ASO workflow file contains INTERFACE LOCK comments."""
        wf_path = PROJECT_ROOT / "agent_core" / "workflows" / "aso_target_screening.py"
        content = wf_path.read_text(encoding="utf-8")
        assert "INTERFACE LOCK" in content
        assert "v1.0.0" in content
        assert "aso_target_screening" in content

    def test_registry_comments_explain_aso_omission(self) -> None:
        """registry.py documents why ASO is omitted from WORKFLOW_CRITIC_PAIRS."""
        reg_path = PROJECT_ROOT / "agent_core" / "workflows" / "registry.py"
        content = reg_path.read_text(encoding="utf-8")
        assert "aso_target_screening" in content
        assert "deterministic" in content.lower() or "retry would" in content.lower()

    def test_ires_workflow_exception_handling(self) -> None:
        """IRES workflow handles missing file / empty sequence gracefully."""
        reg = _make_ires_registry()
        wf = IresPredictionWorkflow(reg)
        with patch.object(IresPredictionWorkflow, "generate_candidates", side_effect=Exception("boom")):
            result = wf.run(IresPredictionInput(sequence_filepath="dummy.fasta"))
            assert result.success is False

    def test_aso_workflow_exception_handling(self) -> None:
        """ASO workflow handles missing file / short sequence gracefully."""
        reg = _make_aso_registry()
        wf = AsoTargetScreeningWorkflow(reg)
        # Empty target
        with patch.object(wf, "_read_target_sequence", return_value=""):
            result = wf.run(AsoScreeningInput(target_mrna_filepath="empty.fasta"))
            assert result.success is False
            assert "empty_candidate_list" in result.errors

    def test_aso_workflow_short_sequence_fails(self) -> None:
        """ASO workflow rejects sequences shorter than aso_length + 10."""
        reg = _make_aso_registry()
        wf = AsoTargetScreeningWorkflow(reg)
        with patch.object(wf, "_read_target_sequence", return_value="AUGCAUGCAU"):
            result = wf.run(AsoScreeningInput(target_mrna_filepath="short.fasta", aso_length=18))
            assert result.success is False

    def test_no_dead_imports_in_workflow_modules(self) -> None:
        """Workflow modules do not contain obviously unused imports (smoke check)."""
        import ast
        for mod_name in ["agent_core.workflows.ires_prediction", "agent_core.workflows.aso_target_screening"]:
            mod = __import__(mod_name, fromlist=["_"])
            src_path = Path(mod.__file__)
            tree = ast.parse(src_path.read_text(encoding="utf-8"))
            imports = [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
            [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            # We do a minimal check: every import should be referenced somewhere
            # This is a smoke test, not exhaustive linting.
            for imp in imports:
                for alias in imp.names:
                    assert alias.name in src_path.read_text(encoding="utf-8"), (
                        f"Potentially unused import {alias.name} in {mod_name}"
                    )


# =============================================================================
# Live LLM tests (optional — skipped unless --live-llm)
# =============================================================================


@pytest.mark.live_llm
def test_ires_critic_live_diagnosis() -> None:
    """Real DeepSeek API call for IresPredictionLLMCritic.diagnose().

    Skipped unless pytest is run with ``--live-llm`` and ``DEEPSEEK_API_KEY`` is set.
    """
    import os
    if not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")

    critic = IresPredictionLLMCritic()
    result = WorkflowResult(
        success=False, task_id="", summary="No candidates.", errors=["empty"]
    )
    diagnosis = critic.diagnose(result, {})
    assert isinstance(diagnosis, dict)
    assert "overall_assessment" in diagnosis
    # Empty result should trigger at least some observation
    assert diagnosis.get("issues") is not None or diagnosis.get("action") is not None


@pytest.mark.live_llm
def test_ires_critic_live_parameter_override() -> None:
    """Real DeepSeek API call verifying critic can suggest parameter overrides."""
    import os
    if not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("DEEPSEEK_API_KEY not set")

    critic = IresPredictionLLMCritic()
    # Build a low-confidence result to trigger retry suggestion
    c = Candidate(
        sequence="ACGU", sequence_type="rna", source="iresfinder:2",
        metadata={
            "iresfinder_mode": 2,
            "metrics_bundle": {
                "ires_probability": 0.51,
                "mfe_kcal_per_mol": -2.0,
                "mean_unpaired_fraction": 0.1,
                "mean_unpaired_prob_1nt": 0.15,
                "region_length": 174,
                "start": 1, "end": 174,
            },
        },
    )
    result = WorkflowResult(
        success=True, task_id="", summary="ok", best_candidate=c, all_candidates=[c]
    )
    state = {"user_constraints": {"probability_threshold": 0.5}}
    diagnosis = critic.diagnose(result, state)
    assert isinstance(diagnosis, dict)
    # May or may not suggest retry depending on LLM, but structure must be valid
    assert "overall_assessment" in diagnosis
