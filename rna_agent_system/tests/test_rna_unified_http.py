"""Unified POST /v1/workflows/run dispatch (FastAPI optional)."""

from __future__ import annotations

import importlib.util

import pytest


def _have_fastapi() -> bool:
    return importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_unified_run_mrna_matches_direct_handler():
    from agent_core.tool_executor import ToolExecutor
    from agent_core.tool_registry import ToolRegistry
    from agent_core.workflow_baseline_eval import StubFoldTool, StubGcTool
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    from workflow_api.app import app
    from workflow_api.mrna_handler import execute_mrna_workflow_http
    from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest
    from workflow_api.rna_unified_handler import execute_rna_workflow_http

    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(StubFoldTool())
    ex = ToolExecutor(reg)

    req = MrnaWorkflowHttpRequest(
        sequence="AUGCAUGCAU",
        task_type="mrna",
        task_id="unified-compare-1",
        constraints={"persist_run": False},
    )
    direct = execute_mrna_workflow_http(req, executor=ex)
    unified = execute_rna_workflow_http(req, executor=ex)
    assert direct.success == unified.success
    assert direct.task_id == unified.task_id == "unified-compare-1"
    assert direct.summary == unified.summary

    with patch("workflow_api.mrna_handler.build_default_tool_registry", return_value=reg):
        client = TestClient(app)
        r = client.post(
            "/v1/workflows/run",
            json={
                "sequence": "AUGCAUGCAU",
                "task_type": "mrna",
                "constraints": {"persist_run": False},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["task_type"] == "mrna"


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_unified_unknown_task_type():
    from fastapi.testclient import TestClient

    from workflow_api.app import app

    client = TestClient(app)
    r = client.post(
        "/v1/workflows/run",
        json={
            "sequence": "AUG",
            "task_type": "not_a_real_task",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "unknown task_type" in data["errors"][0].lower()


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_unified_placeholder_utr5():
    from fastapi.testclient import TestClient

    from workflow_api.app import app

    client = TestClient(app)
    r = client.post(
        "/v1/workflows/run",
        json={
            "sequence": "AUG",
            "task_type": "utr5",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert "not implemented" in data["errors"][0].lower()


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_mrna_endpoint_rejects_non_mrna_task_type():
    from fastapi.testclient import TestClient

    from workflow_api.app import app

    client = TestClient(app)
    r = client.post(
        "/v1/workflows/mrna/run",
        json={"sequence": "AUG", "task_type": "utr5"},
    )
    assert r.status_code == 422
