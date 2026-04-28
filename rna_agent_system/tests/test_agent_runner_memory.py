"""Tests for AgentRunner multi-turn memory integration (Layer 4)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agent_core.planning.base import ExecutionController, ExecutionPlan, PlanStep
from agent_core.runner import AgentRunner
from agent_core.session_memory import SessionMemory
from agent_core.state import AgentState, default_state
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry


def test_runner_without_memory_starts_fresh_each_turn() -> None:
    """When session_memory is None, each .run() begins from default_state."""
    planner = MagicMock()
    plan = ExecutionPlan(steps=[
        PlanStep(step_id="s1", type="capability", target="mock_cap")
    ])
    planner.plan_with_state = MagicMock(return_value=plan)

    exe = ToolExecutor(build_default_tool_registry(include_demo=False))
    runner = AgentRunner(planner, exe)

    with patch.object(
        ExecutionController, "execute", return_value=default_state("turn1")
    ) as mock_exec:
        state1 = runner.run("turn1")
        passed_state = mock_exec.call_args[0][1]
        # default_state("") creates one empty HumanMessage, then run() appends
        # the real user_input plus the routing AIMessage.
        human_msgs = [m for m in passed_state["messages"] if isinstance(m, HumanMessage)]
        assert len(human_msgs) == 2  # empty placeholder + turn1
        assert human_msgs[-1].content == "turn1"

        state2 = runner.run("turn2")
        passed_state2 = mock_exec.call_args[0][1]
        # Without memory, each run starts fresh from default_state("")
        human_msgs2 = [m for m in passed_state2["messages"] if isinstance(m, HumanMessage)]
        assert len(human_msgs2) == 2
        assert human_msgs2[-1].content == "turn2"


def test_runner_with_memory_persists_across_turns() -> None:
    """When session_memory is provided, prior state is reloaded on subsequent runs."""
    planner = MagicMock()
    plan = ExecutionPlan(steps=[
        PlanStep(step_id="s1", type="capability", target="mock_cap")
    ])
    planner.plan_with_state = MagicMock(return_value=plan)

    exe = ToolExecutor(build_default_tool_registry(include_demo=False))
    memory = SessionMemory()
    runner = AgentRunner(planner, exe, session_memory=memory)

    sid = "session-xyz"

    # Simulate first turn result containing a candidate_sequence
    turn1_result = default_state("")
    turn1_result["candidate_sequence"] = "AUGCGCUAGC"
    turn1_result["messages"] = [
        HumanMessage(content="Design mRNA for GFP"),
    ]

    with patch.object(ExecutionController, "execute", return_value=turn1_result):
        state1 = runner.run("Design mRNA for GFP", session_id=sid)
        assert state1["candidate_sequence"] == "AUGCGCUAGC"

    # Simulate second turn — the runner should load the persisted state
    turn2_result = default_state("")
    turn2_result["candidate_sequence"] = "AUGCGCUAGC"  # same or updated
    turn2_result["messages"] = [
        HumanMessage(content="Design mRNA for GFP"),
        HumanMessage(content="Make it more stable"),
    ]

    with patch.object(ExecutionController, "execute", return_value=turn2_result) as mock_exec:
        state2 = runner.run("Make it more stable", session_id=sid)
        passed_state = mock_exec.call_args[0][1]
        # Prior candidate_sequence should be present from memory
        assert passed_state.get("candidate_sequence") == "AUGCGCUAGC"
        # Messages should include both turns
        contents = [m.content for m in passed_state["messages"]]
        assert "Design mRNA for GFP" in contents
        assert "Make it more stable" in contents


def test_runner_explicit_state_bypasses_memory() -> None:
    """Passing an explicit *state* argument skips load/save for backward compat."""
    planner = MagicMock()
    plan = ExecutionPlan(steps=[
        PlanStep(step_id="s1", type="capability", target="mock_cap")
    ])
    planner.plan_with_state = MagicMock(return_value=plan)

    exe = ToolExecutor(build_default_tool_registry(include_demo=False))
    memory = SessionMemory()
    runner = AgentRunner(planner, exe, session_memory=memory)

    explicit = default_state("explicit")
    explicit["candidate_sequence"] = "EXPLICIT_SEQ"

    with patch.object(ExecutionController, "execute", return_value=explicit) as mock_exec:
        result = runner.run("new input", session_id="session-abc", state=explicit)
        passed_state = mock_exec.call_args[0][1]
        # Should use the explicit state, not load from memory
        assert passed_state["candidate_sequence"] == "EXPLICIT_SEQ"

    # Memory should not have been touched for the explicit-state path
    assert "session-abc" not in memory._store


def test_runner_save_noop_for_empty_session_id() -> None:
    """An empty session_id must not crash and must not store state."""
    planner = MagicMock()
    plan = ExecutionPlan(steps=[
        PlanStep(step_id="s1", type="capability", target="mock_cap")
    ])
    planner.plan_with_state = MagicMock(return_value=plan)

    exe = ToolExecutor(build_default_tool_registry(include_demo=False))
    memory = SessionMemory()
    runner = AgentRunner(planner, exe, session_memory=memory)

    with patch.object(ExecutionController, "execute", return_value=default_state("")):
        runner.run("hello", session_id="")

    assert memory._store == {}
