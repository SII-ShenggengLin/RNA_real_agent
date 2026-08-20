"""Fig 5c - mRNA primary endpoint: discordant pairs 30:0 (McNemar P = 1.9e-9)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

v = D.e6_s2_verdict()
mc = v["observed"]["mcnemar"]["C_vs_A"]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.17, right=0.95, top=0.84, bottom=0.17)
cats = ["C passes,\nA fails", "both pass", "both fail", "A passes,\nC fails"]
vals = [mc["b"], v["observed"]["n_pairs"] - mc["b"] - mc["c"], 0, mc["c"]]
cols = [S.MORANDI["blue"], S.MORANDI["green"], S.MORANDI["grey"],
        S.MORANDI["terra"]]
bars = ax.bar(range(4), vals, width=0.55, color=cols)
for i, val in enumerate(vals):
    ax.text(i, val + 1.0, str(val), ha="center", fontsize=5.4, color=S.INK)
ax.set_xticks(range(4))
ax.set_xticklabels(cats, fontsize=5.0)
ax.set_ylabel("Profile pairs (n = 54)")
ax.set_ylim(0, 33)
ax.set_title(f"mRNA delivery: discordant {mc['b']}:{mc['c']}, {S.p_str(mc['p'])}",
             fontsize=6.2, loc="left", pad=5.0)
ax.text(0.97, 0.84, f"gene-level delivery {v['observed']['c_e2e_gene']:.1f}",
        transform=ax.transAxes, ha="right", fontsize=5.2, color=S.MORANDI["sage"])
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
