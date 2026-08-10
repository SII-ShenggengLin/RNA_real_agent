#!/usr/bin/env python3
"""Shared statistics utilities for the RNADesignAgent manuscript experiments.

Implements the conventions in `docs/MANUSCRIPT.md` §13:
- paired comparisons: two-sided Wilcoxon signed-rank + Cliff's delta
- multiple comparisons: Benjamini-Hochberg FDR
- AUROC: bootstrap 95 % CI (10 000 resamples)
"""
from __future__ import annotations

import math
import random

import numpy as np
from scipy import stats


def wilcoxon_paired(x: list[float], y: list[float]) -> float:
    """Two-sided Wilcoxon signed-rank p-value for paired samples (equal length).

    Falls back to NaN when all differences are zero (test undefined).
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    assert len(x) == len(y) and len(x) > 0
    if np.all(x == y):
        return float("nan")
    return float(stats.wilcoxon(x, y, alternative="two-sided").pvalue)


def cliffs_delta(x: list[float], y: list[float]) -> float:
    """Cliff's delta effect size of x vs y (positive = x tends larger)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n_x, n_y = len(x), len(y)
    if n_x == 0 or n_y == 0:
        return float("nan")
    gt = sum(1 for a in x for b in y if a > b)
    lt = sum(1 for a in x for b in y if a < b)
    return (gt - lt) / (n_x * n_y)


def bh_fdr(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted q-values, NaN-safe (NaNs stay NaN at the end)."""
    arr = np.asarray(pvalues, dtype=float)
    q = np.full_like(arr, np.nan)
    valid = ~np.isnan(arr)
    if valid.sum() == 0:
        return q.tolist()
    q[valid] = stats.false_discovery_control(arr[valid], method="bh")
    return q.tolist()


def mannwhitney_p(x: list[float], y: list[float]) -> float:
    """Two-sided Mann-Whitney U p-value."""
    if not x or not y:
        return float("nan")
    return float(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)


def auroc(pos: list[float], neg: list[float]) -> float:
    """Rank-based AUROC (probability a positive scores above a negative)."""
    pos, neg = list(pos), list(neg)
    if not pos or not neg:
        return float("nan")
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
    """AUROC with bootstrap 95 % CI over (pos, neg) pairs resampling."""
    pos, neg = list(pos), list(neg)
    point = auroc(pos, neg)
    if not pos or not neg:
        return (float("nan"),) * 3
    rng = random.Random(seed)
    boot = []
    for _ in range(n_boot):
        ps = [pos[rng.randrange(len(pos))] for _ in pos]
        ns = [neg[rng.randrange(len(neg))] for _ in neg]
        boot.append(auroc(ps, ns))
    boot.sort()
    lo = boot[int(0.025 * n_boot)]
    hi = boot[min(int(0.975 * n_boot), n_boot - 1)]
    return point, lo, hi


def median_iqr(values: list[float]) -> tuple[float, float, float]:
    """Median and interquartile range."""
    v = np.asarray([x for x in values if x is not None and not math.isnan(x)], dtype=float)
    if len(v) == 0:
        return (float("nan"),) * 3
    return float(np.median(v)), float(np.percentile(v, 25)), float(np.percentile(v, 75))
