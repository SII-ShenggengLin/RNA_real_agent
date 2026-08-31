#!/usr/bin/env python3
"""Fig. 3b — structure-oracle ranking power (Cleveland dot plot, reset run).

27 cells (3 oracles × 9 aptamer targets): per-cell Spearman ρ of oracle score
against −log10 of measured Kd on the within-target affinity series, plotted as
dots on a correlation axis.  Cells reaching the pre-registered ranking gate
ρ ≥ 0.6 carry a nominal-pass ring — the only keyed element.  Printed ρ values
sit in a fixed right-hand column (forest-plot convention) so no value label
can cross a pass ring.  Every element is the v3 reset re-run: 2026-08-29
user-directed revisions dropped the retained-evidence open markers and
dumbbell hairlines, then the zero/gate reference lines and their tags
(uninformative ink) — the panel shows the latest run only.

Chart type: Cleveland dot plot (+ gate line), registered in
FIGURE_PLAN_V5.md row 3c.

Style (reset programme, Nature convention): no in-figure title — the headline
lives in the caption and the assembler adds the panel letter; every text
element is one 6-pt ink-black style (fig2d/fig2f/fig2i convention); oracle
group headers are centred over the data area; the ring legend is a centred
row block directly under the x-axis label (fig2i convention).

Colours (palette rev 7): the three oracle identity colours — terracotta
(EGARPS), slate blue (ProteinX), sage green (RhoFold) — data dots only; the
nominal-pass rings in the held-out dark warm grey (#7A7672, neutral-dark
semantic, matching fig3a's pass-ring convention).  All text is ink black
regardless of element.

Data  : experiments/results/exp11_oracle_ranking_power/summary.json
Usage : python experiments/plots/fig3b_oracle_ranking.py
Output: experiments/plots/output/fig3b_oracle_ranking.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY = (
    PROJECT_ROOT / "experiments" / "results" / "exp11_oracle_ranking_power" / "summary.json"
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
    "egarps_native_probability": "EGARPS+ native probability",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold mean pLDDT",
}
ORACLE_COLORS = {
    "egarps_native_probability": PALETTE_BY_NAME["terracotta"],   # #C08B7C
    "proteinx_ipTM": PALETTE_BY_NAME["slate_blue"],               # #6B7B8D
    "rhofold_mean_plddt": PALETTE_BY_NAME["sage_green"],          # #A3B18A
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


GATE = 0.6
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]   # #7A7672 (held-out neutral-dark)
X_COL = 1.14                                 # fixed ρ-value column (data x)
FS = 6                                       # the programme's single text size

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FS,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "legend.fontsize": FS,
    "pdf.fonttype": 42,
})


def main() -> int:
    if not SUMMARY.exists():
        print("no summary.json — run experiments/exp11_oracle_ranking_power.py --summary first")
        return 1
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    cells = s["cells"]
    TARGET_COLS = _derive_targets(cells)

    # rows: oracle blocks (top→bottom) × target, first row on top.
    rows = []
    for oracle in ORACLE_ROWS:
        for target in TARGET_COLS:
            cell = cells.get(f"{oracle} | {target}", {})
            if "ranking_spearman_rho" not in cell:
                continue
            rows.append({
                "oracle": oracle,
                "target": target,
                "rho": cell["ranking_spearman_rho"],
                "n": cell["n_affinity_series"],
            })

    n_expected = len(ORACLE_ROWS) * len(TARGET_COLS)
    fig_w, fig_h = 88 / 25.4, 76 / 25.4 * max(1.0, n_expected / 18.0)  # scales with cell count
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.30, 0.115, 0.595, 0.80])

    # y positions.  Vertical budget in row units (1 unit ≈ 64 px at output):
    # 6-pt text needs ≈0.78, a data dot ±0.30, a pass ring ±0.52.  The
    # inter-block gap of 2.0 hosts the bold oracle header on its own band
    # (no separator hairlines — the gap + header carry the grouping).
    gap = 2.0
    ys_list: list[float] = []
    y_cursor = 0.0
    for r in range(len(rows)):
        if r and r % len(TARGET_COLS) == 0:
            y_cursor += gap
        ys_list.append(-y_cursor)
        y_cursor += 1.0
    y_top, y_bot = 0.0, ys_list[-1]
    ys = ys_list

    y_lo, y_hi = y_bot - 0.75, y_top + 1.75
    ax.set_xlim(-1.05, 1.08)
    ax.set_ylim(y_lo, y_hi)

    for y, row in zip(ys, rows):
        color = ORACLE_COLORS[row["oracle"]]
        ax.scatter(row["rho"], y, s=17, c=color, edgecolors="white",
                   linewidths=0.4, zorder=5)
        if row["rho"] >= GATE:  # nominal pass ring (fig3a convention)
            ax.scatter(row["rho"], y, s=50, facecolors="none",
                       edgecolors=C_GATE, linewidths=0.9, zorder=6)
        # printed ρ in the fixed right-hand column — never crosses a graphic
        ax.text(X_COL, y, f"{row['rho']:+.2f}".replace("-", "−"), fontsize=FS,
                va="center", ha="left", color=TEXT, clip_on=False)

    # y labels: target (+n), ink black like every other text element
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{TARGET_LABELS[r['target']]} (n = {r['n']})" for r in rows],
                       fontsize=FS)
    for b, oracle in enumerate(ORACLE_ROWS):
        blk_ys = [ys[i] for i, r in enumerate(rows) if r["oracle"] == oracle]
        if not blk_ys:
            continue
        # bold group header centred over the data area on its own band inside
        # the inter-block gap — clear of the block's first-row dots below and
        # the previous block's last-row dots above
        ax.text(0.015, max(blk_ys) + 1.05, ORACLE_LABELS[oracle], fontsize=FS,
                fontweight="bold", ha="center", va="center", color=TEXT, zorder=5)

    ax.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    ax.set_xticklabels(["−1", "−0.5", "0", "0.5", "1"], fontsize=FS)
    ax.tick_params(axis="both", labelsize=FS, length=1.5, pad=1)
    ax.set_xlabel("Spearman ρ (oracle score vs −log$_{10}$ K$_{d}$)",
                  fontsize=FS, labelpad=2)
    for s_name in ("top", "right", "left"):
        ax.spines[s_name].set_visible(False)
    ax.set_axisbelow(True)

    # the ρ-column header sits level with the first block header
    ax.text(X_COL, y_top + 1.05, "ρ", fontsize=FS, ha="left", va="center",
            color=TEXT, clip_on=False)

    # ring legend: centred row block directly under the x-axis label (fig2i
    # convention) — the dots are the reset run's per-cell ρ values,
    # self-evident from the axes, so the ring overlay is the only keyed element
    handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=7.0,
               markerfacecolor="none", markeredgecolor=C_GATE,
               markeredgewidth=0.9, label="nominal pass (ρ ≥ 0.6)"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.082),
              ncol=1, frameon=False, fontsize=FS, handletextpad=0.5,
              borderaxespad=0.0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3b_oracle_ranking.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for r in rows:
        print(f"{r['oracle']:>28s} | {r['target']:<15s} n={r['n']} "
              f"rho={r['rho']:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
