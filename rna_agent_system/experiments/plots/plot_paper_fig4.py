#!/usr/bin/env python3
"""Paper Fig 4 — Self-audit and gating.

Panels:
  a  The confound: Cliff's delta of the legacy Fig-4 main effect vs the two
     budget-matched controls (P0, P3); pre-registered GO gate delta >= 0.3.
  b  Self-audit (E2): two in-house claims through the 4-step audit, 0/2 survive
     vs the pre-registered 70% threshold.
  c  Double gating (E3): FP rate, true positives, overreach events, ungated vs gated.

Data (read directly from result files):
  experiments/results/fig4_summary.json
  experiments/results/p0_budget_matched_summary.json
  experiments/results/p3_guided_vs_unguided_summary.json
  experiments/results/e3_runs_full_summary.json
  (E2 verdict per experiments/results/E2_SELF_AUDIT_FIG4_FIG7B.md: survival 0/2 < 70%)

Output: experiments/plots/paper/fig4.png  (300 dpi)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec

import json

RESULTS = Path(__file__).resolve().parent.parent / "results"
OUTDIR = Path(__file__).resolve().parent / "paper"
OUTDIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "savefig.dpi": 300,
        "figure.dpi": 300,
    }
)
BLUE, ORANGE, GREEN, RED, PURPLE = "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"
GREY = "#666666"


def strip_spines(ax, keep=("left", "bottom")):
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


# ------------------------------------------------------------------ data ----
f4 = json.load(open(RESULTS / "fig4_summary.json"))
main_eff = f4["paired_tests"]["metrics"]["egarps_component"]["bmc1_vs_serial"]
p0 = json.load(open(RESULTS / "p0_budget_matched_summary.json"))
p3 = json.load(open(RESULTS / "p3_guided_vs_unguided_summary.json"))
e3 = json.load(open(RESULTS / "e3_runs_full_summary.json"))
ungated = e3["per_arm"]["ungated"]
gated = e3["per_arm"]["gated"]

# ---------------------------------------------------------------- figure ----
fig = plt.figure(figsize=(7.2, 3.2))
gs = gridspec.GridSpec(
    1, 3, figure=fig, width_ratios=[1.10, 1.00, 1.50],
    wspace=0.40, left=0.06, right=0.985, top=0.80, bottom=0.16,
)

# ---- Panel a: the confound (forest plot of Cliff's delta) -------------------
axa = fig.add_subplot(gs[0, 0])
rows = [
    ("Ungated main effect (legacy Fig 4)",
     f"δ = {main_eff['cliffs_delta']:.3f}, p = 2.1×10$^{{-4}}$ (n = 19)",
     main_eff["cliffs_delta"], RED),
    ("Budget-matched control (P0)",
     f"δ = {p0['cliffs_delta']:.3f}, p = {p0['wilcoxon_paired_p']:.3f} NS (n = 12)",
     p0["cliffs_delta"], BLUE),
    ("Guided vs unguided diagnosis (P3)",
     f"δ = {p3['cliffs_delta']:.3f}, p = {p3['wilcoxon_paired_p']:.3f} NS (n = 12)",
     p3["cliffs_delta"], BLUE),
]
ys = [2.4, 1.2, 0.0]
for (label, stats, d, col), y in zip(rows, ys):
    axa.text(0.0, y + 0.37, label, fontsize=6.8, ha="left", va="center")
    axa.scatter([d], [y], s=55, color=col, zorder=3, edgecolor="white", linewidth=0.7)
    axa.text(0.0, y - 0.37, stats, fontsize=6.3, ha="left", va="center", color=col)
axa.axvline(0.3, color=GREY, lw=0.9, ls="--", zorder=1)
axa.text(0.3, 3.30, "pre-registered\nGO gate δ ≥ 0.3", fontsize=6.3, color=GREY,
         ha="center", va="bottom", linespacing=1.3)
axa.axvline(0.0, color=GREY, lw=0.6, zorder=1)
axa.set_xlim(-0.02, 0.95)
axa.set_ylim(-0.78, 4.05)
axa.set_yticks([])
axa.set_xticks([0.0, 0.2, 0.4, 0.6])
axa.set_xlabel("Cliff's δ (EGARPS component, best-of-pool)", fontsize=7)
axa.set_title("The confound: the effect falls below\nthe GO gate once budgets match",
              pad=3)
strip_spines(axa, keep=("bottom",))
axa.xaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axa.set_axisbelow(True)
axa.text(-0.04, 1.18, "a", transform=axa.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")

# ---- Panel b: self-audit (E2) ----------------------------------------------
axb = fig.add_subplot(gs[0, 1])
axb.set_xlim(0, 1)
axb.set_ylim(0, 1)
axb.set_xticks([])
axb.set_yticks([])
strip_spines(axb, keep=())
axb.set_title("Self-audit of in-house claims (E2):\n4-step audit, gated verdict",
              pad=3)
claims = [
    ("Fig-4 coordination effect",
     "“BMC×1 improves aptamer design”"),
    ("Fig-7B pegaptanib comparison",
     "“designed candidate vs marketed drug”"),
]
for i, (c1, c2) in enumerate(claims):
    yc = 0.84 - i * 0.27
    axb.text(0.02, yc, c1, transform=axb.transAxes, fontsize=6.8, va="center",
             fontweight="bold")
    axb.text(0.02, yc - 0.09, c2, transform=axb.transAxes, fontsize=6.0,
             va="center", color=GREY)
    axb.text(0.98, yc - 0.045, "✗ retired", transform=axb.transAxes, fontsize=7,
             color=RED, ha="right", va="center", fontweight="bold")
    if i == 0:
        axb.plot([0.02, 0.98], [yc - 0.175] * 2, color="#DDDDDD", lw=0.6,
                 transform=axb.transAxes)
# survival bar
yb = 0.12
axb.add_patch(plt.Rectangle((0.02, yb), 0.96, 0.065, fc="#E7E7E7", ec="none",
                            transform=axb.transAxes))
axb.plot([0.02 + 0.96 * 0.7] * 2, [yb - 0.025, yb + 0.095], color=GREY, lw=0.9,
         ls="--", transform=axb.transAxes)
axb.text(0.02 + 0.96 * 0.7, yb + 0.115, "gate: survival < 70%",
         transform=axb.transAxes, fontsize=6.0, color=GREY, ha="center",
         va="bottom")
axb.text(0.02, yb - 0.06, "claim survival: 0/2 (0%) — both retired",
         transform=axb.transAxes, fontsize=6.5, color="black", ha="left",
         va="top", fontweight="bold")
axb.text(-0.05, 1.18, "b", transform=axb.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")

# ---- Panel c: double gating (E3) --------------------------------------------
gsc = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[0, 2], wspace=0.78)
specs = [
    ("FP rate (%)", ungated["fp_rate"] * 100, gated["fp_rate"] * 100,
     "57.9%", "0%",
     ungated["fp_rate"] * 100 * e3["thresholds"]["fp_relative_reduction_go"],
     "≥50% rel. reduction", None),
    ("true positives (n)", ungated["TP"], gated["TP"], "8", "9",
     ungated["TP"] * e3["thresholds"]["tp_retention_go"], "≥90% retention",
     "retention 112.5%"),
    ("overreach (n)", ungated["overreach_events"], gated["overreach_events"],
     "23", "0", None, None, None),
]
for k, (ylab, vu, vg, lu, lg, thr, thrtxt, extra) in enumerate(specs):
    ax = fig.add_subplot(gsc[0, k])
    ax.bar([0], [vu], width=0.62, color=RED, zorder=3)
    ax.bar([1], [vg], width=0.62, color=GREEN, zorder=3)
    ax.text(0, vu, lu, ha="center", va="bottom", fontsize=7, fontweight="bold",
            color=RED)
    ax.text(1, vg, lg, ha="center", va="bottom", fontsize=7, fontweight="bold",
            color=GREEN)
    ymax = max(vu, vg)
    if thr is not None:
        ax.axhline(thr, color=GREY, lw=0.9, ls="--", zorder=2)
        ax.text(1.60, thr, thrtxt, fontsize=5.6, color=GREY, ha="center",
                va="bottom", rotation=90)
    if extra:
        ax.text(0.5, 0.99, "retention\n112.5%", transform=ax.transAxes,
                fontsize=5.8, color=GREEN, ha="center", va="top",
                linespacing=1.25)
    ax.set_xlim(-0.65, 1.65)
    ax.set_ylim(0, ymax * 1.38)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["ungated", "gated"], fontsize=6, rotation=25, ha="right")
    ax.set_ylabel(ylab, fontsize=6.3)
    ax.set_yticks([0, ymax])
    ax.tick_params(labelsize=6.3)
    strip_spines(ax)
    ax.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
fig.axes[-2].set_title("Double gating (E3): 20 tasks × 2 arms", pad=3)
fig.axes[-3].text(-0.55, 1.18, "c", transform=fig.axes[-3].transAxes,
                  fontsize=10, fontweight="bold", va="top", ha="left")

fig.savefig(OUTDIR / "fig4.png")
print("wrote", OUTDIR / "fig4.png")
