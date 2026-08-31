#!/usr/bin/env python3
"""Fig. 3i — Confounded improvement: the coordination-loop apparent effect
dissolves under pre-registered controls (annotated slope + gate +
permutation-null histogram inset, observed δ marked).

Main axes: Cliff's δ trajectory of the EGARPS-component best-of-pool
coordination benefit across the three pre-registered comparisons — the
apparent effect (coordination loop vs serial, unequal budget), the
budget-matched control (vs one-pass 16-candidate serial) and the
fixed-resampling control (vs forced content-free regeneration) — with the
pre-registered GO gate δ = 0.3 dashed (the P0/P3 convention) and per-stage
δ / P printed above each dot. Inset: the sign-flip permutation null (10^4)
of the apparent effect with the observed δ marked (the Robin Extended Data
Fig. 4c convention) — the effect is real-looking precisely because the
budget confound is real; the controls, not the loop, carry it. The inset
is placed in the data-emptiest corner so it never covers a stage dot,
its printed values or the gate line.

Colours (palette rev 7): stage dots — terracotta (apparent / confounded),
grey blue (budget-matched), sage (fixed-resampling); connecting line warm
grey; gate line dark warm grey dashed (the fig3b/fig3c gate convention);
zero line neutral grid grey; null bars warm grey with the observed-δ marker
line terracotta.

Style: the fig2d–fig3h conventions — no in-figure title (the headline lives
in the caption), every text element one font size and ink black,
single-column geometry.

Data  : experiments/results/exp16_confounded_improvement/summary.json
Usage : python experiments/plots/fig3i_dissolution.py
Output: experiments/plots/output/fig3i_dissolution.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp16_confounded_improvement"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6
C_APPARENT = PALETTE_BY_NAME["terracotta"]      # #C08B7C — the confounded claim
C_BUDGET = PALETTE_BY_NAME["grey_blue"]         # #8FA6BB — budget-matched control
C_FIXED = PALETTE_BY_NAME["sage_green"]         # #A3B18A — fixed-resampling control
C_LINE = PALETTE_BY_NAME["warm_grey"]           # #B7B0A2 — trajectory line / null bars
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]      # #7A7672 — gate line (fig3b/3c)
C_REF = NEUTRAL_GRID

STAGES = [
    ("apparent", "Apparent\neffect", C_APPARENT),
    ("budget_matched", "Budget-\nmatched", C_BUDGET),
    ("fixed_resampling", "Fixed\nresampling", C_FIXED),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
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
    n_pairs = an[STAGES[0][0]]["n_pairs"]
    survival = s["self_audit"]["survival"]

    fig_w, fig_h = 88 / 25.4, 58 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    # main axes (mm geometry)
    x0_mm, w_mm, y0_mm, h_mm = 14, 69, 13, 33
    ax = fig.add_axes([x0_mm / 25.4 / fig_w, y0_mm / 25.4 / fig_h,
                       w_mm / 25.4 / fig_w, h_mm / 25.4 / fig_h])

    xs = [0, 1, 2]
    ax.plot(xs, vals, color=C_LINE, linewidth=0.9, zorder=2)
    ax.scatter(xs, vals, s=20, c=[c for _, _, c in STAGES],
               edgecolors="white", linewidths=0.4, zorder=3)

    gate = s.get("gate_delta", 0.3)
    y_lo, y_hi = -0.12, 0.66
    ax.axhline(gate, color=C_GATE, linewidth=0.7, linestyle=(0, (3, 2)), zorder=1)
    ax.text(0.985, gate + 0.012, f"GO gate δ ≥ {gate:.1f}", fontsize=FONT,
            ha="right", va="bottom", color=C_GATE, transform=ax.get_yaxis_transform())
    ax.axhline(0, color=C_REF, linewidth=0.5, zorder=1)

    for x, (v, p) in enumerate(zip(vals, ps)):
        above = v < gate - 0.06  # keep the two-line label clear of the gate line
        ax.text(x, v + (0.035 if above else 0.035), f"δ = {v:+.2f}\n{p_str(p)}",
                fontsize=FONT, ha="center",
                va="bottom" if above else "bottom", color=TEXT, zorder=5)

    ax.set_xlim(-0.35, 2.45)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xticks(xs)
    ax.set_xticklabels([lab for _, lab, _ in STAGES])
    ax.set_ylabel("Cliff's δ, coordination benefit")
    ax.tick_params(length=1.5, width=0.5, pad=1.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.text(0.0, 1.05, f"n = {n_pairs} paired cells; self-audit claim survival {survival}",
            transform=ax.transAxes, fontsize=FONT, ha="left", va="bottom",
            color=TEXT, style="italic")

    # ── inset: permutation null of the apparent effect, observed δ marked ──
    null = an["apparent"].get("perm_null") or {}
    obs = vals[0]
    if null.get("hist"):
        hist = null["hist"]
        counts = [c for _, c in hist]
        centers = [c for c, _ in hist]
        width = (centers[1] - centers[0]) if len(centers) > 1 else 0.02
        x_obs = sum(1 for c in centers if c < obs) - 0.5

        # data-emptiest corner for the inset (never over dots, labels or gate)
        iw, ih = 0.46, 0.52  # axes fraction
        corners = {
            "upper left": (0.07, 0.97, "left", "top"),
            "upper right": (0.93, 0.97, "right", "top"),
            "lower left": (0.07, 0.06, "left", "bottom"),
            "lower right": (0.93, 0.06, "right", "bottom"),
        }
        def occupancy(key: str) -> float:
            fx, fy, hx, hy = corners[key]
            cx = -0.35 + fx * 2.8
            cy = y_lo + fy * (y_hi - y_lo)
            score = 0.0
            for v in vals:
                score += max(0.0, 1.2 - abs(v - cy) / 0.5)  # dot rows
            score += max(0.0, 1.0 - abs(gate - cy) / 0.15) * 0.8  # gate line
            score += max(0.0, 1.0 - abs(0.0 - cy) / 0.1) * 0.4    # zero line
            # stage label columns are near x = 0/1/2 — the inset mid-x matters less
            return score

        placement = min(corners, key=occupancy)
        fx, fy, hx, hy = corners[placement]
        axi = ax.inset_axes([fx if hx == "left" else fx - iw, fy - ih if hy == "top" else fy,
                             iw, ih], transform=ax.transAxes)

        axi.bar(range(len(counts)), counts, width=1.0, color=C_LINE,
                edgecolor="none", zorder=2)
        axi.axvline(x_obs, color=C_APPARENT, linewidth=1.1, zorder=4)
        # observed-δ label with a white halo, anchored inside the inset
        label_right = x_obs > len(counts) * 0.6
        axi.text(x_obs - 0.6 if label_right else x_obs + 0.6, max(counts) * 0.97,
                 f"observed\nδ = {obs:+.2f}", fontsize=FONT,
                 ha="right" if label_right else "left", va="top",
                 color=C_APPARENT, zorder=5,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
        axi.text(0.03, 0.97, f"permutation null\n($10^4$ sign flips)\n{p_str(null.get('p_perm'))}",
                 transform=axi.transAxes, fontsize=FONT, ha="left", va="top",
                 color=TEXT, zorder=5,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0})
        axi.set_xlim(-0.8, len(counts) - 0.2)
        axi.set_ylim(0, max(counts) * 1.15)
        axi.set_yticks([])
        axi.set_xticks([])
        axi.tick_params(length=0, pad=0)
        for spine in axi.spines.values():
            spine.set_linewidth(0.4)
            spine.set_color(C_GATE)
        axi.set_title("δ null, apparent effect", fontsize=FONT, pad=1.5, color=TEXT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig3i_dissolution.{ext}",
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    print(f"written: {OUT_DIR}/fig3i_dissolution.{{pdf,png}} (inset at {placement if null.get('hist') else 'n/a'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
