#!/usr/bin/env python3
"""Paper Fig 5 — Generation-layer constraint navigation (E5 diagnosis + E6/E8 GenNav).

Panels:
  a  E5 S1 diagnosis: constraint-passing pool fraction per target (315 candidates
     each), with the failure attribution; all residual failures are generation-layer.
  b  E6 S2 primary endpoint: per-profile joint-criteria delivery (JCD pass) grid,
     18 targets x 3 profiles, arm A (rule-based) vs arm C (gated GenNav);
     McNemar 30:0, p = 1.9e-09.
  c  Efficiency: LLM calls per gene (arm C) vs the pre-registered 5-9 budget band.
  d  E8 S2 aptamer transfer: per-profile JCD grid, 10 targets x 3 profiles;
     discordance 3:1 (C repairs BSA compact / VEGF extended / SARS-CoV-2 N
     extended; one self-inflicted shortfall MBP compact), McNemar p = 0.625 NS —
     primary endpoint NOT met (26/30 pairs saturate); shown honestly as
     mechanical, budget-matched transfer (C e2e 9/10 vs A 7/10; mean raw spend
     36 vs 48 candidates).

Data:
  experiments/results/E5_REPORT_2026-08-09.md   (pool-pass counts, r5 table)
  experiments/results/e6_s2_runs.jsonl          (per-target per-profile JCD, LLM calls)
  experiments/results/e6_s2_verdict_aggregated.json (McNemar stats; asserted)
  experiments/results/e8_verdict_s2.json        (E8 per-pair JCD + McNemar; asserted)
  experiments/results/e8_runs_s2.jsonl          (E8 per-arm raw candidate spend, e2e)

Output: experiments/plots/paper/fig5.png  (300 dpi)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from matplotlib.patches import Patch
from matplotlib import colors as mcolors

import json
import re

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
# Panel a: pool-pass counts parsed from the E5 report r5 table (lines like
# "| A1AT | human | 60/315 | ..."); GFP pre-B0 = 0/315 (report: "0/315 → 12/315").
report = (RESULTS / "E5_REPORT_2026-08-09.md").read_text()
pool = {}
for m in re.finditer(r"^\|\s*([A-Za-z0-9\-]+)\s*\|[^|]*\|\s*(\d+)/315", report, re.M):
    pool[m.group(1)] = int(m.group(2))
assert pool == {"A1AT": 60, "Insulin": 92, "EPO": 306, "GFP": 12, "IL-2": 192}, pool
e5_targets = ["EPO", "IL-2", "Insulin", "A1AT", "GFP"]  # descending pass count
e5_verdict = {"EPO": "GO", "IL-2": "GO", "Insulin": "NO-GO", "A1AT": "NO-GO",
              "GFP": "NO-GO"}

# Panels b/c: recompute per-profile JCD pass from the run records.
runs = [json.loads(l) for l in open(RESULTS / "e6_s2_runs.jsonl")]
verdict = json.load(open(RESULTS / "e6_s2_verdict_aggregated.json"))
profiles = ["expression", "stability", "balanced"]
targets, grid_a, grid_c, llm = [], [], [], []
for r in runs:
    targets.append(r["target_id"])
    ja, jc = {}, {}
    for p in r["evaluations"]["A"]["profiles"]:
        ja[p["profile"]] = bool(p["e2e_pass"] and p["D1"] and p["D2"] and p["R3"])
    for p in r["evaluations"]["C"]["profiles"]:
        jc[p["profile"]] = bool(p["e2e_pass"] and p["D1"] and p["D2"] and p["R3"])
    grid_a.append([ja[p] for p in profiles])
    grid_c.append([jc[p] for p in profiles])
    llm.append(r["evaluations"]["C"]["llm_calls"])
grid_a = np.array(grid_a).T  # 3 profiles x 18 targets
grid_c = np.array(grid_c).T
# cross-check against the aggregated verdict (McNemar b=30, c=0, n=54)
b_disc = int(np.sum((~grid_a) & grid_c))
c_disc = int(np.sum(grid_a & (~grid_c)))
assert (b_disc, c_disc) == (30, 0), (b_disc, c_disc)
assert verdict["observed"]["mcnemar"]["C_vs_A"]["b"] == 30
assert sum(llm) == 43 and len(llm) == 18
her2_i = targets.index("HER2")

# Panel d: E8 aptamer transfer (S2) — per-pair JCD from the verdict file,
# raw candidate spend from the run records; everything cross-asserted.
e8v = json.load(open(RESULTS / "e8_verdict_s2.json"))
e8_runs = [json.loads(l) for l in open(RESULTS / "e8_runs_s2.jsonl")]
e8_profiles = ["compact", "standard", "extended"]
e8_targets = e8v["targets"]
e8_pairs = {(p["target_id"], p["profile"]): (p["A_jcd"], p["C_jcd"])
            for p in e8v["pairs"]}
grid8_a = np.array([[e8_pairs[(t, p)][0] for t in e8_targets]
                    for p in e8_profiles])
grid8_c = np.array([[e8_pairs[(t, p)][1] for t in e8_targets]
                    for p in e8_profiles])
b8 = int(np.sum((~grid8_a) & grid8_c))
c8 = int(np.sum(grid8_a & (~grid8_c)))
mc = e8v["primary"]["mcnemar"]
assert (b8, c8) == (mc["b"], mc["c"]) == (3, 1), (b8, c8)
assert e8v["primary"]["n_pairs"] == 30 and not e8v["primary"]["pass"]
spend = {arm: [len(r.get("candidates") or []) for r in e8_runs
               if r["arm"] == arm] for arm in ("A", "C")}
e2e = {arm: [bool(r.get("e2e")) for r in e8_runs if r["arm"] == arm]
       for arm in ("A", "C")}
assert len(spend["A"]) == len(spend["C"]) == 10
mean_a, mean_c = float(np.mean(spend["A"])), float(np.mean(spend["C"]))
assert round(mean_a) == 48 and round(mean_c) == 36, (mean_a, mean_c)
assert sum(e2e["A"]) == 7 and sum(e2e["C"]) == 9
assert (e8v["primary"]["a_e2e_rate"], e8v["primary"]["c_e2e_rate"]) == (0.7, 0.9)
# discordant cells: frame BOTH cells of each pair, coloured by the winner
e8_discordant = []
for j, t in enumerate(e8_targets):
    for i, p in enumerate(e8_profiles):
        a_ok, c_ok = e8_pairs[(t, p)]
        if a_ok != c_ok:
            winner = "C" if c_ok else "A"
            e8_discordant += [(i, j, winner), (3 + i, j, winner)]
assert len(e8_discordant) == 8
n8_concordant_pass = int(np.sum(grid8_a & grid8_c))
assert n8_concordant_pass == 26

# ---------------------------------------------------------------- figure ----
fig = plt.figure(figsize=(7.2, 9.7))
gs = gridspec.GridSpec(
    3, 2, figure=fig, height_ratios=[1.0, 0.95, 0.82], width_ratios=[1.25, 1.15],
    hspace=0.52, wspace=0.30, left=0.14, right=0.985, top=0.94, bottom=0.115,
)

# ---- Panel a: E5 pool-pass fractions ----------------------------------------
axa = fig.add_subplot(gs[0, 0])
fracs = [pool[t] / 315 * 100 for t in e5_targets]
colors = [GREEN if e5_verdict[t] == "GO" else RED for t in e5_targets]
colors[e5_targets.index("GFP")] = ORANGE  # GFP: post-B0 state
xa = np.arange(len(e5_targets))
axa.bar(xa, fracs, width=0.62, color=colors, zorder=3)
for xi, t, f in zip(xa, e5_targets, fracs):
    dx = -0.30 if t == "GFP" else 0.0  # keep GFP labels clear of the B0 arrow
    axa.text(xi + dx, f + 2.0, f"{pool[t]}/315", ha="center", va="bottom",
             fontsize=6.5)
    axa.text(xi + dx, f + 8.5, e5_verdict[t], ha="center", va="bottom",
             fontsize=5.8, fontweight="bold",
             color=colors[list(xa).index(xi)])
attrib = (
    "Insulin — R3+D1: edit dist. 0.82% < 2% (λ saturation)\n"
    "A1AT — R3: pool λ-gear separation insufficient\n"
    "GFP — D2: only λ{4,10} feasible gears"
)
axa.text(1.15, 99, attrib, fontsize=5.8, ha="left", va="top", linespacing=1.55,
         color=GREY)
axa.annotate("pre-B0: 0/315 → 12/315\n(species-matched codon table)",
             xy=(4.31, 2.5), xytext=(4.45, 42), fontsize=5.8, ha="right",
             va="bottom", linespacing=1.4,
             arrowprops=dict(arrowstyle="->", lw=0.6, color=GREY))
axa.set_xticks(xa)
axa.set_xticklabels(e5_targets, fontsize=7)
axa.set_xlim(-0.55, 4.55)
axa.set_ylim(0, 112)
axa.set_ylabel("constraint-passing pool\nfraction (%)", fontsize=7)
axa.set_title("E5 S1 diagnosis: pool pass fraction\nper target (315 candidates each)",
              pad=24)
axa.text(0.5, 1.075, "all residual failures are generation-layer structural",
         transform=axa.transAxes, ha="center", fontsize=6.5, color=RED)
strip_spines(axa)
axa.yaxis.grid(True, color="#EBEBEB", lw=0.6, zorder=0)
axa.set_axisbelow(True)
axa.text(-0.16, 1.14, "a", transform=axa.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")

# ---- Panel c: LLM calls per gene --------------------------------------------
axc = fig.add_subplot(gs[0, 1])
xc = np.arange(len(targets))
axc.axhspan(5, 9, color="#F0F0F0", zorder=0)
axc.text(17.3, 7.0, "pre-registered\nbudget 5–9 / gene", fontsize=5.8, color=GREY,
         ha="right", va="center", linespacing=1.3)
axc.bar(xc, llm, width=0.66, color=BLUE, zorder=3)
mean_llm = np.mean(llm)
axc.axhline(mean_llm, color=ORANGE, lw=0.9, ls="--", zorder=4)
axc.text(17.3, mean_llm + 0.22, "mean 2.4", fontsize=6, color=ORANGE, ha="right")
for xi, v in zip(xc, llm):
    axc.text(xi, v - 0.15, str(v), ha="center", va="top", fontsize=5.6,
             color="white", zorder=5)
axc.set_xticks(xc)
axc.set_xticklabels(targets, rotation=90, fontsize=5.4)
axc.set_ylim(0, 10.2)
axc.set_yticks([0, 2, 4, 6, 8])
axc.set_ylabel("LLM calls per gene (arm C)", fontsize=7)
axc.set_title("E6 S2 efficiency: 43 LLM calls / 18 genes", pad=4)
axc.text(0.02, 0.97, "LD lattice: 125 slot counts →\n61 new calls, 64 cache hits",
         transform=axc.transAxes, fontsize=5.8, color=GREY, va="top",
         linespacing=1.3)
strip_spines(axc)
axc.text(-0.11, 1.14, "c", transform=axc.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")

# ---- Panel b: E6 S2 JCD grid (bottom, spanning) ------------------------------
gsb = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[1, :])
axb = fig.add_subplot(gsb[0, 0])
grid = np.vstack([grid_a, grid_c])  # 6 rows x 18 targets
cmap = mcolors.ListedColormap([RED, GREEN])
axb.imshow(grid.astype(float), cmap=cmap, vmin=0, vmax=1, aspect="auto")
# HER2 column: declared-degrade marker (frame + dagger in the tick label)
axb.add_patch(plt.Rectangle((her2_i - 0.5, -0.5), 1, 6, fill=False, ec="black",
                            lw=1.1))
axb.axhline(2.5, color="white", lw=3.0)
axb.text(-1.7, 1.0, "arm A\nrule-based", fontsize=6, ha="right", va="center",
         linespacing=1.3)
axb.text(-1.7, 4.0, "arm C\ngated GenNav", fontsize=6, ha="right", va="center",
         linespacing=1.3)
axb.set_yticks(range(6))
axb.set_yticklabels(profiles + profiles, fontsize=6)
tick_labels = [t + " †" if i == her2_i else t for i, t in enumerate(targets)]
axb.set_xticks(range(len(targets)))
axb.set_xticklabels(tick_labels, rotation=90, fontsize=5.4)
axb.xaxis.set_ticks_position("bottom")
axb.tick_params(length=0)
strip_spines(axb, keep=())
axb.set_title("E6 S2 primary endpoint: per-profile joint-criteria delivery (JCD)",
              pad=16)
axb.text(0.5, 1.045,
         "McNemar P = 1.9×10$^{-9}$, discordant 30:0 (n = 54); "
         "gene-level e2e = 1.0",
         transform=axb.transAxes, ha="center", fontsize=7)
axb.legend(handles=[Patch(fc=GREEN, label="pass"), Patch(fc=RED, label="fail")],
           loc="upper right", bbox_to_anchor=(1.0, 1.115), frameon=False,
           fontsize=6, ncol=2, handlelength=1.1, borderaxespad=0.0,
           labelspacing=0.3, columnspacing=0.9)
axb.text(-0.042, 1.16, "b", transform=axb.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")
fig.text(0.985, 0.335,
         "† HER2: zero feasible λ gear → declared degrade; secondary endpoint "
         "not passed, disclosed",
         ha="right", va="bottom", fontsize=6, color=GREY)

# ---- Panel d: E8 aptamer transfer JCD grid (bottom, spanning) ----------------
gsd = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs[2, :])
axd = fig.add_subplot(gsd[0, 0])
grid8 = np.vstack([grid8_a, grid8_c])  # 6 rows x 10 targets
axd.imshow(grid8.astype(float), cmap=cmap, vmin=0, vmax=1, aspect="auto")
axd.axhline(2.5, color="white", lw=3.0)
axd.text(-1.25, 1.0, "arm A\nrule-based", fontsize=6, ha="right", va="center",
         linespacing=1.3)
axd.text(-1.25, 4.0, "arm C\ngated GenNav", fontsize=6, ha="right",
         va="center", linespacing=1.3)
axd.set_yticks(range(6))
axd.set_yticklabels(e8_profiles + e8_profiles, fontsize=6)
axd.set_xticks(range(len(e8_targets)))
axd.set_xticklabels(e8_targets, rotation=90, fontsize=5.4)
axd.set_xlim(-0.5, len(e8_targets) - 0.5 + 3.6)  # right margin: legend zone
axd.xaxis.set_ticks_position("bottom")
axd.tick_params(length=0)
strip_spines(axd, keep=())
for r, j, winner in e8_discordant:
    axd.add_patch(plt.Rectangle(
        (j - 0.5, r - 0.5), 1, 1, fill=False, lw=1.5,
        ec=BLUE if winner == "C" else ORANGE))
axd.set_title("E8 S2: GenNav on 10 aptamer targets — per-profile JCD", pad=17)
axd.text(0.36, 1.065,
         f"McNemar P = {mc['p']:.3f} NS, discordant {b8}:{c8} (n = 30) — "
         "primary endpoint NOT met",
         transform=axd.transAxes, ha="center", fontsize=6.8)
axd.text(0.36, 1.015,
         f"{n8_concordant_pass}/30 pairs concordant-pass (saturated); "
         f"C e2e {sum(e2e['C'])}/10 vs A {sum(e2e['A'])}/10; mean spend "
         f"{mean_c:.0f} vs {mean_a:.0f} candidates",
         transform=axd.transAxes, ha="center", fontsize=6.2, color=GREY)
axd.legend(handles=[
    Patch(fc=GREEN, label="pass"),
    Patch(fc=RED, label="fail"),
    Patch(fill=False, ec=BLUE, lw=1.5, label="C-only repair (3)"),
    Patch(fill=False, ec=ORANGE, lw=1.5, label="A-only — self-inflicted (1)"),
], loc="upper left", bbox_to_anchor=(0.755, 0.99), frameon=True,
    facecolor="white", framealpha=0.95, edgecolor="#CCCCCC", fontsize=6,
    ncol=1, handlelength=1.1, borderaxespad=0.0, labelspacing=0.4)
axd.text(-0.058, 1.20, "d", transform=axd.transAxes, fontsize=10,
         fontweight="bold", va="top", ha="left")

fig.savefig(OUTDIR / "fig5.png")
print("wrote", OUTDIR / "fig5.png")
