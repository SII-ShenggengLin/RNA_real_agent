"""Fig 2h - End-to-end runtime by workflow (log scale)."""
import sys, pathlib
from collections import defaultdict
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

by_wf = defaultdict(list)
for r in D.fig2_runtime_rows():
    by_wf[r["workflow"]].append(r["elapsed_seconds"])
for r in D.pa_regression_rows():
    by_wf[r["workflow"]].append(r["duration_s"])

order = sorted(by_wf.items(), key=lambda kv: np.median(kv[1]))
SHORT = {"mrna_cds_design": "CDS design", "full_length_mrna_design": "full-length mRNA",
         "mrna_sequence_scoring": "seq scoring", "sirna_design": "siRNA",
         "sgrna_design": "sgRNA", "aso_target_screening": "ASO screen",
         "ires_prediction": "IRES", "rna_aptamer_design": "aptamer",
         "rna_secondary_structure_design": "secondary struct.",
         "rna_tertiary_structure_design": "tertiary struct.",
         "rna_small_molecule_interaction": "small molecule"}
names = [SHORT.get(k, k) for k, _ in order]
vals = [np.array(v) / 60.0 for _, v in order]  # minutes

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.36, right=0.96, top=0.85, bottom=0.30)
rng = np.random.default_rng(3)
for i, v in enumerate(vals):
    jitter = rng.uniform(-0.16, 0.16, size=len(v))
    ax.scatter(np.full(len(v), i) + jitter, v, s=2.4, color=S.MORANDI["blue"],
               alpha=0.55, edgecolors="none", zorder=3)
    ax.hlines(np.median(v), i - 0.28, i + 0.28, color=S.INK, lw=1.1, zorder=4)
ax.set_yscale("log")
ax.set_yticks([0.02, 0.1, 1, 10, 60, 180])
ax.set_yticklabels(["1 s", "6 s", "1 min", "10 min", "1 h", "3 h"])
ax.set_xticks(range(len(names)))
ax.set_xticklabels(names, rotation=45, ha="right", fontsize=4.4)
ax.set_ylabel("Wall-clock per task")
ax.set_title("Campaign runtime, 11 workflows", fontsize=6.2, loc="left", pad=5.0)
ax.grid(axis="y", color=S.GRID, lw=0.4)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "h"))
