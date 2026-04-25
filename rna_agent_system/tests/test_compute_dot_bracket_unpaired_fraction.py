"""Tests for compute_dot_bracket_unpaired_fraction tool and sequence_utils helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from agent_core.file_manager import PROJECT_ROOT
from agent_core.sequence_utils import (
    compute_dot_bracket_unpaired_fraction,
    extract_dot_bracket,
    validate_dot_bracket,
)
from agent_core.tools import compute_dot_bracket_unpaired_fraction as unpaired_tool


# ═══════════════════════════════════════════════════════════════════════════════
# sequence_utils helpers
# ═══════════════════════════════════════════════════════════════════════════════


def test_extract_dot_bracket_skips_headers_and_empty_lines():
    raw = ">seq1\n..((..))\n\n>seq2\n(((...)))\n"
    assert extract_dot_bracket(raw) == "..((..))(((...)))"


def test_extract_dot_bracket_plain_text():
    assert extract_dot_bracket("..((..))..") == "..((..)).."


def test_validate_dot_bracket_accepts_legal_symbols():
    validate_dot_bracket("..((..))[[{{<<>>}}]]")


def test_validate_dot_bracket_rejects_empty():
    with pytest.raises(ValueError, match="Empty"):
        validate_dot_bracket("")


def test_validate_dot_bracket_rejects_illegal_chars():
    with pytest.raises(ValueError, match="dot-bracket symbols"):
        validate_dot_bracket("..((A))..")


def test_compute_dot_bracket_unpaired_fraction_basic():
    result = compute_dot_bracket_unpaired_fraction("..((..))..")
    assert result == {
        "structure_length": 10,
        "dot_count": 6,
        "unpaired_fraction": 0.6,
    }


def test_compute_dot_bracket_unpaired_fraction_all_paired():
    result = compute_dot_bracket_unpaired_fraction("((()))")
    assert result["structure_length"] == 6
    assert result["dot_count"] == 0
    assert result["unpaired_fraction"] == 0.0


def test_compute_dot_bracket_unpaired_fraction_all_unpaired():
    result = compute_dot_bracket_unpaired_fraction("....")
    assert result["structure_length"] == 4
    assert result["dot_count"] == 4
    assert result["unpaired_fraction"] == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Tool wrapper (mocked HTTP)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def dotbracket_sample_filepath():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_unpaired_fraction_demo.ss"
    (ws / name).write_text(">demo\n..((..))..\n", encoding="utf-8")
    return f"workspace/{name}"


def test_compute_unpaired_fraction_returns_dict(dotbracket_sample_filepath):
    fake_body = {
        "input_filepath": dotbracket_sample_filepath,
        "resolved_filepath": "/x/test.ss",
        "structure_length": 10,
        "dot_count": 6,
        "unpaired_fraction": 0.6,
        "model": "rna-sequence-metrics-unpaired",
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
        out = unpaired_tool.invoke(
            {
                "filepath": dotbracket_sample_filepath,
                "service_url": "http://test/unpaired-fraction",
            }
        )

    assert isinstance(out, dict)
    assert out["unpaired_fraction"] == 0.6
    assert out["structure_length"] == 10
    assert out["dot_count"] == 6
    assert out["model"] == "rna-sequence-metrics-unpaired"


def test_compute_unpaired_fraction_timeout_passed_through(dotbracket_sample_filepath):
    captured = {}

    class _Resp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {
                "structure_length": 10,
                "dot_count": 6,
                "unpaired_fraction": 0.6,
                "model": "rna-sequence-metrics-unpaired",
            }

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(response=self)

    def _capture_post(url, json, timeout):
        captured["timeout"] = timeout
        return _Resp()

    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        unpaired_tool.invoke(
            {
                "filepath": dotbracket_sample_filepath,
                "service_url": "http://test/unpaired-fraction",
                "timeout_seconds": 45.0,
            }
        )

    assert captured.get("timeout") == 45.0


def test_compute_unpaired_fraction_http_error_raises(dotbracket_sample_filepath):
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
            unpaired_tool.invoke(
                {
                    "filepath": dotbracket_sample_filepath,
                    "service_url": "http://test/unpaired-fraction",
                }
            )
