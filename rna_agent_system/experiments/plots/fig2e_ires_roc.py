#!/usr/bin/env python3
"""Fig. 2e — IRES literature-panel prediction: ROC curve with bootstrap CI band.

Threshold-free discrimination of the ``ires_prediction`` workflow on 9
literature IRES 5′UTRs vs 50 random human 5′UTR negatives (GENCODE v46).
**Figure endpoint (user re-registration 2026-08-26): the mode-2 sliding-window
scanning arm** (window 174 / step 50 at upstream defaults — the oracle's
native regime and the legacy panel's protocol). The pre-registered mode-0
default-path primary remains the analysis record and renders as the archived
variant ``--arm mode0`` → ``fig2e_ires_roc_mode0.*``. Statistics from the
driver's ``summary.json`` (stratified bootstrap, 10,000 replicates, seed
20260825).

Data   : experiments/results/exp5_ires_panel/summary.json
Usage  : python experiments/plots/fig2e_ires_roc.py [--arm mode0]
Output : experiments/plots/output/fig2e_ires_roc.{pdf,png}   (mode-2 endpoint)
         experiments/plots/output/fig2e_ires_roc_mode0.{pdf,png} (archived arm)
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
from palette import NEUTRAL_GRID, TEXT, WORKFLOW_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SUMMARY = PROJECT_ROOT / "experiments" / "results" / "exp5_ires_panel" / "summary.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

CURVE = WORKFLOW_COLORS["ires_prediction"]  # warm grey — this workflow's colour


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
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.16, 0.15, 0.70, 0.68])

    ax.plot([0, 1], [0, 1], color=NEUTRAL_GRID, lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax.fill_between(grid, lo, hi, facecolor=CURVE, alpha=0.38,
                    edgecolor="none", zorder=2,
                    label="95% CI band ($10^4$ bootstrap)")
    ax.plot(fpr, tpr, color=CURVE, lw=1.4, solid_joinstyle="round",
            zorder=3, label="IRES prediction workflow")

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("False-positive rate", fontsize=6, labelpad=2)
    ax.set_ylabel("True-positive rate", fontsize=6, labelpad=2)
    ax.set_title("IRES literature panel — threshold-free ROC"
                 + ("" if arm == "mode2" else " (full-sequence default arm)"),
                 loc="left", fontsize=6.5, pad=14)

    p_txt = "NA" if p is None else (f"P = {p:.1e}" if p < 1e-3 else f"P = {p:.3g}")
    ax.text(0.98, 0.05,
            f"AUROC = {auroc:.3f}\n(95% CI {ci[0]:.2f}–{ci[1]:.2f}; {p_txt})\n"
            f"n = {summary['panel'][f'positives_scored_{arm}']} IRES / "
            f"{summary['panel'][f'negatives_scored_{arm}']} 5′UTR",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=5.4,
            color="#444444", linespacing=1.5)

    leg = ax.legend(loc="upper left", fontsize=5.2, handlelength=1.6,
                    frameon=False, borderaxespad=0.2, labelspacing=0.35)
    leg.get_frame().set_linewidth(0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = "fig2e_ires_roc" if arm == "mode2" else "fig2e_ires_roc_mode0"
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
