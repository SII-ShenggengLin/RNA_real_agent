"""File workspace manager to avoid token explosion."""

from __future__ import annotations

import contextvars
import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

from agent_core.workspace_manager import WorkspaceManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Global WorkspaceManager instance — used by all file operations.
_GLOBAL_WM = WorkspaceManager()

# Context variable for implicit session_id propagation.
# AgentRunner sets this before executing so that tools/workflows do not
# need to thread session_id through every call site.
_SESSION_ID_CTX: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="")


def _resolve_dir(*, session_id: str = "") -> Path:
    """Return the appropriate workspace directory, optionally scoped to a session.

    Priority:
    1. Explicit *session_id* argument.
    2. Context variable set by AgentRunner.
    3. Global workspace base directory.
    """
    if session_id:
        return _GLOBAL_WM.get_session_dir(session_id)
    ctx_session_id = _SESSION_ID_CTX.get()
    if ctx_session_id:
        return _GLOBAL_WM.get_session_dir(ctx_session_id)
    return _GLOBAL_WM.base_dir


def _resolve_session_id(session_id: str) -> str:
    if not session_id:
        return _SESSION_ID_CTX.get()
    return session_id


def current_session_id() -> str:
    """The context-propagated session id (empty string outside a run)."""
    return _SESSION_ID_CTX.get()


def _workspace_path(prefix: str, suffix: str, *, session_id: str = "") -> Path:
    """Return an unused absolute Path under the resolved workspace directory."""
    dir_path = _resolve_dir(session_id=_resolve_session_id(session_id))
    dir_path.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid4().hex[:10]}{suffix}"
    return dir_path / filename


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def save_sequence(content: str, prefix: str = "seq", *, session_id: str = "") -> str:
    """Save sequence content into workspace and return relative filepath."""
    absolute_path = _workspace_path(prefix, ".fasta", session_id=session_id)
    absolute_path.write_text(content, encoding="utf-8")
    return _rel(absolute_path)


def save_text_file(content: str, prefix: str, suffix: str, *, session_id: str = "") -> str:
    """Save an arbitrary text artifact into workspace and return relative filepath."""
    absolute_path = _workspace_path(prefix, suffix, session_id=session_id)
    absolute_path.write_text(content, encoding="utf-8")
    return _rel(absolute_path)


def copy_file_to_workspace(
    source_path: str,
    prefix: str,
    suffix: Optional[str] = None,
    *,
    session_id: str = "",
) -> str:
    """Copy an existing file into workspace and return the relative filepath."""
    source = Path(source_path)
    absolute_path = _workspace_path(prefix, suffix or source.suffix, session_id=session_id)
    shutil.copy2(source, absolute_path)
    return _rel(absolute_path)


def resolve_project_path(filepath: str) -> str:
    """Resolve a workspace-relative path to absolute, or pass through absolute paths."""
    path_obj = Path(filepath.strip())
    if path_obj.is_absolute():
        return str(path_obj.resolve())
    return str((PROJECT_ROOT / filepath).resolve())


def read_sequence(filepath: str) -> str:
    """Read sequence content from workspace or absolute path."""
    path_obj = Path(filepath)
    if not path_obj.is_absolute():
        path_obj = PROJECT_ROOT / filepath
    return path_obj.read_text(encoding="utf-8")
