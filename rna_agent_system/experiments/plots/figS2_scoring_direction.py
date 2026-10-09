#!/usr/bin/env python3
"""Supplementary Fig. S2 — Scoring direction on vaccine and wild-type
sequences: each wild-type CDS against its own ten seeded random synonymous
resamples.

The primary analysis of the scoring-direction validation (Supplementary
Note 1 S1.3), drawn per target: ten open dots = the target's random
synonymous resamples, the black tick = their median, the filled dot = the
wild-type coding sequence on the shared score axis (total = -MFE +
codon_count * log(CAI)). Rows sort by the per-target delta (wild type minus
its resamples' median), descending; sage = the wild type scores above its
own median, terracotta = below (the five measured exceptions). No statistic
is computed here — per-target values are recomputed from the frozen records
and asserted equal to the frozen summary (sign 15/20, P = 0.041; above all
ten resamples on 12/20; the two vaccine CDSs, 260.7 and 404.8, are carried
in the Note S1.3 text only and are not drawn).

2026-10-09 figure-fix batch (user-directed, Nature style): the in-figure
results headline is retired (Nature titles and results lines live in the
caption; 15/20, P = 0.041 and 12/20 carry verbatim in Note S1.3, the sort
order in the figure legend), the score-axis label drops the "Composite
score" prefix and takes the Supplementary Table S1 registered formula form,
the target row labels take the Fig. 5c registered names (Greek beta for
beta-galactosidase, IFN-alpha2a closed up, SARS-CoV-2 spike lower case,
short forms HIV-1 gp120 / Influenza HA / RSV F / PDGFB), and the key is
shortened and moved into the panel's empty lower-right pocket (the five
below-median targets sort last and their data ends left of the pocket),
guarded to sit fully inside the axes and clear of every plotted datum.
Follow-up the same day (user-directed): the score axis extends one extra
100-unit block on the right (ending on its 400 tick) so the key sits well
clear of the last rows' resamples, with a minimum-gap guard of 2 mm
between the key frame and the nearest datum; the left and bottom margins
tightened to about 1.5 mm of ink (the label column and axis move left,
the canvas shrinks 67 to 63.9 mm and the axis widens to absorb the freed
width, leaving roughly 1.5 mm of ink on every side).

Style: house conventions (no in-figure title, single 6-pt pure-black text,
palette rev 7, absolute-mm geometry, no tight crop, 1200-dpi PNG + vector
PDF, text/collision guards, raster QA).

Data  : experiments/results/exp39_scoring_anchor_direction/{summary,records}.*
Usage : python experiments/plots/figS2_scoring_direction.py
Output : experiments/plots/output/figS2_scoring_direction.{pdf,png}
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
RESULT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp39_scoring_anchor_direction"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 63.9
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)

C_WIN = PALETTE_BY_NAME["sage_green"]        # WT above its own median
C_LOSE = PALETTE_BY_NAME["terracotta"]       # WT below (the five exceptions)
C_DRAW = PALETTE_BY_NAME["dark_warm_grey"]   # random synonymous resamples

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

LBL_R_MM = 18.9                 # row labels right-align here
AX_L, AX_W = 19.9, 62.6         # the score axis
AX_BOT, AX_H = 7.4, 55.0

DISPLAY = {  # target_id -> row label (Fig. 5c registered names)
    "A1AT": "A1AT", "Albumin": "Albumin", "Beta_galactosidase": "\u03b2-galactosidase",
    "EPO": "EPO", "GFP": "GFP", "Growth_hormone": "Growth hormone",
    "HER2": "HER2", "HIV-1_Env_gp120": "HIV-1 gp120",
    "HPV16_L1": "HPV16 L1", "IFN_alpha_2a": "IFN-\u03b12a", "IL-2": "IL-2",
    "Influenza_HA_H1N1": "Influenza HA", "Insulin": "Insulin",
    "Luciferase": "Luciferase", "OTC": "OTC", "Ovalbumin": "Ovalbumin",
    "PDGFB": "PDGFB", "RSV_F_protein": "RSV F",
    "SARS-CoV-2_Spike_WT": "SARS-CoV-2 spike", "Transferrin": "Transferrin",
}
EXPECT_EXCEPTIONS = {  # the five measured below-median targets (frozen)
    "GFP", "HPV16_L1", "Luciferase", "RSV_F_protein", "SARS-CoV-2_Spike_WT",
}


def main() -> int:
    summary = json.loads((RESULT_DIR / "summary.json").read_text(encoding="utf-8"))
    recs = [json.loads(l) for l in
            (RESULT_DIR / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # ---- frozen-number assertions -------------------------------------------------
    prim = summary["primary_stratified"]
    assert prim["n_targets"] == 20
    assert prim["n_wt_above_random_median"] == 15
    assert prim["n_wt_above_all_draws"] == 12
    assert prim["sign_test_p"] == 0.04138946533203125
    assert prim["wilcoxon_signed_rank_p_on_delta_vs_median"] == 0.00830841064453125

    wt = {r["target_id"]: r["total_score"] for r in recs if r["arm"] == "wt"}
    draws = {}
    for r in recs:
        if r["arm"] == "random":
            draws.setdefault(r["target_id"], []).append(r["total_score"])
    assert len(wt) == 20 and all(len(v) == 10 for v in draws.values()) and len(draws) == 20

    rows = []
    for t in prim["per_target"]:
        med = float(np.median(draws[t["target_id"]]))
        # recompute the frozen per-target comparison from the raw records
        assert med == t["random_median_total_score"], t["target_id"]
        assert wt[t["target_id"]] == t["wt_total_score"], t["target_id"]
        assert (wt[t["target_id"]] > med) == t["wt_above_median"], t["target_id"]
        above_all = wt[t["target_id"]] > max(draws[t["target_id"]])
        assert above_all == t["wt_above_all_draws"], t["target_id"]
        rows.append({
            "target": t["target_id"],
            "wt": t["wt_total_score"],
            "med": med,
            "draws": sorted(draws[t["target_id"]]),
            "delta": t["delta_vs_median"],
            "above": t["wt_above_median"],
        })
    assert {r["target"] for r in rows if not r["above"]} == EXPECT_EXCEPTIONS
    vac = {r["target_id"]: r["total_score"] for r in recs if r["arm"] == "vaccine"}
    assert round(vac["bnt162b2"], 1) == 260.7 and round(vac["mrna1273"], 1) == 404.8

    rows.sort(key=lambda r: -r["delta"])

    all_draws = [v for r in rows for v in r["draws"]]
    x_lo = min(all_draws)
    x_hi = max(all_draws + [r["wt"] for r in rows])
    # the right bound extends past the largest datum (ending on its tick)
    # so the key's lower-right pocket sits well clear of the data
    XLIM = (np.floor((x_lo - 8) / 50) * 50, np.ceil((x_hi + 58) / 100) * 100)

    # ---- draw ----------------------------------------------------------------------
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)
    ax = fig.add_axes([AX_L / W_MM, AX_BOT / H_MM, AX_W / W_MM, AX_H / H_MM])
    n = len(rows)
    ax.set_xlim(*XLIM)
    ax.set_ylim(n - 0.5, -0.5)                       # first row on top
    ax.set_yticks(range(n))
    ax.set_yticklabels([DISPLAY[r["target"]] for r in rows])
    ax.tick_params(axis="y", length=0, pad=1.6)
    tick_step = 100 if XLIM[1] - XLIM[0] <= 500 else 200
    ticks = list(range(int(XLIM[0]), int(XLIM[1]) + 1, tick_step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    ax.set_xlabel("\u2212MFE + codons\u00b7log(CAI)", labelpad=2.0)
    ax.tick_params(axis="x", length=2, pad=1.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, r in enumerate(rows):
        ax.scatter(r["draws"], [i] * len(r["draws"]), s=6, facecolor="none",
                   edgecolor=C_DRAW, linewidth=0.45, zorder=2)
        ax.plot([r["med"], r["med"]], [i - 0.26, i + 0.26], color=INK,
                lw=0.7, zorder=3, solid_capstyle="butt")
        ax.scatter([r["wt"]], [i], s=16,
                   facecolor=C_WIN if r["above"] else C_LOSE,
                   edgecolor=C_WIN if r["above"] else C_LOSE,
                   linewidth=0.5, zorder=4)

    # key, in the panel's empty lower-right pocket (marker sizes and strokes
    # match the plotted dots); guarded below to clear every datum
    key = ax.legend(handles=[
        plt.Line2D([], [], color=C_WIN, marker="o", ms=4.0, lw=0,
                   label="Wild type above median"),
        plt.Line2D([], [], color=C_LOSE, marker="o", ms=4.0, lw=0,
                   label="Wild type below median"),
        plt.Line2D([], [], color=C_DRAW, marker="o", ms=2.45, lw=0,
                   mfc="none", markeredgewidth=0.45,
                   label="Synonymous resamples"),
        plt.Line2D([], [], color=INK, lw=0.7,
                   label="Resample median"),
    ], loc="lower right", bbox_to_anchor=(0.995, 0.015), ncol=1,
        fontsize=FONT, handlelength=1.1, handletextpad=0.4,
        labelspacing=0.35, borderpad=0.2, frameon=False)
    for t in key.get_texts():
        t.set_color(INK)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guards: text in canvas; pairwise text-text non-collision
    texts = (list(ax.get_xticklabels()) + list(ax.get_yticklabels())
             + [ax.xaxis.label] + list(key.get_texts()))
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

    # guard: row labels stay left of the axes
    ax_x0 = AX_L / W_MM * fig.bbox.width
    for t in ax.get_yticklabels():
        assert t.get_window_extent(renderer).x1 <= ax_x0 - 1.0, \
            f"row label enters the axes: {t.get_text()!r}"

    # guard: the key sits fully inside the axes and clear of every datum
    # (marker radius + a pixel of margin, per the figS1 key convention)
    lb = key.get_window_extent(renderer)
    ab = ax.get_window_extent(renderer)
    assert (lb.x0 >= ab.x0 and lb.x1 <= ab.x1
            and lb.y0 >= ab.y0 and lb.y1 <= ab.y1), "key outside the axes"
    inv = ax.transData.inverted()
    (kx0, ky0), (kx1, ky1) = inv.transform([(lb.x0, lb.y0), (lb.x1, lb.y1)])
    px0, py0 = ax.transData.transform((XLIM[0], n - 0.5))
    px1, py1 = ax.transData.transform((XLIM[1], -0.5))
    unit_x = (px1 - px0) / (XLIM[1] - XLIM[0])       # px per x-data unit
    unit_y = abs(py1 - py0) / n                      # px per row
    pxpt = DPI / 72.0                                # px per point
    radii = {("draw",): 1.225 * pxpt + 2.0, ("wt",): 2.0 * pxpt + 2.0}
    min_gap = None
    for i, r in enumerate(rows):
        for x, rpx in ([(v, radii[("draw",)]) for v in r["draws"]]
                       + [(r["med"], radii[("draw",)]), (r["wt"], radii[("wt",)])]):
            cx = min(max(x, kx0), kx1)
            cy = min(max(i, ky0), ky1)
            dx = (x - cx) * unit_x
            dy = (i - cy) * unit_y
            dist = (dx * dx + dy * dy) ** 0.5
            assert dist > rpx, \
                f"key overlaps datum: {r['target']} at {x:.1f}"
            gap = dist - rpx
            min_gap = gap if min_gap is None else min(min_gap, gap)
    gap_mm = min_gap / DPI * 25.4
    assert gap_mm >= 2.0, \
        f"key sits closer than 2 mm to a datum ({gap_mm:.2f} mm)"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figS2_scoring_direction.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA: exact canvas, clean border, palette purity
    img = mpimg.imread(OUT_DIR / "figS2_scoring_direction.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, img.shape
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    def seg(p, q, tol: float = 8.0):
        p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
        d = q - p
        t = np.clip(((uni - p) @ d) / (d @ d), 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for hexc in (C_WIN, C_LOSE, C_DRAW):
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # wild-type dots overlap their own draws' dots and the median ticks, so
    # anti-aliased pixels blend up to three inks: allow the tetrahedron
    # spanned by the three palette colours and white
    verts = [np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], float)
             for c in (C_WIN, C_LOSE, C_DRAW)] + [np.array([255.0, 255.0, 255.0])]

    def _pt_tri(P, A, B, C):
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

    faces = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    hull_ok = np.array([
        min(_pt_tri(c, verts[i], verts[j], verts[k]) for i, j, k in faces) <= 8.0
        for c in uni
    ])
    ok |= hull_ok
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"

    n_above = sum(r["above"] for r in rows)
    print(f"wrote figS2_scoring_direction (20 targets, {n_above} above own"
          f" median; raster QA green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
