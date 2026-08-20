"""Fig 5h - E14 delivery map: 12 targets x 3 profiles, pair outcomes."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S
import data as D

W, H = 55, 42

v = D.aptamer_verdict("14")
targets = v["targets"]
order = ["compact", "standard", "extended"]
idx = {t: i for i, t in enumerate(targets)}

COL = {(True, True): S.MORANDI["green"], (True, False): S.MORANDI["blue"],
       (False, True): S.MORANDI["terra"], (False, False): S.MORANDI["grey"]}
counts = {(True, True): 0, (True, False): 0, (False, True): 0, (False, False): 0}

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.27, right=0.98, top=0.84, bottom=0.13)
for p in v["pairs"]:
    i, j = idx[p["target_id"]], order.index(p["profile"])
    key = (bool(p["C_jcd"]), bool(p["A_jcd"]))
    counts[key] += 1
    ax.add_patch(Rectangle((j, len(targets) - 1 - i), 0.92, 0.92, fc=COL[key],
                           ec="white", lw=0.5))
ax.set_xlim(-0.05, 3.0)
ax.set_ylim(-0.6, len(targets))
ax.set_xticks([0.46, 1.46, 2.46])
ax.set_xticklabels(["compact", "standard", "extended"], fontsize=5.0)
ax.set_yticks([len(targets) - 1 - i + 0.46 for i in range(len(targets))])
ax.set_yticklabels([t.replace("SARS-CoV-2_Nucleocapsid", "SARS-N")
                    .replace("Carbonic_anhydrase_II", "CAII")
                    .replace("Chymotrypsinogen", "Chymotr.").replace("_", " ")
                    for t in targets], fontsize=4.2)
ax.tick_params(length=0)
for sp in ax.spines.values():
    sp.set_visible(False)
handles = [Rectangle((0, 0), 1, 1, fc=COL[k]) for k in
           ((True, False), (True, True), (False, True), (False, False))]
ax.legend(handles, [f"navigation only ({counts[(True, False)]})",
                    f"both ({counts[(True, True)]})",
                    f"rule only ({counts[(False, True)]})",
                    f"neither ({counts[(False, False)]})"],
          loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=4.4,
          frameon=False, handlelength=1.0, handletextpad=0.4, columnspacing=0.8)
ax.set_title("E14: per-profile joint delivery (12 targets)", fontsize=6.2,
             loc="left", pad=5.0)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "h"))
