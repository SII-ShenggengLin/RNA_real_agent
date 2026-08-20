"""Fig 2a - RNADesign-210 task success by workflow (210/210)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

cov = D.fig2_summary()["coverage"]
items = sorted(cov.items(), key=lambda kv: kv[1]["n_tasks"])
SHORT = {"mrna_cds_design": "CDS design", "full_length_mrna_design": "full-length mRNA",
         "mrna_sequence_scoring": "seq scoring", "sirna_design": "siRNA",
         "sgrna_design": "sgRNA", "aso_target_screening": "ASO screen",
         "ires_prediction": "IRES", "rna_aptamer_design": "aptamer",
         "rna_secondary_structure_design": "secondary struct.",
         "rna_tertiary_structure_design": "tertiary struct.",
         "rna_small_molecule_interaction": "small molecule"}
names = [SHORT.get(k, k) for k, _ in items]
n_ok = [v["n_success"] for _, v in items]
n_all = [v["n_tasks"] for _, v in items]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.34, right=0.97, top=0.90, bottom=0.16)
y = range(len(items))
ax.barh(list(y), n_all, height=0.62, color=S.MORANDI["blue"], alpha=0.85,
        edgecolor="none")
for yi, (ok, all_) in enumerate(zip(n_ok, n_all)):
    ax.text(all_ + max(n_all) * 0.015, yi, f"{ok}/{all_}", va="center",
            ha="left", fontsize=5.2, color=S.INK)
ax.set_yticks(list(y))
ax.set_yticklabels(names, fontsize=5.2)
ax.set_xlabel("Tasks (all succeeded)", fontsize=S.mpl.rcParams["axes.labelsize"])
ax.set_xlim(0, max(n_all) * 1.30)
ax.set_title("RNADesign-210: 210/210 tasks succeed", fontsize=6.2, loc="left", pad=5.0,
             color=S.INK)
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
