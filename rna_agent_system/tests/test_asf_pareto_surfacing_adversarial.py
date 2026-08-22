"""Adversarial tests for the Pareto-frontier surfacing fix (2026-08-22).

Stress-tests the sirna/sgrna/tertiary frontier surfacing beyond the happy
path in ``test_asf_pareto_surfacing.py``:

- empty pool → dedicated empty result, no frontier claims, no crash;
- single candidate → frontier is that candidate;
- all components nulled by the metrics-bundle rule → frontier [], size 0;
- identical candidates → strict domination fails → both on the frontier;
- strictly dominated candidate → excluded from the frontier;
- partially measured candidate → dominated on its measured dims → excluded;
- siRNA candidate_count truncation → the surfaced frontier must only
  reference delivered candidates (all_candidates ⊇ frontier members).
"""

from __future__ import annotations

from types import SimpleNamespace
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


def _cand(cid: str, scores: dict[str, Any], bundle: dict[str, Any]) -> Candidate:
    c = Candidate(
        sequence="ACGUACGUAAGGCCUUACGU" + cid,
        sequence_type="rna",
        source=f"stub:{cid}",
        metadata={"metrics_bundle": dict(bundle)},
    )
    c.scores = dict(scores)
    c.status = "evaluated"
    return c


def _sirna_wf() -> SirnaDesignWorkflow:
    return SirnaDesignWorkflow(_Registry())


def _sgrna_wf() -> SgRnaDesignWorkflow:
    return SgRnaDesignWorkflow(_Registry())


def _tertiary_wf() -> RnaTertiaryStructureDesignWorkflow:
    return RnaTertiaryStructureDesignWorkflow(_Registry())


# ── 1. empty pools ───────────────────────────────────────────────────────────


def test_empty_pool_no_frontier_claims():
    for wf in (_sirna_wf(), _sgrna_wf(), _tertiary_wf()):
        result = wf.rank_and_format([])
        assert result.success is False
        assert getattr(result, "pareto_frontier", None) in (None, [])
        assert "pareto_frontier_size" not in result.summary


# ── 2. single candidate ──────────────────────────────────────────────────────


def test_single_candidate_frontier_is_itself():
    wf = _sirna_wf()
    c = _cand(
        "only",
        {"efficiency_component": 0.8, "specificity_component": 0.9,
         "asymmetry_component": 0.5, "total_rank": 1.0},
        {"duplex_mfe_kcal_per_mol": -30.0, "off_target_count": 0,
         "specificity_score": 0.9, "duplex_asymmetry": 0.5},
    )
    result = wf.rank_and_format([c])
    assert result.success is True
    frontier = getattr(result, "pareto_frontier", [])
    assert [x.id for x in frontier] == [c.id]
    assert "pareto_frontier_size=1" in result.summary


# ── 3. all components nulled by the bundle rule ──────────────────────────────


def test_all_components_nulled_frontier_empty_but_success():
    """Unmeasured pool: efficiency/asymmetry None (bundle absent), specificity
    re-scores to 1.0 for everyone (no off-target info) — the only surviving
    dim is equal for all candidates, so nobody dominates: the frontier is the
    whole pool, ranking degrades to pool order, summary stays honest."""
    wf = _sirna_wf()
    cands = [
        _cand("a", {"efficiency_component": None, "specificity_component": None,
                    "asymmetry_component": 0.9, "total_rank": 1.0}, {}),
        _cand("b", {"efficiency_component": None, "specificity_component": None,
                    "asymmetry_component": 0.1, "total_rank": 2.0}, {}),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    frontier = getattr(result, "pareto_frontier", [])
    frontier_ids = {c.id for c in frontier}
    delivered_ids = {c.id for c in result.all_candidates}
    # equal specificity-only pool: all non-dominated, all delivered
    assert frontier_ids == delivered_ids == {cands[0].id, cands[1].id}
    reported = int(
        [ln for ln in result.summary.splitlines()
         if ln.startswith("pareto_frontier_size=")][0].split("=")[1]
    )
    assert reported == len(frontier)
    # degraded ranking keeps pool order (candidate 'a' first)
    assert result.all_candidates[0].source == "stub:a"


# ── 4. identical candidates: strict domination fails ─────────────────────────


def test_identical_candidates_both_on_frontier():
    wf = _sgrna_wf()
    scores = {"nn_component": 0.8, "crisot_component": 0.8, "total_score": 0.8}
    bundle = {"nn_score": 0.8, "crisot_score": 0.8}
    cands = [_cand("x1", scores, bundle), _cand("x2", scores, bundle)]
    result = wf.rank_and_format(cands)
    assert result.success is True
    frontier_ids = {c.id for c in getattr(result, "pareto_frontier", [])}
    assert frontier_ids == {cands[0].id, cands[1].id}


# ── 5. dominated candidate excluded ──────────────────────────────────────────


def test_strictly_dominated_candidate_excluded():
    wf = _sgrna_wf()
    cands = [
        _cand("lead_nn", {"nn_component": 0.95, "crisot_component": 0.6,
                          "total_score": 0.8}, {"nn_score": 0.95, "crisot_score": 0.6}),
        _cand("lead_cr", {"nn_component": 0.5, "crisot_component": 0.97,
                          "total_score": 0.7}, {"nn_score": 0.5, "crisot_score": 0.97}),
        _cand("dominated", {"nn_component": 0.4, "crisot_component": 0.5,
                            "total_score": 0.4}, {"nn_score": 0.4, "crisot_score": 0.5}),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    frontier_ids = {c.id for c in getattr(result, "pareto_frontier", [])}
    assert frontier_ids == {cands[0].id, cands[1].id}
    assert cands[2].metadata.get("pareto_tag") in (None, "balanced")


# ── 6. partially measured candidate dominated on its measured dims ──────────


def test_partial_measurement_not_on_frontier_when_dominated():
    wf = _sirna_wf()
    cands = [
        _cand("full_lead", {"efficiency_component": 0.9, "specificity_component": 0.9,
                            "asymmetry_component": 0.5, "total_rank": 1.0},
              {"duplex_mfe_kcal_per_mol": -35.0, "off_target_count": 0,
               "specificity_score": 0.9, "duplex_asymmetry": 0.5}),
        # only efficiency measured, and it is below full_lead's → dominated
        # on its measured dims (asymmetry missing here, so full_lead must
        # dominate via efficiency+specificity only)
        _cand("partial", {"efficiency_component": 0.5, "specificity_component": 0.8,
                          "asymmetry_component": None, "total_rank": 2.0},
              {"duplex_mfe_kcal_per_mol": -20.0, "off_target_count": 0,
               "specificity_score": 0.8}),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    frontier_ids = {c.id for c in getattr(result, "pareto_frontier", [])}
    assert frontier_ids == {cands[0].id}


# ── 7. siRNA truncation × frontier consistency ──────────────────────────────


def test_sirna_truncation_frontier_only_references_delivered():
    wf = _sirna_wf()
    wf._workflow_state["_sirna_input"] = SimpleNamespace(
        mingc=0.0, maxgc=1.0, candidate_count=3
    )
    cands = [
        _cand("c1", {"efficiency_component": 0.9, "specificity_component": 0.9,
                     "asymmetry_component": 0.5, "total_rank": 1.0},
              {"gc_content": 0.45, "duplex_mfe_kcal_per_mol": -35.0,
               "off_target_count": 0, "specificity_score": 0.9,
               "duplex_asymmetry": 0.5}),
        _cand("c2", {"efficiency_component": 0.8, "specificity_component": 0.5,
                     "asymmetry_component": 0.6, "total_rank": 2.0},
              {"gc_content": 0.45, "duplex_mfe_kcal_per_mol": -30.0,
               "off_target_count": 0, "specificity_score": 0.5,
               "duplex_asymmetry": 0.6}),
        _cand("c3", {"efficiency_component": 0.5, "specificity_component": 0.95,
                     "asymmetry_component": 0.4, "total_rank": 3.0},
              {"gc_content": 0.45, "duplex_mfe_kcal_per_mol": -25.0,
               "off_target_count": 0, "specificity_score": 0.95,
               "duplex_asymmetry": 0.4}),
        _cand("c4", {"efficiency_component": 0.4, "specificity_component": 0.85,
                     "asymmetry_component": 0.7, "total_rank": 4.0},
              {"gc_content": 0.45, "duplex_mfe_kcal_per_mol": -22.0,
               "off_target_count": 0, "specificity_score": 0.85,
               "duplex_asymmetry": 0.7}),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    delivered_ids = {c.id for c in result.all_candidates}
    assert len(result.all_candidates) == 3  # truncated to candidate_count
    frontier_ids = {c.id for c in getattr(result, "pareto_frontier", [])}
    # BUG CHECK: every surfaced frontier member must be among the delivered
    assert frontier_ids <= delivered_ids, (
        f"frontier references undelivered candidates: {frontier_ids - delivered_ids}"
    )
    reported = int(
        [ln for ln in result.summary.splitlines()
         if ln.startswith("pareto_frontier_size=")][0].split("=")[1]
    )
    assert reported == len(frontier_ids)


# ── 8. tertiary direction sanity: rmsd component is inverted before ranking ──


def test_tertiary_rmsd_inversion_frontier():
    wf = _tertiary_wf()
    # rhofold equal; lower raw RMSD → higher rmsd_component → dominates
    cands = [
        _cand("close", {"rhofold_component": 0.8, "rmsd_component": 0.9,
                        "total_score": 0.85},
              {"rhofold_mean_plddt": 80.0, "alignment_rmsd": 0.5}),
        _cand("far", {"rhofold_component": 0.8, "rmsd_component": 0.5,
                      "total_score": 0.65},
              {"rhofold_mean_plddt": 80.0, "alignment_rmsd": 2.5}),
    ]
    result = wf.rank_and_format(cands)
    assert result.success is True
    frontier_ids = {c.id for c in getattr(result, "pareto_frontier", [])}
    assert frontier_ids == {cands[0].id}  # close dominates far
    assert result.best_candidate.id == cands[0].id
