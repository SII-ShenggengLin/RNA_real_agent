"""File workspace manager to avoid token explosion."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_ROOT / "workspace"


def _resolve_dir(*, session_id: str = "") -> Path:
    """Return the appropriate workspace directory, optionally scoped to a session."""
    if session_id:
        return WORKSPACE_DIR / "sessions" / session_id
    return WORKSPACE_DIR


def save_sequence(content: str, prefix: str = "seq", *, session_id: str = "") -> str:
    """Save sequence content into workspace and return relative filepath."""
    dir_path = _resolve_dir(session_id=session_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid4().hex[:10]}.fasta"
    absolute_path = dir_path / filename
    absolute_path.write_text(content, encoding="utf-8")
    rel = absolute_path.relative_to(PROJECT_ROOT)
    return str(rel).replace("\\", "/")


def save_text_file(content: str, prefix: str, suffix: str, *, session_id: str = "") -> str:
    """Save an arbitrary text artifact into workspace and return relative filepath."""
    dir_path = _resolve_dir(session_id=session_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid4().hex[:10]}{suffix}"
    absolute_path = dir_path / filename
    absolute_path.write_text(content, encoding="utf-8")
    rel = absolute_path.relative_to(PROJECT_ROOT)
    return str(rel).replace("\\", "/")


def copy_file_to_workspace(
    source_path: str,
    prefix: str,
    suffix: Optional[str] = None,
    *,
    session_id: str = "",
) -> str:
    """Copy an existing file into workspace and return the relative filepath."""
    dir_path = _resolve_dir(session_id=session_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    target_suffix = suffix or source.suffix
    filename = f"{prefix}_{uuid4().hex[:10]}{target_suffix}"
    target = dir_path / filename
    shutil.copyfile(source, target)
    rel = target.relative_to(PROJECT_ROOT)
    return str(rel).replace("\\", "/")


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
