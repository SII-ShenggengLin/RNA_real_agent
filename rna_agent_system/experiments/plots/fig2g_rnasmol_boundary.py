#!/usr/bin/env python3
"""Fig. 2g — small-molecule oracle two-sided boundary (forest dot + CI).

Four AUROC rows on one chance-anchored axis: the deployed RNAsmol service on
its own official held-out test splits (in-distribution) versus the literature
short-aptamer panel (out-of-distribution). Horizontal bars are stratified-
bootstrap 95% CIs; the dot is the point AUROC.

Reference lines: chance (0.5, solid) and the 0.8 screening gate the capability
profile assigns this oracle (dashed).

Colours (palette rev 7): in-distribution rows in the RNA–small-molecule
workflow's khaki; out-of-distribution rows in the held-out dark warm grey
(the palette's neutral-dark semantic for undemonstrated power, matching the
fig2d miss / fig2f nonzero convention).

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
from palette import NEUTRAL_GRID, TEXT, PALETTE_BY_NAME, WORKFLOW_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp7_rnasmol_boundary"
OUT_DIR = PROJECT_ROOT / "plots" if False else PROJECT_ROOT / "experiments" / "plots" / "output"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

C_IN_DIST = WORKFLOW_COLORS["rna_small_molecule_interaction"]  # khaki #CDBF9E
C_OOD = PALETTE_BY_NAME["dark_warm_grey"]                      # #7A7672


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
            "label": "ROBIN test\n(in-distribution)",
            "n_label": f"n = {s['robin_test']['n_scored']}",
            "color": C_IN_DIST,
            **block(s, "robin_test"),
        },
        {
            "label": "PDB test\n(in-distribution)",
            "n_label": f"n = {s['pdb_test']['n_scored']}",
            "color": C_IN_DIST,
            **block(s, "pdb_test"),
        },
        {
            "label": "Aptamer panel\nvs random chemistry (OOD)",
            "n_label": f"n = {s['ood_aptamer']['n_binders']} + "
                       f"{s['ood_aptamer']['n_random_chem']}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_random_chem"),
        },
        {
            "label": "Aptamer panel\nvs near-cognate (OOD)",
            "n_label": f"n = {s['ood_aptamer']['n_binders']} + "
                       f"{s['ood_aptamer']['n_near_cognate']}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_near_cognate"),
        },
    ]

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel (fig2b–f geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.30, 0.17, 0.60, 0.70])

    ys = list(range(len(rows)))[::-1]  # first row on top
    ax.axvline(0.5, color=TEXT, linewidth=0.6, zorder=2)
    ax.axvline(0.8, color=TEXT, linewidth=0.6, linestyle=(0, (3, 2)), zorder=2)

    for y, row in zip(ys, rows):
        ax.plot([row["lo"], row["hi"]], [y, y], color=row["color"],
                linewidth=2.2, solid_capstyle="butt", zorder=3)
        for x_edge in (row["lo"], row["hi"]):  # CI end caps
            ax.plot([x_edge, x_edge], [y - 0.09, y + 0.09], color=row["color"],
                    linewidth=1.0, zorder=3)
        ax.scatter(row["auroc"], y, s=22, c=row["color"],
                   edgecolors="white", linewidths=0.4, zorder=4)
        # point estimate (CI) annotation at the right margin
        ha = "left"
        x_text = max(row["hi"] + 0.015, 0.86) if row["hi"] < 0.95 else row["hi"] + 0.015
        if x_text > 0.995:
            x_text, ha = row["lo"] - 0.015, "right"
        ax.text(x_text, y,
                f"{row['auroc']:.3f} ({row['lo']:.2f}–{row['hi']:.2f})",
                fontsize=5.2, va="center", ha=ha, color=row["color"])

    ax.set_yticks(ys)
    ax.set_yticklabels([r["label"] for r in rows], fontsize=5.4, linespacing=1.15)
    for tick, row in zip(ax.get_yticklabels(), rows):
        tick.set_color(row["color"])
    # n annotations under the row labels
    for y, row in zip(ys, rows):
        ax.text(-0.285, y - 0.24, row["n_label"], transform=ax.get_yaxis_transform(),
                fontsize=4.8, color=row["color"], va="top")

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.55, len(rows) - 0.45)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=5.5)
    ax.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)
    ax.set_xlabel("AUROC of the deployed RNAsmol service", fontsize=6, labelpad=2)
    for s_name in ("top", "right", "left"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="x", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # reference-line tags at the top of the panel
    ax.text(0.5, len(rows) - 0.52, "chance", fontsize=4.8, ha="center",
            va="bottom", color=TEXT)
    ax.text(0.8, len(rows) - 0.52, "0.8 screening gate", fontsize=4.8,
            ha="center", va="bottom", color=TEXT)

    ax.set_title("Small-molecule oracle — two-sided boundary",
                 loc="left", fontsize=6.5, pad=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2g_rnasmol_boundary.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].replace(chr(10), ' ')}: {row['auroc']} "
              f"({row['lo']}–{row['hi']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
