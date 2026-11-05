#!/usr/bin/env python3
"""Figs. 2b & 2c — CDS null model: designed vs wild-type vs random-synonymous.

2b: CAI per arm (violin + jitter; medians marked and printed above each arm,
    n carried by the tick labels; pairwise Mann–Whitney P and Cliff's δ live
    in the manuscript legend, not on the panel — Nature panel style).
2c: folding energy per nucleotide per arm (same geometry; more negative =
    more structured; the panel spells out the manuscript's "folding energy
    per nucleotide" — the MFE abbreviation lives in the SI only).

Data  : experiments/results/exp2_cds_nulls/fig2_cds_nulls.jsonl
        (+ summary.json for the annotated statistics)

Geometry (2026-10-10, user-directed three-column relayout of the Fig. 2
composite): exact 57 x 57 mm canvas (no tight crop), absolute-mm axes
placement shared with panels d–g so the three-per-row panels align (axes
bottom 12 mm, top 3 mm, left 12 mm); the random-synonymous arm's tick
label wraps to four lines — same words, rewrapped — because the
three-column width cannot carry it on one line beside its neighbours'
labels; the 6-pt text scale is unchanged (no panel is scaled at assembly).

Usage : python experiments/plots/fig2bc_cds_nulls.py
Output : experiments/plots/output/fig2b_cai.{pdf,png}
         experiments/plots/output/fig2c_mfe_per_nt.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.stats import gaussian_kde  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import ARM_COLORS, NEUTRAL_GRID, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp2_cds_nulls"
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

ARMS = ["designed", "wt", "random"]
ARM_LABELS = {"designed": "Designed", "wt": "Wild type", "random": "Random synonymous sequences"}
# Tick-label wraps at the three-column width: the random arm's two-line
# label ("Random synonymous sequences" on one line) is wider than the
# arm pitch, so it wraps further; the words are the manuscript's own.
ARM_TICK_WRAP = {
    "designed": ("Designed", "(n = {n})"),
    "wt": ("Wild type", "(n = {n})"),
    "random": ("Random", "synonymous", "sequences", "(n = {n})"),
}

# Shared three-column geometry (panels b–g, 2026-10-10): exact canvas,
# axes placed in absolute mm so every panel in a composite row aligns.
W_MM, H_MM = 57.0, 57.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)
AX_L, AX_BOT, AX_R, AX_TOP = 12.0, 12.0, 2.0, 3.0


def load_records() -> list[dict]:
    recs: dict[str, dict] = {}
    path = RESULTS_DIR / "fig2_cds_nulls.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("success"):
            recs[f"{rec['arm']}:{rec['target_id']}:{rec.get('draw')}"] = rec
    return list(recs.values())


def load_summary() -> dict:
    p = RESULTS_DIR / "summary.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def violin_jitter(ax, data: list[np.ndarray], stats: dict) -> None:
    """One violin+jitter panel; `stats` is summary.json[metric] (n per arm)."""
    n = len(ARMS)
    rng = np.random.default_rng(0)

    # KDE violins. The evaluation grid extends three bandwidths past the data
    # extremes so the density tapers to zero instead of ending in a chopped
    # edge at the sample min/max.
    tops: list[float] = []
    bottoms: list[float] = []
    for i, vals in enumerate(data):
        color = ARM_COLORS[ARMS[i]]
        xs = np.asarray(vals, dtype=float)
        if len(vals) >= 8:
            kde = gaussian_kde(vals)
            bw = float(kde.factor) * float(np.std(vals, ddof=1))
            pad = max(3.0 * bw, 0.02 * float(np.ptp(vals)))
            xs = np.linspace(vals.min() - pad, vals.max() + pad, 300)
            dens = kde(xs)
            dens = dens / dens.max() * 0.34
            ax.fill_betweenx(xs, i + 1 - dens, i + 1 + dens,
                             facecolor=color, alpha=0.55, edgecolor=color, linewidth=0.6)
        tops.append(float(xs.max()))
        bottoms.append(float(xs.min()))
        # jitter points
        jit = rng.uniform(-0.16, 0.16, size=len(vals))
        marker_size = 4.0 if len(vals) <= 20 else 2.4
        alpha = 0.9 if len(vals) <= 20 else 0.55
        ax.scatter(i + 1 + jit, vals, s=marker_size, c=TEXT, alpha=alpha,
                   linewidths=0, zorder=4)
        # median marker
        med = float(np.median(vals))
        ax.hlines(med, i + 1 - 0.38, i + 1 + 0.38, colors=TEXT, linewidth=1.0, zorder=5)

    # Symmetric margins: identical gaps between arms and to the axes edges.
    ax.set_xlim(0.45, n + 0.55)
    yr = float(max(tops) - min(bottoms)) or 1.0
    ax.set_ylim(min(bottoms) - 0.04 * yr, max(tops) + 0.16 * yr)

    ax.set_xticks(range(1, n + 1))
    tick_labels = []
    for i, a in enumerate(ARMS):
        arm_n = stats.get("arms", {}).get(a, {}).get("n", len(data[i]))
        tick_labels.append("\n".join(line.format(n=arm_n)
                                     for line in ARM_TICK_WRAP[a]))
    ax.set_xticklabels(tick_labels)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=6, length=1.5, pad=1.5)

    # Median value centred above each violin — clear of every drawn element.
    # (\u2212 matches the tick labels' minus sign.)
    for i, vals in enumerate(data):
        label = f"{np.median(vals):.3f}".replace("-", "\u2212")
        ax.text(i + 1, tops[i] + 0.02 * yr, label,
                ha="center", va="bottom", fontsize=6, color=TEXT, zorder=6,
                bbox=dict(facecolor="white", edgecolor="none",
                          alpha=0.85, pad=0.5))


def draw(values_by_arm: dict[str, np.ndarray],
         stats: dict, ylabel: str, stem: str) -> int:
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9),
                     facecolor="white")
    ax = fig.add_axes([(AX_L / W_MM), (AX_BOT / H_MM),
                       ((W_MM - AX_L - AX_R) / W_MM),
                       ((H_MM - AX_BOT - AX_TOP) / H_MM)])
    data = [values_by_arm[a] for a in ARMS]
    violin_jitter(ax, data, stats)
    ax.set_ylabel(ylabel, fontsize=6, labelpad=2)

    # Guards (house convention): neighbouring tick labels must not touch,
    # and the rotated ylabel must fit the axes height (plus the small
    # symmetric overhang the top/bottom margins can host).
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [lbl.get_window_extent(renderer) for lbl in ax.get_xticklabels()]
    for b1, b2 in zip(boxes, boxes[1:]):
        if b1.x1 >= b2.x0 - 2.0:  # >=2 px (~0.5 mm) clearance at draw dpi
            raise AssertionError(
                f"{stem}: x-tick labels collide ({b1.x1:.0f} >= {b2.x0:.0f} px)")
    yl_box = ax.yaxis.label.get_window_extent(renderer)
    ax_box = ax.get_window_extent(renderer)
    overhang = (yl_box.height - ax_box.height) / 2.0
    if overhang > 2.0 / 25.4 * fig.dpi:  # 2 mm of margin on each side
        raise AssertionError(
            f"{stem}: rotated ylabel {yl_box.height / fig.dpi * 25.4:.1f} mm "
            f"exceeds the axes plus margin budget")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(out, format=ext, dpi=DPI if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    return 0


def main() -> int:
    records = load_records()
    if not records:
        print("no scoring records found — run experiments/exp2_cds_null_model.py first")
        return 1
    summary = load_summary()

    by_arm: dict[str, list[float]] = {a: [] for a in ARMS}
    by_arm_mfe: dict[str, list[float]] = {a: [] for a in ARMS}
    for r in records:
        if r.get("cai_score") is not None:
            by_arm[r["arm"]].append(float(r["cai_score"]))
        if r.get("mfe_per_nt") is not None:
            by_arm_mfe[r["arm"]].append(float(r["mfe_per_nt"]))

    cai_arrays = {a: np.array(v, dtype=float) for a, v in by_arm.items()}
    mfe_arrays = {a: np.array(v, dtype=float) for a, v in by_arm_mfe.items()}

    rc = draw(cai_arrays, summary.get("cai", {}), "CAI", "fig2b_cai")
    rc += draw(mfe_arrays, summary.get("mfe_per_nt", {}),
               "Folding energy per nucleotide (kcal/mol/nt)", "fig2c_mfe_per_nt")
    for a in ARMS:
        print(f"{a:8s} CAI n={len(cai_arrays[a]):3d} "
              f"median={np.median(cai_arrays[a]) if len(cai_arrays[a]) else float('nan'):.4f}   "
              f"MFE/nt n={len(mfe_arrays[a]):3d} "
              f"median={np.median(mfe_arrays[a]) if len(mfe_arrays[a]) else float('nan'):.4f}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
