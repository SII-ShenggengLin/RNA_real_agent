"""Fig 3f - Claim overreach of the ungated agent (E3, aptamer audit set)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

s = D.e3_summary()["per_arm"]["ungated"]
fp, tp = s["FP"], s["TP"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 1], left=0.20, right=0.97,
                      top=0.84, bottom=0.17, hspace=0.85)

axw = fig.add_subplot(gs[0])
claims = ([S.MORANDI["terra"]] * fp) + ([S.MORANDI["blue"]] * tp)
ncol = 10
for i, c in enumerate(claims):
    r, col_i = divmod(i, ncol)
    axw.add_patch(plt.Rectangle((col_i * 1.0, -(r * 1.0)), 0.82, 0.82, fc=c,
                                ec="white", lw=0.6))
axw.set_xlim(-0.1, ncol)
axw.set_ylim(-1.05, 0.95)
axw.axis("off")
axw.set_title(f"Ungated claims: {fp}/{fp + tp} false positives "
              f"({s['fp_rate'] * 100:.1f}%)", fontsize=6.2, loc="left", pad=5.0)
axw.text(ncol - 3.2, 0.35, "false positive", fontsize=4.8,
         color=S.MORANDI["terra"])
axw.text(ncol - 3.2, -0.6, "true positive", fontsize=4.8,
         color=S.MORANDI["blue"])

axb = fig.add_subplot(gs[1])
evs = {}
for r in D.e3_runs():
    if r["arm"] != "ungated":
        continue
    for e in (r["result"].get("overreach_events") or []):
        evs[e["oracle"]] = evs.get(e["oracle"], 0) + 1
names = {"egarps_native_probability": "EGARPS np", "proteinx_ipTM": "ipTM",
         "rhofold_mean_plddt": "pLDDT"}
ks = sorted(evs, key=evs.get)
axb.barh([names.get(k, k) for k in ks], [evs[k] for k in ks], height=0.55,
         color=S.MORANDI["lavender"])
for i, k in enumerate(ks):
    axb.text(evs[k] + 0.25, i, str(evs[k]), va="center", fontsize=5.0,
             color=S.INK)
axb.set_xlim(0, max(evs.values()) * 1.25)
axb.set_xlabel("Overreach events (ungated: 23; gated: 0)", fontsize=5.5)
S.style_cat_ax(axb)
axb.tick_params(labelsize=5.0)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
