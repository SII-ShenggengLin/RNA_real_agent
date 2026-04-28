"""Layer 4 — Session & Memory: in-memory context persistence."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict

from agent_core.state import AgentState, default_state


class SessionMemory:
    """In-memory session store for multi-turn ``AgentState`` persistence.

    This is the **minimum viable** implementation using a plain ``dict``.
    It can be swapped for Redis, SQLite, or another backend without changing
    the ``AgentRunner`` interface.
    """

    def __init__(self) -> None:
        self._store: Dict[str, AgentState] = {}

    def load(self, session_id: str) -> AgentState:
        """Return the stored state for *session_id* or a fresh default.

        A missing session yields ``default_state("")`` (empty user input) so
        that the caller can append the real user text before execution.
        """
        if not session_id or session_id not in self._store:
            return default_state("")
        return deepcopy(self._store[session_id])

    def save(self, session_id: str, state: AgentState) -> None:
        """Persist a **deep copy** of *state* under *session_id*.

        No-op when *session_id* is empty.
        """
        if not session_id:
            return
        self._store[session_id] = deepcopy(state)
