"""File workspace manager to avoid token explosion."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_ROOT / "workspace"


def save_sequence(content: str, prefix: str = "seq") -> str:
    """Save sequence content into workspace and return relative filepath."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid4().hex[:10]}.fasta"
    absolute_path = WORKSPACE_DIR / filename
    absolute_path.write_text(content, encoding="utf-8")
    return f"workspace/{filename}"


def save_text_file(content: str, prefix: str, suffix: str) -> str:
    """Save an arbitrary text artifact into workspace and return relative filepath."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid4().hex[:10]}{suffix}"
    absolute_path = WORKSPACE_DIR / filename
    absolute_path.write_text(content, encoding="utf-8")
    return f"workspace/{filename}"


def copy_file_to_workspace(source_path: str, prefix: str, suffix: Optional[str] = None) -> str:
    """Copy an existing file into workspace and return the relative filepath."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    target_suffix = suffix or source.suffix
    filename = f"{prefix}_{uuid4().hex[:10]}{target_suffix}"
    target = WORKSPACE_DIR / filename
    shutil.copyfile(source, target)
    return f"workspace/{filename}"


def read_sequence(filepath: str) -> str:
    """Read sequence content from workspace or absolute path."""
    path_obj = Path(filepath)
    if not path_obj.is_absolute():
        path_obj = PROJECT_ROOT / filepath
    return path_obj.read_text(encoding="utf-8")
