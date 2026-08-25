from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from agent_core.file_manager import PROJECT_ROOT, _GLOBAL_WM
from agent_core.tools import compute_rna_sequence_u_content


@pytest.fixture()
def u_sample_filepath():
    ws = _GLOBAL_WM.base_dir
    name = "test_u_langchain_demo.fasta"
    (ws / name).write_text(">demo\nAUGCAUAUGCAU\n", encoding="utf-8")
    return str((ws / name).relative_to(PROJECT_ROOT))


def test_compute_rna_sequence_u_content_returns_dict(u_sample_filepath):
    fake_body = {
        "input_filepath": u_sample_filepath,
        "resolved_filepath": "/x/test.fasta",
        "sequence_length": 12,
        "u_count": 3,
        "u_fraction": 0.25,
        "model": "rna-u-content",
    }

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return fake_body

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(response=self)

    with patch(
        "agent_core.tools.requests.post",
        return_value=_Resp(),
    ):
        out = compute_rna_sequence_u_content.invoke(
            {"filepath": u_sample_filepath, "service_url": "http://test/u-content"}
        )

    assert isinstance(out, dict)
    assert out["u_fraction"] == 0.25
    assert out["sequence_length"] == 12
    assert out["u_count"] == 3
    assert out["model"] == "rna-u-content"


def test_compute_rna_sequence_u_content_timeout_passed_through(u_sample_filepath):
    captured = {}

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {
                "sequence_length": 12,
                "u_count": 3,
                "u_fraction": 0.25,
                "model": "rna-u-content",
            }

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(response=self)

    def _capture_post(url, json, timeout):
        captured["timeout"] = timeout
        return _Resp()

    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        compute_rna_sequence_u_content.invoke(
            {
                "filepath": u_sample_filepath,
                "service_url": "http://test/u-content",
                "timeout_seconds": 45.0,
            }
        )

    assert captured.get("timeout") == 45.0


def test_compute_rna_sequence_u_content_http_error_raises(u_sample_filepath):
    class _Resp:
        ok = False
        status_code = 500
        text = "server error"

        def json(self):
            return {"detail": "boom"}

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(response=self)

    with patch("agent_core.tools.requests.post", return_value=_Resp()):
        with pytest.raises(ValueError, match="RNA sequence metrics"):
            compute_rna_sequence_u_content.invoke(
                {"filepath": u_sample_filepath, "service_url": "http://test/u-content"}
            )
