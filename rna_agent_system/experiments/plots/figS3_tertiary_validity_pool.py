#!/usr/bin/env python3
"""Supplementary Fig. S3 — Tertiary-structure design validity pool: per-
candidate refold confidence and reference closeness, by reference structure.

Every candidate of the 20 tertiary-structure benchmark tasks (73 in total,
zero new computation — the frozen Exp-38 pool aggregates the production
campaign's own quality fields) is one dot on two shared-row axes: left, the
RhoFold refold confidence of the designed sequence (mean pLDDT, dashed
lines at the task thresholds 65 and 70); right, the refold-versus-reference
alignment RMSD (the shaded 0-3 A band marks the RMSD-gated tasks' bounds,
registered by 3 of the 20 tasks / 14 candidates). Rows follow the
Supplementary Note 2 S2.3 table order; sage = passes the task rubric,
unfilled = fails it; the per-row right margin prints rubric pass / n.

The panel makes the mixed outcome of Note S2.3 visible: confident refolds
concentrate on three of the eight references (1F7U 14/14, 1EHZ 4/5, 1Y26
2/2), the hammerhead-ribozyme tasks are the cleanest negative (0/18 at the
lowest RMSD median of the panel), and the near-reference corner is
essentially empty apart from the two 1Y26 candidates. Every number is
asserted against the frozen pool summary and records.

Style: house conventions (no in-figure title, single 6-pt pure-black text,
palette rev 7, absolute-mm geometry, no tight crop, 1200-dpi PNG + vector
PDF, text/collision guards, raster QA).

Data  : experiments/results/exp38_tertiary_validity_pool/{summary,records}.*
Usage : python experiments/plots/figS3_tertiary_validity_pool.py
Output : experiments/plots/output/figS3_tertiary_validity_pool.{pdf,png}
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
    NEUTRAL_GRID,
    PALETTE_BY_NAME,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp38_tertiary_validity_pool"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 58.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)

C_PASS = PALETTE_BY_NAME["sage_green"]      # rubric pass (the house positive)
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

# rows follow the S2.3 per-reference table order; short names here, the
# full reference names live in the S2.3 table and the figure caption
REFS = [
    ("1F7U", "Theophylline"),
    ("1EHZ", "tRNA-Phe"),
    ("1Y26", "Hairpin"),
    ("1GID", "Group I intron"),
    ("1HR2", "P4-P6"),
    ("2GDI", "T-box"),
    ("3D2V", "SAM-I"),
    ("1MME", "Hammerhead"),
]
EXPECT_PER_REF = {  # n_candidates / n_pass_rubric, from the frozen summary
    "1F7U": (14, 14), "1EHZ": (5, 4), "1Y26": (2, 2), "1GID": (12, 2),
    "1HR2": (11, 3), "2GDI": (7, 2), "3D2V": (4, 1), "1MME": (18, 0),
}

# geometry (mm): shared-row label column, two x axes, right count margin
LBL_R_MM = 20.0                 # row labels right-align here
AX1_L, AX1_W = 21.0, 26.0       # pLDDT axis
AX2_L, AX2_W = 49.0, 30.0       # RMSD axis
AX_BOT, AX_H = 14.0, 36.0
CNT_L_MM = 80.3                 # per-row pass-count margin

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
        (ax2, RMSD_LIM, RMSD_TICKS, "Refold\u2013reference RMSD (\u00c5)"),
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

    # threshold reference marks: pLDDT task thresholds 65/70 (dashed),
    # RMSD-gated bounds 2-3 A (shaded band over 0-3 A)
    for x in (65.0, 70.0):
        ax1.axvline(x, color=C_FAIL, lw=0.5, ls=(0, (4, 3)), zorder=1)
    ax2.axvspan(0.0, 3.0, color=NEUTRAL_GRID, zorder=0)

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

    # per-row rubric pass counts, right margin
    count_texts = []
    for row, (ref, _) in enumerate(REFS):
        n, npass = EXPECT_PER_REF[ref]
        count_texts.append(fig.text(
            CNT_L_MM / W_MM, (AX_BOT + AX_H * (1 - (row + 0.5) / len(REFS))) / H_MM,
            f"{npass}/{n}", ha="left", va="center", fontsize=FONT, color=INK))

    # pooled outcome, one line above the axes
    head = fig.text(
        (AX1_L + (AX2_L + AX2_W - AX1_L) / 2) / W_MM, (AX_BOT + AX_H + 2.6) / H_MM,
        "pooled rubric pass 28/73 (38.4%) \u00b7 12/20 tasks with \u22651 passing candidate",
        ha="center", va="center", fontsize=FONT, color=INK)

    # legend row under the figure: the two dot encodings + the two marks
    y0 = (AX_BOT - 6.6) / H_MM
    leg_x = AX1_L / W_MM
    leg_items = [
        (C_PASS, "filled", "rubric pass"),
        (C_FAIL, "open", "rubric fail"),
        (C_FAIL, "dashed", "pLDDT thresholds 65/70"),
        (NEUTRAL_GRID, "band", "RMSD gates 2\u20133 \u00c5"),
    ]
    leg_handles = []
    for color, kind, label in leg_items:
        if kind == "filled":
            leg_handles.append(plt.Line2D([], [], color=color, marker="o", ms=2.4,
                                          lw=0, label=label))
        elif kind == "open":
            leg_handles.append(plt.Line2D([], [], color=color, marker="o", ms=2.4,
                                          lw=0, mfc="none", label=label))
        elif kind == "dashed":
            leg_handles.append(plt.Line2D([], [], color=color, lw=0.6,
                                          ls=(0, (4, 3)), label=label))
        else:
            leg_handles.append(plt.Rectangle((0, 0), 1, 1, fc=color, ec="none",
                                             label=label))
    key = fig.legend(handles=leg_handles, loc="lower left",
                     bbox_to_anchor=(leg_x, 0.008), ncol=2,
                     fontsize=FONT, handlelength=1.3, handletextpad=0.4,
                     columnspacing=1.0, frameon=False)
    for t in key.get_texts():
        t.set_color(INK)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # guards: every text inside the canvas; pairwise text-text non-collision
    texts = (list(ax1.get_xticklabels()) + list(ax2.get_xticklabels())
             + [ax1.xaxis.label, ax2.xaxis.label]
             + list(ax1.get_yticklabels()) + count_texts + [head]
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

    # guard: row labels end left of the pLDDT axis; counts right of the RMSD axis
    ax1_x0 = AX1_L / W_MM * fig.bbox.width
    ax2_x1 = AX2_L + AX2_W
    for t in ax1.get_yticklabels():
        assert t.get_window_extent(renderer).x1 <= ax1_x0 - 1.0, \
            f"row label enters the axes: {t.get_text()!r}"
    for t in count_texts:
        assert t.get_window_extent(renderer).x0 >= ax2_x1 / W_MM * fig.bbox.width + 0.5, \
            f"count enters the axes: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figS3_tertiary_validity_pool.{ext}", dpi=DPI)
    plt.close(fig)

    # raster QA: exact canvas, clean border, palette purity
    img = mpimg.imread(OUT_DIR / "figS3_tertiary_validity_pool.png")
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

    for hexc in (C_PASS, C_FAIL, NEUTRAL_GRID):
        p = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        ok |= seg(p, [0, 0, 0]) | seg(p, [255, 255, 255])
    # dots sit on the dashed threshold lines and inside the shaded band, so
    # anti-aliased pixels blend up to three of the drawn inks (dot colour x
    # line/band colour x white); the allowed region is the tetrahedron
    # spanned by the two dot colours, the band grey and white
    sage_rgb = np.array([int(C_PASS[i:i + 2], 16) for i in (1, 3, 5)], float)
    dark_rgb = np.array([int(C_FAIL[i:i + 2], 16) for i in (1, 3, 5)], float)
    grid_rgb = np.array([int(NEUTRAL_GRID[i:i + 2], 16) for i in (1, 3, 5)], float)
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

    verts = (sage_rgb, dark_rgb, grid_rgb, white_rgb)
    faces = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    hull_ok = np.array([
        min(_pt_tri(c, verts[i], verts[j], verts[k]) for i, j, k in faces) <= 8.0
        for c in uni
    ])
    ok |= hull_ok
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"

    print(f"wrote figS3_tertiary_validity_pool (73 candidates over 8 references; "
          f"raster QA green -> {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
