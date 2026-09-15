#!/usr/bin/env python3
"""Supplementary Fig. S2 — Aptamer constraint navigation across the quota
regime: delivered cells versus raw-candidate cap on the 39-target expanded
pool (the pre-registered budget sweep behind the main-text deployment rule).

One line per condition across the five pre-registered caps (16 / 20 / 24 /
32 / 48 raw candidates per target): GenNav navigation (sage) versus the
static grid (terracotta) — the Fig-5 arm colours. Delivered = pair-outcome
cells (39 targets x 3 length-class profiles = 117 cells). The per-cap
paired discordance (navigation-only b : static-only c) and the exact
McNemar P are printed under each cap; every number is asserted against the
frozen sweep summary. No statistic is computed here — the panel re-draws
the frozen verdicts verbatim.

The crossover between the 24- and 32-candidate caps is the figure's point:
navigation leads where the quota is scarce (10:2, P = 0.039 at the
starvation cap) and the static grid's exhaustive per-setting depth wins
where the quota is loose (12:30, P = 0.008 at 48) — the two-sided
operating signature of main-text section 2.5.

Style: house conventions (no in-figure title, single 6-pt pure-black text,
palette rev 7, absolute-mm geometry, no tight crop, 1200-dpi PNG + vector
PDF, text/collision guards, raster QA).

Data  : experiments/results/exp29_aptamer_campaign_arc/expanded_summary.json
Usage : python experiments/plots/figS2_aptamer_budget_sweep.py
Output : experiments/plots/output/figS2_aptamer_budget_sweep.{pdf,png}
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
SUMMARY = (
    PROJECT_ROOT
    / "experiments"
    / "results"
    / "exp29_aptamer_campaign_arc"
    / "expanded_summary.json"
)
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 58.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)

C_NAV = PALETTE_BY_NAME["sage_green"]    # navigation (the Fig-5 arm colour)
C_RULE = PALETTE_BY_NAME["terracotta"]   # static grid (the Fig-5 arm colour)

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

AX_LEFT_MM, AX_W_MM = 11.0, 73.0
AX_BOT_MM, AX_H_MM = 16.0, 36.2

CAPS = [16, 20, 24, 32, 48]
EXPECT_NAV = [10, 9, 18, 17, 34]          # delivered C arm (navigation)
EXPECT_STATIC = [2, 4, 15, 29, 52]        # delivered A arm (static grid)
EXPECT_BC = [(10, 2), (9, 4), (13, 10), (10, 22), (12, 30)]
EXPECT_P = [0.03857421875, 0.266845703125, 0.6776394844055176,
            0.050102459732443094, 0.007915897334896727]
XLIM = (14.9, 49.9)
YLIM = (0, 58)


def main() -> int:
    sweep = json.loads(SUMMARY.read_text(encoding="utf-8"))["caps"]
    nav, static, bc, pvals = [], [], [], []
    for cap in CAPS:
        v = sweep[str(cap)]
        assert v["n_targets"] == 39
        # arm labels as frozen: A = the static grid, C = navigation — the
        # mcnemar block disambiguates (b_nav_only counts navigation-only
        # discordant cells and must equal the C arm's delivered advantage)
        nav.append(v["delivered"]["C"])
        static.append(v["delivered"]["A"])
        m = v["mcnemar"]
        bc.append((m["b_nav_only"], m["c_rule_only"]))
        pvals.append(m["p_exact"])
    assert nav == EXPECT_NAV, nav
    assert static == EXPECT_STATIC, static
    assert bc == EXPECT_BC, bc
    assert pvals == EXPECT_P, pvals

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)  # the guards below measure in final-raster pixels
    ax = fig.add_axes([AX_LEFT_MM / W_MM, AX_BOT_MM / H_MM,
                       AX_W_MM / W_MM, AX_H_MM / H_MM])
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    # two-line tick labels carry the cap and the paired discordance
    # (navigation-only : static-only cells); the five exact-McNemar P
    # values are stated verbatim in the figure caption
    ax.set_xticks(CAPS)
    ax.set_xticklabels([
        f"{cap}\n{b}:{c}"
        for cap, (b, c) in zip(CAPS, bc)
    ], linespacing=1.35)
    ax.set_yticks([0, 10, 20, 30, 40, 50])
    ax.set_xlabel("Raw-candidate quota cap (per target)\n"
                  "under each cap: b : c = navigation-only : static-only"
                  " discordant cells", labelpad=2.4, linespacing=1.45)
    ax.set_ylabel("Delivered cells (of 117)", labelpad=1.8)
    ax.tick_params(length=2, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    x_mm = lambda v: AX_LEFT_MM + (v - XLIM[0]) / (XLIM[1] - XLIM[0]) * AX_W_MM
    y_mm = lambda v: AX_BOT_MM + (v - YLIM[0]) / (YLIM[1] - YLIM[0]) * AX_H_MM
    x_px = lambda v: x_mm(v) / 25.4 * DPI
    y_px = lambda v: y_mm(v) / 25.4 * DPI

    for xs, ys, color in ((CAPS, nav, C_NAV), (CAPS, static, C_RULE)):
        ax.plot(xs, ys, color=color, lw=0.8, zorder=2,
                solid_joinstyle="round")
        ax.scatter(xs, ys, s=13, facecolor=color, edgecolor=color,
                   linewidth=0.5, zorder=4)

    # mm -> data-unit conversions for label offsets (absolute-mm geometry)
    u_per_mm_x = (XLIM[1] - XLIM[0]) / AX_W_MM
    u_per_mm_y = (YLIM[1] - YLIM[0]) / AX_H_MM

    # per-point value labels: navigation above its marker, static grid below
    # (the cap-16 static marker sits 2 cells off the floor, so its label
    # moves to the right of the marker to stay clear of the axis)
    labels = []
    for cap, v in zip(CAPS, nav):
        labels.append(ax.text(cap, v + 1.1 * u_per_mm_y, str(v),
                              ha="center", va="bottom",
                              fontsize=FONT, color=INK))
    for cap, v in zip(CAPS, static):
        if cap == 16:
            # above the marker: the below placement would dip under the
            # axis floor (y = 2) and the left/right bands carry the line
            labels.append(ax.text(cap, v + 1.1 * u_per_mm_y, str(v),
                                  ha="center", va="bottom",
                                  fontsize=FONT, color=INK))
        else:
            # below the marker; cap 20 takes the tighter 1.1 mm drop so the
            # label stays above the axis floor, the rising-segment caps take
            # 1.5 mm to clear their incoming segments
            drop = 1.1 if cap == 20 else 1.5
            labels.append(ax.text(cap, v - drop * u_per_mm_y, str(v),
                                  ha="center", va="top",
                                  fontsize=FONT, color=INK))

    # per-cap paired discordance + exact McNemar P live in the tick labels;
    # their gloss is the xlabel's second line

    # one-row key, upper left (both curves start at the bottom of that corner)
    key = ax.legend(handles=[
        plt.Line2D([], [], color=C_NAV, lw=0.8, marker="o", ms=2.6,
                   label="GenNav navigation"),
        plt.Line2D([], [], color=C_RULE, lw=0.8, marker="o", ms=2.6,
                   label="Static grid"),
    ], loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=1,
        fontsize=FONT, handlelength=1.6, handletextpad=0.5,
        borderaxespad=0.0, frameon=False)
    for t in key.get_texts():
        t.set_color(INK)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guard: every text inside the canvas
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
             + [ax.xaxis.label, ax.yaxis.label]
             + labels + [t for t in fig.texts] + list(key.get_texts()))
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r}"
        boxes.append(bb)
    # guard: pairwise text-text non-collision
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"

    # guard: value labels clear of both curves' markers (0.30 mm clearance)
    mm_px = DPI / 25.4
    r_px = ((13 ** 0.5) / 2 + 0.25) / 72.0 * DPI
    mboxes = []
    for cap, v in list(zip(CAPS, nav)) + list(zip(CAPS, static)):
        cx, cy = x_px(cap), y_px(v)
        mboxes.append((cx - r_px, cy - r_px, cx + r_px, cy + r_px))
    for t in labels:
        bb = t.get_window_extent(renderer)
        for mx0, my0, mx1, my1 in mboxes:
            assert (bb.x1 <= mx0 - 0.30 * mm_px
                    or bb.x0 >= mx1 + 0.30 * mm_px
                    or bb.y1 <= my0 - 0.30 * mm_px
                    or bb.y0 >= my1 + 0.30 * mm_px), \
                f"text-marker collision: {t.get_text()!r}"

    # guard: value labels clear of both drawn polylines (line half-width
    # 0.4 pt + 0.25 mm clearance) — segment-to-rect distance
    def _pt_seg(p, a, b):
        a, b, p = np.asarray(a, float), np.asarray(b, float), np.asarray(p, float)
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

    clear_line = 0.4 / 72.0 * DPI / 2 + 0.25 * mm_px
    for t in labels:
        bb = t.get_window_extent(renderer)
        for xs_, ys_ in ((CAPS, nav), (CAPS, static)):
            pts = [tuple(ax.transData.transform((x, y)))
                   for x, y in zip(xs_, ys_)]
            for k in range(len(pts) - 1):
                assert _seg_rect(pts[k], pts[k + 1], bb) >= clear_line, \
                    f"text-line collision: {t.get_text()!r} x segment {k}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figS2_aptamer_budget_sweep.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA: exact canvas, clean border, palette purity
    img = mpimg.imread(OUT_DIR / "figS2_aptamer_budget_sweep.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, img.shape
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    def seg(p, q, tol: float = 8.0):
        p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
        d = q - p
        denom = float(d @ d)
        t = np.clip(((uni - p) @ d) / denom, 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for hexc in (C_NAV, C_RULE):
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # the two drawn lines cross between the 24- and 32-candidate caps: the
    # crossing pixels blend the two line colours with each other and with
    # the white background (three-ink anti-aliasing), so the allowed region
    # is the triangle spanned by the two line colours and white
    sage_rgb = np.array([int(C_NAV[i:i + 2], 16) for i in (1, 3, 5)], float)
    terra_rgb = np.array([int(C_RULE[i:i + 2], 16) for i in (1, 3, 5)], float)
    white_rgb = np.array([255.0, 255.0, 255.0])

    def _pt_tri(P, A, B, C):
        # point-to-triangle distance in RGB space (0 inside)
        AB, AC, AP = B - A, C - A, P - A
        d1 = AB @ AP
        d2 = AC @ AP
        if d1 <= 0 and d2 <= 0:
            return float(np.linalg.norm(P - A))
        BP = P - B
        d3, d4 = AB @ BP, AC @ BP
        if d3 >= 0 and d4 <= d3:
            return float(np.linalg.norm(P - B))
        vc = d1 * d4 - d3 * d2
        if vc <= 0 and d1 >= 0 and d3 <= 0:
            t = d1 / (d1 - d3)
            return float(np.linalg.norm(P - (A + t * AB)))
        CP = P - C
        d5, d6 = AB @ CP, AC @ CP
        if d6 >= 0 and d5 <= d6:
            return float(np.linalg.norm(P - C))
        vb = d5 * d2 - d1 * d6
        if vb <= 0 and d2 >= 0 and d6 <= 0:
            t = d2 / (d2 - d6)
            return float(np.linalg.norm(P - (A + t * AC)))
        va = d3 * d6 - d5 * d4
        if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
            t = (d4 - d3) / ((d4 - d3) + (d5 - d6))
            return float(np.linalg.norm(P - (B + t * (C - B))))
        denom = 1.0 / (va + vb + vc)
        v = vb * denom
        w = vc * denom
        return float(np.linalg.norm(P - (A + AB * v + AC * w)))

    tri_ok = np.array([
        _pt_tri(c, sage_rgb, terra_rgb, white_rgb) <= 8.0 for c in uni
    ])
    ok |= tri_ok
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"

    print(f"wrote figS2_aptamer_budget_sweep ({len(CAPS)} caps, "
          f"nav {nav} vs static {static}; raster QA green -> "
          f"{W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
