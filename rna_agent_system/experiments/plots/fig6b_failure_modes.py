"""Fig 6b — Non-delivery decomposition: why turns fail, per condition
(the E21/E22 three-arm comparison).

One horizontal stacked bar per condition (n = 96 turns each), segmented by
the deterministic failure mode: delivered (sage green, the figure-wide
delivered-class colour), out of budget without an answer (warm grey —
the mechanical per-action LLM tax), answered below the system's frozen
best (pale mauve grey), answered invalid (solid
mauve grey): one hue family per failure kind with lightness encoding
severity (the fig3e family-x-lightness convention).  Segment counts printed
in-canvas where the segment is wide enough; the system bar is uniformly
delivered.

2026-10-09 terminology pass (user-directed pending-item batch): the fourth
key label "structurally invalid" -> "invalid" — the structural->validity
unification of section 2.6, the Fig. 6 legend (b) and M4 ("validity
checks"); the frozen JSON class key answered_structurally_invalid stays
verbatim; no number, colour or geometry changed.

2026-10-06 figure-adjustment pass (user direction, post-polish Fig. 6
batch):
- key labels aligned verbatim with the polished Fig. 6 legend (b) and
  section 2.6: "budget exhausted" -> "out of budget", "below platform
  quality" -> "below the system's best" ("platform" is a paper-wide
  retired term; the class totals 358/137/56/25 unchanged);
- condition labels follow the figure-wide naming alignment: "Bare LLM"
  -> "Bare model", "ReAct agent" -> "ReAct loop";
- canvas 89 x 50.5 -> 100.12 x 50.5 mm (user direction: b widened to
  the composite's full right-block width after a narrowed to 79 mm);
- class colours unchanged (sage / warm grey / mauve-grey ramp) — under
  the 2026-10-06 semantic condition colours of panels a/c/d they are
  again disjoint from every condition colour.

2026-09-14 figure-repair pass (user direction):
- class colours rebuilt (delivered sage unchanged; dark warm grey ->
  warm grey; the two answered-but-failed classes -> a pale->solid
  mauve-grey ramp): black in-segment numerals on the old dark warm grey
  were unreadable (the 86-turn block), and the three flat greys read as an
  undifferentiated wash; every fill stays palette rev 7 derived (the pale
  mauve is mauve grey blended 40% toward white, the fig6a tile-blend
  technique) and disjoint from fig6a's six condition colours;
- the ragged two-row centred key replaced by a 2 x 2 column-aligned key
  centred under the axes, reading order following the stacking order,
  labels in the caption's plain wording (per-class turn totals kept);
- x axis gained its title ("Turns per condition (n = 96)"); y tick labels
  spell the fig6a condition names in full ("ReAct agent matched" etc.);
- the fixed 34-mm label block replaced by a measured block (the fig6a
  pattern): 1.5-mm side margins, the bar span widened 46 -> ~64 mm (the
  old layout left broad blank bands on both sides); canvas 89 x 50 ->
  89 x 50.5 mm;
- no in-panel title (Nature convention: the panel letter is added at
  assembly); every text element one 6-pt pure-black style.

Reads the frozen comparison JSON and asserts every segment count.

Style: the fig5/fig6 house conventions — no in-figure title, single 6-pt
pure-black text style, palette rev 7 only, absolute-mm geometry, 1200-dpi
PNG + vector PDF, text-in-canvas + collision guards, raster QA.

Data  : experiments/results/exp42_43_comparison/comparison.json
Usage : python experiments/plots/fig6b_failure_modes.py
Output : experiments/plots/output/fig6b_failure_modes.{pdf,png}
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
W_MM, H_MM = 100.12, 50.5

ROWS = [
    ("platform", "RNADesignAgent"),
    ("bare_zeroshot", "Bare model zero-shot"),
    ("bare_fewshot", "Bare model few-shot"),
    ("react_matched", "ReAct loop matched"),
    ("react_3x", "ReAct loop 3\u00d7"),
    ("react_10x", "ReAct loop 10\u00d7"),
]


def blend_to_white(hex_color: str, frac_white: float) -> str:
    p = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(c + (255 - c) * frac_white):02X}" for c in p)


MAUVE = PALETTE_BY_NAME["mauve_grey"]
SEGMENTS = [
    ("delivered", "delivered", PALETTE_BY_NAME["sage_green"]),
    ("budget_exhausted_no_answer", "out of budget",
     PALETTE_BY_NAME["warm_grey"]),
    ("answered_below_platform_quality_parity", "below the system's best",
     blend_to_white(MAUVE, 0.4)),
    ("answered_structurally_invalid", "invalid", MAUVE),
]
N_TURNS = 96

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

MARGIN_MM = 1.5          # outer side margin
GAP_LABEL_MM = 1.4       # y-label block -> bars (covers tick + tick pad)
BAR_PITCH_MM = 5.6
AX_BOT_MM = 14.9         # axes bottom, from canvas bottom
LEG_ROW2_Y_MM = 4.0      # lower key-row centre, from canvas bottom
LEG_ROW_PITCH_MM = 3.0
LEG_COL_GAP_MM = 2.0
SW_MM = 1.3              # key swatch edge
GAP_IN_MM = 0.6          # swatch -> its label


def main() -> int:
    comp = json.loads(COMPARISON.read_text(encoding="utf-8"))
    fm = comp["failure_modes"]
    overall = comp["overall_delivery"]

    # assertions: segments + delivered == 96 per condition
    matrix = {}
    for key, _ in ROWS:
        m = dict(fm.get(key, {})) if key != "platform" else {}
        delivered = overall[key]["delivered"]
        assert overall[key]["turns"] == N_TURNS
        m["delivered"] = delivered
        total = sum(m.get(s, 0) for s, _, _ in SEGMENTS)
        assert total == N_TURNS, (key, total)
        matrix[key] = m
    assert matrix["react_matched"]["budget_exhausted_no_answer"] == 86
    assert matrix["bare_zeroshot"]["answered_below_platform_quality_parity"] == 14
    assert matrix["react_10x"]["answered_below_platform_quality_parity"] == 16

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    ax = fig.add_axes([0.3, AX_BOT_MM / H_MM, 0.6,
                       (len(ROWS) * BAR_PITCH_MM) / H_MM])
    ax.set_xlim(0, N_TURNS)
    ax.set_ylim(0, len(ROWS))
    ax.invert_yaxis()
    ax.set_xticks([0, 24, 48, 72, 96])
    ax.set_yticks([i + 0.5 for i in range(len(ROWS))])
    ax.set_yticklabels([lab for _, lab in ROWS])
    ax.tick_params(length=2, pad=1.8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    for row, (key, _) in enumerate(ROWS):
        x = 0.0
        for seg_key, _, color in SEGMENTS:
            v = matrix[key].get(seg_key, 0)
            if v:
                ax.add_patch(Rectangle((x, row + 0.18), v, 0.64,
                                       facecolor=color, edgecolor="none"))
                if v >= 8:  # print only when the segment fits the numeral
                    ax.text(x + v / 2, row + 0.5, str(v), ha="center",
                            va="center", fontsize=FONT, color=INK)
            x += v

    ax.set_xlabel("Turns per condition (n = 96)", fontsize=FONT, labelpad=2.2)

    # measured label block (the fig6a pattern): the bar span runs from the
    # labels' right edge to the right margin — no blank side bands
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(
        t.get_window_extent(renderer).width for t in ax.get_yticklabels()
    ) / fig.bbox.width * W_MM
    bar_left_mm = MARGIN_MM + label_w_mm + GAP_LABEL_MM
    bar_w_mm = W_MM - MARGIN_MM - bar_left_mm
    ax.set_position([bar_left_mm / W_MM, AX_BOT_MM / H_MM,
                     bar_w_mm / W_MM, (len(ROWS) * BAR_PITCH_MM) / H_MM])

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    # key: a 2 x 2 column-aligned grid centred under the axes; reading
    # order follows the stacking order
    totals = {k: sum(matrix[key].get(k, 0) for key, _ in ROWS) for k, _, _ in SEGMENTS}
    items = [(color, f"{lab} ({totals[seg]})") for seg, lab, color in SEGMENTS]
    grid = [(items[0], items[1]), (items[2], items[3])]
    sw = SW_MM / W_MM
    gap_in = GAP_IN_MM / W_MM
    col_gap = LEG_COL_GAP_MM / W_MM
    col_w = [sw + gap_in + max(text_w(grid[r][c][1]) for r in range(2))
             for c in range(2)]
    block_w = col_w[0] + col_gap + col_w[1]
    axes_cx = (bar_left_mm + bar_w_mm / 2) / W_MM
    x0 = axes_cx - block_w / 2
    assert x0 >= MARGIN_MM / W_MM and x0 + block_w <= 1 - MARGIN_MM / W_MM, \
        f"key block breaks the side margins: {x0 * W_MM:.1f} .. " \
        f"{(x0 + block_w) * W_MM:.1f} mm"
    key_texts = []
    key_swatches = []  # (x, y, w, h) figure fractions
    for r in range(2):
        y = (LEG_ROW2_Y_MM + (1 - r) * LEG_ROW_PITCH_MM) / H_MM
        x = x0
        for c in range(2):
            color, lab = grid[r][c]
            key_swatches.append((x, y - (SW_MM / 2) / H_MM, sw, SW_MM / H_MM))
            fig.patches.append(Rectangle(
                (x, y - (SW_MM / 2) / H_MM), sw, SW_MM / H_MM,
                transform=fig.transFigure, facecolor=color, edgecolor="none"))
            key_texts.append(fig.text(x + sw + gap_in, y, lab, fontsize=FONT,
                                      color=INK, va="center"))
            x += col_w[c] + col_gap

    # guards
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
             + [ax.xaxis.get_label()] + key_texts)
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
        "row labels cross into the bars"
    # key swatches clear every text element
    for sx, sy, swf, shf in key_swatches:
        sb = Bbox([fig.transFigure.transform((sx, sy)),
                   fig.transFigure.transform((sx + swf, sy + shf))])
        for t, bb in zip(texts, boxes):
            assert not sb.overlaps(bb), \
                f"key swatch touches text: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6b_failure_modes.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA
    img = mpimg.imread(OUT_DIR / "fig6b_failure_modes.png")
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
        t = np.clip(((uni - p) @ d) / (d @ d), 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for hexc in (PALETTE_BY_NAME["sage_green"], PALETTE_BY_NAME["warm_grey"],
                 MAUVE):
        ok |= on_segment(hexc, "#FFFFFF") | on_segment(hexc, "#000000")
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6b_failure_modes (6 conditions x 96 turns; raster QA "
          f"green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
