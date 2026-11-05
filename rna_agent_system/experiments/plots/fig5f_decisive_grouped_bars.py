"""Fig 5f — Aptamer delivery-scarce campaign: delivered pairs, end-to-end
targets and discordance (Experiment 29, the 12 delivery-scarce targets;
the pre-registered primary endpoint panel).

Single-panel grouped bars: three metric groups on the x axis — delivered
pairs (of 36), end-to-end targets (of 12) and discordant pairs — each
pairing the navigation condition (sage) against the static condition
(terracotta) with the counts printed above the bars.  The two-condition
key sits as one column at the axes' upper right (user direction,
2026-09-08).

2026-10-06 follow-up (user-directed): (i) the stat line above the axes
deleted — the McNemar result (10:3, P = 0.092, n = 36) is carried
verbatim by §2.5 and the Fig. 5e legend, and the pre-registered no-go
verdict by the body's "not statistically significant" (the label retires
to the frozen verdict record); (ii) the panel narrowed 89 → 48.5 mm and
shortened 40 → 36 mm (the strip's reservation released) to share the
d|e|f group row, with the middle group label re-wrapped "End-to-end
targets (of 12)" over three lines and the first "Delivered pairs (of 36)"
over two; same day, the panel grew 36 → 54 mm to match panel e's height,
so the d|e|f row renders at one panel height; text unchanged at 6 pt,
zero number changes.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch):
"cells" → "pairs" in the group labels (the §2.5/legend term); the stat
line's "McNemar b:c =" decoded to "McNemar discordance" (the fig5b
convention) and its "NO-GO" set as "no-go" (the paper-wide term), the
em-dash separator retired to a comma; the key's "static grid" → "static
condition" (the body/legend condition name, the figS2 key precedent); no
number, colour or geometry changed.

2026-09-08 figure-repair pass (user direction): the bottom pair-outcome
stacked strip was removed — its four counts (14 both / 10 navigation-only
/ 3 grid-only / 9 neither) are exactly the Fig 5g mosaic tiles and are
text-reported in the Fig. 5g caption, so the strip duplicated panel g on
a different axis (one plot per panel, the fig5a/5b/5c/5d convention); the
floating in-axes "NO-GO (pre-registered)" text — in reading terms an
off-centre in-figure title — merged into the stat line; the "Targets e2e"
group label spelt out ("End-to-end targets"); the axes widened to the
house full-width geometry.  All text one 6-pt pure-black style; canvas
89×56 → 89×40 mm.

Style (the fig5b/5c house style): no in-figure title — the panel letter is
added at assembly; every text element one 6-pt pure-black style; colours
exclusively from palette rev 7; absolute-mm geometry, single column;
1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/seg3_decisive/verdict.json
Usage : python experiments/plots/fig5f_decisive_grouped_bars.py
Output : experiments/plots/output/fig5f_decisive_grouped_bars.{pdf,png}

2026-10-10 row-alignment polish (user-directed Fig. 5 batch): axes bottom
10.6 -> 9.1 mm and height 41.0 -> 42.5 mm (top edge anchored unchanged at
2.4 mm from the canvas top) so the x-axis spine lands on panel d's spine
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERDICT = (PROJECT_ROOT / "experiments" / "results"
           / "exp29_aptamer_campaign_arc" / "seg3_decisive" / "verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 48.5, 54.0

C_NAV = PALETTE_BY_NAME["sage_green"]     # navigation condition
C_RULE = PALETTE_BY_NAME["terracotta"]    # static condition

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

DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)   # exact 1200-dpi canvas pixels
H_PX = round(H_MM / 25.4 * DPI)


def fmt_p(p: float) -> str:
    if p >= 0.01:
        return f"P = {p:.3f}".rstrip("0").rstrip(".")
    return f"P = {p:.2e}" if p > 0 else "P < 1e-300"


def main() -> int:
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    n_cells = verdict["n_cells"]
    n_targets = verdict["n_targets"]
    del_c = verdict["delivered_cells"]["C"]
    del_a = verdict["delivered_cells"]["A"]
    e2e_c = verdict["e2e_targets"]["C"]
    e2e_a = verdict["e2e_targets"]["A"]
    b = verdict["mcnemar"]["b_nav_only"]
    c_ = verdict["mcnemar"]["c_rule_only"]
    p = verdict["mcnemar"]["p_exact"]
    go = (verdict.get("go_rule") or {}).get("verdict", "—")

    # +1e-9 in: defeat float truncation so the saved canvas is exactly
    # W_PX × H_PX (matplotlib takes int(figsize × dpi); the fig5c
    # convention)
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    ax = fig.add_axes([8.0 / W_MM, 9.1 / H_MM, 39.3 / W_MM, 42.5 / H_MM])
    groups = [
        (f"Delivered\npairs (of {n_cells})", del_c, del_a),
        (f"End-to-end\ntargets\n(of {n_targets})", e2e_c, e2e_a),
        ("Discordant\npairs", b, c_),
    ]
    ymax = max(del_c, del_a, e2e_c, e2e_a, b, c_, 1)
    count_labels = []
    for gi, (label, v_c, v_a) in enumerate(groups):
        for dx, val, color in ((-0.17, v_c, C_NAV), (0.17, v_a, C_RULE)):
            ax.bar(gi + dx, val, width=0.30, facecolor=color,
                   edgecolor="none", zorder=2)
            count_labels.append(ax.annotate(
                str(val), (gi + dx, val), textcoords="offset points",
                xytext=(0, 2), ha="center", fontsize=FONT, color=INK))
    ax.set_xlim(-0.58, 2.58)
    ax.set_ylim(0, ymax + 5.0)
    ax.set_yticks(range(0, ymax + 5, 5))
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g[0] for g in groups], fontsize=FONT,
                       linespacing=1.25)
    ax.set_ylabel("Count", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── key: the two condition swatches as one column at the axes' upper
    #    right (user direction, 2026-09-08), renderer-measured widths ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [(C_NAV, "navigation"), (C_RULE, "static condition")]
    swatch_w = 1.25 / W_MM
    swatch_h = 0.95 / H_MM
    gap_in = 0.006
    block_w = swatch_w + gap_in + max(text_w(s) for _, s in key_items)
    ax_r = (8.0 + 39.3) / W_MM         # axes right edge, fig fraction
    ax_t = (9.1 + 42.5) / H_MM         # axes top edge, fig fraction
    x_sw = ax_r - 1.0 / W_MM - block_w  # block sits 1 mm inside the axes
    x_tx = x_sw + swatch_w + gap_in
    key_texts, swatches = [], []
    for row, (color, label) in enumerate(key_items):
        yb = ax_t - (2.0 + 2.4 * row) / H_MM
        sax = fig.add_axes([x_sw, yb + 0.1 / H_MM, swatch_w, swatch_h])
        sax.set_xticks([]), sax.set_yticks([])
        for s in sax.spines.values():
            s.set_visible(False)
        sax.set_facecolor(color)
        swatches.append(sax)
        key_texts.append(fig.text(x_tx, yb, label, fontsize=FONT,
                                  color=INK, va="baseline"))

    # ── programmatic guards: every text and swatch in-canvas, pairwise
    #    non-colliding, and the bar counts below the axes top ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    items = [(t.get_text(), t.get_window_extent(renderer))
             for t in ([ax.yaxis.label] + count_labels + key_texts
                       + list(ax.get_xticklabels())
                       + list(ax.get_yticklabels()))]
    items += [("swatch", sax.bbox) for sax in swatches]
    for name, bb in items:
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"{name!r} outside canvas"
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            assert not items[i][1].overlaps(items[j][1]), \
                f"collision: {items[i][0]!r} x {items[j][0]!r}"
    for t in count_labels:
        assert t.get_window_extent(renderer).y1 <= ax.bbox.y1 + 1.0, \
            f"bar count {t.get_text()!r} crosses the axes top"
    bar_boxes = [p.get_window_extent(renderer) for p in ax.patches]
    key_boxes = ([t.get_window_extent(renderer) for t in key_texts]
                 + [sax.bbox for sax in swatches])
    for kb in key_boxes:
        for pb in bar_boxes:
            assert not kb.overlaps(pb), "key element overlaps a bar"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5f_decisive_grouped_bars.{ext}", dpi=DPI)
    plt.close(fig)

    img = mpimg.imread(OUT_DIR / "fig5f_decisive_grouped_bars.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    print(f"wrote fig5f_decisive_grouped_bars "
          f"(delivered {del_c}:{del_a} of {n_cells}, "
          f"e2e {e2e_c}:{e2e_a} of {n_targets}, "
          f"b:c = {b}:{c_}, {fmt_p(p)}, {go}; {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
