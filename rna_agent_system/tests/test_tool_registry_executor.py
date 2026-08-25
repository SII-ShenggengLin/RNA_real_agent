from __future__ import annotations

import logging

from langchain_core.tools import tool

from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.tool_registry import ToolNotRegisteredError, ToolRegistry
from agent_core.workflow_models import Candidate, TaskState


@tool
def mock_echo(text: str = "") -> dict:
    """Echo tool for executor happy-path tests."""

    return {"echo": text, "length": len(text)}


@tool
def mock_exploding(text: str = "") -> str:
    """Always raises for executor error-path tests."""

    raise ValueError("intentional failure")


def _registry_with(*tools) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_many(list(tools))
    return registry


def test_registry_register_get_list_has():
    registry = _registry_with(mock_echo)
    assert registry.has("mock_echo")
    assert "mock_echo" in registry.list_names()
    tool_obj = registry.get("mock_echo")
    assert getattr(tool_obj, "name", None) == "mock_echo"


def test_registry_get_missing_raises():
    registry = ToolRegistry()
    try:
        registry.get("nonexistent_tool_xyz")
        raise AssertionError("expected ToolNotRegisteredError")
    except ToolNotRegisteredError as exc:
        assert exc.tool_name == "nonexistent_tool_xyz"


def test_executor_unknown_tool_returns_failure_result():
    registry = ToolRegistry()
    executor = ToolExecutor(registry, logger=logging.getLogger("test"))
    result = executor.run_tool("missing")
    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "ToolNotRegisteredError"


def test_executor_success_echo_tool():
    executor = ToolExecutor(_registry_with(mock_echo), logger=logging.getLogger("test"))
    result = executor.run_tool("mock_echo", text="hello")
    assert result.success is True
    assert result.artifacts["result"]["length"] == 5


def test_executor_handles_invoke_exception():
    executor = ToolExecutor(_registry_with(mock_exploding), logger=logging.getLogger("test"))
    result = executor.run_tool("mock_exploding", text="x")
    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "ValueError"


def test_run_tool_for_workflow_writes_candidate_and_task_logs():
    executor = ToolExecutor(_registry_with(mock_echo), logger=logging.getLogger("test"))
    task = TaskState(task_type="demo")
    cand = Candidate(sequence="AUG", source="test")
    result = executor.run_tool_for_workflow(
        "mock_echo",
        task=task,
        candidate=cand,
        step_name="demo_step",
        text="hi",
    )
    assert result.success is True
    assert len(cand.tool_records) == 1
    assert cand.tool_records[0].tool_name == "mock_echo"
    assert cand.tool_records[0].step_name == "demo_step"
    assert len(task.logs) == 1
    assert task.logs[0].tool_name == "mock_echo"


def test_run_tool_for_workflow_only_task_trace():
    executor = ToolExecutor(_registry_with(mock_echo), logger=logging.getLogger("test"))
    task = TaskState(task_type="demo")
    executor.run_tool_for_workflow(
        "mock_echo",
        task=task,
        candidate=None,
        write_candidate=False,
        write_task_log=True,
        text="only-task",
    )
    assert len(task.logs) == 1
