"""mRNA ranking scores: combined stability + expression metric.

Core formula:
    total_score = -mfe + codon_count * log(CAI)

Other component scores (gc_component, mfe_component, unpaired_component) are
computed for display / summary purposes only; they do not affect ranking.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

from agent_core.sequence_utils import compute_gc_content, normalize_rna_sequence


def _optional_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def gc_fraction_from_sequence(sequence: str) -> float:
    """(G+C) / length for normalized AUCG string; empty → 0.0."""

    if not sequence:
        return 0.0
    normalized = normalize_rna_sequence(sequence)
    if not normalized:
        return 0.0
    result = compute_gc_content(normalized)
    return float(result["gc_content"])


def gc_band_score(gc: float, *, low: float = 0.42, mid: float = 0.50, high: float = 0.58) -> float:
    """Triangle peak at ``mid``; 0 outside [low, high]."""

    if gc <= low or gc >= high:
        return 0.0
    if gc < mid:
        return (gc - low) / (mid - low)
    return (high - gc) / (high - mid)


def mfe_stability_component(
    mfe_kcal_per_mol: Optional[float], *, sequence_length: int
) -> float:
    """Map folding energy normalised by sequence length to [0, 1]."""

    if mfe_kcal_per_mol is None or sequence_length <= 0:
        return 0.45
    try:
        mfe = float(mfe_kcal_per_mol) / sequence_length
    except (TypeError, ValueError):
        return 0.45
    x = (-mfe - 0.02) / 0.25
    return float(min(1.0, max(0.0, x)))


def unpaired_band_score(
    unpaired: Optional[float], *, low: float = 0.30, mid: float = 0.50, high: float = 0.70
) -> float:
    """Triangle peak at ``mid``; 0 outside [low, high]."""
    if unpaired is None:
        return 0.45
    try:
        u = float(unpaired)
    except (TypeError, ValueError):
        return 0.45
    if u <= low or u >= high:
        return 0.0
    if u < mid:
        return (u - low) / (mid - low)
    return (high - u) / (high - mid)


def compute_mrna_metric_bundle(
    *,
    sequence: str,
    gc_from_tools: Optional[float],
    sequence_length_from_tools: Optional[int],
    mfe_kcal_per_mol: Optional[float],
    unpaired_fraction: Optional[float] = None,
    rnastop_overall_stability: Optional[float] = None,
    cai_score: Optional[float] = None,
) -> Dict[str, Any]:
    """Collect canonical keys used by scoring and summaries."""

    gc_local = gc_fraction_from_sequence(sequence)
    gc_eff = gc_from_tools if gc_from_tools is not None else gc_local
    length_eff = (
        sequence_length_from_tools
        if sequence_length_from_tools is not None
        else len(sequence)
    )
    mfe_per_nt = None
    if mfe_kcal_per_mol is not None and length_eff > 0:
        try:
            mfe_per_nt = float(mfe_kcal_per_mol) / length_eff
        except (TypeError, ValueError):
            mfe_per_nt = None
    return {
        "gc_content": float(gc_eff),
        "gc_content_local": float(gc_local),
        "sequence_length": int(length_eff),
        "mfe_kcal_per_mol": mfe_kcal_per_mol,
        "mfe_per_nt": mfe_per_nt,
        "unpaired_fraction": unpaired_fraction,
        "rnastop_overall_stability": rnastop_overall_stability,
        "cai_score": cai_score,
    }


def score_mrna_candidate(
    bundle: Mapping[str, Any],
    *,
    gc_low: float = 0.42,
    gc_mid: float = 0.50,
    gc_high: float = 0.58,
) -> Dict[str, float]:
    """Return component scores and ``total_score``.

    ``total_score`` is computed as ``-mfe + codon_count * log(CAI)``.
    Other components (gc_component, mfe_component, unpaired_component) are
    computed for display / summary purposes only.
    """

    gc = float(bundle.get("gc_content", 0.0))
    length_nt = int(bundle.get("sequence_length", 0))
    mfe_raw = bundle.get("mfe_kcal_per_mol")
    unpaired_raw = bundle.get("unpaired_fraction")
    cai_raw = bundle.get("cai_score")

    gc_c = gc_band_score(gc, low=gc_low, mid=gc_mid, high=gc_high)
    mfe_c = mfe_stability_component(_optional_float(mfe_raw), sequence_length=length_nt)
    unp_c = unpaired_band_score(_optional_float(unpaired_raw))

    result: Dict[str, float] = {
        "gc_component": float(gc_c),
        "mfe_component": float(mfe_c),
        "unpaired_component": float(unp_c),
        "mfe_per_nt": bundle.get("mfe_per_nt"),
    }

    if cai_raw is not None:
        result["cai_score"] = float(cai_raw)

    # total_score = -mfe + codon_count * log(CAI)
    if mfe_raw is not None and cai_raw is not None:
        try:
            cai_val = float(cai_raw)
            mfe_val = float(mfe_raw)
            if cai_val > 0.0 and length_nt > 0:
                codon_count = length_nt // 3
                combined_score = -mfe_val + codon_count * math.log(cai_val)
                result["combined_score"] = float(combined_score)
                result["total_score"] = float(combined_score)
                return result
        except (TypeError, ValueError):
            pass

    # Fallback when CAI or MFE is missing (should not happen in normal operation)
    result["total_score"] = 0.0
    return result
