#!/usr/bin/env python3
"""Fig. 2d — Secondary-structure inverse folding: per-benchmark recovery distance.

Top    : strip of per-benchmark structure distances (one dot per benchmark;
         exact recoveries in the workflow's grey-green, misses in the held-out
         dark warm grey — the palette's neutral-dark semantic).
Bottom  : staircase cumulative count of benchmarks within distance ≤ d
         (slate blue), annotated with the exact-recovery count at distance 0.

Data  : experiments/results/exp4_inverse_folding/records.jsonl
        (+ summary.json for the annotated counts)

Usage : python experiments/plots/fig2d_inverse_folding.py
Output : experiments/plots/output/fig2d_inverse_folding.{pdf,png}
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
from palette import (  # noqa: E402
    NEUTRAL_GRID,
    TEXT,
    WORKFLOW_COLORS,
    PALETTE_BY_NAME,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp4_inverse_folding"
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

# Palette roles: exact = the secondary-structure workflow's grey green;
# miss = held-out dark warm grey (neutral-dark semantic); cumulative curve
# = slate blue (the palette's designated separator/structural tone).
C_EXACT = WORKFLOW_COLORS["rna_secondary_structure_design"]      # #8DA290
C_MISS = PALETTE_BY_NAME["dark_warm_grey"]                        # #7A7672
C_STEP = PALETTE_BY_NAME["slate_blue"]                            # #6B7B8D


def load_records() -> list[dict]:
    recs: dict[str, dict] = {}
    path = RESULTS_DIR / "records.jsonl"
    if not path.exists():
        path = RESULTS_DIR / "pilot.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        recs[rec["task_id"]] = rec  # latest wins
    ok = [r for r in recs.values() if r.get("success")]
    return sorted(ok, key=lambda r: r["task_id"])


def main() -> int:
    records = load_records()
    if not records:
        print("no records found — run experiments/exp4_inverse_folding.py first")
        return 1
    n_total = len(records)
    dists = np.array(
        [r["best_structure_distance"] for r in records], dtype=float
    )
    n_exact = int(np.sum(dists == 0))

    fig_w, fig_h = 88 / 25.4, 66 / 25.4  # single-column panel (fig2b/c geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_strip = fig.add_axes([0.155, 0.585, 0.70, 0.275])
    ax_step = fig.add_axes([0.155, 0.135, 0.70, 0.375])

    xmax = max(int(dists.max()), 1)
    xlo, xhi = -0.6, xmax + 0.6
    ticks = list(range(0, xmax + 1))

    # ── strip: one dot per benchmark ──
    rng = np.random.default_rng(0)
    for d, r in zip(dists, records):
        y = rng.uniform(0.22, 0.78)
        exact = d == 0
        ax_strip.scatter(
            d, y, s=13,
            c=C_EXACT if exact else C_MISS,
            edgecolors="white", linewidths=0.35, zorder=3,
        )
    ax_strip.set_xlim(xlo, xhi)
    ax_strip.set_ylim(0, 1)
    ax_strip.set_yticks([])
    ax_strip.set_xticks(ticks)
    ax_strip.tick_params(labelbottom=False, length=1.5, pad=1)
    for s in ("top", "right", "left"):
        ax_strip.spines[s].set_visible(False)
    ax_strip.set_ylabel("benchmarks", fontsize=6, labelpad=2)
    # legend inline, top-left of the strip band
    ax_strip.scatter([], [], s=13, c=C_EXACT, edgecolors="white",
                     linewidths=0.35, label=f"exact ({n_exact}/{n_total})")
    ax_strip.scatter([], [], s=13, c=C_MISS, edgecolors="white",
                     linewidths=0.35, label=f"miss ({n_total - n_exact}/{n_total})")
    ax_strip.legend(loc="lower right", fontsize=5.2, frameon=False,
                    handletextpad=0.2, borderaxespad=0.1, markerfirst=True,
                    labelspacing=0.25)

    # ── step cumulative curve: # benchmarks with distance ≤ d ──
    xs = np.arange(0, xmax + 1)
    counts = np.array([int(np.sum(dists <= d)) for d in xs])
    ax_step.step(xs, counts, where="post", color=C_STEP, linewidth=1.2,
                 zorder=3)
    ax_step.scatter(xs, counts, s=7, c=C_STEP, zorder=4, linewidths=0)
    ax_step.axhline(n_total, color=NEUTRAL_GRID, linewidth=0.5, zorder=1)
    ax_step.set_xlim(xlo, xhi)
    ax_step.set_ylim(0, n_total + 1.2)
    ax_step.set_xticks(ticks)
    ax_step.set_xlabel("structure distance to target (dot-bracket mismatches)",
                       fontsize=6, labelpad=2)
    ax_step.set_ylabel("cumulative benchmarks", fontsize=6, labelpad=2)
    ax_step.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)
    for s in ("top", "right"):
        ax_step.spines[s].set_visible(False)
    ax_step.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax_step.set_axisbelow(True)
    ax_step.annotate(
        f"{n_exact}/{n_total} exact\n(distance = 0)",
        xy=(0, n_exact), xytext=(6, 2), textcoords="offset points",
        fontsize=5.4, color=C_STEP, ha="left", va="bottom",
    )

    ax_strip.set_title("Inverse folding — distance to target structure",
                       loc="left", fontsize=6.5, pad=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2d_inverse_folding.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"n = {n_total}, exact = {n_exact}, "
          f"distances = {sorted(int(d) for d in dists)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
