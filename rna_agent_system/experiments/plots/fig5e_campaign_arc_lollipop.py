"""Fig 5e — Aptamer campaign arc: discordance and exact McNemar P per
campaign, one lollipop pair per segment (Experiment 29 + Experiment 40
deployment completion).

One lollipop pair per campaign (x): the navigation-only discordant pairs
(sage stem-and-head) and the static-only discordant pairs (terracotta),
with the count printed above each head, the exact two-sided McNemar P
annotated above each pair and the campaign's pair count n beneath the
campaign label.  The five campaigns follow the arc order — delivery-easy
matrix (v0) → scarce matrix (production v3) → delivery-scarce targets
(the shipped production mode; the pre-registered primary endpoint panel)
→ confirmation (the scarcity-complement panel) → deployment (the six
form-entry targets completed by Exp 40).  The key is a one-column legend
inside the axes' upper-left corner.

2026-10-06 follow-up (user-directed): (i) the two pooled strip lines
above the axes deleted — the pooled 26-target result is carried verbatim
by the Fig. 5e legend ("Pooled over 26 targets, navigation delivers 48
pairs to 42 (18:12, P = 0.36)"), so the panel keeps only the per-campaign
annotations; (ii) the panel narrowed 89 → 80.5 mm and shortened 62 →
54 mm (the strip's reservation released) to share the d|e|f group row;
text unchanged at 6 pt, zero number changes.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch): (i)
the "Pooled decisive + confirmation (20 targets)" strip line deleted —
the paper reports the final pooled 26-target result only (the Fig. 5e
legend carries the same single pooled line); (ii) the McNemar b/c
notation decoded — the per-campaign "b = …   c = …" annotation replaced
by the bare counts printed above each lollipop head (the fig5f bar-count
convention) and the key's "(b)"/"(c)" letter tags dropped; (iii) "cells"
→ "pairs" on the y axis and in the pooled strip (the §2.5/legend term);
(iv) the key's "static-grid-only" → "static-only" (the legend's class
name); (v) the campaign labels aligned to the legend's names —
"Initial migration" → "Delivery-easy matrix", "Re-anchoring" → "Scarce
matrix", "Decisive (primary)" → "Delivery-scarce (primary)"; (vi) the
printed P values aligned to the legend verbatim — deployment "P = 0.07"
→ "P = 0.070" and the pooled "P = 0.362" → "P = 0.36"; no frozen number,
colour or geometry changed.

2026-09-08 figure-repair pass (user direction): the five-line tick blocks
(phase name + two lever-ladder descriptor lines + cell count) collided
with the bottom key row and the pooled line, and the phase labels broke
mid-word ("Confirm-ation").  The lever ladder leaves the panel (the
per-campaign levers are stated in §2.5 and the Fig. 5e legend — nothing
lost); the tick blocks are now phase name (natural word breaks) + n; the
pooled note moves from the bottom of the canvas to a reserved strip above
the axes (the fig5b/5d stat-strip convention) and the key becomes a
one-column legend inside the axes' upper-left corner (the seg-1 region
above the two count-1 lollipops is empty), renderer-measured and
collision-asserted; the key label "rule-only" is renamed
"static-grid-only" to match the Fig. 5e legend wording.  All text one
6-pt pure-black style.

Style (the fig3/fig4/fig5a–d house style): no in-figure title — the panel
letter is added at assembly; every text element one 6-pt pure-black style;
colours exclusively from palette rev 7; absolute-mm geometry, single
column; 1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/arc.json
Usage : python experiments/plots/fig5e_campaign_arc_lollipop.py
Output : experiments/plots/output/fig5e_campaign_arc_lollipop.{pdf,png}

2026-10-10 row-alignment polish (user-directed Fig. 5 batch): axes bottom
10.0 -> 9.1 mm and height 41.0 -> 41.9 mm (top edge anchored unchanged at
3.0 mm from the canvas top) so the x-axis spine lands on panel d's spine
line (9.1 mm from the canvas bottom) — row 3's three axes baselines now
align exactly; no number, colour or text change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARC = (PROJECT_ROOT / "experiments" / "results"
       / "exp29_aptamer_campaign_arc" / "arc.json")
POOLED = (PROJECT_ROOT / "experiments" / "results"
          / "exp40_static_completion" / "pooled" / "aptamer_pooled_verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 80.5, 54.0

C_NAV = PALETTE_BY_NAME["sage_green"]    # navigation-only discordance
C_RULE = PALETTE_BY_NAME["terracotta"]   # static-only discordance

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
W_PX = round(W_MM / 25.4 * DPI)   # exact 1200-dpi canvas pixels
H_PX = round(H_MM / 25.4 * DPI)

SEGMENTS = [
    ("seg1_migration", "Delivery-easy\nmatrix"),
    ("seg2_reanchor", "Scarce\nmatrix"),
    ("seg3_decisive", "Delivery-scarce\n(primary)"),
    ("seg4_confirmation", "Confirmation"),
    ("deployment", "Form entry\n(new targets)"),
]

# 2026-10-09 terminology retirement (user-directed, M2 polish round): the
# cohort label "Deployment (new targets)" → "Form entry (new targets)" —
# the entry path names the cohort (§2.5 "entered through the production
# form entry", M2 "entered through the user form"), retiring the third
# name for the same eleven targets and the collision with the registered
# tool sense "deployed tools/service".  The segment key "deployment" stays
# (it addresses the frozen arc.json cohort_splits["deployment_6"]); no
# number, colour or geometry changed.


def fmt_p(p: float) -> str:
    if p >= 0.9995:
        return "P = 1"
    if p >= 0.01:
        return f"P = {p:.3f}"
    return f"P = {p:.2e}" if p > 0 else "P < 1e-300"


def main() -> int:
    arc = json.loads(ARC.read_text(encoding="utf-8"))
    segs = dict(arc["segments"])
    pooled_doc = json.loads(POOLED.read_text(encoding="utf-8"))
    dep = pooled_doc["cohort_splits"]["deployment_6"]["mcnemar"]
    segs["deployment"] = {
        "n_cells": 18,
        "mcnemar": {"b_nav_only": dep["b"], "c_rule_only": dep["c"],
                    "p_exact": dep["p"]},
    }

    # +1e-9 in: defeat float truncation so the saved canvas is exactly
    # W_PX × H_PX (matplotlib takes int(figsize × dpi); the fig5c
    # convention)
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    ax = fig.add_axes([8.0 / W_MM, 9.1 / H_MM, 71.0 / W_MM, 41.9 / H_MM])
    ymax = 1
    for i, (key, _) in enumerate(SEGMENTS):
        v = segs.get(key)
        if v is None:
            continue
        x = i
        b = v["mcnemar"]["b_nav_only"]
        c_ = v["mcnemar"]["c_rule_only"]
        p = v["mcnemar"]["p_exact"]
        ymax = max(ymax, b, c_)
        for dx, val, color in ((-0.10, b, C_NAV), (0.10, c_, C_RULE)):
            ax.plot([x + dx, x + dx], [0, val], color=color, lw=1.1,
                    solid_capstyle="butt", zorder=2)
            ax.plot(x + dx, val, "o", ms=2.8, mfc=color, mec=color, zorder=3)
            ax.annotate(str(val), (x + dx, val), textcoords="offset points",
                        xytext=(0, 2), ha="center", fontsize=FONT, color=INK)
        ax.annotate(fmt_p(p), (x, max(b, c_)), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=FONT, color=INK)
    ax.set_xlim(-0.62, len(SEGMENTS) - 0.38)
    ax.set_ylim(0, max(13.2, ymax + 2.5))
    ax.set_yticks([0, 2, 4, 6, 8, 10, 12])
    ax.set_xticks([i for i in range(len(SEGMENTS))])
    ax.set_xticklabels(
        [f"{name}\nn = {segs[key]['n_cells']}" if key in segs else name
         for key, name in SEGMENTS],
        fontsize=FONT, linespacing=1.25)
    ax.set_ylabel("Discordant pairs", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── legend: one column inside the axes' upper-left corner (the seg-1
    #    region above the two count-1 lollipops is empty) ──
    key_items = [(C_NAV, "navigation-only"),
                 (C_RULE, "static-only")]
    lx, sw_w, sw_h = 0.015, 0.016, 0.020
    for (color, label), yc in zip(key_items, (0.955, 0.885)):
        ax.add_patch(Rectangle((lx, yc - sw_h / 2), sw_w, sw_h,
                               transform=ax.transAxes, facecolor=color,
                               edgecolor="none", zorder=3))
        ax.text(lx + sw_w + 0.008, yc, label,
                transform=ax.transAxes, va="center",
                fontsize=FONT, color=INK)

    # ── renderer-measured guards (the fig5d house pattern): every text
    #    inside the canvas, no text–text collision anywhere ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = (list(ax.texts) + [ax.yaxis.label]
             + list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.x1 <= fig.bbox.width
                and bb.y0 >= 0 and bb.y1 <= fig.bbox.height), \
            f"text overflows canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5e_campaign_arc_lollipop.{ext}", dpi=DPI)
    plt.close(fig)

    img = mpimg.imread(OUT_DIR / "fig5e_campaign_arc_lollipop.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    summary = ", ".join(
        f"{key.split('_')[0]}: b{v['mcnemar']['b_nav_only']}"
        f"/c{v['mcnemar']['c_rule_only']}"
        for key, v in segs.items())
    print(f"wrote fig5e_campaign_arc_lollipop ({summary}; "
          f"{W_MM}x{H_MM} mm, {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
