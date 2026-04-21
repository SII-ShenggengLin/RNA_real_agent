from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
import requests

from agent_core.file_manager import PROJECT_ROOT
from agent_core.workflow_tools.rna_gc_content_workflow import (
    RnaGcContentWorkflowInput,
    run_rna_gc_content_workflow,
)


@pytest.fixture()
def gc_sample_filepath():
    """File under rna_agent_system/workspace/ (service reads this path shape)."""
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_gc_workflow_demo.fasta"
    (ws / name).write_text("AUGCAUAUGCAU\n", encoding="utf-8")
    return f"workspace/{name}"


def test_run_rna_gc_content_parses_metrics(gc_sample_filepath):
    fake_body = {
        "input_filepath": gc_sample_filepath,
        "resolved_filepath": "/x",
        "sequence_length": 12,
        "g_count": 3,
        "c_count": 3,
        "gc_count": 6,
        "gc_content": 0.5,
        "model": "rna-sequence-metrics-gc",
    }

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return fake_body

    with patch(
        "agent_core.workflow_tools.rna_gc_content_workflow.requests.post",
        return_value=_Resp(),
    ):
        out = run_rna_gc_content_workflow(
            RnaGcContentWorkflowInput(
                filepath=gc_sample_filepath, service_url="http://test/gc-content"
            )
        )

    assert out.success is True
    assert out.metrics["gc_content"] == 0.5
    assert out.metrics["sequence_length"] == 12
    assert out.metrics["gc_count"] == 6
    assert out.artifacts["model"] == "rna-sequence-metrics-gc"


def test_run_rna_gc_content_http_error(gc_sample_filepath):
    class _Resp:
        ok = False
        status_code = 400
        text = "bad"

        def json(self):
            return {"detail": "not found"}

    with patch(
        "agent_core.workflow_tools.rna_gc_content_workflow.requests.post",
        return_value=_Resp(),
    ):
        out = run_rna_gc_content_workflow(
            RnaGcContentWorkflowInput(
                filepath=gc_sample_filepath, service_url="http://test/gc-content"
            )
        )

    assert out.success is False
    assert out.error is not None
    assert out.error.get("status_code") == 400


def test_python_function_tool_and_executor_writes_trace(gc_sample_filepath):
    from agent_core.tool_executor import ToolExecutor
    from agent_core.tool_registry import ToolRegistry
    from agent_core.workflow_models import Candidate, TaskState
    from agent_core.workflow_tools import create_workflow_rna_gc_content_tool

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {
                "sequence_length": 6,
                "g_count": 0,
                "c_count": 0,
                "gc_count": 0,
                "gc_content": 0.0,
                "model": "rna-sequence-metrics-gc",
            }

    with patch(
        "agent_core.workflow_tools.rna_gc_content_workflow.requests.post",
        return_value=_Resp(),
    ):
        reg = ToolRegistry()
        reg.register(create_workflow_rna_gc_content_tool())
        ex = ToolExecutor(reg, logger=logging.getLogger("test_gc"))
        task = TaskState(task_type="t")
        cand = Candidate(sequence="AUG", source="test")
        r = ex.run_tool_for_workflow(
            "workflow_rna_gc_content",
            task=task,
            candidate=cand,
            filepath=gc_sample_filepath,
        )
    assert r.success
    assert len(cand.tool_records) == 1
    assert len(task.logs) == 1


@pytest.mark.integration
def test_run_rna_gc_content_live_if_service_up(gc_sample_filepath):
    try:
        requests.get("http://127.0.0.1:8020/health", timeout=1.0).raise_for_status()
    except (requests.RequestException, OSError):
        pytest.skip("port 8020 rna_sequence_metrics_service not up")

    out = run_rna_gc_content_workflow(RnaGcContentWorkflowInput(filepath=gc_sample_filepath))
    assert out.success
    assert "gc_content" in out.metrics
