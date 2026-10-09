#!/usr/bin/env python3
"""Fig. 2d — Secondary-structure inverse folding: per-benchmark recovery distance.

Single panel, stacked dot plot (Wilkinson): one dot per benchmark, stacked
above its best-candidate base-pair distance to the target structure, with
the stack count printed on top — the column at distance 0 is the exact
recoveries (the secondary-structure workflow's grey green), the short
columns are the misses (held-out dark warm grey — the palette's
neutral-dark semantic).

Figure revision 2026-10-02 (user-adjudicated, text-consistency pass): the
panel now plots the whole-base-pair distance (1/1/2/3) so the axis reads
exactly as the manuscript's "one to three base pairs"; the dot-bracket
Hamming distances (2/2/4/6) stay in the frozen records. Both fields are
frozen in exp4's records.jsonl — a rendering-metric switch, zero data
change. (Earlier revision 2026-08-27 replaced the cumulative step curve
with this stacked-dot encoding and removed the in-figure title — Nature
style, the headline lives in the caption, panels carry letters only;
every text element shares one font size and colour.)

Data  : experiments/results/exp4_inverse_folding/records.jsonl
        (+ summary.json for the annotated counts)

Usage : python experiments/plots/fig2d_inverse_folding.py
Output : experiments/plots/output/fig2d_inverse_folding.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from collections import Counter
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

FONT = 6  # single font size for every in-figure text element

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

# Palette roles: exact = the secondary-structure workflow's grey green;
# miss = held-out dark warm grey (neutral-dark semantic).
C_EXACT = WORKFLOW_COLORS["rna_secondary_structure_design"]      # #8DA290
C_MISS = PALETTE_BY_NAME["dark_warm_grey"]                        # #7A7672


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
        [r["best_base_pair_distance"] for r in records], dtype=float
    )
    n_exact = int(np.sum(dists == 0))
    by_dist = Counter(int(d) for d in dists)

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel (fig2b–g geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([
        0.40 / fig_w, 0.32 / fig_h,
        (fig_w - 0.46) / fig_w, (fig_h - 0.38) / fig_h,
    ])

    xmax = max(int(dists.max()), 1)
    xlo, xhi = -0.6, xmax + 0.6
    ticks = list(range(0, xmax + 1))

    # ── stacked dots: one per benchmark, count printed above each stack ──
    for d, c in sorted(by_dist.items()):
        ys = np.arange(1, c + 1)
        ax.scatter(
            np.full_like(ys, d, dtype=float), ys, s=12,
            c=C_EXACT if d == 0 else C_MISS,
            edgecolors="white", linewidths=0.35, zorder=3,
        )
        ax.text(d, c + 0.7, str(c), ha="center", va="bottom",
                fontsize=FONT, color=TEXT, zorder=4)

    # legend in the empty upper-right region (all stacks are short there)
    ax.scatter([], [], s=12, c=C_EXACT, edgecolors="white",
               linewidths=0.35, label=f"exact recovery ({n_exact}/{n_total})")
    ax.scatter([], [], s=12, c=C_MISS, edgecolors="white",
               linewidths=0.35, label=f"miss ({n_total - n_exact}/{n_total})")
    leg = ax.legend(loc="upper right", fontsize=FONT, frameon=False,
                    handletextpad=0.2, borderaxespad=0.1, markerfirst=True,
                    labelspacing=0.3, bbox_to_anchor=(1.0, 0.98))
    for t in leg.get_texts():
        t.set_color(TEXT)

    ax.set_xlim(xlo, xhi)
    ax.set_ylim(0, n_total + 2.2)
    ax.set_xticks(ticks)
    ax.set_yticks(list(range(0, n_total + 1, 5)))
    ax.set_xlabel("base-pair distance to the target structure",
                  fontsize=FONT, labelpad=2)
    ax.set_ylabel("number of benchmarks", fontsize=FONT, labelpad=2)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2d_inverse_folding.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"n = {n_total}, exact = {n_exact}, "
          f"distances = {sorted(int(d) for d in dists)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
