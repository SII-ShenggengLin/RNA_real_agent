#!/usr/bin/env python3
"""Fig. 2f — small-molecule oracle two-sided boundary (forest dot + CI).

Re-lettered g → f on 2026-09-11 (user direction) when the IRES panel moved
out of Fig. 2 to Supplementary Fig. S1; data and rendering unchanged.

Four AUROC rows on one axis: the deployed small-molecule service on its own
official held-out test splits (in-distribution) versus the literature
short-aptamer panel (out-of-distribution). Horizontal bars are
stratified-bootstrap 95% CIs; the dot is the point AUROC, printed with its
CI directly above each dot.

Figure revision 2026-10-02 (user-adjudicated, text-consistency pass):
(i) the "(OOD)" abbreviation spelled out as "(out-of-distribution)" — the
manuscript never defines OOD (the Fig. 2f legend writes "out-of-distribution
short aptamers"); the aptamer rows now carry four-line labels and the panel
is 58 → 62 mm tall to keep the label blocks clear of each other. (ii) The
printed point estimates and CIs now use the manuscript's three-decimal
half-up rounding (0.974 (0.968–0.980), 0.983 (0.961–0.997), 0.722
(0.278–1.000), 0.563 (0.063–1.000)) — the earlier two-decimal CIs rounded
0.997 to 1.00 and the point estimate 0.5625 to 0.562 against the text's
0.563. (iii) The x-axis reads "AUROC" — plain metric name, the Fig. 4c
convention; the deployed-service provenance is carried by the body and the
caption. (iv) n prints with the manuscript's thousands separator
(n = 1,492). (v) Same-day follow-up (user-adjudicated): the out-of-
distribution rows read "Short aptamers" — the body/legend term, "panel"
being internal register vocabulary — and the two control classes read
"vs random molecules" / "vs close analogues", plain descriptions keeping
the body's word roots (the §2.2 sentence was synced to the same wording:
"against random molecules and close analogues"); the x-axis lost its
"(deployed service)" qualifier at the same time.

Colours (palette rev 7): in-distribution rows in the RNA–small-molecule
workflow's khaki; out-of-distribution rows in the held-out dark warm grey
(the palette's neutral-dark semantic for undemonstrated power, matching the
fig2d miss / fig2e nonzero convention).

Data  : experiments/results/exp7_rnasmol_boundary/summary.json
Usage : python experiments/plots/fig2f_rnasmol_boundary.py
Output : experiments/plots/output/fig2f_rnasmol_boundary.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT, PALETTE_BY_NAME, WORKFLOW_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp7_rnasmol_boundary"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6  # single font size for every in-figure text element

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

C_IN_DIST = WORKFLOW_COLORS["rna_small_molecule_interaction"]  # khaki #CDBF9E
C_OOD = PALETTE_BY_NAME["dark_warm_grey"]                      # #7A7672

X_MAX = 1.08  # headroom so the hi = 1.0 CI caps clear the panel edge


def fmt3(v: float) -> str:
    """Manuscript three-decimal half-up rounding (0.5625 → "0.563", not
    the float half-even "0.562" — the body text writes 0.563)."""
    return str(Decimal(repr(v)).quantize(Decimal("0.001"),
                                         rounding=ROUND_HALF_UP))


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp7_rnasmol_boundary.py --summary first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))

    def block(parent: dict, key: str) -> dict:
        b = parent[key]
        return {
            "auroc": b["point_auroc"],
            "lo": b["auroc_ci95"][0],
            "hi": b["auroc_ci95"][1],
        }

    rows = [
        {
            "label": "ROBIN test\n(in-distribution)\nn = "
                     f"{s['robin_test']['n_scored']:,}",
            "color": C_IN_DIST,
            **block(s, "robin_test"),
        },
        {
            "label": "PDB test\n(in-distribution)\nn = "
                     f"{s['pdb_test']['n_scored']:,}",
            "color": C_IN_DIST,
            **block(s, "pdb_test"),
        },
        {
            "label": "Short aptamers\n(out-of-distribution)\n"
                     "vs random molecules\nn = "
                     f"{s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_random_chem']:,}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_random_chem"),
        },
        {
            "label": "Short aptamers\n(out-of-distribution)\n"
                     "vs close analogues\nn = "
                     f"{s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_near_cognate']:,}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_near_cognate"),
        },
    ]

    fig_w, fig_h = 88 / 25.4, 62 / 25.4  # single-column panel (62 mm: the
    # four-line out-of-distribution row labels need the extra height)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # absolute-mm geometry: 24 mm label column | plot to the right edge
    ax = fig.add_axes([
        24 / 25.4 / fig_w, 9 / 25.4 / fig_h,
        ((88 - 27) / 25.4) / fig_w, (62 - 9 - 7) / 25.4 / fig_h,
    ])

    ys = list(range(len(rows)))[::-1]  # first row on top

    # annotation width in axis units (19 chars at FONT pt over the axis width)
    ax_w_mm = (88 - 27)
    half_w = (19 * FONT * 0.5 / 25.4 * 1.15) / ax_w_mm * (X_MAX - 0.0) / 1.0

    for y, row in zip(ys, rows):
        ax.plot([row["lo"], row["hi"]], [y, y], color=row["color"],
                linewidth=1.4, solid_capstyle="butt", zorder=3)
        for x_edge in (row["lo"], row["hi"]):  # CI end caps
            ax.plot([x_edge, x_edge], [y - 0.09, y + 0.09], color=row["color"],
                    linewidth=0.9, zorder=3)
        ax.scatter(row["auroc"], y, s=22, c=row["color"],
                   edgecolors="white", linewidths=0.4, zorder=4)
        # point estimate (95% CI) above the dot, clamped inside the axis
        x_text = min(max(row["auroc"], half_w + 0.01), X_MAX - half_w - 0.01)
        ax.text(x_text, y + 0.16,
                f"{fmt3(row['auroc'])} ({fmt3(row['lo'])}–{fmt3(row['hi'])})",
                fontsize=FONT, va="bottom", ha="center", color=TEXT)

    ax.set_yticks(ys)
    ax.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                       linespacing=1.2, color=TEXT)

    ax.set_xlim(0.0, X_MAX)
    ax.set_ylim(-0.5, len(rows) - 0.35)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=FONT)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=2)
    ax.set_xlabel("AUROC", fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Pin one explicit crop box for both backends: the raster and vector
    # tight bboxes measure text extents at their own dpi and can disagree
    # by a few px at 1200 dpi (the right-hand CI annotations reach past
    # the axes' right edge); a shared box keeps the two canvases identical
    # by construction (the qa_fig2_figs.py PNG/PDF agreement check).
    # pad_inches is ignored for an explicit bbox, so the box is padded
    # here, and measured at the save dpi to avoid the 100-dpi pixel
    # quantization showing up at the canvas border.
    fig.set_dpi(1200)
    fig.canvas.draw()
    tb = fig.get_tightbbox(fig.canvas.get_renderer())  # inches
    pad = 0.02
    crop = matplotlib.transforms.Bbox(
        [[tb.x0 - pad, tb.y0 - pad], [tb.x1 + pad, tb.y1 + pad]])
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2f_rnasmol_boundary.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches=crop)
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: {row['auroc']} "
              f"({row['lo']}–{row['hi']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
