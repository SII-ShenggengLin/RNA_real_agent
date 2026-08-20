"""Fig 5d - mRNA delivery map: 18 targets x 3 profiles, pair outcomes."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S
import data as D

W, H = 55, 42

PROFILES = ["expression", "balanced", "stability"]


def jcd(p):
    return bool(p.get("e2e_pass") and p.get("D1") and p.get("D2") and p.get("R3"))


runs = D.e6_s2_runs()
targets = [r["target_id"] for r in runs]
grid = np.zeros((len(targets), 3), dtype=int)  # 0 none, 1 both, 2 C-only, 3 A-only
for i, r in enumerate(runs):
    eva = {p["profile"]: jcd(p) for p in r["evaluations"]["A"]["profiles"]}
    evc = {p["profile"]: jcd(p) for p in r["evaluations"]["C"]["profiles"]}
    for j, prof in enumerate(PROFILES):
        a, c = eva.get(prof, False), evc.get(prof, False)
        grid[i, j] = 1 if (a and c) else 2 if (c and not a) else 3 if (a and not c) else 0

COL = {0: S.MORANDI["grey"], 1: S.MORANDI["green"], 2: S.MORANDI["blue"],
       3: S.MORANDI["terra"]}

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.24, right=0.98, top=0.84, bottom=0.13)
for i in range(len(targets)):
    for j in range(3):
        ax.add_patch(Rectangle((j, len(targets) - 1 - i), 0.92, 0.92,
                               fc=COL[int(grid[i, j])], ec="white", lw=0.5))
ax.set_xlim(-0.05, 3.0)
ax.set_ylim(-0.6, len(targets))
ax.set_xticks([0.46, 1.46, 2.46])
ax.set_xticklabels(["expr.", "bal.", "stab."], fontsize=5.0)
ax.set_yticks([len(targets) - 1 - i + 0.46 for i in range(len(targets))])
ax.set_yticklabels([t.replace("SARS-CoV-2_Spike_WT", "Spike").replace("_", " ")
                    for t in targets], fontsize=4.0)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
counts = {k: int((grid == k).sum()) for k in (0, 1, 2, 3)}
handles = [Rectangle((0, 0), 1, 1, fc=COL[k]) for k in (2, 1, 3, 0)]
ax.legend(handles, [f"navigation only ({counts[2]})", f"both ({counts[1]})",
                    f"rule only ({counts[3]})", f"neither ({counts[0]})"],
          loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=4.4,
          frameon=False, handlelength=1.0, handletextpad=0.4, columnspacing=0.8)
ax.set_title("mRNA: per-profile joint delivery (18 targets)", fontsize=6.2,
             loc="left", pad=5.0)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
