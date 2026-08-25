"""Layer-5 fresh-data audit regressions (2026-08-22).

Defects found by ``workspace/layer5_fresh_audit_2026-08-22/`` (live audit on
freshly fetched TTR NM_000371 / IFNA2 NM_000605 data) and fixed the same day:

1. ``WorkspaceManager.delete_session("")`` removed the **whole** ``sessions/``
   tree: ``Path(base) / "sessions" / ""`` is a no-op join, so the empty id
   aliased the sessions root and ``rmtree`` deleted every session workspace
   (returning ``True`` as if one session had gone).
2. Session ids were joined into filesystem paths unvalidated, so ids with
   path separators or ``.``/``..`` components escaped the per-session
   sandbox (``get_session_dir("../x")`` created directories outside
   ``sessions/``; reachable from the client-controlled workflow-API
   ``task_id``).
3. ``list_files`` called ``get_session_dir`` and therefore **created** the
   session directory as a side effect of a pure listing (its own
   ``exists()`` guard was dead code).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_core.workspace_manager import WorkspaceManager


@pytest.fixture
def wm(tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(base_dir=str(tmp_path))


def _seed_session(manager: WorkspaceManager, sid: str, payload: str = "x") -> Path:
    d = manager.get_session_dir(sid)
    (d / "data.txt").write_text(payload)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# 1. delete_session("") must not destroy the sessions tree

def test_delete_empty_session_id_is_noop_and_siblings_survive(wm: WorkspaceManager) -> None:
    _seed_session(wm, "alpha")
    _seed_session(wm, "beta")

    assert wm.delete_session("") is False

    sessions_root = wm.base_dir / "sessions"
    assert sessions_root.exists()
    assert (sessions_root / "alpha" / "data.txt").exists()
    assert (sessions_root / "beta" / "data.txt").exists()


def test_delete_whitespace_session_id_is_noop(wm: WorkspaceManager) -> None:
    _seed_session(wm, "alpha")
    assert wm.delete_session("   ") is False
    assert (wm.base_dir / "sessions" / "alpha" / "data.txt").exists()


# ─────────────────────────────────────────────────────────────────────────────
# 2. path-escaping session ids are rejected before any filesystem effect

@pytest.mark.parametrize("bad_id", ["../escaped", "..", ".", "a/b", "a\\b", "/abs/abs"])
def test_get_session_dir_rejects_path_escaping_ids(
    wm: WorkspaceManager, bad_id: str
) -> None:
    with pytest.raises(ValueError):
        wm.get_session_dir(bad_id)
    assert not (wm.base_dir / "escaped").exists()
    sessions = wm.base_dir / "sessions"
    assert not sessions.exists() or list(sessions.iterdir()) == []


def test_get_session_dir_rejects_empty_id(wm: WorkspaceManager) -> None:
    with pytest.raises(ValueError):
        wm.get_session_dir("")


def test_delete_session_with_escaping_id_is_noop(wm: WorkspaceManager) -> None:
    _seed_session(wm, "alpha")
    assert wm.delete_session("../alpha") is False
    assert (wm.base_dir / "sessions" / "alpha" / "data.txt").exists()
    assert wm.delete_session("a/b") is False


def test_add_file_with_escaping_id_raises_and_copies_nothing(
    wm: WorkspaceManager, tmp_path: Path
) -> None:
    src = tmp_path / "src.fasta"
    src.write_text(">x\nAUGCAUGCAUGC\n")
    with pytest.raises(ValueError):
        wm.add_file("../escape", str(src))
    assert not (wm.base_dir / "escape").exists()


def test_list_files_rejects_empty_id(wm: WorkspaceManager) -> None:
    with pytest.raises(ValueError):
        wm.list_files("")


# ─────────────────────────────────────────────────────────────────────────────
# 3. list_files is a pure read

def test_list_files_does_not_create_the_session_directory(
    wm: WorkspaceManager
) -> None:
    assert wm.list_files("ghost-session") == []
    assert not (wm.base_dir / "sessions" / "ghost-session").exists()


# ─────────────────────────────────────────────────────────────────────────────
# legitimate ids keep working end to end

def test_valid_session_round_trip(wm: WorkspaceManager, tmp_path: Path) -> None:
    src = tmp_path / "seq.fasta"
    src.write_text(">ttr_cds\nATGGCTTCC\n")

    d = wm.get_session_dir("pa020_20260716_120000")  # PA-driver id shape
    assert d.exists()

    rel = wm.add_file("pa020_20260716_120000", str(src))
    # base_dir lives outside PROJECT_ROOT, so the documented return is absolute
    assert str(d / "seq.fasta") == rel
    assert wm.list_files("pa020_20260716_120000") == [rel]

    assert wm.delete_session("pa020_20260716_120000") is True
    assert not d.exists()
    assert wm.list_files("pa020_20260716_120000") == []


def test_file_manager_session_context_scoping(tmp_path: Path) -> None:
    """file_manager writes follow the context-propagated session id."""
    from agent_core.file_manager import (
        _SESSION_ID_CTX,
        read_sequence,
        resolve_project_path,
        save_sequence,
    )

    sid = "pytest_l5_ctx_scope"
    token = _SESSION_ID_CTX.set(sid)
    try:
        rel = save_sequence("AUGCAUGCAUGCAUGCAUGC", prefix="pytest_l5")
    finally:
        _SESSION_ID_CTX.reset(token)

    assert f"sessions/{sid}/" in rel
    assert read_sequence(rel).strip() == "AUGCAUGCAUGCAUGCAUGC"

    # cleanup through the (now hardened) default manager
    assert WorkspaceManager().delete_session(sid) is True
    assert not Path(resolve_project_path(rel)).exists()
