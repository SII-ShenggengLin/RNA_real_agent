"""Fig 1f - RNADesign-210 composition: tasks per workflow + anchors and nulls."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 181, 34

cov = D.fig2_summary()["coverage"]
items = sorted(cov.items(), key=lambda kv: -kv[1]["n_tasks"])
SHORT = {"mrna_cds_design": "CDS design", "full_length_mrna_design": "full-length mRNA",
         "mrna_sequence_scoring": "seq scoring", "sirna_design": "siRNA",
         "sgrna_design": "sgRNA", "aso_target_screening": "ASO screen",
         "ires_prediction": "IRES", "rna_aptamer_design": "aptamer",
         "rna_secondary_structure_design": "secondary struct.",
         "rna_tertiary_structure_design": "tertiary struct.",
         "rna_small_molecule_interaction": "small molecule"}
names = [SHORT.get(k, k) for k, _ in items]
vals = [v["n_tasks"] for _, v in items]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.13, right=0.985, top=0.80, bottom=0.30)
xs = range(len(items))
ax.bar(list(xs), vals, width=0.6, color=S.MORANDI["blue"])
for x, v in zip(xs, vals):
    ax.text(x, v + 0.8, str(v), ha="center", fontsize=5.2, color=S.INK)
ax.set_xticks(list(xs))
ax.set_xticklabels(names, fontsize=5.0)
ax.set_ylabel("Tasks")
ax.set_ylim(0, max(vals) * 1.22)
ax.set_title("RNADesign-210: 210 tasks across 11 workflows - with designed null models "
             "(WT vs random-synonymous) and literature anchors (vaccine mRNAs, known aptamers, "
             "IRES panels, measured MRL)", fontsize=6.0, loc="left", pad=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
