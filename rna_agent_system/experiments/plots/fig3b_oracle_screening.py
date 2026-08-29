#!/usr/bin/env python3
"""Fig. 3b — structure-oracle screening-power balloon matrix (reset run).

3 oracles (rows) × N aptamer targets (columns — 6 on the v2 summary, 9 on the
v3 extension; derived from the summary cells): per-cell binder-vs-negative
AUROC of the reset Exp-10 run, dual-encoded as bubble size and bubble colour;
the AUROC value is printed in every cell.  Reference mark: chance (0.5,
solid) on the colour bar.
Per-target anchor counts (binders + / negatives −) sit under the column
labels.

Chart type: balloon-matrix heatmap (CASCADE Fig. 3b / ERA Fig. 2b lineage),
registered in FIGURE_PLAN_V5.md row 3b.

Colours (palette rev 7): the continuous AUROC scale is a LinearSegmentedColormap
anchored on slate blue → sand → terracotta (all anchors from the mandated
twelve-colour set); gridlines use the non-data grey.

Figure revision 2026-08-29 (user-directed): in-figure title removed (Nature
style — the headline lives in the caption, panels carry letters only, and
letters are drawn at assembly time); every text element unified to one 6-pt
ink-black style — the cell values had been white on dark bubbles with a white
halo (added 2026-08-28 for two minimal-bubble cells), which left exactly
those cells illegible white-on-white; plain ink-black text without a halo is
readable at every bubble size on the muted palette; colour-bar label
shortened to the quantity alone (the reference-line meanings live in the
caption); width capped at the Nature 183-mm double-column maximum; pass ring
removed (same-day follow-up, user-directed — gate status is carried by the
printed values, and every bubble now renders identically); the dashed 0.8
gate line on the colour bar removed as well (same follow-up — only the
solid chance line remains).

Data  : experiments/results/exp10_structure_oracle_screening/summary.json
        (FIG3_SUMMARY env override — the v3 render points it at
        experiments/results/exp10_structure_oracle_screening_v3/summary.json)
Usage : python experiments/plots/fig3b_oracle_screening.py
Output: experiments/plots/output/fig3b_oracle_screening.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY = (
    PROJECT_ROOT / "experiments" / "results" / "exp10_structure_oracle_screening" / "summary.json"
)
import os
if os.environ.get("FIG3_SUMMARY"):
    SUMMARY = Path(os.environ["FIG3_SUMMARY"]).resolve()
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

ORACLE_ROWS = [
    "egarps_native_probability",
    "proteinx_ipTM",
    "rhofold_mean_plddt",
]
ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS+\nnative probability",
    "proteinx_ipTM": "ProteinX\nipTM",
    "rhofold_mean_plddt": "RhoFold\nmean pLDDT",
}
TARGET_LABELS = {
    "Thrombin": "Thrombin",
    "VEGF": "VEGF",
    "PDGF-BB": "PDGF-BB",
    "IL-17A": "IL-17A",
    "Angiopoietin-2": "Angiopoietin-2",
    "SARS-CoV-2 N": "SARS-CoV-2 N",
    "FGF2": "FGF2",
    "Influenza H3N2 HA": "swine H3 HA",
    "IFN-gamma": "IFN-\u03b3",
}
# v3 re-run endpoint: FIG3_SUMMARY points the script at the _v3 results and
# the target columns are derived from the summary cells (registered targets
# first, then new targets in first-appearance order) — no hardcoded 6.
V2_TARGET_ORDER = ["Thrombin", "VEGF", "PDGF-BB", "IL-17A", "Angiopoietin-2", "SARS-CoV-2 N"]


def _derive_targets(cells) -> list:
    seen = []
    for key in cells:
        _, _, target = key.partition(" | ")
        if target and target not in seen:
            seen.append(target)
    ordered = [t for t in V2_TARGET_ORDER if t in seen]
    ordered += [t for t in seen if t not in V2_TARGET_ORDER]
    return ordered
GATE = 0.8
CHANCE = 0.5
VMIN, VMAX = 0.1, 0.9

C_MAP = LinearSegmentedColormap.from_list(
    "auroc_morandi",
    [PALETTE_BY_NAME["slate_blue"], PALETTE_BY_NAME["sand"], PALETTE_BY_NAME["terracotta"]],
)

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


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    cells = summary["cells"]
    TARGET_COLS = _derive_targets(cells)

    fig, ax = plt.subplots(figsize=(min(183 / 25.4, 5.12 * len(TARGET_COLS) / 6), 1.95))
    norm = TwoSlopeNorm(vmin=VMIN, vcenter=CHANCE, vmax=VMAX)
    s_min, s_max = 30.0, 300.0

    n_cells = 0
    n_pass = 0
    for r, oracle in enumerate(ORACLE_ROWS):
        for c, target in enumerate(TARGET_COLS):
            cell = cells.get(f"{oracle} | {target}", {})
            if "auroc" not in cell:
                continue
            n_cells += 1
            auroc = cell["auroc"]
            frac = min(1.0, max(0.0, (auroc - VMIN) / (VMAX - VMIN)))
            size = s_min + frac * (s_max - s_min)
            color = C_MAP(norm(auroc))
            n_pass += int(auroc > GATE)
            ax.scatter(c, r, s=size, c=[color], edgecolors="white",
                       linewidths=0.5, zorder=3)
            ax.text(c, r, f"{auroc:.2f}", ha="center", va="center",
                    fontsize=FONT, color=TEXT, zorder=4)

    # per-target anchor counts under the column labels
    counts = {}
    for target in TARGET_COLS:
        first = next((cells[f"{o} | {target}"] for o in ORACLE_ROWS
                      if f"{o} | {target}" in cells), {})
        counts[target] = (first.get("n_binder"), first.get("n_negative"))

    ax.set_xticks(range(len(TARGET_COLS)))
    ax.set_xticklabels(
        [f"{TARGET_LABELS[t]}\n{counts[t][0]}+ / {counts[t][1]}−" for t in TARGET_COLS],
        fontsize=FONT,
    )
    ax.set_yticks(range(len(ORACLE_ROWS)))
    ax.set_yticklabels([ORACLE_LABELS[o] for o in ORACLE_ROWS], fontsize=FONT)
    ax.tick_params(length=0)
    # axes limits flush with the outermost gridlines (no white gap at the frame)
    ax.set_xlim(-0.5, len(TARGET_COLS) - 0.5)
    ax.set_ylim(len(ORACLE_ROWS) - 0.5, -0.5)

    for x in range(len(TARGET_COLS) + 1):
        ax.axvline(x - 0.5, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)
    for y in range(len(ORACLE_ROWS) + 1):
        ax.axhline(y - 0.5, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)

    cbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=C_MAP), ax=ax,
        fraction=0.035, pad=0.02, ticks=[0.1, 0.3, 0.5, 0.7, 0.9],
    )
    cbar.ax.yaxis.set_ticks_position("right")
    cbar.ax.yaxis.set_label_position("right")
    cbar.set_label("AUROC (binder vs negative)", fontsize=FONT)
    cbar.ax.tick_params(labelsize=FONT, length=2, pad=1.5)
    cbar.outline.set_linewidth(0.4)
    cbar.ax.axhline(CHANCE, color=TEXT, linewidth=0.7, linestyle="-")

    # Nature style: no in-figure title — the headline lives in the caption.
    print(f"cells passing AUROC > {GATE:g}: {n_pass}/{n_cells}")
    fig.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3b_oracle_screening.{ext}"
        fig.savefig(out, dpi=600 if ext == "png" else None, bbox_inches="tight")
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
