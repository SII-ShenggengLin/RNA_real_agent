"""Fig 4c - Claim adjudication: ungated vs gated waffle grids."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

pa = D.e3_summary()["per_arm"]


def waffle(ax, counts, colors, title):
    cells = []
    for label, n in counts:
        cells.extend([label] * n)
    ncol = 10
    for i, lab in enumerate(cells):
        r, c = divmod(i, ncol)
        ax.add_patch(plt.Rectangle((c, -(r)), 0.84, 0.84, fc=colors[lab],
                                   ec="white", lw=0.6))
    ax.set_xlim(-0.1, ncol)
    ax.set_ylim(-(len(cells) // ncol + 1), 1.0)
    ax.axis("off")
    ax.set_title(title, fontsize=5.8, loc="left", pad=3.0)


colors = {"FP": S.MORANDI["terra"], "TP": S.MORANDI["blue"],
          "suppressed": S.MORANDI["grey"], "borderline": S.MORANDI["sand"]}

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], left=0.05, right=0.97,
                      top=0.86, bottom=0.13, hspace=0.65)
ax1 = fig.add_subplot(gs[0])
waffle(ax1, [("FP", pa["ungated"]["FP"]), ("TP", pa["ungated"]["TP"])], colors,
       f"ungated: {pa['ungated']['n_claims']} claims")
ax2 = fig.add_subplot(gs[1])
waffle(ax2, [("TP", pa["gated"]["TP"]), ("suppressed", pa["gated"]["suppressed"]),
             ("borderline", pa["gated"]["borderline"])], colors,
       f"gated: {pa['gated']['n_claims']} claims")
handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in colors.values()]
fig.legend(handles, ["false positive", "true positive", "suppressed", "borderline"],
           loc="lower center", ncol=4, fontsize=4.8, frameon=False,
           bbox_to_anchor=(0.5, 0.0))
fig.suptitle("Claim-by-claim adjudication (blind, deterministic)", fontsize=6.2,
             x=0.05, ha="left", y=0.97)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
