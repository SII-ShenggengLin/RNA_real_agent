"""Profiling metrics for capability grading (CASF four capabilities).

Consumes profiling rows in the E1 driver schema (Part A sequence-level rows,
Part B pose-level rows) and computes the pre-registered metrics:
screening -> AUROC (+ bootstrap CI), ranking -> Spearman rho,
docking -> top-1 native-pose identification rate.

Thresholds mirror the E1 extension analysis convention
(AUROC > 0.8, rho >= 0.6, top-1 >= 2/3) and are overridable.
Deterministic; no LLM.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Iterable

from scipy.stats import spearmanr

_LOGGER = logging.getLogger(__name__)

AUROC_PASS = 0.8
RHO_PASS = 0.6
DOCK_PASS_FRAC = 2.0 / 3.0

_BINDER_ROLES = ("binder", "binder_no_kd")


def _auroc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUROC (probability a positive scores above a negative)."""
    wins = ties = 0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def bootstrap_auroc_ci(
    pos: list[float],
    neg: list[float],
    *,
    n_boot: int = 10_000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """AUROC with bootstrap 95 % CI over (pos, neg) pairs resampling.

    Inlined verbatim from the deleted ``experiments/analysis/stats_utils.py``
    (2026-08-25 reset) so the calibrated stack stays self-contained.
    """
    pos, neg = list(pos), list(neg)
    if not pos or not neg:
        return (float("nan"),) * 3
    point = _auroc(pos, neg)
    rng = random.Random(seed)
    boot = []
    for _ in range(n_boot):
        ps = [pos[rng.randrange(len(pos))] for _ in pos]
        ns = [neg[rng.randrange(len(neg))] for _ in neg]
        boot.append(_auroc(ps, ns))
    boot.sort()
    lo = boot[int(0.025 * n_boot)]
    hi = boot[min(int(0.975 * n_boot), n_boot - 1)]
    return point, lo, hi


def _score(row: dict[str, Any], oracle_key: str) -> float | None:
    raw = row.get("raw") or {}
    val = raw.get(oracle_key)
    return float(val) if val is not None else None


def screening_metrics(rows: Iterable[dict[str, Any]], oracle_key: str) -> dict[str, float]:
    """AUROC of *oracle_key* separating binders from negatives."""
    pos: list[float] = []
    neg: list[float] = []
    for row in rows:
        if not row.get("success"):
            continue
        val = _score(row, oracle_key)
        if val is None:
            continue
        if row.get("role") in _BINDER_ROLES:
            pos.append(val)
        elif row.get("role") == "negative":
            neg.append(val)
    if not pos or not neg:
        return {"auroc": float("nan"), "auroc_ci_lo": float("nan"), "auroc_ci_hi": float("nan"),
                "n_pos": float(len(pos)), "n_neg": float(len(neg))}
    point, lo, hi = bootstrap_auroc_ci(pos, neg)
    return {
        "auroc": point,
        "auroc_ci_lo": lo,
        "auroc_ci_hi": hi,
        "n_pos": float(len(pos)),
        "n_neg": float(len(neg)),
    }


def ranking_metrics(rows: Iterable[dict[str, Any]], oracle_key: str) -> dict[str, float]:
    """Spearman rho of *oracle_key* vs -log10(Kd) on ranking-eligible binders."""
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        if not row.get("success") or not row.get("ranking_eligible"):
            continue
        kd = row.get("kd_nm")
        if row.get("role") not in _BINDER_ROLES or kd is None:
            continue
        val = _score(row, oracle_key)
        if val is None:
            continue
        xs.append(val)
        ys.append(-math.log10(float(kd)))
    if len(xs) < 3:
        return {"spearman_rho": float("nan"), "n": float(len(xs))}
    rho = float(spearmanr(xs, ys).statistic)
    return {"spearman_rho": rho, "n": float(len(xs))}


def docking_metrics(rows: Iterable[dict[str, Any]], oracle_key: str = "egarps_native_probability") -> dict[str, float]:
    """Top-1 native identification rate, per docking anchor.

    Rows carry ``anchor`` / ``kind`` (native|decoy) / score. For each anchor the
    native pose must rank first among all successful poses to count as a hit.
    """
    by_anchor: dict[str, list[tuple[float, str]]] = {}
    for row in rows:
        if not row.get("success"):
            continue
        val = _score(row, oracle_key) if "raw" in row else row.get(oracle_key)
        if val is None:
            continue
        by_anchor.setdefault(str(row.get("anchor")), []).append((float(val), str(row.get("kind"))))
    if not by_anchor:
        return {"docking_top1_rate": float("nan"), "n_anchors": 0.0}
    hits = 0
    for anchor in sorted(by_anchor):
        poses = sorted(by_anchor[anchor], key=lambda t: -t[0])
        if poses and poses[0][1] == "native":
            hits += 1
    return {"docking_top1_rate": hits / len(by_anchor), "n_anchors": float(len(by_anchor))}


def grade_capability(capability: str, metrics: dict[str, float], *,
                     auroc_pass: float = AUROC_PASS,
                     rho_pass: float = RHO_PASS,
                     dock_pass_frac: float = DOCK_PASS_FRAC) -> str | None:
    """Map metrics to ``verified`` / ``failed``; None when not decidable."""
    if capability == "screening":
        val = metrics.get("auroc")
        if val is None or math.isnan(val):
            return None
        return "verified" if val > auroc_pass else "failed"
    if capability == "ranking":
        val = metrics.get("spearman_rho")
        if val is None or math.isnan(val):
            return None
        return "verified" if val >= rho_pass else "failed"
    if capability == "docking":
        val = metrics.get("docking_top1_rate")
        if val is None or math.isnan(val):
            return None
        return "verified" if val >= dock_pass_frac else "failed"
    if capability == "scoring":
        # Scoring power (numeric agreement with experiment) is not graded by
        # this protocol; callers leave it unprofiled.
        return None
    raise ValueError(f"unknown capability: {capability}")
