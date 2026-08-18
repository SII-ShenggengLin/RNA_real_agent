"""Unit tests for full-length mRNA scoring and the junction evaluator.

Generic (non-BMC) slices of the former BMC test module: the per-module raw
scorer and the JunctionEvaluator GC-diff / ddG metrics.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agent_core.workflow_models import Candidate
from agent_core.workflows.evaluators import JunctionEvaluator
from agent_core.workflows.scoring import FullLengthScoringFunction

import pytest


# Full-length scoring tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFullLengthScoringFunction:
    def test_score_returns_all_raw_components(self):
        scorer = FullLengthScoringFunction()
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
        scorer = FullLengthScoringFunction()
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
        scorer = FullLengthScoringFunction()
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
