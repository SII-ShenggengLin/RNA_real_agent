"""Fig 3e - Calibration inversion: thrombin Kd series + binders below negatives."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

p2 = D.p2_calibration()
recs = p2["records"]
pts = p2["thrombin_series"]["points"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25], left=0.13, right=0.97,
                      top=0.82, bottom=0.24, wspace=0.42)

ax1 = fig.add_subplot(gs[0])
kd = [p["kd_nm"] for p in pts]
sc = [p["native_probability"] for p in pts]
ax1.scatter(kd, sc, s=10, color=S.MORANDI["blue"], zorder=3)
ax1.set_xscale("log")
ax1.set_xlabel("K$_d$ (nM)")
ax1.set_ylabel("EGARPS native probability")
ax1.set_title(f"Affinity series, ρ = {p2['thrombin_series']['spearman_rho_native_probability_vs_neglogKd']:.2f}",
              fontsize=5.8, loc="left", pad=5.0)
S.despine(ax1)

ax2 = fig.add_subplot(gs[1])
binders = [(k, v["native_probability"]) for k, v in recs.items()
           if v["role"] == "binder"]
negatives = [(k, v["native_probability"]) for k, v in recs.items()
             if v["role"] == "negative"]
rng = np.random.default_rng(5)
ax2.scatter(np.full(len(negatives), 1) + rng.uniform(-0.15, 0.15, len(negatives)),
            [v for _, v in negatives], s=8, color=S.MORANDI["grey"], zorder=3,
            label=f"negatives (n={len(negatives)})")
ax2.scatter(np.full(len(binders), 0) + rng.uniform(-0.15, 0.15, len(binders)),
            [v for _, v in binders], s=8, color=S.MORANDI["terra"], zorder=3,
            label=f"known binders (n={len(binders)})")
ax2.set_yscale("log")
ax2.set_xticks([0, 1])
ax2.set_xticklabels(["binders", "negatives"], fontsize=5.4)
ax2.set_ylabel("EGARPS native probability")
ax2.set_title(f"Screening AUROC {p2['binder_vs_negative']['auroc']:.2f} "
              f"[{p2['binder_vs_negative']['auroc_ci95'][0]:.1f}, "
              f"{p2['binder_vs_negative']['auroc_ci95'][1]:.1f}]",
              fontsize=5.8, loc="left", pad=5.0)
ax2.legend(loc="upper right", fontsize=4.6, handletextpad=0.2)
ax2.annotate("pegaptanib\n(K$_d$ 49 pM)", xy=(0.13, 1.9e-6),
             xytext=(0.42, 8e-5), fontsize=4.6, color=S.INK,
             arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
ax2.annotate("scrambled TBA", xy=(1.14, 0.987), xytext=(0.30, 0.52),
             fontsize=4.6, color=S.INK,
             arrowprops=dict(arrowstyle="-", lw=0.5, color=S.INK_SOFT))
S.despine(ax2)
fig.suptitle("The oracle inverts on known aptamers", fontsize=6.2, x=0.13,
             ha="left", y=0.97)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
