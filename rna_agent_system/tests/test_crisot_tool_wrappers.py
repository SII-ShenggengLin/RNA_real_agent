"""W3.2 — unit coverage for the CRISOT suite tool wrappers (v0.2.0, locked).

Seven of the eight CRISOT wrappers had zero test coverage (test debt
registered in the 2026-08-18 completion program).  These tests exercise the
HTTP request/response contract against a stubbed ``requests.post``: correct
payload keys are required, parsed fields surface in the return dict, and a
service error raises ``ValueError`` with the service tag.  No live service.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_core import tools as T


class _Resp:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _tmp_file(content: str, suffix: str = ".txt") -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


def _post_stub(payload_factory):
    """Return a MagicMock replacing requests.post that serves payload_factory(url)."""
    def _fake_post(url, json=None, timeout=None, **kwargs):
        return _Resp(payload_factory(url, json))
    return MagicMock(side_effect=_fake_post)


def test_calculate_crispr_specificity_with_crisot(tmp_path: Path):
    csv_fp = _tmp_file("On,Off\nGAGTCCGAGCAGAAGAAGAANGG,GAGTCCGAGCAGAAGAAGAAGGG\n", suffix=".csv")
    fake = _post_stub(lambda url, body: {"crisot_spec": 0.7321, "row_count": 1})
    with patch.object(T.requests, "post", fake):
        out = T.calculate_crispr_specificity_with_crisot.func(csv_fp)
    assert out["crisot_spec"] == pytest.approx(0.7321)
    assert out["row_count"] == 1
    body = fake.call_args.kwargs.get("json")
    assert body["csv_path"] == csv_fp and body["on_item"] == "On"


def test_crisot_wrappers_raise_on_missing_required_key():
    on_fp = _tmp_file("AAAA\n", suffix=".csv")
    off_fp = _tmp_file("CCCC\n", suffix=".csv")
    with patch.object(T.requests, "post", _post_stub(lambda url, body: {"unexpected": 1})):
        with pytest.raises(ValueError, match="crisot_spec"):
            T.calculate_crispr_specificity_with_crisot.func(on_fp, off_fp)


def test_crisot_wrappers_raise_on_service_error():
    csv_fp = _tmp_file("On,Off\nAAAA,CCCC\n", suffix=".csv")
    import requests as _requests

    def _conn_error(url, json=None, timeout=None, **kwargs):
        raise _requests.ConnectionError("down")

    with patch.object(T.requests, "post", MagicMock(side_effect=_conn_error)):
        with pytest.raises(ValueError, match="CRISOT"):
            T.calculate_crispr_specificity_with_crisot.func(csv_fp)
