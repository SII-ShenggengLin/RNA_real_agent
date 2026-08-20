"""Fig 6d - Cross-campaign memory does not pay (E4, 120 campaigns)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

e4 = D.e4_memory()
eff = e4["endpoints"]["efficiency"]
sav = eff["cumulative_budget_saving"]
slopes = eff["slopes_by_group"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.35], left=0.15, right=0.97,
                      top=0.82, bottom=0.19, wspace=0.75)

ax1 = fig.add_subplot(gs[0])
ax1.bar(["no memory", "memory"], [sav["nomem_total"], sav["memory_total"]],
        width=0.55, color=[S.MORANDI["grey"], S.MORANDI["lavender"]])
for i, v in enumerate([sav["nomem_total"], sav["memory_total"]]):
    ax1.text(i, v + 60, f"{int(v):,}", ha="center", fontsize=5.2, color=S.INK)
ax1.set_ylabel("Total evaluations")
ax1.set_ylim(0, sav["nomem_total"] * 1.18)
ax1.set_title(f"budget \u2212{sav['saving_fraction'] * 100:.0f}%", fontsize=5.8,
              loc="left", pad=5.0)
S.despine(ax1)

ax2 = fig.add_subplot(gs[1])
groups = sorted(slopes)
xs = range(len(groups))
mem = [slopes[g]["memory"]["slope"] * 1000 for g in groups]
nom = [slopes[g]["nomem"]["slope"] * 1000 for g in groups]
ax2.scatter([x - 0.14 for x in xs], nom, s=14, color=S.MORANDI["grey"],
            zorder=3, label="no memory")
ax2.scatter([x + 0.14 for x in xs], mem, s=14, color=S.MORANDI["lavender"],
            zorder=3, label="memory")
for x, m, n in zip(xs, mem, nom):
    ax2.plot([x - 0.14, x + 0.14], [n, m], color=S.GRID, lw=0.6, zorder=1)
ax2.axhline(0, color=S.INK_SOFT, lw=0.5)
ax2.set_xticks(list(xs))
ax2.set_xticklabels([f"grp {g}" for g in groups], fontsize=4.8)
ax2.set_ylabel("Learning slope (evals/campaign \u00d7 10$^{-3}$)")
ax2.set_title("no learning curve (t P = 0.91)", fontsize=5.8, loc="left",
              pad=5.0)
ax2.legend(fontsize=4.6, loc="upper right")
S.despine(ax2)
fig.suptitle("Memory cuts budget but buys no quality", fontsize=6.2, x=0.15,
             ha="left", y=0.97)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
