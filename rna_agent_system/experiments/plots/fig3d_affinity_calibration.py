#!/usr/bin/env python3
"""Fig. 3d — EGARPS affinity calibration at anchor-set scale (single-panel scatter).

The panel: Kd-vs-score scatter for every anchor-set binder with a measured
Kd (log Kd vs log native probability; all 62 Kd binders — the x-range
extends to 1.2e3 nM so the three IFN-gamma family members at Kd 440–914 nM
are on-panel).  The six-point thrombin Kd anchors are emphasized (ink-black
rings) with a ringed-marker legend entry in the empty head band above the
data (carrying its rho stat); pegaptanib is annotated (the marketed binder
that scores near 1e-6 — the per-entry inversion that survives scale,
against scrambled TBA near 0.98).

The companion class-separation view (binders vs literature negatives vs
random-sequence negatives on the same score axis) is NOT shown: its content
is text-reported instead (round 7, user-directed) — the pooled
binder-vs-negative AUROC (0.52, CI 0.39–0.65, 62 vs 28 — the registered P2
Kd-binder convention) and the three-class medians (0.22 / 1.4e-3 /
2.2e-2) live in the Fig-3d caption and the main text, and the screening
failure is shown systematically in Fig. 3a.

Chart type: Kd scatter (single panel), registered in
FIGURE_PLAN_V5.md row 3e.

Colours (palette rev 7): binders terracotta (the EGARPS oracle colour used
across Fig. 3); thrombin-series emphasis ring in ink black; every text
element one 6-pt ink-black style.  No in-figure titles (Nature convention —
panels are lettered at composite assembly, the headline lives in the
caption).  PNG saved at 1200 dpi (Nature Methods line-art guidance).

2026-08-29 user-directed revisions: (round 1) legend recentred under the
whole figure (was clipped at the figure edge under the right panel),
ridgelines spread across the panel (were squashed into the left half),
stat annotations moved off the data (thrombin rho into the head band,
pooled AUROC into the caption), pegaptanib callout repositioned clear of
points, x-range extended to cover all 62 Kd binders, 1200-dpi PNG;
(round 2) one-sided ridges replaced by mirrored density violins (the
half-violin look read as odd for three side-by-side groups — same data,
same Scott-bandwidth KDE, mirrored), the separate legend row dropped in
favour of direct group labels under each violin, the pegaptanib leader
shortened so it cannot read as a trend line; (round 3) violin KDEs
truncated at the probability boundary (score = 1) so the right panel gains
an empty head band, and the pooled-AUROC stat restored on-panel there;
(round 4) the pooled-AUROC stat taken back off the panel — its 62-vs-28
basis (the registered P2 Kd-binder convention) read as inconsistent with
the 67/11/17 group labels, and the number with CI and composition lives in
the caption and main text — and the ordinate marked directly on the right
panel instead (y tick labels + major gridlines extended across the
violins); (round 5) the thrombin head-band label replaced by a proper
ringed-marker legend entry so the ink-ringed points are self-explanatory;
(round 6) density violins replaced by jittered column scatter with median
ticks — at n = 11–67 over a nine-order log range a density curve implies
structure that is not in the data, and showing every point is the honest
rendering (it also rhymes with the left panel's dots on the shared axis);
(round 7) the class-distribution panel dropped altogether — the figure is
now the single Kd–score scatter; the class-separation evidence (pooled
AUROC + three-class medians) is text-reported in the caption and main text,
and the screening failure is shown systematically in Fig. 3a.
2026-10-02 revision (Fig. 3 text-sync batch, user-adjudicated): the legend
entry reworded "thrombin series" to "thrombin Kd anchors" (the anchors
vocabulary, body §2.3 synced the same day) and wrapped to two lines; the
canvas narrowed to 57.2 mm so d, e and f share one three-column row (the
user-directed 2026-10-02 layout; fonts unchanged 6-pt, no data change).

Data  : experiments/results/exp13_affinity_calibration/{records.jsonl,summary.json}
Usage : python experiments/plots/fig3d_affinity_calibration.py
Output: experiments/plots/output/fig3d_affinity_calibration.{pdf,png}
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
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp13_affinity_calibration"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6          # single font size for every in-figure text element
C_BINDER = PALETTE_BY_NAME["terracotta"]      # #C08B7C
EMPH_EDGE = TEXT

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "axes.labelcolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2,
    "ytick.major.size": 2,
    "pdf.fonttype": 42,
})


def load_records() -> list[dict]:
    recs = [json.loads(l) for l in (RESULTS_DIR / "records.jsonl").read_text().splitlines()
            if l.strip()]
    ok = [r for r in recs if r["success"] and r["raw"]["egarps_native_probability"] is not None]
    return ok


def main() -> int:
    records = load_records()
    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    thr = summary["thrombin_series"]

    binders_kd = [r for r in records if r["role"] == "binder" and r["kd_nm"]]
    thr_ids = {p["id"] for p in thr["points"]}
    thr_pts = [r for r in binders_kd if r["id"] in thr_ids]
    other_pts = [r for r in binders_kd if r["id"] not in thr_ids]
    np_all = np.array([r["raw"]["egarps_native_probability"] for r in records])
    ymin = np.floor(np.log10(np_all[np_all > 0].min())) - 0.5
    ymax = 1.2  # head band above the data (max score 1.0) for the legend —
    # 2026-10-02: raised from 0.9 so the single-line legend entry clears the
    # topmost (score ≈ 1) points at the narrowed 45-mm axes width

    fig_w, fig_h = 55.8 / 25.4, 44.0 / 25.4  # inches (2026-10-02 second
    # pass: 57.2 → 55.8 mm, tracking the composite's narrowed three-column
    # width; fonts unchanged 6-pt, no data change)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_s = fig.add_axes([10.5 / 55.8, 10.0 / 44.0, 43.8 / 55.8, 32.0 / 44.0])

    # ── left: Kd–score scatter ──────────────────────────────────────────────
    ax_s.scatter([r["kd_nm"] for r in other_pts],
                 [r["raw"]["egarps_native_probability"] for r in other_pts],
                 s=9, facecolor=C_BINDER, edgecolor="none", alpha=0.85, zorder=4)
    ax_s.scatter([r["kd_nm"] for r in thr_pts],
                 [r["raw"]["egarps_native_probability"] for r in thr_pts],
                 s=16, facecolor=C_BINDER, edgecolor=EMPH_EDGE, linewidth=0.6,
                 zorder=5)

    peg = next(r for r in binders_kd if r["id"] == "pegaptanib_vegf")
    ax_s.annotate("pegaptanib",
                  xy=(peg["kd_nm"], peg["raw"]["egarps_native_probability"]),
                  xytext=(0.15, peg["raw"]["egarps_native_probability"]),
                  textcoords="data",
                  fontsize=FONT, color=TEXT, ha="left", va="center",
                  arrowprops=dict(arrowstyle="-", linewidth=0.5, color=TEXT,
                                  shrinkA=1.5, shrinkB=1.5))

    ax_s.set_xscale("log")
    ax_s.set_yscale("log")
    ax_s.set_xlim(0.02, 1200)
    ax_s.set_ylim(10**ymin, 10**ymax)
    ax_s.set_xlabel("Measured K$_d$ (nM)", fontsize=FONT, labelpad=2)
    ax_s.set_ylabel("EGARPS+ native probability", fontsize=FONT, labelpad=2)
    ax_s.tick_params(labelsize=FONT, pad=1.5)
    ax_s.grid(True, which="major", axis="both", color=NEUTRAL_GRID, linewidth=0.4,
              zorder=0)
    # ringed-marker legend entry: explains the ink-black ringed points
    # (the pre-registered thrombin Kd series) and carries its rho stat
    from matplotlib.lines import Line2D
    thr_handle = Line2D([0], [0], marker="o", linestyle="None",
                        markerfacecolor=C_BINDER, markeredgecolor=EMPH_EDGE,
                        markeredgewidth=0.6, markersize=4,
                        label=(f"thrombin Kd anchors ρ = "
                               f"{thr['spearman_rho_vs_neglog_kd']:+.2f} "
                               f"(n = {thr['n_points']})"))
    ax_s.legend(handles=[thr_handle], loc="upper left",
                bbox_to_anchor=(0.015, 1.0), frameon=False, fontsize=FONT,
                handletextpad=0.35, borderaxespad=0.1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3d_affinity_calibration.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
