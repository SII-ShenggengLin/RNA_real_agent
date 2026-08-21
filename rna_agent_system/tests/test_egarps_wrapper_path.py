"""EGARPS wrapper path-resolution regression (2026-08-21 Layer-1 fresh-data audit).

The EGARPS+ service checks ``Path(pdb_path).exists()`` against its *own*
working directory, so a workspace-relative ``filepath`` posted verbatim
404'd ("PDB file not found").  The wrapper now resolves workspace-relative
paths to absolute before the request, matching the blast / GC wrappers.

These tests pin the request-side behavior with a stubbed ``requests.post``
(no service needed) and go through Layer 1 (``Capability.invoke``) so the
fix is exercised on the exact path workflows use.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.capabilities.base import build_default_capability_registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _registry():
    return build_default_capability_registry(ToolExecutor(build_default_tool_registry()))


def test_relative_workspace_path_is_resolved_before_post(tmp_path):
    pdb = tmp_path / "complex.pdb"
    pdb.write_text("HEADER stub\n")
    rel = str(pdb.relative_to(PROJECT_ROOT)) if PROJECT_ROOT in pdb.parents else None
    if rel is None:  # tmp_path outside the project: simulate a workspace-relative path
        rel = "workspace/does_not_need_to_exist_for_the_stub.fa"

    sent: dict = {}

    def fake_post(url, json=None, timeout=None):
        sent.update(json or {})
        return _FakeResponse({"complex_id": "x", "native_probability": 1.0,
                              "academic": False, "model": "EGARPS+", "pdb_path": "stub"})

    with patch("agent_core.tools.requests.post", side_effect=fake_post):
        res = _registry().get("score_rna_protein_complex_with_egarps").invoke(
            {"filepath": rel}, state={}
        )

    assert res.success, res.error
    posted = Path(sent["pdb_path"])
    assert posted.is_absolute()
    assert "pdb_path" in sent and sent["academic"] is False
    assert res.output["input_filepath"] == rel  # original argument echoed back


def test_absolute_path_passes_through(tmp_path):
    pdb = tmp_path / "abs_complex.pdb"
    pdb.write_text("HEADER stub\n")
    sent: dict = {}

    def fake_post(url, json=None, timeout=None):
        sent.update(json or {})
        return _FakeResponse({"complex_id": "y", "native_probability": 0.5,
                              "academic": True, "model": "EGARPS+", "pdb_path": "stub"})

    with patch("agent_core.tools.requests.post", side_effect=fake_post):
        res = _registry().get("score_rna_protein_complex_with_egarps").invoke(
            {"filepath": str(pdb), "academic": True}, state={}
        )

    assert res.success, res.error
    assert Path(sent["pdb_path"]).is_absolute()
    assert str(pdb) == sent["pdb_path"]
    assert res.output["native_probability"] == 0.5
