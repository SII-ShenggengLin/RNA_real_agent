#!/usr/bin/env python3
"""Supplementary Fig. S1 — IRES literature-panel prediction: ROC curve with
bootstrap CI band.

Moved out of main Fig. 2 (where it was panel e) into the supplement on
2026-09-11 (user direction) — data, arm registration and rendering unchanged;
the panel script never drew a letter (panel letters are an assembler
responsibility), so the supplementary panel stands without one.

Threshold-free discrimination of the ``ires_prediction`` workflow on 9
literature IRES 5′UTRs vs 50 random human 5′UTR negatives (GENCODE v46).
**Figure endpoint (user re-registration 2026-08-26): the mode-2 sliding-window
scanning arm** (window 174 / step 50 at upstream defaults — the oracle's
native regime and the legacy panel's protocol). The pre-registered mode-0
default-path primary remains the analysis record and renders as the archived
variant ``--arm mode0`` → ``figS1_ires_panel_mode0.*``. Statistics from the
driver's ``summary.json`` (stratified bootstrap, 10,000 replicates, seed
20260825).

Figure revision 2026-08-27 (user-directed): Nature panel-style pass — the
in-figure title removed (the headline lives in the caption; panels carry
letters only, same as the fig2d revision) and nothing drawn above the axes;
every text element shares one font size and is uniform black; tick labels
trimmed (0 / 0.25 / 0.5 / 0.75 / 1); axes limits extended to ±0.03 so the
TPR = 1 band edge and the (1, 1) curve endpoint sit visibly inside the frame.
The legend (one column, two rows) and the AUROC/CI/P statistics share the
empty lower-right corner — the legend takes the lowest strip, the statistics
sit right-aligned above it — both placements verified clear of the CI band on
the full-resolution band grid for both arms (legend top 0.095 vs band floor
0.111 at its left edge in mode-0; every statistics line ends right of where
the band floor rises above it).

Data   : experiments/results/exp5_ires_panel/summary.json
Usage  : python experiments/plots/figS1_ires_panel.py [--arm mode0]
Output : experiments/plots/output/figS1_ires_panel.{pdf,png}   (mode-2 endpoint)
         experiments/plots/output/figS1_ires_panel_mode0.{pdf,png} (archived arm)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, WORKFLOW_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY = PROJECT_ROOT / "experiments" / "results" / "exp5_ires_panel" / "summary.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6           # single font size for every text element (Fig. 2 convention)
BLACK = "#000000"  # user directive 2026-08-27: all in-figure text uniform black

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": BLACK,
    "axes.edgecolor": BLACK,
    "axes.labelcolor": BLACK,
    "xtick.color": BLACK,
    "ytick.color": BLACK,
    "pdf.fonttype": 42,
})

CURVE = WORKFLOW_COLORS["ires_prediction"]  # warm grey — this workflow's colour
TICKS = [0, 0.25, 0.5, 0.75, 1.0]
TICK_LABELS = ["0", "0.25", "0.5", "0.75", "1"]


def main() -> int:
    arm = "mode0" if "--arm" in sys.argv and "mode0" in sys.argv else "mode2"
    if not SUMMARY.exists():
        print("summary.json missing — run experiments/exp5_ires_literature_panel.py --summary first")
        return 1
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    res = summary.get(f"results_{arm}") or {}
    if not res:
        print(f"summary.json has no results_{arm} block — complete that arm first")
        return 1

    fpr = [p[0] for p in res["roc_points"]]
    tpr = [p[1] for p in res["roc_points"]]
    grid = np.asarray(res["roc_fpr_grid"])
    lo = np.asarray(res["roc_band_tpr_lo"])
    hi = np.asarray(res["roc_band_tpr_hi"])
    auroc = res["point_auroc"]
    ci = res["auroc_ci95"]
    p = res.get("mannwhitney_p_two_sided")

    fig_w, fig_h = 88 / 25.4, 66 / 25.4  # single-column panel
    left, bottom, ax_w, ax_h = 0.40, 0.30, fig_w - 0.50, fig_h - 0.38
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([left / fig_w, bottom / fig_h, ax_w / fig_w, ax_h / fig_h])

    ax.plot([0, 1], [0, 1], color=NEUTRAL_GRID, lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax.fill_between(grid, lo, hi, facecolor=CURVE, alpha=0.38,
                    edgecolor="none", zorder=2,
                    label="95% CI band ($10^4$ bootstrap)")
    ax.plot(fpr, tpr, color=CURVE, lw=1.4, solid_joinstyle="round",
            zorder=3, label="IRES prediction workflow")

    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xticks(TICKS)
    ax.set_xticklabels(TICK_LABELS)
    ax.set_yticks(TICKS)
    ax.set_yticklabels(TICK_LABELS)
    ax.set_xlabel("False positive rate", fontsize=FONT, labelpad=2)
    ax.set_ylabel("True positive rate", fontsize=FONT, labelpad=2)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)

    # legend and statistics share the empty lower-right corner: the legend
    # takes the lowest strip (row tops stay below the band floor — 0.111 at
    # its left edge in mode-0), the statistics sit right-aligned above it
    leg = ax.legend(loc="lower right", ncol=1, bbox_to_anchor=(0.97, 0.03),
                    fontsize=FONT, handlelength=1.5, handletextpad=0.5,
                    labelspacing=0.35, borderaxespad=0, frameon=False)
    for t in leg.get_texts():
        t.set_color(BLACK)

    p_txt = "NA" if p is None else (f"P = {p:.1e}" if p < 1e-3 else f"P = {p:.3g}")
    ax.text(0.97, 0.16,
            f"AUROC = {auroc:.3f}\n95% CI {ci[0]:.2f}–{ci[1]:.2f}\n{p_txt}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=FONT, color=BLACK, linespacing=1.5)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = "figS1_ires_panel" if arm == "mode2" else "figS1_ires_panel_mode0"
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
