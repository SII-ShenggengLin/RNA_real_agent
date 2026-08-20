"""Fig 2b - CDS null model: CAI of designed vs wild-type vs random-synonymous."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = D.load_jsonl("fig2_cds_nulls.jsonl")
groups = {"random_syn": [], "wt": [], "cai_only": []}
for r in rows:
    if r.get("success") and r.get("cai_score") is not None:
        groups[r["arm"]].append(r["cai_score"])
order = ["random_syn", "wt", "cai_only"]
labels = [f"random\n(n={len(groups['random_syn'])})",
          f"wild type\n(n={len(groups['wt'])})",
          f"designed\n(n={len(groups['cai_only'])})"]
colors = [S.MORANDI["grey"], S.MORANDI["green"], S.MORANDI["blue"]]
med = [float(np.median(groups[k])) for k in order]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.96, top=0.88, bottom=0.20)
S.boxplot_morandi(ax, [groups[k] for k in order], positions=[0, 1, 2],
                  colors=colors)
for x, m in enumerate(med):
    ax.text(x + 0.30, m, f"{m:.3f}", fontsize=5.2, color=S.INK, va="center")
ax.set_xticks([0, 1, 2])
ax.set_xticklabels(labels, fontsize=5.2)
ax.set_ylabel("Codon adaptation index")
ax.set_title("Designed CDSs lift CAI over wild type", fontsize=6.2, loc="left", pad=5.0)
ax.set_ylim(0.60, 0.86)
S.sig_bracket(ax, 0, 1, 0.815, f"MW {S.p_str(4.02e-7)}, \u03b4 = 0.69", text_size=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
