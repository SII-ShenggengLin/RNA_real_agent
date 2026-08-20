"""Thermodynamic end-asymmetry extension (sirna-duplex v0.5.0, 2026-08-20).

Covers the service-side NN end evaluation (real RNAlib when importable, CLI
fallback otherwise), the additive tool-wrapper keys, the
``asymmetry_component`` mapping, and the siRNA ASF third dimension including
the older-service degrade (dimension drops pool-wide).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "microservices" / "viennarna_fold"))
import main as viennarna_main  # noqa: E402

from agent_core.tools import compute_sirna_duplex_binding_vienna  # noqa: E402
from agent_core.workflows.sirna_design import (  # noqa: E402
    SirnaDesignWorkflow,
    score_sirna_candidate,
)

try:
    import RNA  # type: ignore

    _HAS_RNALIB = True
except ImportError:
    _HAS_RNALIB = False


# ── Service-side end-thermodynamics ──────────────────────────────────────────


@pytest.mark.skipif(not (_HAS_RNALIB or viennarna_main._RNAEVAL_EXE),
                    reason="no ViennaRNA evaluation backend")
def test_miniduplex_eval_accepts_cofold_syntax() -> None:
    params = viennarna_main.ViennaModelParams()
    value = viennarna_main._eval_miniduplex_kcal("GGGG", "CCCC", params)
    assert value is not None and value < 0.0  # a paired mini-duplex is stable


@pytest.mark.skipif(not (_HAS_RNALIB or viennarna_main._RNAEVAL_EXE),
                    reason="no ViennaRNA evaluation backend")
def test_asymmetry_is_antisymmetric_under_strand_swap() -> None:
    params = viennarna_main.ViennaModelParams()
    sense = "GGGCCCUUUAAAAUUUGGGC"
    anti = "GCCCAAUUUAAAGGGCCCUU"
    _, _, asym = viennarna_main._duplex_end_asymmetry(sense, anti, params)
    _, _, asym_swapped = viennarna_main._duplex_end_asymmetry(anti, sense, params)
    assert asym is not None and asym_swapped is not None
    assert asym == pytest.approx(-asym_swapped, abs=1e-6)


@pytest.mark.skipif(not (_HAS_RNALIB or viennarna_main._RNAEVAL_EXE),
                    reason="no ViennaRNA evaluation backend")
def test_asymmetry_sign_convention_favors_less_stable_antisense_end() -> None:
    """An antisense 5' end rich in AU (weak) opposite a GC-rich (stable) sense
    5' end is the classical RISC-loading orientation: asymmetry > 0."""
    params = viennarna_main.ViennaModelParams()
    sense = "GCGCGCAAAAAUGCGCGCAAA"      # sense 5' end GC-rich (stable)
    anti = "UUUGCGCGCAUUUUUGCGCGC"       # antisense 5' end AU-rich (weak)
    dg_s, dg_a, asym = viennarna_main._duplex_end_asymmetry(sense, anti, params)
    assert dg_s is not None and dg_a is not None
    assert dg_a > dg_s          # antisense 5' end less stable
    assert asym == pytest.approx(dg_a - dg_s, abs=1e-6)
    assert asym > 0.0


def test_asymmetry_short_strands_return_none() -> None:
    params = viennarna_main.ViennaModelParams()
    assert viennarna_main._duplex_end_asymmetry("AUG", "CAU", params) == (None, None, None)


# ── Tool wrapper (additive keys, older-service tolerant) ─────────────────────


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def _duplex_payload(**extra) -> dict:
    payload = {
        "sense": "GGGG",
        "antisense": "CCCC",
        "cofold_sequence": "GGGG&CCCC",
        "structure": "((((&))))",
        "mfe": -5.3,
        "backend": "RNAlib",
    }
    payload.update(extra)
    return payload


def test_wrapper_returns_asymmetry_keys(tmp_path) -> None:
    seq_file = tmp_path / "duplex.fasta"
    seq_file.write_text(">sense\nGGGG\n>antisense\nCCCC\n", encoding="utf-8")
    payload = _duplex_payload(
        dg_sense_5p_end_kcal_per_mol=-4.1,
        dg_antisense_5p_end_kcal_per_mol=-3.2,
        asymmetry_kcal_per_mol=0.9,
        asymmetry_convention="asymmetry = dg_antisense_5p - dg_sense_5p",
    )
    with patch("agent_core.tools.requests.post", return_value=_FakeResponse(payload)):
        out = compute_sirna_duplex_binding_vienna.invoke({"filepath": str(seq_file)})
    assert out["mfe_kcal_per_mol"] == pytest.approx(-5.3)
    assert out["asymmetry_kcal_per_mol"] == pytest.approx(0.9)
    assert out["dg_sense_5p_end_kcal_per_mol"] == pytest.approx(-4.1)
    assert out["dg_antisense_5p_end_kcal_per_mol"] == pytest.approx(-3.2)
    assert out["asymmetry_convention"]


def test_wrapper_tolerates_older_service_without_asymmetry(tmp_path) -> None:
    seq_file = tmp_path / "duplex.fasta"
    seq_file.write_text(">sense\nGGGG\n>antisense\nCCCC\n", encoding="utf-8")
    with patch("agent_core.tools.requests.post", return_value=_FakeResponse(_duplex_payload())):
        out = compute_sirna_duplex_binding_vienna.invoke({"filepath": str(seq_file)})
    assert out["mfe_kcal_per_mol"] == pytest.approx(-5.3)
    assert out["asymmetry_kcal_per_mol"] is None
    assert out["dg_sense_5p_end_kcal_per_mol"] is None
    assert out["asymmetry_convention"] is None


# ── Component mapping + ASF dimension ────────────────────────────────────────


def test_asymmetry_component_linear_mapping() -> None:
    assert score_sirna_candidate({"duplex_asymmetry": -3.0})["asymmetry_component"] == pytest.approx(0.0)
    assert score_sirna_candidate({"duplex_asymmetry": 0.0})["asymmetry_component"] == pytest.approx(0.5)
    assert score_sirna_candidate({"duplex_asymmetry": 3.0})["asymmetry_component"] == pytest.approx(1.0)
    assert score_sirna_candidate({"duplex_asymmetry": 10.0})["asymmetry_component"] == pytest.approx(1.0)


def test_asymmetry_component_none_when_absent() -> None:
    assert score_sirna_candidate({"duplex_mfe": -30.0})["asymmetry_component"] is None


def test_rank_uses_asymmetry_third_dimension() -> None:
    """Two candidates identical on efficiency and specificity, differing on
    end asymmetry: the better RISC-loading orientation wins."""
    wf = SirnaDesignWorkflow.__new__(SirnaDesignWorkflow)  # rank path only
    wf._workflow_state = {"_sirna_input": SimpleNamespace(candidate_count=10, mingc=0.0, maxgc=1.0)}
    wf._trace_records = []
    from agent_core.workflow_models import Candidate

    def _mk(source, asym):
        return Candidate(
            sequence="ACGUACGUACGUACGUACGU",
            sequence_type="sirna",
            source=source,
            scores={},
            metadata={"metrics_bundle": {
                "gc_content": 0.5,
                "duplex_mfe": -30.0,
                "off_target_count": 0,
                "duplex_asymmetry": asym,
            }},
        )

    result = wf.rank_and_format([_mk("bad_orientation", -1.5), _mk("good_orientation", 1.5)])
    assert result.best_candidate is not None
    assert result.best_candidate.source == "good_orientation"


def test_rank_drops_asymmetry_dimension_without_measurements() -> None:
    """Older service (no asymmetry keys): the dimension drops pool-wide and
    the ordering equals the two-dimension behaviour."""
    wf = SirnaDesignWorkflow.__new__(SirnaDesignWorkflow)
    wf._workflow_state = {"_sirna_input": SimpleNamespace(candidate_count=10, mingc=0.0, maxgc=1.0)}
    wf._trace_records = []
    from agent_core.workflow_models import Candidate

    def _mk(source, mfe):
        return Candidate(
            sequence="ACGUACGUACGUACGUACGU",
            sequence_type="sirna",
            source=source,
            scores={},
            metadata={"metrics_bundle": {
                "gc_content": 0.5,
                "duplex_mfe": mfe,
                "off_target_count": 0,
            }},
        )

    result = wf.rank_and_format([_mk("weak", -20.0), _mk("strong", -35.0)])
    assert result.best_candidate is not None
    assert result.best_candidate.source == "strong"
