"""Fig 3d - Docking power: native-pose rank across five complexes (0/5)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

e1 = D.e1_capability()
dock = e1["part_b_docking"]
names = {"tba_thrombin": ("TBA\n(thrombin)", "4DII"),
         "toggle25t_thrombin": ("Toggle-25t\n(thrombin)", "3DD2"),
         "t1p1_hiv1rt": ("t1p1\n(HIV-1 RT)", "1HVU"),
         "dtri177_fixa": ("DTri177\n(FIXa)", "8EPK"),
         "hd22_t27_thrombin": ("HD22-T27\n(thrombin)", "4I7Y")}
cases = list(dock.items())
n = len(cases)
ranks = np.array([c["native_rank"] / c["n_poses_scored"] for _, c in cases],
                 dtype=float)
abs_rank = [c["native_rank"] for _, c in cases]
abs_tot = [c["n_poses_scored"] for _, c in cases]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.97, top=0.84, bottom=0.24)
x = np.arange(n)
ax.axhspan(0, 1 / 3, color=S.MORANDI["green"], alpha=0.15, lw=0)
ax.axhline(1 / 3, color=S.MORANDI["sage"], lw=0.6, ls=(0, (4, 2)))
ax.text(n - 0.5, 0.30, "gate: top 1/3", fontsize=4.8,
        color=S.MORANDI["sage"], ha="right")
ax.vlines(x, 0, ranks, color=S.MORANDI["terra"], lw=1.6)
ax.scatter(x, ranks, s=14, color=S.MORANDI["terra"], zorder=3)
for xi, (ar, at) in enumerate(zip(abs_rank, abs_tot)):
    ax.text(xi + 0.10, ranks[xi] - 0.005, f"{ar}/{at}", fontsize=4.6, va="top",
            color=S.INK)
ax.set_xticks(x)
ax.set_xticklabels([f"{names[k][0]}\n{names[k][1]}" for k, _ in cases],
                   fontsize=4.6)
ax.set_ylabel("Native-pose rank (fraction of decoys)")
ax.set_ylim(0, 1.12)
ax.set_xlim(-0.55, n - 0.30)
ax.set_yticks([0, 1 / 3, 2 / 3, 1])
ax.set_yticklabels(["0", "1/3", "2/3", "1"])
ax.set_title("Docking: native pose never top-1 (0/5 complexes)", fontsize=6.2,
             loc="left", pad=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
