"""Fig 2g - Small-molecule oracle: in-distribution power vs OOD boundary."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rn = D.rnasmol_boundary()
rows = [
    ("robin test", rn["robin_test"]["auroc"], rn["robin_test"]["auroc_ci95"], True),
    ("pdb test", rn["pdb_test"]["auroc"], rn["pdb_test"]["auroc_ci95"], True),
    ("OOD: vs random-chem", rn["ood_aptamer"]["auroc_vs_random_chem"],
     rn["ood_aptamer"]["auroc_vs_random_chem_ci95"], False),
    ("OOD: vs near-cognate", rn["ood_aptamer"]["auroc_vs_near_cognate"],
     rn["ood_aptamer"]["auroc_vs_near_cognate_ci95"], False),
]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.33, right=0.985, top=0.85, bottom=0.18)
ys = list(range(len(rows)))[::-1]
for y, (lab, a, ci, in_dist) in zip(ys, rows):
    col = S.MORANDI["green"] if in_dist else S.MORANDI["terra"]
    ax.plot(ci, [y, y], color=col, lw=2.2, solid_capstyle="round")
    ax.scatter([a], [y], s=10, color=col, zorder=3)
    ax.text(1.06, y, f"{a:.2f} [{ci[0]:.2f},{ci[1]:.2f}]", fontsize=4.6,
            va="center", color=S.INK)
ax.axvline(0.5, color=S.MORANDI["grey"], lw=0.6, ls=(0, (3, 2)))
ax.text(0.5, len(rows) - 0.35, "chance", fontsize=5.2, color=S.MORANDI["grey_dk"],
        ha="center")
ax.axvline(0.8, color=S.MORANDI["green"], lw=0.6, ls=(0, (3, 2)))
ax.text(0.8, -0.62, "gate 0.8", fontsize=5.2, color=S.MORANDI["sage"], ha="center")
ax.axvline(1.0, color=S.GRID, lw=0.5)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=4.8)
ax.set_xlim(0.0, 1.58)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xlabel("AUROC")
ax.set_title("Deployed-artifact boundary, two-sided", fontsize=6.2, loc="left", pad=5.0)
S.style_cat_ax(ax)
ax.spines["left"].set_visible(False)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "g"))
