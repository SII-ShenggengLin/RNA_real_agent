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

Geometry (2026-10-10, user-directed three-column relayout of the Fig. 2
composite): exact 57 x 57 mm canvas (no tight crop), absolute-mm axes
placement shared with panels b, c and e–g (axes bottom 12 mm, top 3 mm,
left 12 mm) so the three-per-row panels align; the x-axis label wraps to
two lines — same words — because the three-column width cannot carry it
on one; the 6-pt text scale is unchanged.

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

# Shared three-column geometry (panels b–g, 2026-10-10): exact canvas,
# axes placed in absolute mm so every panel in a composite row aligns.
W_MM, H_MM = 57.0, 57.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)
AX_L, AX_BOT, AX_R, AX_TOP = 12.0, 12.0, 2.0, 3.0


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

    fig_w, fig_h = W_PX / DPI + 1e-9, H_PX / DPI + 1e-9
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([
        AX_L / W_MM, AX_BOT / H_MM,
        (W_MM - AX_L - AX_R) / W_MM, (H_MM - AX_BOT - AX_TOP) / H_MM,
    ])

    xmax = max(int(dists.max()), 1)
    xlo, xhi = -0.6, xmax + 0.6
    ticks = list(range(0, xmax + 1))

    # ── stacked dots: one per benchmark, count printed above each stack ──
    count_texts = []
    for d, c in sorted(by_dist.items()):
        ys = np.arange(1, c + 1)
        ax.scatter(
            np.full_like(ys, d, dtype=float), ys, s=12,
            c=C_EXACT if d == 0 else C_MISS,
            edgecolors="white", linewidths=0.35, zorder=3,
        )
        count_texts.append(ax.text(d, c + 0.7, str(c), ha="center",
                                   va="bottom", fontsize=FONT, color=TEXT,
                                   zorder=4))

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
    ax.set_xlabel("base-pair distance\nto the target structure",
                  fontsize=FONT, labelpad=2)
    ax.set_ylabel("number of benchmarks", fontsize=FONT, labelpad=2)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # Guards (house convention): the legend must sit clear of every drawn
    # marker and count label (its upper-right pocket), and every text
    # element must sit fully inside the fixed canvas.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    leg_box = leg.get_window_extent(renderer)
    dot_r_px = fig.dpi / 72.0 * (12.0 ** 0.5) / 2.0  # marker radius (s=12)
    for coll in ax.collections:
        for px, py in coll.get_offsets():
            cx, cy = ax.transData.transform((px, py))
            dot_box = matplotlib.transforms.Bbox(
                [[cx - dot_r_px, cy - dot_r_px],
                 [cx + dot_r_px, cy + dot_r_px]])
            if matplotlib.transforms.Bbox.intersection(dot_box, leg_box):
                raise AssertionError(
                    f"a stack dot at ({px:g}, {py:g}) falls under the legend")
    for t in count_texts:
        if matplotlib.transforms.Bbox.intersection(
                t.get_window_extent(renderer).expanded(1.05, 1.2), leg_box):
            raise AssertionError("a stack count label falls under the legend")
    fw, fh = fig_w * fig.dpi, fig_h * fig.dpi
    for t in (ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(),
              *ax.get_yticklabels(), *leg.get_texts()):
        tb = t.get_window_extent(renderer)
        if tb.x0 < -0.5 or tb.y0 < -0.5 or tb.x1 > fw + 0.5 or tb.y1 > fh + 0.5:
            raise AssertionError(f"text element {t.get_text()!r} leaves "
                                 f"the canvas")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2d_inverse_folding.{ext}"
        fig.savefig(out, format=ext, dpi=DPI if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    print(f"n = {n_total}, exact = {n_exact}, "
          f"distances = {sorted(int(d) for d in dists)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
