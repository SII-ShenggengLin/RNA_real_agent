"""Fig 5b - Why selection-layer navigation failed (E5 pool saturation)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

n = D.e5_report_numbers()
rows = [("A1AT", n["a1at_pool_pass"]), ("Insulin", n["insulin_pool_pass"]),
        ("IL-2", n["il2_pool_pass"]), ("GFP", n["gfp_pool_pass_after_ecoli_table"]),
        ("EPO", n["epo_pool_pass"])]
rows = sorted(rows, key=lambda r: r[1])
POOL = n["gfp_pool_size"]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.22, right=0.95, top=0.84, bottom=0.17)
ys = range(len(rows))
cols = [S.MORANDI["blue"]] * len(rows)
cols[rows.index(("GFP", n["gfp_pool_pass_after_ecoli_table"]))] = S.MORANDI["terra"]
ax.barh(list(ys), [v for _, v in rows], height=0.58, color=cols)
for y, (lab, v) in zip(ys, rows):
    ax.text(v + 4, y, f"{v}/{POOL}", va="center", fontsize=5.0, color=S.INK)
ax.set_yticks(list(ys))
ax.set_yticklabels([lab for lab, _ in rows], fontsize=5.2)
ax.set_xlim(0, POOL + 30)
ax.set_xlabel(f"Candidates passing the matrix (of {POOL})")
ax.set_title("Fixed pool saturates one lambda gear", fontsize=6.2, loc="left",
             pad=5.0)
ax.annotate("GFP: 0/315 before the\nspecies-matched codon table",
            xy=(13, -0.22), xytext=(60, -0.95),
            fontsize=4.6, color=S.INK,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
ax.text(POOL + 26, -0.95, f"Insulin batch diversity {n['insulin_batch_diversity']:.4f} < {n['diversity_gate']:.2f} gate",
        fontsize=4.4, ha="right", color=S.INK_SOFT, style="italic")
ax.set_ylim(-1.5, len(rows) - 0.5)
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
