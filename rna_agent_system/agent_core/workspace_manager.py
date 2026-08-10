"""Layer 5 — WorkspaceManager: per-session file isolation."""

from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class WorkspaceManager:
    """Manage per-session workspace directories.

    Each session receives its own sub-directory under
    ``{base_dir}/sessions/{session_id}/``.
    """

    def __init__(self, base_dir: str = "workspace") -> None:
        self.base_dir = PROJECT_ROOT / base_dir

    def get_session_dir(self, session_id: str) -> Path:
        """Return the absolute ``Path`` for *session_id*, creating it if necessary."""
        session_dir = self.base_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def add_file(self, session_id: str, file_path: str) -> str:
        """Copy an existing file into the session workspace.

        Returns
        -------
        str
            Project-relative path when the workspace lives under the project
            root, otherwise an absolute path.
        """
        source = Path(file_path)
        session_dir = self.get_session_dir(session_id)
        target = session_dir / source.name
        shutil.copy2(source, target)
        if target.is_relative_to(PROJECT_ROOT):
            rel = target.relative_to(PROJECT_ROOT)
            return str(rel).replace("\\", "/")
        return str(target).replace("\\", "/")

    def list_files(self, session_id: str) -> list[str]:
        """List all files in the session workspace as project-relative paths."""
        session_dir = self.get_session_dir(session_id)
        if not session_dir.exists():
            return []
        paths: list[str] = []
        for p in session_dir.iterdir():
            if not p.is_file():
                continue
            if p.is_relative_to(PROJECT_ROOT):
                paths.append(str(p.relative_to(PROJECT_ROOT)).replace("\\", "/"))
            else:
                paths.append(str(p).replace("\\", "/"))
        return paths

    def delete_session(self, session_id: str) -> bool:
        """Recursively remove the workspace directory for *session_id*.

        Returns
        -------
        bool
            ``True`` if the directory existed and was removed, ``False`` otherwise.
        """
        session_dir = self.base_dir / "sessions" / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            return True
        return False

    def copy_to_session(self, session_id: str, source_path: str) -> str:
        """Alias for ``add_file``."""
        return self.add_file(session_id, source_path)
