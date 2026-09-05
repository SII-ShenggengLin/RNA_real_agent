"""Fig 5h — Aptamer navigation cost-delivery curve: the pre-registered
budget sweep (Experiment 29 sweep stage, panel D, 2026-09-04).

Main panel — delivered profile cells (0-36) against the raw generator
budget cap (24 / 32 / 48) for the two arms on the frozen decisive panel:
the shipped navigator (v3b production mode, sage) against the static
band-centre grid under the registered equal-split scaling rule (terracotta;
16/16/16 at 48 reproduces the frozen arc's static arm).  Point markers =
per-cap totals; the paired per-cell discordance annotated at each cap
(b:c, exact McNemar P).  At the tightest cap the navigator delivers 8
cells against the static grid's 3 (b:c = 8:3) — adaptive concentration
beats the starved 8/8/8 split; the arms converge as the budget relaxes
(8:8 at 32, parity at 48).

Inset — the easy-regime cost saving (seg1, loose matrix v0, all 20
targets): identical delivered cells (56 = 56) with the navigator's mean
spend 32.7 against the static arm's fixed 48 (bar pair), the −32%
same-delivery cost saving that motivates the early-stop design.

Style (the fig5b-5g house style): no in-figure title; every text element
one 6-pt pure-black style; colours exclusively from palette rev 7;
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/
        {sweep_curve.json, seg3_decisive/verdict.json,
         seg1_migration/verdict.json}
Usage : python experiments/plots/fig5h_production_navigation_pareto.py
Output : experiments/plots/output/fig5h_production_navigation_pareto.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE = PROJECT_ROOT / "experiments" / "results" / "exp29_aptamer_campaign_arc"
CURVE = BASE / "sweep_curve.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 62.0

C_NAV = PALETTE_BY_NAME["sage_green"]     # navigation arm
C_RULE = PALETTE_BY_NAME["terracotta"]    # static grid arm
C_GRID = "#D9D9D9"

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

MM = 1 / 25.4
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)


def main() -> int:
    # the full expanded-pool curve (39 targets x caps 16-48) + the 20-pool
    # registered-protocol point; both directions of significance annotated
    summary = json.loads((BASE / "expanded_summary.json").read_text(encoding="utf-8"))
    caps = [16, 20, 24, 32, 48]
    nav_y, sta_y, notes = [], [], []
    for cap in caps:
        c = summary["caps"][str(cap)]
        mc = c["mcnemar"]
        nav_y.append(c["delivered"]["C"])
        sta_y.append(c["delivered"]["A"])
        star = "*" if mc["p_exact"] < 0.05 else ""
        notes.append(f"b:c = {mc['b_nav_only']}:{mc['c_rule_only']}{star}\nP = {mc['p_exact']:.3f}")
    v20 = json.loads((BASE / "seg3_decisive" / "verdict.json").read_text())
    mc48_notes = "20-pool 48: 8:9, e2e 4:0"

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.115, 0.315, 0.53, 0.60])
    ax.plot(caps, nav_y, "o-", color=C_NAV, lw=1.1, ms=3.0, zorder=3)
    ax.plot(caps, sta_y, "o-", color=C_RULE, lw=1.1, ms=3.0, zorder=3)
    for cap, y in zip(caps, nav_y):
        ax.annotate(str(y), (cap, y), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=FONT, color=INK)
    for cap, y in zip(caps, sta_y):
        ax.annotate(str(y), (cap, y), textcoords="offset points",
                    xytext=(0, -8), ha="center", fontsize=FONT, color=INK)
    for cap, y_nav, y_sta, note in zip(caps, nav_y, sta_y, notes):
        top = max(y_nav, y_sta)
        ax.annotate(note, (cap, top), textcoords="offset points",
                    xytext=(0, 5), ha="center", fontsize=FONT - 0.5,
                    color=INK, linespacing=1.15)
    ax.set_xlim(13, 53)
    ax.set_ylim(0, 60)
    ax.set_xticks(caps)
    ax.set_xticklabels([str(c) for c in caps])
    ax.set_xlabel("Raw generator budget cap", fontsize=FONT)
    ax.set_ylabel("Delivered cells (of 117, 39 targets)", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── inset: the easy-regime same-delivery cost saving (seg1) ──
    seg1 = json.loads((BASE / "seg1_migration" / "verdict.json")
                      .read_text(encoding="utf-8"))
    axi = fig.add_axes([0.665, 0.40, 0.28, 0.30])
    bars = [("GenNav\n32.7", seg1["budget"]["nav_raw_spent_mean"], C_NAV),
            ("static\n48", 48.0, C_RULE)]
    for i, (label, val, color) in enumerate(bars):
        axi.bar(i, val, width=0.62, facecolor=color, edgecolor="none")
        axi.annotate(label, (i, val), textcoords="offset points",
                     xytext=(0, 2), ha="center", fontsize=FONT, color=INK)
    axi.set_xlim(-0.55, 1.55)
    axi.set_ylim(0, 58)
    axi.set_xticks([])
    axi.set_ylabel("Mean raw spend", fontsize=FONT, labelpad=1.0)
    axi.tick_params(length=1.5, pad=1.2, labelsize=FONT - 0.5)
    axi.set_title("Same delivery\n(56 = 56 cells)", fontsize=FONT,
                  color=INK, pad=2.0)
    for s in axi.spines.values():
        s.set_linewidth(0.4)

    # key row (renderer-measured widths, canvas-overflow assert)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [
        ("line", C_NAV, "GenNav (navigation)"),
        ("line", C_RULE, "static grid (equal split)"),
    ]
    gap = 0.024
    widths = [0.014 + 0.005 + text_w(label) + gap for _, _, label in key_items]
    total_w = sum(widths)
    assert total_w < 0.90, f"key row overflows canvas: {total_w:.3f}"
    x = 0.5 - total_w / 2
    y = 0.055
    for (kind, color, label), w in zip(key_items, widths):
        fig.add_artist(Line2D([x, x + 0.014], [y, y], color=color, lw=1.2))
        fig.text(x + 0.019, y - 0.003, label, fontsize=FONT, color=INK,
                 va="center_baseline")
        x += w

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5h_production_navigation_pareto.{ext}",
                    dpi=1200)
    plt.close(fig)
    print(f"wrote fig5h_production_navigation_pareto "
          f"(cap curve nav {nav_y} vs static {sta_y})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
