"""Scoring for full-length mRNA workflow candidates (Layer 2)."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger("agent_core.workflows.scoring")


class FullLengthScoringFunction:
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
