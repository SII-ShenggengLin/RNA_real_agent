"""Fig 5a — the selection-layer precursor fails for generation-structural
reasons: fixed-pool pass rates and batch-diversity saturation.

Two stacked bar groups from the exp26 re-measurement (Experiment 26, paper
registry E5; the selection-layer constraint-navigation precursor):

  top    — fixed-pool pass count under the registered hard-constraint matrix
           (n of 315 constructs per target): the four species-matched targets
           (grey blue), then the GFP pair that exhibits the codon-table defect —
           default (human) table terracotta vs species-matched E. coli table
           sage green, the registered zero → nonzero repair (rotated tick
           labels, the fig3d convention);
  bottom — delivered-batch diversity per target (minimum pairwise distance
           over each profile's delivered five, worst profile, %), bars coloured
           sage (≥ 2% gate) / terracotta (below gate — the λ-saturation
           failure), the 2% requirement as a dashed gate line with tag.

Style (Nature conventions, the fig3/fig4-panel house style): no in-figure
titles or summary statistics — the panel letter is added at assembly and the
headline numbers live in the Fig. 5a caption; every text element one 6-pt
pure-black style; colours only from palette rev 7; 1200-dpi PNG + vector PDF
(fonttype 42); absolute-mm geometry, single-column width.

Data  : experiments/results/exp26_selection_layer_pool/full/summary.json
Usage : python experiments/plots/fig5a_selection_pool_pass.py
Output : experiments/plots/output/fig5a_selection_pool_pass.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = (PROJECT_ROOT / "experiments" / "results"
           / "exp26_selection_layer_pool" / "full" / "summary.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
GATE = 2.0  # diversity requirement, %

C_HUMAN = PALETTE_BY_NAME["grey_blue"]       # species-matched targets
C_DEFECT = PALETTE_BY_NAME["terracotta"]     # GFP default-table / below-gate
C_REPAIR = PALETTE_BY_NAME["sage_green"]     # GFP E. coli-table / pass-gate
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]   # gate line (neutral-dark)

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


def main() -> int:
    summary = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = {(r["target"], r["wiring"]): r for r in summary["targets"]}

    # ── data assembly ────────────────────────────────────────────────────
    pass_bars = [
        ("A1AT", "production", "A1AT"),
        ("Insulin", "production", "Insulin"),
        ("EPO", "production", "EPO"),
        ("IL-2", "production", "IL-2"),
        ("GFP", "pre_b0", "GFP (default)"),
        ("GFP", "production", "GFP (matched)"),
    ]
    div_bars = [
        ("A1AT", "production"), ("Insulin", "production"),
        ("EPO", "production"), ("IL-2", "production"),
        ("GFP", "production"),
    ]

    fig_w, fig_h = 89 / 25.4, 82 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    # ── top: fixed-pool pass count (n of 315) ────────────────────────────
    ax_t = fig.add_axes([30 / 25.4 / fig_w, 57 / 25.4 / fig_h,
                         53 / 25.4 / fig_w, 17 / 25.4 / fig_h])
    values = [rows[(t, w)]["pass_n"] for t, w, _ in pass_bars]
    colors = [C_HUMAN, C_HUMAN, C_HUMAN, C_HUMAN, C_DEFECT, C_REPAIR]
    labels = [lbl for _, _, lbl in pass_bars]
    y_top = int(max(60, ((max(values) * 1.18 + 49) // 50) * 50))
    for x, (v, c) in enumerate(zip(values, colors)):
        ax_t.bar(x, v, width=0.62, color=c, edgecolor="none")
        ax_t.text(x, (v if v else 4) + 0.015 * y_top, str(v),
                  ha="center", va="bottom", fontsize=FONT, color=INK)
    ax_t.set_xticks(range(len(pass_bars)))
    ax_t.set_xticklabels(labels, fontsize=FONT, rotation=45,
                         ha="right", rotation_mode="anchor")
    ax_t.set_xlim(-0.55, len(pass_bars) - 0.45)
    ax_t.set_ylim(0, y_top)
    ax_t.set_yticks([0, y_top // 2, y_top])
    ax_t.set_ylabel("Fixed-pool pass (n of 315)", fontsize=FONT, labelpad=2)
    ax_t.tick_params(length=1.5, pad=1.5)
    ax_t.spines["top"].set_visible(False)
    ax_t.spines["right"].set_visible(False)

    # ── bottom: delivered-batch diversity with the 2% gate line ─────────
    ax_b = fig.add_axes([30 / 25.4 / fig_w, 13 / 25.4 / fig_h,
                         53 / 25.4 / fig_w, 17 / 25.4 / fig_h])
    div_values = [100.0 * rows[(t, w)]["d1_min_dist_min_over_profiles"]
                  for t, w in div_bars]
    div_labels = [t for t, _ in div_bars]
    div_colors = [C_REPAIR if v >= GATE else C_DEFECT for v in div_values]
    y_top_d = max(2.6, ((max(div_values) * 1.35 + 0.9) // 1.0) * 1.0)
    for x, (v, c) in enumerate(zip(div_values, div_colors)):
        ax_b.bar(x, v, width=0.62, color=c, edgecolor="none")
        ax_b.text(x, v + 0.03 * y_top_d, f"{v:.2f}", ha="center",
                  va="bottom", fontsize=FONT, color=INK)
    ax_b.axhline(GATE, color=C_GATE, linestyle=(0, (3, 2)), linewidth=0.6)
    # Gate tag in the clear band directly above the line over a below-gate
    # bar (no bar ink crosses the line there); if every bar clears the gate,
    # extend the axis and park the tag past the last bar instead.
    below = [i for i, v in enumerate(div_values) if v < GATE]
    if below:
        ax_b.text(below[0], GATE + 0.04 * y_top_d, "2% gate",
                  ha="center", va="bottom", fontsize=FONT, color=INK)
    else:
        ax_b.set_xlim(-0.55, len(div_bars) + 0.55)
        ax_b.text(len(div_bars) - 0.45 + 0.06, GATE + 0.04 * y_top_d,
                  "2% gate", ha="left", va="bottom", fontsize=FONT, color=INK)
    ax_b.set_xticks(range(len(div_bars)))
    ax_b.set_xticklabels(div_labels, fontsize=FONT)
    ax_b.set_xlim(-0.55, len(div_bars) - 0.45)
    ax_b.set_ylim(0, y_top_d)
    ax_b.set_yticks([0, 2, 4] if y_top_d >= 4 else [0, 1, 2])
    ax_b.set_ylabel("Batch diversity (min distance, %)",
                    fontsize=FONT, labelpad=2)
    ax_b.tick_params(length=1.5, pad=1.5)
    ax_b.spines["top"].set_visible(False)
    ax_b.spines["right"].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5a_selection_pool_pass.{ext}", dpi=1200,
                    facecolor="white")
    print(f"written: {OUT_DIR / 'fig5a_selection_pool_pass'}.pdf/.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
