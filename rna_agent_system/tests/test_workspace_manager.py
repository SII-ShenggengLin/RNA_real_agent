"""Unit tests for Layer 4 — WorkspaceManager."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent_core.workspace_manager import WorkspaceManager


@pytest.fixture
def temp_workspace(tmp_path: Path) -> WorkspaceManager:
    """Return a WorkspaceManager rooted in a temporary directory."""
    return WorkspaceManager(base_dir=str(tmp_path))


def test_get_session_dir_creates_directory(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid = "session-abc"
    session_dir = wm.get_session_dir(sid)
    assert session_dir.exists()
    assert session_dir.name == sid
    assert session_dir.parent.name == "sessions"


def test_add_file_copies_into_session(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid = "session-def"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        f.write(">seq\nAUGC")
        source = f.name

    rel_path = wm.add_file(sid, source)
    assert f"sessions/{sid}/" in rel_path

    abs_path = wm.base_dir.parent / rel_path  # rel_path is relative to PROJECT_ROOT
    # Because base_dir is a tmp_path under /tmp, not under PROJECT_ROOT,
    # we need to check via the session_dir directly.
    session_dir = wm.get_session_dir(sid)
    copied = session_dir / Path(source).name
    assert copied.exists()
    assert copied.read_text() == ">seq\nAUGC"


def test_list_files_returns_project_relative_paths(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid = "session-ghi"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        source = f.name

    rel_path = wm.add_file(sid, source)
    files = wm.list_files(sid)
    assert rel_path in files
    assert len(files) == 1


def test_list_files_empty_for_new_session(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    assert wm.list_files("new-empty-session") == []


def test_copy_to_session_alias(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid = "session-jkl"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f1:
        f1.write("a,b,c")
        source1 = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f2:
        f2.write("d,e,f")
        source2 = f2.name

    rel1 = wm.add_file(sid, source1)
    rel2 = wm.copy_to_session(sid, source2)
    # Both calls should land files in the same session directory.
    assert f"sessions/{sid}/" in rel1
    assert f"sessions/{sid}/" in rel2
    assert len(wm.list_files(sid)) == 2


def test_sessions_are_isolated(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid_a = "session-A"
    sid_b = "session-B"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        f.write("AUGC")
        source = f.name

    wm.add_file(sid_a, source)
    assert len(wm.list_files(sid_a)) == 1
    assert len(wm.list_files(sid_b)) == 0


def test_delete_session_removes_directory(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    sid = "session-to-delete"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("data")
        source = f.name

    wm.add_file(sid, source)
    session_dir = wm.get_session_dir(sid)
    assert session_dir.exists()
    assert wm.delete_session(sid) is True
    assert not session_dir.exists()


def test_delete_missing_session_returns_false(temp_workspace: WorkspaceManager) -> None:
    wm = temp_workspace
    assert wm.delete_session("no-such-session") is False
