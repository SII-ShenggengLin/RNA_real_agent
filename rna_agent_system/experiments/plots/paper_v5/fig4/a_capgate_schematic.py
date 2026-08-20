"""Fig 4a - CapGate schematic: two deterministic gates fed by the capability self-model."""
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


def box(x, y, w, h, text, fc, ec, fs=4.5, tc=None, lw=0.7, bold=False):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.10",
                       fc=fc, ec=ec, lw=lw)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center",
            color=tc or S.INK, weight="bold" if bold else "normal", linespacing=1.25)


def arrow(x0, y0, x1, y1, color=None, style="-|>", ls="-"):
    ar = FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=5,
                         lw=0.7, color=color or S.INK_SOFT, linestyle=ls)
    ax.add_patch(ar)


ax.text(0.15, 9.55, "CapGate: deterministic gates on actions and claims", fontsize=6.0,
        color=S.INK, weight="bold", va="center")

# left column: profiling -> self model
box(0.20, 6.55, 2.30, 1.55, "anchor sets\n(assertion-curated)", S.CREAM, S.CREAM_DK)
box(0.20, 4.35, 2.30, 1.55, "capability\nprofiler", S.CREAM, S.CREAM_DK)
box(0.20, 2.10, 2.30, 1.60, "SelfModel\n(oracle x task x family\ngrades)", "white",
    S.MORANDI["blue"], fs=4.3, bold=False)
arrow(1.35, 6.50, 1.35, 5.95)
arrow(1.35, 4.30, 1.35, 3.75)

# centre column: gates
box(3.35, 6.15, 2.55, 1.75, "DecisionGate\nblocks actions without\nan evidence basis",
    "white", S.MORANDI["blue"])
box(3.35, 3.35, 2.55, 1.75, "ClaimGate\ndowngrades claims to\nvalidated scope",
    "white", S.MORANDI["blue"])
arrow(2.55, 5.15, 3.30, 6.85)
arrow(2.55, 2.95, 3.30, 4.25)

# scope ladder
box(6.65, 3.35, 3.15, 4.55, "", S.CREAM, S.CREAM_DK)
ax.text(8.22, 7.45, "scope ladder", fontsize=4.8, ha="center", color=S.INK,
        weight="bold")
for i, (lab, col) in enumerate([("absolute", S.MORANDI["terra"]),
                                ("same-target relative", S.MORANDI["sand"]),
                                ("trend only", S.MORANDI["lavender"]),
                                ("suppressed", S.MORANDI["grey"])]):
    yl = 6.75 - i * 0.92
    box(6.92, yl - 0.32, 2.60, 0.66, lab, "white", col, fs=4.2)
    if i < 3:
        arrow(8.22, yl - 0.38, 8.22, yl - 0.56)
arrow(5.95, 4.22, 6.60, 5.0)

# agent + audit
box(3.35, 0.55, 2.55, 1.45, "agent actions\n+ reports", "white", S.INK_SOFT)
arrow(4.60, 6.10, 4.60, 2.05, style="-|>", color=S.MORANDI["blue"])
ax.text(4.72, 4.10, "gated", fontsize=4.2, color=S.MORANDI["blue"], rotation=90,
        va="center")
box(6.65, 0.55, 3.15, 1.80, "append-only audit trail\n(call + gate decisions)",
    "white", S.MORANDI["lavender"], fs=4.3)
arrow(5.95, 1.28, 6.60, 1.45)
box(0.20, 0.55, 2.30, 1.10, "zero LLM in the\ngate path", S.CREAM, S.CREAM_DK, fs=4.2)
arrow(1.35, 2.05, 1.35, 1.70)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
