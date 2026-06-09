"""Tests for siRNA HTTP handler and FastAPI endpoints."""

from __future__ import annotations

import importlib.util
from unittest.mock import patch

import pytest

from agent_core.tool_executor import ToolExecutor
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_baseline_eval import StubGcTool


def _have_fastapi() -> bool:
    return importlib.util.find_spec("fastapi") is not None


# ── Stub tools tailored for siRNA ──

class _StubEvitarTool:
    name = "design_sirna_with_evitar"

    def invoke(self, kwargs):
        return {
            "top_results": [
                {"siRNA": "AUGCCCGGGUUUAAAUUUAAA", "score": "0.95"},
                {"siRNA": "GGGCCCAUUAAAUUUAAAUUU", "score": "0.75"},
            ],
            "result_count": 2,
            "mode": kwargs.get("mode", "existing"),
            "predict": kwargs.get("predict", "predsi"),
            "off_target": False,
        }


class _StubDuplexTool:
    name = "compute_sirna_duplex_binding_vienna"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -28.5,
            "sense": "AUGCCC",
            "antisense": "UUUGGG",
            "structure": "((((((",
        }


class _StubBlastZeroTool:
    name = "run_blastn_similarity_search"

    def invoke(self, kwargs):
        return {"hit_count": 0, "subject_mode": "fasta"}


class _StubFoldTool:
    name = "predict_rna_secondary_structure"

    def invoke(self, kwargs):
        return {
            "mfe_kcal_per_mol": -15.2,
            "structure": "(((...)))",
        }


def _build_stub_executor() -> ToolExecutor:
    reg = ToolRegistry()
    reg.register(StubGcTool())
    reg.register(_StubFoldTool())
    reg.register(_StubEvitarTool())
    reg.register(_StubDuplexTool())
    reg.register(_StubBlastZeroTool())
    return ToolExecutor(reg)


def test_execute_sirna_happy_path():
    from workflow_api.sirna_handler import execute_sirna_workflow_http
    from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest

    req = SirnaWorkflowHttpRequest(
        mode="antiviral",
        target_sequence="AUGC" * 30,
        candidate_count=5,
        task_id="sirna-test-1",
        debug=True,
    )
    ex = _build_stub_executor()
    out = execute_sirna_workflow_http(req, executor=ex)
    assert out.success is True
    assert out.task_type == "sirna"
    assert out.task_id == "sirna-test-1"
    assert out.best_candidate is not None
    assert len(out.candidates) > 0


def test_execute_sirna_generic_mode():
    from workflow_api.sirna_handler import execute_sirna_workflow_http
    from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest

    req = SirnaWorkflowHttpRequest(
        mode="generic",
        target_sequence="AUGC" * 30,
        candidate_count=3,
    )
    ex = _build_stub_executor()
    out = execute_sirna_workflow_http(req, executor=ex)
    assert out.success is True
    assert all(c.source.startswith("sliding_window") for c in out.candidates)


def test_execute_sirna_missing_target_raises():
    from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest

    with pytest.raises(Exception):
        SirnaWorkflowHttpRequest(mode="generic")


@pytest.mark.skipif(not _have_fastapi(), reason="fastapi not installed")
def test_fastapi_agent_run_sirna():
    from fastapi.testclient import TestClient

    from agent_core.workflow_models import Candidate, WorkflowResult
    from workflow_api.app import app

    mock_result = WorkflowResult(
        success=True,
        task_id="sirna-agent-test",
        best_candidate=Candidate(sequence="AUGCCCGGGUUUAAAUUUAAA", scores={"total_score": 0.95}),
        all_candidates=[Candidate(sequence="AUGCCCGGGUUUAAAUUUAAA", scores={"total_score": 0.95})],
        summary="ok",
    )
    with patch("workflow_api.app._agent_runner.run", return_value={
        "workflow_result": mock_result,
        "task_id": "sirna-agent-test",
    }):
        client = TestClient(app)
        r = client.post(
            "/v1/agent/run",
            json={
                "user_text": "Design antiviral siRNA against target sequence " + "AUGC" * 30,
                "debug": False,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["best_candidate"] is not None
