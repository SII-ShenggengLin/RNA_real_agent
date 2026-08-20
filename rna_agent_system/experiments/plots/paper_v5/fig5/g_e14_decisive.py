"""Fig 5g - E14 decisive: navigation delivers more cells at equal budget."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

v = D.aptamer_verdict("14")
pairs = v["pairs"]
c_cells = sum(1 for p in pairs if p["C_jcd"])
a_cells = sum(1 for p in pairs if p["A_jcd"])
pr = v["primary"]
n_targets = v["n_targets"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], left=0.14, right=0.97,
                      top=0.82, bottom=0.19, wspace=0.62)

ax1 = fig.add_subplot(gs[0])
groups = ["profile cells\ndelivered", "end-to-end\ntargets"]
nav = [c_cells, round(pr["c_e2e_rate"] * n_targets)]
rule = [a_cells, round(pr["a_e2e_rate"] * n_targets)]
tot = [len(pairs), n_targets]
x = [0, 1]
w = 0.32
ax1.bar([xi - w / 2 for xi in x], [v_ / t_ for v_, t_ in zip(rule, tot)], width=w,
        color=S.MORANDI["terra"], label="rule grid")
ax1.bar([xi + w / 2 for xi in x], [v_ / t_ for v_, t_ in zip(nav, tot)], width=w,
        color=S.MORANDI["blue"], label="navigation")
for xi, (r_, n_, t_) in zip(x, zip(rule, nav, tot)):
    ax1.text(xi - w / 2, r_ / t_ + 0.03, f"{r_}/{t_}", ha="center", fontsize=5.0,
             color=S.INK)
    ax1.text(xi + w / 2, n_ / t_ + 0.03, f"{n_}/{t_}", ha="center", fontsize=5.0,
             color=S.INK)
ax1.set_xticks(x)
ax1.set_xticklabels(groups, fontsize=5.2)
ax1.set_ylim(0, 1.02)
ax1.set_ylabel("Fraction delivered")
ax1.set_title("E14 (12 targets, 48-raw budget)", fontsize=5.8, loc="left", pad=5.0)
ax1.legend(fontsize=4.8, loc="upper right")
S.despine(ax1)

ax2 = fig.add_subplot(gs[1])
cats = ["nav\nonly", "both", "rule\nonly"]
b = pr["mcnemar"]["b"]
c = pr["mcnemar"]["c"]
both = len(pairs) - b - c
vals = [b, both, c]
cols = [S.MORANDI["blue"], S.MORANDI["green"], S.MORANDI["terra"]]
ax2.bar(range(3), vals, width=0.55, color=cols)
for i, val in enumerate(vals):
    ax2.text(i, val + 0.5, str(val), ha="center", fontsize=5.2, color=S.INK)
ax2.set_xticks(range(3))
ax2.set_xticklabels(cats, fontsize=5.0)
ax2.set_ylabel("Discordant pairs")
ax2.set_ylim(0, max(vals) * 1.35)
ax2.set_title(f"{b}:{c}, {S.p_str(pr['mcnemar']['p'])}", fontsize=5.8, loc="left",
              pad=5.0)
S.despine(ax2)
fig.suptitle("Decisive aptamer campaign", fontsize=6.2, x=0.11, ha="left", y=0.97)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "g"))
