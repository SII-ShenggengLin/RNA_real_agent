"""Backward-compatible session isolation tests for file_manager.py."""

from __future__ import annotations



from agent_core.file_manager import PROJECT_ROOT, save_sequence, save_text_file, copy_file_to_workspace


def test_save_sequence_without_session_uses_root_workspace() -> None:
    fp = save_sequence("AUGCGCUAGC", prefix="test")
    assert fp.startswith("workspace/")
    assert "sessions/" not in fp
    abs_path = PROJECT_ROOT / fp
    assert abs_path.exists()
    abs_path.unlink()


def test_save_sequence_with_session_uses_session_subdir() -> None:
    sid = "test-session-fm"
    fp = save_sequence("AUGCGCUAGC", prefix="test", session_id=sid)
    assert f"sessions/{sid}/" in fp
    abs_path = PROJECT_ROOT / fp
    assert abs_path.exists()
    abs_path.unlink()
    # Clean up empty session dir
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / sid
    if session_dir.exists():
        session_dir.rmdir()


def test_save_text_file_with_session() -> None:
    sid = "test-session-txt"
    fp = save_text_file("hello", prefix="note", suffix=".txt", session_id=sid)
    assert f"sessions/{sid}/" in fp
    assert fp.endswith(".txt")
    abs_path = PROJECT_ROOT / fp
    assert abs_path.read_text() == "hello"
    abs_path.unlink()
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / sid
    if session_dir.exists():
        session_dir.rmdir()


def test_copy_file_to_workspace_with_session() -> None:
    sid = "test-session-cp"
    source = PROJECT_ROOT / "workspace" / "tmp_src.txt"
    source.write_text("copy me")
    fp = copy_file_to_workspace(str(source), prefix="copied", session_id=sid)
    assert f"sessions/{sid}/" in fp
    abs_path = PROJECT_ROOT / fp
    assert abs_path.exists()
    abs_path.unlink()
    source.unlink()
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / sid
    if session_dir.exists():
        session_dir.rmdir()
