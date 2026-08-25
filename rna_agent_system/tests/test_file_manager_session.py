"""Session isolation tests for file_manager.py.

Path prefixes are asserted semantically (``sessions/<sid>/``) so the tests
hold under any configured workspace base, including the suite-wide scratch
redirect installed by ``conftest._isolated_workspace``.
"""

from __future__ import annotations

from pathlib import Path

from agent_core.file_manager import (
    copy_file_to_workspace,
    resolve_project_path,
    save_sequence,
    save_text_file,
)


def test_save_sequence_without_session_uses_workspace_root() -> None:
    fp = save_sequence("AUGCGCUAGC", prefix="test")
    assert fp.startswith(("workspace/", "/"))
    assert "sessions/" not in fp


def test_save_sequence_with_session_uses_session_subdir() -> None:
    sid = "test-session-fm"
    fp = save_sequence("AUGCGCUAGC", prefix="test", session_id=sid)
    assert f"sessions/{sid}/" in fp
    assert Path(resolve_project_path(fp)).exists()


def test_save_text_file_with_session() -> None:
    sid = "test-session-txt"
    fp = save_text_file("hello", prefix="note", suffix=".txt", session_id=sid)
    assert f"sessions/{sid}/" in fp
    assert fp.endswith(".txt")


def test_copy_file_to_workspace_with_session(tmp_path) -> None:
    sid = "test-session-cp"
    source = tmp_path / "tmp_src.txt"
    source.write_text("copy me")
    fp = copy_file_to_workspace(str(source), prefix="copied", session_id=sid)
    assert f"sessions/{sid}/" in fp
