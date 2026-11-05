#!/usr/bin/env python3
"""Fig. 4c — RNAsmol deployment-artifact fidelity (dumbbell with a live
verification fork).

The same deployed small-molecule oracle, its own official held-out test
splits. The v0.2.0 service (uppercased RNA vocab; the defect class) scored
AUROC 0.786 / 0.410 on these splits — a silent degradation with zero error
signals, caught only by profiling the deployed artifact against its own
publication. The preprocessing repair restored exact official parity, and
today both of the platform's shipped integration paths were re-verified
live, zero-intervention, on all 1,662 pairs (exp15): the default agent tool
path (whose wrapper uppercases + T→U-converts — verified applied on every
pair) and the verbatim service endpoint both deliver the published AUROCs
(0.975 / 0.986 and 0.974 / 0.983), with the endpoint arm bit-identical to
the registered exp7 evidence.

Per split the panel draws three points: the v0.2.0 pre-fix value as an open
circle — re-measured from the git-recovered artifact (commit 7262e54,
sha-asserted, sandbox port 8107, exp15 addendum `exp15_rnasmol_v020_sandbox`),
agreeing with the registered 2026-08-11 history within ≤ 0.009 — forking to
the two live arms (default tool path in terracotta, verbatim endpoint in
sage), each with its stratified-bootstrap 95% CI. The decomposition closes:
v0.2.0 (uppercase + rewritten adjacency) collapses while arm A (uppercase +
upstream-faithful adjacency) does not — the same case treatment on both
sides, so the adjacency rewrite carries the damage. Chance 0.5 solid, the
0.8 screening-gate line dashed (the fig3a/3b/fig4a reference convention).

Colours (palette rev 7): terracotta (#C08B7C) = the platform's default tool
path — the fig3e failure semantic, and the pre-fix open marker's edge; sage
(#A3B18A) = the verbatim service endpoint — the fig3e true/pass semantic;
connector + gate line in the held-out dark warm grey.

Style: the fig2d–fig4a conventions — no in-figure title (the headline lives
in the caption; Nature panels carry letters only), every text element one
font size, single-column geometry, legend as centred rows under the axes
box (two rows; see the 2026-10-10 note below).

Figure revision 2026-08-30 (user-directed): every text element pure black
#000000 (the fig3e convention — the chance tag was dark warm grey and the
remaining text near-black #1A1A1A); the x-axis label shortened to
"Screening AUROC" — the held-out-split clause is caption material, and the
long label centred on the shifted axes box read as a misplaced title;
the in-figure legend rewritten as strategy labels without the internal
version string or the provenance qualifiers ("Pre-fix preprocessing" /
"Tool-path normalization" / "Verbatim input" — the re-measured/live
provenance lives in the caption); the chance line retained
— the pre-fix PDB arm (0.420) falls below it, and the below-chance reading
is the panel's failure evidence (unlike fig2g/fig4a, whose dropped chance
lines carried no below-chance point).

2026-10-02 text sync (user-adjudicated, the Fig. 4 figure-by-figure pass):
the in-figure legend re-labelled "Pre-repair tool" / "Repaired tool,
normalized input" / "Repaired tool, verbatim input" — "pre-repair" takes
the polished caption's term, and both live arms are the repaired tool,
distinguished by input treatment (the agent tool path applies the
case-preserving normalization per pair; the endpoint receives verbatim
inputs). Measured one-row legend width 82.1 mm against the 88-mm canvas.

2026-10-10 legend rework (user-directed figure-repair pass, three rounds):
the one-row legend spanned 82 mm — wider than the axes box — so centring it
on the canvas pushed its left edge ~19 mm left of the axes into the
label-column gutter, leaving a detached blank band lower-left. The legend
is now TWO single-row legends sharing one left anchor: "Pre-repair tool"
(row 1) and "Repaired tool, verbatim input" (row 2) start at the same x
(user-directed column alignment), row 1's second entry ("Repaired tool,
normalized input") follows at the standard ~2.6-mm entry spacing (a
two-column grid instead sized column 1 to its wider row-2 entry, opening a
~15-mm gap inside row 1 — user-directed tightening), and the block is
centred on the axes box by row 1's ink width (user-directed centring).
Labels verbatim, one 6-pt size. The label column also tightened 22 ->
13.5 mm with the axes widened 61 -> 71 mm (a ~10-mm blank strip ran down
the canvas's left edge; the 88 x 50-mm canvas is unchanged so composite
scaling keeps the sibling panels' font parity), and the axes box moved up
1 mm (y0 12 -> 13 mm) to fund the second row. Renderer-bbox guards (canvas
containment, axes-span containment, column alignment, no overlap with the
x-axis label or between the rows) and a post-save raster QA carry the
layout.

2026-10-10 composite-grid batch (user-directed row/column alignment): the
canvas narrows to an exact 82.5 x 50 mm cell of the Fig. 4 two-column grid
(column 1; row 2 shares its height with fig4d), axes 71 -> 67 mm, saved
exact as before — the assembler now places every panel at scale 1.0, so
the 6-pt text size is shared across the whole composite without scaling.

Data  : experiments/results/exp15_rnasmol_fidelity/summary.json (live arms)
        + experiments/results/exp15_rnasmol_v020_sandbox/summary.json
        (the git-recovered v0.2.0 pre-fix arm, re-measured)
Usage : python experiments/plots/fig4c_rnasmol_fidelity.py
Output : experiments/plots/output/fig4c_rnasmol_fidelity.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_fidelity"
V020_DIR = PROJECT_ROOT / "experiments" / "results" / "exp15_rnasmol_v020_sandbox"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"   # 2026-08-30 user direction: every text element pure black
FONT = 6          # single font size for every in-figure text element
C_PRE = PALETTE_BY_NAME["terracotta"]     # #C08B7C — default tool path / pre-fix edge
C_POST = PALETTE_BY_NAME["sage_green"]    # #A3B18A — service endpoint (verbatim)
C_LINK = PALETTE_BY_NAME["dark_warm_grey"]  # #7A7672 — connectors + gate line
C_REF = NEUTRAL_GRID                        # chance reference line

# The registered v0.2.0 values (PAPER_FACT_SHEET E7 register, 2026-08-11) —
# fallback only; the panel's points come from the re-measured sandbox arm.
HIST_AUROC_REGISTERED = {"robin_test": 0.7864, "pdb_test": 0.4103}

ROW_META = [
    ("robin_test", "ROBIN test\nn = 1,492"),
    ("pdb_test", "PDB test\nn = 170"),
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

X_MIN, X_MAX = 0.0, 1.30  # 0–1 metric scale + label headroom


def ci_bar(ax, y: float, est: float, lo: float, hi: float, colour: str,
           size: float = 22.0) -> None:
    ax.plot([lo, hi], [y, y], color=colour, linewidth=1.3,
            solid_capstyle="butt", zorder=3)
    for x_edge in (lo, hi):
        ax.plot([x_edge, x_edge], [y - 0.07, y + 0.07], color=colour,
                linewidth=0.9, zorder=3)
    ax.scatter(est, y, s=size, c=colour, edgecolors="white",
               linewidths=0.4, zorder=4)


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp15_rnasmol_fidelity.py "
              "--summary first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    v020_path = V020_DIR / "summary.json"
    v020 = json.loads(v020_path.read_text(encoding="utf-8")) \
        if v020_path.exists() else None

    rows = []
    for split, label in ROW_META:
        pre = s[f"tool_layer::{split}"]
        post = s[f"service_endpoint::{split}"]
        if v020 is not None:
            hist = v020[f"v020_sandbox::{split}"]["point_auroc"]
            hist = float(hist)
        else:
            hist = HIST_AUROC_REGISTERED[split]
        rows.append({
            "split": split,
            "label": label,
            "hist": hist,
            "tool": (pre["point_auroc"], *pre["auroc_ci95"]),
            "endpoint": (post["point_auroc"], *post["auroc_ci95"]),
        })

    fig_w, fig_h = 82.5 / 25.4, 50 / 25.4  # exact grid cell (composite batch)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # 2026-10-10 pass two: label column 22 -> 13.5 mm and axes 61 -> 71 mm
    # (the 22-mm column left a ~10-mm blank strip down the canvas's left
    # edge); y0 12 -> 13 mm funds the second legend row (pass one);
    # 2026-10-10 composite-grid batch: canvas 88 -> 82.5 mm, axes 71 -> 67
    label_mm, ax_w, y0_mm, h_mm = 13.5, 67, 13, 32
    ax = fig.add_axes([label_mm / 25.4 / fig_w, y0_mm / 25.4 / fig_h,
                       ax_w / 25.4 / fig_w, h_mm / 25.4 / fig_h])

    # per split: three lanes — verbatim endpoint (top), fork point (middle,
    # v0.2.0 open marker), default tool path (bottom)
    def lanes(i: int) -> tuple[float, float, float]:
        base = 2.0 - i * 1.32
        return base, base - 0.30, base - 0.60  # endpoint, hist, tool

    y_top = lanes(0)[0] + 0.16

    for i, row in enumerate(rows):
        y_ep, y_h, y_tool = lanes(i)
        hist_x, tool, ep = row["hist"], row["tool"], row["endpoint"]
        # fork connectors from the historical marker to both live dots
        ax.plot([hist_x, ep[0]], [y_h, y_ep], color=C_LINK,
                linewidth=0.6, zorder=2)
        ax.plot([hist_x, tool[0]], [y_h, y_tool], color=C_LINK,
                linewidth=0.6, zorder=2)
        # v0.2.0 pre-fix: open marker (registered history, no CI)
        ax.scatter(hist_x, y_h, s=20, facecolors="white", edgecolors=C_PRE,
                   linewidths=1.0, zorder=4)
        # value label left of the fork marker — the below-placement sat on
        # the gate (0.8) / chance (0.5) reference lines
        ax.text(hist_x - 0.02, y_h, f"{hist_x:.3f}", fontsize=FONT,
                ha="right", va="center", color=INK, zorder=5)
        # live arms with CIs and printed values
        ci_bar(ax, y_ep, *ep, colour=C_POST)
        ax.text(ep[0] + 0.02, y_ep + 0.10, f"{ep[0]:.3f} ({ep[1]:.2f}–{ep[2]:.2f})",
                fontsize=FONT, va="bottom", ha="left", color=INK, zorder=5)
        ci_bar(ax, y_tool, *tool, colour=C_PRE, size=16.0)
        ax.text(tool[0] + 0.02, y_tool - 0.10,
                f"{tool[0]:.3f} ({tool[1]:.2f}–{tool[2]:.2f})",
                fontsize=FONT, va="top", ha="left", color=INK, zorder=5)

    # reference lines: chance solid grid grey, gate dashed dark warm grey
    for x, gate, label in ((0.5, False, "chance"), (0.8, True, "gate 0.8")):
        ax.plot([x, x], [-0.25, y_top], color=C_LINK if gate else C_REF,
                linewidth=0.7, linestyle=(0, (3, 2)) if gate else "-",
                zorder=1)
        ax.text(x, y_top + 0.05, label, fontsize=FONT, ha="center",
                va="bottom", color=INK, zorder=5)

    ax.set_yticks([lanes(i)[1] for i in range(len(rows))])
    ax.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                       linespacing=1.2, color=INK)
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(-0.25, y_top + 0.42)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=FONT)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=2)
    ax.set_xlabel("Screening AUROC", fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)

    # legend: two single-row legends sharing ONE left anchor (2026-10-10 pass
    # three). Row 1 = "Pre-repair tool" | "Repaired tool, normalized input"
    # at the standard ~2.6-mm entry spacing; row 2 = "Repaired tool, verbatim
    # input" starting at the same x as "Pre-repair tool" (user-directed
    # column alignment). The block is centred on the axes box by row 1's ink
    # width below (a two-column grid instead sized column 1 to its wider
    # row-2 entry, opening a ~15-mm gap inside row 1 — user-directed
    # tightening). Labels verbatim, one 6-pt size, entry spacing unchanged.
    handles_row1 = [
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor="white", markeredgecolor=C_PRE,
               markeredgewidth=0.8, label="Pre-repair tool"),
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor=C_PRE, markeredgecolor="white",
               markeredgewidth=0.4, label="Repaired tool, normalized input"),
    ]
    handles_row2 = [
        Line2D([], [], marker="o", linestyle="", markersize=3.4,
               markerfacecolor=C_POST, markeredgecolor="white",
               markeredgewidth=0.4, label="Repaired tool, verbatim input"),
    ]
    # anchor tops place the row inks at ~5.1-7.0 / ~2.3-4.2 mm from the
    # canvas floor; the legend frames pad ~0.85 mm around the ink (measured)
    ANCHOR_Y1, ANCHOR_Y2 = 0.1575, 0.102
    anchor_x = 0.27  # provisional; re-centred on the measured row-1 ink
    legend_kw = dict(loc="upper left", frameon=False, fontsize=FONT,
                     handlelength=1.0, handletextpad=0.35, columnspacing=0.9,
                     borderaxespad=0.0)
    leg_row1 = fig.legend(handles=handles_row1, ncols=2,
                          bbox_to_anchor=(anchor_x, ANCHOR_Y1), **legend_kw)
    leg_row2 = fig.legend(handles=handles_row2, ncols=1,
                          bbox_to_anchor=(anchor_x, ANCHOR_Y2), **legend_kw)

    # ---- layout guards (the figS1 convention) ------------------------------
    # Collision checks run on INK extents, not the padded legend frames: the
    # frames pad ~0.85 mm around the rows, so adjacent rows' frames would
    # touch even with a healthy ink gap. Markers sit ~3 mm left of the first
    # text (handle + handletextpad + outer pad), so each row's ink box
    # extends that far left of its text.
    fig.canvas.draw()

    def px2mm(v: float) -> float:
        return v * 25.4 / fig.dpi

    def ink_box(leg) -> tuple[float, float, float, float]:
        renderer = fig.canvas.get_renderer()
        bbs = [t.get_window_extent(renderer) for t in leg.get_texts()]
        return (min(b.x0 for b in bbs) - 3.0 / 25.4 * fig.dpi,
                min(b.y0 for b in bbs), max(b.x1 for b in bbs),
                max(b.y1 for b in bbs))

    # recentre the block: shift both anchors so row 1's ink (the wider row)
    # centres on the axes box, keeping the shared left anchor
    target_c = label_mm + ax_w / 2.0
    cur_c = px2mm(sum(ink_box(leg_row1)[::2]) / 2)
    anchor_x += (target_c - cur_c) / (fig_w * 25.4)
    leg_row1.set_bbox_to_anchor((anchor_x, ANCHOR_Y1))
    leg_row2.set_bbox_to_anchor((anchor_x, ANCHOR_Y2))
    fig.canvas.draw()

    fig_w_px, fig_h_px = fig.get_size_inches() * fig.dpi
    ink1 = ink_box(leg_row1)   # legend row 1 (pre | normalized)
    ink2 = ink_box(leg_row2)   # legend row 2 (verbatim, under pre)
    for name, (x0, y0, x1, y1) in (("legend row 1", ink1),
                                   ("legend row 2", ink2)):
        assert x0 >= 0 and y0 >= 0 and x1 <= fig_w_px and y1 <= fig_h_px, \
            f"{name} escapes the canvas"
        assert px2mm(x0) >= label_mm - 0.2, \
            f"{name} reaches {px2mm(x0):.2f} mm, left of the axes"
        assert px2mm(x1) <= label_mm + ax_w + 0.2, \
            f"{name} reaches {px2mm(x1):.2f} mm, right of the axes"
    # the shared anchor: row 2 sits directly under row 1's first entry
    assert abs(px2mm(ink1[0] - ink2[0])) <= 0.15, \
        (f"left edges misaligned: row 1 at {px2mm(ink1[0]):.2f} mm, "
         f"row 2 at {px2mm(ink2[0]):.2f} mm")
    # the block centred on the axes box (by row 1, the wider row)
    assert abs(px2mm((ink1[0] + ink1[2]) / 2) - target_c) <= 0.3, \
        f"legend block centre {px2mm((ink1[0] + ink1[2]) / 2):.2f} mm " \
        f"vs axes centre {target_c:.2f} mm"
    # display y grows upwards: gaps are lower element's top to upper's bottom
    assert px2mm(ink1[1] - ink2[3]) >= 0.4, "legend ink rows under 0.4 mm apart"
    renderer = fig.canvas.get_renderer()
    x_lab = ax.xaxis.label.get_window_extent(renderer)
    assert px2mm(x_lab.y0 - ink1[3]) >= 0.5, \
        "x-axis label to legend row 1 under 0.5 mm"
    assert px2mm(ink2[1]) >= 1.0, \
        "legend ink under 1.0 mm from the canvas floor"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # save at the true 88 x 50 mm single-column canvas — the panel is sparse,
    # and tight-cropping shrank it to 78 mm, which made the uniform 6-pt text
    # effectively oversized next to the sibling panels (the 2026-08-30 axis-
    # text review)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig4c_rnasmol_fidelity.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")

    # ---- raster QA on the saved PNG (the figS1 convention) -----------------
    # exact 88 x 50 mm at 1200 dpi; below the axes bottom (37 mm) the bands
    # are x-tick labels, x-axis label, then the two legend rows — the legend
    # rows must sit inside the axes span and keep >= 0.4 mm separation.
    img = np.array(Image.open(OUT_DIR / "fig4c_rnasmol_fidelity.png")
                   .convert("L"))
    assert img.shape == (int(50 / 25.4 * 1200), int(82.5 / 25.4 * 1200)), \
        img.shape
    ink = img < 250
    prof = ink.sum(axis=1)
    bands: list[tuple[float, float]] = []
    start = None
    for ypx in range(int(39.5 / 25.4 * 1200), img.shape[0]):
        if prof[ypx] > 0 and start is None:
            start = ypx
        elif prof[ypx] == 0 and start is not None:
            bands.append((start / 1200 * 25.4, ypx / 1200 * 25.4))
            start = None
    if start is not None:
        bands.append((start / 1200 * 25.4, img.shape[0] / 1200 * 25.4))
    assert len(bands) == 3, \
        f"expected x-label + two legend rows below the ticks, got {bands}"
    gaps = [bands[i + 1][0] - bands[i][1] for i in range(2)]
    assert min(gaps) >= 0.4, f"bottom-band gaps under 0.4 mm: {gaps}"
    assert 50.0 - bands[-1][1] >= 0.7, "legend under 0.7 mm from the floor"
    lefts: list[float] = []
    for name, (b0, b1) in zip(("x-axis label", "legend row 1", "legend row 2"),
                              bands):
        cc = np.where(ink[int(b0 / 25.4 * 1200):int(b1 / 25.4 * 1200), :]
                      .any(axis=0))[0]
        c0, c1 = cc.min() / 1200 * 25.4, cc.max() / 1200 * 25.4
        if name != "x-axis label":
            assert c0 >= label_mm - 0.2 and c1 <= label_mm + ax_w + 0.2, \
                f"{name} spans {c0:.2f}-{c1:.2f} mm, outside the axes"
            lefts.append(c0)
        print(f"QA {name}: rows {b0:.2f}-{b1:.2f} mm, cols {c0:.2f}-{c1:.2f} mm")
    # 0.3 mm tolerance: the markers share their column anchor, but the open
    # marker's 0.8-pt edge draws ~0.15 mm wider than the filled marker's
    # 0.4-pt edge, so the ink extents differ by a hair (the text-anchored
    # renderer guard keeps the strict 0.15-mm bound)
    assert abs(lefts[0] - lefts[1]) <= 0.3, \
        f"legend rows not first-column aligned: {lefts[0]:.2f} vs {lefts[1]:.2f} mm"
    # block centring: row 1 (the wider row) centres on the axes box
    r1 = bands[1]
    cc1 = np.where(ink[int(r1[0] / 25.4 * 1200):int(r1[1] / 25.4 * 1200), :]
                   .any(axis=0))[0]
    centre = (cc1.min() + cc1.max()) / 2 / 1200 * 25.4
    target_c = label_mm + ax_w / 2.0
    assert abs(centre - target_c) <= 0.4, \
        f"legend block centre {centre:.2f} mm vs axes centre {target_c:.2f} mm"
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: v0.2.0 {row['hist']:.4f} | "
              f"tool_layer {row['tool'][0]} {tuple(row['tool'][1:])} | "
              f"endpoint {row['endpoint'][0]} {tuple(row['endpoint'][1:])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
