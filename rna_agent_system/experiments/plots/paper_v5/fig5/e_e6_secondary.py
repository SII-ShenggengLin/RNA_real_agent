"""Fig 5e - mRNA secondary endpoint disclosed + LLM budget."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

q = D.e6_s2_verdict()["observed"]["quality"]
items = [("R1/R4\nranking", q["R1_R4_all_profiles"]),
         ("R3\ngear sep.", q["R3_all_arms"]),
         ("D1/D2/D3\ndiversity", q["D1_D2_D3_all_profiles"]),
         ("lattice\n>= 3 gears", q["E14_gen_lattice_ge3_all"])]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.24, right=0.95, top=0.84, bottom=0.34)
ys = range(len(items))
cols = [S.MORANDI["green"] if v else S.MORANDI["terra"] for _, v in items]
ax.barh(list(ys), [1 if v else 0.28 for _, v in items], height=0.52, color=cols)
for y, (lab, v) in zip(ys, items):
    ax.text(1.03, y, "pass" if v else "fail", va="center", fontsize=5.0,
            color=S.MORANDI["sage"] if v else S.MORANDI["brick"])
ax.set_yticks(list(ys))
ax.set_yticklabels([lab for lab, _ in items], fontsize=5.0)
ax.set_xlim(0, 1.35)
ax.set_xticks([])
ax.set_title("Secondary quality bundle (disclosed failure)", fontsize=6.2,
             loc="left", pad=5.0)
ax.text(0.02, -0.22, "failures trace to HER2: no feasible lambda gear\n-> declared degrade",
        transform=ax.transAxes, fontsize=4.6, color=S.INK_SOFT, style="italic", va="top")
ax.text(0.02, -0.47, "LLM usage: 43 calls total (mean 2.4/gene; budget 5-9)",
        transform=ax.transAxes, fontsize=4.6, color=S.INK, va="top")
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
