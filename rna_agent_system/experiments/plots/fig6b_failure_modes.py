"""Fig 6b — Non-delivery decomposition: why turns fail, per condition
(the E21/E22 three-arm comparison).

One horizontal stacked bar per condition (n = 96 turns each), segmented by
the deterministic failure mode: delivered (sage green), budget-exhausted
without an answer (dark warm grey — the mechanical per-action LLM tax),
answered below the platform's frozen quality parity (mauve grey), answered
structurally invalid (warm grey).  Segment counts printed in-canvas where
the segment is wide enough; the platform bar is uniformly delivered.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON = (
    PROJECT_ROOT / "experiments" / "results" / "exp42_43_comparison" / "comparison.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 50.0

ROWS = [
    ("platform", "Platform"),
    ("bare_zeroshot", "Bare LLM zero-shot"),
    ("bare_fewshot", "Bare LLM few-shot"),
    ("react_matched", "ReAct matched"),
    ("react_3x", "ReAct 3\u00d7"),
    ("react_10x", "ReAct 10\u00d7"),
]
SEGMENTS = [
    ("delivered", "delivered", PALETTE_BY_NAME["sage_green"]),
    ("budget_exhausted_no_answer", "budget exhausted",
     PALETTE_BY_NAME["dark_warm_grey"]),
    ("answered_below_platform_quality_parity", "below platform parity",
     PALETTE_BY_NAME["mauve_grey"]),
    ("answered_structurally_invalid", "structurally invalid",
     PALETTE_BY_NAME["warm_grey"]),
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

BAR_LEFT_MM = 34.0    # y-label block -> bars
BAR_W_MM = 46.0
BAR_TOP_MM = 36.0
BAR_PITCH_MM = 5.6
LEG_Y_MM = 6.5


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
    ax = fig.add_axes([BAR_LEFT_MM / W_MM, (H_MM - BAR_TOP_MM) / H_MM,
                       BAR_W_MM / W_MM, (len(ROWS) * BAR_PITCH_MM) / H_MM])
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

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    # key: two centred rows (2 + 2 class swatches with counts)
    SW = 1.3 / W_MM
    GAP_IN, GAP_OUT = 0.6 / W_MM, 1.5 / W_MM
    totals = {k: sum(matrix[key].get(k, 0) for key, _ in ROWS) for k, _, _ in SEGMENTS}
    items = [(color, f"{lab} ({totals[seg]})") for seg, lab, color in SEGMENTS]
    key_texts = []
    for row_i, idxs in enumerate((range(0, 2), range(2, 4))):
        sub = [items[i] for i in idxs]
        widths = [SW + GAP_IN + text_w(lab) + GAP_OUT for _, lab in sub]
        total_w = sum(widths) - GAP_OUT
        assert total_w < 0.94, f"key row overflows canvas: {total_w:.3f}"
        x = 0.5 - total_w / 2
        y = (LEG_Y_MM + (1 - row_i) * 2.6) / H_MM
        for (color, lab), w in zip(sub, widths):
            fig.patches.append(Rectangle(
                (x, y - 0.65 / H_MM), SW, 1.3 / H_MM,
                transform=fig.transFigure, facecolor=color, edgecolor="none"))
            x += SW + GAP_IN
            key_texts.append(fig.text(x, y, lab, fontsize=FONT, color=INK,
                                      va="baseline"))
            x += text_w(lab) + GAP_OUT

    # guards
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

    for _, _, hexc in SEGMENTS:
        ok |= on_segment(hexc, "#FFFFFF") | on_segment(hexc, "#000000")
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6b_failure_modes (6 conditions x 96 turns; raster QA "
          f"green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
