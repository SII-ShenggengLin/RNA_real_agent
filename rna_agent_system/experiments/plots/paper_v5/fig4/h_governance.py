"""Fig 4h - Governance: quality review is advisory (19/19 both arms)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = D.quality_ablation_rows()
tasks = sorted({r["task_id"] for r in rows})
on = {r["task_id"]: r for r in rows if r["arm"] == "quality_on"}
off = {r["task_id"]: r for r in rows if r["arm"] == "quality_off"}
succ_on = [1 if on[t].get("final_success") else 0 for t in tasks]
succ_off = [1 if off[t].get("final_success") else 0 for t in tasks]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.30, right=0.96, top=0.84, bottom=0.20)
ys = range(len(tasks))
for y, a, b in zip(ys, succ_on, succ_off):
    ax.plot([0.28, 0.72], [y, y], color=S.GRID, lw=0.6)
    ax.scatter([0.28], [y], s=14, color=S.MORANDI["blue"] if a else S.MORANDI["terra"],
               zorder=3, clip_on=False)
    ax.scatter([0.72], [y], s=14, color=S.MORANDI["blue"] if b else S.MORANDI["terra"],
               zorder=3, clip_on=False)
labels = [t.replace("_", " ")[:18] for t in tasks]
ax.set_yticks(list(ys))
ax.set_yticklabels(labels, fontsize=4.2)
ax.set_xticks([0.28, 0.72])
ax.set_xticklabels(["review on", "review off"], fontsize=5.4)
ax.set_xlim(0, 1)
ax.set_ylim(-0.8, len(tasks) - 0.2)
ax.set_title("QualityAgent advisory: 19/19 vs 19/19", fontsize=6.2, loc="left",
             pad=5.0)
ax.text(0.99, len(tasks) / 2, "success\nall green", fontsize=4.8, ha="right",
        va="center", color=S.MORANDI["sage"], style="italic",
        transform=ax.get_yaxis_transform())
S.despine(ax, left=False)
ax.spines["left"].set_visible(False)
ax.tick_params(length=0)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "h"))
