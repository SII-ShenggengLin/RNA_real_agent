"""Ranking-governance tests: verdict-driven objective assembly (DECISIONS (p)).

Pins docs/RANKING_GOVERNANCE.md §7 against the packaged SelfModel
(``default_self_model.json``): per-workflow assembly outcomes, mode
independence, the aptamer ``ranking_evidence_unavailable`` degrade, gated-
annotation recognition, and the no-op guarantee for the all-compute / all-
pending / unprofiled workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent_core.calibrated.objective_assembly import (
    ObjectiveRef,
    assemble_for_workflow,
    assemble_ranking_objectives,
    is_gated_error,
    review_oracle_use,
    screening_filter_demoted,
)
from agent_core.calibrated.runtime import (
    DEFAULT_SELF_MODEL_PATH,
    CalibratedRuntime,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.workflow_models import Candidate
from agent_core.workflows.multi_objective import apply_reference_point_ranking

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def packaged_self_model() -> SelfModel:
    return SelfModel.from_dict(
        json.loads(DEFAULT_SELF_MODEL_PATH.read_text(encoding="utf-8"))
    )


@pytest.fixture(autouse=True)
def _clean_runtime():
    """No process-wide CalibratedRuntime leaks into or out of these tests."""
    CalibratedRuntime.clear()
    yield
    CalibratedRuntime.clear()


def _configure_runtime(policy: str, tmp_path: Path) -> None:
    CalibratedRuntime.configure(
        self_model_path=DEFAULT_SELF_MODEL_PATH,
        audit_path=tmp_path / "audit.jsonl",
        policy=policy,
    )


# ─────────────────────────────────────────────────────────────────────────────
# §7.1  Assembly pinning against the packaged SelfModel
# ─────────────────────────────────────────────────────────────────────────────

APTAMER_REFS = {
    "egarps_component": ObjectiveRef(
        "egarps_component",
        "score_rna_protein_complex_with_egarps",
        "egarps_native_probability",
    ),
    "rhofold_component": ObjectiveRef(
        "rhofold_component",
        "predict_rna_tertiary_structure_with_rhofold",
        "rhofold_mean_plddt",
    ),
    "iptm_component": ObjectiveRef(
        "iptm_component",
        "predict_rna_protein_complex_with_proteinx",
        "proteinx_ipTM",
    ),
}

FULL_LENGTH_REFS = {
    "utr5_mrl": ObjectiveRef(
        "utr5_mrl", "predict_5utr_mrl_with_gemorna", "gemorna_5utr_mrl"
    ),
    "utr3_stability": ObjectiveRef(
        "utr3_stability", "predict_3utr_stability_with_gemorna", "gemorna_3utr_stability"
    ),
}

SGRNA_REFS = {
    "nn_component": ObjectiveRef(
        "nn_component", "score_sgrna_handle_with_crgpt", "crgpt_handle_score"
    ),
    "crisot_component": ObjectiveRef(
        "crisot_component", "score_crispr_off_target_with_crisot", "crisot_off_target_score"
    ),
}

TERTIARY_REFS = {
    "rhofold_component": ObjectiveRef(
        "rhofold_component",
        "predict_rna_tertiary_structure_with_rhofold",
        "rhofold_mean_plddt",
    ),
}


def test_assembly_pinning_aptamer_all_demoted(packaged_self_model) -> None:
    a = assemble_ranking_objectives(
        list(APTAMER_REFS), APTAMER_REFS, packaged_self_model, "rna_aptamer_design"
    )
    assert a.ranking_dims == []
    assert a.kept_flags == {}
    assert sorted(a.demoted) == ["egarps_component", "iptm_component", "rhofold_component"]
    assert a.degrade_reason is not None


def test_assembly_pinning_full_length_all_kept(packaged_self_model) -> None:
    objectives = ["cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"]
    a = assemble_ranking_objectives(
        objectives, FULL_LENGTH_REFS, packaged_self_model, "full_length_mrna"
    )
    # utr5_mrl: E7-verified on all families -> transferred-verified (keep+flag).
    # utr3_stability: gemorna_3utr_stability has no records -> unprofiled (keep+flag).
    # cds_component / full_mfe_score: deterministic compute, no ref.
    assert a.ranking_dims == objectives
    assert a.kept_flags == {
        "utr5_mrl": "transferred",
        "utr3_stability": "unprofiled",
    }
    assert a.demoted == {}
    assert a.degrade_reason is None


def test_assembly_pinning_sgrna_pending(packaged_self_model) -> None:
    objectives = ["nn_component", "crisot_component", "crisot_specificity_component"]
    a = assemble_ranking_objectives(objectives, SGRNA_REFS, packaged_self_model, "sgrna_design")
    assert a.ranking_dims == objectives
    assert a.kept_flags == {"nn_component": "pending", "crisot_component": "pending"}
    assert a.demoted == {}


def test_assembly_pinning_tertiary_unprofiled_under_task_key(packaged_self_model) -> None:
    objectives = ["rhofold_component", "rmsd_component", "tm_component"]
    a = assemble_ranking_objectives(
        objectives, TERTIARY_REFS, packaged_self_model, "rna_tertiary_structure_design"
    )
    # DECISIONS (k): RhoFold gates under the *calling* task type; the E1
    # aptamer failure is NOT inherited — no records exist for this key.
    assert a.ranking_dims == objectives
    assert a.kept_flags == {"rhofold_component": "unprofiled"}
    assert a.demoted == {}


def test_workflow_ref_tables_match_pinned_sets() -> None:
    """The workflow modules' ref tables must match the pinned sets above."""
    from agent_core.workflows.full_length_mrna_design import (
        _ORACLE_BACKED_OBJECTIVES as fl_refs,
    )
    from agent_core.workflows.rna_aptamer_design import (
        _ORACLE_BACKED_OBJECTIVES as apt_refs,
    )
    from agent_core.workflows.rna_tertiary_structure_design import (
        _ORACLE_BACKED_OBJECTIVES as tert_refs,
    )
    from agent_core.workflows.sgrna_design import (
        _ORACLE_BACKED_OBJECTIVES as sg_refs,
    )

    assert dict(fl_refs) == FULL_LENGTH_REFS
    assert dict(apt_refs) == APTAMER_REFS
    assert dict(sg_refs) == SGRNA_REFS
    assert dict(tert_refs) == TERTIARY_REFS


# ─────────────────────────────────────────────────────────────────────────────
# §7.2  Mode independence (advisory == enforce; off == escape hatch)
# ─────────────────────────────────────────────────────────────────────────────

def test_assembly_mode_independent(tmp_path) -> None:
    results = []
    for policy in ("advisory", "enforce"):
        _configure_runtime(policy, tmp_path)
        results.append(
            assemble_for_workflow(
                list(APTAMER_REFS), APTAMER_REFS, "rna_aptamer_design"
            )
        )
    a1, a2 = results
    assert (a1.ranking_dims, a1.kept_flags, sorted(a1.demoted), a1.degrade_reason) == (
        a2.ranking_dims, a2.kept_flags, sorted(a2.demoted), a2.degrade_reason
    )
    assert a1.ranking_dims == []  # aptamer demoted under both policies


def test_assembly_off_disables_the_mechanism() -> None:
    a = assemble_for_workflow(list(APTAMER_REFS), APTAMER_REFS, "rna_aptamer_design")
    assert a.governance == "off"
    assert a.ranking_dims == list(APTAMER_REFS)
    assert a.demoted == {}
    assert a.degrade_reason is None
    assert screening_filter_demoted(
        "predict_rna_tertiary_structure_with_rhofold", "rna_aptamer_design"
    ) is False


def test_screening_filter_demoted_for_rhofold(packaged_self_model) -> None:
    decision = review_oracle_use(
        "predict_rna_tertiary_structure_with_rhofold",
        "screening_evaluation",
        packaged_self_model,
        "rna_aptamer_design",
    )
    assert decision is not None and decision.verdict == "reject"


# ─────────────────────────────────────────────────────────────────────────────
# §7.3  Degrade path: aptamer rank_and_format under full demotion
# ─────────────────────────────────────────────────────────────────────────────

def _aptamer_workflow():
    from agent_core.workflows.rna_aptamer_design import (
        RnaAptamerDesignInput,
        RnaAptamerDesignWorkflow,
    )

    wf = RnaAptamerDesignWorkflow(MagicMock())
    wf._workflow_state["_aptamer_input"] = RnaAptamerDesignInput(
        protein_sequence="MTEY"  # minimal; ranking path only reads the input
    )
    return wf


def _candidates(n: int = 3) -> list[Candidate]:
    out = []
    for i in range(n):
        c = Candidate(sequence=f"ACGUACGUACGU{i}", source=f"gen{i}")
        c.scores.update(
            {
                "egarps_component": 0.9 - i * 0.1,
                "rhofold_component": 0.8 - i * 0.1,
                "iptm_component": 0.7 - i * 0.1,
            }
        )
        out.append(c)
    return out


def test_aptamer_degrade_state(tmp_path) -> None:
    _configure_runtime("advisory", tmp_path)
    wf = _aptamer_workflow()
    candidates = _candidates()

    result = wf.rank_and_format(candidates)

    # success stays True and errors stay empty: candidates were generated and
    # evaluated, retry cannot restore falsified oracles, and a non-empty
    # errors list is a hard failure under WorkflowResult.is_hard_failure.
    assert result.success is True
    assert result.errors == []
    assert result.is_hard_failure is False
    # extras land as top-level attributes (WorkflowResult extra="allow")
    assert getattr(result, "ranking_evidence_unavailable", None) is True
    assert getattr(result, "best_candidate_source", None) == "generation_order_no_evidence"
    assert result.summary.startswith("ranking_evidence_unavailable:")
    # No fabricated ASF: asf_distance absent, order preserved (generation).
    assert [c.id for c in result.all_candidates] == [c.id for c in candidates]
    assert all(c.scores.get("asf_distance") is None for c in result.all_candidates)
    gov = wf._workflow_state["_ranking_governance"]
    assert gov["degrade_reason"] and sorted(gov["demoted"]) == sorted(APTAMER_REFS)


def test_aptamer_ranks_when_governance_off() -> None:
    wf = _aptamer_workflow()
    candidates = _candidates()

    result = wf.rank_and_format(candidates)

    assert result.success is True
    assert getattr(result, "ranking_evidence_unavailable", None) is None
    # Candidate 0 leads every objective -> utopian ASF 0 -> ranked first.
    assert result.all_candidates[0].id == candidates[0].id
    assert result.all_candidates[0].scores["asf_distance"] == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# §7.4  Gated-annotation recognition
# ─────────────────────────────────────────────────────────────────────────────

def test_is_gated_error() -> None:
    assert is_gated_error({"type": "GatedActionError", "message": "failed ranking profiling"}) is True
    assert is_gated_error({"type": "ValueError", "message": "boom"}) is False
    assert is_gated_error(None) is False


# ─────────────────────────────────────────────────────────────────────────────
# §7.5  No-op regression: all-compute / all-pending / unprofiled workflows
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "objectives,refs,task_type",
    [
        (
            ["efficiency_component", "specificity_component", "asymmetry_component"],
            {},
            "sirna_design",
        ),
        (
            ["nn_component", "crisot_component", "crisot_specificity_component"],
            SGRNA_REFS,
            "sgrna_design",
        ),
        (
            ["rhofold_component", "rmsd_component", "tm_component"],
            TERTIARY_REFS,
            "rna_tertiary_structure_design",
        ),
        (
            ["cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"],
            FULL_LENGTH_REFS,
            "full_length_mrna",
        ),
    ],
)
def test_assembly_is_ranking_noop(
    objectives, refs, task_type, packaged_self_model
) -> None:
    """With governance off, assembly keeps every dim and the ASF is unchanged."""
    a = assemble_ranking_objectives(objectives, refs, packaged_self_model, task_type)
    assert a.ranking_dims == objectives
    assert a.degrade_reason is None

    pool = _candidates(4)
    full = apply_reference_point_ranking(pool, objectives)
    assembled = apply_reference_point_ranking(pool, a.ranking_dims)
    assert full.asf_map == assembled.asf_map
    assert full.best.id == assembled.best.id
