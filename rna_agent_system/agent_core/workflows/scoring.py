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


class FullLengthMrnaScoringFunction(ScoringFunction):
    """Score full-length mRNA candidate for Borda-count ranking.

    Returns per-module raw scores:
      - cds_component: normalized CDS score (combined_score / cds_length)
      - cds_combined_score: classic -mfe + codon_count * log(CAI)
      - utr5_mrl: raw predicted MRL
      - utr3_stability: raw predicted stability
    """

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        cds_length = int(metrics.get("cds_length", 0))

        # CDS component
        cds_bundle = {
            "mfe_kcal_per_mol": metrics.get("cds_mfe"),
            "cai_score": metrics.get("cds_cai"),
            "sequence_length": cds_length,
        }
        # Import here to avoid circular dependency at module load time
        from agent_core.sequence_utils import score_mrna_candidate

        cds_scores = score_mrna_candidate(cds_bundle)
        cds_combined_score = cds_scores.get("combined_score", 0.0)
        cds_component = (
            cds_combined_score / cds_length if cds_length > 0 else None
        )

        # 5'UTR MRL
        utr5_mrl = metrics.get("utr5_predicted_mrl")
        utr5_component = float(utr5_mrl) if utr5_mrl is not None else None

        # 3'UTR stability
        utr3_stability = metrics.get("utr3_predicted_stability")
        utr3_component = float(utr3_stability) if utr3_stability is not None else None

        return {
            "cds_component": cds_component,
            "cds_combined_score": float(cds_combined_score),
            "utr5_mrl": utr5_component,
            "utr3_stability": utr3_component,
        }


class FullLengthBMCScoringFunction(ScoringFunction):
    """Score full-length mRNA with junction-aware penalty terms.

    Returns per-module **raw scores** (not a weighted sum).  Aggregation is
    performed in ``rank_and_format`` via a 5-dimensional **equal-weight Borda
    count** so that heterogeneous metrics (MFE, CAI, MRL, stability,
    junction penalties) can be combined without arbitrary min-max bounds.

    Score components (raw values, passed to Borda ranking)
    ----------------
    cds_component      : combined_score / cds_length
    utr5_mrl           : predicted mean ribosomal load
    utr3_stability     : predicted 3'UTR stability
    full_mfe_score     : inverted full-length MFE (more negative = higher raw)
    junction_score     : sum of inverted junction MFEs minus GC-diff penalties
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

        # ── Junction score (NEW) ──
        j1_mfe = metrics.get("junction_5utr_cds_mfe")
        j2_mfe = metrics.get("junction_cds_3utr_mfe")
        j1_gc_diff = metrics.get("junction_5utr_cds_gc_diff", 0.0)
        j2_gc_diff = metrics.get("junction_cds_3utr_gc_diff", 0.0)

        junction_score = 0.0
        if j1_mfe is not None:
            junction_score += -float(j1_mfe)
        if j2_mfe is not None:
            junction_score += -float(j2_mfe)
        gc_penalty = 0.0
        if j1_gc_diff is not None:
            gc_penalty += float(j1_gc_diff)
        if j2_gc_diff is not None:
            gc_penalty += float(j2_gc_diff)
        junction_score -= 5.0 * gc_penalty
        scores["junction_score"] = junction_score

        # No total here — aggregation happens via equal-weight Borda count in
        # rank_and_format so that each dimension contributes one rank.
        return scores
