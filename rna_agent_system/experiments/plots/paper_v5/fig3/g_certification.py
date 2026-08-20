"""Fig 3g - Profiling certifies power where it exists (E7, MRL oracle)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

e7 = D.e7_profile()
fams = ["sample2019_egfp_random50", "sample2019_varying_length_random",
        "sample2019_varying_length_human"]
short = ["EGFP random\n(50 nt)", "random 25-100 nt", "human endogenous\n25-100 nt"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1], left=0.14, right=0.97,
                      top=0.82, bottom=0.22, wspace=0.55)

ax1 = fig.add_subplot(gs[0])
vals = [e7["per_family"][f]["screening"]["auroc"] for f in fams]
los = [v - e7["per_family"][f]["screening"]["auroc_ci_lo"] for v, f in
       zip(vals, fams)]
his = [e7["per_family"][f]["screening"]["auroc_ci_hi"] - v for v, f in
       zip(vals, fams)]
ax1.errorbar(range(3), vals, yerr=[los, his], fmt="o", ms=4, lw=1.0,
             capsize=2.2, color=S.MORANDI["green"])
ax1.axhline(0.8, color=S.MORANDI["sage"], lw=0.6, ls=(0, (4, 2)))
ax1.text(2.45, 0.815, "gate", fontsize=5.0, color=S.MORANDI["sage"], ha="right")
ax1.axhline(0.5, color=S.GRID, lw=0.5)
ax1.set_xticks(range(3))
ax1.set_xticklabels(short, fontsize=4.6)
ax1.set_ylabel("Screening AUROC")
ax1.set_ylim(0.45, 1.06)
ax1.set_title("Screening: all families certified", fontsize=5.8, loc="left",
              pad=5.0)
S.despine(ax1)

ax2 = fig.add_subplot(gs[1])
vals = [e7["per_family"][f]["ranking"]["spearman_rho"] for f in fams]
ax2.scatter(range(3), vals, s=14, color=S.MORANDI["green"], zorder=3)
ax2.axhline(0.6, color=S.MORANDI["sage"], lw=0.6, ls=(0, (4, 2)))
ax2.text(-0.45, 0.615, "gate ρ ≥ 0.6", fontsize=5.0, color=S.MORANDI["sage"],
         ha="left")
ax2.set_xticks(range(3))
ax2.set_xticklabels([""] * 3)
ax2.set_ylabel("Ranking Spearman ρ\n(vs measured MRL, n = 120)")
ax2.set_ylim(0.5, 1.06)
ax2.set_title("Ranking: all families certified", fontsize=5.8, loc="left",
              pad=5.0)
S.despine(ax2)
fig.suptitle("The expression oracle passes decisively (706 anchors)", fontsize=6.2,
             x=0.13, ha="left", y=0.97)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "g"))
