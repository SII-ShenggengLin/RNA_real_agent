"""Tests for the junction-aware LinearDesign tool (2026-08, additive).

Covers, without starting any real service:
- tools.py input schema validation (negative junction_weight, zero window)
- wrapper HTTP pass-through / timeout rule / error paths (mocked requests.post)
- microservice flank normalization & junction-side slicing (5' tail / 3' head)
- junction_window_pair_count counting on hand-computed dot-brackets
- endpoint-level 422 validation and pair_count / mfe_thermo semantics
  (FastAPI TestClient with the binary runner monkeypatched out)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from pydantic import ValidationError

from agent_core.file_manager import PROJECT_ROOT
from agent_core.tools import (
    LinearDesignCdsJunctionAwareInput,
    design_mrna_cds_junction_aware_with_lineardesign,
)

# Allow importing microservices/lineardesign_service (same pattern as
# tests/test_rhodesign_interface.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "microservices"))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from lineardesign_service.main import (  # noqa: E402
    DEFAULT_FLANK_NT,
    _count_junction_window_pairs,
    _normalize_junction_flank,
    _slice_junction_flank,
    app,
)


@pytest.fixture()
def protein_filepath():
    ws = PROJECT_ROOT / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    name = "test_junction_aware_protein.fasta"
    (ws / name).write_text("MKKKKKKKKK\n", encoding="utf-8")
    return f"workspace/{name}"


def _fake_junction_response_body() -> dict:
    full = "GCG" + "AUGAAG" + "CCG"  # flank5 + CDS + flank3
    return {
        "generated_sequence": full,
        "structure": "((....))....",
        "mfe": -12.5,
        "cai_score": 0.876,
        "lambda_value": 0.0,
        "codon_usage_path": "/x/codon.csv",
        "model": "LinearDesign",
        "raw_output": "raw",
        "stderr": "",
        "cds_sequence": "AUGAAG",
        "cds_cai": 0.876,
        "full_construct_sequence": full,
        "utr5_flank": "GCG",
        "utr3_flank": "CCG",
        "junction_weight": 1.0,
        "junction_window_nt": 20,
        "flank_nt": 21,
        "junction_window_pair_count": 2,
        "mfe_thermo": -14.5,
    }


class _Resp:
    def __init__(self, body, ok=True, status_code=200):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.text = "" if ok else "error"

    def json(self):
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(response=self)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Input schema validation
# ─────────────────────────────────────────────────────────────────────────────


def test_input_schema_defaults():
    schema = LinearDesignCdsJunctionAwareInput(filepath="workspace/x.fasta")
    assert schema.junction_weight == 0.0
    assert schema.junction_window_nt == 20
    assert schema.flank_nt == DEFAULT_FLANK_NT == 21
    assert schema.service_url.endswith("/generate/cds_junction_aware")
    assert schema.utr5_flank is None and schema.utr3_flank is None


def test_input_schema_rejects_negative_junction_weight():
    with pytest.raises(ValidationError):
        LinearDesignCdsJunctionAwareInput(filepath="workspace/x.fasta", junction_weight=-0.5)


def test_input_schema_rejects_zero_window():
    with pytest.raises(ValidationError):
        LinearDesignCdsJunctionAwareInput(filepath="workspace/x.fasta", junction_window_nt=0)


def test_input_schema_rejects_negative_lambda():
    with pytest.raises(ValidationError):
        LinearDesignCdsJunctionAwareInput(filepath="workspace/x.fasta", lambda_value=-1.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Wrapper pass-through (mocked HTTP)
# ─────────────────────────────────────────────────────────────────────────────


def test_wrapper_passes_through_response_fields(protein_filepath):
    captured = {}

    def _capture_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp(_fake_junction_response_body())

    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        out = design_mrna_cds_junction_aware_with_lineardesign.invoke(
            {
                "filepath": protein_filepath,
                "service_url": "http://test/junction",
                "utr5_flank": "GCGGCGGCG",
                "utr3_flank": "CCGCCGCCG",
                "junction_weight": 1.0,
            }
        )

    # Request wiring: flank/weight fields forwarded, protein read from file.
    assert captured["url"] == "http://test/junction"
    assert captured["json"]["protein_sequence"] == "MKKKKKKKKK"
    assert captured["json"]["utr5_flank"] == "GCGGCGGCG"
    assert captured["json"]["utr3_flank"] == "CCGCCGCCG"
    assert captured["json"]["junction_weight"] == 1.0
    assert captured["json"]["junction_window_nt"] == 20
    assert captured["json"]["flank_nt"] == 21

    # Response pass-through.
    assert out["input_filepath"] == protein_filepath
    assert out["generated_sequence"] == "GCGAUGAAGCCG"
    assert out["full_construct_sequence"] == "GCGAUGAAGCCG"
    assert out["cds_sequence"] == "AUGAAG"
    assert out["cds_cai"] == pytest.approx(0.876)
    assert out["cai_score"] == pytest.approx(0.876)
    assert out["mfe"] == pytest.approx(-12.5)
    assert out["mfe_thermo"] == pytest.approx(-14.5)
    assert out["junction_window_pair_count"] == 2
    assert out["junction_weight"] == pytest.approx(1.0)
    assert out["junction_window_nt"] == 20
    assert out["flank_nt"] == 21
    assert out["utr5_flank"] == "GCG"
    assert out["utr3_flank"] == "CCG"
    assert out["model"] == "LinearDesign"

    # Full construct saved into workspace.
    saved = (PROJECT_ROOT / out["output_filepath"]).read_text(encoding="utf-8")
    assert saved == "GCGAUGAAGCCG"


def test_wrapper_protein_sequence_overrides_file(protein_filepath):
    captured = {}

    def _capture_post(url, json, timeout):
        captured["json"] = json
        return _Resp(_fake_junction_response_body())

    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        design_mrna_cds_junction_aware_with_lineardesign.invoke(
            {
                "filepath": protein_filepath,
                "protein_sequence": "MGG*",
                "service_url": "http://test/junction",
            }
        )
    assert captured["json"]["protein_sequence"] == "MGG*"


def test_wrapper_timeout_uses_full_construct_nt(protein_filepath):
    captured = {}

    def _capture_post(url, json, timeout):
        captured["timeout"] = timeout
        return _Resp(_fake_junction_response_body())

    long_protein = "M" + "K" * 499  # 500 aa -> 1500 nt CDS
    with patch("agent_core.tools.requests.post", side_effect=_capture_post):
        design_mrna_cds_junction_aware_with_lineardesign.invoke(
            {
                "filepath": protein_filepath,
                "protein_sequence": long_protein,
                "service_url": "http://test/junction",
                "utr5_flank": "G" * 21,
                "utr3_flank": "C" * 21,
            }
        )
    expected = max(300, int((1500 + 42) * 0.8) + 180)
    assert captured["timeout"] == expected


def test_wrapper_http_500_raises_value_error(protein_filepath):
    with patch(
        "agent_core.tools.requests.post",
        return_value=_Resp({"detail": "boom"}, ok=False, status_code=500),
    ):
        with pytest.raises(ValueError, match="LinearDesign junction-aware"):
            design_mrna_cds_junction_aware_with_lineardesign.invoke(
                {"filepath": protein_filepath, "service_url": "http://test/junction"}
            )


def test_wrapper_http_422_raises_value_error(protein_filepath):
    with patch(
        "agent_core.tools.requests.post",
        return_value=_Resp({"detail": "Invalid utr5_flank"}, ok=False, status_code=422),
    ):
        with pytest.raises(ValueError, match="LinearDesign junction-aware"):
            design_mrna_cds_junction_aware_with_lineardesign.invoke(
                {
                    "filepath": protein_filepath,
                    "service_url": "http://test/junction",
                    "utr5_flank": "GCX",
                }
            )


def test_wrapper_missing_generated_sequence_raises(protein_filepath):
    body = _fake_junction_response_body()
    del body["generated_sequence"]
    with patch("agent_core.tools.requests.post", return_value=_Resp(body)):
        with pytest.raises(ValueError, match="generated_sequence"):
            design_mrna_cds_junction_aware_with_lineardesign.invoke(
                {"filepath": protein_filepath, "service_url": "http://test/junction"}
            )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Service-side flank normalization & slicing helpers
# ─────────────────────────────────────────────────────────────────────────────


def test_normalize_flank_uppercases_and_converts_t_to_u():
    assert _normalize_junction_flank("gcgt", "utr5_flank") == "GCGU"
    assert _normalize_junction_flank("", "utr5_flank") == ""
    assert _normalize_junction_flank(None, "utr5_flank") == ""


def test_normalize_flank_rejects_invalid_chars_with_422():
    with pytest.raises(HTTPException) as exc_info:
        _normalize_junction_flank("GCGX", "utr5_flank")
    assert exc_info.value.status_code == 422


def test_slice_flank_junction_side_direction():
    flank5 = "AAAAAAAAAACCCCCCCCCC" + "UUU"  # 23 nt
    flank3 = "GGG" + "AAAAAAAAAACCCCCCCCCC"
    # 5' flank keeps the LAST flank_nt nt (junction side).
    assert _slice_junction_flank(flank5, 9, is_5prime=True) == "CCCCCCUUU"
    # 3' flank keeps the FIRST flank_nt nt (junction side).
    assert _slice_junction_flank(flank3, 9, is_5prime=False) == "GGGAAAAAA"


def test_slice_flank_shorter_than_flank_nt_floors_to_multiple_of_3():
    # 8 nt usable -> take 6; 5' takes the tail, 3' takes the head.
    assert _slice_junction_flank("AACCGGUU", 21, is_5prime=True) == "CCGGUU"
    assert _slice_junction_flank("AACCGGUU", 21, is_5prime=False) == "AACCGG"


def test_slice_flank_rejects_under_3_nt_with_422():
    with pytest.raises(HTTPException) as exc_info:
        _slice_junction_flank("AU", 21, is_5prime=True)
    assert exc_info.value.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 4. junction_window_pair_count counting (hand-computed dot-brackets)
# ─────────────────────────────────────────────────────────────────────────────


def test_pair_count_hand_computed():
    # L5=6, Lcds=12, L3=6, total=24, w=4 -> W1=[2,10), W2=[14,22).
    struct = ["."] * 24
    for pos, ch in {0: "(", 3: "(", 8: "(", 11: "(", 12: ")", 15: ")", 20: ")", 23: ")"}.items():
        struct[pos] = ch
    structure = "".join(struct)
    # pairs: (0,23) out/out -> no; (3,20) W1/W2 -> yes; (8,15) W1/W2 -> yes; (11,12) out/out -> no
    assert _count_junction_window_pairs(structure, l5=6, lcds=12, window_nt=4) == 2


def test_pair_count_zero_flank_windows():
    # L5=0, Lcds=10, w=3 -> W1=[0,3), W2=[7,10) (clipped).
    assert _count_junction_window_pairs("((........))", l5=0, lcds=10, window_nt=3) == 2
    # No pairs at all.
    assert _count_junction_window_pairs("..........", l5=0, lcds=10, window_nt=3) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Endpoint-level validation & derived-field semantics (TestClient, runner mocked)
# ─────────────────────────────────────────────────────────────────────────────


def test_endpoint_rejects_bad_flank_chars_422():
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={"protein_sequence": "MKK", "utr5_flank": "GCGX"},
    )
    assert resp.status_code == 422


def test_endpoint_rejects_short_flank_422():
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={"protein_sequence": "MKK", "utr5_flank": "AU"},
    )
    assert resp.status_code == 422


def test_endpoint_rejects_bad_flank_nt_422():
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={"protein_sequence": "MKK", "utr5_flank": "GCGGCG", "flank_nt": 22},
    )
    assert resp.status_code == 422


def test_endpoint_rejects_negative_weight_422():
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={"protein_sequence": "MKK", "junction_weight": -1.0},
    )
    assert resp.status_code == 422


def test_endpoint_junction_mode_derived_fields(monkeypatch):
    def _fake_run(**kwargs):
        # 21nt flank5 + 30nt CDS + 21nt flank3 = 72 nt construct.
        struct = ["("] * 5 + ["."] * 62 + [")"] * 5  # pairs (0,71)..(4,67)
        raw = (
            "mRNA sequence:  " + "G" * 21 + "A" * 30 + "C" * 21 + "\n"
            "mRNA structure: " + "".join(struct) + "\n"
            "mRNA folding free energy: -30.00 kcal/mol; mRNA CAI: 0.900\n"
            "CDS sequence: " + "A" * 30 + "\n"
            "CDS CAI: 0.900\n"
        )
        return {
            "generated_sequence": "G" * 21 + "A" * 30 + "C" * 21,
            "structure": "".join(struct),
            "mfe": -30.0,
            "cai_score": 0.9,
            "cds_sequence": "A" * 30,
            "cds_cai": 0.9,
            "raw_output": raw,
            "stderr": "",
        }

    monkeypatch.setattr(
        "lineardesign_service.main._run_lineardesign_junction_aware_once", _fake_run
    )
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={
            "protein_sequence": "M" + "K" * 9,
            "utr5_flank": "G" * 21,
            "utr3_flank": "C" * 21,
            "junction_weight": 2.0,
            "junction_window_nt": 20,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # W1 = [max(0,21-20), 21+20) = [1,41); W2 = [51-20, 51+20) = [31,71) (total 72).
    # Pairs: (4,67),(3,68),(2,69),(1,70) have left endpoint in W1 -> counted;
    # (0,71): 0 not in W1 and 71 not in W2 (half-open) -> not counted.
    assert body["junction_window_pair_count"] == 4
    # mfe is the objective value; mfe_thermo = mfe - w * count.
    assert body["mfe"] == pytest.approx(-30.0)
    assert body["mfe_thermo"] == pytest.approx(-30.0 - 2.0 * 4)
    assert body["cds_sequence"] == "A" * 30
    assert body["cds_cai"] == pytest.approx(0.9)
    assert body["full_construct_sequence"] == body["generated_sequence"]
    assert body["utr5_flank"] == "G" * 21
    assert body["utr3_flank"] == "C" * 21
    assert body["flank_nt"] == 21


def test_endpoint_zero_flank_degenerates_to_legacy(monkeypatch):
    captured = {}

    def _fake_legacy_run(**kwargs):
        captured.update(kwargs)
        return {
            "generated_sequence": "AUGAAG",
            "structure": "......",
            "mfe": -1.5,
            "cai_score": 0.8,
            "raw_output": "raw",
            "stderr": "",
        }

    def _unexpected_junction_run(**kwargs):
        raise AssertionError("junction-aware runner must not be called without flanks")

    monkeypatch.setattr("lineardesign_service.main._run_lineardesign_once", _fake_legacy_run)
    monkeypatch.setattr(
        "lineardesign_service.main._run_lineardesign_junction_aware_once",
        _unexpected_junction_run,
    )
    client = TestClient(app)
    resp = client.post(
        "/generate/cds_junction_aware",
        json={"protein_sequence": "MK", "junction_weight": 3.0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Legacy path: penalty not applied -> mfe_thermo == mfe even with junction_weight > 0.
    assert body["mfe_thermo"] == pytest.approx(body["mfe"])
    assert body["cds_sequence"] == body["generated_sequence"]
    assert body["cds_cai"] == pytest.approx(body["cai_score"])
    assert body["utr5_flank"] == "" and body["utr3_flank"] == ""
