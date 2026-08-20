"""Fig 3i - Confounded improvement: our own coordination claim dissolves."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

f4 = D.fig4_ungated()["paired_tests"]["metrics"]["egarps_component"]["bmc1_vs_serial"]
p0 = D.p0_budget()
p3 = D.p3_guided()

stages = [("ungated\neffect", f4["cliffs_delta"], f4["wilcoxon_p"]),
          ("budget-\nmatched", p0["cliffs_delta"], p0["wilcoxon_paired_p"]),
          ("guided\ncontrol", p3["cliffs_delta"], p3["wilcoxon_paired_p"])]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.16, right=0.96, top=0.84, bottom=0.26)
xs = range(3)
vals = [s[1] for s in stages]
ax.plot(list(xs), vals, color=S.MORANDI["grey"], lw=0.9, zorder=2)
ax.scatter(list(xs), vals, s=16, color=[S.MORANDI["terra"], S.MORANDI["blue"],
                                        S.MORANDI["blue"]], zorder=3)
for x, (lab, d, p) in zip(xs, stages):
    ax.text(x, d + 0.028, f"δ = {d:.2f}", fontsize=5.2, ha="center", color=S.INK)
    ax.text(x, -0.13, S.p_str(p), fontsize=4.8, ha="center", color=S.INK_SOFT)
ax.axhline(0.3, color=S.MORANDI["sage"], lw=0.7, ls=(0, (4, 2)))
ax.text(0.02, 0.315, "GO gate δ ≥ 0.3", fontsize=5.0, color=S.MORANDI["sage"],
        ha="left", transform=ax.get_yaxis_transform())
ax.axhline(0, color=S.GRID, lw=0.5)
ax.set_xticks(list(xs))
ax.set_xticklabels([s[0] for s in stages], fontsize=5.0)
ax.set_ylabel("Cliff's δ (coordination benefit)")
ax.set_ylim(-0.08, 0.62)
ax.set_title("Same effect under pre-registered controls", fontsize=6.2,
             loc="left", pad=5.0)
ax.text(0.02, 0.035, "self-audit claim survival 0/2", transform=ax.transAxes,
        fontsize=5.2, color=S.INK, style="italic")
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "i"))
