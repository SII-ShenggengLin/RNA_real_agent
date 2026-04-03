"""File workspace manager to avoid token explosion."""

from __future__ import annotations

from pathlib import Path
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


def read_sequence(filepath: str) -> str:
    """Read sequence content from workspace or absolute path."""
    path_obj = Path(filepath)
    if not path_obj.is_absolute():
        path_obj = PROJECT_ROOT / filepath
    return path_obj.read_text(encoding="utf-8")
