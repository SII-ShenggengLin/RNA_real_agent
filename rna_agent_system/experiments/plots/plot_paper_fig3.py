#!/usr/bin/env python3
"""Paper Fig 3 — Oracle capability profiling, two-sided (E1 v2 + P2 + E7).

Panels (paper v2, 2026-08-11):
  a  Screening heatmap: 3 oracles x 6 targets AUROC (centered at 0.5 = chance).
  b  Ranking: Spearman rho per oracle x target vs pre-registered rho >= 0.6 gate.
  c  Aptamer chain, continued: docking native-pose ranks (0/5 top-1) + P2
     thrombin 4-point Kd calibration (rho = 0.40) + binder-vs-negative strips
     (AUROC = 0.356).
  d  mRNA chain (E7): GEMORNA 5'UTR MRL oracle passes both gates on all three
     measured-MRL anchor families (n = 706 anchors); the 3'UTR stability
     predictor is registered unprofiled and gated off (hatched cells).
     Message: revocation on the aptamer chain, certification on the mRNA chain.

Data (read directly, nothing recomputed beyond reshaping):
  experiments/results/e1_capability_summary_v2.json
  experiments/results/p2_aptamer_calibration_summary.json
  experiments/results/p2_aptamer_calibration.jsonl
  experiments/results/e7_mrna_oracle_profile_summary.json

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

# E7 mRNA-side oracle profile (GEMORNA 5'UTR MRL on measured-MRL anchors).
e7 = json.load(open(RESULTS / "e7_mrna_oracle_profile_summary.json"))
e7_fams = e7["per_family"]
e7_order = ["sample2019_egfp_random50", "sample2019_varying_length_human",
            "sample2019_varying_length_random"]
e7_short = ["EGFP\nrandom-50", "human\nvary-length", "random\nvary-length"]
e7_auroc = [e7_fams[f]["screening"]["auroc"] for f in e7_order]
e7_rho = [e7_fams[f]["ranking"]["spearman_rho"] for f in e7_order]
e7_n = sum(e7_fams[f]["n_scored"] for f in e7_order)
assert e7_n == 706 and all(e7_fams[f]["screening"]["grade"] == "verified"
                           and e7_fams[f]["ranking"]["grade"] == "verified"
                           for f in e7_order)

# ---------------------------------------------------------------- figure ----
fig = plt.figure(figsize=(7.2, 10.4))
gs = gridspec.GridSpec(
    3, 2, figure=fig, height_ratios=[1.05, 0.72, 0.78], width_ratios=[1.0, 1.0],
    hspace=0.40, wspace=0.40, left=0.125, right=0.98, top=0.95, bottom=0.075,
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

# ---- Panel c: docking + affinity calibration (aptamer chain) ----------------
gsc = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[1, :], wspace=0.50)

axc1 = fig.add_subplot(gsc[0, 0])
labels, ranks, totals = [], [], []
for key, d in dock_cases:
    labels.append(LIGAND[key])
    ranks.append(d["native_rank"])
    totals.append(d["n_poses_scored"])
xc = np.arange(len(labels))
for xi, r, n in zip(xc, ranks, totals):
    axc1.plot([xi, xi], [1, r], color=GREY, lw=0.9, zorder=2)
    axc1.scatter([xi], [r], s=26, color=BLUE, zorder=3, edgecolor="white",
                 linewidth=0.5)
    axc1.annotate(f"{r}/{n}", xy=(xi, r), xytext=(0, 4),
                  textcoords="offset points", ha="center", fontsize=5.6)
axc1.axhline(1, color=GREEN, lw=0.9, ls="--", zorder=1)
axc1.set_ylim(24, -3.0)  # inverted: rank 1 (best) at top
axc1.set_yticks([1, 5, 10, 15, 21])
axc1.set_ylabel("native-pose rank\n(rank 1 = best)", fontsize=6.5)
axc1.set_xticks(xc)
axc1.set_xticklabels(labels, fontsize=6, rotation=24, ha="right")
axc1.set_xlim(-0.55, len(labels) - 0.45)
axc1.set_title("docking: native-pose rank\n0/5 top-1 (gate ≥ 2/3) → fail",
               pad=4, fontsize=7)
strip_spines(axc1)
axc1.tick_params(labelsize=6)
panel_label(axc1, "c", dx=-0.24, dy=1.16)

axc2 = fig.add_subplot(gsc[0, 1])
axc2.scatter(thr_x, thr_y, s=24, color=BLUE, zorder=3, edgecolor="white",
             linewidth=0.5)
axc2.set_yscale("log")
axc2.set_ylim(3e-4, 3)
axc2.set_xlim(-1.85, 0.75)
axc2.set_xlabel("−log$_{10}$ $K_d$ (nM), thrombin", fontsize=6.5)
axc2.set_ylabel("EGARPS native prob.", fontsize=6.5)
axc2.set_title(f"affinity calibration (thrombin)\nρ = {thr_rho:.2f} "
               "(gate ≥ 0.6) → fail", pad=4, fontsize=7)
strip_spines(axc2)
axc2.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axc2.set_axisbelow(True)
axc2.tick_params(labelsize=6)

axc3 = fig.add_subplot(gsc[0, 2])
rng = np.random.default_rng(7)
for xi, vals, col in [(0, binders, BLUE), (1, negatives, RED)]:
    jit = rng.uniform(-0.12, 0.12, len(vals))
    axc3.scatter(np.full(len(vals), xi) + jit, vals, s=20, color=col,
                 alpha=0.85, zorder=3, edgecolor="white", linewidth=0.4)
axc3.set_yscale("log")
axc3.set_ylim(8e-9, 6)
axc3.set_xlim(-0.6, 1.6)
axc3.set_xticks([0, 1])
axc3.set_xticklabels([f"binders\n(n={len(binders)})",
                      f"negatives\n(n={len(negatives)})"], fontsize=6)
axc3.set_ylabel("EGARPS native prob.", fontsize=6.5)
axc3.set_title(f"binders vs negatives\nAUROC = {p2_auroc:.3f} (inverted) → fail",
               pad=4, fontsize=7)
strip_spines(axc3)
axc3.tick_params(labelsize=6)

# ---- Panel d: E7 mRNA-side oracle profile ------------------------------------
gsd = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[2, :], wspace=0.38)
fam_labels = e7_short + ["3'UTR stab.\n(unprofiled)"]
xd = np.arange(len(fam_labels))

axd1 = fig.add_subplot(gsd[0, 0])
axd1.bar(xd[:3], e7_auroc, width=0.62, color=GREEN, zorder=3)
axd1.bar([xd[3]], [1.0], width=0.62, facecolor="white", edgecolor=GREY,
         hatch="///", lw=0.7, zorder=3)
axd1.text(xd[3], 0.44, "registered\nunprofiled\ngated off", ha="center",
          fontsize=6, color=GREY, linespacing=1.3)
for xi, v in zip(xd[:3], e7_auroc):
    axd1.text(xi, v + 0.04, f"{v:.3f}", ha="center", fontsize=6.5,
              color=GREEN, fontweight="bold")
axd1.axhline(0.8, color=RED, lw=0.9, ls="--", zorder=2)
axd1.text(3.45, 0.79, "gate > 0.8", fontsize=6, color=RED, ha="right",
          va="top")
axd1.set_xticks(xd)
axd1.set_xticklabels(fam_labels, fontsize=6.5)
axd1.set_xlim(-0.55, 3.55)
axd1.set_ylim(0, 1.20)
axd1.set_yticks([0, 0.5, 0.8, 1.0])
axd1.set_ylabel("screening AUROC", fontsize=7)
axd1.set_title("screening: 3/3 families verified", pad=4, fontsize=7)
strip_spines(axd1)
axd1.tick_params(labelsize=6.5)
axd1.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axd1.set_axisbelow(True)
panel_label(axd1, "d", dx=-0.16, dy=1.16)

axd2 = fig.add_subplot(gsd[0, 1])
axd2.bar(xd[:3], e7_rho, width=0.62, color=GREEN, zorder=3)
axd2.bar([xd[3]], [1.0], width=0.62, facecolor="white", edgecolor=GREY,
         hatch="///", lw=0.7, zorder=3)
axd2.text(xd[3], 0.44, "registered\nunprofiled\ngated off", ha="center",
          fontsize=6, color=GREY, linespacing=1.3)
for xi, v in zip(xd[:3], e7_rho):
    axd2.text(xi, v + 0.04, f"{v:.3f}", ha="center", fontsize=6.5,
              color=GREEN, fontweight="bold")
axd2.axhline(0.6, color=RED, lw=0.9, ls="--", zorder=2)
axd2.text(3.45, 0.59, "gate ρ ≥ 0.6", fontsize=6, color=RED, ha="right",
          va="top")
axd2.set_xticks(xd)
axd2.set_xticklabels(fam_labels, fontsize=6.5)
axd2.set_xlim(-0.55, 3.55)
axd2.set_ylim(0, 1.10)
axd2.set_yticks([0, 0.3, 0.6, 0.9])
axd2.set_ylabel("Spearman ρ (score vs measured MRL)", fontsize=7)
axd2.set_title("ranking: 3/3 families verified", pad=4, fontsize=7)
strip_spines(axd2)
axd2.tick_params(labelsize=6.5)
axd2.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axd2.set_axisbelow(True)
axd1.text(0.0, 1.26,
          f"mRNA chain (E7): GEMORNA 5′UTR MRL oracle — certified, "
          f"n = {e7_n} anchors",
          transform=axd1.transAxes, fontsize=7.5, color=GREEN,
          fontweight="bold", ha="left")

fig.savefig(OUTDIR / "fig3.png")
print("wrote", OUTDIR / "fig3.png")
