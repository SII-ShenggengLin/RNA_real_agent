"""Multi-objective utilities for reference-point optimization and Pareto frontiers.

These helpers are intentionally decoupled from any specific workflow so that both
``FullLengthMrnaDesignWorkflow`` and ``RnaAptamerDesignWorkflow`` can reuse the
same dominance, scalarization, and normalization logic.
"""

from __future__ import annotations

from typing import Any

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
    comparisons (e.g. BMC vs Serial ablations) must therefore NOT compare raw
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


def compute_violation(
    value: float,
    target: float,
    direction: str,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
) -> float:
    """Compute continuous violation of a metric against a target or interval.

    Args:
        value: Observed metric value.
        target: Target value (used for single-sided objectives).
        direction: "maximize" (value should be >= target) or "minimize"
            (value should be <= target). For interval constraints, use
            "interval" and provide ``lower_bound``/``upper_bound``.
        lower_bound: Lower bound for interval constraints.
        upper_bound: Upper bound for interval constraints.

    Returns:
        Non-negative violation distance. Zero means the constraint is satisfied.
    """
    if direction == "maximize":
        return max(0.0, target - value)
    if direction == "minimize":
        return max(0.0, value - target)
    if direction == "interval":
        if lower_bound is not None and value < lower_bound:
            return lower_bound - value
        if upper_bound is not None and value > upper_bound:
            return value - upper_bound
        return 0.0
    raise ValueError(f"Unknown direction: {direction}")


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


def build_normalized_reference_point(
    candidates: list[Candidate],
    objectives: list[str],
    maximize: dict[str, bool] | None = None,
    user_reference_point: dict[str, float] | None = None,
) -> tuple[dict[str, float], list[Candidate], dict[str, dict[str, float]]]:
    """Build a normalized reference point and normalize candidate scores.

    For each objective dimension:
      - Collect raw values from ``candidate.scores`` across the candidate pool.
      - Compute min/max bounds.
      - Normalize each candidate's value to [0, 1] using those bounds.
      - If the user provided a raw reference value, normalize it with the same
        bounds; otherwise use the utopian point (best observed value).

    Args:
        candidates: Evaluated candidates with ``scores`` populated.
        objectives: Objective dimension keys to consider.
        maximize: Per-direction flag. Defaults to all ``True``.
        user_reference_point: Optional user-provided raw reference values.

    Returns:
        A tuple of ``(norm_reference_point, norm_candidates, dim_bounds)``.
        ``norm_candidates`` are the input candidates mutated in place with
        additional ``{key}_norm`` entries in ``scores``. ``dim_bounds`` maps
        each dimension to ``{"min": ..., "max": ...}`` for traceability.
    """
    maximize = maximize or {key: True for key in objectives}
    user_reference_point = user_reference_point or {}

    norm_reference_point: dict[str, float] = {}
    dim_bounds: dict[str, dict[str, float]] = {}

    for key in objectives:
        raw_values = [
            float(c.scores[key])
            for c in candidates
            if c.scores.get(key) is not None
        ]
        if not raw_values:
            continue

        # Convert minimization objectives to maximization space for uniform
        # normalization, matching _as_maximization behavior.
        if maximize.get(key, True):
            converted_values = raw_values
        else:
            converted_values = [-v for v in raw_values]

        min_val = min(converted_values)
        max_val = max(converted_values)
        dim_bounds[key] = {"min": min_val, "max": max_val}

        span = max_val - min_val
        for c in candidates:
            raw = c.scores.get(key)
            if raw is None:
                continue
            converted = float(raw) if maximize.get(key, True) else -float(raw)
            c.scores[f"{key}_norm"] = 0.5 if span == 0 else (converted - min_val) / span

        # Reference value: user-provided (converted + normalized) or utopian.
        user_raw = user_reference_point.get(key)
        if user_raw is not None:
            user_converted = float(user_raw) if maximize.get(key, True) else -float(user_raw)
            norm_reference_point[key] = 0.5 if span == 0 else (user_converted - min_val) / span
        else:
            norm_reference_point[key] = 1.0 if span != 0 else 0.5

    return norm_reference_point, candidates, dim_bounds


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
