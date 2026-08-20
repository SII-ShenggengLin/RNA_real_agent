"""Fig 5a - GenNav mechanism schematic."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import style as S

W, H = 55, 42

fig = S.new_free(W, H)
ax = fig.add_axes((0.01, 0.01, 0.98, 0.95))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")


def box(x, y, w, h, text, fc, ec, fs=4.3, lw=0.7, tc=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.06,rounding_size=0.10",
                                fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center",
            color=tc or S.INK, linespacing=1.25)


def arrow(x0, y0, x1, y1, color=None):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=5, lw=0.7,
                                 color=color or S.INK_SOFT))


ax.text(0.15, 9.55, "GenNav: navigate the generator's control space", fontsize=6.0,
        color=S.INK, weight="bold", va="center")

box(0.20, 6.85, 2.15, 1.35, "constraint matrix\n(pre-registered)", S.CREAM,
    S.CREAM_DK)
box(0.20, 4.55, 2.15, 1.55, "gear lattice\n(mRNA λ / aptamer\nlength-seed-sample)", S.CREAM,
    S.CREAM_DK)
box(0.20, 2.15, 2.15, 1.55, "feasibility probe\n(shallow, adaptive)", "white",
    S.MORANDI["blue"])
arrow(1.28, 6.80, 1.28, 6.15)
arrow(1.28, 4.50, 1.28, 3.75)

box(3.15, 4.10, 2.45, 3.05, "budget allocation\nguarantee rounds:\none repair round per\nband before any band\ngets a second", "white",
    S.MORANDI["blue"])
arrow(2.40, 2.95, 3.10, 4.60)

box(6.30, 6.55, 3.45, 1.65, "per-profile delivery\n(5 candidates x 3 profiles,\ndiversity gate D1)", "white",
    S.MORANDI["green"])
box(6.30, 3.95, 3.45, 1.60, "declared degrade\n(no feasible gear:\nHER2 class)", "white",
    S.MORANDI["terra"])
arrow(5.65, 6.20, 6.25, 7.35, color=S.MORANDI["green"])
arrow(5.65, 5.00, 6.25, 4.75, color=S.MORANDI["terra"])

box(3.15, 0.60, 6.60, 1.85, "equal budget across arms (48 raw candidates)\nevery generation and folding call audited\ndeterministic - the LLM arbitrates ties only",
    S.CREAM, S.CREAM_DK, fs=4.2)
arrow(4.37, 4.05, 4.37, 2.50)
ax.text(8.10, 2.80, "budget cap 48", fontsize=4.4, color=S.INK_SOFT, ha="center",
        style="italic")
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
