"""Unit tests for Layer 4 — SessionMemory."""

from __future__ import annotations

from copy import deepcopy

import pytest

from agent_core.session_memory import SessionMemory
from agent_core.state import AgentState, default_state


def test_load_missing_session_returns_default() -> None:
    mem = SessionMemory()
    state = mem.load("nonexistent-session")
    assert state == default_state("")


def test_load_empty_session_id_returns_default() -> None:
    mem = SessionMemory()
    state = mem.load("")
    assert state == default_state("")


def test_save_and_load_roundtrip() -> None:
    mem = SessionMemory()
    sid = "test-session-123"
    original = default_state("Design mRNA for GFP")
    original["candidate_sequence"] = "AUGCGCUAGCUAGC"
    original["tool_results"] = {"fold": {"mfe": -25.3}}

    mem.save(sid, original)
    loaded = mem.load(sid)

    assert loaded["candidate_sequence"] == "AUGCGCUAGCUAGC"
    assert loaded["tool_results"]["fold"]["mfe"] == -25.3
    assert loaded["messages"] == original["messages"]


def test_load_returns_deep_copy() -> None:
    mem = SessionMemory()
    sid = "test-session-456"
    original = default_state("hello")
    original["candidate_sequence"] = "AAA"

    mem.save(sid, original)
    loaded = mem.load(sid)

    # Mutating the loaded state must not affect the stored copy.
    loaded["candidate_sequence"] = "BBB"
    reloaded = mem.load(sid)
    assert reloaded["candidate_sequence"] == "AAA"


def test_save_does_not_mutate_original() -> None:
    mem = SessionMemory()
    sid = "test-session-789"
    original = default_state("hello")
    original["candidate_sequence"] = "CCC"

    mem.save(sid, original)
    original["candidate_sequence"] = "DDD"

    reloaded = mem.load(sid)
    assert reloaded["candidate_sequence"] == "CCC"


def test_save_empty_session_id_is_noop() -> None:
    mem = SessionMemory()
    original = default_state("hello")
    mem.save("", original)
    # No exception and store remains empty.
    assert mem._store == {}


def test_multi_turn_message_accumulation() -> None:
    """Simulate two turns: the second load must contain the first turn's data."""
    mem = SessionMemory()
    sid = "multi-turn-session"

    # Turn 1
    state1 = default_state("Design mRNA for GFP")
    state1["candidate_sequence"] = "SEQ1"
    mem.save(sid, state1)

    # Turn 2 — load previous state and append new user input
    state2 = mem.load(sid)
    state2["messages"].append({"role": "user", "content": "Make it more stable"})
    state2["candidate_sequence"] = "SEQ2"
    mem.save(sid, state2)

    # Turn 3 — verify history is preserved
    state3 = mem.load(sid)
    assert state3["candidate_sequence"] == "SEQ2"
    assert len(state3["messages"]) == 2  # original + turn 2 user msg
