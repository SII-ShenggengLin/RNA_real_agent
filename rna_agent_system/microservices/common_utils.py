"""Shared utilities for RNA agent microservices.

Eliminates copy-paste duplication of path-resolution and log-parsing helpers
across service modules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException


class PathResolver:
    """Resolve repo-relative or absolute paths consistently across microservices."""

    def __init__(self, project_root: Path, repo_root: Path) -> None:
        self.project_root = project_root
        self.repo_root = repo_root

    def resolve(self, path_str: str) -> Path:
        """Return an absolute Path, trying project_root and repo_root lookups."""
        path = Path(path_str)
        if path.is_absolute():
            return path

        candidate_paths = [
            self.project_root / path,
            self.repo_root / path,
        ]

        path_text = str(path)
        if path_text.startswith("rna_agent_system/"):
            candidate_paths.insert(0, self.repo_root / path)
        elif path_text.startswith(
            ("workspace/", "external_repos/", "microservices/", "agent_core/", "docs/")
        ):
            candidate_paths.insert(0, self.project_root / path)

        for candidate in candidate_paths:
            if candidate.exists():
                return candidate

        return candidate_paths[0]

    def require_existing(self, path_str: str, label: str) -> Path:
        """Resolve a path and raise HTTPException(400) if it does not exist."""
        resolved = self.resolve(path_str)
        if not resolved.exists():
            raise HTTPException(status_code=400, detail=f"{label} does not exist: {resolved}")
        return resolved


def _is_lfs_pointer(path: Path) -> bool:
    """Check whether a file is a Git LFS pointer instead of real content."""
    if not path.exists():
        return False
    try:
        prefix = path.read_bytes()[:64]
    except OSError:
        return False
    return prefix.startswith(b"version https://git-lfs.github.com/spec/v1")


def parse_recovery_rate(stdout: str) -> Optional[float]:
    """Extract a recovery rate float from subprocess stdout.

    Tries multiple regex patterns to accommodate both RhoDesign and RiboDiffusion output formats.
    """
    for pattern in (
        r"recovery_rate\s+([0-9]*\.?[0-9]+)",
        r"recovery rate:\s*([0-9]*\.?[0-9]+)",
    ):
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None
