from __future__ import annotations

import importlib.util
from unittest.mock import patch

import pytest


def _have_fastapi() -> bool:
    return importlib.util.find_spec("fastapi") is not None

from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_baseline_eval import StubCaiTool, StubFoldTool, StubGcTool


@pytest.fixture()
def stub_registry():
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    reg.register(StubCaiTool())
    return reg


def test_execute_http_happy_path(stub_registry):
    from workflow_api.mrna_handler import execute_mrna_workflow_http
    from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

    req = MrnaWorkflowHttpRequest(
        sequence="AUGCAUGCAUGCAU",
        task_id="manual-task-1",
        task_type="mrna",
        debug=True,
        constraints={"persist_run": False},
    )
    ex = ToolExecutor(stub_registry)
    out = execute_mrna_workflow_http(req, executor=ex)
    assert out.success is True
    assert out.task_id == "manual-task-1"
    assert out.best_candidate is not None
    assert out.trace is not None
    assert len(out.warnings) == 0


def test_execute_http_tool_failure_returns_warnings(stub_registry):
    from workflow_api.mrna_handler import execute_mrna_workflow_http
    from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

    class _Fail:
        name = "compute_rna_sequence_gc_content"

        def invoke(self, kwargs):
            from agent_core.tool_runtime import ToolResult

            return ToolResult(success=False, tool_name=self.name, error={"message": "down"})

    reg = ToolRegistry()
    reg.register(_Fail())
    reg.register(StubFoldTool())

    req = MrnaWorkflowHttpRequest(sequence="AUGC", constraints={"persist_run": False})
    out = execute_mrna_workflow_http(req, executor=ToolExecutor(reg))
    assert out.success is True
    assert len(out.warnings) >= 1
    assert out.best_candidate is not None


def test_execute_internal_error_no_debug_detail(stub_registry):
    from workflow_api.mrna_handler import execute_mrna_workflow_http
    from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

    req = MrnaWorkflowHttpRequest(sequence="AUG", debug=False)
    with patch("workflow_api.mrna_handler.run_mrna_workflow", side_effect=RuntimeError("internal")):
        out = execute_mrna_workflow_http(req, executor=ToolExecutor(stub_registry))
    assert out.success is False
    assert out.debug_detail is None
    assert len(out.errors) >= 1


def test_execute_internal_error_debug_detail(stub_registry):
    from workflow_api.mrna_handler import execute_mrna_workflow_http
    from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest

    req = MrnaWorkflowHttpRequest(sequence="AUG", debug=True)
    with patch("workflow_api.mrna_handler.run_mrna_workflow", side_effect=RuntimeError("internal")):
        out = execute_mrna_workflow_http(req, executor=ToolExecutor(stub_registry))
    assert out.success is False
    assert out.debug_detail is not None
    assert "Traceback" in out.debug_detail


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_fastapi_422_when_both_sequence_and_protein():
    from fastapi.testclient import TestClient

    from workflow_api.app import app

    client = TestClient(app)
    r = client.post(
        "/v1/workflows/mrna/run",
        json={"sequence": "AUG", "protein": "MK"},
    )
    assert r.status_code == 422


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_fastapi_mrna_ok_with_stub_registry(stub_registry):
    from fastapi.testclient import TestClient

    from workflow_api.app import app

    with patch("workflow_api.mrna_handler.build_default_tool_registry", return_value=stub_registry):
        client = TestClient(app)
        r = client.post(
            "/v1/workflows/mrna/run",
            json={
                "sequence": "AUGCAUGCAUGCAU",
                "debug": False,
                "constraints": {"persist_run": False},
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["task_id"]
        assert data["best_candidate"] is not None
