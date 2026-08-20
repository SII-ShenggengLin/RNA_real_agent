# -*- coding: utf-8 -*-
"""Regenerate fig5 panel b (E6 JCD grid) and panel e (E14 JCD grid) as
standalone PPT-ready figures with larger fonts. Data loading replicates
experiments/plots/plot_paper_fig5.py exactly (same sources, same assertions).
"""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib import colors as mcolors

ROOT = Path("/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent")
RESULTS = ROOT / "rna_agent_system/experiments/results"
OUT = ROOT / "PPT/ppt_build_2608/crops"

plt.rcParams.update({
    "font.family": ["DejaVu Sans", "Noto Sans CJK JP"],
    "savefig.dpi": 300,
    "figure.dpi": 300,
})
BLUE, ORANGE, GREEN, RED, GREY = "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#666666"

# ------------------------------------------------------------ E6 data ----
runs = [json.loads(l) for l in open(RESULTS / "e6_s2_runs.jsonl")]
verdict = json.load(open(RESULTS / "e6_s2_verdict_aggregated.json"))
profiles = ["expression", "stability", "balanced"]
targets, grid_a, grid_c = [], [], []
for r in runs:
    targets.append(r["target_id"])
    ja, jc = {}, {}
    for p in r["evaluations"]["A"]["profiles"]:
        ja[p["profile"]] = bool(p["e2e_pass"] and p["D1"] and p["D2"] and p["R3"])
    for p in r["evaluations"]["C"]["profiles"]:
        jc[p["profile"]] = bool(p["e2e_pass"] and p["D1"] and p["D2"] and p["R3"])
    grid_a.append([ja[p] for p in profiles])
    grid_c.append([jc[p] for p in profiles])
grid_a = np.array(grid_a).T
grid_c = np.array(grid_c).T
b_disc = int(np.sum((~grid_a) & grid_c))
c_disc = int(np.sum(grid_a & (~grid_c)))
assert (b_disc, c_disc) == (30, 0)
her2_i = targets.index("HER2")

# ------------------------------------------------------------ E14 data ----
e14v = json.load(open(RESULTS / "e14_verdict_s2.json"))
e14_profiles = ["compact", "standard", "extended"]
e14_targets = e14v["targets"]
e14_pairs = {(p["target_id"], p["profile"]): (p["A_jcd"], p["C_jcd"])
             for p in e14v["pairs"]}
grid14_a = np.array([[e14_pairs[(t, p)][0] for t in e14_targets]
                     for p in e14_profiles])
grid14_c = np.array([[e14_pairs[(t, p)][1] for t in e14_targets]
                     for p in e14_profiles])
b14 = int(np.sum((~grid14_a) & grid14_c))
c14 = int(np.sum(grid14_a & (~grid14_c)))
mc14 = e14v["primary"]["mcnemar"]
assert (b14, c14) == (mc14["b"], mc14["c"]) == (14, 3)
e14_discordant = []
for j, t in enumerate(e14_targets):
    for i, p in enumerate(e14_profiles):
        a_ok, c_ok = e14_pairs[(t, p)]
        if a_ok != c_ok:
            winner = "C" if c_ok else "A"
            e14_discordant += [(i, j, winner), (3 + i, j, winner)]
n14_c = int(np.sum(grid14_a & grid14_c)) + b14
n14_a = int(np.sum(grid14_a & grid14_c)) + c14
assert (n14_c, n14_a) == (26, 15)

cmap = mcolors.ListedColormap([RED, GREEN])


def draw_grid(grid, row_labels, col_labels, arm_labels, discordant,
              title_lines, legend_handles, figsize, out_name,
              her2_col=None):
    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(grid.astype(float), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    n_rows = grid.shape[0]
    ax.axhline(n_rows / 2 - 0.5, color="white", lw=4.0)
    n_cols = grid.shape[1]
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(row_labels, fontsize=13)
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, rotation=90, fontsize=11.5)
    ax.xaxis.set_ticks_position("bottom")
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    # arm labels on the left, well clear of the row tick labels
    ax.text(-3.1, n_rows / 4 - 0.5, arm_labels[0], fontsize=13, ha="right",
            va="center", linespacing=1.4, fontweight="bold")
    ax.text(-3.1, 3 * n_rows / 4 - 0.5, arm_labels[1], fontsize=13, ha="right",
            va="center", linespacing=1.4, fontweight="bold")
    if her2_col is not None:
        ax.add_patch(plt.Rectangle((her2_col - 0.5, -0.5), 1, n_rows,
                                   fill=False, ec="black", lw=1.6))
    for r, j, winner in discordant or []:
        ax.add_patch(plt.Rectangle((j - 0.5, r - 0.5), 1, 1, fill=False,
                                   lw=2.2, ec=BLUE if winner == "C" else ORANGE))
    ax.set_title(title_lines[0], fontsize=15, pad=56, loc="center")
    ax.text(0.5, 1.095, title_lines[1], transform=ax.transAxes, ha="center",
            fontsize=13, fontweight="bold")
    if len(title_lines) > 2:
        ax.text(0.5, 1.028, title_lines[2], transform=ax.transAxes,
                ha="center", fontsize=11.5, color=GREY)
    ax.legend(handles=legend_handles, loc="upper left",
              bbox_to_anchor=(1.005, 1.02), frameon=False, fontsize=12,
              ncol=1, handlelength=1.2, borderaxespad=0.0, labelspacing=0.5)
    fig.savefig(out_name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", out_name)


# ---- E6 grid ----
tick_labels = [t + " †" if i == her2_i else t for i, t in enumerate(targets)]
draw_grid(
    np.vstack([grid_a, grid_c]), profiles + profiles, tick_labels,
    ["arm A\n规则基线", "arm C\nGenNav"],
    None,
    ["E6 主终点:逐画像联合判据交付 (JCD)",
     "McNemar P = 1.9×10⁻⁹,discordant 30:0 (n = 54);基因级 e2e = 1.0",
     "† HER2:零可行 λ 档 → 显式声明降级;次终点未过,如实披露"],
    [Patch(fc=GREEN, label="pass"), Patch(fc=RED, label="fail")],
    (11.5, 3.2), OUT / "ppt_e6_grid.png", her2_col=her2_i,
)

# ---- E14 grid ----
short14 = [t.replace("SARS-CoV-2_Nucleocapsid", "SARS-CoV-2 N")
           for t in e14_targets]
draw_grid(
    np.vstack([grid14_a, grid14_c]), e14_profiles + e14_profiles, short14,
    ["arm A\n规则基线", "arm C\nGenNav"],
    e14_discordant,
    ["E14 主终点 GO:12 个适配体靶点 × 3 长度带",
     f"McNemar P = {mc14['p']:.4f},discordant {b14}:{c14} (n = 36),两臂同 48-raw 预算",
     f"C 交付 {n14_c}/36 格 vs A {n14_a}/36 格;C e2e 6/12 vs A 0/12;全程仅 1 次 LLM 调用"],
    [Patch(fc=GREEN, label="pass"), Patch(fc=RED, label="fail"),
     Patch(fill=False, ec=BLUE, lw=2.2, label="C-only win (14)"),
     Patch(fill=False, ec=ORANGE, lw=2.2, label="A-only win (3)")],
    (11.5, 3.4), OUT / "ppt_e14_grid.png",
)
