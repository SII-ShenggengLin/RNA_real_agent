"""Layer-6 fresh-data audit regressions (2026-08-22).

Defects found by ``workspace/layer6_fresh_audit_2026-08-22/`` (live audit on
freshly fetched PRL NM_000948 / IL10 NM_000572 / HAV NC_001489 data) and
fixed the same day:

1. ``AgentRunner.run_pipeline`` never set the session context, so tool-level
   artifacts of pipeline runs (CLI ``--pipeline-file``, API
   ``/v1/agent/pipeline``) leaked into the global workspace root instead of
   ``workspace/sessions/<session_id>/`` (violating the Layer-5
   no-global-root-leak contract that ``run_form``/``stream_form`` uphold).
2. ``/v1/agent/run`` misreported a crashed node as success: when the node
   raised (``workflow_result`` absent, ``pipeline_result.success=False``)
   the endpoint fell through to the generic fallback branch and returned
   ``"success": True``.
3. ``/v1/agent/run`` echoed a task_id that did not identify the session the
   artifacts were written under when the request omitted ``task_id`` (a
   fresh unrelated uuid; ``state.get("task_id")`` was dead code).
4. ``MrnaSequenceScoringWorkflow.run`` accepted ``progress_callback`` but
   never called it, so the locked ``stream_form`` event sequence
   (``router, plan, progress…, tool_execution, runner``) carried no
   progress events for this workflow and the CLI
   progress lines stayed silent.
5. Nobody emitted ``step_start``/``step_done`` progress events — the CLI
   handlers for them were dead code.
6. ``cli/form_chat.py --pipeline-file`` still had the bare ``input()`` on
   service-start failure (the 2026-07 EOFError incident; the isatty guard
   had been added only to the ``--workflow`` branch).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

CLI_DIR = APP_ROOT / "cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from agent_core.agents.base import AgentResult  # noqa: E402
from agent_core.agents.quality_agent import QualityReport  # noqa: E402
from agent_core.file_manager import _SESSION_ID_CTX  # noqa: E402
from agent_core.pipeline.models import PipelinePlan, PipelineResult  # noqa: E402
from agent_core.runner import AgentRunner  # noqa: E402
from agent_core.workflow_models import Candidate, WorkflowResult  # noqa: E402
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringWorkflow  # noqa: E402
from cli import form_chat  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# 1. run_pipeline scopes the session context (no global-root leak)


def _bare_runner_with_capture(captured: dict) -> AgentRunner:
    """An AgentRunner whose pipeline_agent.execute records the session ctx."""
    runner = object.__new__(AgentRunner)  # bypass heavy __init__; only run_pipeline is used

    def _execute(plan, state=None, progress_callback=None):
        captured["session_ctx"] = _SESSION_ID_CTX.get()
        return PipelineResult(plan_id=plan.plan_id, success=True, node_results={})

    runner.pipeline_agent = SimpleNamespace(execute=_execute)
    return runner


def test_run_pipeline_sets_session_ctx_from_state() -> None:
    captured: dict = {}
    runner = _bare_runner_with_capture(captured)
    plan = PipelinePlan.single("mrna_sequence_scoring", {"sequence": "AUGCAUGCAUGC"})

    runner.run_pipeline(plan, state={"session_id": "l6reg_pipe_sid"})

    assert captured["session_ctx"] == "l6reg_pipe_sid"


def test_run_pipeline_without_state_keeps_empty_ctx() -> None:
    captured: dict = {}
    runner = _bare_runner_with_capture(captured)
    plan = PipelinePlan.single("mrna_sequence_scoring", {"sequence": "AUGCAUGCAUGC"})

    runner.run_pipeline(plan)

    assert captured["session_ctx"] == ""


def test_run_pipeline_resets_session_ctx_afterwards() -> None:
    captured: dict = {}
    runner = _bare_runner_with_capture(captured)
    plan = PipelinePlan.single("mrna_sequence_scoring", {"sequence": "AUGCAUGCAUGC"})

    runner.run_pipeline(plan, state={"session_id": "l6reg_reset"})

    assert _SESSION_ID_CTX.get() == ""


# ─────────────────────────────────────────────────────────────────────────────
# 2/3. /v1/agent/run: crashed node is not success; task_id identifies the session


def _fake_wf_result() -> WorkflowResult:
    return WorkflowResult(
        success=True,
        task_id="t1",
        best_candidate=Candidate(sequence="AUGC", source="test"),
        all_candidates=[Candidate(sequence="AUGC", source="test")],
    )


@pytest.fixture
def client() -> TestClient:
    from workflow_api import app as workflow_app

    return TestClient(workflow_app.app)


def test_run_endpoint_crashed_node_reports_failure(client: TestClient, monkeypatch) -> None:
    state = {
        "workflow_result": None,  # node crashed — no WorkflowResult produced
        "session_id": "l6reg_crash",
        "pipeline_result": {
            "success": False,
            "errors": ["Node n1: execution failed: ValueError: boom"],
        },
        "final_report": "Workflow failed: Node n1: execution failed: ValueError: boom",
        "_routing_method": "explicit",
        "tool_results": {},
    }
    wf_app = __import__("workflow_api.app", fromlist=["_agent_runner"])
    monkeypatch.setattr(
        wf_app,
        "_agent_runner",
        SimpleNamespace(
            workflow_registry={"mrna_sequence_scoring": object()},
            run_form=lambda *a, **k: state,
        ),
    )
    response = client.post(
        "/v1/agent/run",
        json={"workflow": "mrna_sequence_scoring", "params": {"sequence": "AUGCAUGCAUGC"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Node n1: execution failed: ValueError: boom" in data["errors"]


def test_run_endpoint_task_id_identifies_session_dir(client: TestClient, monkeypatch) -> None:
    state = {
        "workflow_result": _fake_wf_result(),
        "session_id": "l6reg_echo_sid",
    }
    monkeypatch.setattr(
        __import__("workflow_api.app", fromlist=["_agent_runner"]),
        "_agent_runner",
        SimpleNamespace(workflow_registry={"mrna_sequence_scoring": object(), "ires_prediction": object()}, run_form=lambda *a, **k: state),
    )
    response = client.post(
        "/v1/agent/run",
        json={"workflow": "mrna_sequence_scoring", "params": {"sequence": "AUGCAUGCAUGC"}},
    )
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "l6reg_echo_sid"  # identifies the artifact session dir


def test_run_endpoint_exception_echoes_session_id(client: TestClient, monkeypatch) -> None:
    def _raise(*a, **k):
        raise ValueError("Missing required parameters for ires_prediction: sequence_filepath")

    monkeypatch.setattr(
        __import__("workflow_api.app", fromlist=["_agent_runner"]),
        "_agent_runner",
        SimpleNamespace(workflow_registry={"mrna_sequence_scoring": object(), "ires_prediction": object()}, run_form=_raise),
    )
    response = client.post(
        "/v1/agent/run",
        json={
            "workflow": "ires_prediction",
            "params": {},
            "task_id": "l6reg_exc_sid",
        },
    )
    data = response.json()
    assert data["success"] is False
    assert data["task_id"] == "l6reg_exc_sid"


def test_pipeline_endpoint_scopes_session_and_echoes_it(client: TestClient, monkeypatch) -> None:
    captured: dict = {}

    def _run_pipeline(plan, state=None):
        captured["state"] = state
        return PipelineResult(plan_id=plan.plan_id, success=True, node_results={})

    monkeypatch.setattr(
        __import__("workflow_api.app", fromlist=["_agent_runner"]),
        "_agent_runner",
        SimpleNamespace(run_pipeline=_run_pipeline),
    )
    plan_payload = {
        "plan_id": "l6reg_plan",
        "nodes": [
            {
                "node_id": "n1",
                "workflow": "mrna_sequence_scoring",
                "static_params": {"sequence": "AUGCAUGCAUGC"},
            }
        ],
        "edges": [],
    }
    response = client.post(
        "/v1/agent/pipeline", json={"plan": plan_payload, "task_id": "l6reg_pipe_task"}
    )
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == "l6reg_pipe_task"
    assert captured["state"]["session_id"] == "l6reg_pipe_task"


# ─────────────────────────────────────────────────────────────────────────────
# 4. mrna_sequence_scoring emits progress events (locked stream contract)


def _scoring_workflow_for_progress(monkeypatch) -> MrnaSequenceScoringWorkflow:
    wf = MrnaSequenceScoringWorkflow(SimpleNamespace(executor=None))
    wf.auto_start_services = False
    monkeypatch.setattr(
        wf,
        "evaluate",
        lambda candidate: {
            "gc_content": 0.5,
            "sequence_length": 24,
            "mfe_kcal_per_mol": -5.0,
            "cai_score": 0.9,
        },
        raising=True,
    )
    return wf


def test_scoring_run_emits_generate_and_evaluate_progress(monkeypatch) -> None:
    wf = _scoring_workflow_for_progress(monkeypatch)
    events: list[dict] = []
    result = wf.run(
        {"sequence": "AUGCAUGCAUGCAUGCAUGCAUGC", "run_gc_tool": False, "run_fold_tool": False},
        progress_callback=events.append,
    )
    assert result.success is True
    kinds = [e["event"] for e in events]
    assert kinds[0] == "generate_complete"
    assert events[0]["candidate_count"] == 1
    assert kinds.count("evaluate_progress") == 1
    assert events[-1]["current"] == 1 and events[-1]["total"] == 1


def test_scoring_run_emits_events_even_for_empty_input(monkeypatch) -> None:
    wf = _scoring_workflow_for_progress(monkeypatch)
    events: list[dict] = []
    result = wf.run({"sequence": "", "run_gc_tool": False, "run_fold_tool": False},
                    progress_callback=events.append)
    assert result.success is False  # empty-candidates hard failure contract
    assert [e["event"] for e in events] == ["generate_complete"]
    assert events[0]["candidate_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. PipelineAgent emits step_start/step_done per node


def _pipeline_agent_with_stub_specialist(events: list[dict]):
    from agent_core.agents.pipeline_agent import PipelineAgent

    class _StubSpecialist:
        def run(self, node_id, params, quality_agent, state=None, progress_callback=None):
            return AgentResult(
                node_id=node_id,
                workflow="mrna_sequence_scoring",
                success=True,
                metadata={
                    "quality_report": QualityReport(
                        overall_assessment="ok",
                        quality_score=1.0,
                        action="pass",
                        reasoning="fine",
                    )
                },
            )

    class _StubQA:
        pass

    class _StubSynthesis:
        @staticmethod
        def synthesize(plan, node_results, quality_reports):
            return "stub report"

    return PipelineAgent(
        specialist_registry={"mrna_sequence_scoring": _StubSpecialist()},
        quality_agent=_StubQA(),
        synthesis_agent=_StubSynthesis(),
    )


def test_pipeline_agent_emits_step_events() -> None:
    events: list[dict] = []
    agent = _pipeline_agent_with_stub_specialist(events)
    plan = PipelinePlan.single("mrna_sequence_scoring", {"sequence": "AUGCAUGCAUGC"})

    result = agent.execute(plan, state={}, progress_callback=events.append)

    assert result.success is True
    kinds = [(e["event"], e.get("target")) for e in events]
    assert ("step_start", "n1") in kinds
    assert ("step_done", "n1") in kinds
    done = next(e for e in events if e["event"] == "step_done")
    assert done["success"] is True


def test_pipeline_agent_emits_step_done_false_on_crash() -> None:
    from agent_core.agents.pipeline_agent import PipelineAgent

    class _CrashingSpecialist:
        def run(self, *a, **k):
            raise RuntimeError("node exploded")

    agent = PipelineAgent(
        specialist_registry={"mrna_sequence_scoring": _CrashingSpecialist()},
        quality_agent=SimpleNamespace(),
        synthesis_agent=SimpleNamespace(synthesize=lambda *a, **k: "report"),
    )
    events: list[dict] = []
    plan = PipelinePlan.single("mrna_sequence_scoring", {"sequence": "AUGCAUGCAUGC"})

    result = agent.execute(plan, state={}, progress_callback=events.append)

    assert result.success is False
    done = next(e for e in events if e["event"] == "step_done")
    assert done["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. CLI --pipeline-file: no bare input() on service failure with non-tty stdin


class _NonTty(io.StringIO):
    def isatty(self) -> bool:
        return False


@pytest.fixture
def cli_env(monkeypatch, tmp_path):
    """Patch the heavy parts of form_chat.main() for the --pipeline-file branch."""
    monkeypatch.setattr(form_chat.resource_checker, "check_all", lambda: (True, "ok"))
    monkeypatch.setattr(
        form_chat,
        "AgentRunner",
        lambda **kwargs: SimpleNamespace(run_pipeline=lambda plan, state=None: None),
    )
    monkeypatch.setattr(form_chat, "SessionMemory", lambda: None)
    plan = {
        "plan_id": "l6reg_cli_plan",
        "nodes": [
            {
                "node_id": "n1",
                "workflow": "mrna_sequence_scoring",
                "static_params": {"sequence": "AUGCAUGCAUGCAUGCAUGC"},
            }
        ],
        "edges": [],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan))

    run_calls: list[dict] = []

    def _fake_run_pipeline(runner, session_id, plan, *, save_file=True):
        run_calls.append({"session_id": session_id, "plan_id": plan.plan_id})
        return SimpleNamespace(plan_id=plan.plan_id, success=True, final_report="r")

    monkeypatch.setattr(form_chat, "_run_pipeline", _fake_run_pipeline)
    return SimpleNamespace(plan_file=plan_file, run_calls=run_calls)


def test_cli_pipeline_branch_survives_non_tty_service_failure(monkeypatch, cli_env) -> None:
    monkeypatch.setattr(
        form_chat.service_orchestrator,
        "ensure_multi_workflow_services_ready",
        lambda workflows, **kw: (False, ["probe: service failed"]),
    )
    monkeypatch.setattr("sys.stdin", _NonTty())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "form_chat.py",
            "--pipeline-file",
            str(cli_env.plan_file),
            "--session-id",
            "l6reg_cli_sid",
        ],
    )

    rc = form_chat.main()  # pre-fix: EOFError from the bare input()

    assert rc == 0
    assert cli_env.run_calls and cli_env.run_calls[0]["session_id"] == "l6reg_cli_sid"


def test_cli_pipeline_branch_still_prompts_on_tty(monkeypatch, cli_env) -> None:
    monkeypatch.setattr(
        form_chat.service_orchestrator,
        "ensure_multi_workflow_services_ready",
        lambda workflows, **kw: (False, ["probe: service failed"]),
    )

    class _Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", _Tty())
    monkeypatch.setattr("builtins.input", lambda *a: "n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["form_chat.py", "--pipeline-file", str(cli_env.plan_file), "--session-id", "s"],
    )

    rc = form_chat.main()

    assert rc == 1
    assert not cli_env.run_calls  # user declined — pipeline never runs


# ─────────────────────────────────────────────────────────────────────────────
# _format_final_report reports a crashed pipeline instead of "completed"


def test_format_final_report_reports_failed_pipeline() -> None:
    state = {
        "workflow_result": None,
        "pipeline_result": {
            "success": False,
            "errors": ["Node n1: execution failed: ValueError: boom"],
        },
    }
    report = AgentRunner._format_final_report(state)
    assert report.startswith("Workflow failed:")
    assert "ValueError: boom" in report


def test_format_final_report_tool_results_branch_unchanged() -> None:
    state = {"workflow_result": None, "tool_results": {"gc": {"ok": 1}}}
    report = AgentRunner._format_final_report(state)
    assert "已执行工具" in report
