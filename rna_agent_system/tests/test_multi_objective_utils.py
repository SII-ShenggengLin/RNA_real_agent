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
