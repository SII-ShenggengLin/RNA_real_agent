"""Tests for agent_core.calibrated.profiling_metrics."""

from __future__ import annotations

import math

import pytest

from agent_core.calibrated import profiling_metrics as pm


def _row(role, score, kd=None, eligible=True, success=True):
    return {
        "role": role,
        "kd_nm": kd,
        "ranking_eligible": eligible,
        "success": success,
        "raw": {"oracle_x": score},
    }


def test_screening_perfect_separation_is_verified():
    rows = [_row("binder", s, kd=10.0) for s in (0.9, 0.8, 0.85, 0.95)]
    rows += [_row("negative", s) for s in (0.1, 0.2, 0.15)]
    m = pm.screening_metrics(rows, "oracle_x")
    assert m["auroc"] == pytest.approx(1.0)
    assert m["n_pos"] == 4 and m["n_neg"] == 3
    assert pm.grade_capability("screening", m) == "verified"


def test_screening_inverse_separation_fails():
    rows = [_row("binder", s, kd=10.0) for s in (0.1, 0.2, 0.15, 0.05)]
    rows += [_row("negative", s) for s in (0.9, 0.8, 0.85)]
    m = pm.screening_metrics(rows, "oracle_x")
    assert m["auroc"] == pytest.approx(0.0)
    assert pm.grade_capability("screening", m) == "failed"


def test_screening_undecidable_without_negatives():
    m = pm.screening_metrics([_row("binder", 0.9, kd=5.0)], "oracle_x")
    assert math.isnan(m["auroc"])
    assert pm.grade_capability("screening", m) is None


def test_ranking_monotonic_is_verified():
    kds = [1.0, 10.0, 100.0, 1000.0]
    scores = [0.99, 0.8, 0.5, 0.1]  # higher score = tighter binder
    rows = [_row("binder", s, kd=k) for s, k in zip(scores, kds)]
    m = pm.ranking_metrics(rows, "oracle_x")
    assert m["spearman_rho"] == pytest.approx(1.0)
    assert m["n"] == 4
    assert pm.grade_capability("ranking", m) == "verified"


def test_ranking_requires_three_eligible_rows():
    rows = [_row("binder", 0.9, kd=1.0), _row("binder", 0.1, kd=100.0)]
    m = pm.ranking_metrics(rows, "oracle_x")
    assert math.isnan(m["spearman_rho"])
    # Non-eligible rows are excluded.
    rows += [_row("binder", 0.5, kd=10.0, eligible=False)]
    assert math.isnan(pm.ranking_metrics(rows, "oracle_x")["spearman_rho"])


def test_ranking_failure_below_threshold():
    kds = [1.0, 10.0, 100.0, 1000.0]
    scores = [0.1, 0.5, 0.8, 0.99]  # anti-correlated
    rows = [_row("binder", s, kd=k) for s, k in zip(scores, kds)]
    m = pm.ranking_metrics(rows, "oracle_x")
    assert pm.grade_capability("ranking", m) == "failed"


def test_docking_top1_rate():
    rows = [
        {"anchor": "a1", "kind": "native", "success": True, "raw": {"oracle_x": 0.9}},
        {"anchor": "a1", "kind": "decoy", "success": True, "raw": {"oracle_x": 0.1}},
        {"anchor": "a2", "kind": "native", "success": True, "raw": {"oracle_x": 0.2}},
        {"anchor": "a2", "kind": "decoy", "success": True, "raw": {"oracle_x": 0.8}},
    ]
    m = pm.docking_metrics(rows, "oracle_x")
    assert m["docking_top1_rate"] == pytest.approx(0.5)
    assert m["n_anchors"] == 2
    assert pm.grade_capability("docking", m) == "failed"


def test_docking_verified_at_two_thirds():
    rows = []
    for i, native_best in enumerate((True, True, False)):
        anchor = f"a{i}"
        rows.append({"anchor": anchor, "kind": "native", "success": True,
                     "raw": {"oracle_x": 0.9 if native_best else 0.1}})
        rows.append({"anchor": anchor, "kind": "decoy", "success": True,
                     "raw": {"oracle_x": 0.1 if native_best else 0.9}})
    m = pm.docking_metrics(rows, "oracle_x")
    assert m["docking_top1_rate"] == pytest.approx(2 / 3)
    assert pm.grade_capability("docking", m) == "verified"


def test_grade_scoring_not_decidable_and_unknown_rejected():
    assert pm.grade_capability("scoring", {}) is None
    with pytest.raises(ValueError):
        pm.grade_capability("magic", {})
