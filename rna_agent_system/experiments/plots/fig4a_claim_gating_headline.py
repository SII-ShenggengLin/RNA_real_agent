"""Fig 4a — capability gating eliminates false claims, preserves true ones.

Grouped bar headline of the E3 dual-arm re-run (Experiment 17, gated
treatment arm, paired with the Exp-5 ungated control arm on the identical
45-task audit set): left axis, false-positive claim rate FP/(FP+TP) per
arm with Wilson 95% CI whiskers; right axis, true-positive claim counts.
Value labels above every bar; n claims carried by the arm tick labels
(the fig2b convention). Arm colours: ungated terracotta / gated sage
green — the same warm/cool semantics as the per-claim verdict colours of
Fig. 4b (FP terracotta, TP sage).

Style (Nature conventions, the fig3-panel house style): no in-figure
titles or summary statistics — the panel letter is added at assembly and
the headline numbers live in the Fig. 4a caption; every text element one
6-pt pure-black style; colours only from palette rev 7; 1200-dpi PNG +
vector PDF (fonttype 42); absolute-mm geometry, single-column width.

Data  : experiments/results/exp17_claim_gating/summary.json
Usage : python experiments/plots/fig4a_claim_gating_headline.py
Output : experiments/plots/output/fig4a_claim_gating.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results" / "exp17_claim_gating" / "summary.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

ARM_COLORS = {"ungated": PALETTE_BY_NAME["terracotta"],
              "gated": PALETTE_BY_NAME["sage_green"]}
ARM_LABELS = {"ungated": "Ungated", "gated": "Gated"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
})


def main() -> int:
    summary = json.loads(RESULTS.read_text(encoding="utf-8"))
    arms = summary["arms"]
    n_claims = {arm: arms[arm]["TP"] + arms[arm]["FP"] for arm in ("ungated", "gated")}

    fig_w, fig_h = 89 / 25.4, 46 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    def _ax(x0_mm: float, w_mm: float) -> plt.Axes:
        return fig.add_axes([x0_mm / 25.4 / fig_w, 13 / 25.4 / fig_h,
                             w_mm / 25.4 / fig_w, 26 / 25.4 / fig_h])

    xs = [0, 1]
    # ── left: false-positive claim rate (%), Wilson CI whiskers ──────────
    ax_l = _ax(26, 24)
    for x, arm in zip(xs, ("ungated", "gated")):
        rate = arms[arm]["fp_rate"]
        lo, hi = arms[arm]["fp_rate_ci95"]
        ax_l.bar(x, 100 * rate, width=0.58, color=ARM_COLORS[arm],
                 edgecolor="none")
        label_y = 100 * rate + 3
        if rate > 0:
            ax_l.errorbar(x, 100 * rate,
                          yerr=[[100 * (rate - lo)], [100 * (hi - rate)]],
                          color=INK, elinewidth=0.5, capsize=1.4,
                          capthick=0.5, fmt="none")
            label_y = 100 * hi + 4
        else:
            label_y = 4.5
        ax_l.text(x, label_y, f"{100 * rate:.1f}%",
                  ha="center", va="bottom", fontsize=FONT, color=INK)
    ax_l.set_xticks(xs)
    ax_l.set_xticklabels([f"{ARM_LABELS[a]}\n(n = {n_claims[a]})"
                          for a in ("ungated", "gated")], fontsize=FONT)
    ax_l.set_xlim(-0.55, 1.55)
    ax_l.set_ylim(0, 100)
    ax_l.set_yticks(range(0, 101, 25))
    ax_l.set_ylabel("False-positive claims (%)", fontsize=FONT, labelpad=2)
    ax_l.tick_params(length=1.5, pad=1.5)
    ax_l.spines["top"].set_visible(False)
    ax_l.spines["right"].set_visible(False)

    # ── right: true-positive claim counts ────────────────────────────────
    ax_r = _ax(59, 24)
    tp = {a: arms[a]["TP"] for a in ("ungated", "gated")}
    y_max = max(tp.values())
    step = 5 if y_max <= 25 else 10
    y_top = ((y_max * 1.25 + step - 1) // step) * step
    for x, arm in zip(xs, ("ungated", "gated")):
        ax_r.bar(x, tp[arm], width=0.58, color=ARM_COLORS[arm], edgecolor="none")
        ax_r.text(x, tp[arm] + 0.035 * y_top, str(tp[arm]),
                  ha="center", va="bottom", fontsize=FONT, color=INK)
    ax_r.set_xticks(xs)
    ax_r.set_xticklabels([ARM_LABELS[a] for a in ("ungated", "gated")],
                         fontsize=FONT)
    ax_r.set_xlim(-0.55, 1.55)
    ax_r.set_ylim(0, y_top)
    ax_r.set_yticks(list(range(0, int(y_top) + 1, int(step))))
    ax_r.set_ylabel("True-positive claims", fontsize=FONT, labelpad=2)
    ax_r.tick_params(length=1.5, pad=1.5)
    ax_r.spines["top"].set_visible(False)
    ax_r.spines["right"].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4a_claim_gating.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"fig4a -> {OUT_DIR / 'fig4a_claim_gating.pdf'} (+png 1200 dpi); "
          f"FP rate {100 * arms['ungated']['fp_rate']:.1f}% -> "
          f"{100 * arms['gated']['fp_rate']:.1f}%, "
          f"TP {tp['ungated']} -> {tp['gated']} "
          f"(retention {100 * summary['tp_retention']:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
