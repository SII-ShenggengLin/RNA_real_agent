"""Fig 2c - Folding-energy control: MFE/nt of wild type vs random-synonymous."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = D.load_jsonl("fig2_cds_nulls.jsonl")
groups = {"random_syn": [], "wt": []}
for r in rows:
    if r.get("success") and r.get("mfe_per_nt") is not None and r["arm"] in groups:
        groups[r["arm"]].append(r["mfe_per_nt"])
labels = [f"random\n(n={len(groups['random_syn'])})",
          f"wild type\n(n={len(groups['wt'])})"]
colors = [S.MORANDI["grey"], S.MORANDI["green"]]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.17, right=0.96, top=0.88, bottom=0.20)
S.boxplot_morandi(ax, [groups["random_syn"], groups["wt"]], positions=[0, 1],
                  colors=colors)
med = [float(np.median(groups[k])) for k in ("random_syn", "wt")]
for x, m in enumerate(med):
    ax.text(x + 0.24, m, f"{m:.3f}", fontsize=5.2, color=S.INK, va="center")
ax.set_xticks([0, 1])
ax.set_xticklabels(labels, fontsize=5.2)
ax.set_ylabel("MFE per nt (kcal/mol/nt)")
ax.set_title("Folding energy: no WT-random difference", fontsize=6.2, loc="left", pad=5.0)
S.sig_bracket(ax, 0, 1, -0.028, "MW P = 0.23, NS", text_size=5.0)
ax.set_ylim(-0.105, -0.018)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
