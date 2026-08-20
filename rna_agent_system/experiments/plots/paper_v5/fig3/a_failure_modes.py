"""Fig 3a - Schematic: three failure modes of an ungated scientific agent."""
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

CARD_W = 2.86
cards = [
    dict(x=0.22, title="1  Uncalibrated\n tool trust",
         row1=("oracle", "agent"),
         row2="score consumed\nat face value",
         foot="no power check for task,\nfamily or regime",
         col=S.MORANDI["blue"]),
    dict(x=3.57, title="2  Claim\n overreach",
         row1=("measurements", "report"),
         row2="claim exceeds\nthe evidence",
         foot="overreach enters\nthrough language",
         col=S.MORANDI["terra"]),
    dict(x=6.92, title="3  Confounded\n improvement",
         row1=("strategy A\n(n = 8)", "strategy B\n(n = 16)"),
         row2="apparent gain =\nmore samples",
         foot="budget confound,\nnot mechanism",
         col=S.MORANDI["lavender"]),
]

for c in cards:
    x0 = c["x"]
    card = FancyBboxPatch((x0, 0.55), CARD_W, 8.25,
                          boxstyle="round,pad=0.10,rounding_size=0.16",
                          fc=S.CREAM, ec=S.CREAM_DK, lw=0.7)
    ax.add_patch(card)
    ax.text(x0 + CARD_W / 2, 8.30, c["title"], fontsize=5.2, color=S.INK,
            weight="bold", va="center", ha="center", linespacing=1.25)
    # row 1: two boxes with an arrow between
    bw, bh, by = 1.08, 1.55, 5.35
    bx1 = x0 + 0.20
    bx2 = x0 + CARD_W - 0.20 - bw
    for bx, label in ((bx1, c["row1"][0]), (bx2, c["row1"][1])):
        b = FancyBboxPatch((bx, by), bw, bh,
                           boxstyle="round,pad=0.06,rounding_size=0.10",
                           fc="white", ec=c["col"], lw=0.7)
        ax.add_patch(b)
        ax.text(bx + bw / 2, by + bh / 2, label, fontsize=4.5, ha="center",
                va="center", color=S.INK)
    ar = FancyArrowPatch((bx1 + bw + 0.06, by + bh / 2), (bx2 - 0.06, by + bh / 2),
                         arrowstyle="-|>", mutation_scale=5, lw=0.7,
                         color=S.INK_SOFT)
    ax.add_patch(ar)
    # row 2: consequence box
    w2, h2, y2 = 2.34, 1.5, 2.85
    x2 = x0 + (CARD_W - w2) / 2
    b2 = FancyBboxPatch((x2, y2), w2, h2,
                        boxstyle="round,pad=0.06,rounding_size=0.10",
                        fc=c["col"], ec=c["col"], lw=0.7, alpha=0.30)
    ax.add_patch(b2)
    ax.text(x2 + w2 / 2, y2 + h2 / 2, c["row2"], fontsize=4.6, ha="center",
            va="center", color=S.INK)
    ar2 = FancyArrowPatch((x0 + CARD_W / 2, by - 0.06), (x0 + CARD_W / 2, y2 + h2 + 0.08),
                          arrowstyle="-|>", mutation_scale=5, lw=0.7,
                          color=S.INK_SOFT)
    ax.add_patch(ar2)
    ax.text(x0 + CARD_W / 2, 1.45, c["foot"], fontsize=4.5, ha="center",
            va="center", color=S.INK_SOFT, style="italic")

ax.text(0.22, 9.55, "Three failure modes, all measured in this work",
        fontsize=6.0, color=S.INK, weight="bold", va="center")
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
