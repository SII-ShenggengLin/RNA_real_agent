"""Multi-objective utilities for reference-point optimization and Pareto frontiers.

These helpers are intentionally decoupled from any specific workflow so that both
``FullLengthMrnaDesignWorkflow`` and ``RnaAptamerDesignWorkflow`` can reuse the
same dominance, scalarization, and normalization logic.
"""

from __future__ import annotations


from agent_core.workflow_models import Candidate


def extract_objective_vector(
    candidate: Candidate,
    objectives: list[str],
) -> dict[str, float]:
    """Extract the objective values from a candidate's scores.

    Missing objectives are omitted from the returned dictionary.
    """
    vector: dict[str, float] = {}
    for key in objectives:
        value = candidate.scores.get(key)
        if value is not None:
            try:
                vector[key] = float(value)
            except (TypeError, ValueError):
                continue
    return vector


def compute_utopian_reference_point(
    candidates: list[Candidate],
    objectives: list[str],
    maximize: dict[str, bool] | None = None,
) -> dict[str, float]:
    """Build a utopian reference point from the best value of each objective.

    For maximization objectives the reference is the maximum observed value;
    for minimization objectives it is the minimum observed value. Dimensions
    with no valid values are omitted.

    ANALYSIS CAVEAT (2026-07 experiment note): under a utopian reference the
    ASF-best candidate can have ``asf_distance == 0`` by construction (it *is*
    the reference when one candidate leads every objective). Cross-condition
    comparisons across pools of different sizes must therefore NOT compare raw
    utopian ASF distances; use a shared fixed reference point, per-objective
    raw components, or Pareto hypervolume instead.
    """
    maximize = maximize or {key: True for key in objectives}
    ref: dict[str, float] = {}
    for key in objectives:
        values = [
            float(c.scores[key])
            for c in candidates
            if c.scores.get(key) is not None
        ]
        if not values:
            continue
        ref[key] = max(values) if maximize.get(key, True) else min(values)
    return ref


def _as_maximization(
    vector: dict[str, float],
    maximize: dict[str, bool],
) -> dict[str, float]:
    """Convert a raw objective vector into an all-maximization vector.

    Dimensions marked ``False`` in ``maximize`` are negated so that "lower is
    better" becomes "higher is better" uniformly.
    """
    return {
        key: (value if maximize.get(key, True) else -value)
        for key, value in vector.items()
    }


def _dominates(
    a_vector: dict[str, float],
    b_vector: dict[str, float],
    objectives: list[str],
) -> bool:
    """Return True if ``a`` dominates ``b`` in maximization space.

    ``a`` dominates ``b`` only when ``a`` has a value for every objective that
    ``b`` has, is at least as good on all of them, and strictly better on at
    least one. Missing values are treated conservatively: a candidate missing a
    dimension cannot dominate another candidate that possesses that dimension.
    """
    # For every objective that b has, a must also have it and be no worse.
    for key in objectives:
        b_has = key in b_vector
        a_has = key in a_vector
        if b_has and not a_has:
            return False
        if b_has and a_has and a_vector[key] < b_vector[key]:
            return False

    # There must be at least one objective where both have values and a is strictly better.
    strictly_better = False
    for key in objectives:
        if key in a_vector and key in b_vector and a_vector[key] > b_vector[key]:
            strictly_better = True
            break
    return strictly_better


def is_dominated(
    candidate: Candidate,
    others: list[Candidate],
    objectives: list[str],
    maximize: dict[str, bool] | None = None,
) -> bool:
    """Check whether ``candidate`` is Pareto-dominated by any candidate in ``others``.

    Args:
        candidate: The candidate to test.
        others: The candidate pool to test against.
        objectives: Objective dimension keys to consider.
        maximize: Mapping from objective key to True if higher is better.
            Defaults to all-True (all objectives maximized).

    Returns:
        True if at least one other candidate dominates ``candidate``.
    """
    maximize = maximize or {key: True for key in objectives}
    candidate_vec = _as_maximization(
        extract_objective_vector(candidate, objectives), maximize
    )
    if not candidate_vec:
        return False

    for other in others:
        if other is candidate:
            continue
        other_vec = _as_maximization(
            extract_objective_vector(other, objectives), maximize
        )
        if not other_vec:
            continue
        if _dominates(other_vec, candidate_vec, objectives):
            return True
    return False


def compute_pareto_frontier(
    candidates: list[Candidate],
    objectives: list[str],
    maximize: dict[str, bool] | None = None,
) -> list[Candidate]:
    """Return the subset of candidates that are not Pareto-dominated.

    Args:
        candidates: All evaluated candidates.
        objectives: Objective dimension keys.
        maximize: Per-dimension maximization flag. Defaults to all True.

    Returns:
        List of non-dominated candidates, in the same order they appeared.
    """
    if not candidates:
        return []

    maximize = maximize or {key: True for key in objectives}
    frontier: list[Candidate] = []

    for candidate in candidates:
        if not is_dominated(candidate, candidates, objectives, maximize):
            frontier.append(candidate)

    return frontier


def normalize_to_unit_range(
    values: list[float],
) -> list[float]:
    """Min-max normalize a list of floats to [0, 1].

    If all values are identical, every entry is mapped to 0.5 so that the
    dimension does not distort the scalarizing function.
    """
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    span = max_val - min_val
    if span == 0:
        return [0.5 for _ in values]
    return [(v - min_val) / span for v in values]


def normalize_value(
    value: float,
    min_val: float,
    max_val: float,
) -> float:
    """Min-max normalize a single value to [0, 1].

    If ``min_val == max_val``, returns 0.5 so the dimension remains neutral.
    Values outside the [min_val, max_val] range are allowed and will map
    outside [0, 1], which is useful for ambitious reference points.
    """
    span = max_val - min_val
    if span == 0:
        return 0.5
    return (value - min_val) / span


def achievement_scalarizing_function(
    score_vector: dict[str, float],
    reference_point: dict[str, float],
    weights: dict[str, float],
    rho: float = 1e-3,
) -> float:
    """Compute the Achievement Scalarizing Function (ASF) distance to a reference point.

    Lower values indicate that ``score_vector`` is closer to ``reference_point``
    along the weighted Chebyshev plus augmented term. All inputs are assumed to
    be in maximization space and pre-normalized to comparable ranges.

    Args:
        score_vector: Current candidate's normalized objective values.
        reference_point: User-provided normalized reference point.
        weights: Per-dimension weights (should sum to 1 if used as a convex
            combination, but this is not enforced).
        rho: Small augmentation coefficient to guarantee Pareto optimality.

    Returns:
        Non-negative scalar ASF value.
    """
    if not score_vector:
        return float("inf")

    common = [k for k in score_vector if k in reference_point]
    if not common:
        return float("inf")

    weighted_diffs: list[float] = []
    for key in common:
        weight = weights.get(key, 1.0)
        diff = reference_point[key] - score_vector[key]
        weighted_diffs.append(weight * diff)

    max_term = max(weighted_diffs)
    sum_term = sum(abs(wd) for wd in weighted_diffs)
    return max_term + rho * sum_term


def assign_pareto_tags(
    candidates: list[Candidate],
    objectives: list[str],
    maximize: dict[str, bool] | None = None,
) -> None:
    """Annotate each candidate in ``candidates`` with a ``pareto_tag`` in metadata.

    The tag describes the objective dimension on which the candidate leads (or
    is closest to leading) within the provided set. This is useful for
    presenting the Pareto frontier to users.
    """
    if not candidates or not objectives:
        return

    maximize = maximize or {key: True for key in objectives}

    # Per-dimension champion among the provided candidates.
    champions: dict[str, Candidate | None] = {}
    best_values: dict[str, float] = {}
    for key in objectives:
        best_candidate: Candidate | None = None
        best_value: float | None = None
        for candidate in candidates:
            value = candidate.scores.get(key)
            if value is None:
                continue
            try:
                value_f = float(value)
            except (TypeError, ValueError):
                continue
            # Convert to maximization space for uniform comparison.
            if not maximize.get(key, True):
                value_f = -value_f
            if best_value is None or value_f > best_value:
                best_value = value_f
                best_candidate = candidate
        champions[key] = best_candidate
        if best_value is not None:
            best_values[key] = best_value

    assigned: set[int] = set()
    for key, champion in champions.items():
        if champion is not None and id(champion) not in assigned:
            champion.metadata.setdefault("pareto_tag", key)
            assigned.add(id(champion))

    # Fall back to "balanced" for untagged frontier members.
    for candidate in candidates:
        if "pareto_tag" not in candidate.metadata:
            candidate.metadata["pareto_tag"] = "balanced"


def cap_pareto_frontier(
    frontier: list[Candidate],
    max_size: int = 10,
) -> list[Candidate]:
    """Limit a Pareto frontier to ``max_size`` members.

    If the frontier exceeds ``max_size``, keep tagged champions first, then
    fall back to the original ordering. This preserves diversity without
    requiring an expensive secondary optimization.
    """
    if len(frontier) <= max_size:
        return frontier

    tagged = [c for c in frontier if c.metadata.get("pareto_tag") != "balanced"]
    untagged = [c for c in frontier if c.metadata.get("pareto_tag") == "balanced"]

    combined = tagged + untagged
    return combined[:max_size]
