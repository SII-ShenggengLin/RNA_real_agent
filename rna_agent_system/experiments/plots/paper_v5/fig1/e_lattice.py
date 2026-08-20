"""Fig 1e - Gear-lattice mini-visualization (probe -> feasible gears -> delivery)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

W, H = 55, 46

# 17-length densified aptamer lattice with three delivery bands
lattice = [25, 28, 31, 34, 40, 43, 46, 49, 52, 55, 61, 64, 67, 70, 73, 76, 80]
bands = {"compact\n25-34": (25, 34, S.MORANDI["blue"]),
         "standard\n40-55": (40, 55, S.MORANDI["green"]),
         "extended\n61-80": (61, 80, S.MORANDI["lavender"])}
feasible = {25, 28, 34, 40, 43, 49, 55, 61, 67, 70, 76}

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.10, right=0.97, top=0.74, bottom=0.19)
for i, L in enumerate(lattice):
    in_band = None
    for name, (lo, hi, col) in bands.items():
        if lo <= L <= hi:
            in_band = col
    fc = in_band if L in feasible else "#EDEAE2"
    ax.add_patch(Rectangle((i - 0.38, 0), 0.76, 1.0, fc=fc, ec="white", lw=0.5))
ax.set_xlim(-0.8, len(lattice) - 0.2)
ax.set_ylim(-0.25, 1.55)
ax.set_yticks([])
ax.set_xticks(range(len(lattice)))
ax.set_xticklabels([str(L) for L in lattice], fontsize=4.2)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
handles = [Rectangle((0, 0), 1, 1, fc=c) for _, (_, _, c) in bands.items()]
handles.append(Rectangle((0, 0), 1, 1, fc="#EDEAE2"))
ax.legend(handles, [k.replace("\n", " ") for k in bands] + ["probe: infeasible"],
          loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=4.4,
          frameon=False, handlelength=1.0, handletextpad=0.4, columnspacing=0.8)
ax.set_title("The generator's gear lattice (17 lengths)", fontsize=6.2, loc="left",
             pad=5.0)
ax.text(0.0, 1.28, "probe at depth 2 \u2192 feasible gears \u2192 guarantee-round allocation",
        transform=ax.transAxes, fontsize=4.4, color=S.INK_SOFT)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
