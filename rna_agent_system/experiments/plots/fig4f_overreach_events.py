"""Fig 4f — plan-level overreach events of the E3 dual-arm re-run.

Paired bars per oracle x intended use (plan requests of a structural oracle
as ranking objective / screening evaluation): ungated control arm (Exp 5,
59 events, terracotta) vs gated treatment arm (Exp 17, 0 events, sage) —
arm colours as Fig. 4d; a bracket annotation carries the registered delta
(59 to 0). Use is carried by the x-axis cells (ranking / screening), oracle
labels centred on their cell pairs (the fig3e group-label convention). The
gated arm's 71 blocked plan requests (the mechanism behind the zero) are
stated in the caption, not drawn.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles
or summary statistics beyond the registered delta annotation; every text
element one 6-pt pure-black style; colours only from palette rev 7; 1200-dpi
PNG + vector PDF (fonttype 42); absolute-mm geometry, single-column width.

2026-09-01 user-directed revision (same frozen results, no re-run): the arm
key was moved from the floating figure-top position to a single centred row
directly under the panel (the fig3e convention — legend attached to the
panel); the y-axis label was shortened from the 31-character
"Decision-layer overreach events" (which overflowed the 23-mm axis at 6 pt)
to "Overreach events" — the decision-layer qualifier is stated verbatim in
the Fig. 4f caption; and the figure geometry was rebalanced to the new
stack (44 → 40.5 mm tall).

Data  : experiments/results/exp5_claim_overreach/runs_summary.json (ungated)
        experiments/results/exp17_claim_gating/summary.json (gated)
Usage : python experiments/plots/fig4f_overreach_events.py
        FIG4F_LAYOUT=tall python experiments/plots/fig4f_overreach_events.py
            (composite stack variant — same data, taller axes)
Output : experiments/plots/output/fig4f_overreach_events.{pdf,png}
         (+ fig4f_overreach_events_tall.{pdf,png} for the tall variant)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP5_SUMMARY = (PROJECT_ROOT / "experiments" / "results" / "exp5_claim_overreach"
                / "runs_summary.json")
EXP17_SUMMARY = (PROJECT_ROOT / "experiments" / "results" / "exp17_claim_gating"
                 / "summary.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

ARM_COLORS = {"ungated": PALETTE_BY_NAME["terracotta"],
              "gated": PALETTE_BY_NAME["sage_green"]}
ORACLE_ORDER = ["rhofold_mean_plddt", "proteinx_ipTM", "egarps_native_probability"]
ORACLE_LABELS = {"rhofold_mean_plddt": "RhoFold", "proteinx_ipTM": "ProteinX",
                 "egarps_native_probability": "EGARPS"}
USES = ["ranking_objective", "screening_evaluation"]
USE_LABELS = {"ranking_objective": "Ranking", "screening_evaluation": "Screening"}

# Composite-layout variant (the fig3c convention): FIG4F_LAYOUT=tall renders
# the same frozen data on a taller canvas (axes stretched vertically, same
# 6-pt text, no data change) so the panel fills the Fig. 4 composite's row-2
# stack (d over f) flush with panel e's height; 2026-10-07 (user-directed
# equal-width four-row layout, panels re-ordered e|f / g|h): the tall
# variant's axes also widen 72.0 → 83.1 mm so the e|f row spans the same
# content width as the other rows. 2026-10-10 composite-grid batch
# (user-directed row/column alignment): the tall variant re-renders on an
# exact 96.5 x 66.2 mm cell of the Fig. 4 two-column grid (column 2; row
# 3 shares its height with fig4e), saved without the tight crop so the
# assembler places it at scale 1.0 (axes 82.0 x 49.2 mm). The standalone
# render is the default and is untouched. Output goes to a separate _tall
# file pair.
LAYOUT = os.environ.get("FIG4F_LAYOUT", "standalone")
FIG_H_MM = 66.2 if LAYOUT == "tall" else 40.5
AX_H_MM = 49.2 if LAYOUT == "tall" else 23.5
FIG_W_MM = 96.5 if LAYOUT == "tall" else 89.0
AX_W_MM = 82.0 if LAYOUT == "tall" else 72.0
OUT_STEM = "fig4f_overreach_events_tall" if LAYOUT == "tall" else "fig4f_overreach_events"

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
    exp5 = json.loads(EXP5_SUMMARY.read_text(encoding="utf-8"))
    exp17 = json.loads(EXP17_SUMMARY.read_text(encoding="utf-8"))

    # cell layout: x positions 0,1 | 2.5,3.5 | 5,6 (oracle groups gapped)
    xs = [0.0, 1.0, 2.5, 3.5, 5.0, 6.0]
    cells = [(o, u) for o in ORACLE_ORDER for u in USES]
    ungated = [exp5["overreach_by_oracle_use"][f"{o}:{u}"] for o, u in cells]
    gated_total = exp17["arms"]["gated"]["overreach_events"]
    assert gated_total == 0 and sum(ungated) == exp5["overreach_total"]

    fig_w, fig_h = FIG_W_MM / 25.4, FIG_H_MM / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([11 / 25.4 / fig_w, 12.5 / 25.4 / fig_h,
                       AX_W_MM / 25.4 / fig_w, AX_H_MM / 25.4 / fig_h])

    w = 0.34
    y_top = max(ungated) * 1.48
    for x, n in zip(xs, ungated):
        ax.bar(x - w / 2 - 0.01, n, width=w, color=ARM_COLORS["ungated"],
               edgecolor="none")
        ax.text(x - w / 2 - 0.01, n + 0.28, str(n), ha="center", va="bottom",
                fontsize=FONT, color=INK)
        ax.bar(x + w / 2 + 0.01, 0, width=w, color=ARM_COLORS["gated"],
               edgecolor="none")
        ax.text(x + w / 2 + 0.01, 0.28, "0", ha="center", va="bottom",
                fontsize=FONT, color=INK)

    ax.set_xticks(xs)
    ax.set_xticklabels([USE_LABELS[u] for _, u in cells], fontsize=FONT)
    ax.tick_params(axis="x", length=0, pad=1.5)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=1)
    # oracle labels centred on their cell pairs (fig3e group-label convention);
    # the offset is an absolute mm distance below the axis, so it does not
    # scale with the axis height (the tall composite variant keeps the
    # standalone 4.11 mm clearance above the legend row)
    for gx, o in zip((0.5, 3.0, 5.5), ORACLE_ORDER):
        ax.text(gx, -4.11 / AX_H_MM, ORACLE_LABELS[o], ha="center", va="top",
                fontsize=FONT, color=INK, transform=ax.get_xaxis_transform())
    ax.set_xlim(-0.75, 6.75)
    ax.set_ylim(0, y_top)
    ax.set_yticks(range(0, 12, 3))
    ax.set_ylabel("Overreach events", fontsize=FONT, labelpad=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # registered delta annotation: bracket spanning the axis, 59 to 0
    bx0, bx1 = -0.6, 6.6
    by = max(ungated) * 1.30
    ax.plot([bx0, bx1], [by, by], color=INK, linewidth=0.4)
    for bx in (bx0, bx1):
        ax.plot([bx, bx], [by - 0.35, by], color=INK, linewidth=0.4)
    ax.text((bx0 + bx1) / 2, by + 0.35, f"{sum(ungated)} to 0",
            ha="center", va="bottom", fontsize=FONT, color=INK)

    # arm key: one centred row directly under the panel, centred on the axes
    # (the fig3e convention — the legend attaches to the panel rather than
    # floating above it)
    def _fx(v: float) -> float: return v / 25.4 / fig_w
    def _fy(v: float) -> float: return v / 25.4 / fig_h
    sw_w, sw_h, gap_k, gap_e = 2.4, 1.6, 1.6, 4.0
    entries = (("ungated", "Ungated"), ("gated", "Gated"))
    label_w = {"ungated": 7.4, "gated": 5.5}
    row_w = (sum(sw_w + gap_k + label_w[a] for a, _ in entries)
             + gap_e * (len(entries) - 1))
    x = (11 + AX_W_MM / 2) - row_w / 2
    for arm, lab in entries:
        fig.patches.append(plt.Rectangle(
            (_fx(x), _fy(3.0 - sw_h / 2)), _fx(sw_w), _fy(sw_h),
            facecolor=ARM_COLORS[arm], edgecolor="none",
            transform=fig.transFigure))
        fig.text(_fx(x + sw_w + gap_k), _fy(3.0), lab, ha="left", va="center",
                 fontsize=FONT, color=INK)
        x += sw_w + gap_k + label_w[arm] + gap_e

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        # the tall grid cell saves exact (the composite places it 1:1); the
        # standalone render keeps the tight crop
        save_kw = ({} if LAYOUT == "tall"
                   else {"bbox_inches": "tight", "pad_inches": 0.02})
        fig.savefig(OUT_DIR / f"{OUT_STEM}.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", **save_kw)
    plt.close(fig)
    print(f"fig4f ({LAYOUT}) -> {OUT_DIR / f'{OUT_STEM}.pdf'} (+png 1200 dpi); "
          f"overreach {sum(ungated)} -> 0 by oracle x use "
          f"({', '.join(str(n) for n in ungated)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
