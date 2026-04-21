"""Simple mRNA ranking scores built from tool metrics + sequence-derived features.

Weights and normalization rules are explicit so other workflows (UTR, circRNA, intron) can reuse
the same helper pattern with different ``MrnaScoreWeights``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class MrnaScoreWeights:
    """Default weights for ``total_score`` (components are in [0, 1])."""

    gc: float = 0.40
    mfe: float = 0.35
    length: float = 0.25

    def normalized(self) -> MrnaScoreWeights:
        """Scale weights to sum to 1.0."""

        s = self.gc + self.mfe + self.length
        if s <= 0:
            return MrnaScoreWeights(gc=1.0 / 3, mfe=1.0 / 3, length=1.0 / 3)
        return MrnaScoreWeights(gc=self.gc / s, mfe=self.mfe / s, length=self.length / s)


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
    g = sequence.count("G")
    c = sequence.count("C")
    return (g + c) / float(len(sequence))


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


def mfe_stability_component(mfe_kcal_per_mol: Optional[float]) -> float:
    """Map folding energy (kcal/mol, typically negative) to [0, 1].

    Rule (documented): treat more negative MFE as more favorable for this minimal scorer
    (secondary-structure stability proxy). Missing / NaN → **0.45** (slightly below neutral)
    so failed folds do not dominate ranking.

    Linear map: ``mfe=-50`` → ~1.0, ``mfe=-5`` → ~0.1, clipped.
    """

    if mfe_kcal_per_mol is None:
        return 0.45
    try:
        mfe = float(mfe_kcal_per_mol)
    except (TypeError, ValueError):
        return 0.45
    # (-mfe - 5) / 45 maps roughly [-50,-5] into [1, 0]
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


def compute_mrna_metric_bundle(
    *,
    sequence: str,
    gc_from_tools: Optional[float],
    sequence_length_from_tools: Optional[int],
    mfe_kcal_per_mol: Optional[float],
    target_length_nt: Optional[int],
) -> Dict[str, Any]:
    """Collect canonical keys used by scoring and summaries."""

    gc_local = gc_fraction_from_sequence(sequence)
    gc_eff = gc_from_tools if gc_from_tools is not None else gc_local
    length_eff = sequence_length_from_tools if sequence_length_from_tools is not None else len(sequence)
    return {
        "gc_content": float(gc_eff),
        "gc_content_local": float(gc_local),
        "sequence_length": int(length_eff),
        "mfe_kcal_per_mol": mfe_kcal_per_mol,
        "target_length_nt": target_length_nt,
    }


def score_mrna_candidate(
    bundle: Mapping[str, Any],
    *,
    weights: Optional[MrnaScoreWeights] = None,
    target_length_nt: Optional[int] = None,
) -> Dict[str, float]:
    """Return component scores and ``total_score`` in [0, 1].

    ``bundle`` should include keys from ``compute_mrna_metric_bundle`` or compatible.
    """

    w = (weights or MrnaScoreWeights()).normalized()

    gc = float(bundle.get("gc_content", 0.0))
    length_nt = int(bundle.get("sequence_length", 0))
    mfe_raw = bundle.get("mfe_kcal_per_mol")
    tl_raw = target_length_nt if target_length_nt is not None else bundle.get("target_length_nt")
    tl: Optional[int] = int(tl_raw) if isinstance(tl_raw, int) else None

    gc_c = gc_band_score(gc)
    mfe_c = mfe_stability_component(_optional_float(mfe_raw))
    len_c = length_target_score(length_nt, target_nt=tl)

    total = w.gc * gc_c + w.mfe * mfe_c + w.length * len_c
    return {
        "gc_component": float(gc_c),
        "mfe_component": float(mfe_c),
        "length_component": float(len_c),
        "total_score": float(total),
    }
