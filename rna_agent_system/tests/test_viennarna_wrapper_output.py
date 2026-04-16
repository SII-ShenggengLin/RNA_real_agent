from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from agent_core.tools import predict_rna_secondary_structure


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_predict_rna_secondary_structure_returns_dict(tmp_path):
    seq_file = tmp_path / "seq.fasta"
    seq_file.write_text("AUGCUA", encoding="utf-8")

    payload = {"sequence": "AUGCUA", "structure": "......", "mfe": -1.2, "backend": "RNAfold-cli"}

    with patch("agent_core.tools.requests.post", return_value=_FakeResponse(payload)):
        out = predict_rna_secondary_structure.invoke({"filepath": str(seq_file), "service_url": "http://x/fold"})

    assert isinstance(out, dict)
    assert out["input_filepath"] == str(seq_file)
    assert out["structure"] == "......"
    assert out["mfe_kcal_per_mol"] == -1.2

