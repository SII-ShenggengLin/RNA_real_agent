"""Fig 4e - E3-M: mRNA-side audit set, per-task-family verdicts (paired)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

d = D.load_json("e3_mrna_runs_full_adjudicated_summary.json")
ung = d["ungated"]["per_task_verdict"]
gat = d["gated"]["per_task_verdict"]
tasks = list(ung.keys())
FAM_COL = {"TP": S.MORANDI["blue"], "FP": S.MORANDI["terra"],
           "suppressed": S.MORANDI["grey"], "neutral": S.MORANDI["sand"]}
fam = lambda t: t.split("_")[0] if not t.startswith("cds") else "cds"

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.34, right=0.97, top=0.84, bottom=0.17)
ys = range(len(tasks))
for y, t in zip(ys, tasks):
    ax.scatter(-0.22, y, s=16, color=FAM_COL[ung[t]], zorder=3, clip_on=False)
    ax.scatter(0.22, y, s=16, color=FAM_COL[gat[t]], zorder=3, clip_on=False)
    ax.plot([-0.22, 0.22], [y, y], color=S.GRID, lw=0.6, zorder=1)
SHORTT = {"cds_cai_report": "CAI report", "cds_mfe_report": "CDS MFE",
          "cds_constraint_report": "constraints", "cds_relative_compare": "rel. compare",
          "utr3_stability_rank": "3'UTR rank", "cross_family_expression": "cross-fam.",
          "junction_quality": "junction", "mrl_optimum": "MRL optim."}
import re as _re
labels = [SHORTT.get(_re.sub(r"_\d+$", "", t.split("::")[0]),
                     _re.sub(r"_\d+$", "", t.split("::")[0])) for t in tasks]
ax.set_yticks(list(ys))
ax.set_yticklabels(labels, fontsize=4.4)
ax.set_xticks([-0.22, 0.22])
ax.set_xticklabels(["ungated", "gated"], fontsize=5.4)
ax.set_xlim(-0.5, 0.5)
ax.set_ylim(-0.8, len(tasks) - 0.2)
ax.axvline(0, color=S.GRID, lw=0.5)
ax.set_title("mRNA audit set: FP 38.9% \u2192 8.3%, TP 11/11", fontsize=6.0,
             loc="left", pad=5.0)
handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=3.5)
           for c in FAM_COL.values()]
ax.legend(handles, ["true positive", "false positive", "suppressed", "neutral"],
          loc="center right", fontsize=4.4, handletextpad=0.1, borderpad=0.2,
          bbox_to_anchor=(1.02, 0.5))
S.despine(ax, left=False)
ax.spines["left"].set_visible(False)
ax.tick_params(length=0)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
