"""Fig 4d - Overreach events: where they come from, and that gating zeroes them."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

evs = {}
for r in D.e3_runs():
    if r["arm"] != "ungated":
        continue
    for e in (r["result"].get("overreach_events") or []):
        evs[e["oracle"]] = evs.get(e["oracle"], 0) + 1
names = {"egarps_native_probability": "EGARPS np\n(ranking use)", "proteinx_ipTM":
         "Protenix ipTM\n(ranking use)", "rhofold_mean_plddt": "RhoFold pLDDT\n(ranking use)"}
ks = sorted(evs, key=evs.get)

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.28, right=0.95, top=0.84, bottom=0.15)
ys = range(len(ks))
ax.barh(list(ys), [evs[k] for k in ks], height=0.55, color=S.MORANDI["lavender"])
for i, k in enumerate(ks):
    ax.text(evs[k] + 0.25, i, str(evs[k]), va="center", fontsize=5.2, color=S.INK)
ax.set_yticks(list(ys))
ax.set_yticklabels([names.get(k, k) for k in ks], fontsize=4.8)
ax.set_xlim(0, max(evs.values()) * 1.3)
ax.set_xlabel("Overreach events")
ax.set_title("Ungated: 23 events   |   gated: 0", fontsize=6.2, loc="left",
             pad=5.0)
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
