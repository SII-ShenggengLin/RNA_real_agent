from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from agent_core.file_manager import PROJECT_ROOT
from agent_core.tools import compute_rna_sequence_gc_content


@pytest.fixture()
def gc_sample_filepath():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_gc_langchain_demo.fasta"
    (ws / name).write_text(">demo\nAUGCAUAUGCAU\n", encoding="utf-8")
    return f"workspace/{name}"


def test_compute_rna_sequence_gc_content_returns_dict(gc_sample_filepath):
    fake_body = {
        "input_filepath": gc_sample_filepath,
        "resolved_filepath": "/x/test.fasta",
        "sequence_length": 12,
        "g_count": 3,
        "c_count": 3,
        "gc_count": 6,
        "gc_content": 0.5,
        "model": "rna-sequence-metrics-gc",
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
        out = compute_rna_sequence_gc_content.invoke(
            {"filepath": gc_sample_filepath, "service_url": "http://test/gc-content"}
        )

    assert isinstance(out, dict)
    assert out["gc_content"] == 0.5
    assert out["sequence_length"] == 12
    assert out["g_count"] == 3
    assert out["c_count"] == 3
    assert out["gc_count"] == 6
    assert out["model"] == "rna-sequence-metrics-gc"


def test_compute_rna_sequence_gc_content_timeout_passed_through(gc_sample_filepath):
    captured = {}

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {
                "sequence_length": 12,
                "g_count": 3,
                "c_count": 3,
                "gc_count": 6,
                "gc_content": 0.5,
                "model": "rna-sequence-metrics-gc",
            }

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(response=self)

    def _capture_post(url, json, timeout):
        captured["timeout"] = timeout
        return _Resp()

    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        compute_rna_sequence_gc_content.invoke(
            {
                "filepath": gc_sample_filepath,
                "service_url": "http://test/gc-content",
                "timeout_seconds": 45.0,
            }
        )

    assert captured.get("timeout") == 45.0


def test_compute_rna_sequence_gc_content_http_error_raises(gc_sample_filepath):
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
            compute_rna_sequence_gc_content.invoke(
                {"filepath": gc_sample_filepath, "service_url": "http://test/gc-content"}
            )
