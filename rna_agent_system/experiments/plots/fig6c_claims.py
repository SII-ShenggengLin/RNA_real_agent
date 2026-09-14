"""Fig 6c — Claim adjudication of the baseline conditions: false-positive
rate (solid, Wilson 95% CI whiskers) and unverifiable-claim share (light
companion), against the ungated-control anchor (the section-2.3 measured
54.5%, dashed reference line).

Five conditions on the x axis (bare LLM zero-/few-shot; ReAct matched /
3x / 10x); the platform condition publishes zero claims by construction
(ClaimGate is pipeline-synthesis-only) and is annotated as such.  Every
number is asserted against the frozen comparison JSON and the frozen
ungated-control summary.

Style: the fig6 house conventions (no in-figure title, single 6-pt
pure-black text, palette rev 7, absolute-mm geometry, 1200-dpi PNG + PDF,
text/collision guards, raster QA with palette purity).

Data  : experiments/results/exp42_43_comparison/comparison.json
        experiments/results/exp5_claim_overreach/runs_summary.json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON = (
    PROJECT_ROOT / "experiments" / "results" / "exp42_43_comparison" / "comparison.json"
)
UNGATED = (
    PROJECT_ROOT / "experiments" / "results" / "exp5_claim_overreach" / "runs_summary.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 50.0

CONDS = [
    ("bare_zeroshot", "Bare\nzero-shot", PALETTE_BY_NAME["sand"]),
    ("bare_fewshot", "Bare\nfew-shot", PALETTE_BY_NAME["khaki"]),
    ("react_matched", "ReAct\nmatched", PALETTE_BY_NAME["pale_dusty_rose"]),
    ("react_3x", "ReAct\n3\u00d7", PALETTE_BY_NAME["dusty_mauve_pink"]),
    ("react_10x", "ReAct\n10\u00d7", PALETTE_BY_NAME["terracotta"]),
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

AX_LEFT_MM, AX_W_MM = 13.0, 67.0
AX_BOT_MM, AX_H_MM = 15.0, 26.5
LEG_Y_MM = 5.2


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
    ung = json.loads(UNGATED.read_text(encoding="utf-8"))
    anchor = ung["overall"]["fp_rate"]
    assert abs(anchor - 30 / 55) < 1e-9  # the registered ungated control

    for key, _, _ in CONDS:
        c = claims[key]
        assert c["fp_rate"] is not None and c["fp_rate_ci"][0] is not None
    assert abs(claims["react_10x"]["fp_rate"] - 0.5109) < 1e-9
    assert abs(claims["bare_fewshot"]["fp_rate"] - 0.1136) < 1e-9

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    ax = fig.add_axes([AX_LEFT_MM / W_MM, AX_BOT_MM / H_MM,
                       AX_W_MM / W_MM, AX_H_MM / H_MM])
    ax.set_xlim(-0.5, len(CONDS) - 0.5)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.set_xticks(range(len(CONDS)))
    ax.set_xticklabels([lab for _, lab, _ in CONDS])
    ax.tick_params(length=2, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    bw = 0.34
    for i, (key, _, color) in enumerate(CONDS):
        c = claims[key]
        # light companion: unverifiable share
        ax.add_patch(Rectangle((i - bw - 0.02, 0), bw, c["unverifiable_share"],
                               facecolor=blend_to_white(color, 0.55),
                               edgecolor="none"))
        # solid: FP rate with Wilson CI whiskers
        ax.add_patch(Rectangle((i + 0.02, 0), bw, c["fp_rate"],
                               facecolor=color, edgecolor="none"))
        lo, hi = c["fp_rate_ci"]
        ax.plot([i + 0.02 + bw / 2, i + 0.02 + bw / 2], [lo, hi],
                color=INK, lw=0.6, zorder=4)
        for yv in (lo, hi):
            ax.plot([i + 0.02 + bw / 2 - 0.05, i + 0.02 + bw / 2 + 0.05],
                    [yv, yv], color=INK, lw=0.6, zorder=4)

    # ungated-control anchor (the section-2.3 measured rate)
    ax.plot([-0.5, len(CONDS) - 0.5], [anchor, anchor],
            color=PALETTE_BY_NAME["dark_warm_grey"], lw=0.7,
            linestyle=(0, (3, 2)), zorder=3)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    # anchor label, right-aligned above the dashed line (in-axes coords)
    ax.text(len(CONDS) - 0.5, anchor + 0.035, "ungated control 54.5%",
            ha="right", va="bottom", fontsize=FONT, color=INK)

    # platform zero-claims note, left-aligned inside the axes headroom
    ax.text(-0.42, 0.93, "platform: 0 claims", ha="left", va="top",
            fontsize=FONT, color=INK)

    # key: one centred row (solid / light swatches)
    SW = 1.3 / W_MM
    GAP_IN, GAP_OUT = 0.6 / W_MM, 1.5 / W_MM
    items = [
        (PALETTE_BY_NAME["terracotta"], "solid: false-positive rate (95% CI)"),
        (blend_to_white(PALETTE_BY_NAME["terracotta"], 0.55),
         "light: unverifiable share"),
        (PALETTE_BY_NAME["dark_warm_grey"], "dashed: ungated-control anchor"),
    ]
    key_texts = []
    for row_i, idxs in enumerate((range(0, 2), range(2, 3))):
        sub = [items[i] for i in idxs]
        widths = [SW + GAP_IN + text_w(lab) + GAP_OUT for _, lab in sub]
        total_w = sum(widths) - GAP_OUT
        assert total_w < 0.94, f"key row overflows canvas: {total_w:.3f}"
        x = 0.5 - total_w / 2
        y = (LEG_Y_MM + (1 - row_i) * 2.7) / H_MM
        for (color, lab), w in zip(sub, widths):
            fig.patches.append(Rectangle(
                (x, y - 0.65 / H_MM), SW, 1.3 / H_MM,
                transform=fig.transFigure,
                facecolor=(tuple(np.clip(color, 0, 1)) if isinstance(color, tuple) else color),
                edgecolor="none"))
            x += SW + GAP_IN
            key_texts.append(fig.text(x, y, lab, fontsize=FONT, color=INK,
                                      va="baseline"))
            x += text_w(lab) + GAP_OUT

    # guards
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels()) + key_texts
             + [t for t in ax.texts])
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
        # the dashed anchor line crosses the bars: its antialiasing blends
        # dark warm grey with each condition colour
        ok |= on_segment_rgb_tuple(uni, hexc, PALETTE_BY_NAME["dark_warm_grey"])
        light = tuple(int(v * 255) for v in blend_to_white(hexc, 0.55))
        ok |= on_segment_rgb_tuple(uni, light, (0, 0, 0))
        ok |= on_segment_rgb_tuple(uni, light, (255, 255, 255))
    ok |= on_segment(PALETTE_BY_NAME["dark_warm_grey"], "#FFFFFF")
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6c_claims (5 conditions; anchor {anchor:.3f}; raster QA "
          f"green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
