"""Composable scoring framework for RNA workflow candidates (Layer 2).

Provides ``ScoringFunction`` as a protocol/abstract base, plus concrete
implementations for each workflow domain. Also exposes generic utilities
like ``normalize_score`` for clamping and scaling.

Example::

    scorer = MrnaCdsScoringFunction()
    scores = scorer.score(metrics)
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from typing import Any


_LOGGER = logging.getLogger("agent_core.workflows.scoring")


# ─────────────────────────────────────────────────────────────────────────────
# Generic utilities
# ─────────────────────────────────────────────────────────────────────────────


def normalize_score(
    value: float | None,
    *,
    lower: float = 0.0,
    upper: float = 1.0,
    invert: bool = False,
) -> float:
    """Clamp *value* to [*lower*, *upper*] and optionally invert.

    Parameters
    ----------
    value
        Raw score value.
    lower, upper
        Bounds for clamping.
    invert
        If True, return ``upper - clamped + lower`` (so higher raw = lower
        normalized, useful when lower raw values are better).

    Returns
    -------
    float
        Normalized score in [lower, upper], or 0.0 if *value* is None.
    """
    if value is None:
        return 0.0
    try:
        v = float(value)
        clamped = max(lower, min(upper, v))
        if invert:
            return upper - clamped + lower
        return clamped
    except (TypeError, ValueError):
        return 0.0


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return ``numerator / denominator`` or *default* if denominator is 0."""
    if denominator == 0:
        return default
    return numerator / denominator


# ─────────────────────────────────────────────────────────────────────────────
# ScoringFunction protocol / abstract base
# ─────────────────────────────────────────────────────────────────────────────


class ScoringFunction(ABC):
    """Abstract base for a scoring function that turns raw metrics into scores."""

    @abstractmethod
    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Turn raw metrics into normalized score components.

        Must at minimum populate ``total_score`` key for ranking.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Concrete scoring functions
# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsScoringFunction(ScoringFunction):
    """Score mRNA CDS candidate: ``total_score = -mfe + codon_count * log(CAI)``."""

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        mfe_raw = metrics.get("mfe_kcal_per_mol")
        cai_raw = metrics.get("cai_score")
        length_nt = int(metrics.get("sequence_length", 0))

        result: dict[str, float] = {}

        mfe_per_nt = metrics.get("mfe_per_nt")
        if mfe_per_nt is not None:
            result["mfe_per_nt"] = float(mfe_per_nt)

        if cai_raw is not None:
            result["cai_score"] = float(cai_raw)

        if mfe_raw is not None and cai_raw is not None:
            try:
                cai_val = float(cai_raw)
                mfe_val = float(mfe_raw)
                if (
                    cai_val > 0.0
                    and length_nt > 0
                    and math.isfinite(cai_val)
                    and math.isfinite(mfe_val)
                ):
                    codon_count = length_nt // 3
                    combined_score = -mfe_val + codon_count * math.log(cai_val)
                    result["combined_score"] = float(combined_score)
                    result["total_score"] = float(combined_score)
                    return result
            except (TypeError, ValueError):
                pass

        result["total_score"] = 0.0
        return result


class SirnaRankScoringFunction(ScoringFunction):
    """Rank-based scoring for siRNA across all candidates.

    This is NOT a per-candidate scoring function. It operates on the full
    candidate list and mutates candidate.scores in place.
    """

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Per-candidate scoring for API compatibility."""
        duplex_mfe = metrics.get("duplex_mfe")
        off_target = metrics.get("off_target_count", 0)

        scores: dict[str, float] = {}
        if duplex_mfe is not None:
            scores["efficiency_component"] = min(
                1.0, max(0.0, -float(duplex_mfe) / 40.0)
            )
        else:
            scores["efficiency_component"] = 0.0

        scores["off_target_count"] = float(off_target)
        scores["specificity_component"] = 1.0 / (1.0 + float(off_target))
        scores["total_score"] = scores["efficiency_component"]
        return scores


class SgRnaScoringFunction(ScoringFunction):
    """Score sgRNA candidate from nn_score and crisot_score components."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or {"nn": 0.5, "crisot": 0.5}

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        nn_score = metrics.get("nn_score") or metrics.get("design_nn_score")
        crisot_score = metrics.get("crisot_score")

        scores: dict[str, float] = {}

        if nn_score is not None:
            scores["nn_component"] = max(0.0, min(1.0, 1.0 / float(nn_score)))
        else:
            scores["nn_component"] = 0.0

        if crisot_score is not None:
            scores["crisot_component"] = max(0.0, min(1.0, float(crisot_score)))
        else:
            scores["crisot_component"] = 0.0

        active_weights = 0.0
        weighted_sum = 0.0
        for key, weight in self.weights.items():
            comp_key = f"{key}_component"
            if comp_key in scores:
                active_weights += weight
                weighted_sum += weight * scores[comp_key]

        if active_weights > 0:
            scores["total_score"] = weighted_sum / active_weights
        else:
            scores["total_score"] = 0.0

        return scores


class FullLengthBMCScoringFunction(ScoringFunction):
    """Score full-length mRNA into per-module raw scores.

    Returns per-module **raw scores** (not a weighted sum).  The workflow
    aggregates them via reference-point optimization (Achievement Scalarizing
    Function) in ``rank_and_format``.

    Score components (raw values, passed to reference-point optimization)
    ----------------
    cds_component      : combined_score / cds_length
    utr5_mrl           : predicted mean ribosomal load
    utr3_stability     : predicted 3'UTR stability
    full_mfe_score     : inverted full-length MFE (more negative = higher raw)
    junction_5utr_cds_score : inverted 5'UTR-CDS junction MFE/nt minus GC-diff penalty
    junction_cds_3utr_score : inverted CDS-3'UTR junction MFE/nt minus GC-diff penalty
    """

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        scores: dict[str, float] = {}

        # ── CDS component ──
        cds_length = int(metrics.get("cds_length", 0))
        cds_bundle = {
            "mfe_kcal_per_mol": metrics.get("cds_mfe"),
            "cai_score": metrics.get("cds_cai"),
            "sequence_length": cds_length,
        }
        # Import here to avoid circular dependency at module load time
        from agent_core.sequence_utils import score_mrna_candidate

        cds_scores = score_mrna_candidate(cds_bundle)
        cds_combined_score = cds_scores.get("combined_score", 0.0)
        scores["cds_component"] = (
            cds_combined_score / cds_length if cds_length > 0 else 0.0
        )

        # ── UTR components ──
        utr5_mrl = metrics.get("utr5_predicted_mrl")
        scores["utr5_mrl"] = float(utr5_mrl) if utr5_mrl is not None else 0.0

        utr3_stab = metrics.get("utr3_predicted_stability")
        scores["utr3_stability"] = float(utr3_stab) if utr3_stab is not None else 0.0

        # ── Full-length MFE (more negative = better → higher raw score) ──
        full_mfe = metrics.get("full_length_mfe")
        if full_mfe is not None:
            scores["full_mfe_score"] = -float(full_mfe)
        else:
            scores["full_mfe_score"] = 0.0

        # ── Junction scores (length-normalized MFE) ──
        # Use per-nt MFE so junctions of different effective lengths are comparable.
        # More negative MFE → higher raw score (same sign convention as full MFE).
        # GC-diff penalty uses coefficient 1.0 so that MFE and GC smoothness
        # contribute on comparable scales (~0-0.5 vs ~0-1.0).
        j1_mfe_per_nt = metrics.get("junction_5utr_cds_mfe_per_nt")
        j2_mfe_per_nt = metrics.get("junction_cds_3utr_mfe_per_nt")
        j1_gc_diff = metrics.get("junction_5utr_cds_gc_diff")
        j2_gc_diff = metrics.get("junction_cds_3utr_gc_diff")

        junction_5utr_cds_score = 0.0
        if j1_mfe_per_nt is not None:
            junction_5utr_cds_score += -float(j1_mfe_per_nt)
        if j1_gc_diff is not None:
            junction_5utr_cds_score -= 1.0 * float(j1_gc_diff)
        scores["junction_5utr_cds_score"] = junction_5utr_cds_score

        junction_cds_3utr_score = 0.0
        if j2_mfe_per_nt is not None:
            junction_cds_3utr_score += -float(j2_mfe_per_nt)
        if j2_gc_diff is not None:
            junction_cds_3utr_score -= 1.0 * float(j2_gc_diff)
        scores["junction_cds_3utr_score"] = junction_cds_3utr_score

        return scores
