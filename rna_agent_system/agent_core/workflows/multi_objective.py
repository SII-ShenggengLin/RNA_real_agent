"""Multi-objective utilities for reference-point optimization and Pareto frontiers.

These helpers are intentionally decoupled from any specific workflow so every
workflow with heterogeneous multi-objective candidate pools
(``FullLengthMrnaDesignWorkflow``, ``RnaAptamerDesignWorkflow``,
``SirnaDesignWorkflow``, ``SgRnaDesignWorkflow``,
``RnaTertiaryStructureDesignWorkflow``) can reuse the same dominance,
scalarization, and normalization logic through
:func:`apply_reference_point_ranking`.

Ranking-policy notes (2026-08-20 ASF audit, DECISIONS.md (n)):

- A dimension missing for *one* candidate is imputed at the pool-worst
  normalized value (0.0), never omitted: dropping a term from the Chebyshev
  max can only lower a candidate's ASF, so omission rewarded evaluation
  failures.
- A dimension missing for the *whole pool* (e.g. an oracle gated off by
  CapGate enforce, or an optional evaluator disabled) drops out of the
  ranking for everyone equally and is reported in ``dropped_dims``.
- A user reference point covering only a subset of the pool dimensions
  restricts the ranking to that subset (``partial_reference=True``); callers
  must surface the warning instead of silently re-weighting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

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


# ─────────────────────────────────────────────────────────────────────────────
# Shared reference-point ranking (single implementation for every ASF workflow)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ReferencePointRanking:
    """Outcome of :func:`apply_reference_point_ranking`.

    ``dropped_dims`` lists objectives with no measurement anywhere in the pool
    (they cannot rank); ``partial_reference`` flags a user reference point that
    covers only a subset of the measurable dimensions, which restricts the
    ranking to that subset.
    """

    best: Optional[Candidate] = None
    pareto_frontier: list[Candidate] = field(default_factory=list)
    raw_reference_point: Optional[dict[str, float]] = None
    asf_map: dict[str, float] = field(default_factory=dict)
    ranking_dims: list[str] = field(default_factory=list)
    dropped_dims: list[str] = field(default_factory=list)
    partial_reference: bool = False


def apply_reference_point_ranking(
    candidates: list[Candidate],
    objectives: list[str],
    reference_point: Optional[dict[str, float]] = None,
    *,
    maximize: Optional[dict[str, bool]] = None,
    weights: Optional[dict[str, float]] = None,
    rho: float = 1e-3,
    pareto_max_size: int = 10,
) -> ReferencePointRanking:
    """Rank ``candidates`` by augmented-Chebyshev ASF distance to a reference point.

    Policy (see module docstring): per-candidate missing dimensions are imputed
    at the pool-worst normalized value; dimensions unmeasured across the whole
    pool drop out for everyone; a partial user reference point restricts the
    ranking to its dimensions and is flagged. The Pareto frontier is always
    computed on raw measured values with conservative dominance.

    Args:
        candidates: Candidate pool (ranking happens over measured scores).
        objectives: Ordered objective dimension keys.
        reference_point: Optional user reference point in raw units; when
            omitted a utopian point (pool-best per dimension) is derived.
        maximize: Per-dimension direction flag (default all-True).
        weights: Optional per-dimension ASF weights (raw, renormalized to sum
            1 over the ranking dimensions); default uniform. If a ranking
            dimension lacks a weight, the uniform default is used for all.
        rho: Augmentation coefficient of the ASF.
        pareto_max_size: Frontier size cap.

    Returns:
        A :class:`ReferencePointRanking`; ``asf_map`` covers every candidate
        with at least one measurable ranking dimension (imputation may still
        assign it the worst value), so callers can sort by
        ``asf_map.get(candidate.id, inf)``.
    """
    result = ReferencePointRanking()
    if not candidates:
        return result

    maximize = maximize or {key: True for key in objectives}

    # Measured vectors in maximization space (missing dims omitted here; the
    # imputation step below fills them with the pool-worst normalized value).
    measured: list[dict[str, float]] = [
        _as_maximization(extract_objective_vector(c, objectives), maximize)
        for c in candidates
    ]

    # Dimensions measurable anywhere in the pool; the rest cannot rank.
    pool_dims = [
        key for key in objectives if any(key in vec for vec in measured)
    ]
    result.dropped_dims = [key for key in objectives if key not in pool_dims]

    # Reference point: user-provided (restricted to measurable dims) or the
    # pool utopian point.
    if reference_point is not None:
        raw_ref = {
            key: float(value)
            for key, value in reference_point.items()
            if key in pool_dims
        }
    else:
        raw_ref = compute_utopian_reference_point(candidates, pool_dims, maximize)
    result.raw_reference_point = raw_ref or None

    # Ranking dimensions follow the reference point; a user reference point
    # that skips measurable dims restricts the ranking (flagged, not silent).
    ranking_dims = [key for key in pool_dims if key in raw_ref]
    result.ranking_dims = ranking_dims
    result.partial_reference = bool(
        reference_point is not None and len(ranking_dims) < len(pool_dims)
    )
    if not ranking_dims:
        result.best = candidates[0]
        return result

    # Per-dimension normalization over *measured* values only, so imputed
    # pool-worst entries do not extend the observed range and compress the
    # spread of the measured candidates.
    dim_measured: dict[str, list[float]] = {key: [] for key in ranking_dims}
    for vec in measured:
        for key in ranking_dims:
            if key in vec:
                dim_measured[key].append(vec[key])

    dim_min: dict[str, float] = {}
    dim_span: dict[str, float] = {}
    for key in ranking_dims:
        values = dim_measured[key]
        dim_min[key] = min(values)
        span = max(values) - dim_min[key]
        dim_span[key] = span if span > 0 else 0.0

    def _norm(key: str, value: float) -> float:
        if dim_span[key] == 0.0:
            return 0.5
        return (value - dim_min[key]) / dim_span[key]

    norm_ref = {key: _norm(key, raw_ref[key]) for key in ranking_dims}

    # Weights: uniform by default; provided weights are renormalized over the
    # ranking dimensions. A missing weight for any ranking dim falls back to
    # uniform for all (mixed semantics would be arbitrary).
    if weights is not None and all(key in weights for key in ranking_dims):
        total = sum(float(weights[key]) for key in ranking_dims)
        asf_weights = (
            {key: float(weights[key]) / total for key in ranking_dims}
            if total > 0
            else {key: 1.0 / len(ranking_dims) for key in ranking_dims}
        )
    else:
        asf_weights = {key: 1.0 / len(ranking_dims) for key in ranking_dims}

    best: Optional[Candidate] = None
    best_asf = float("inf")
    for candidate, vec in zip(candidates, measured):
        norm_vec = {
            key: (_norm(key, vec[key]) if key in vec else 0.0)
            for key in ranking_dims
        }
        asf = achievement_scalarizing_function(
            norm_vec, norm_ref, asf_weights, rho=rho
        )
        result.asf_map[candidate.id] = asf
        if asf < best_asf:
            best_asf = asf
            best = candidate
    result.best = best if best is not None else candidates[0]

    # Pareto frontier on raw measured values (conservative dominance; a
    # candidate with no measured dimension at all stays off the frontier).
    pareto_pool = [c for c, vec in zip(candidates, measured) if vec]
    result.pareto_frontier = cap_pareto_frontier(
        compute_pareto_frontier(pareto_pool, objectives, maximize)
        if pareto_pool
        else [],
        max_size=pareto_max_size,
    )
    if result.pareto_frontier:
        assign_pareto_tags(result.pareto_frontier, objectives, maximize)

    return result
