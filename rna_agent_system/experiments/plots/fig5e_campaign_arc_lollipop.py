"""Fig 5e — Aptamer campaign arc: discordance and exact McNemar P per
campaign, with the pre-registered lever ladder labelled (Experiment 29).

One lollipop pair per campaign (x): the navigation-only discordant cells b
(sage stem-and-head) and the rule-only discordant cells c (terracotta), with
the exact two-sided McNemar P annotated above each pair and the campaign's
cell count n in the tick block.  The four campaigns follow the arc order —
initial migration (delivery-easy matrix v0, sparse lattice, mechanized
reinforcement only) → re-anchoring (production scarce matrix v3, densified
lattice, S1-measured priors) → decisive (the shipped production mode with
cycling guaranteed-repair allocation; the pre-registered primary endpoint
panel) → confirmation (the scarcity-complement panel; Fig 6f data).  The
pooled decisive+confirmation discordance is annotated when both segments are
present.  Rows are lollipop stems from zero; heads carry the counts.

Style (the fig5b/5c house style): no in-figure title — the panel letter is
added at assembly; every text element one 6-pt pure-black style; colours
exclusively from palette rev 7; absolute-mm geometry, single column;
1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/arc.json
Usage : python experiments/plots/fig5e_campaign_arc_lollipop.py
Output : experiments/plots/output/fig5e_campaign_arc_lollipop.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARC = (PROJECT_ROOT / "experiments" / "results"
       / "exp29_aptamer_campaign_arc" / "arc.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 58.0

C_NAV = PALETTE_BY_NAME["sage_green"]    # navigation-only discordance (b)
C_RULE = PALETTE_BY_NAME["terracotta"]   # rule-only discordance (c)
C_POOL = PALETTE_BY_NAME["grey_blue"]    # pooled annotation

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

SEGMENTS = [
    ("seg1_migration", "Initial\nmigration",
     "matrix v0 · sparse\nlattice · mechanized"),
    ("seg2_reanchor", "Re-\nanchoring",
     "matrix v3 · densified\nlattice · S1 priors"),
    ("seg3_decisive", "Decisive\n(primary)",
     "+ guaranteed repair\n(production mode)"),
    ("seg4_confirmation", "Confirm-\nation",
     "scarcity-complement\npanel"),
]


def fmt_p(p: float) -> str:
    if p >= 0.01:
        return f"P = {p:.3f}".rstrip("0").rstrip(".")
    return f"P = {p:.2e}" if p > 0 else "P < 1e-300"


def main() -> int:
    arc = json.loads(ARC.read_text(encoding="utf-8"))
    segs = arc["segments"]

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.085, 0.235, 0.905, 0.62])
    ymax = 1
    xs: list[float] = []
    for i, (key, _, _) in enumerate(SEGMENTS):
        v = segs.get(key)
        if v is None:
            continue
        x = i
        xs.append(x)
        b = v["mcnemar"]["b_nav_only"]
        c_ = v["mcnemar"]["c_rule_only"]
        p = v["mcnemar"]["p_exact"]
        ymax = max(ymax, b, c_)
        for dx, val, color in ((-0.10, b, C_NAV), (0.10, c_, C_RULE)):
            ax.plot([x + dx, x + dx], [0, val], color=color, lw=1.1,
                    solid_capstyle="butt", zorder=2)
            ax.plot(x + dx, val, "o", ms=2.8, mfc=color, mec=color, zorder=3)
        ax.annotate(f"b = {b}   c = {c_}",
                    (x, max(b, c_)), textcoords="offset points",
                    xytext=(0, 3), ha="center", fontsize=FONT, color=INK)
        ax.annotate(fmt_p(p), (x, max(b, c_)), textcoords="offset points",
                    xytext=(0, 10.5), ha="center", fontsize=FONT, color=INK)
        go = (v.get("go_rule") or {}).get("verdict")
        if go == "GO":
            ax.annotate("GO", (x, max(b, c_)), textcoords="offset points",
                        xytext=(0, 18), ha="center", fontsize=FONT, color=INK)
    ax.set_xlim(-0.62, len(SEGMENTS) - 0.38)
    ax.set_ylim(0, ymax * 1.42 + 1.0)
    ax.set_xticks([i for i in range(len(SEGMENTS))])
    ax.set_xticklabels(
        [f"{name}\n{lever}\nn = {segs[key]['n_cells']} cells"
         if key in segs else name
         for key, name, lever in SEGMENTS],
        fontsize=FONT, linespacing=1.25)
    ax.set_ylabel("Discordant cells", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # pooled decisive + confirmation annotation (bottom-right text block)
    pooled = arc.get("pooled_seg3_seg4")
    if pooled:
        ax.annotate(
            f"pooled decisive + confirmation: "
            f"b = {pooled['b']} : c = {pooled['c']}, "
            f"{fmt_p(pooled['p_exact'])}",
            xy=(1.0, -0.315), xycoords="axes fraction",
            ha="right", va="top", fontsize=FONT, color=INK)

    # key: swatch + label row, renderer-measured (fig4g/5c convention)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [(C_NAV, "navigation-only (b)"),
                 (C_RULE, "rule-only (c)")]
    swatch_w = 0.014
    gap_in, gap_out = 0.006, 0.024
    parts: list[tuple[str, object]] = []
    for color, label in key_items:
        parts.append(("swatch", color))
        parts.append(("label", label))
    widths = [swatch_w + gap_in if k == "swatch" else
              text_w(v) + gap_out for k, v in parts]
    total_w = sum(widths)
    assert total_w < 0.90, f"key row overflows canvas: {total_w:.3f}"
    x = 0.5 - total_w / 2
    y = 0.045
    for (kind, val), w in zip(parts, widths):
        if kind == "swatch":
            ax = fig.add_axes([x, y - 0.008, swatch_w, 0.014])
            ax.set_xticks([]), ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
            ax.set_facecolor(val)
        else:
            fig.text(x, y - 0.003, val, fontsize=FONT, color=INK,
                     va="center_baseline")
        x += w

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5e_campaign_arc_lollipop.{ext}", dpi=1200)
    plt.close(fig)
    summary = ", ".join(
        f"{key.split('_')[0]}: b{v['mcnemar']['b_nav_only']}"
        f"/c{v['mcnemar']['c_rule_only']}"
        for key, v in segs.items())
    print(f"wrote fig5e_campaign_arc_lollipop ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
