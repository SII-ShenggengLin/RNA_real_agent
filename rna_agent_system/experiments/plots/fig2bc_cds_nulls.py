#!/usr/bin/env python3
"""Figs. 2b & 2c — CDS null model: designed vs wild-type vs random-synonymous.

2b: CAI per arm (violin + jitter; medians marked, pairwise Mann–Whitney P and
    Cliff's δ annotated).
2c: MFE/nt per arm (same geometry; more negative = more structured).

Data  : experiments/results/exp2_cds_nulls/fig2_cds_nulls.jsonl
        (+ summary.json for the annotated statistics)

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
ARM_LABELS = {"designed": "Designed", "wt": "Wild-type", "random": "Random synonymous"}


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


def fmt_p(p: float | None) -> str:
    if p is None:
        return "NA"
    return f"P = {p:.1e}".replace("e-0", "e-").replace("e-0", "e-") if p < 1e-3 else f"P = {p:.3g}"


def violin_jitter(ax, data: list[np.ndarray], metric: str, stats: dict) -> None:
    """One violin+jitter panel; `stats` is summary.json[metric]."""
    n = len(ARMS)
    rng = np.random.default_rng(0)

    # KDE violins (bandwidth-scott via gaussian_kde; mirrored densities)
    for i, vals in enumerate(data):
        color = ARM_COLORS[ARMS[i]]
        if len(vals) >= 8:
            kde = gaussian_kde(vals)
            span = np.ptp(vals)
            xs = np.linspace(vals.min() - 0.02 * span - 1e-6,
                             vals.max() + 0.02 * span + 1e-6, 240)
            dens = kde(xs)
            dens = dens / dens.max() * 0.34
            ax.fill_betweenx(xs, i + 1 - dens, i + 1 + dens,
                             facecolor=color, alpha=0.55, edgecolor=color, linewidth=0.6)
        # jitter points
        jit = rng.uniform(-0.16, 0.16, size=len(vals))
        marker_size = 4.0 if len(vals) <= 20 else 2.4
        alpha = 0.9 if len(vals) <= 20 else 0.55
        ax.scatter(i + 1 + jit, vals, s=marker_size, c=TEXT, alpha=alpha,
                   linewidths=0, zorder=4)
        # median marker
        med = float(np.median(vals))
        ax.hlines(med, i + 1 - 0.38, i + 1 + 0.38, colors=TEXT, linewidth=1.0, zorder=5)
        arm_n = stats.get("arms", {}).get(ARMS[i], {}).get("n", len(vals))
        ax.annotate(f"{med:.3f}\nn = {arm_n}", (i + 1, med),
                    xytext=(14, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=5.2, zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none",
                              alpha=0.75, pad=0.6))

    ax.set_xlim(0.45, n + 0.55 + 0.85)  # right margin for median labels
    ax.set_xticks(range(1, n + 1))
    ax.set_xticklabels([ARM_LABELS[a] for a in ARMS], fontsize=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)

    # pairwise stats strip under the title
    pairs = [("designed", "wt"), ("wt", "random"), ("designed", "random")]
    labels = []
    for a, b in pairs:
        st = stats.get(f"{a}_vs_{b}") or {}
        if "mannwhitney_p" in st:
            labels.append(f"{ARM_LABELS[a].split()[0]}–{ARM_LABELS[b].split()[0]}: "
                          f"{fmt_p(st['mannwhitney_p'])}, δ = {st['cliffs_delta']:+.2f}")
    for j, lab in enumerate(labels):
        ax.text(0.0, 1.035 - j * 0.085, lab, transform=ax.transAxes,
                ha="left", va="bottom", fontsize=5.2, color="#444444")


def draw(metric_key: str, values_by_arm: dict[str, np.ndarray],
         stats: dict, ylabel: str, title: str, stem: str) -> int:
    fig_w, fig_h = 88 / 25.4, 66 / 25.4  # single-column panel
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.155, 0.135, 0.72, 0.70])
    data = [values_by_arm[a] for a in ARMS]
    violin_jitter(ax, data, metric_key, stats)
    ax.set_ylabel(ylabel, fontsize=6, labelpad=2)
    ax.set_title(title, loc="left", fontsize=6.5, pad=14)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
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

    rc = draw("cai", cai_arrays, summary.get("cai", {}),
              "CAI", "CDS null model — codon adaptation index", "fig2b_cai")
    rc += draw("mfe_per_nt", mfe_arrays, summary.get("mfe_per_nt", {}),
               "MFE per nucleotide (kcal mol$^{-1}$ nt$^{-1}$)",
               "CDS null model — folding energy per nucleotide", "fig2c_mfe_per_nt")
    for a in ARMS:
        print(f"{a:8s} CAI n={len(cai_arrays[a]):3d} "
              f"median={np.median(cai_arrays[a]) if len(cai_arrays[a]) else float('nan'):.4f}   "
              f"MFE/nt n={len(mfe_arrays[a]):3d} "
              f"median={np.median(mfe_arrays[a]) if len(mfe_arrays[a]) else float('nan'):.4f}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
