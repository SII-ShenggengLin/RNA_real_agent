"""Fig 3h - Deployed-artifact fidelity: silent preprocessing fault found by profiling."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rn = D.rnasmol_boundary()
# Pre-fix service AUROCs documented in PAPER_FACT_SHEET section 2 (fig2d addendum):
# v0.2.0 service (uppercased vocab) 0.7864 / 0.4103; official pipeline and the
# v0.3.0 faithful service both 0.9744 / 0.9828.
rows = [("robin test\n(n = 1,492)", 0.7864, rn["robin_test"]["auroc"]),
        ("pdb test\n(n = 170)", 0.4103, rn["pdb_test"]["auroc"])]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.24, right=0.96, top=0.86, bottom=0.19)
ys = [1, 0]
for y, (lab, pre, post) in zip(ys, rows):
    ax.plot([pre, post], [y, y], color=S.GRID, lw=1.2, zorder=2)
    ax.scatter([pre], [y], s=12, color=S.MORANDI["terra"], zorder=3)
    ax.scatter([post], [y], s=12, color=S.MORANDI["green"], zorder=3)
    ax.text(pre - 0.015, y, f"{pre:.2f}", fontsize=5.2, ha="right", color=S.INK)
    ax.text(post + 0.015, y, f"{post:.2f}", fontsize=5.2, ha="left", color=S.INK)
ax.axvline(0.8, color=S.MORANDI["sage"], lw=0.6, ls=(0, (4, 2)))
ax.set_ylim(-0.42, 1.58)
ax.text(0.8, 1.47, "gate 0.8", fontsize=5.0, color=S.MORANDI["sage"], ha="center")
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=5.0)
ax.set_xlim(0.30, 1.10)
ax.set_xticks([0.4, 0.6, 0.8, 1.0])
ax.set_xlabel("AUROC on RNAsmol's own held-out test splits")
ax.set_title("Profile the deployed artifact, not the paper", fontsize=6.2,
             loc="left", pad=5.0)
ax.scatter([], [], s=12, color=S.MORANDI["terra"], label="deployed v0.2.0 (silent fault)")
ax.scatter([], [], s=12, color=S.MORANDI["green"], label="deployed v0.3.0 = official")
ax.legend(loc="lower right", fontsize=4.8)
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "h"))
