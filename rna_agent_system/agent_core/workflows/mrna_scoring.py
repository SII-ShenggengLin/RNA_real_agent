"""Simple mRNA ranking scores built from tool metrics + sequence-derived features.

Weights and normalization rules are explicit so other workflows (UTR, circRNA, intron) can reuse
the same helper pattern with different ``MrnaScoreWeights``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from agent_core.sequence_utils import compute_gc_content, normalize_rna_sequence


@dataclass(frozen=True)
class MrnaScoreWeights:
    """Default weights for ``total_score`` (components are in [0, 1]).

    For CDS-only design the length component is normally 0 because the
    protein fixes the CDS length.  Unpaired fraction (from dot-bracket)
    is added as a new structural-quality dimension.
    """

    gc: float = 0.40
    mfe: float = 0.35
    unpaired: float = 0.25
    length: float = 0.0

    def normalized(self) -> MrnaScoreWeights:
        """Scale weights to sum to 1.0."""

        s = self.gc + self.mfe + self.unpaired + self.length
        if s <= 0:
            return MrnaScoreWeights(
                gc=1.0 / 3, mfe=1.0 / 3, unpaired=1.0 / 3, length=0.0
            )
        return MrnaScoreWeights(
            gc=self.gc / s,
            mfe=self.mfe / s,
            unpaired=self.unpaired / s,
            length=self.length / s,
        )


def _optional_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def gc_fraction_from_sequence(sequence: str) -> float:
    """(G+C) / length for normalized AUCG string; empty → 0.0.

    Uses the shared normalization/computation so local fallback scores are
    consistent with the microservice.
    """

    if not sequence:
        return 0.0
    normalized = normalize_rna_sequence(sequence)
    if not normalized:
        return 0.0
    result = compute_gc_content(normalized)
    return float(result["gc_content"])


def gc_band_score(gc: float, *, low: float = 0.42, mid: float = 0.50, high: float = 0.58) -> float:
    """Triangle peak at ``mid``; 0 outside [low, high].

    Interpretation: many designs target moderate GC for balance of stability vs expression;
    adjust ``low/high`` if your organism panel differs.
    """

    if gc <= low or gc >= high:
        return 0.0
    if gc < mid:
        return (gc - low) / (mid - low)
    return (high - gc) / (high - mid)


def mfe_stability_component(
    mfe_kcal_per_mol: Optional[float], *, sequence_length: Optional[int] = None
) -> float:
    """Map folding energy (kcal/mol, typically negative) to [0, 1].

    When *sequence_length* is provided the MFE is normalised by length
    (kcal/mol per nt) so that scores are comparable across different CDS
    lengths.

    Missing / NaN → **0.45** (slightly below neutral) so failed folds do
    not dominate ranking.
    """

    if mfe_kcal_per_mol is None:
        return 0.45
    try:
        mfe = float(mfe_kcal_per_mol)
    except (TypeError, ValueError):
        return 0.45

    if sequence_length and sequence_length > 0:
        mfe = mfe / sequence_length
        # Normalised range roughly [-0.30, -0.02] per nt
        x = (-mfe - 0.02) / 0.28
    else:
        # Legacy linear map: [-50,-5] → [1, 0]
        x = (-mfe - 5.0) / 45.0
    return float(min(1.0, max(0.0, x)))


def length_target_score(length_nt: int, *, target_nt: Optional[int]) -> float:
    """If ``target_nt`` is None → always 1.0 (ignore length). Else triangular peak at target."""

    if target_nt is None or target_nt <= 0:
        return 1.0
    # Within ±25% of target full score at center; linear decay to 0 at ±40%.
    delta = abs(length_nt - target_nt) / float(target_nt)
    if delta <= 0.25:
        return 1.0
    if delta >= 0.40:
        return 0.0
    return 1.0 - (delta - 0.25) / (0.40 - 0.25)


def unpaired_band_score(
    unpaired: Optional[float], *, low: float = 0.30, mid: float = 0.50, high: float = 0.70
) -> float:
    """Triangle peak at ``mid``; 0 outside [low, high].

    A moderate unpaired fraction is preferred: too low means excessive
    secondary-structure folding, too high means the CDS is structurally
    too loose.
    """
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
    target_length_nt: Optional[int],
    unpaired_fraction: Optional[float] = None,
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
        "target_length_nt": target_length_nt,
        "unpaired_fraction": unpaired_fraction,
    }


def score_mrna_candidate(
    bundle: Mapping[str, Any],
    *,
    weights: Optional[MrnaScoreWeights] = None,
    target_length_nt: Optional[int] = None,
    gc_low: float = 0.42,
    gc_mid: float = 0.50,
    gc_high: float = 0.58,
) -> Dict[str, float]:
    """Return component scores and ``total_score`` in [0, 1].

    ``bundle`` should include keys from ``compute_mrna_metric_bundle`` or compatible.
    """

    w = (weights or MrnaScoreWeights()).normalized()

    gc = float(bundle.get("gc_content", 0.0))
    length_nt = int(bundle.get("sequence_length", 0))
    mfe_raw = bundle.get("mfe_kcal_per_mol")
    unpaired_raw = bundle.get("unpaired_fraction")
    tl_raw = (
        target_length_nt
        if target_length_nt is not None
        else bundle.get("target_length_nt")
    )
    tl: Optional[int] = int(tl_raw) if isinstance(tl_raw, int) else None

    gc_c = gc_band_score(gc, low=gc_low, mid=gc_mid, high=gc_high)
    mfe_c = mfe_stability_component(
        _optional_float(mfe_raw), sequence_length=length_nt if length_nt > 0 else None
    )
    unp_c = unpaired_band_score(_optional_float(unpaired_raw))
    len_c = length_target_score(length_nt, target_nt=tl)

    total = w.gc * gc_c + w.mfe * mfe_c + w.unpaired * unp_c + w.length * len_c
    return {
        "gc_component": float(gc_c),
        "mfe_component": float(mfe_c),
        "unpaired_component": float(unp_c),
        "length_component": float(len_c),
        "total_score": float(total),
        "mfe_per_nt": bundle.get("mfe_per_nt"),
    }
