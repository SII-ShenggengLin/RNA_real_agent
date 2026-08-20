"""Fig 6a - The two-sided capability map (oracle x task-type grades)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S

W, H = 55, 42

# Grades from the frozen verdict files (E1 v2, E7, RNAsmol boundary panel).
ROWS = [
    ("EGARPS np (aptamer)", ["failed", "failed", "failed"]),
    ("Protenix ipTM (aptamer)", ["failed", "failed", "failed"]),
    ("RhoFold pLDDT (aptamer)", ["failed", "failed", "failed"]),
    ("GEMORNA 5'UTR MRL (mRNA)", ["verified", "verified", "n.a."]),
    ("GEMORNA 3'UTR stab. (mRNA)", ["unprofiled", "unprofiled", "n.a."]),
    ("RNAsmol (training dist.)", ["verified", "n.a.", "n.a."]),
    ("RNAsmol (short-aptamer OOD)", ["failed", "unprofiled", "n.a."]),
]
COLS = ["screening", "ranking", "docking"]
GC = {"verified": S.MORANDI["green"], "failed": S.MORANDI["terra"],
      "unprofiled": S.MORANDI["grey"], "n.a.": "#EDEAE2"}
SYM = {"verified": "\u2713", "failed": "\u2715", "unprofiled": "?", "n.a.": ""}

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
ax = fig.add_axes((0.40, 0.20, 0.57, 0.66))
ax.set_xlim(0, 3)
ax.set_ylim(0, len(ROWS))
ax.invert_yaxis()
ax.axis("off")
fig.text(0.03, 0.93, "The capability map is two-sided", fontsize=6.2,
         weight="bold", color=S.INK)
fig.text(0.03, 0.87, "every grade = one anchor-set verdict", fontsize=4.8,
         color=S.INK_SOFT)
for j, cname in enumerate(COLS):
    ax.text(j + 0.5, -0.28, cname, fontsize=4.8, ha="center", color=S.INK)
for i, (rname, grades) in enumerate(ROWS):
    y = i + 0.5
    fig.text(0.385, y, rname, fontsize=4.4, ha="right", va="center", color=S.INK)
    for j, g in enumerate(grades):
        ax.add_patch(Rectangle((j + 0.06, i + 0.10), 0.88, 0.80, fc=GC[g],
                               ec="white", lw=0.6))
        ax.text(j + 0.5, y, SYM[g], fontsize=5.0, ha="center", va="center",
                color="white" if g != "n.a." else S.INK)
handles = [Rectangle((0, 0), 1, 1, fc=GC[k]) for k in
           ("verified", "failed", "unprofiled")]
fig.legend(handles, ["verified", "failed", "unprofiled"], loc="lower center",
           ncol=3, fontsize=4.8, frameon=False, bbox_to_anchor=(0.62, 0.045))
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
