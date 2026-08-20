"""Fig 4b - E3 headline: gating eliminates false-positive claims, keeps true ones."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

pa = D.e3_summary()["per_arm"]
groups = ["False-positive rate", "True-positive retention"]
ung = [pa["ungated"]["fp_rate"] * 100, 100.0]
gat = [pa["gated"]["fp_rate"] * 100,
       pa["gated"]["TP"] / pa["ungated"]["TP"] * 100]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.96, top=0.84, bottom=0.17)
x = [0, 1]
w = 0.32
ax.bar([xi - w / 2 for xi in x], ung, width=w, color=S.MORANDI["terra"],
       label="ungated")
ax.bar([xi + w / 2 for xi in x], gat, width=w, color=S.MORANDI["blue"],
       label="gated")
for xi, (u, g) in zip(x, zip(ung, gat)):
    ax.text(xi - w / 2, u + 2, f"{u:.1f}%", ha="center", fontsize=5.2, color=S.INK)
    ax.text(xi + w / 2, g + 2, f"{g:.1f}%" if g < 200 else f"{g:.1f}%",
            ha="center", fontsize=5.2, color=S.INK)
ax.set_xticks(x)
ax.set_xticklabels(["false-positive\nclaim rate", "true-positive\nretention"],
                   fontsize=5.2)
ax.set_ylabel("Per cent")
ax.set_ylim(0, 132)
ax.set_title("Aptamer audit set (20 tasks, 2 arms)", fontsize=6.2, loc="left",
             pad=5.0)
ax.legend(loc="upper right", fontsize=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
