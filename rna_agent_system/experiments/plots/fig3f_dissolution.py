#!/usr/bin/env python3
"""Fig. 3f — Confounded improvement: the coordination-loop apparent effect
dissolves under pre-registered controls (annotated slope + gate +
null-distribution histogram inset, observed δ marked).

Main axes: Cliff's δ trajectory of the EGARPS-component best-of-pool
coordination advantage across the three pre-registered comparisons — the
apparent advantage (coordination loop vs serial, unequal budget), the
budget-matched control (vs one-pass 16-candidate serial) and the
fixed-resampling control (vs forced content-free regeneration) — with the
GO gate δ = 0.3 dashed (the P0/P3 convention) and per-stage
δ / P printed above each dot. Inset: the sign-flip null distribution (10^4)
of the apparent effect with the observed δ marked (the Robin Extended Data
Fig. 4c convention) — the effect is real-looking precisely because the
budget confound is real; the controls, not the loop, carry it.

2026-10-02 revision (Fig. 3 text-sync batch, user-adjudicated): the on-panel
text synced to the polished body/caption vocabulary — stage labels
"Apparent effect"/"Budget-matched" → "Apparent advantage"/"Budget matching"
(the caption's nouns), the gate tag "GO gate" → "pre-registered gate" (the
Fig. 3c caption's registered term; the tag moved just below the gate line
on the right, the only clear band at the narrower canvas), the inset head
"permutation null" → "null distribution", and the y-label's "coordination
benefit" → "coordination-loop advantage". The canvas narrowed to
57.2 × 50 mm so d, e and f share one three-column row of the composite
(the user-directed 2026-10-02 layout; fonts unchanged 6-pt, the inset
widened to keep its two text blocks separated, no data change).
2026-10-02 same-day second pass (user-adjudicated): the inset head
plain-worded to "no real effect (10⁴ sign flips)" (the legend carries
nothing about the inset, so the panel text decodes itself; "null
distribution" retired after one render); the canvas narrowed again to
55.8 mm and the x-limits widened to (−0.45, 2.45) so the apparent-advantage
label stays inside the left spine (the figure's moderate-narrowing pass).
2026-10-10 revision (Fig. 3 row-3 alignment batch, user-directed): the
canvas and axes moved to the shared exact-millimetre row-3 geometry
(`fig3_row3_layout.py` — 54.0 x 52.0 mm canvas, axes 12.0/12.0/41.0/36.0,
identical with panels d and e so the three axes land on the same lines at
assembly; the audited 36 mm axes height is what the shared rectangle
adopts) and the tight-crop save retired (the figS house convention); the
axes narrow 43.9 → 41.0 mm, fonts unchanged 6-pt, no data change.

2026-08-31 user-directed repair: every text element pure black #000000 (the
fig3e convention — the gate tag had been dark warm grey and the observed-δ
tag terracotta, the rest palette-TEXT #1A1A1A); the two in-figure
title-like strings removed (Nature style — the italic "n = 56 paired cells;
self-audit claim survival 0/2" summary line and the "δ null, apparent
effect" inset title; both facts already live in the Fig-3f caption); the
inset moved to a fixed upper-left rect audited against the frozen summary
so it clears the gate line, every stage dot and every two-line stage label
(the earlier quadrant-adaptive placement scored only dots/lines and covered
the apparent-effect label); the inset's two text blocks horizontally
separated so neither white halo clips the other (the permutation-null block
had covered the leading glyphs of the observed-δ label).

Colours (palette rev 7): stage dots — terracotta (apparent / confounded),
grey blue (budget-matched), sage (fixed-resampling); connecting line warm
grey; gate line dark warm grey dashed (the fig3a/fig3b gate convention);
zero line neutral grid grey; null bars warm grey with the observed-δ marker
line terracotta. All text ink black.

Style: the fig2d–fig3h conventions — no in-figure title (the headline lives
in the caption), every text element one 6-pt font size and pure black,
single-column geometry, 1200-dpi PNG.

Data  : experiments/results/exp16_confounded_improvement/summary.json
Usage : python experiments/plots/fig3f_dissolution.py
Output: experiments/plots/output/fig3f_dissolution.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig3_row3_layout import (  # noqa: E402
    AX_B_MM, AX_H_MM, AX_L_MM, AX_W_MM, CANVAS_H_MM, CANVAS_W_MM)
from palette import NEUTRAL_GRID, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp16_confounded_improvement"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6
INK = "#000000"   # fig3e convention: every text element pure black
C_APPARENT = PALETTE_BY_NAME["terracotta"]      # #C08B7C — the confounded claim
C_BUDGET = PALETTE_BY_NAME["grey_blue"]         # #8FA6BB — budget-matched control
C_FIXED = PALETTE_BY_NAME["sage_green"]         # #A3B18A — fixed-resampling control
C_LINE = PALETTE_BY_NAME["warm_grey"]           # #B7B0A2 — trajectory line / null bars
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]      # #7A7672 — gate line (fig3a/3b)
C_REF = NEUTRAL_GRID

STAGES = [
    ("apparent", "Apparent\nadvantage", C_APPARENT),
    ("budget_matched", "Budget\nmatching", C_BUDGET),
    ("fixed_resampling", "Fixed\nresampling", C_FIXED),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
})


def p_str(p: float | None) -> str:
    if p is None:
        return "P = NA"
    if p >= 0.01:
        return f"P = {p:.2f}"
    return f"P = {p:.1e}".replace("e-0", "e\u2212").replace("e-", "e\u2212")


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp16_confounded_improvement.py first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    an = s["analyses"]

    vals = [an[k]["delta"] for k, _, _ in STAGES]
    ps = [an[k].get("p_wilcoxon") for k, _, _ in STAGES]

    # shared row-3 geometry (fig3_row3_layout.py) — exact canvas, no tight
    # crop, so the axes rectangle is identical in panels d, e and f
    fig_w, fig_h = CANVAS_W_MM / 25.4, CANVAS_H_MM / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    ax = fig.add_axes([AX_L_MM / CANVAS_W_MM, AX_B_MM / CANVAS_H_MM,
                       AX_W_MM / CANVAS_W_MM, AX_H_MM / CANVAS_H_MM])

    xs = [0, 1, 2]
    ax.plot(xs, vals, color=C_LINE, linewidth=0.9, zorder=2)
    ax.scatter(xs, vals, s=20, c=[c for _, _, c in STAGES],
               edgecolors="white", linewidths=0.4, zorder=3)

    gate = s.get("gate_delta", 0.3)
    y_lo, y_hi = -0.12, 0.66
    ax.axhline(gate, color=C_GATE, linewidth=0.7, linestyle=(0, (3, 2)), zorder=1)
    # the tag sits just below the gate line on the right — at the narrowed
    # canvas the inset owns the upper left and the right-anchored "gate"
    # wording no longer fits above the line beside it
    ax.text(0.985, gate - 0.018, f"gate δ ≥ {gate:.1f}",
            fontsize=FONT, ha="right", va="top", color=INK,
            transform=ax.get_yaxis_transform())
    ax.axhline(0, color=C_REF, linewidth=0.5, zorder=1)

    for x, (v, p) in enumerate(zip(vals, ps)):
        ax.text(x, v + 0.035, f"δ = {v:+.2f}\n{p_str(p)}",
                fontsize=FONT, ha="center", va="bottom", color=INK, zorder=5)

    ax.set_xlim(-0.45, 2.45)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xticks(xs)
    ax.set_xticklabels([lab for _, lab, _ in STAGES])
    ax.set_ylabel("Cliff's δ, coordination-loop advantage")
    ax.tick_params(length=1.5, width=0.5, pad=1.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # ── inset: permutation null of the apparent effect, observed δ marked ──
    null = an["apparent"].get("perm_null") or {}
    obs = vals[0]
    if null.get("hist"):
        hist = null["hist"]
        counts = [c for _, c in hist]
        centers = [c for c, _ in hist]
        x_obs = sum(1 for c in centers if c < obs) - 0.5

        # Fixed upper-left rect (axes fraction), audited against the frozen
        # summary: bottom edge at data y = 0.329 sits above the gate line and
        # the apparent-advantage label; the right edge clears the stage dots;
        # no stage dot, label, or reference line is covered. 2026-10-02:
        # widened 0.58 → 0.70 of the narrower axes so the two text blocks
        # keep their horizontal separation.
        axi = ax.inset_axes([0.03, 0.575, 0.70, 0.39], transform=ax.transAxes)

        axi.bar(range(len(counts)), counts, width=1.0, color=C_LINE,
                edgecolor="none", zorder=2)
        axi.axvline(x_obs, color=C_APPARENT, linewidth=1.1, zorder=4)
        # observed-δ label right of the marker line in an empty headroom band
        # (the xlim extends 14 bins past the last bar); at the narrowed 2026-10-02
        # canvas the old left-of-line top placement sat within halo reach of the
        # null-distribution block
        axi.text(x_obs + 1.2, max(counts) * 0.97,
                 f"observed\nδ = {obs:+.2f}", fontsize=FONT,
                 ha="left", va="top",
                 color=INK, zorder=5,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
        axi.text(0.03, 0.97,
                 f"no real effect\n($10^4$ sign flips)\n{p_str(null.get('p_perm'))}",
                 transform=axi.transAxes, fontsize=FONT, ha="left", va="top",
                 color=INK, zorder=4,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
        axi.set_xlim(-0.8, len(counts) - 0.2 + 14)
        axi.set_ylim(0, max(counts) * 1.15)
        axi.set_yticks([])
        axi.set_xticks([])
        axi.tick_params(length=0, pad=0)
        for spine in axi.spines.values():
            spine.set_linewidth(0.4)
            spine.set_color(INK)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        # exact-canvas save (no tight crop) — the row-3 alignment convention
        fig.savefig(OUT_DIR / f"fig3f_dissolution.{ext}",
                    dpi=1200 if ext == "png" else None,
                    facecolor="white")
    print(f"written: {OUT_DIR}/fig3f_dissolution.{{pdf,png}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
