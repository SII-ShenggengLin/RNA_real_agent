"""Fig 6a — External-baseline delivery map: the 11-workflow x 6-condition
per-turn delivered-validity mosaic (the E21/E22 three-arm comparison).

One tile per (workflow, condition) cell; the tile fill is the condition's
palette colour blended toward white by the undelivered fraction of that
cell's turns, and the delivered/turns count is printed in the tile in ink.
Rows follow the canonical workflow order (palette.WORKFLOW_ORDER, grouped
design workflows top, prediction-type workflows bottom with a divider);
columns are Platform / bare LLM (zero-shot, few-shot) / ReAct (matched,
3x, 10x).  The platform column is solid everywhere by construction of the
symmetric re-adjudication (96/96); the bare columns show the tool-free
floor (solid on short-composition workflows, hollow on tertiary structure
and sgRNA); the ReAct columns show the budget-tier gradient.

Data assertions: every cell equals the frozen comparison JSON
(exp42_43_comparison/comparison.json, delivery_by_workflow) verbatim.

Style (the fig5c/fig5g carpet house style): no in-figure title (the panel
letter is added at assembly); every text element one 6-pt pure-black style;
colours exclusively from palette rev 7 (condition colours; tile fills are
palette<->white blends, covered by the raster palette-purity check);
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF
(fonttype 42).  Programmatic guards: every text in-canvas, pairwise text
non-collision, row-label/mosaic clearance, exact canvas pixels, raster
palette purity, white outer border.

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
W_MM, H_MM = 89.0, 92.0

CONDITIONS = [
    ("platform", "Platform", PALETTE_BY_NAME["slate_blue"]),
    ("bare_zeroshot", "Bare zs", PALETTE_BY_NAME["sand"]),
    ("bare_fewshot", "Bare fs", PALETTE_BY_NAME["khaki"]),
    ("react_matched", "ReAct m", PALETTE_BY_NAME["pale_dusty_rose"]),
    ("react_3x", "ReAct 3\u00d7", PALETTE_BY_NAME["dusty_mauve_pink"]),
    ("react_10x", "ReAct 10\u00d7", PALETTE_BY_NAME["terracotta"]),
]

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
GAP_LABEL_MM = 1.4     # row-label block -> mosaic
MOSAIC_W_MM = 58.0     # 6 columns
ROW_PITCH_MM = 5.6
MOSAIC_TOP_MM = 78.0   # top of the tile grid (below the column headers)
LEG1_Y_MM = 4.6        # key baseline


def blend_to_white(hex_color: str, frac_white: float) -> tuple[float, float, float]:
    p = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return tuple(p + (1.0 - p) * frac_white)


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
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))

    ax = fig.add_axes([0.30, (H_MM - MOSAIC_TOP_MM) / H_MM,
                       MOSAIC_W_MM / W_MM, (n * ROW_PITCH_MM) / H_MM])
    ax.set_xlim(0, len(CONDITIONS))
    ax.set_ylim(0, n)
    ax.invert_yaxis()
    ax.set_aspect("auto")
    ax.set_xticks([i + 0.5 for i in range(len(CONDITIONS))])
    ax.set_xticklabels([lab for _, lab, _ in CONDITIONS])
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks([i + 0.5 for i in range(n)])
    ax.set_yticklabels([WORKFLOW_LABELS[w] for w in ROWS])
    ax.tick_params(length=0, pad=1.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="x", pad=2.2)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(
        t.get_window_extent(renderer).width for t in ax.get_yticklabels()
    ) / fig.bbox.width * W_MM
    content_mm = label_w_mm + GAP_LABEL_MM + MOSAIC_W_MM
    left0_mm = (W_MM - content_mm) / 2
    ax.set_position([(left0_mm + label_w_mm + GAP_LABEL_MM) / W_MM,
                     (H_MM - MOSAIC_TOP_MM) / H_MM,
                     MOSAIC_W_MM / W_MM, (n * ROW_PITCH_MM) / H_MM])

    # tiles: fill blended by undelivered fraction, delivered/turns in ink
    for row, wf in enumerate(ROWS):
        for col, (key, _, color) in enumerate(CONDITIONS):
            cell = by_wf[wf][key]
            frac = cell["delivered"] / cell["turns"]
            ax.add_patch(Rectangle((col + 0.07, row + 0.16), 0.86, 0.68,
                                   facecolor=blend_to_white(color, 1.0 - frac)
                                   if frac > 0 else "white",
                                   edgecolor=color if frac == 0 else "none",
                                   linewidth=0.5))
            ax.text(col + 0.5, row + 0.5, f"{cell['delivered']}/{cell['turns']}",
                    ha="center", va="center", fontsize=FONT, color=INK)

    # divider between design and prediction-type workflows
    ax.plot([-0.03, len(CONDITIONS) + 0.03], [N_DESIGN, N_DESIGN],
            color=PALETTE_BY_NAME["warm_grey"], lw=0.6, zorder=4, clip_on=False)

    # key: one centred row — the condition colours (column identity)
    hdr_bb = ax.get_xticklabels()[0].get_window_extent(renderer)
    fig.text(0.5, hdr_bb.y1 / fig.bbox.height + 1.2 / H_MM,
             "Tile fill darkens with the delivered fraction of the cell\'s turns",
             ha="center", va="bottom", fontsize=FONT, color=INK)

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    SW = 1.3 / W_MM
    GAP_IN, GAP_OUT = 0.6 / W_MM, 1.7 / W_MM
    labels = [lab.replace("\n", " ") for _, lab, _ in CONDITIONS]
    colors = [c for _, _, c in CONDITIONS]
    key_texts = []
    for row_i, idxs in enumerate((range(0, 3), range(3, 6))):
        widths = [SW + GAP_IN + text_w(labels[i]) + GAP_OUT for i in idxs]
        total_w = sum(widths) - GAP_OUT
        assert total_w < 0.94, f"key row overflows canvas: {total_w:.3f}"
        x = 0.5 - total_w / 2
        y = (LEG1_Y_MM + (1 - row_i) * 2.4) / H_MM
        for i in idxs:
            fig.patches.append(Rectangle(
                (x, y - 0.65 / H_MM), SW, 1.3 / H_MM,
                transform=fig.transFigure, facecolor=colors[i], edgecolor="none"))
            x += SW + GAP_IN
            key_texts.append(fig.text(x, y, labels[i], fontsize=FONT, color=INK,
                                      va="baseline"))
            x += text_w(labels[i]) + GAP_OUT

    # programmatic guards
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = list(ax.get_xticklabels()) + list(ax.get_yticklabels()) + key_texts
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

    def on_segment(hex1: str, hex2: str, tol: float = 8.0) -> np.ndarray:
        p = np.array([int(hex1[i:i + 2], 16) for i in (1, 3, 5)])
        q = np.array([int(hex2[i:i + 2], 16) for i in (1, 3, 5)])
        d = (q - p).astype(float)
        t = np.clip(((uni - p) @ d) / (d @ d), 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

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
    # anchor<->black segment; the plain condition colours anchor the key
    # swatches and the zero-delivery tile outlines
    anchors = [tuple(int(v * 255) for v in blend_to_white(hexc, 0.0))
               for _, _, hexc in CONDITIONS]
    for wf in ROWS:
        for key, _, hexc in CONDITIONS:
            cell = by_wf[wf][key]
            if cell["turns"]:
                anchors.append(tuple(int(v * 255) for v in
                                     blend_to_white(hexc, 1.0 - cell["delivered"] / cell["turns"])))
    for a in anchors:
        ok |= on_segment_rgb(a, (0, 0, 0)) | on_segment_rgb(a, (255, 255, 255))
    ok |= on_segment(PALETTE_BY_NAME["warm_grey"], "#FFFFFF")
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6a_baseline_delivery_mosaic ({n} workflows x "
          f"{len(CONDITIONS)} conditions; raster QA green -> "
          f"{W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
