"""Layer 4 — Session & Memory: in-memory context persistence."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
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
        self._lock = Lock()

    def load(self, session_id: str) -> AgentState:
        """Return the stored state for *session_id* or a fresh default.

        A missing session yields ``default_state("")`` (empty user input) so
        that the caller can append the real user text before execution.
        """
        if not session_id:
            return default_state("")
        with self._lock:
            if session_id not in self._store:
                return default_state("")
            return deepcopy(self._store[session_id])

    def save(self, session_id: str, state: AgentState) -> None:
        """Persist a **deep copy** of *state* under *session_id*.

        No-op when *session_id* is empty.
        """
        if not session_id:
            return
        with self._lock:
            self._store[session_id] = deepcopy(state)

    def delete(self, session_id: str) -> bool:
        """Remove the stored state for *session_id*.

        Returns
        -------
        bool
            ``True`` if a state existed and was removed, ``False`` otherwise.
        """
        if not session_id:
            return False
        with self._lock:
            return self._store.pop(session_id, None) is not None

    def list_sessions(self) -> list[str]:
        """Return a list of all active session IDs."""
        with self._lock:
            return list(self._store.keys())
