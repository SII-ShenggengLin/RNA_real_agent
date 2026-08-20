"""Fig 6f - E15 confirmatory boundary: scarcity-panel regime (14:6, NS)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

v = D.aptamer_verdict("15")
pairs = v["pairs"]
b = v["primary"]["mcnemar"]["b"]
c = v["primary"]["mcnemar"]["c"]
both = len(pairs) - b - c

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.95, top=0.84, bottom=0.20)
cats = ["navigation\nonly", "both", "rule\nonly"]
vals = [b, both, c]
cols = [S.MORANDI["blue"], S.MORANDI["green"], S.MORANDI["terra"]]
ax.bar(range(3), vals, width=0.52, color=cols)
for i, val in enumerate(vals):
    ax.text(i, val + 0.5, str(val), ha="center", fontsize=5.4, color=S.INK)
ax.set_xticks(range(3))
ax.set_xticklabels(cats, fontsize=5.2)
ax.set_ylabel("Discordant profile pairs (n = 36)")
ax.set_ylim(0, max(vals) * 1.30)
ax.set_title(f"E15 confirmatory: {b}:{c}, {S.p_str(v['primary']['mcnemar']['p'])}",
             fontsize=6.2, loc="left", pad=5.0)
ax.text(0.97, 0.86, f"pooled E14+E15 28:9, {S.p_str(0.0026)}",
        transform=ax.transAxes, ha="right", fontsize=5.0, color=S.INK_SOFT)
ax.text(0.97, 0.74, "advantage is regime-specific\n(delivery-scarce panels)",
        transform=ax.transAxes, ha="right", fontsize=4.6, color=S.INK_SOFT,
        style="italic")
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
