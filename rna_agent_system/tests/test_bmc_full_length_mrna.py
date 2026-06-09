"""Unit tests for Bounded Multi-Module Coordination (BMC) components.

These tests validate the new coordinator, junction evaluator, and BMC scoring
without requiring live microservices.
"""

from __future__ import annotations

import pytest

from agent_core.workflows.coordinator import (
    FullLengthCoordinator,
    Issue,
)
from agent_core.workflows.scoring import FullLengthBMCScoringFunction


# ─────────────────────────────────────────────────────────────────────────────
# Coordinator tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFullLengthCoordinator:
    def test_diagnose_no_issues(self):
        """All metrics within thresholds → empty issue list."""
        coord = FullLengthCoordinator()
        metrics = {
            "full_length_mfe": -120.0,  # -120/400 = -0.30 < -0.25 threshold
            "total_length": 400,
            "full_paired_fraction": 0.70,
            "junction_5utr_cds_mfe": -15.0,
            "junction_cds_3utr_mfe": -20.0,
            "junction_cds_3utr_gc_diff": 0.05,
        }
        issues = coord.diagnose(metrics)
        assert issues == []

    def test_diagnose_full_mfe_too_high(self):
        """Length-normalized MFE above threshold triggers issue."""
        coord = FullLengthCoordinator()
        # 400 nt, MFE = -30 → MFE/nt = -0.075 > threshold -0.15
        metrics = {"full_length_mfe": -30.0, "total_length": 400}
        issues = coord.diagnose(metrics)
        assert len(issues) == 1
        assert issues[0].issue_type == "FULL_MFE_TOO_HIGH"
        assert "5UTR" in issues[0].affected_modules
        assert "CDS" in issues[0].affected_modules
        assert "3UTR" in issues[0].affected_modules
        # Verify the reported value is the normalized one
        assert issues[0].value == pytest.approx(-0.075, rel=1e-3)

    def test_diagnose_full_structure_too_loose(self):
        """Paired fraction below threshold triggers issue."""
        coord = FullLengthCoordinator()
        metrics = {"full_paired_fraction": 0.45}
        issues = coord.diagnose(metrics)
        assert any(i.issue_type == "FULL_STRUCTURE_TOO_LOOSE" for i in issues)

    def test_diagnose_full_mfe_passes_with_length_normalization(self):
        """Long sequence with sufficient normalized MFE should pass."""
        coord = FullLengthCoordinator()
        # 1000 nt, MFE = -300 → MFE/nt = -0.30 < threshold -0.25 (passes)
        metrics = {"full_length_mfe": -300.0, "total_length": 1000}
        issues = coord.diagnose(metrics)
        assert not any(i.issue_type == "FULL_MFE_TOO_HIGH" for i in issues)

    def test_diagnose_junction_5utr_cds_too_stable(self):
        coord = FullLengthCoordinator()
        metrics = {"junction_5utr_cds_mfe": -25.0}
        issues = coord.diagnose(metrics)
        assert any(i.issue_type == "JUNCTION_5UTR_CDS_TOO_STABLE" for i in issues)

    def test_diagnose_junction_5utr_cds_aug_buried(self):
        coord = FullLengthCoordinator()
        metrics = {
            "junction_5utr_cds_aug_buried": True,
            "junction_5utr_cds_aug_position": 22,
        }
        issues = coord.diagnose(metrics)
        assert any(i.issue_type == "JUNCTION_5UTR_CDS_AUG_BURIED" for i in issues)

    def test_diagnose_junction_5utr_cds_kozak_buried(self):
        coord = FullLengthCoordinator()
        metrics = {
            "junction_5utr_cds_kozak_buried": True,
            "junction_5utr_cds_kozak_position_start": 18,
        }
        issues = coord.diagnose(metrics)
        assert any(i.issue_type == "JUNCTION_5UTR_CDS_KOZAK_BURIED" for i in issues)

    def test_diagnose_junction_cds_3utr_gc_mismatch(self):
        coord = FullLengthCoordinator()
        metrics = {
            "junction_cds_3utr_gc_diff": 0.25,
            "junction_cds_3utr_left_gc": 0.65,
            "junction_cds_3utr_right_gc": 0.40,
        }
        issues = coord.diagnose(metrics)
        assert any(i.issue_type == "JUNCTION_CDS_3UTR_GC_MISMATCH" for i in issues)

    def test_broadcast_feedback_cds_only(self):
        coord = FullLengthCoordinator()
        issues = [
            Issue(
                issue_type="FULL_MFE_TOO_HIGH",
                value=-30.0,
                target=-50.0,
                affected_modules=("CDS",),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "CDS" in feedback
        assert "5UTR" not in feedback
        assert feedback["CDS"].priority == "medium"
        assert any(a.param == "lambda_value" for a in feedback["CDS"].adjustments)

    def test_broadcast_feedback_multiple_modules(self):
        coord = FullLengthCoordinator()
        issues = [
            Issue(
                issue_type="JUNCTION_5UTR_CDS_TOO_STABLE",
                value=-5.0,
                target=-10.0,
                affected_modules=("5UTR", "CDS"),
                evidence="test",
            )
        ]
        feedback = coord.broadcast_feedback(issues)
        assert "5UTR" in feedback
        assert "CDS" in feedback

    def test_convergence_max_rounds(self):
        coord = FullLengthCoordinator()
        should_stop, reason = coord.has_converged(
            100.0, 90.0, round_num=3, max_rounds=3
        )
        assert should_stop is True
        assert "max_rounds_reached" in reason

    def test_convergence_insufficient_improvement(self):
        coord = FullLengthCoordinator()
        should_stop, reason = coord.has_converged(
            100.0, 99.5, round_num=2, improvement_threshold=1.0
        )
        assert should_stop is True
        assert "insufficient_improvement" in reason

    def test_convergence_score_degraded(self):
        coord = FullLengthCoordinator()
        should_stop, reason = coord.has_converged(
            95.0, 100.0, round_num=2
        )
        assert should_stop is True
        assert "score_degraded" in reason

    def test_convergence_continue(self):
        coord = FullLengthCoordinator()
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
            "junction_5utr_cds_mfe": -12.0,
            "junction_cds_3utr_mfe": -15.0,
            "junction_5utr_cds_gc_diff": 0.05,
            "junction_cds_3utr_gc_diff": 0.03,
        }
        scores = scorer.score(metrics)
        # All 5 raw components must be present
        assert "cds_component" in scores
        assert "utr5_mrl" in scores
        assert "utr3_stability" in scores
        assert "full_mfe_score" in scores
        assert "junction_score" in scores
        # Raw value checks
        assert scores["full_mfe_score"] == 60.0  # -(-60)
        # junction_score = 12 + 15 - 5*(0.05+0.03) = 27 - 0.4 = 26.6
        assert scores["junction_score"] == pytest.approx(26.6, rel=1e-3)
        # total_score is NO LONGER computed here — it lives in rank_and_format
        assert "total_score" not in scores

    def test_score_without_junction_metrics(self):
        """Missing junction metrics should not crash; penalty = 0."""
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
        assert scores["junction_score"] == 0.0
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
            "junction_5utr_cds_mfe": -12.0,
            # missing junction_cds_3utr_mfe and gc diffs
        }
        scores = scorer.score(metrics)
        assert scores["junction_score"] == 12.0  # only j1 contributes
        assert "total_score" not in scores
