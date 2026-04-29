"""mRNA ranking scores: combined stability + expression metric.

Core formula:
    total_score = -mfe + codon_count * log(CAI)

Only ``total_score`` (and the intermediate ``combined_score``) affect ranking.
Raw metrics from the evaluate phase (gc_content, mfe_kcal_per_mol,
unpaired_fraction, cai_score, etc.) are displayed directly in reports.
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
) -> Dict[str, float]:
    """Return ``total_score`` computed as ``-mfe + codon_count * log(CAI)``.

    Raw metrics from *bundle* (gc_content, mfe_kcal_per_mol,
    unpaired_fraction, cai_score) are preserved in the result for display
    purposes but do **not** affect the ranking formula.
    """

    mfe_raw = bundle.get("mfe_kcal_per_mol")
    cai_raw = bundle.get("cai_score")
    length_nt = int(bundle.get("sequence_length", 0))

    result: Dict[str, float] = {
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
