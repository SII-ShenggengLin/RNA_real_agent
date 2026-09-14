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

2026-09-14 repair pass (user direction, the fig6a batch): point labels
spelt out ("RNADesignAgent", "Bare LLM zero-shot/few-shot"); bare
few-shot colour khaki -> grey blue (sage is fig6b's delivered-class
colour), keeping the fig-6-wide condition-colour identity with
fig6a/fig6c.

2026-09-14 second repair pass (user direction): the two bare-model
conditions both spent exactly 96 calls, so their markers (71 vs 69
delivered) nearly coincide — they are drawn at a symmetric +/-20-call
horizontal offset for visibility (the true values are asserted below;
the join line and all other markers sit at exact data coordinates).
Point labels re-anchored: vertically centred on their markers, and the
two inner ReAct tier labels moved off the budget-gradient line ("ReAct
matched" was struck through by the matched->3x segment, "ReAct 3x" was
grazed by the departing segment). Y ticks regularized to
0/20/40/60/80/100 (the old 0/25/50/75/96 mixed a 21-unit top interval
with 25-unit steps). Guards extended beyond text-text/canvas-bounds to
text-marker, marker-marker and text-line collision checks.

2026-09-14 layout-repair pass (user direction — the Fig-6 composite
re-arranged to a full-height left column a beside the b / c+d stack, so
c and d each get a half-block ~43-mm column): canvas 89 x 50 ->
43.12 x 55 mm at unchanged 6-pt text; the ReAct 10x label sits above
its marker at the upper right (ha=right, its right end at the plot's
right edge — a true right-side placement is impossible: the marker at
756/850 leaves only ~3.8 mm to the edge against a ~10-mm label) — the
bare zero-shot label is raised (+2.6 mm) and the few-shot label lowered
(-1.8 mm) to open that band — and the remaining label offsets
re-measured under the same guards.

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
W_MM, H_MM = 43.12, 55.0

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

AX_LEFT_MM, AX_W_MM = 8.6, 34.02
AX_BOT_MM, AX_H_MM = 7.3, 46.2

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
        # (label, x llm, y delivered, color, dx_mm, dy_mm, x_dodge_calls, ha)
        ("RNADesignAgent", platform_llm, od["platform"]["delivered"],
         PALETTE_BY_NAME["slate_blue"], 1.6, 0.0, 0.0, "left"),
        ("Bare LLM zero-shot", bare_llm, od["bare_zeroshot"]["delivered"],
         PALETTE_BY_NAME["sand"], 1.1, 2.6, -20.0, "left"),
        ("Bare LLM few-shot", bare_llm, od["bare_fewshot"]["delivered"],
         PALETTE_BY_NAME["grey_blue"], 1.6, -1.8, 20.0, "left"),
        ("ReAct matched", react["matched"]["llm_calls_total"],
         od["react_matched"]["delivered"],
         PALETTE_BY_NAME["pale_dusty_rose"], 2.0, -0.45, 0.0, "left"),
        ("ReAct 3\u00d7", react["3x"]["llm_calls_total"],
         od["react_3x"]["delivered"],
         PALETTE_BY_NAME["dusty_mauve_pink"], 1.6, -1.6, 0.0, "left"),
        ("ReAct 10\u00d7", react["10x"]["llm_calls_total"],
         od["react_10x"]["delivered"],
         PALETTE_BY_NAME["terracotta"], 3.7, 2.2, 0.0, "right"),
    ]

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)  # the guards below measure in final-raster pixels
    ax = fig.add_axes([AX_LEFT_MM / W_MM, AX_BOT_MM / H_MM,
                       AX_W_MM / W_MM, AX_H_MM / H_MM])
    ax.set_xlim(0, 850)
    ax.set_ylim(0, 104)
    ax.set_xticks([0, 200, 400, 600, 800])
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Total LLM calls (96-turn suite)", labelpad=1.8)
    ax.set_ylabel("Delivered turns (of 96)", labelpad=1.8)
    ax.tick_params(length=2, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # the ReAct budget gradient, joined in tier order
    rx = [react[t]["llm_calls_total"] for t in ("matched", "3x", "10x")]
    ry = [od[f"react_{t}"]["delivered"] for t in ("matched", "3x", "10x")]
    ax.plot(rx, ry, color=PALETTE_BY_NAME["warm_grey"], lw=0.6, zorder=2)

    markers = []
    labels = []
    for lab, x, y, color, dx, dy, dodge, ha in points:
        xp = x + dodge
        ax.scatter([xp], [y], s=14, facecolor=color, edgecolor=INK,
                   linewidth=0.5, zorder=4,
                   marker="s" if lab == "RNADesignAgent" else "o")
        markers.append((lab, xp, y))
        labels.append(ax.text(xp + dx * (850 / AX_W_MM), y + dy * (104 / AX_H_MM),
                              lab, ha=ha, va="center", fontsize=FONT,
                              color=INK))

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guards: text in canvas, text-text pairwise non-collision
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

    label_boxes = [t.get_window_extent(renderer) for t in labels]

    # guard: text-marker non-collision (clearance 0.35 mm)
    mm_px = DPI / 25.4
    r_px = ((14 ** 0.5) / 2 + 0.25) / 72.0 * DPI  # marker half-side + edge
    mboxes = []
    for mlab, xp, y in markers:
        cx, cy = ax.transData.transform((xp, y))
        mboxes.append((mlab, cx - r_px, cy - r_px, cx + r_px, cy + r_px))
    clear_tm = 0.35 * mm_px
    for t, bb in zip(labels, label_boxes):
        for mlab, mx0, my0, mx1, my1 in mboxes:
            assert (bb.x1 <= mx0 - clear_tm or bb.x0 >= mx1 + clear_tm
                    or bb.y1 <= my0 - clear_tm or bb.y0 >= my1 + clear_tm), \
                f"text-marker collision: {t.get_text()!r} x {mlab!r}"

    # guard: marker-marker non-collision (clearance 0.15 mm)
    for i in range(len(mboxes)):
        for j in range(i + 1, len(mboxes)):
            (_, ax0, ay0, ax1, ay1), (_, bx0, by0, bx1, by1) = \
                mboxes[i], mboxes[j]
            d = float(np.hypot((ax0 + ax1 - bx0 - bx1) / 2,
                               (ay0 + ay1 - by0 - by1) / 2))
            assert d >= 2 * r_px + 0.15 * mm_px, \
                f"marker collision: {mboxes[i][0]!r} x {mboxes[j][0]!r}"

    # guard: text-line non-collision (line half-width + 0.30 mm clearance)
    seg_pts = [tuple(ax.transData.transform((x, y))) for x, y in zip(rx, ry)]

    def _pt_seg(p, a, b):
        a, b, p = np.asarray(a), np.asarray(b), np.asarray(p)
        d = b - a
        s = float(np.clip((p - a) @ d / (d @ d), 0.0, 1.0))
        return float(np.linalg.norm(p - (a + s * d)))

    def _pt_rect(p, bb):
        dx_ = max(bb.x0 - p[0], 0.0, p[0] - bb.x1)
        dy_ = max(bb.y0 - p[1], 0.0, p[1] - bb.y1)
        return float(np.hypot(dx_, dy_))

    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _seg_cross(p1, p2, p3, p4):
        return (((_cross(p3, p4, p1) > 0) != (_cross(p3, p4, p2) > 0))
                and ((_cross(p1, p2, p3) > 0) != (_cross(p1, p2, p4) > 0)))

    def _seg_rect(a, b, bb):
        if ((bb.x0 <= a[0] <= bb.x1 and bb.y0 <= a[1] <= bb.y1)
                or (bb.x0 <= b[0] <= bb.x1 and bb.y0 <= b[1] <= bb.y1)):
            return 0.0
        corners = [(bb.x0, bb.y0), (bb.x0, bb.y1),
                   (bb.x1, bb.y0), (bb.x1, bb.y1)]
        edges = [(corners[0], corners[1]), (corners[0], corners[2]),
                 (corners[1], corners[3]), (corners[2], corners[3])]
        if any(_seg_cross(a, b, e0, e1) for e0, e1 in edges):
            return 0.0
        return min([_pt_rect(a, bb), _pt_rect(b, bb)]
                   + [_pt_seg(c, a, b) for c in corners])

    clear_tl = (0.6 / 2) / 72.0 * DPI + 0.30 * mm_px
    for t, bb in zip(labels, label_boxes):
        for k in range(len(seg_pts) - 1):
            assert _seg_rect(seg_pts[k], seg_pts[k + 1], bb) >= clear_tl, \
                f"text-line collision: {t.get_text()!r} x gradient segment {k}"

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

    for hexc in [c for _, _, _, c, _, _, _, _ in points] + [
        PALETTE_BY_NAME["warm_grey"],
    ]:
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # marker interiors blend the edge ink ring with the face colour
    for a_hex, b_hex in (
        (PALETTE_BY_NAME["sand"], INK),
        (PALETTE_BY_NAME["grey_blue"], INK),
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
