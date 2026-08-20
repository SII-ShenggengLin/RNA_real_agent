"""Fig 3b - Screening power: AUROC heatmap, 3 oracles x 6 targets (0/18 pass)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

e1 = D.e1_capability()
cells = e1["part_a_per_oracle_target"]
oracles = ["egarps_native_probability", "proteinx_ipTM", "rhofold_mean_plddt"]
targets = e1["targets"]
short_o = ["EGARPS np", "Protenix ipTM", "RhoFold pLDDT"]
short_t = [t.replace("SARS-CoV-2 N", "SARS-N").replace("Angiopoietin-2", "Ang-2")
           for t in targets]

M = np.zeros((len(oracles), len(targets)))
for i, o in enumerate(oracles):
    for j, t in enumerate(targets):
        M[i, j] = cells[f"{o} | {t}"]["screening_auroc"]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.245, right=0.865, top=0.84, bottom=0.17)
im = ax.imshow(M, cmap=S.SEQ_CMAP, vmin=0.3, vmax=0.9, aspect="auto")
for i in range(len(oracles)):
    for j in range(len(targets)):
        ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=4.6,
                color="white" if M[i, j] > 0.72 else S.INK)
ax.set_xticks(range(len(targets)))
ax.set_xticklabels(short_t, rotation=38, ha="right", fontsize=4.6)
ax.set_yticks(range(len(oracles)))
ax.set_yticklabels(short_o, fontsize=4.8)
ax.set_title("Screening power: 0/18 cells pass (gate AUROC > 0.8)", fontsize=6.2,
             loc="left", pad=5.0)
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.01)
cb.ax.tick_params(labelsize=4.6)
cb.outline.set_linewidth(0.4)
for sp in ax.spines.values():
    sp.set_visible(False)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
