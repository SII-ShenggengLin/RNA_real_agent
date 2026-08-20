"""Fig 6b - Junction repair has no free lunch: four gated attempts, four NO-GO."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

j = D.junction_summaries()
attempts = [
    ("P1 shuffle", j["p1"]["results"]["burial_fix_rate"],
     "repair 13/14;\nstability cost +0.022/nt", False),
    ("P1 v2 sweep", 1.0,
     "repair 7/7 at every w;\ncost never halved", False),
    ("integrated LD", max(
        j["integrated"]["per_weight"][w]["hard_repair_rate"] for w in
        j["integrated"]["per_weight"]),
     "best repair 2/7;\ncost > gate at all w", False),
    ("ddG route C", j["ddg"]["gate2_route_c"]["n_targets_pass"] / 3,
     "1/3 targets pass (EPO)", False),
]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.22, right=0.62, top=0.84, bottom=0.19)
ys = list(range(len(attempts)))[::-1]
ax.barh(ys, [a[1] for a in attempts], height=0.5, color=S.MORANDI["lavender"])
ax.axvline(2 / 3, color=S.MORANDI["sage"], lw=0.7, ls=(0, (4, 2)))
ax.text(2 / 3, len(attempts) - 0.45, "gate 2/3", fontsize=4.8,
        color=S.MORANDI["sage"], ha="center")
for y, a in zip(ys, attempts):
    ax.text(1.04, y, a[2], fontsize=4.4, va="center", color=S.INK,
            transform=ax.get_yaxis_transform())
ax.set_yticks(ys)
ax.set_yticklabels([a[0] for a in attempts], fontsize=4.6)
ax.set_xlim(0, 1.05)
ax.set_xticks([0, 0.33, 0.67, 1.0])
ax.set_xlabel("Hard-target repair rate")
ax.set_title("Four pre-registered attempts, all NO-GO", fontsize=6.2, loc="left",
             pad=5.0)
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
