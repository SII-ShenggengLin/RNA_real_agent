"""Fig 5f - Aptamer campaign arc E8-E15: discordance and P per campaign."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

nums = []
for e in ("8", "9", "10", "12", "14", "15"):
    v = D.aptamer_verdict(e)
    nums.append((f"E{e}", v["primary"]["mcnemar"]["b"], v["primary"]["mcnemar"]["c"],
                 v["primary"]["mcnemar"]["p"]))

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.14, right=0.84, top=0.84, bottom=0.30)
xs = range(len(nums))
b = [n[1] for n in nums]
c = [n[2] for n in nums]
ax.vlines([x - 0.10 for x in xs], 0, b, color=S.MORANDI["blue"], lw=1.6)
ax.scatter([x - 0.10 for x in xs], b, s=12, color=S.MORANDI["blue"], zorder=3,
           label="nav wins (b)")
ax.vlines([x + 0.10 for x in xs], 0, c, color=S.MORANDI["terra"], lw=1.6)
ax.scatter([x + 0.10 for x in xs], c, s=12, color=S.MORANDI["terra"], zorder=3,
           label="rule wins (c)")
ax2 = ax.twinx()
ps = [n[3] for n in nums]
ax2.plot(list(xs), ps, color=S.INK_SOFT, lw=0.8, ls=(0, (3, 2)), marker="o",
         ms=2.4, label="McNemar P")
ax2.set_yscale("log")
ax2.set_ylim(0.004, 2.2)
ax2.set_ylabel("McNemar P")
ax2.spines["top"].set_visible(False)
ax2.tick_params(labelsize=5.0)
ax.set_xticks(list(xs))
ax.set_xticklabels([n[0] for n in nums], fontsize=5.4)
ax.set_ylabel("Discordant pairs")
ax.set_ylim(0, 16.5)
ax.set_title("Aptamer arc: same budget, better navigation", fontsize=6.2,
             loc="left", pad=5.0)
ax.annotate("densified lattice\n+ S1 priors", xy=(2.9, 9.2), xytext=(0.9, 10.6),
            fontsize=4.4, color=S.INK,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
ax.annotate("guarantee\nrounds", xy=(4.06, 14), xytext=(2.9, 15.1), fontsize=4.4,
            color=S.INK,
            arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
ax.text(-0.42, 14.6, "nav wins (b)", fontsize=4.6, color=S.MORANDI["slate"])
ax.text(-0.42, 2.1, "rule wins (c)", fontsize=4.6, color=S.MORANDI["brick"])
ax2.text(0.98, 0.88, "McNemar P (right)", fontsize=4.6, color=S.INK_SOFT,
         ha="right", transform=ax2.transAxes)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
