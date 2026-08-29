#!/usr/bin/env python3
"""Fig. 3e — EGARPS affinity calibration at anchor-set scale (scatter + ridgeline).

Left axes: Kd-vs-score scatter for every anchor-set binder with a measured
Kd (log Kd vs log native probability); the six-point thrombin series is
emphasized and carries the within-target Spearman ρ annotation; pegaptanib
is annotated (the marketed binder that scores near 1e-6 — the per-entry
inversion that survives scale, against scrambled TBA near 0.98).

Right axes (shared log-score y-axis): horizontal ridgeline densities of the
three pre-registered groups — binders, literature negatives and the
random-sequence negative class — all three spanning the full nine-order
score range with interleaved medians: no separation (pooled AUROC ≈ chance,
the retained P2 pilot's below-chance 0.356 not surviving scale).  Pooled
binder-vs-negative AUROC annotated (the retained P2 framing, gate 0.8).

Chart type: Kd scatter + ridgeline densities, registered in
FIGURE_PLAN_V5.md row 3e (user-directed 2026-08-28; ridgeline style after
the SeFMol Fig. 3d convention).

Colours (palette rev 7): binders terracotta (the EGARPS oracle colour used
across Fig. 3), literature negatives slate blue, random-sequence negatives
sand; thrombin-series emphasis ring in ink black; all text one 6-pt
ink-black style (no in-figure title, Nature convention).

Data  : experiments/results/exp13_affinity_calibration/{records.jsonl,summary.json}
Usage : python experiments/plots/fig3e_affinity_calibration.py
Output: experiments/plots/output/fig3e_affinity_calibration.{pdf,png}
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

C_BINDER = PALETTE_BY_NAME["terracotta"]      # #C08B7C
C_LITNEG = PALETTE_BY_NAME["slate_blue"]      # #6B7B8D
C_RANDNEG = PALETTE_BY_NAME["sand"]           # #D9C3A9
EMPH_EDGE = TEXT

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 6,
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


def kde_curve(values: np.ndarray, grid: np.ndarray, scale: float | None = None):
    """Gaussian KDE on log10 scores evaluated on `grid`; peak height
    normalized to `scale` (ridgeline row height) when given."""
    from scipy.stats import gaussian_kde

    kde = gaussian_kde(values)  # Scott's rule bandwidth (registered convention)
    dens = kde(grid)
    if scale is not None and dens.max() > 0:
        dens = dens / dens.max() * scale
    return dens


def main() -> int:
    records = load_records()
    summary = json.loads((RESULTS_DIR / "summary.json").read_text())
    thr = summary["thrombin_series"]
    pooled = summary["pooled_binder_vs_negative"]["egarps_native_probability"]

    binders_kd = [r for r in records if r["role"] == "binder" and r["kd_nm"]]
    thr_ids = {p["id"] for p in thr["points"]}
    thr_pts = [r for r in binders_kd if r["id"] in thr_ids]
    other_pts = [r for r in binders_kd if r["id"] not in thr_ids]
    lit_neg = [r for r in records if r["role"] == "negative" and not r.get("random_negative")]
    rand_neg = [r for r in records if r.get("random_negative")]

    np_all = np.array([r["raw"]["egarps_native_probability"] for r in records])
    ymin = np.floor(np.log10(np_all[np_all > 0].min())) - 0.5
    ymax = 0.3

    fig_w, fig_h = 7.16, 2.5  # inches (~183 mm double-column, panel e)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_s = fig.add_axes([0.085, 0.20, 0.485, 0.72])
    ax_r = fig.add_axes([0.615, 0.20, 0.33, 0.72], sharey=ax_s)

    # ── left: Kd–score scatter ───────────────────────────────────────────────
    xs_other = [r["kd_nm"] for r in other_pts]
    ys_other = [r["raw"]["egarps_native_probability"] for r in other_pts]
    ax_s.scatter(xs_other, ys_other, s=9, facecolor=C_BINDER, edgecolor="none",
                 alpha=0.85, zorder=4)
    ax_s.scatter([r["kd_nm"] for r in thr_pts],
                 [r["raw"]["egarps_native_probability"] for r in thr_pts],
                 s=16, facecolor=C_BINDER, edgecolor=EMPH_EDGE, linewidth=0.6,
                 zorder=5)

    peg = next(r for r in binders_kd if r["id"] == "pegaptanib_vegf")
    ax_s.annotate("pegaptanib", xy=(peg["kd_nm"], peg["raw"]["egarps_native_probability"]),
                  xytext=(2.0, 1.5e-7), fontsize=6, color=TEXT,
                  arrowprops=dict(arrowstyle="-", linewidth=0.5, color=TEXT))

    ax_s.set_xscale("log")
    ax_s.set_yscale("log")
    ax_s.set_xlim(0.02, 400)
    ax_s.set_ylim(10**ymin, 10**ymax)
    ax_s.set_xlabel("Measured K$_d$ (nM)", fontsize=6, labelpad=2)
    ax_s.set_ylabel("EGARPS+ native probability", fontsize=6, labelpad=2)
    ax_s.tick_params(labelsize=6, pad=1.5)
    ax_s.grid(True, which="major", axis="both", color=NEUTRAL_GRID, linewidth=0.4,
              zorder=0)
    ax_s.text(0.97, 0.96,
              f"thrombin series ρ = {thr['spearman_rho_vs_neglog_kd']:+.2f} (n = {thr['n_points']})",
              transform=ax_s.transAxes, fontsize=6, color=TEXT, va="top", ha="right")

    # ── right: horizontal ridgeline (shared log-score axis) ─────────────────
    grid = np.linspace(ymin, ymax, 400)
    binders_all = [r for r in records if r["role"] in ("binder", "binder_no_kd")]
    rows = [
        ("Binders (all targets)", binders_all, C_BINDER, 0.15),
        ("Literature negatives", lit_neg, C_LITNEG, 1.35),
        ("Random sequences", rand_neg, C_RANDNEG, 2.55),
    ]
    row_h = 0.75
    from matplotlib.patches import Patch
    handles = []
    for label, grp, colour, base in rows:
        vals = np.log10([r["raw"]["egarps_native_probability"] for r in grp
                         if r["raw"]["egarps_native_probability"] > 0])
        dens = kde_curve(vals, grid, scale=row_h)
        ax_r.fill_betweenx(10**grid, base, base + dens, facecolor=colour,
                           edgecolor=TEXT, linewidth=0.4, alpha=0.9, zorder=3)
        ax_r.axvline(base, color=NEUTRAL_GRID, linewidth=0.4, zorder=1)
        handles.append(Patch(facecolor=colour, edgecolor=TEXT, linewidth=0.4,
                             label=f"{label} (n = {len(grp)})"))
    ax_r.set_xlim(0, 6.4)
    ax_r.set_ylim(10**ymin, 10**ymax)
    ax_r.set_xticks([])
    ax_r.tick_params(labelleft=False, labelsize=6)
    ax_r.set_xlabel("Density", fontsize=6, labelpad=2)
    for spine in ("top", "right"):
        ax_r.spines[spine].set_visible(False)
    ax_r.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
                ncol=3, frameon=False, fontsize=6, handlelength=1.0,
                handleheight=0.8, columnspacing=1.0, handletextpad=0.4)
    ax_r.text(0.98, 0.97,
              f"pooled AUROC = {pooled['auroc']:.2f} "
              f"({pooled['n_binders']} vs {pooled['n_negatives']})",
              transform=ax_r.transAxes, fontsize=6, color=TEXT, va="top", ha="right")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3e_affinity_calibration.{ext}"
        fig.savefig(out, format=ext, dpi=600, facecolor="white")
        print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
