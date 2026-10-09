#!/usr/bin/env python3
"""Supplementary Fig. S1 — Tertiary-structure inverse-folding validity pool:
per-candidate refold confidence and reference closeness, by reference
structure.

Every candidate of the 20 tertiary-structure benchmark tasks (73 in total,
zero new computation — the frozen Exp-38 pool aggregates the production
campaign's own quality fields) is one dot on two shared-row axes: left, the
RhoFold refold confidence of the designed sequence (mean pLDDT); right, the
alignment RMSD against the reference. Rows follow the Supplementary Table
S4 order; sage = meets the task's pass criteria, unfilled = fails it. The
pass/fail key sits inside the figure's top-right corner, one column. The
task pLDDT thresholds 65 and 70 and the RMSD gates 2.0/3.0 A carry in the
Note S1.2 text (no reference marks are drawn); the per-reference candidate
and pass counts carry in Table S4.

Reference names follow the RCSB entity titles (fact-checked 2026-10-09
against the deposited entries): 1F7U is yeast tRNA-Arg from the
arginyl-tRNA synthetase complex, 1Y26 the Vibrio vulnificus adenine
riboswitch, 2GDI and 3D2V TPP riboswitches (3D2V the eukaryotic one), and
1GID / 1HR2 the Tetrahymena group I intron P4-P6 domain and its DelC209
mutant. The historical benchmark-task source labels (theophylline aptamer,
hairpin ribozyme, T-box, SAM-I) were wrong and are corrected in the task
JSONs by the same-date repo-wide sweep.

2026-10-09 figure-fix batches (user-directed, Nature-style): the in-figure
pooled-pass headline is retired (Nature titles/results lines live in the
legend; 28/73 = 38.4% stays carried by the Table S4 column sums, the
frozen Exp-38 summary and the fact sheet), the 0-3 A RMSD-gate shaded
band, its legend entry, the dashed pLDDT-threshold lines and their legend
entry, and the per-row right-margin pass counts are all retired (user
points 7-8 and 11; every retired fact stays carried by Note S1.2 or Table
S4), the legend moved inside the figure's top-right corner as one column
(user point 10) with marker stroke and size matching the plotted dots
(user point 9), and the RMSD axis label uses the registered term
alignment RMSD.

The panel makes the uneven outcome of Note 1 S1.2 visible: among the
designs of 154 nt or longer, RhoDesign's 23 refold at pLDDT 24.6-29.1
while RiboDiffusion's 7 (158-nt designs against the two Tetrahymena
references) refold at 70.0-70.7; the hammerhead-ribozyme tasks are the
cleanest negative (0/18 at the second-lowest RMSD median of the panel),
and the near-reference corner is essentially empty apart from the two
1Y26 candidates. Every number is asserted against the frozen pool summary
and records.

Style: house conventions (no in-figure title, single 6-pt pure-black text,
palette rev 7, absolute-mm geometry, no tight crop, 1200-dpi PNG + vector
PDF, text/collision guards, raster QA).

Data  : experiments/results/exp38_tertiary_validity_pool/{summary,records}.*
Usage : python experiments/plots/figS1_tertiary_validity_pool.py
Output : experiments/plots/output/figS1_tertiary_validity_pool.{pdf,png}
"""

from __future__ import annotations

import hashlib
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import (  # noqa: E402
    PALETTE_BY_NAME,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp38_tertiary_validity_pool"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 50.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)

C_PASS = PALETTE_BY_NAME["sage_green"]      # pass (the house positive)
C_FAIL = PALETTE_BY_NAME["dark_warm_grey"]  # reserved neutral-dark semantic

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

# rows follow the Supplementary Table S4 order; short names here, the full
# RCSB-anchored reference names live in the Table S4 Reference column
REFS = [
    ("1F7U", "tRNA-Arg"),
    ("1EHZ", "tRNA-Phe"),
    ("1Y26", "Adenine riboswitch"),
    ("1GID", "Group I intron P4-P6"),
    ("1HR2", "P4-P6 (DelC209)"),
    ("2GDI", "TPP riboswitch"),
    ("3D2V", "TPP riboswitch"),
    ("1MME", "Hammerhead"),
]
EXPECT_PER_REF = {  # n_candidates / n_pass_rubric, from the frozen summary
    "1F7U": (14, 14), "1EHZ": (5, 4), "1Y26": (2, 2), "1GID": (12, 2),
    "1HR2": (11, 3), "2GDI": (7, 2), "3D2V": (4, 1), "1MME": (18, 0),
}

# geometry (mm): shared-row label column, two x axes; the pass/fail key sits
# inside the RMSD panel's empty top-right corner (top-row data ends at 19.6 A)
LBL_R_MM = 26.4                 # row labels right-align here (AX1_L - y-pad)
AX1_L, AX1_W = 28.0, 21.5       # pLDDT axis (ends 49.5 mm)
AX2_L, AX2_W = 51.0, 34.0       # RMSD axis (ends 85.0 mm)
AX_BOT, AX_H = 10.0, 38.0       # axes 10-48 mm

PLDDT_LIM = (20.0, 90.0)
PLDDT_TICKS = [25, 50, 75]
RMSD_LIM = (0.0, 30.0)
RMSD_TICKS = [0, 10, 20, 30]


def _jit(cid: str) -> float:
    """Deterministic per-candidate row jitter in [-0.20, 0.20] row units."""
    h = int(hashlib.sha256(cid.encode()).hexdigest()[:8], 16)
    return (h / 0xFFFFFFFF - 0.5) * 0.40


def main() -> int:
    summary = json.loads((RESULT_DIR / "summary.json").read_text(encoding="utf-8"))
    recs = [json.loads(l) for l in
            (RESULT_DIR / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # ---- frozen-number assertions -------------------------------------------------
    pooled = summary["pooled"]
    assert len(recs) == pooled["n_candidates"] == 73
    assert pooled["n_pass_rubric"] == 28 and pooled["n_pass_plddt"] == 31
    assert pooled["n_pass_rmsd"] == 1 and pooled["n_rmsd_gated"] == 14
    assert abs(pooled["pass_rate"] - 0.3835616438356164) < 1e-12
    assert summary["n_tasks"] == 20 and summary["n_tasks_with_any_pass"] == 12
    assert st.median(r["rhofold_mean_plddt"] for r in recs) == pooled["plddt"]["median"]
    assert st.median(r["alignment_rmsd"] for r in recs) == pooled["rmsd"]["median"]
    assert {r["mean_plddt_threshold"] for r in recs} == {65.0, 70.0}
    assert sum(1 for r in recs if r["rmsd_threshold"] is not None) == 14
    assert {r["rmsd_threshold"] for r in recs if r["rmsd_threshold"] is not None} == {2.0, 3.0}
    for ref, (n, npass) in EXPECT_PER_REF.items():
        rows = [r for r in recs if r["paper_reference"] == ref]
        assert len(rows) == n and sum(r["pass_rubric"] for r in rows) == npass, ref

    by_ref = {ref: [r for r in recs if r["paper_reference"] == ref]
              for ref, _ in REFS}
    assert sum(len(v) for v in by_ref.values()) == 73

    # ---- draw ----------------------------------------------------------------------
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))
    fig.set_dpi(DPI)
    ax1 = fig.add_axes([AX1_L / W_MM, AX_BOT / H_MM, AX1_W / W_MM, AX_H / H_MM])
    ax2 = fig.add_axes([AX2_L / W_MM, AX_BOT / H_MM, AX2_W / W_MM, AX_H / H_MM])
    for ax, xlim, ticks, xlabel in (
        (ax1, PLDDT_LIM, PLDDT_TICKS, "Refold confidence (mean pLDDT)"),
        (ax2, RMSD_LIM, RMSD_TICKS, "Alignment RMSD (\u00c5)"),
    ):
        ax.set_xlim(*xlim)
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks])
        ax.set_xlabel(xlabel, labelpad=2.0)
        ax.tick_params(axis="x", length=2, pad=1.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
    ax1.set_ylim(-0.6, len(REFS) - 0.4)
    ax1.set_yticks(range(len(REFS)))
    ax1.set_yticklabels(
        [f"{pdb} {name}" for pdb, name in REFS], fontsize=FONT)
    ax1.tick_params(axis="y", length=0, pad=1.6)
    ax1.spines["left"].set_visible(True)
    ax2.set_ylim(-0.6, len(REFS) - 0.4)
    ax2.set_yticks([])

    for row, (ref, _) in enumerate(REFS):
        for r in by_ref[ref]:
            y = row + _jit(r["candidate_id"])
            (ax1 if r["pass_rubric"] else ax1).scatter(
                [r["rhofold_mean_plddt"]], [y],
                s=9 if r["pass_rubric"] else 10,
                facecolor=C_PASS if r["pass_rubric"] else "none",
                edgecolor=C_PASS if r["pass_rubric"] else C_FAIL,
                linewidth=0.5, zorder=3)
            ax2.scatter([r["alignment_rmsd"]], [y],
                        s=9 if r["pass_rubric"] else 10,
                        facecolor=C_PASS if r["pass_rubric"] else "none",
                        edgecolor=C_PASS if r["pass_rubric"] else C_FAIL,
                        linewidth=0.5, zorder=3)

    # pass/fail key inside the RMSD panel's top-right corner, one column,
    # tucked close to the corner; the marker stroke (0.5) and size match
    # the plotted dots
    leg_handles = [
        plt.Line2D([], [], color=C_PASS, marker="o", ms=3.4,
                   lw=0, label="pass"),
        plt.Line2D([], [], color=C_FAIL, marker="o", ms=3.4,
                   lw=0, mfc="none", markeredgewidth=0.5, label="fail"),
    ]
    key = ax2.legend(handles=leg_handles, loc="upper right", ncol=1,
                     fontsize=FONT, handlelength=1.0, handletextpad=0.4,
                     labelspacing=0.55, borderaxespad=0.45, frameon=False)
    for t in key.get_texts():
        t.set_color(INK)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guards: every text inside the canvas; pairwise text-text non-collision
    texts = (list(ax1.get_xticklabels()) + list(ax2.get_xticklabels())
             + [ax1.xaxis.label, ax2.xaxis.label]
             + list(ax1.get_yticklabels())
             + list(key.get_texts()))
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

    # guard: row labels end left of the pLDDT axis
    ax1_x0 = AX1_L / W_MM * fig.bbox.width
    for t in ax1.get_yticklabels():
        assert t.get_window_extent(renderer).x1 <= ax1_x0 - 1.0, \
            f"row label enters the axes: {t.get_text()!r}"

    # guards: the key stays fully inside the RMSD axes, and no data dot
    # (either panel's, with marker radius) falls inside the key box
    key_bb = key.get_window_extent(renderer)
    ax2_bb = ax2.get_window_extent(renderer)
    assert (key_bb.x0 >= ax2_bb.x0 and key_bb.y0 >= ax2_bb.y0
            and key_bb.x1 <= ax2_bb.x1 and key_bb.y1 <= ax2_bb.y1), \
        "key extends beyond the RMSD axes"
    pad_px = 3.0 * DPI / 72.0  # dot radius ~1.8 pt plus a hair
    for row, (ref, _) in enumerate(REFS):
        for r in by_ref[ref]:
            for ax, xv in ((ax1, r["rhofold_mean_plddt"]),
                           (ax2, r["alignment_rmsd"])):
                yv = row + _jit(r["candidate_id"])
                px, py = ax.transData.transform((xv, yv))
                assert not (key_bb.x0 - pad_px <= px <= key_bb.x1 + pad_px
                            and key_bb.y0 - pad_px <= py <= key_bb.y1 + pad_px), \
                    f"data dot under the key: {r['candidate_id']}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figS1_tertiary_validity_pool.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA: exact canvas, clean border, palette purity
    img = mpimg.imread(OUT_DIR / "figS1_tertiary_validity_pool.png")
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

    for hexc in (C_PASS, C_FAIL):
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # adjacent pass/fail dots can touch, so anti-aliased pixels may blend a
    # dot colour, the other dot colour and white; the allowed region is the
    # triangle spanned by the two dot colours and white
    sage_rgb = np.array([int(C_PASS[i:i + 2], 16) for i in (1, 3, 5)], float)
    dark_rgb = np.array([int(C_FAIL[i:i + 2], 16) for i in (1, 3, 5)], float)
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

    hull_ok = np.array([
        _pt_tri(c, sage_rgb, dark_rgb, white_rgb) <= 8.0 for c in uni
    ])
    ok |= hull_ok
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"

    print(f"wrote figS1_tertiary_validity_pool (73 candidates over 8 references; "
          f"raster QA green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
