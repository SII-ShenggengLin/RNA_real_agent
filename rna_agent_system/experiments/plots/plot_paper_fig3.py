#!/usr/bin/env python3
"""Paper Fig 3 — Oracle capability profiling (E1 v2 + P2 calibration).

Panels:
  a  Screening heatmap: 3 oracles x 6 targets AUROC (centered at 0.5 = chance).
  b  Ranking: Spearman rho per oracle x target vs pre-registered rho >= 0.6 gate.
  c  Docking: native-pose rank for 5 RNA-protein complexes (rank 1 = best, inverted y).
  d  P2 calibration: thrombin 4-point Kd series + binder-vs-negative score strips.

Data (read directly, nothing recomputed beyond reshaping):
  experiments/results/e1_capability_summary_v2.json
  experiments/results/p2_aptamer_calibration_summary.json
  experiments/results/p2_aptamer_calibration.jsonl

Output: experiments/plots/paper/fig3.png  (300 dpi)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib import gridspec

import json

RESULTS = Path(__file__).resolve().parent.parent / "results"
OUTDIR = Path(__file__).resolve().parent / "paper"
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- style ----
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


def panel_label(ax, letter, dx=-0.14, dy=1.06):
    ax.text(
        dx, dy, letter, transform=ax.transAxes,
        fontsize=10, fontweight="bold", va="top", ha="left",
    )


# ------------------------------------------------------------------ data ----
e1 = json.load(open(RESULTS / "e1_capability_summary_v2.json"))
targets = e1["targets"]  # Thrombin, VEGF, PDGF-BB, IL-17A, Angiopoietin-2, SARS-CoV-2 N
oracle_keys = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
oracle_names = ["EGARPS\nnative prob.", "Protenix\nipTM", "RhoFold\npLDDT"]
pa = e1["part_a_per_oracle_target"]

auroc = np.array([[pa[f"{o} | {t}"]["screening_auroc"] for t in targets] for o in oracle_keys])
rho = np.array([[pa[f"{o} | {t}"]["ranking_spearman_rho"] for t in targets] for o in oracle_keys])

dock = e1["part_b_docking"]
PDB = {  # anchor -> pdb id (verified against e1_docking_power{,_v2}.jsonl)
    "tba_thrombin": "4DII", "toggle25t_thrombin": "3DD2", "hd22_t27_thrombin": "4I7Y",
    "t1p1_hiv1rt": "1HVU", "dtri177_fixa": "8EPK",
}
LIGAND = {
    "tba_thrombin": "TBA", "toggle25t_thrombin": "Toggle-25t",
    "hd22_t27_thrombin": "HD22-T27", "t1p1_hiv1rt": "t1p1",
    "dtri177_fixa": "DTri177",
}
dock_cases = sorted(dock.items(), key=lambda kv: -kv[1]["native_rank"])

p2s = json.load(open(RESULTS / "p2_aptamer_calibration_summary.json"))
p2_rows = [json.loads(l) for l in open(RESULTS / "p2_aptamer_calibration.jsonl")]
thr_pts = p2s["thrombin_series"]["points"]
thr_x = [-np.log10(p["kd_nm"]) for p in thr_pts]
thr_y = [p["native_probability"] for p in thr_pts]
thr_rho = p2s["thrombin_series"]["spearman_rho_native_probability_vs_neglogKd"]
binders = [r["raw"]["egarps_native_probability"] for r in p2_rows if r["role"] == "binder"]
negatives = [r["raw"]["egarps_native_probability"] for r in p2_rows if r["role"] == "negative"]
p2_auroc = p2s["binder_vs_negative"]["auroc"]

# ---------------------------------------------------------------- figure ----
fig = plt.figure(figsize=(7.2, 7.0))
gs = gridspec.GridSpec(
    2, 2, figure=fig, height_ratios=[1.0, 0.95], width_ratios=[1.0, 1.0],
    hspace=0.58, wspace=0.40, left=0.125, right=0.98, top=0.90, bottom=0.10,
)

# ---- Panel a: screening AUROC heatmap -------------------------------------
axa = fig.add_subplot(gs[0, 0])
norm = mcolors.TwoSlopeNorm(vmin=0.0, vcenter=0.5, vmax=1.0)
im = axa.imshow(auroc, cmap="RdYlGn", norm=norm, aspect="auto")
for i in range(auroc.shape[0]):
    for j in range(auroc.shape[1]):
        axa.text(j, i, f"{auroc[i, j]:.2f}", ha="center", va="center",
                 fontsize=7, color="black")
axa.set_xticks(range(len(targets)))
axa.set_xticklabels(targets, rotation=28, ha="right")
axa.set_yticks(range(len(oracle_names)))
axa.set_yticklabels(oracle_names, fontsize=7)
axa.set_title("Screening power: binder-vs-negative AUROC", pad=24)
axa.text(0.5, 1.075, "0/18 cells pass (best = 0.80, 95% CI 0.33–1.0)",
         transform=axa.transAxes, ha="center", fontsize=7.5, color=RED)
axa.set_xticks(np.arange(-0.5, len(targets), 1), minor=True)
axa.set_yticks(np.arange(-0.5, len(oracle_names), 1), minor=True)
axa.grid(which="minor", color="white", linewidth=1.2)
axa.tick_params(which="minor", length=0)
strip_spines(axa, keep=())
cb = fig.colorbar(im, ax=axa, fraction=0.045, pad=0.03)
cb.set_ticks([0.0, 0.25, 0.5, 1.0])
cb.ax.tick_params(labelsize=7, width=0.6, length=2.5)
cb.outline.set_visible(False)
cb.ax.plot([0, 1], [0.8, 0.8], color="black", lw=1.0, transform=cb.ax.transAxes)
cb.ax.text(1.5, 0.8, "pass gate\n> 0.8", transform=cb.ax.transAxes,
           fontsize=6.5, va="center", ha="left", linespacing=1.1)
panel_label(axa, "a", dx=-0.26, dy=1.13)

# ---- Panel b: ranking Spearman rho ----------------------------------------
axb = fig.add_subplot(gs[0, 1])
x = np.arange(len(targets))
w = 0.26
cols = [BLUE, ORANGE, GREEN]
for k, name in enumerate(["EGARPS np", "Protenix ipTM", "RhoFold pLDDT"]):
    axb.bar(x + (k - 1) * w, rho[k], width=w, color=cols[k], label=name,
            edgecolor="none", zorder=3)
axb.axhline(0.6, color=RED, lw=0.9, ls="--", zorder=2)
axb.text(5.45, 0.64, "pre-registered gate ρ ≥ 0.6", fontsize=6.5,
         color=RED, ha="right")
axb.axhline(0.0, color=GREY, lw=0.6, zorder=2)
best_i, best_j = 2, targets.index("PDGF-BB")  # rhofold x PDGF-BB = 0.564
bx = x[best_j] + (best_i - 1) * w
axb.plot([bx], [rho[best_i, best_j] + 0.035], marker="*", color="black",
         markersize=7, zorder=4)
axb.text(0.98, 0.965, "* best ρ = 0.564 (RhoFold × PDGF-BB) — still fails",
         transform=axb.transAxes, ha="right", va="top", fontsize=6.5, color="black")
axb.set_xticks(x)
axb.set_xticklabels(targets, rotation=28, ha="right")
axb.set_ylabel("Spearman ρ (score vs measured $K_d$)")
axb.set_ylim(-0.62, 0.98)
axb.set_title("Affinity-ranking power ($K_d$ series)", pad=6)
axb.legend(loc="lower left", frameon=False, handlelength=1.2,
           borderaxespad=0.0, labelspacing=0.3)
strip_spines(axb)
axb.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axb.set_axisbelow(True)
panel_label(axb, "b", dx=-0.20)

# ---- Panel c: docking native-pose ranks ------------------------------------
axc = fig.add_subplot(gs[1, 0])
labels, ranks, totals = [], [], []
for key, d in dock_cases:
    labels.append(f"{LIGAND[key]}\n({PDB[key]})")
    ranks.append(d["native_rank"])
    totals.append(d["n_poses_scored"])
xc = np.arange(len(labels))
for xi, r, n in zip(xc, ranks, totals):
    axc.plot([xi, xi], [1, r], color=GREY, lw=1.0, zorder=2)
    axc.scatter([xi], [r], s=42, color=BLUE, zorder=3, edgecolor="white", linewidth=0.6)
    axc.annotate(f"{r}/{n}", xy=(xi, r), xytext=(0, 6), textcoords="offset points",
                 ha="center", fontsize=7, color="black")
axc.axhline(1, color=GREEN, lw=0.9, ls="--", zorder=1)
axc.text(0.1, 2.6, "native pose ranked top-1 (best)", fontsize=6.5, color=GREEN)
axc.set_ylim(23, -2.0)  # inverted: rank 1 (best) at top
axc.set_yticks([1, 5, 10, 15, 21])
axc.set_ylabel("Native-pose rank among scored poses\n(rank 1 = best)")
axc.set_xticks(xc)
axc.set_xticklabels(labels, fontsize=6.5)
axc.set_xlim(-0.55, len(labels) - 0.45)
axc.set_title("Docking power: native-pose rank (EGARPS)", pad=24)
axc.text(0.5, 1.075, "gate: native top-1 in ≥ 2/3 of cases  →  0/5 passed",
         transform=axc.transAxes, ha="center", fontsize=7.5, color=RED)
strip_spines(axc)
panel_label(axc, "c", dx=-0.26, dy=1.13)

# ---- Panel d: P2 calibration (two sub-axes) --------------------------------
gsd = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[1, 1], wspace=0.75)
axd1 = fig.add_subplot(gsd[0, 0])
axd1.scatter(thr_x, thr_y, s=34, color=BLUE, zorder=3, edgecolor="white", linewidth=0.6)
short = {"hd22_thrombin": "HD22", "hd22_t27_thrombin": "HD22-T27",
         "toggle25t_thrombin": "Tog-25t", "tba_thrombin": "TBA"}
offsets = {"hd22_thrombin": (4, 4), "hd22_t27_thrombin": (5, -3),
           "toggle25t_thrombin": (4, -8), "tba_thrombin": (4, 3)}
for p, xi, yi in zip(thr_pts, thr_x, thr_y):
    axd1.annotate(short[p["id"]], xy=(xi, yi), xytext=offsets[p["id"]],
                  textcoords="offset points", fontsize=6, color=GREY)
axd1.set_yscale("log")
axd1.set_ylim(3e-4, 3)
axd1.set_xlim(-1.85, 0.75)
axd1.set_xlabel("−log$_{10}$ $K_d$ (nM), thrombin series", fontsize=7)
axd1.set_ylabel("EGARPS native probability", fontsize=7)
axd1.set_title("Thrombin 4-point $K_d$ series", pad=26, fontsize=7.5)
axd1.text(0.5, 1.05, f"Spearman ρ = {thr_rho:.2f}\n(gate ≥ 0.6) → fail",
          transform=axd1.transAxes, ha="center", va="bottom", fontsize=6.5,
          color=RED, linespacing=1.3)
strip_spines(axd1)
axd1.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axd1.set_axisbelow(True)
axd1.tick_params(labelsize=6.5)

axd2 = fig.add_subplot(gsd[0, 1])
rng = np.random.default_rng(7)
for xi, vals, col in [(0, binders, BLUE), (1, negatives, RED)]:
    jit = rng.uniform(-0.12, 0.12, len(vals))
    axd2.scatter(np.full(len(vals), xi) + jit, vals, s=26, color=col, alpha=0.85,
                 zorder=3, edgecolor="white", linewidth=0.5)
axd2.set_yscale("log")
axd2.set_ylim(8e-9, 6)
axd2.set_xlim(-0.6, 3.5)
axd2.set_xticks([0, 1])
axd2.set_xticklabels(["binders (n=9)", "negatives (n=5)"], rotation=22, ha="right")
axd2.set_ylabel("EGARPS native probability", fontsize=7)
axd2.set_title("Binders vs negatives", pad=26, fontsize=7.5)
axd2.text(0.30, 1.05, f"AUROC = {p2_auroc:.3f}\ndirectionally inverted",
          transform=axd2.transAxes, ha="center", va="bottom", fontsize=6.5,
          color=RED, linespacing=1.3)
axd2.annotate("pegaptanib\n1.9×10$^{-6}$", xy=(0.06, 1.9145918e-06),
              xytext=(-0.52, 2.0e-4), fontsize=6, ha="left", linespacing=1.2,
              arrowprops=dict(arrowstyle="-", lw=0.6, color=GREY))
axd2.annotate("scrambled TBA 0.99\nrandom 30-nt 0.95", xy=(1.02, 0.97),
              xytext=(-0.5, 1.6), fontsize=6, ha="left", va="bottom",
              linespacing=1.3,
              arrowprops=dict(arrowstyle="-", lw=0.6, color=GREY))
strip_spines(axd2)
axd2.tick_params(labelsize=6.5)
panel_label(axd1, "d", dx=-0.34, dy=1.10)

fig.savefig(OUTDIR / "fig3.png")
print("wrote", OUTDIR / "fig3.png")
