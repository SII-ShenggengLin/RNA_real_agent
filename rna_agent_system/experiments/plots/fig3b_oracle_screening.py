#!/usr/bin/env python3
"""Fig. 3b — structure-oracle screening-power balloon matrix (reset run).

3 oracles (rows) × 6 aptamer targets (columns): per-cell binder-vs-negative
AUROC of the reset Exp-10 run, dual-encoded as bubble size and bubble colour;
the AUROC value is printed in every cell.  Reference marks: chance (0.5,
solid) and the pre-registered screening gate (0.8, dashed) on the colour bar;
a dark ring marks any passing cell (expected none — 0/18 in the retained
evidence).  Per-target anchor counts sit under the column labels.

Chart type: balloon-matrix heatmap (CASCADE Fig. 3b / ERA Fig. 2b lineage),
registered in FIGURE_PLAN_V5.md row 3b.

Colours (palette rev 7): the continuous AUROC scale is a LinearSegmentedColormap
anchored on slate blue → sand → terracotta (all anchors from the mandated
twelve-colour set); the pass ring uses the held-out dark warm grey (the
palette's neutral-dark semantic); gridlines use the non-data grey.

Data  : experiments/results/exp10_structure_oracle_screening/summary.json
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
import matplotlib.patheffects as patheffects  # noqa: E402
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
C_PASS_RING = PALETTE_BY_NAME["dark_warm_grey"]

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


def _luminance(rgb: tuple[float, float, float]) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def main() -> int:
    summary = json.loads(SUMMARY.read_text())
    cells = summary["cells"]
    TARGET_COLS = _derive_targets(cells)

    fig, ax = plt.subplots(figsize=(min(7.4, 5.12 * len(TARGET_COLS) / 6), 2.05))
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
            ring = auroc > GATE
            n_pass += int(ring)
            ax.scatter(c, r, s=size, c=[color], edgecolors="white",
                       linewidths=0.5, zorder=3)
            if ring:
                ax.scatter(c, r, s=size + 46, facecolors="none",
                           edgecolors=C_PASS_RING, linewidths=1.1, zorder=3)
            txt_color = "white" if _luminance(color[:3]) < 0.55 else TEXT
            ax.text(c, r, f"{auroc:.2f}", ha="center", va="center",
                    fontsize=5.2, color=txt_color, zorder=4,
                    path_effects=[patheffects.withStroke(linewidth=1.6,
                                                          foreground="white")])

    # per-target anchor counts under the column labels
    counts = {}
    for target in TARGET_COLS:
        first = next((cells[f"{o} | {target}"] for o in ORACLE_ROWS
                      if f"{o} | {target}" in cells), {})
        counts[target] = (first.get("n_binder"), first.get("n_negative"))

    ax.set_xticks(range(len(TARGET_COLS)))
    ax.set_xticklabels(
        [f"{TARGET_LABELS[t]}\n{counts[t][0]}+ / {counts[t][1]}−" for t in TARGET_COLS],
        fontsize=5.5,
    )
    ax.set_yticks(range(len(ORACLE_ROWS)))
    ax.set_yticklabels([ORACLE_LABELS[o] for o in ORACLE_ROWS], fontsize=5.8)
    ax.tick_params(length=0)
    ax.set_xlim(-0.6, len(TARGET_COLS) - 0.3)
    ax.set_ylim(len(ORACLE_ROWS) - 0.4, -0.6)

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
    cbar.set_label("AUROC (binder vs negative)\nsolid line: chance 0.5 · dashed: gate 0.8",
                   fontsize=5.0)
    cbar.ax.tick_params(labelsize=5, length=2, pad=1.5)
    cbar.outline.set_linewidth(0.4)
    cbar.ax.axhline(CHANCE, color=TEXT, linewidth=0.7, linestyle="-")
    cbar.ax.axhline(GATE, color=C_PASS_RING, linewidth=0.9, linestyle="--")

    ax.set_title(
        f"Structure-oracle screening power — {n_pass}/{n_cells} cells pass AUROC > {GATE:g}",
        fontsize=6.5, pad=6,
    )
    fig.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3b_oracle_screening.{ext}"
        fig.savefig(out, dpi=600 if ext == "png" else None, bbox_inches="tight")
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
