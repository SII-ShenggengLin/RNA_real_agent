"""Fig 6d — Cost-delivery frontier of the three-arm comparison: total LLM
calls (x, log-free linear scale) against per-turn delivered validity (y, of
96 turns), one marker per condition.

The ReAct budget gradient is joined by a thin line in tier order
(matched -> 3x -> 10x); the platform marker anchors the top-left region
(146 calls, 96/96 delivered); the bare-LLM conditions sit at 96 calls each.
Every number is asserted against the frozen comparison JSON.

Style: the fig6 house conventions (no in-figure title, single 6-pt
pure-black text, palette rev 7, absolute-mm geometry, 1200-dpi PNG + PDF,
text/collision guards, raster QA).

Data  : experiments/results/exp42_43_comparison/comparison.json
Usage : python experiments/plots/fig6d_cost_delivery.py
Output : experiments/plots/output/fig6d_cost_delivery.{pdf,png}
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

AX_LEFT_MM, AX_W_MM = 17.0, 64.0
AX_BOT_MM, AX_H_MM = 13.5, 29.0

MARKER = {"platform": "s", "bare": "o", "react": "o"}


def main() -> int:
    comp = json.loads(COMPARISON.read_text(encoding="utf-8"))
    eff = comp["efficiency"]
    od = comp["overall_delivery"]

    platform_llm = eff["platform"]["llm_calls_total"]
    bare_llm = eff["bare_llm"]["llm_calls_total"] // 2  # per regime
    react = {t: eff["react"][t] for t in ("matched", "3x", "10x")}
    assert platform_llm == 146 and bare_llm == 96
    assert (react["matched"]["llm_calls_total"],
            react["3x"]["llm_calls_total"],
            react["10x"]["llm_calls_total"]) == (143, 466, 756)
    assert (od["react_matched"]["delivered"], od["react_3x"]["delivered"],
            od["react_10x"]["delivered"]) == (7, 44, 71)

    points = [
        # (label, x llm, y delivered, color, ha, dx_mm, dy_mm)
        ("Platform", platform_llm, od["platform"]["delivered"],
         PALETTE_BY_NAME["slate_blue"], "left", 1.6, -1.4),
        ("Bare zero-shot", bare_llm, od["bare_zeroshot"]["delivered"],
         PALETTE_BY_NAME["sand"], "left", 1.6, 1.6),
        ("Bare few-shot", bare_llm, od["bare_fewshot"]["delivered"],
         PALETTE_BY_NAME["khaki"], "left", 1.6, -3.4),
        ("ReAct matched", react["matched"]["llm_calls_total"],
         od["react_matched"]["delivered"],
         PALETTE_BY_NAME["pale_dusty_rose"], "left", 1.6, 1.6),
        ("ReAct 3\u00d7", react["3x"]["llm_calls_total"],
         od["react_3x"]["delivered"],
         PALETTE_BY_NAME["dusty_mauve_pink"], "left", 1.6, 1.6),
        ("ReAct 10\u00d7", react["10x"]["llm_calls_total"],
         od["react_10x"]["delivered"],
         PALETTE_BY_NAME["terracotta"], "left", 1.6, 1.6),
    ]

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    ax = fig.add_axes([AX_LEFT_MM / W_MM, AX_BOT_MM / H_MM,
                       AX_W_MM / W_MM, AX_H_MM / H_MM])
    ax.set_xlim(0, 850)
    ax.set_ylim(0, 104)
    ax.set_xticks([0, 200, 400, 600, 800])
    ax.set_yticks([0, 25, 50, 75, 96])
    ax.set_yticklabels(["0", "25", "50", "75", "96"])
    ax.set_xlabel("Total LLM calls (96-turn suite)", labelpad=1.8)
    ax.set_ylabel("Delivered turns (of 96)", labelpad=1.8)
    ax.tick_params(length=2, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # the ReAct budget gradient, joined in tier order
    rx = [react[t]["llm_calls_total"] for t in ("matched", "3x", "10x")]
    ry = [od[f"react_{t}"]["delivered"] for t in ("matched", "3x", "10x")]
    ax.plot(rx, ry, color=PALETTE_BY_NAME["warm_grey"], lw=0.6, zorder=2)

    labels = []
    for lab, x, y, color, ha, dx, dy in points:
        ax.scatter([x], [y], s=14, facecolor=color, edgecolor=INK,
                   linewidth=0.5, zorder=4,
                   marker="s" if lab == "Platform" else "o")
        t = ax.text(x + dx * (850 / 64.0), y + dy * (104 / 29.0), lab,
                    ha=ha, va="center", fontsize=FONT, color=INK)
        labels.append(t)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guards
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
             + [ax.xaxis.label, ax.yaxis.label] + labels)
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r} (move its label offset)"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig6d_cost_delivery.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA
    img = mpimg.imread(OUT_DIR / "fig6d_cost_delivery.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    # tol 12 (vs the house 8): the gradient line runs under the marker
    # rings, and single pixels at those boundaries blend three anchors
    # (face colour + warm grey line + ink ring) inside the anchor triangle
    # but up to ~11 off every pairwise segment
    def seg(p, q, tol: float = 12.0):
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)
        d = q - p
        denom = float(d @ d)
        if denom == 0.0:
            return np.zeros(len(uni), dtype=bool)
        t = np.clip(((uni - p) @ d) / denom, 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for hexc in [c for _, _, _, c, _, _, _ in points] + [
        PALETTE_BY_NAME["warm_grey"],
    ]:
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # marker interiors blend the edge ink ring with the face colour
    for a_hex, b_hex in (
        (PALETTE_BY_NAME["sand"], INK),
        (PALETTE_BY_NAME["khaki"], INK),
        (PALETTE_BY_NAME["pale_dusty_rose"], INK),
        (PALETTE_BY_NAME["dusty_mauve_pink"], INK),
        (PALETTE_BY_NAME["terracotta"], INK),
        (PALETTE_BY_NAME["slate_blue"], INK),
        (PALETTE_BY_NAME["warm_grey"], PALETTE_BY_NAME["dusty_mauve_pink"]),
        (PALETTE_BY_NAME["warm_grey"], PALETTE_BY_NAME["terracotta"]),
    ):
        pa = [int(a_hex[i:i + 2], 16) for i in (1, 3, 5)]
        pb = [int(b_hex[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(pa, pb)
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6d_cost_delivery (6 conditions; raster QA green -> "
          f"{W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
