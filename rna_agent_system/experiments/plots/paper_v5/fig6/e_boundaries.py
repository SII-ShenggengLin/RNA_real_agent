"""Fig 6e - Generator boundaries a calibrated agent must know upfront."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import style as S
import data as D

W, H = 55, 42

ft = D.failure_taxonomy()["totals"]["final_failures"]

fig = S.new_free(W, H)
ax = fig.add_axes((0.01, 0.01, 0.98, 0.95))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

cards = [
    ("ODesign: zero candidates\non ferritin-family targets",
     f"{ft.get('boundary_odesign_zero_output', 24)} final failures",
     "deterministic empty output;\npanel rule excludes them", S.MORANDI["terra"]),
    ("LinearDesign: memory ceiling\non multi-kilo-aa proteins",
     f"{ft.get('boundary_lineardesign_oom', 2)} final failures",
     "fail-fast address-space guard\n(Zika polyprotein, factor VIII)",
     S.MORANDI["sand"]),
    ("No feasible lambda gear\non HER2-class targets",
     "1 target class (E6)",
     "feasibility probe returns [];\ndeclared degrade path", S.MORANDI["lavender"]),
]
y = 7.0
for title, stat, note, col in cards:
    card = FancyBboxPatch((0.25, y - 1.75), 9.5, 2.05,
                          boxstyle="round,pad=0.10,rounding_size=0.14",
                          fc=S.CREAM, ec=S.CREAM_DK, lw=0.7)
    ax.add_patch(card)
    ax.add_patch(FancyBboxPatch((0.45, y - 1.55), 0.16, 1.65,
                                boxstyle="round,pad=0.02,rounding_size=0.04",
                                fc=col, ec=col, lw=0.5))
    ax.text(0.90, y - 0.15, title, fontsize=5.0, color=S.INK, va="top",
            weight="bold", linespacing=1.3)
    ax.text(6.10, y - 0.15, stat, fontsize=5.0, color=col, va="top", ha="left",
            weight="bold")
    ax.text(0.90, y - 1.05, note, fontsize=4.4, color=S.INK_SOFT, va="top",
            linespacing=1.3)
    y -= 2.42

ax.text(0.25, 9.55, "Generator boundaries known before planning",
        fontsize=6.0, color=S.INK, weight="bold", va="center")
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
