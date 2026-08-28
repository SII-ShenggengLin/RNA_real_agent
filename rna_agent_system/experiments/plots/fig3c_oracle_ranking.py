#!/usr/bin/env python3
"""Fig. 3c — structure-oracle ranking power (Cleveland dot plot, reset run).

18 cells (3 oracles × 6 aptamer targets): per-cell Spearman ρ of oracle score
against −log10 of measured Kd on the within-target affinity series, plotted as
dots on a correlation axis.  Reference marks: no-correlation zero (solid) and
the pre-registered ranking gate ρ ≥ 0.6 (dashed).  The retained-evidence ρ of
each cell rides as a small open marker connected by a hairline — the
reset-vs-retained dumbbell shows ProteinX-complex realization variance while
the gate is reached in neither realization (expected 0/18 both).

Chart type: Cleveland dot plot (+ gate line), registered in
FIGURE_PLAN_V5.md row 3c.

Colours (palette rev 7): the three oracle identity colours — terracotta
(EGARPS), slate blue (ProteinX), sage green (RhoFold); retained markers and
connectors in the non-data grey; the gate line in the held-out dark warm grey
(neutral-dark semantic, matching fig3b's pass-ring convention).

Data  : experiments/results/exp11_oracle_ranking_power/summary.json
Usage : python experiments/plots/fig3c_oracle_ranking.py
Output: experiments/plots/output/fig3c_oracle_ranking.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

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
    "egarps_native_probability": "EGARPS+\nnative probability",
    "proteinx_ipTM": "ProteinX\nipTM",
    "rhofold_mean_plddt": "RhoFold\nmean pLDDT",
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
C_RETAINED = "#9A9A9A"                        # retained-marker neutral (non-data)

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


def main() -> int:
    if not SUMMARY.exists():
        print("no summary.json — run experiments/exp11_oracle_ranking_power.py --summary first")
        return 1
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    cells = s["cells"]
    TARGET_COLS = _derive_targets(cells)
    retained = s.get("comparison_vs_retained", {})

    # 18 rows: oracle blocks (top→bottom) × target, first row on top.
    rows = []
    for oracle in ORACLE_ROWS:
        for target in TARGET_COLS:
            cell = cells.get(f"{oracle} | {target}", {})
            if "ranking_spearman_rho" not in cell:
                continue
            key = f"{oracle} | {target}"
            rows.append({
                "oracle": oracle,
                "target": target,
                "rho": cell["ranking_spearman_rho"],
                "n": cell["n_affinity_series"],
                "retained_rho": retained.get(key, {}).get("retained_rho"),
            })

    n_cells = len(rows)
    n_pass = sum(1 for r in rows if r["rho"] >= GATE)
    pass_ns = sorted(r["n"] for r in rows if r["rho"] >= GATE)
    best = max(rows, key=lambda r: r["rho"])

    n_expected = len(ORACLE_ROWS) * len(TARGET_COLS)
    fig_w, fig_h = 88 / 25.4, 76 / 25.4 * max(1.0, n_expected / 18.0)  # scales with cell count
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.30, 0.155, 0.635, 0.775])

    # y positions with an inter-block gap that hosts the oracle group headers
    gap = 1.35
    ys_list: list[float] = []
    y_cursor = 0.0
    for r in range(len(rows)):
        if r and r % len(TARGET_COLS) == 0:
            y_cursor += gap
        ys_list.append(-y_cursor)
        y_cursor += 1.0
    y_top, y_bot = 0.0, ys_list[-1]
    ys = ys_list

    # reference lines
    ax.axvline(0.0, color=TEXT, linewidth=0.6, zorder=2)
    ax.axvline(GATE, color=C_GATE, linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)

    for y, row in zip(ys, rows):
        color = ORACLE_COLORS[row["oracle"]]
        # reset-vs-retained dumbbell: hairline connector + open retained marker
        if row["retained_rho"] is not None:
            ax.plot([row["retained_rho"], row["rho"]], [y, y], color=NEUTRAL_GRID,
                    linewidth=0.7, zorder=3)
            ax.scatter(row["retained_rho"], y, s=7, facecolors="none",
                       edgecolors=C_RETAINED, linewidths=0.7, zorder=4)
        ax.scatter(row["rho"], y, s=17, c=color, edgecolors="white",
                   linewidths=0.4, zorder=5)
        if row["rho"] >= GATE:  # nominal pass ring (fig3b convention)
            ax.scatter(row["rho"], y, s=17 + 30, facecolors="none",
                       edgecolors=C_GATE, linewidths=0.9, zorder=6)
        # printed value right of the dot (left if near the right margin)
        x_text = row["rho"] + 0.045
        ha = "left"
        if x_text > 0.93:
            x_text, ha = row["rho"] - 0.045, "right"
        ax.text(x_text, y, f"{row['rho']:+.2f}", fontsize=4.8, va="center",
                ha=ha, color=color)

    # y labels: target (+n); oracle block headers inline at the empty left edge
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{TARGET_LABELS[r['target']]}  (n={r['n']})" for r in rows],
                       fontsize=5.0)
    for tick, row in zip(ax.get_yticklabels(), rows):
        tick.set_color(ORACLE_COLORS[row["oracle"]])
    for b, oracle in enumerate(ORACLE_ROWS):
        block = [r for r in rows if r["oracle"] == oracle]
        if not block:
            continue
        blk_ys = [ys[rows.index(r)] for r in block]
        if b:
            ax.axhline(max(blk_ys) + (1.0 + gap) / 2, color=NEUTRAL_GRID,
                       linewidth=0.4, zorder=1)
        # every dot sits right of −0.5 — the left edge strip is reserved for headers
        ax.text(-1.01, (max(blk_ys) + min(blk_ys)) / 2, ORACLE_LABELS[oracle],
                fontsize=5.4, fontweight="bold", ha="left", va="center",
                color=ORACLE_COLORS[oracle], linespacing=1.15, zorder=5)

    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(y_bot - 1.25, y_top + 0.75)
    ax.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    ax.set_xticklabels(["−1", "−0.5", "0", "0.5", "1"], fontsize=5.5)
    ax.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)
    ax.set_xlabel("Spearman ρ vs measured Kd (−log$_{10}$)", fontsize=6, labelpad=2)
    for s_name in ("top", "right", "left"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="x", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # reference-line tags (inside the top headroom, clear of the title)
    ax.text(0.0, y_top + 0.22, "no correlation", fontsize=4.6, ha="center",
            va="bottom", color=TEXT)
    ax.text(GATE, y_top + 0.22, "0.6 ranking gate", fontsize=4.6, ha="center",
            va="bottom", color=C_GATE)

    # reset/retained marker legend (below the last row, inside the left strip)
    y_leg = y_bot - 0.85
    ax.scatter([-1.01], [y_leg], s=17, c=PALETTE_BY_NAME["terracotta"],
               edgecolors="white", linewidths=0.4, zorder=5, clip_on=False)
    ax.text(-0.965, y_leg, "reset run", fontsize=4.8, va="center", color=TEXT)
    ax.scatter([-0.70], [y_leg], s=7, facecolors="none", edgecolors=C_RETAINED,
               linewidths=0.7, zorder=5, clip_on=False)
    ax.text(-0.655, y_leg, "retained evidence", fontsize=4.8, va="center", color=TEXT)

    ax.set_title(
        f"Structure-oracle ranking power — {n_pass}/{n_cells} cells ≥ {GATE:g}"
        + (f" (n = {', '.join(str(n) for n in pass_ns)} only, CIs vacuous)" if n_pass else ""),
        loc="left", fontsize=6.5, pad=6,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3c_oracle_ranking.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for r in rows:
        print(f"{r['oracle']:>28s} | {r['target']:<15s} n={r['n']} "
              f"rho={r['rho']:+.4f} retained={r['retained_rho']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
