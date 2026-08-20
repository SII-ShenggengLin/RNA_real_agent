"""Fig 6g - Escape routes closed by simulation (E11): symmetric budget cannot win."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S

W, H = 55, 42

# E11 feasibility simulation over the real E10 S2 cache (PAPER_FACT_SHEET section 4,
# E11; deterministic re-run verified 2026-08-13).
rows = [
    ("cap-64, floor-round", 0.63), ("cap-64, degrade-aware", 0.58),
    ("cap-64, best grid", 0.34), ("panel expansion", 0.13),
    ("asymmetric 48/64", 0.0215),
]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.31, right=0.94, top=0.84, bottom=0.30)
ys = list(range(len(rows)))[::-1]
cols = [S.MORANDI["lavender"]] * (len(rows) - 1) + [S.MORANDI["terra"]]
ax.barh(ys, [r[1] for r in rows], height=0.52, color=cols)
for y, r in zip(ys, rows):
    ax.text(r[1] + 0.012, y, f"{r[1]:.3f}".rstrip("0").rstrip("."), va="center",
            fontsize=4.8, color=S.INK)
ax.axvline(0.05, color=S.MORANDI["sage"], lw=0.7, ls=(0, (4, 2)))
ax.text(0.05, -0.62, "alpha 0.05", fontsize=4.8, color=S.MORANDI["sage"],
        ha="center")
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=4.6)
ax.set_xlabel("Paired McNemar P (navigation vs rule)")
ax.set_xlim(0, 0.72)
ax.set_title("Both escape routes closed", fontsize=6.2, loc="left", pad=5.0)
ax.text(0.02, -0.26, "asymmetric budget rejected: violates the\nbudget-matching iron rule",
        transform=ax.transAxes, fontsize=4.4, color=S.INK_SOFT, style="italic",
        va="top")
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "g"))
