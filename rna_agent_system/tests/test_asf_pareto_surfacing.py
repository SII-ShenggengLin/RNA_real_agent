"""Pareto-frontier surfacing regression (2026-08-22 consistency pass).

Every ASF workflow must surface the shared layer's Pareto frontier on the
WorkflowResult object (`pareto_frontier` extras + `pareto_frontier_size` in
the summary): full-length, aptamer (pre-existing), aso + mrna_cds
(v1.1.0/v1.2.0), and sirna/sgrna/tertiary (v1.3.1/v1.3.1/v1.2.1 — previously
computed but discarded).
"""

from __future__ import annotations

from typing import Any, Optional

from agent_core.capabilities.base import CapabilityResult
from agent_core.workflow_models import Candidate
from agent_core.workflows.rna_tertiary_structure_design import (
    RnaTertiaryStructureDesignWorkflow,
)
from agent_core.workflows.sgrna_design import SgRnaDesignWorkflow
from agent_core.workflows.sirna_design import SirnaDesignWorkflow


class _Cap:
    def __init__(self, name: str) -> None:
        self._name = name

    def invoke(self, args: dict, state: Optional[dict] = None) -> CapabilityResult:
        return CapabilityResult(success=True, tool_name=self._name, output={})


class _Registry:
    def __init__(self, *names: str) -> None:
        self._caps = {n: _Cap(n) for n in names}

    def has(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> _Cap:
        return self._caps[name]


def _cand(cid: str, seq: str, scores: dict[str, Any], bundle: dict[str, Any]) -> Candidate:
    # metrics_bundle must back every component: the ASF-audit nulling rule
    # re-marks components whose source metric is absent as None.
    c = Candidate(sequence=seq, sequence_type="rna", source=f"stub:{cid}",
                  metadata={"metrics_bundle": dict(bundle)})
    c.scores = dict(scores)
    c.status = "evaluated"
    return c


def _sirna_result():
    wf = SirnaDesignWorkflow(_Registry())
    cands = [
        _cand("a", "ACGU" * 6 + "A",
              {"efficiency_component": 0.9, "specificity_component": 0.8,
               "asymmetry_component": 0.6, "total_rank": 3.0},
              {"duplex_mfe_kcal_per_mol": -30.0, "off_target_count": 0,
               "specificity_score": 0.8, "duplex_asymmetry": 0.6}),
        _cand("b", "ACGU" * 6 + "C",
              {"efficiency_component": 0.7, "specificity_component": 1.0,
               "asymmetry_component": 0.5, "total_rank": 4.0},
              {"duplex_mfe_kcal_per_mol": -28.0, "off_target_count": 0,
               "specificity_score": 1.0, "duplex_asymmetry": 0.5}),
    ]
    return wf.rank_and_format(cands)


def _sgrna_result():
    wf = SgRnaDesignWorkflow(_Registry())
    cands = [
        _cand("a", "ACGU" * 20 + "A",
              {"nn_component": 0.9, "crisot_component": 0.7, "total_score": 0.8},
              {"nn_score": 0.9, "crisot_score": 0.7}),
        _cand("b", "ACGU" * 20 + "C",
              {"nn_component": 0.6, "crisot_component": 0.95, "total_score": 0.7},
              {"nn_score": 0.6, "crisot_score": 0.95}),
    ]
    return wf.rank_and_format(cands)


def _tertiary_result():
    wf = RnaTertiaryStructureDesignWorkflow(_Registry())
    cands = [
        _cand("a", "ACGU" * 10 + "A",
              {"rhofold_component": 0.9, "total_score": 0.8},
              {"rhofold_mean_plddt": 85.0}),
        _cand("b", "ACGU" * 10 + "C",
              {"rhofold_component": 0.7, "total_score": 0.6},
              {"rhofold_mean_plddt": 70.0}),
    ]
    return wf.rank_and_format(cands)


def test_sirna_surfaces_pareto_frontier():
    result = _sirna_result()
    assert result.success is True
    assert "pareto_frontier_size" in result.summary
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier is not None and len(frontier) >= 1


def test_sgrna_surfaces_pareto_frontier():
    result = _sgrna_result()
    assert result.success is True
    assert "pareto_frontier_size" in result.summary
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier is not None and len(frontier) >= 1


def test_tertiary_surfaces_pareto_frontier():
    result = _tertiary_result()
    assert result.success is True
    assert "pareto_frontier_size" in result.summary
    frontier = getattr(result, "pareto_frontier", None)
    assert frontier is not None and len(frontier) >= 1
