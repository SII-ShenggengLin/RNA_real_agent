#!/usr/bin/env python3
"""Fig. 2g — small-molecule oracle two-sided boundary (forest dot + CI).

Four AUROC rows on one axis: the deployed RNAsmol service on its own official
held-out test splits (in-distribution) versus the literature short-aptamer
panel (out-of-distribution). Horizontal bars are stratified-bootstrap 95%
CIs; the dot is the point AUROC, printed with its CI directly above each dot.

Colours (palette rev 7): in-distribution rows in the RNA–small-molecule
workflow's khaki; out-of-distribution rows in the held-out dark warm grey
(the palette's neutral-dark semantic for undemonstrated power, matching the
fig2d miss / fig2f nonzero convention).

Figure revision 2026-08-28 (user-directed, second revision): removed the
in-figure title (Nature style — the headline lives in the caption, panels
carry letters only); every text element shares one font size and one colour
(black); uniform three-line row labels (name / contrast / n, n now the
total). Second revision (same day, user-directed): dropped the chance/gate
reference lines, the pass-region shading and the right-hand stats column;
the point estimate (95% CI) is printed above each dot inside the plot;
thinner CI bars; x-axis extended past 1 so the CI caps no longer touch the
panel edge.

Data  : experiments/results/exp7_rnasmol_boundary/summary.json
Usage : python experiments/plots/fig2g_rnasmol_boundary.py
Output : experiments/plots/output/fig2g_rnasmol_boundary.{pdf,png}
"""
from __future__ import annotations

import json
import sys
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
                     f"{s['robin_test']['n_scored']}",
            "color": C_IN_DIST,
            **block(s, "robin_test"),
        },
        {
            "label": "PDB test\n(in-distribution)\nn = "
                     f"{s['pdb_test']['n_scored']}",
            "color": C_IN_DIST,
            **block(s, "pdb_test"),
        },
        {
            "label": "Aptamer panel (OOD)\nvs random chemistry\n"
                     f"n = {s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_random_chem']}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_random_chem"),
        },
        {
            "label": "Aptamer panel (OOD)\nvs near-cognate\n"
                     f"n = {s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_near_cognate']}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_near_cognate"),
        },
    ]

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel (fig2b–f geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # absolute-mm geometry: 24 mm label column | plot to the right edge
    ax = fig.add_axes([
        24 / 25.4 / fig_w, 9 / 25.4 / fig_h,
        ((88 - 27) / 25.4) / fig_w, (58 - 9 - 7) / 25.4 / fig_h,
    ])

    ys = list(range(len(rows)))[::-1]  # first row on top

    # annotation width in axis units (17 chars at FONT pt over the axis width)
    ax_w_mm = (88 - 27)
    half_w = (17 * FONT * 0.5 / 25.4 * 1.15) / ax_w_mm * (X_MAX - 0.0) / 1.0

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
                f"{row['auroc']:.3f} ({row['lo']:.2f}–{row['hi']:.2f})",
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
    ax.set_xlabel("AUROC (deployed RNAsmol service)", fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2g_rnasmol_boundary.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: {row['auroc']} "
              f"({row['lo']}–{row['hi']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
