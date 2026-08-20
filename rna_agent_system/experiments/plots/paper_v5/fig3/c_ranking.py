"""Fig 3c - Ranking power: per-cell Spearman rho vs the 0.6 gate."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

e1 = D.e1_capability()
cells = e1["part_a_per_oracle_target"]
oracles = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
short_o = ["EGARPS np", "ipTM", "pLDDT"]
targets = e1["targets"]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.20, right=0.97, top=0.84, bottom=0.17)
rng = np.random.default_rng(11)
best = ("", -1)
for i, o in enumerate(oracles):
    rhos = [cells[f"{o} | {t}"]["ranking_spearman_rho"] for t in targets]
    x = np.full(len(rhos), i) + rng.uniform(-0.16, 0.16, len(rhos))
    ax.scatter(x, rhos, s=8, color=S.MORANDI["blue"], alpha=0.85, zorder=3)
    m = float(np.max(rhos))
    if m > best[1]:
        best = (f"{short_o[i]} × {targets[int(np.argmax(rhos))]}", m)
ax.axhline(0.6, color=S.MORANDI["sage"], lw=0.7, ls=(0, (4, 2)))
ax.text(-0.42, 0.615, "gate ρ ≥ 0.6", fontsize=5.0, color=S.MORANDI["sage"],
        ha="left")
ax.axhline(0, color=S.GRID, lw=0.5)
ax.set_xticks(range(3))
ax.set_xticklabels(short_o, fontsize=5.2)
ax.set_ylabel("Spearman ρ vs measured K$_d$")
ax.set_ylim(-0.45, 0.85)
ax.set_title("Ranking power: no cell reaches the gate", fontsize=6.2, loc="left",
             pad=5.0)
ax.annotate(f"best ρ = {best[1]:.2f}", xy=(2.05, best[1]),
            xytext=(1.02, 0.74), fontsize=5.0, color=S.INK,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
