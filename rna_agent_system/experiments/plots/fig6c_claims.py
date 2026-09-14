"""Fig 6c — Claim adjudication of the baseline conditions: false-positive
rate (solid bars, Wilson 95% CI whiskers) and unverifiable-claim share
(light companion bars), the value printed at every bar end.

Five conditions on the y axis (bare LLM zero-/few-shot; ReAct matched /
3x / 10x); the platform condition publishes zero claims by construction
(ClaimGate is pipeline-synthesis-only) — carried by the Fig. 6 caption,
not annotated in-panel.  The section-2.3 ungated-control rate (54.5%)
is the reference class for these rates and is likewise carried by the
caption and the section text.  Every number shown is asserted against
the frozen comparison JSON.

Style: the fig6 house conventions (no in-figure title, single 6-pt
pure-black text, palette rev 7, absolute-mm geometry, 1200-dpi PNG + PDF,
text/collision guards, raster QA with palette purity).

2026-09-14 repair pass (user direction, the fig6a batch): condition labels
spelt out (Bare LLM zero-/few-shot, ReAct agent matched/3x/10x); bare
few-shot colour khaki -> grey blue (sage is fig6b's delivered-class
colour), keeping the fig-6-wide condition-colour identity with fig6a/6d.

2026-09-14 second repair pass (user direction): the two in-axes
annotations ("RNADesignAgent: 0 claims", "ungated control 54.5%") and
the dashed anchor line removed (the zero-claims fact and the 54.5%
reference rate live in the Fig. 6 caption and the section text);
per-bar value labels added; y axis titled "Fraction of claims" (both
quantities are fractions of the condition's claims); all text stays
6-pt pure black.  Key: each quantity's name followed by its five
condition swatches in the condition order (solid group verbatim, light
group the 55%-white tints), swatches tightly pitched and centred on the
text midline.

2026-09-14 layout-repair pass (user direction — the Fig-6 composite
re-arranged to a full-height left column a beside the b / c+d stack, so
c and d each get a half-block ~43-mm column): vertical grouped bars
re-laid as horizontal grouped bars — five spelt-out condition columns
plus per-bar value labels cannot keep the uniform 6-pt text on a 43-mm
x axis (the measured label block alone would overflow the plot), while
horizontal lanes give every label its own row; each condition carries a
light bar (unverifiable share, value at its end) above a solid bar (FP
rate, Wilson CI whisker, value at the whisker end); the axis title
"Fraction of claims" moves to the x axis; the key keeps both quantity
rows with all 5x2 condition swatches, wrapped to one centred row per
quantity (the single-row key of the 89-mm canvas no longer fits a 43-mm
column).  Canvas 89 x 50 -> 43.12 x 55 mm (the half-block width of the
new composite grid).  Guards extended: value labels additionally
asserted clear of every bar.

Data  : experiments/results/exp42_43_comparison/comparison.json
Usage : python experiments/plots/fig6c_claims.py
Output : experiments/plots/output/fig6c_claims.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON = (
    PROJECT_ROOT / "experiments" / "results" / "exp42_43_comparison" / "comparison.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 43.12, 55.0

CONDS = [
    ("bare_zeroshot", "Bare LLM zero-shot", PALETTE_BY_NAME["sand"]),
    ("bare_fewshot", "Bare LLM few-shot", PALETTE_BY_NAME["grey_blue"]),
    ("react_matched", "ReAct agent matched", PALETTE_BY_NAME["pale_dusty_rose"]),
    ("react_3x", "ReAct agent 3\u00d7", PALETTE_BY_NAME["dusty_mauve_pink"]),
    ("react_10x", "ReAct agent 10\u00d7", PALETTE_BY_NAME["terracotta"]),
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

DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)

# absolute-mm layout
AX_BOT_MM = 15.6         # axes bottom, from canvas bottom (x title + key below)
AX_TOP_GAP_MM = 1.2
MARGIN_L_MM = 1.0
MARGIN_R_MM = 1.3
GAP_LABEL_MM = 1.4       # condition-label block -> bars
BAR_H_MM = 2.4
PAIR_GAP_MM = 0.3        # light bar -> solid bar within a pair
GROUP_PITCH_MM = 7.7     # pair top -> next pair top
TOP_INSET_MM = 1.2       # plot top -> first pair top
VALUE_PAD_MM = 0.4       # bar/CI end -> value label
CAP_HALF_MM = 0.55       # CI whisker cap half-height
KEY_ROW1_Y_MM = 6.2      # FP key-row centre, from canvas bottom
KEY_ROW2_Y_MM = 3.2      # unverifiable key-row centre
SW_MM = 1.3              # key swatch edge
LAB_GAP_MM = 1.2         # quantity label -> its swatch group
SW_PITCH_MM = 2.0        # swatch-to-swatch spacing within a group


def blend_to_white(hex_color: str, frac_white: float):
    p = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return tuple(p + (1.0 - p) * frac_white)


def on_segment_rgb_tuple(uni, p_rgb, q_rgb, tol: float = 8.0) -> np.ndarray:
    p = np.asarray(p_rgb, dtype=float) if not isinstance(p_rgb, str) else \
        np.array([int(p_rgb[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    q = np.asarray(q_rgb, dtype=float) if not isinstance(q_rgb, str) else \
        np.array([int(q_rgb[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    d = q - p
    denom = float(d @ d)
    if denom == 0.0:
        return np.zeros(len(uni), dtype=bool)
    t = np.clip(((uni - p) @ d) / denom, 0.0, 1.0)
    return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol


def main() -> int:
    comp = json.loads(COMPARISON.read_text(encoding="utf-8"))
    claims = comp["claims"]

    for key, _, _ in CONDS:
        c = claims[key]
        assert c["fp_rate"] is not None and c["fp_rate_ci"][0] is not None
    assert abs(claims["react_10x"]["fp_rate"] - 0.5109) < 1e-9
    assert abs(claims["bare_fewshot"]["fp_rate"] - 0.1136) < 1e-9

    plot_h_mm = H_MM - AX_BOT_MM - AX_TOP_GAP_MM
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)  # the guards below measure in final-raster pixels
    ax = fig.add_axes([0.5, AX_BOT_MM / H_MM, 0.4, plot_h_mm / H_MM])
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, plot_h_mm)  # 1 y unit = 1 mm of plot height
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
    pair_h_mm = 2 * BAR_H_MM + PAIR_GAP_MM
    pair_centres = [plot_h_mm - TOP_INSET_MM - g * GROUP_PITCH_MM - pair_h_mm / 2
                    for g in range(len(CONDS))]
    ax.set_yticks(pair_centres)
    ax.set_yticklabels([lab for _, lab, _ in CONDS])
    ax.set_xlabel("Fraction of claims", labelpad=1.8)
    ax.tick_params(length=2, pad=1.8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    # measured label block (the fig6a/6b pattern): the bar span runs from
    # the labels' right edge to the right margin
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(
        t.get_window_extent(renderer).width for t in ax.get_yticklabels()
    ) / fig.bbox.width * W_MM
    bar_left_mm = MARGIN_L_MM + label_w_mm + GAP_LABEL_MM
    bar_w_mm = W_MM - MARGIN_R_MM - bar_left_mm
    ax.set_position([bar_left_mm / W_MM, AX_BOT_MM / H_MM,
                     bar_w_mm / W_MM, plot_h_mm / H_MM])

    bar_rects = []  # data-coord (x0, y0, w, h) for the text-bar guard
    value_texts = []
    for g, (key, _, color) in enumerate(CONDS):
        c = claims[key]
        pair_top = plot_h_mm - TOP_INSET_MM - g * GROUP_PITCH_MM
        # light bar (unverifiable share) on top, solid bar (FP rate) below
        y_light = pair_top - BAR_H_MM
        y_solid = pair_top - BAR_H_MM - PAIR_GAP_MM - BAR_H_MM
        ax.add_patch(Rectangle((0.0, y_light), c["unverifiable_share"], BAR_H_MM,
                               facecolor=blend_to_white(color, 0.55),
                               edgecolor="none"))
        ax.add_patch(Rectangle((0.0, y_solid), c["fp_rate"], BAR_H_MM,
                               facecolor=color, edgecolor="none"))
        bar_rects.append((0.0, y_light, c["unverifiable_share"], BAR_H_MM))
        bar_rects.append((0.0, y_solid, c["fp_rate"], BAR_H_MM))
        # Wilson CI whisker on the solid bar
        lo, hi = c["fp_rate_ci"]
        yc_solid = y_solid + BAR_H_MM / 2
        ax.plot([lo, hi], [yc_solid, yc_solid], color=INK, lw=0.6, zorder=4)
        for xv in (lo, hi):
            ax.plot([xv, xv], [yc_solid - CAP_HALF_MM, yc_solid + CAP_HALF_MM],
                    color=INK, lw=0.6, zorder=4)
        # per-bar value labels at the bar / whisker end (0-1 fraction scale)
        value_texts.append(ax.text(
            c["unverifiable_share"] + VALUE_PAD_MM / bar_w_mm,
            y_light + BAR_H_MM / 2, f"{c['unverifiable_share']:.2f}",
            ha="left", va="center", fontsize=FONT, color=INK))
        value_texts.append(ax.text(
            hi + VALUE_PAD_MM / bar_w_mm, yc_solid, f"{c['fp_rate']:.2f}",
            ha="left", va="center", fontsize=FONT, color=INK))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    # key: one centred row per quantity — the quantity's name followed by
    # its five condition swatches in the panel order (solid group =
    # condition colours verbatim, light group = their 55%-white companion
    # tints); swatches centred on the text midline
    SW = SW_MM / W_MM
    LAB_GAP = LAB_GAP_MM / W_MM
    SW_PITCH = SW_PITCH_MM / W_MM
    key_groups = [
        ("False-positive rate (95% CI)", [c for _, _, c in CONDS]),
        ("Unverifiable share of claims",
         [blend_to_white(c, 0.55) for _, _, c in CONDS]),
    ]
    group_w = (len(CONDS) - 1) * SW_PITCH + SW
    key_texts = []
    key_swatches = []  # (x, y, w, h) figure fractions
    for row, (lab, colors) in enumerate(key_groups):
        total_w = text_w(lab) + LAB_GAP + group_w
        assert total_w < 0.96, f"key row overflows canvas: {total_w:.3f}"
        x = 0.5 - total_w / 2
        y = (KEY_ROW1_Y_MM if row == 0 else KEY_ROW2_Y_MM) / H_MM
        key_texts.append(fig.text(x, y, lab, fontsize=FONT, color=INK,
                                  ha="left", va="center"))
        x += text_w(lab) + LAB_GAP
        for k, color in enumerate(colors):
            key_swatches.append((x + k * SW_PITCH, y - (SW_MM / 2) / H_MM,
                                 SW, SW_MM / H_MM))
            fig.patches.append(Rectangle(
                (x + k * SW_PITCH, y - (SW_MM / 2) / H_MM), SW, SW_MM / H_MM,
                transform=fig.transFigure,
                facecolor=(tuple(np.clip(color, 0, 1)) if isinstance(color, tuple) else color),
                edgecolor="none"))

    # guards
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
             + [ax.xaxis.label] + key_texts + value_texts)
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"
    ylabel_boxes = [t.get_window_extent(renderer) for t in ax.get_yticklabels()]
    assert max(b.x1 for b in ylabel_boxes) < ax.bbox.x0, \
        "condition labels cross into the bars"
    # value labels clear every bar (and the CI whisker caps they sit beside)
    for t, bb in zip(value_texts, [t.get_window_extent(renderer)
                                   for t in value_texts]):
        for bx0, by0, bw, bh in bar_rects:
            p0 = ax.transData.transform((bx0, by0))
            p1 = ax.transData.transform((bx0 + bw, by0 + bh))
            bar_bb = Bbox([p0, p1])
            assert not bb.overlaps(bar_bb), \
                f"value label crosses a bar: {t.get_text()!r}"
    # key swatches clear every text element
    for sx, sy, swf, shf in key_swatches:
        sb = Bbox([fig.transFigure.transform((sx, sy)),
                   fig.transFigure.transform((sx + swf, sy + shf))])
        for t, bb in zip(texts, boxes):
            assert not sb.overlaps(bb), \
                f"key swatch touches text: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6c_claims.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA
    img = mpimg.imread(OUT_DIR / "fig6c_claims.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    def on_segment(hex1: str, hex2: str, tol: float = 8.0) -> np.ndarray:
        p = np.array([int(hex1[i:i + 2], 16) for i in (1, 3, 5)])
        q = np.array([int(hex2[i:i + 2], 16) for i in (1, 3, 5)])
        d = (q - p).astype(float)
        denom = float(d @ d)
        if denom == 0.0:
            return np.zeros(len(uni), dtype=bool)
        t = np.clip(((uni - p) @ d) / denom, 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for _, _, hexc in CONDS:
        ok |= on_segment(hexc, "#FFFFFF") | on_segment(hexc, "#000000")
        light = tuple(int(v * 255) for v in blend_to_white(hexc, 0.55))
        ok |= on_segment_rgb_tuple(uni, light, (0, 0, 0))
        ok |= on_segment_rgb_tuple(uni, light, (255, 255, 255))
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6c_claims (5 conditions x 2 quantities, horizontal "
          f"grouped bars; raster QA green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
