"""Unit tests for multi-objective utilities (RPO + Pareto frontier)."""

from __future__ import annotations

import pytest

from agent_core.workflow_models import Candidate
from agent_core.workflows.multi_objective import (
    achievement_scalarizing_function,
    assign_pareto_tags,
    cap_pareto_frontier,
    compute_pareto_frontier,
    extract_objective_vector,
    is_dominated,
    normalize_to_unit_range,
)


def _candidate(scores: dict[str, float], seq: str = "ACGU") -> Candidate:
    return Candidate(sequence=seq, sequence_type="mrna", source="test", scores=scores)


def test_extract_objective_vector_skips_missing() -> None:
    c = _candidate({"a": 1.0})
    vec = extract_objective_vector(c, ["a", "b", "c", "d"])
    assert vec == {"a": 1.0}


def test_normalize_to_unit_range_basic() -> None:
    assert normalize_to_unit_range([0.0, 5.0, 10.0]) == [0.0, 0.5, 1.0]


def test_normalize_to_unit_range_identical() -> None:
    assert normalize_to_unit_range([3.0, 3.0, 3.0]) == [0.5, 0.5, 0.5]


def test_normalize_to_unit_range_empty() -> None:
    assert normalize_to_unit_range([]) == []


def test_is_dominated_simple() -> None:
    a = _candidate({"x": 1.0, "y": 1.0})
    b = _candidate({"x": 2.0, "y": 2.0})
    c = _candidate({"x": 3.0, "y": 0.5})
    maximize = {"x": True, "y": True}

    assert is_dominated(a, [b], ["x", "y"], maximize) is True
    assert is_dominated(b, [a], ["x", "y"], maximize) is False
    # c is better on x but worse on y -> trade-off, not dominated by b
    assert is_dominated(c, [b], ["x", "y"], maximize) is False


def test_is_dominated_minimization() -> None:
    a = _candidate({"cost": 10.0})
    b = _candidate({"cost": 5.0})
    maximize = {"cost": False}

    assert is_dominated(a, [b], ["cost"], maximize) is True
    assert is_dominated(b, [a], ["cost"], maximize) is False


def test_is_dominated_missing_value_is_conservative() -> None:
    a = _candidate({"x": 1.0, "y": 1.0})
    b = _candidate({"x": 2.0})  # missing y
    maximize = {"x": True, "y": True}

    # b cannot dominate a because it lacks y
    assert is_dominated(a, [b], ["x", "y"], maximize) is False


def test_compute_pareto_frontier() -> None:
    c1 = _candidate({"x": 1.0, "y": 1.0})  # dominated
    c2 = _candidate({"x": 2.0, "y": 2.0})  # non-dominated
    c3 = _candidate({"x": 3.0, "y": 0.5})  # non-dominated (trade-off)
    c4 = _candidate({"x": 0.5, "y": 0.5})  # dominated

    frontier = compute_pareto_frontier(
        [c1, c2, c3, c4], ["x", "y"], {"x": True, "y": True}
    )
    frontier_ids = {c.id for c in frontier}
    assert frontier_ids == {c2.id, c3.id}


def test_achievement_scalarizing_function_reaches_reference() -> None:
    ref = {"x": 1.0, "y": 1.0}
    weights = {"x": 0.5, "y": 0.5}
    # Candidate exactly at reference point -> ASF should be 0
    assert achievement_scalarizing_function(ref, ref, weights) == pytest.approx(0.0)

    # Candidate below reference on both dimensions -> positive ASF
    below = {"x": 0.5, "y": 0.5}
    assert achievement_scalarizing_function(below, ref, weights) > 0.0


def test_achievement_scalarizing_function_no_common_objectives() -> None:
    assert achievement_scalarizing_function({"x": 1.0}, {"y": 1.0}, {"x": 1.0}) == float("inf")


def test_assign_pareto_tags() -> None:
    c1 = _candidate({"x": 3.0, "y": 1.0})
    c2 = _candidate({"x": 1.0, "y": 3.0})
    c3 = _candidate({"x": 2.0, "y": 2.0})

    assign_pareto_tags([c1, c2, c3], ["x", "y"])
    assert c1.metadata["pareto_tag"] == "x"
    assert c2.metadata["pareto_tag"] == "y"
    assert c3.metadata["pareto_tag"] == "balanced"


def test_cap_pareto_frontier() -> None:
    candidates = [_candidate({"x": float(i)}, seq=f"seq{i}") for i in range(15)]
    for c in candidates:
        c.metadata["pareto_tag"] = "balanced"
    capped = cap_pareto_frontier(candidates, max_size=10)
    assert len(capped) == 10


def test_cap_pareto_frontier_keeps_tagged_first() -> None:
    tagged = _candidate({"x": 1.0}, seq="tagged")
    tagged.metadata["pareto_tag"] = "x"
    balanced = [_candidate({"x": float(i)}, seq=f"seq{i}") for i in range(15)]
    for c in balanced:
        c.metadata["pareto_tag"] = "balanced"

    frontier = [tagged] + balanced
    capped = cap_pareto_frontier(frontier, max_size=5)
    assert capped[0].id == tagged.id
    assert len(capped) == 5


# ── Shared reference-point ranking layer (ASF audit 2026-08-20) ──────────────

from agent_core.workflows.multi_objective import apply_reference_point_ranking  # noqa: E402


def test_ranking_missing_dim_imputed_pool_worst_not_rewarded() -> None:
    """A candidate missing its would-be-worst dimension must not outrank a
    candidate measured there (omission used to lower the Chebyshev max)."""
    complete = _candidate({"a": 1.0, "b": 0.1}, seq="complete")  # worst on b
    unmeasured = _candidate({"a": 1.0}, seq="unmeasured")       # b missing
    ranking = apply_reference_point_ranking(
        [complete, unmeasured], ["a", "b"]
    )
    assert ranking.asf_map[complete.id] < ranking.asf_map[unmeasured.id]


def test_ranking_imputation_does_not_distort_measured_normalization() -> None:
    """Imputed pool-worst entries use the measured minimum, not a 0.0 literal,
    so the measured candidates' normalized spread is preserved."""
    # a is constant (neutral dim); b spread over the measured candidates.
    measured = [_candidate({"a": 0.5, "b": v}, seq=f"m{i}") for i, v in enumerate((0.9, 0.8, 0.7))]
    missing = _candidate({"a": 0.5}, seq="miss")  # b missing
    ranking = apply_reference_point_ranking(measured + [missing], ["a", "b"])
    # Pool-worst imputation ties the missing candidate with the measured
    # pool-worst candidate (identical normalized vectors by design) and is
    # strictly worse than everything better than pool-worst.
    assert ranking.asf_map[missing.id] == pytest.approx(
        max(ranking.asf_map[c.id] for c in measured)
    )
    assert ranking.asf_map[missing.id] > ranking.asf_map[measured[0].id]
    assert ranking.best is not None and ranking.best.id != missing.id


def test_ranking_pool_wide_missing_dim_drops_for_everyone() -> None:
    candidates = [
        _candidate({"a": 1.0, "b": 1.0}, seq="one"),
        _candidate({"a": 0.5, "b": 0.5}, seq="two"),
    ]
    ranking = apply_reference_point_ranking(
        candidates, ["a", "b", "gated_off_dim"]
    )
    assert ranking.dropped_dims == ["gated_off_dim"]
    assert ranking.ranking_dims == ["a", "b"]
    assert set(ranking.asf_map) == {c.id for c in candidates}


def test_ranking_partial_reference_point_flagged_and_restricts_dims() -> None:
    a_champion = _candidate({"a": 1.0, "b": 0.0}, seq="a_champion")
    b_champion = _candidate({"a": 0.0, "b": 1.0}, seq="b_champion")
    ranking = apply_reference_point_ranking(
        [a_champion, b_champion], ["a", "b"], reference_point={"a": 1.0}
    )
    assert ranking.partial_reference is True
    assert ranking.ranking_dims == ["a"]
    assert ranking.best is not None and ranking.best.id == a_champion.id
    assert ranking.raw_reference_point == {"a": 1.0}


def test_ranking_full_reference_point_not_flagged_partial() -> None:
    candidates = [_candidate({"a": 1.0, "b": 1.0}, seq="x")]
    ranking = apply_reference_point_ranking(
        candidates, ["a", "b"], reference_point={"a": 1.0, "b": 1.0}
    )
    assert ranking.partial_reference is False


def test_ranking_utopian_reference_prefers_balanced_candidate() -> None:
    balanced = _candidate({"a": 0.7, "b": 0.7}, seq="balanced")
    lopsided = _candidate({"a": 1.0, "b": 0.0}, seq="lopsided")
    mediocre = _candidate({"a": 0.5, "b": 0.5}, seq="mediocre")
    ranking = apply_reference_point_ranking(
        [balanced, lopsided, mediocre], ["a", "b"]
    )
    # Utopian ref: Chebyshev punishes the balanced candidate's worst
    # normalized deficit (0.6) less than the lopsided candidate's full
    # deficit (1.0) on b.
    assert ranking.best is not None and ranking.best.id == balanced.id
    assert ranking.asf_map[balanced.id] < ranking.asf_map[lopsided.id]


def test_ranking_user_weights_favour_heavily_weighted_dimension() -> None:
    strong_on_a = _candidate({"a": 1.0, "b": 0.4}, seq="strong_on_a")
    strong_on_b = _candidate({"a": 0.4, "b": 1.0}, seq="strong_on_b")
    ranking = apply_reference_point_ranking(
        [strong_on_a, strong_on_b], ["a", "b"],
        weights={"a": 0.9, "b": 0.1},
    )
    # A heavy weight on ``a`` punishes a deficit on ``a``: the candidate
    # strong on the heavily weighted dimension wins.
    assert ranking.best is not None and ranking.best.id == strong_on_a.id


def test_ranking_incomplete_weight_map_falls_back_to_uniform() -> None:
    c1 = _candidate({"a": 1.0, "b": 0.4}, seq="c1")
    c2 = _candidate({"a": 0.4, "b": 1.0}, seq="c2")
    ranking = apply_reference_point_ranking(
        [c1, c2], ["a", "b"], weights={"a": 0.9}  # b weight missing
    )
    # Uniform fallback: symmetric candidates tie on ASF.
    assert ranking.asf_map[c1.id] == pytest.approx(ranking.asf_map[c2.id])


def test_ranking_all_candidates_missing_everything_degrade_to_pool_order() -> None:
    c1 = _candidate({}, seq="c1")
    c2 = _candidate({}, seq="c2")
    ranking = apply_reference_point_ranking([c1, c2], ["a", "b"])
    assert ranking.dropped_dims == ["a", "b"]
    assert ranking.asf_map == {}
    assert ranking.best is c1


def test_ranking_empty_pool() -> None:
    ranking = apply_reference_point_ranking([], ["a"])
    assert ranking.best is None
    assert ranking.asf_map == {}
