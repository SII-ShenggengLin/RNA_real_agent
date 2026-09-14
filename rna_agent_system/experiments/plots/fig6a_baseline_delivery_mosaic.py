"""Fig 6a — External-baseline delivery map: the 11-workflow x 6-condition
per-turn delivered-validity mosaic (the E21/E22 three-arm comparison).

One tile per (workflow, condition) cell; the tile fill is the condition's
palette colour blended toward white by the undelivered fraction of that
cell's turns (a mild gamma on the white fraction keeps mid-range cells
chromatic; endpoints unchanged — solid at full delivery, white with a
condition-coloured outline at zero delivery), and the delivered/turns count
is printed in the tile in ink.  Rows follow the canonical workflow order
(palette.WORKFLOW_ORDER, grouped design workflows top, prediction-type
workflows bottom with a divider); columns are RNADesignAgent / Bare LLM
(zero-shot, few-shot) / ReAct agent (matched, 3x, 10x).

2026-09-14 figure-repair pass (user direction):
- all text one 6-pt pure-black style (no greyed or tinted labels);
- no in-panel title (Nature convention: the panel letter is added at
  assembly) and no bottom encoding note either (the tile-fill semantics
  live in the figure caption);
- two-row grouped column headers replace the cryptic one-row labels:
  group row RNADesignAgent / Bare LLM / ReAct agent, sub row
  zero-shot / few-shot / matched / 3x / 10x (zs/fs/m retired), each group
  label carried by a thin spanning rule over exactly its columns (the
  Nature table convention — the rule makes the 1/2/3-column grouping
  explicit so the uneven label rhythm no longer reads as untidy);
- the colour-swatch key removed as redundant — every column is now
  directly labelled (direct labelling beats a legend under Nature
  conventions; this also retires the ragged two-row key);
- condition colour for the bare few-shot column khaki -> grey blue:
  khaki and sand were near-indistinguishable once blended toward white
  (sage green, the first fig5g-flavoured candidate, is fig6b's
  delivered-class colour and would clash within the figure).
  Propagated to fig6c/fig6d to preserve the fig-6-wide condition-colour
  identity;
- canvas 89 x 92 -> 89 x 73.7 mm (the retired key and note freed the
  bottom band).

2026-09-14 layout-repair pass (user direction — the Fig-6 composite
re-arranged to a full-height left column a beside the b / c+d stack):
canvas 89 x 73.7 -> 89 x 109 mm, row pitch 5.6 -> 8.81 mm so the mosaic
exactly fills the left column (header block and all text unchanged).

Data assertions: every cell equals the frozen comparison JSON
(exp42_43_comparison/comparison.json, delivery_by_workflow) verbatim.

Style (the fig5c/fig5g carpet house style): every text element one 6-pt
pure-black style; colours exclusively from palette rev 7 (condition
colours; tile fills are palette<->white blends, covered by the raster
palette-purity check); absolute-mm geometry, single column; 1200-dpi PNG +
vector PDF (fonttype 42).  Programmatic guards: every text in-canvas,
pairwise text non-collision, row-label/mosaic clearance, header/mosaic
clearance, exact canvas pixels, raster palette purity, white outer border.

Data  : experiments/results/exp42_43_comparison/comparison.json
Usage : python experiments/plots/fig6a_baseline_delivery_mosaic.py
Output : experiments/plots/output/fig6a_baseline_delivery_mosaic.{pdf,png}
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME, WORKFLOW_LABELS, WORKFLOW_ORDER  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON = (
    PROJECT_ROOT / "experiments" / "results" / "exp42_43_comparison" / "comparison.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 109.0

CONDITIONS = [
    ("platform", PALETTE_BY_NAME["slate_blue"]),
    ("bare_zeroshot", PALETTE_BY_NAME["sand"]),
    ("bare_fewshot", PALETTE_BY_NAME["grey_blue"]),
    ("react_matched", PALETTE_BY_NAME["pale_dusty_rose"]),
    ("react_3x", PALETTE_BY_NAME["dusty_mauve_pink"]),
    ("react_10x", PALETTE_BY_NAME["terracotta"]),
]
# two-row grouped headers: (group label, group centre in data units,
# first/last column the group's spanning rule covers)
GROUPS = [
    ("RNADesignAgent", 0.5, 0, 0),
    ("Bare LLM", 2.0, 1, 2),
    ("ReAct agent", 4.5, 3, 5),
]
SUBS = ["", "zero-shot", "few-shot", "matched", "3×", "10×"]

# prediction-type workflows (schema-level delivery for every arm) drawn
# below a divider; design workflows carry the structural signal
PREDICTION_WFS = {
    "mrna_sequence_scoring",
    "rna_small_molecule_interaction",
    "ires_prediction",
}
ROWS = [w for w in WORKFLOW_ORDER if w not in PREDICTION_WFS] + [
    w for w in WORKFLOW_ORDER if w in PREDICTION_WFS
]
N_DESIGN = sum(1 for w in ROWS if w not in PREDICTION_WFS)

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
GAP_LABEL_MM = 1.4        # row-label block -> mosaic
MOSAIC_W_MM = 67.0        # 6 columns x 11.17 mm
ROW_PITCH_MM = 8.81
MOSAIC_TOP_MM = 9.6       # canvas top -> mosaic top (two header rows above)
GROUP_Y_MM = 4.2          # group-header baseline, from canvas top
RULE_Y_MM = 5.5           # group spanning rules, from canvas top
SUB_Y_MM = 7.6            # sub-header baseline, from canvas top
BLEND_GAMMA = 1.3         # mild gamma on the white fraction (endpoints fixed)


def blend_to_white(hex_color: str, frac_white: float) -> tuple[float, float, float]:
    p = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return tuple(p + (1.0 - p) * frac_white)


def cell_fill(hex_color: str, frac_delivered: float) -> tuple[float, float, float]:
    return blend_to_white(hex_color, (1.0 - frac_delivered) ** BLEND_GAMMA)


def main() -> int:
    comp = json.loads(COMPARISON.read_text(encoding="utf-8"))
    by_wf = comp["delivery_by_workflow"]

    # data assertions: totals and the headline cells, verbatim from the JSON
    totals = comp["overall_delivery"]
    assert totals["platform"]["delivered"] == 96 and totals["platform"]["turns"] == 96
    assert (totals["bare_zeroshot"]["delivered"], totals["bare_zeroshot"]["turns"]) == (71, 96)
    assert (totals["react_matched"]["delivered"], totals["react_10x"]["delivered"]) == (7, 71)
    for wf, regs in by_wf.items():
        for key, cell in regs.items():
            assert 0 <= cell["delivered"] <= cell["turns"], (wf, key)

    n = len(ROWS)
    mosaic_h_mm = n * ROW_PITCH_MM
    mosaic_bot_mm = H_MM - MOSAIC_TOP_MM - mosaic_h_mm
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))

    ax = fig.add_axes([0.30, mosaic_bot_mm / H_MM,
                       MOSAIC_W_MM / W_MM, mosaic_h_mm / H_MM])
    ax.set_xlim(0, len(CONDITIONS))
    ax.set_ylim(0, n)
    ax.invert_yaxis()
    ax.set_aspect("auto")
    ax.set_xticks([])
    ax.set_yticks([i + 0.5 for i in range(n)])
    ax.set_yticklabels([WORKFLOW_LABELS[w] for w in ROWS])
    ax.tick_params(length=0, pad=1.8)
    for s in ax.spines.values():
        s.set_visible(False)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(
        t.get_window_extent(renderer).width for t in ax.get_yticklabels()
    ) / fig.bbox.width * W_MM
    content_mm = label_w_mm + GAP_LABEL_MM + MOSAIC_W_MM
    left0_mm = (W_MM - content_mm) / 2
    mosaic_left = (left0_mm + label_w_mm + GAP_LABEL_MM) / W_MM
    mosaic_w = MOSAIC_W_MM / W_MM
    ax.set_position([mosaic_left, mosaic_bot_mm / H_MM, mosaic_w,
                     mosaic_h_mm / H_MM])

    # tiles: fill blended by undelivered fraction, delivered/turns in ink
    for row, wf in enumerate(ROWS):
        for col, (key, color) in enumerate(CONDITIONS):
            cell = by_wf[wf][key]
            frac = cell["delivered"] / cell["turns"]
            ax.add_patch(Rectangle((col + 0.07, row + 0.16), 0.86, 0.68,
                                   facecolor=cell_fill(color, frac)
                                   if frac > 0 else "white",
                                   edgecolor=color if frac == 0 else "none",
                                   linewidth=0.5))
            ax.text(col + 0.5, row + 0.5, f"{cell['delivered']}/{cell['turns']}",
                    ha="center", va="center", fontsize=FONT, color=INK)

    # divider between design and prediction-type workflows (kept inside the
    # mosaic span so the white outer border stays clean)
    ax.plot([0.0, float(len(CONDITIONS))], [N_DESIGN, N_DESIGN],
            color=PALETTE_BY_NAME["warm_grey"], lw=0.6, zorder=4,
            clip_on=False, solid_capstyle="butt")

    def col_x(x_data: float) -> float:
        return mosaic_left + x_data / len(CONDITIONS) * mosaic_w

    # two-row grouped column headers (direct labels; no separate key);
    # a thin spanning rule under each group label covers exactly its
    # columns' tile span (the Nature table convention for column groups)
    header_texts = []
    for lab, gx, c0, c1 in GROUPS:
        header_texts.append(fig.text(
            col_x(gx), (H_MM - GROUP_Y_MM) / H_MM, lab,
            ha="center", va="baseline", fontsize=FONT, color=INK))
        x0 = col_x(c0 + 0.07)
        fig.patches.append(Rectangle(
            (x0, (H_MM - RULE_Y_MM) / H_MM), col_x(c1 + 0.93) - x0,
            0.18 / H_MM, transform=fig.transFigure,
            facecolor=INK, edgecolor="none"))
    for i, s in enumerate(SUBS):
        if s:
            header_texts.append(fig.text(
                col_x(i + 0.5), (H_MM - SUB_Y_MM) / H_MM, s,
                ha="center", va="baseline", fontsize=FONT, color=INK))

    # programmatic guards
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = list(ax.get_yticklabels()) + header_texts
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
    assert max(b.x1 for b in ylabel_boxes) < ax.bbox.x0, "row labels cross into the mosaic"
    sub_boxes = [t.get_window_extent(renderer) for t in header_texts[len(GROUPS):]]
    assert min(b.y0 for b in sub_boxes) > ax.bbox.y1, "sub headers cross into the mosaic"
    # every group label clears its spanning rule (descenders included)
    group_boxes = [t.get_window_extent(renderer) for t in header_texts[:len(GROUPS)]]
    rule_top = fig.bbox.height - RULE_Y_MM / H_MM * fig.bbox.height
    assert min(b.y0 for b in group_boxes) > rule_top + 1.0, \
        "group labels touch their spanning rules"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6a_baseline_delivery_mosaic.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA: exact canvas, white border, palette purity
    img = mpimg.imread(OUT_DIR / "fig6a_baseline_delivery_mosaic.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    def on_segment_rgb(p, q, tol: float = 8.0) -> np.ndarray:
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        d = q - p
        denom = float(d @ d)
        if denom == 0.0:
            return np.zeros(len(uni), dtype=bool)
        t = np.clip(((uni - p) @ d) / denom, 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    # anchors: every tile fill actually drawn (condition colour blended by
    # the cell's delivered fraction) -- in-tile ink text antialiases on the
    # anchor<->black segment; the plain condition colours anchor the
    # zero-delivery tile outlines
    anchors = [tuple(int(v * 255) for v in blend_to_white(hexc, 0.0))
               for _, hexc in CONDITIONS]
    for wf in ROWS:
        for key, hexc in CONDITIONS:
            cell = by_wf[wf][key]
            if cell["turns"] and cell["delivered"]:
                anchors.append(tuple(int(v * 255) for v in
                                     cell_fill(hexc, cell["delivered"] / cell["turns"])))
    for a in anchors:
        ok |= on_segment_rgb(a, (0, 0, 0)) | on_segment_rgb(a, (255, 255, 255))
    ok |= on_segment_rgb(
        [int(PALETTE_BY_NAME["warm_grey"][i:i + 2], 16) for i in (1, 3, 5)],
        (255, 255, 255))
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6a_baseline_delivery_mosaic ({n} workflows x "
          f"{len(CONDITIONS)} conditions; raster QA green -> "
          f"{W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
