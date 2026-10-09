"""Fig 6d — Cost-delivery frontier of the three-arm comparison: total model
calls (x, log-free linear scale) against per-turn delivered validity (y, of
96 turns), one marker per condition.

The ReAct-loop budget gradient is joined by a thin line in budget order
(matched -> 3x -> 10x); the system marker anchors the top-left region
(146 calls, 96/96 delivered); the bare-model conditions sit at 96 calls
each.  Every number is asserted against the frozen comparison JSON.

2026-10-06 figure-adjustment pass (user direction, post-polish Fig. 6
batch):
- semantic recolour to the figs-2-5 house semantics: the six flat
  condition colours retired for a three-family map — the system a sage
  square (the fig4a gated / fig5 navigation colour), the bare model a
  grey-blue pair (zero-shot a 45%-white tint, few-shot solid), the
  ReAct loop a terracotta ramp deepening with budget (matched 62% ->
  3x 32% -> 10x solid; terracotta = the fig4a ungated / fig5 static
  colour);
- point labels follow the figure-wide naming alignment ("Bare LLM" ->
  "Bare model", "ReAct agent" -> "ReAct loop", the short "ReAct ..." d
  labels spelt out) and, except the system's, wrap to two lines so the
  full names fit the half-block column;
- x-axis title "Total LLM calls (96-turn suite)" -> "Total model calls
  (96-turn benchmark)" — the polished section 2.6 and the Fig. 6 legend
  (d) both say "model calls", and "suite" is retired paper-wide in
  favour of "benchmark" ("the 31-session process-aware benchmark");
- canvas 43.12 x 55 -> 48.12 x 55 mm (user direction: c/d widened after
  panel a narrowed to 79 mm).

Style: the fig6 house conventions (no in-figure title, single 6-pt
pure-black text, palette rev 7, absolute-mm geometry, 1200-dpi PNG + PDF,
text/collision guards, raster QA).

2026-09-14 repair pass (user direction, the fig6a batch): point labels
spelt out ("RNADesignAgent", "Bare LLM zero-shot/few-shot"); bare
few-shot colour khaki -> grey blue (colour assignments since retired in
the 2026-10-06 pass above).

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
W_MM, H_MM = 48.12, 55.0

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

AX_LEFT_MM, AX_W_MM = 8.6, 39.02
AX_BOT_MM, AX_H_MM = 7.3, 46.2

MARKER = {"platform": "s", "bare": "o", "react": "o"}


def blend_to_white(hex_color: str, frac_white: float) -> tuple[float, float, float]:
    p = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    return tuple(p + (1.0 - p) * frac_white)


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

    grey_blue = PALETTE_BY_NAME["grey_blue"]
    terracotta = PALETTE_BY_NAME["terracotta"]
    points = [
        # (label, x model calls, y delivered, color, dx_mm, dy_mm,
        #  x_dodge_calls, ha)
        ("RNADesignAgent", platform_llm, od["platform"]["delivered"],
         PALETTE_BY_NAME["sage_green"], 1.6, 0.0, 0.0, "left"),
        ("Bare model\nzero-shot", bare_llm, od["bare_zeroshot"]["delivered"],
         blend_to_white(grey_blue, 0.45), 1.1, 2.6, -20.0, "left"),
        ("Bare model\nfew-shot", bare_llm, od["bare_fewshot"]["delivered"],
         grey_blue, 1.6, -1.8, 20.0, "left"),
        ("ReAct loop\nmatched", react["matched"]["llm_calls_total"],
         od["react_matched"]["delivered"],
         blend_to_white(terracotta, 0.62), 2.0, -0.8, 0.0, "left"),
        ("ReAct loop\n3\u00d7", react["3x"]["llm_calls_total"],
         od["react_3x"]["delivered"],
         blend_to_white(terracotta, 0.32), 1.6, -1.6, 0.0, "left"),
        ("ReAct loop\n10\u00d7", react["10x"]["llm_calls_total"],
         od["react_10x"]["delivered"],
         terracotta, 3.7, 3.4, 0.0, "right"),
    ]

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)  # the guards below measure in final-raster pixels
    ax = fig.add_axes([AX_LEFT_MM / W_MM, AX_BOT_MM / H_MM,
                       AX_W_MM / W_MM, AX_H_MM / H_MM])
    ax.set_xlim(0, 850)
    ax.set_ylim(0, 104)
    ax.set_xticks([0, 200, 400, 600, 800])
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("Total model calls (96-turn benchmark)", labelpad=1.8)
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

    def rgb255(col) -> list[int]:
        if isinstance(col, str):
            return [int(col[i:i + 2], 16) for i in (1, 3, 5)]
        return [int(round(v * 255)) for v in col]

    point_cols = [rgb255(c) for _, _, _, c, _, _, _, _ in points]
    warm_grey = rgb255(PALETTE_BY_NAME["warm_grey"])
    for p in point_cols + [warm_grey]:
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # marker interiors blend the edge ink ring with the face colour; the
    # gradient line runs under the ReAct marker rings
    for p in point_cols[3:]:
        ok |= seg(warm_grey, p)
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig6d_cost_delivery (6 conditions; raster QA green -> "
          f"{W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
