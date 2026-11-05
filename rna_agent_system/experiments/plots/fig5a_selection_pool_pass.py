"""Fig 5a — the selection-step precursor fails for reasons inherent in
generation: fixed-pool feasibility against delivered-batch diversity.

One labeled scatter from the exp26 re-measurement (Experiment 26, paper
registry E5; the selection-step constraint-navigation precursor), latest
production wiring only (per-target species-matched codon tables):

  x — passing candidates in the fixed pool (of 315 full-length constructs
      per target) under the registered hard-constraint matrix;
  y — batch diversity (minimum pairwise distance over each profile's
      delivered five, worst profile, %), the diversity threshold drawn as a
      dashed line.

Both registered failure modes read off the single view: insulin saturates
below the diversity threshold (1.01%, the λ-saturation failure) and
GFP/A1AT collapse on feasibility (18 and 27 of 315). The pre-fix
default-table GFP wiring (0/315, the registered B0 defect reproduction)
stays cited in the text/legend; the panel reports the latest production
state only.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch): the
axis labels and the line tag aligned to the polished §2.5/legend wording
— "Fixed-pool pass (n of 315)" → "Passing candidates (of 315)", "Batch
diversity (min distance, %)" → "Batch diversity (%)", and the "2% gate"
tag → "diversity floor" (the body's registered term); no number, colour
or geometry changed.

2026-10-06 follow-up (user-directed): the canvas grew 52 → 56 mm to match
panel b's height, with the axes' bottom edge moved 11 → 8.7 mm to sit on
panel b's axes baseline (8.68 mm) — row 1's two axes boxes now align;
text unchanged at 6 pt, zero number changes.

2026-10-10 row-alignment polish (user-directed Fig. 5 batch): axes height
38.5 → 38.06 mm so the axes TOP also lands on panel b's top edge
(9.24 mm from the canvas top) — row 1's two axes rectangles now share
both edges exactly; no number, colour or text change.

2026-10-07 terminology unification (user-adjudicated): the line tag
"diversity floor" → "diversity threshold" — the paper-wide term
(body §2.5, Methods, the Fig. 1d legend and panel); no number, colour or
geometry changed.

Style (Nature conventions, the fig3/fig4 house style): no in-figure title
or summary statistics — the panel letter is added at assembly and the
headline numbers live in the Fig. 5a caption; every text element one 6-pt
pure-black style; colours only from palette rev 7; 1200-dpi PNG + vector
PDF (fonttype 42); absolute-mm geometry, single-column width.

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

C_POINT = PALETTE_BY_NAME["grey_blue"]       # production-wiring targets
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

# Per-target label placement in data coordinates: (dx, dy, ha, va) relative
# to the point — chosen so no label touches a point, the gate line, or
# another label.
LABEL_PLACEMENT = {
    "A1AT": (0, -0.16, "center", "top"),
    "Insulin": (0, -0.16, "center", "top"),
    "EPO": (0, 0.16, "center", "bottom"),
    "IL-2": (0, -0.16, "center", "top"),
    "GFP": (0, 0.16, "center", "bottom"),
}


def main() -> int:
    summary = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = {(r["target"], r["wiring"]): r for r in summary["targets"]}
    targets = ["A1AT", "Insulin", "EPO", "IL-2", "GFP"]
    pts = [(rows[(t, "production")]["pass_n"],
            100.0 * rows[(t, "production")]["d1_min_dist_min_over_profiles"],
            t) for t in targets]

    fig_w, fig_h = 89 / 25.4, 56 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([16 / 25.4 / fig_w, 8.7 / 25.4 / fig_h,
                       67 / 25.4 / fig_w, 38.06 / 25.4 / fig_h])

    ax.axhline(GATE, color=C_GATE, linestyle=(0, (3, 2)), linewidth=0.6,
               zorder=1)
    for x, y, name in pts:
        ax.scatter([x], [y], s=14, color=C_POINT, edgecolors="none",
                   zorder=3)
        dx, dy, ha, va = LABEL_PLACEMENT[name]
        ax.text(x + dx, y + dy, name, ha=ha, va=va, fontsize=FONT,
                color=INK, zorder=4)
    # Threshold tag in the empty band directly above the line, mid-panel
    # (clear of the left target cluster, the insulin point below, and IL-2
    # right).
    ax.text(170, GATE + 0.12, "diversity threshold", ha="center", va="bottom",
            fontsize=FONT, color=INK, zorder=4)

    ax.set_xlim(-20, 350)
    ax.set_ylim(0, 5)
    ax.set_xticks([0, 100, 200, 300])
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("Passing candidates (of 315)", fontsize=FONT, labelpad=2)
    ax.set_ylabel("Batch diversity (%)", fontsize=FONT, labelpad=2)
    ax.tick_params(length=1.5, pad=1.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5a_selection_pool_pass.{ext}", dpi=1200,
                    facecolor="white")
    print(f"written: {OUT_DIR / 'fig5a_selection_pool_pass'}.pdf/.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
