"""Unit tests for reference-point driven Bounded Multi-Module Coordination (BMC).

These tests validate the ReferencePointCoordinator, junction evaluator, and BMC
scoring without requiring live microservices.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agent_core.workflow_models import Candidate
from agent_core.workflows.coordinator import (
    Issue,
    ReferencePointCoordinator,
)
from agent_core.workflows.evaluators import JunctionEvaluator
from agent_core.workflows.full_length_mrna_design import FullLengthMrnaDesignWorkflow
from agent_core.workflows.scoring import FullLengthBMCScoringFunction

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator tests
# ─────────────────────────────────────────────────────────────────────────────


class TestReferencePointCoordinator:
    def test_diagnose_no_issues_when_meets_reference(self):
        """Candidate at or above reference point in all dimensions → no issues."""
        coord = ReferencePointCoordinator()
        norm_candidate = {
            "cds_component": 0.8,
            "utr5_mrl": 0.8,
            "utr3_stability": 0.8,
            "full_mfe_score": 0.8,
            "junction_5utr_cds_score": 0.8,
            "junction_cds_3utr_score": 0.8,
        }
        reference_point = {
            "cds_component": 0.8,
            "utr5_mrl": 0.8,
            "utr3_stability": 0.8,
            "full_mfe_score": 0.8,
            "junction_5utr_cds_score": 0.8,
            "junction_cds_3utr_score": 0.8,
        }
        issues = coord.diagnose(norm_candidate, reference_point)
        assert issues == []

    def test_diagnose_single_dimension_gap(self):
        """A gap in one dimension emits one issue with correct module mapping."""
        coord = ReferencePointCoordinator()
        norm_candidate = {"cds_component": 0.5}
        reference_point = {"cds_component": 0.7}
        issues = coord.diagnose(norm_candidate, reference_point)
        assert len(issues) == 1
        assert issues[0].issue_type == "CDS_COMPONENT_BELOW_REFERENCE"
        assert issues[0].value == pytest.approx(0.5, abs=1e-6)
        assert issues[0].target == pytest.approx(0.7, abs=1e-6)
        assert issues[0].violation == pytest.approx(0.2, abs=1e-6)
        assert issues[0].affected_modules == ("CDS",)

    def test_diagnose_multiple_dimension_gaps(self):
        """Gaps in multiple dimensions emit multiple issues."""
        coord = ReferencePointCoordinator()
        norm_candidate = {
            "cds_component": 0.5,
            "utr5_mrl": 0.6,
            "full_mfe_score": 0.9,
        }
        reference_point = {
            "cds_component": 0.7,
            "utr5_mrl": 0.8,
            "full_mfe_score": 0.85,
        }
        issues = coord.diagnose(norm_candidate, reference_point)
        issue_types = {i.issue_type for i in issues}
        assert "CDS_COMPONENT_BELOW_REFERENCE" in issue_types
        assert "UTR5_MRL_BELOW_REFERENCE" in issue_types
        assert "FULL_MFE_SCORE_BELOW_REFERENCE" not in issue_types

    def test_diagnose_missing_candidate_dimension_skipped(self):
        """If candidate lacks a dimension, it is skipped rather than crashing."""
        coord = ReferencePointCoordinator()
        norm_candidate = {}
        reference_point = {"cds_component": 0.7}
        issues = coord.diagnose(norm_candidate, reference_point)
        assert issues == []

    def test_diagnose_junction_module_mapping(self):
        """Per-junction score dimensions map to the correct modules."""
        coord = ReferencePointCoordinator()
        norm_candidate = {
            "junction_5utr_cds_score": 0.3,
            "junction_cds_3utr_score": 0.4,
        }
        reference_point = {
            "junction_5utr_cds_score": 0.8,
            "junction_cds_3utr_score": 0.8,
        }
        issues = coord.diagnose(norm_candidate, reference_point)
        j1 = next(i for i in issues if i.issue_type == "JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE")
        j2 = next(i for i in issues if i.issue_type == "JUNCTION_CDS_3UTR_SCORE_BELOW_REFERENCE")
        assert set(j1.affected_modules) == {"5UTR", "CDS"}
        assert set(j2.affected_modules) == {"CDS", "3UTR"}

    def test_broadcast_feedback_cds_lambda(self):
        """CDS component gap triggers a lambda_value adjustment."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                value=0.5,
                target=0.7,
                violation=0.2,
                affected_modules=("CDS",),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "CDS" in feedback
        assert any(a.param == "lambda_value" for a in feedback["CDS"].adjustments)

    def test_broadcast_feedback_full_mfe(self):
        """Full MFE gap affects all three modules."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="FULL_MFE_SCORE_BELOW_REFERENCE",
                value=0.4,
                target=0.8,
                violation=0.4,
                affected_modules=("5UTR", "CDS", "3UTR"),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "CDS" in feedback
        assert "5UTR" in feedback
        assert "3UTR" in feedback
        assert any(a.param == "lambda_value" for a in feedback["CDS"].adjustments)

    def test_broadcast_feedback_cds_cai_weak_increases_lambda(self):
        """If CAI is the weak CDS component, λ should increase."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                value=0.5,
                target=0.7,
                violation=0.2,
                affected_modules=("CDS",),
                evidence="test",
            )
        ]
        metrics = {"cds_cai": 0.6, "cds_mfe": -55.0}  # CAI weak, MFE strong
        feedback = coord.broadcast_feedback(issues, metrics)
        cds_adj = [a for a in feedback["CDS"].adjustments if a.param == "lambda_value"]
        assert len(cds_adj) == 1
        assert cds_adj[0].delta == pytest.approx(2.0)

    def test_broadcast_feedback_cds_mfe_weak_decreases_lambda(self):
        """If MFE stability is the weak CDS component, λ should decrease."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                value=0.5,
                target=0.7,
                violation=0.2,
                affected_modules=("CDS",),
                evidence="test",
            )
        ]
        metrics = {"cds_cai": 0.95, "cds_mfe": -25.0}  # CAI strong, MFE weak
        feedback = coord.broadcast_feedback(issues, metrics)
        cds_adj = [a for a in feedback["CDS"].adjustments if a.param == "lambda_value"]
        assert len(cds_adj) == 1
        assert cds_adj[0].delta == pytest.approx(-2.0)

    def test_broadcast_feedback_5utr_mrl(self):
        """5'UTR MRL gap: UTR presets honour ``utr_mode``; no coordinator override."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="UTR5_MRL_BELOW_REFERENCE",
                value=0.5,
                target=0.8,
                violation=0.3,
                affected_modules=("5UTR",),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "5UTR" in feedback
        assert feedback["5UTR"].adjustments == []
        assert "CDS" not in feedback

    def test_broadcast_feedback_3utr_stability(self):
        """3'UTR stability gap: no coordinator override of UTR presets."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="UTR3_STABILITY_BELOW_REFERENCE",
                value=0.5,
                target=0.8,
                violation=0.3,
                affected_modules=("3UTR",),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "3UTR" in feedback
        assert feedback["3UTR"].adjustments == []

    def test_broadcast_feedback_junction_issues(self):
        """Junction score gaps: no numeric adjustment on either side."""
        coord = ReferencePointCoordinator()
        issues = [
            Issue(
                issue_type="JUNCTION_5UTR_CDS_SCORE_BELOW_REFERENCE",
                value=0.3,
                target=0.8,
                violation=0.5,
                affected_modules=("5UTR", "CDS"),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "5UTR" in feedback
        assert "CDS" in feedback
        assert feedback["5UTR"].adjustments == []
        # CDS gets no numeric adjustment for pure junction issues.
        assert all(a.param != "lambda_value" for a in feedback["CDS"].adjustments)

    def test_convergence_max_rounds(self):
        coord = ReferencePointCoordinator()
        should_stop, reason = coord.has_converged(
            100.0, 90.0, round_num=3, max_rounds=3
        )
        assert should_stop is True
        assert "max_rounds_reached" in reason

    def test_convergence_insufficient_improvement(self):
        coord = ReferencePointCoordinator()
        should_stop, reason = coord.has_converged(
            100.0, 99.5, round_num=2, improvement_threshold=1.0
        )
        assert should_stop is True
        assert "insufficient_improvement" in reason

    def test_convergence_score_degraded(self):
        coord = ReferencePointCoordinator()
        should_stop, reason = coord.has_converged(
            95.0, 100.0, round_num=2
        )
        assert should_stop is True
        assert "score_degraded" in reason

    def test_convergence_continue(self):
        coord = ReferencePointCoordinator()
        should_stop, reason = coord.has_converged(
            110.0, 100.0, round_num=2, improvement_threshold=1.0
        )
        assert should_stop is False
        assert "improved" in reason


# ─────────────────────────────────────────────────────────────────────────────
# BMC Scoring tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFullLengthBMCScoringFunction:
    def test_score_returns_all_raw_components(self):
        scorer = FullLengthBMCScoringFunction()
        metrics = {
            "cds_length": 300,
            "cds_mfe": -40.0,
            "cds_cai": 0.85,
            "utr5_predicted_mrl": 8.5,
            "utr3_predicted_stability": 0.75,
            "full_length_mfe": -60.0,
            "junction_5utr_cds_mfe_per_nt": -0.30,  # -12/40
            "junction_cds_3utr_mfe_per_nt": -0.375,  # -15/40
            "junction_5utr_cds_gc_diff": 0.05,
            "junction_cds_3utr_gc_diff": 0.03,
        }
        scores = scorer.score(metrics)
        # All raw components must be present
        assert "cds_component" in scores
        assert "utr5_mrl" in scores
        assert "utr3_stability" in scores
        assert "full_mfe_score" in scores
        assert "junction_5utr_cds_score" in scores
        assert "junction_cds_3utr_score" in scores
        # Aggregated junction_score is no longer computed.
        assert "junction_score" not in scores
        # Raw value checks
        assert scores["full_mfe_score"] == 60.0  # -(-60)
        # junction_5utr_cds_score = 0.30 - 1*0.05 = 0.25
        assert scores["junction_5utr_cds_score"] == pytest.approx(0.25, rel=1e-3)
        # junction_cds_3utr_score = 0.375 - 1*0.03 = 0.345
        assert scores["junction_cds_3utr_score"] == pytest.approx(0.345, rel=1e-3)
        # total_score is NO LONGER computed here — it lives in rank_and_format
        assert "total_score" not in scores

    def test_score_without_junction_metrics(self):
        """Missing junction metrics should not crash; scores = 0."""
        scorer = FullLengthBMCScoringFunction()
        metrics = {
            "cds_length": 300,
            "cds_mfe": -40.0,
            "cds_cai": 0.85,
            "utr5_predicted_mrl": 8.5,
            "utr3_predicted_stability": 0.75,
            "full_length_mfe": -60.0,
        }
        scores = scorer.score(metrics)
        assert scores["junction_5utr_cds_score"] == 0.0
        assert scores["junction_cds_3utr_score"] == 0.0
        assert "total_score" not in scores

    def test_score_partial_junction_metrics(self):
        scorer = FullLengthBMCScoringFunction()
        metrics = {
            "cds_length": 300,
            "cds_mfe": -40.0,
            "cds_cai": 0.85,
            "utr5_predicted_mrl": 8.5,
            "utr3_predicted_stability": 0.75,
            "full_length_mfe": -60.0,
            "junction_5utr_cds_mfe_per_nt": -0.30,  # -12/40
            # missing junction_cds_3utr metrics and gc diffs
        }
        scores = scorer.score(metrics)
        assert scores["junction_5utr_cds_score"] == pytest.approx(0.30, rel=1e-3)
        assert scores["junction_cds_3utr_score"] == 0.0
        assert "total_score" not in scores


# ─────────────────────────────────────────────────────────────────────────────
# FullLengthMrnaDesignWorkflow BMC helper tests
# ─────────────────────────────────────────────────────────────────────────────


class TestDiagnosisCandidateSelection:
    """Tests for the multi-candidate BMC diagnosis helpers."""

    def _make_candidate(self, cid: str, scores: dict[str, float]) -> Candidate:
        return Candidate(
            id=cid,
            sequence=cid,
            sequence_type="mrna",
            source="test",
            metadata={},
            scores=scores,
        )

    def test_select_always_includes_best(self):
        """The provided best candidate is always in the diagnosis set."""
        best = self._make_candidate("best", {"cds_component": 0.5})
        others = [
            self._make_candidate("c1", {"cds_component": 0.3}),
        ]
        selected = FullLengthMrnaDesignWorkflow._select_diagnosis_candidates(
            others + [best],
            ("cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"),
            best,
        )
        assert len(selected) == 1
        assert selected[0].id == best.id

    def test_select_includes_per_objective_champions(self):
        """Each user-facing objective leader is included alongside the best."""
        best = self._make_candidate(
            "best",
            {
                "cds_component": 0.5,
                "utr5_mrl": 5.0,
                "utr3_stability": 0.5,
                "full_mfe_score": 50.0,
            },
        )
        champ_cds = self._make_candidate("champ_cds", {"cds_component": 0.9})
        champ_mrl = self._make_candidate("champ_mrl", {"utr5_mrl": 8.0})
        champ_stab = self._make_candidate("champ_stab", {"utr3_stability": 0.9})
        champ_mfe = self._make_candidate("champ_mfe", {"full_mfe_score": 80.0})

        candidates = [best, champ_cds, champ_mrl, champ_stab, champ_mfe]
        selected = FullLengthMrnaDesignWorkflow._select_diagnosis_candidates(
            candidates,
            ("cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"),
            best,
        )
        selected_ids = {c.id for c in selected}
        assert selected_ids == {"best", "champ_cds", "champ_mrl", "champ_stab", "champ_mfe"}

    def test_select_deduplicates_when_best_is_champion(self):
        """If the best is also a per-objective champion, it appears only once."""
        best = self._make_candidate(
            "best",
            {
                "cds_component": 0.9,
                "utr5_mrl": 8.0,
                "utr3_stability": 0.9,
                "full_mfe_score": 80.0,
            },
        )
        other = self._make_candidate("other", {"cds_component": 0.3})
        selected = FullLengthMrnaDesignWorkflow._select_diagnosis_candidates(
            [best, other],
            ("cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"),
            best,
        )
        assert len(selected) == 1
        assert selected[0].id == best.id

    def test_select_ignores_candidates_with_missing_objective(self):
        """Candidates missing a score for an objective do not become its champion."""
        best = self._make_candidate("best", {"cds_component": 0.5})
        no_score = self._make_candidate("no_score", {"utr5_mrl": 1.0})
        selected = FullLengthMrnaDesignWorkflow._select_diagnosis_candidates(
            [best, no_score],
            ("cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score"),
            best,
        )
        selected_ids = {c.id for c in selected}
        assert selected_ids == {best.id, no_score.id}

    def test_merge_issues_keeps_max_violation_per_type(self):
        """When the same issue_type appears from multiple candidates, keep the worst."""
        metrics_weak = {"cds_cai": 0.6}
        metrics_weaker = {"cds_cai": 0.4}
        issues = [
            (
                Issue(
                    issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                    value=0.5,
                    target=0.7,
                    violation=0.2,
                    affected_modules=("CDS",),
                    evidence="weak",
                ),
                metrics_weak,
            ),
            (
                Issue(
                    issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                    value=0.4,
                    target=0.7,
                    violation=0.3,
                    affected_modules=("CDS",),
                    evidence="weaker",
                ),
                metrics_weaker,
            ),
        ]
        merged, sources = FullLengthMrnaDesignWorkflow._merge_issues_with_sources(issues)
        assert len(merged) == 1
        assert merged[0].violation == pytest.approx(0.3, abs=1e-6)
        assert merged[0].evidence == "weaker"
        assert sources["CDS_COMPONENT_BELOW_REFERENCE"] == metrics_weaker

    def test_merge_issues_preserves_different_types(self):
        """Different issue types are preserved independently."""
        metrics_cds = {"cds_cai": 0.6}
        metrics_mrl = {"utr5_mrl": 5.0}
        issues = [
            (
                Issue(
                    issue_type="CDS_COMPONENT_BELOW_REFERENCE",
                    value=0.5,
                    target=0.7,
                    violation=0.2,
                    affected_modules=("CDS",),
                    evidence="test",
                ),
                metrics_cds,
            ),
            (
                Issue(
                    issue_type="UTR5_MRL_BELOW_REFERENCE",
                    value=0.5,
                    target=0.8,
                    violation=0.3,
                    affected_modules=("5UTR",),
                    evidence="test",
                ),
                metrics_mrl,
            ),
        ]
        merged, sources = FullLengthMrnaDesignWorkflow._merge_issues_with_sources(issues)
        assert len(merged) == 2
        issue_types = {i.issue_type for i in merged}
        assert issue_types == {
            "CDS_COMPONENT_BELOW_REFERENCE",
            "UTR5_MRL_BELOW_REFERENCE",
        }
        assert sources["CDS_COMPONENT_BELOW_REFERENCE"] == metrics_cds
        assert sources["UTR5_MRL_BELOW_REFERENCE"] == metrics_mrl


# ─────────────────────────────────────────────────────────────────────────────
# JunctionEvaluator translation-start checks
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckTranslationStart:
    """Unit tests for JunctionEvaluator._check_translation_start precision."""

    def test_ignores_upstream_aug_when_offset_provided(self):
        """uAUG in the 5'UTR portion should be ignored if cds_start_offset points to real AUG."""
        # 5'UTR ends with AUG (positions 0-2), CDS starts at position 3 with AUG
        seq = "AUG" + "AUG"
        structure = "..." + "..."
        result = JunctionEvaluator._check_translation_start(seq, structure, cds_start_offset=3)
        assert result["aug_found"] is True
        assert result["aug_position"] == 3
        assert result["aug_buried"] is False

    def test_detects_buried_real_start_codon_with_offset(self):
        """Real start codon at cds_start_offset is correctly flagged when buried."""
        seq = "AUG" + "AUG"
        structure = "..." + "()="  # real AUG (positions 3-5) is paired
        result = JunctionEvaluator._check_translation_start(seq, structure, cds_start_offset=3)
        assert result["aug_found"] is True
        assert result["aug_position"] == 3
        assert result["aug_buried"] is True

    def test_no_aug_found_when_offset_points_to_non_aug(self):
        """If cds_start_offset does not point to AUG, no start codon is reported."""
        seq = "AUG" + "CCC"
        structure = "..." + "..."
        result = JunctionEvaluator._check_translation_start(seq, structure, cds_start_offset=3)
        assert result["aug_found"] is False
        assert result["aug_position"] == -1

    def test_fallback_scans_first_aug_when_offset_omitted(self):
        """Legacy behavior: without offset, first AUG in the sequence is used."""
        seq = "AUG" + "CCC"
        structure = "()=" + "..."  # first AUG is paired
        result = JunctionEvaluator._check_translation_start(seq, structure)
        assert result["aug_found"] is True
        assert result["aug_position"] == 0
        assert result["aug_buried"] is True

    def test_kozak_region_checked_around_real_start(self):
        """Kozak burial is evaluated around the real start codon, not the first AUG."""
        seq = "AUG" + "AUG"
        structure = "()=" + "..."  # upstream AUG buried, real AUG unpaired
        result = JunctionEvaluator._check_translation_start(seq, structure, cds_start_offset=3)
        assert result["aug_buried"] is False
        # Kozak window starts at max(0, 3-4)=0, so includes the buried upstream AUG
        assert result["kozak_buried"] is True
        assert result["kozak_position_start"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# JunctionEvaluator GC-diff boundary calculation
# ─────────────────────────────────────────────────────────────────────────────


class TestJunctionEvaluatorGcDiff:
    """Unit tests for JunctionEvaluator GC-diff boundary calculation.

    The GC-diff must compare the UTR fragment against the CDS fragment at the
    actual junction boundary, not simply split the concatenated junction
    sequence in half.  This matters when one side is shorter than the 20-nt
    overlap window.
    """

    @pytest.fixture
    def evaluator(self):
        """JunctionEvaluator with folding capabilities disabled."""
        reg = MagicMock()
        reg.has.return_value = False
        return JunctionEvaluator(reg)

    def test_symmetric_junction_splits_at_boundary(self, evaluator):
        """When both sides are 20 nt, midpoint split equals boundary split."""
        candidate = Candidate(
            sequence="A" * 20 + "C" * 20 + "G" * 20,
            sequence_type="mrna",
            source="test",
            metadata={
                "utr5_sequence": "A" * 20,
                "cds_sequence": "C" * 20 + "G" * 20,
                "utr3_sequence": "G" * 20,
            },
        )
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        # 5'UTR-CDS: left=20 A's (GC=0), right=20 C's (GC=1)
        assert result["junction_5utr_cds_gc_diff"] == pytest.approx(1.0)
        assert result["junction_5utr_cds_left_gc"] == pytest.approx(0.0)
        assert result["junction_5utr_cds_right_gc"] == pytest.approx(1.0)
        # CDS-3'UTR: left=20 C's (GC=1), right=20 G's (GC=1)
        assert result["junction_cds_3utr_gc_diff"] == pytest.approx(0.0)
        assert result["junction_cds_3utr_left_gc"] == pytest.approx(1.0)
        assert result["junction_cds_3utr_right_gc"] == pytest.approx(1.0)

    def test_short_utr_uses_actual_boundary_not_midpoint(self, evaluator):
        """Short 5'UTR must not be mixed with CDS when computing GC diff."""
        candidate = Candidate(
            sequence="A" * 10 + "C" * 20 + "G" * 20,
            sequence_type="mrna",
            source="test",
            metadata={
                "utr5_sequence": "A" * 10,
                "cds_sequence": "C" * 20 + "G" * 10,
                "utr3_sequence": "G" * 20,
            },
        )
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        # 5'UTR-CDS junction: left=10 A's (GC=0), right=20 C's (GC=1)
        # Old midpoint logic would have split at 15: left = 10 A + 5 C (GC=0.333),
        # right = 15 C (GC=1), diff = 0.667.  New boundary logic gives 1.0.
        assert result["junction_5utr_cds_gc_diff"] == pytest.approx(1.0)
        assert result["junction_5utr_cds_left_gc"] == pytest.approx(0.0)
        assert result["junction_5utr_cds_right_gc"] == pytest.approx(1.0)

    def test_short_cds_uses_actual_boundary_for_cds_3utr(self, evaluator):
        """Short CDS must not be mixed with 3'UTR when computing GC diff."""
        candidate = Candidate(
            sequence="A" * 20 + "C" * 10 + "G" * 20,
            sequence_type="mrna",
            source="test",
            metadata={
                "utr5_sequence": "A" * 20,
                "cds_sequence": "C" * 10,
                "utr3_sequence": "G" * 20,
            },
        )
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        # CDS-3'UTR junction: left=10 C's (GC=1), right=20 G's (GC=1)
        assert result["junction_cds_3utr_gc_diff"] == pytest.approx(0.0)
        assert result["junction_cds_3utr_left_gc"] == pytest.approx(1.0)
        assert result["junction_cds_3utr_right_gc"] == pytest.approx(1.0)
        # 5'UTR-CDS junction: left=20 A's (GC=0), right=10 C's (GC=1)
        assert result["junction_5utr_cds_gc_diff"] == pytest.approx(1.0)
        assert result["junction_5utr_cds_left_gc"] == pytest.approx(0.0)
        assert result["junction_5utr_cds_right_gc"] == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# JunctionEvaluator full-length ddG report metric
# ─────────────────────────────────────────────────────────────────────────────


def _make_ddg_registry(
    mfe_unconstrained: float = -100.0,
    mfe_constrained: float = -90.0,
    fail_constrained: bool = False,
):
    """Registry where only LinearFold exists; MFE depends on constraints."""
    from agent_core.capabilities.base import CapabilityResult

    calls: list[dict] = []
    reg = MagicMock()

    def _has(name: str) -> bool:
        return name == "predict_rna_secondary_structure_with_linearfold"

    def _invoke(args: dict, state: dict | None = None) -> CapabilityResult:
        calls.append(args)
        constraints = args.get("constraints")
        if constraints is not None and fail_constrained:
            return CapabilityResult(
                success=False, tool_name="linearfold", output={}, error="boom"
            )
        mfe = mfe_constrained if constraints is not None else mfe_unconstrained
        struct_len = len(constraints) if constraints is not None else 10
        return CapabilityResult(
            success=True,
            tool_name="linearfold",
            output={"mfe": mfe, "structure": "." * struct_len},
        )

    cap = MagicMock()
    cap.invoke = _invoke
    reg.has = _has
    reg.get = lambda name: cap
    return reg, calls


def _ddg_candidate(utr5_len: int = 50) -> Candidate:
    utr5 = "A" * utr5_len
    cds = "AUG" + "C" * 57  # 60 nt, starts with AUG
    utr3 = "G" * 40
    return Candidate(
        sequence=utr5 + cds + utr3,
        sequence_type="mrna",
        source="test",
        metadata={
            "utr5_sequence": utr5,
            "cds_sequence": cds,
            "utr3_sequence": utr3,
        },
    )


def _ddg_calls(calls: list[dict]) -> list[dict]:
    """Only the full-length ddG folds (not the 20-nt fragment folds)."""
    return [c for c in calls if "junction_ddg" in c.get("filepath", "")]


class TestJunctionDdgConstraintString:
    """Constraint-string construction for the full-length ddG metric."""

    def test_marks_only_window_unpaired(self):
        from agent_core.workflows.evaluators import _ddg_constraint_string

        assert _ddg_constraint_string(10, 3, 6) == "???...????"

    def test_clips_to_sequence_bounds(self):
        from agent_core.workflows.evaluators import _ddg_constraint_string

        assert _ddg_constraint_string(5, -2, 3) == "...??"
        assert _ddg_constraint_string(5, 3, 99) == "???.."


class TestJunctionEvaluatorDdg:
    """Full-length constrained-fold ddG at the 5'UTR-CDS junction."""

    def test_windows_recorded_and_clipped(self):
        """W1 = CDS start -6..+9; W2 clips to the actual 5'UTR length."""
        reg, _calls = _make_ddg_registry()
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate(utr5_len=50)
        u5 = 50
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        assert result["junction_5utr_cds_ddg_w1_start"] == u5 - 6
        assert result["junction_5utr_cds_ddg_w1_end"] == u5 + 9
        # 5'UTR (50 nt) is shorter than the 60-nt W2 tail -> clipped to 0
        assert result["junction_5utr_cds_ddg_w2_start"] == 0
        assert result["junction_5utr_cds_ddg_w2_end"] == u5 + 30

    def test_ddg_open_nonnegative_and_constraint_correct(self):
        """ddG = constrained - unconstrained MFE; window is '.' in constraints."""
        reg, calls = _make_ddg_registry(mfe_unconstrained=-100.0, mfe_constrained=-90.0)
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate(utr5_len=50)
        full_len = len(candidate.sequence)
        u5 = 50
        result = evaluator.evaluate(candidate, {"workflow_state": {}})

        assert result["junction_5utr_cds_ddg_open_w1"] == pytest.approx(10.0)
        assert result["junction_5utr_cds_ddg_open_w2"] == pytest.approx(10.0)
        assert result["junction_5utr_cds_ddg_open_w1"] >= 0.0
        assert result["junction_5utr_cds_ddg_open_w2"] >= 0.0

        # One self-run unconstrained fold + two constrained folds.
        ddg_calls = _ddg_calls(calls)
        unconstrained = [c for c in ddg_calls if c.get("constraints") is None]
        constrained = [c for c in ddg_calls if c.get("constraints") is not None]
        assert len(unconstrained) == 1
        assert len(constrained) == 2

        windows = sorted(
            (c["constraints"].index("."), len(c["constraints"]))
            for c in constrained
        )
        # W1: '.' run starts at u5-6; W2: at 0 (clipped).
        assert windows == [(0, full_len), (u5 - 6, full_len)]
        for c in constrained:
            cons = c["constraints"]
            assert set(cons) <= {"?", "."}
            if cons.index(".") == u5 - 6:
                assert cons[u5 - 6 : u5 + 9] == "." * 15
                assert cons.count(".") == 15
            else:
                assert cons[: u5 + 30] == "." * (u5 + 30)

    def test_reuses_workflow_full_fold_when_linearfold(self):
        """No extra unconstrained fold when the workflow already folded."""
        reg, calls = _make_ddg_registry()
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate()
        context = {
            "workflow_state": {},
            "full_length_fold": {"mfe": -100.0, "fold_tool": "LinearFold"},
        }
        result = evaluator.evaluate(candidate, context)
        assert result["junction_5utr_cds_ddg_open_w1"] == pytest.approx(10.0)
        ddg_calls = _ddg_calls(calls)
        assert [c for c in ddg_calls if c.get("constraints") is None] == []
        assert len([c for c in ddg_calls if c.get("constraints") is not None]) == 2

    def test_self_folds_when_workflow_fold_was_vienna(self):
        """A ViennaRNA full fold cannot be reused (backend mismatch)."""
        reg, calls = _make_ddg_registry()
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate()
        context = {
            "workflow_state": {},
            "full_length_fold": {"mfe": -100.0, "fold_tool": "ViennaRNA"},
        }
        result = evaluator.evaluate(candidate, context)
        assert result["junction_5utr_cds_ddg_open_w1"] == pytest.approx(10.0)
        ddg_calls = _ddg_calls(calls)
        assert len([c for c in ddg_calls if c.get("constraints") is None]) == 1

    def test_constrained_fold_failure_yields_none(self):
        """Fault tolerance: failed constrained folds -> ddG None, no raise."""
        reg, _calls = _make_ddg_registry(fail_constrained=True)
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate()
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        assert result["junction_5utr_cds_ddg_open_w1"] is None
        assert result["junction_5utr_cds_ddg_open_w2"] is None
        # Window coordinates are still recorded.
        assert result["junction_5utr_cds_ddg_w1_start"] == 44

    def test_ddg_skipped_without_linearfold(self):
        """No LinearFold capability -> no ddG keys at all."""
        reg = MagicMock()
        reg.has.return_value = False
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate()
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        assert "junction_5utr_cds_ddg_open_w1" not in result
        assert "junction_5utr_cds_ddg_open_w2" not in result

    def test_no_burial_booleans_emitted(self):
        """The retired fragment-fold burial booleans must not reappear."""
        reg, _calls = _make_ddg_registry()
        evaluator = JunctionEvaluator(reg)
        candidate = _ddg_candidate()
        result = evaluator.evaluate(candidate, {"workflow_state": {}})
        for key in result:
            assert "aug" not in key
            assert "kozak" not in key
