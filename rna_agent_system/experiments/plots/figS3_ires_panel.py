#!/usr/bin/env python3
"""Supplementary Fig. S3 — IRES anchor-set prediction: ROC curve with
bootstrap CI band.

Moved out of main Fig. 2 (where it was panel e) into the supplement on
2026-09-11 (user direction) and re-lettered S1 → S3 in the 2026-10-09
rotation; data, arm registration and rendering otherwise unchanged; the
panel script never drew a letter (panel letters are an assembler
responsibility), so the supplementary panel stands without one.

Threshold-free discrimination of the ``ires_prediction`` workflow on 9
literature IRES 5′UTRs vs 50 random human 5′UTR negatives (GENCODE v46).
**Figure endpoint (user re-registration 2026-08-26): the mode-2 sliding-window
scanning arm** (window 174 / step 50 at upstream defaults — the oracle's
native regime and the legacy panel's protocol). The pre-registered mode-0
default-path primary remains the analysis record and renders as the archived
variant ``--arm mode0`` → ``figS3_ires_panel_mode0.*``. Statistics from the
driver's ``summary.json`` (stratified bootstrap, 10,000 replicates, seed
20260825).

Figure revision 2026-08-27 (user-directed): Nature panel-style pass — the
in-figure title removed (the headline lives in the caption; panels carry
letters only, same as the fig2d revision) and nothing drawn above the axes;
every text element shares one font size and is uniform black; tick labels
trimmed (0 / 0.25 / 0.5 / 0.75 / 1); axes limits extended to ±0.03 so the
TPR = 1 band edge and the (1, 1) curve endpoint sit visibly inside the frame.

Figure revision 2026-10-09 (user-directed, seven-point pass): (i) all
in-figure text uniform black re-verified, wording checked against
Supplementary Note 2 (legend keeps the registered "IRES prediction workflow"
form; no self-made hyphenated compounds); (ii) no title drawn inside the
figure, Nature panel convention, unchanged; (iii) axis labels kept at the
standard ROC forms "False positive rate" / "True positive rate"; (iv) the
canvas is now exact-millimetre 89 × 66 mm saved at exactly 1,200 dpi with a
vector PDF twin (the figS1/figS2 house convention, replacing the earlier
tight-crop save); (v) no biological proper nouns appear in the panel (IRES
is defined at first use in Supplementary Note 2); (vi) the legend
parenthetical retired — "95% CI band ($10^4$ bootstrap)" becomes "95% CI
band" (the 10,000-replicate count stays carried by the main-text Statistical
analysis); (vii) the statistics block reduced to the AUROC point value only
(the 95% CI and the two-sided Mann–Whitney P remain carried verbatim for both
arms in Supplementary Note 2). The AUROC value is asserted against the
registered numbers (mode 2 0.673, mode 0 0.478). Placement follow-up the
same day (user direction): the AUROC line moved to the empty top-left
corner, left-aligned, in both arms; the legend stays in the lower-right
corner. Geometric guards: both boxes stay inside the axes bounding box, the
legend clears the CI band and the ROC curve from below over its full x-span,
the AUROC line clears them from above over its full x-span, and the two
boxes stay clear of each other.

Data   : experiments/results/exp5_ires_panel/summary.json
Usage  : python experiments/plots/figS3_ires_panel.py [--arm mode0]
Output : experiments/plots/output/figS3_ires_panel.{pdf,png}   (mode-2 endpoint)
         experiments/plots/output/figS3_ires_panel_mode0.{pdf,png} (archived arm)
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
BLACK = "#000000"  # all in-figure text uniform black

W_MM, H_MM = 89.0, 66.0                          # exact canvas (figS1/figS2 convention)
DPI = 1200                                        # Nature Methods line-art minimum
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)
AX_L, AX_BOT = 11.0, 8.5                          # axes margins in mm
AX_R, AX_TOP = 4.0, 4.0
AX_W, AX_H = W_MM - AX_L - AX_R, H_MM - AX_BOT - AX_TOP

# Registered AUROC point values (Supplementary Note 2 carries them verbatim;
# the render asserts against drift between summary.json and the paper text).
EXPECT_AUROC = {"mode2": 0.673, "mode0": 0.478}
CLEAR_MARGIN = 0.01  # data units of clearance required below band/curve

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

    if abs(auroc - EXPECT_AUROC[arm]) >= 5e-4:
        print(f"AUROC {auroc:.3f} disagrees with the Supplementary Note 2 "
              f"registered value {EXPECT_AUROC[arm]:.3f} for arm {arm}")
        return 1

    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9), facecolor="white")
    ax = fig.add_axes([AX_L / W_MM, AX_BOT / H_MM, AX_W / W_MM, AX_H / H_MM])

    ax.plot([0, 1], [0, 1], color=NEUTRAL_GRID, lw=0.7, ls=(0, (4, 3)), zorder=1)
    ax.fill_between(grid, lo, hi, facecolor=CURVE, alpha=0.38,
                    edgecolor="none", zorder=2, label="95% CI band")
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

    # legend in the empty lower-right corner (band floor at chance in
    # mode-0; the band hugs the top edge by FPR 0.85 in both arms), AUROC
    # value in the empty top-left corner (band ceiling stays below 0.78 out
    # to FPR 0.2 in mode-2, the tighter arm)
    leg = ax.legend(loc="lower right", ncol=1, bbox_to_anchor=(0.97, 0.03),
                    fontsize=FONT, handlelength=1.5, handletextpad=0.5,
                    labelspacing=0.35, borderaxespad=0, frameon=False)
    for t in leg.get_texts():
        t.set_color(BLACK)

    stats = ax.text(0.03, 0.97, f"AUROC = {auroc:.3f}",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=FONT, color=BLACK)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    leg_bb = leg.get_window_extent(renderer)
    stats_bb = stats.get_window_extent(renderer)

    # --- geometric guards -------------------------------------------------
    # band/curve envelopes on a dense grid: the legend must clear both from
    # below, the AUROC line (top-left) from above
    fine = np.linspace(0.0, 1.0, 2001)
    floor_env = np.minimum(np.interp(fine, grid, lo), np.interp(fine, fpr, tpr))
    ceil_env = np.maximum(np.interp(fine, grid, hi), np.interp(fine, fpr, tpr))
    inv = ax.transData.inverted()

    problems = []
    if (stats_bb.x1 >= leg_bb.x0 and stats_bb.y0 <= leg_bb.y1
            and stats_bb.x0 <= leg_bb.x1 and stats_bb.y1 >= leg_bb.y0):
        problems.append("AUROC line box overlaps the legend box")
    for name, bb, side in (("legend", leg_bb, "below"),
                           ("AUROC line", stats_bb, "above")):
        (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        if not (x0 >= -0.03 and x1 <= 1.03 and y0 >= -0.03 and y1 <= 1.03):
            problems.append(f"{name} box leaves the axes bounding box")
        span = fine[(fine >= x0) & (fine <= x1)]
        if span.size:
            if side == "below":
                floor = floor_env[(fine >= x0) & (fine <= x1)].min()
                if y1 > floor - CLEAR_MARGIN:
                    problems.append(f"{name} top {y1:.3f} not clear of "
                                    f"band/curve floor {floor:.3f}")
            else:
                ceil = ceil_env[(fine >= x0) & (fine <= x1)].max()
                if y0 < ceil + CLEAR_MARGIN:
                    problems.append(f"{name} bottom {y0:.3f} not clear of "
                                    f"band/curve ceiling {ceil:.3f}")
    if problems:
        for msg in problems:
            print(f"[guard] FAIL {msg}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = "figS3_ires_panel" if arm == "mode2" else "figS3_ires_panel_mode0"
    fig.savefig(OUT_DIR / f"{stem}.pdf", format="pdf", facecolor="white")
    fig.savefig(OUT_DIR / f"{stem}.png", format="png", dpi=DPI, facecolor="white")
    print(f"written {OUT_DIR / (stem + '.pdf')} and .png "
          f"({W_PX}x{H_PX} px at {DPI} dpi, {W_MM:.0f}x{H_MM:.0f} mm; "
          f"arm {arm}: AUROC {auroc:.3f}, CI {ci[0]:.3f}-{ci[1]:.3f}, "
          f"P {p:.3g} — CI/P stay figure-free, carried in Note 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
