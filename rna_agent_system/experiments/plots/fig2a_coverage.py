#!/usr/bin/env python3
"""Fig. 2a — RNADesign-210 task-success carpet (single merged panel).

One row per workflow (canonical order), one tile per task in task-id order,
filled with the workflow colour on success (a failed tile would be drawn
white with a grey edge). Row labels carry the per-workflow task count as
"label (n=…)" in the same colour and size as every other in-figure text;
each row end carries the per-workflow success count "ok/n", anchored by a
tile-semantics legend in the empty bottom-right corner (black swatch =
filled tile, task succeeded; white swatch = task failed — none
in the 2026-08-25 reset run). The
shared x-axis gives the task-count scale, so row length doubles as the
per-workflow count — the earlier companion summary-bar panel was redundant
with the carpet and was merged into this axis.

Figure revision 2026-08-27 (user-directed): merged the two sub-panels into
one, removed all in-figure titles (Nature style — the headline lives in the
caption, panels carry letters only), and unified every text element to one
font size and colour.

Data  : experiments/results/exp1_rnadesign210/{pilot,lane_*}.jsonl
Usage : python experiments/plots/fig2a_coverage.py
Output : experiments/plots/output/fig2a_coverage.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import (  # noqa: E402
    NEUTRAL_GRID,
    TEXT,
    WORKFLOW_COLORS,
    WORKFLOW_LABELS,
    WORKFLOW_ORDER,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp1_rnadesign210"
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

TILE = 0.8        # tile side in data units (unit lattice, square tiles)


def load_records() -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    # pilot first, then lanes — later files win, so lane records supersede
    # any stale pilot records for the same task.
    paths = [RESULTS_DIR / "pilot.jsonl", *sorted(RESULTS_DIR.glob("lane_*.jsonl"))]
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_id[rec["task_id"]] = rec
    return by_id


def main() -> int:
    records = load_records()
    if not records:
        print("no run records found — run the benchmark first")
        return 1

    by_wf: dict[str, list[dict]] = {wf: [] for wf in WORKFLOW_ORDER}
    for rec in records.values():
        by_wf.setdefault(rec["workflow"], []).append(rec)
    for wf in by_wf:
        by_wf[wf].sort(key=lambda r: r["task_id"])

    rows: list[tuple[str, list[dict]]] = [
        (wf, by_wf[wf]) for wf in WORKFLOW_ORDER if by_wf.get(wf)
    ]
    n_rows = len(rows)
    total = sum(len(v) for v in by_wf.values())
    n_ok = sum(1 for v in by_wf.values() for r in v if r.get("success"))
    max_cols = max(len(v) for _, v in rows)

    # ---- layout ---------------------------------------------------------
    # 183 mm double-column width; axes height follows from the unit lattice
    # so tiles stay square (aspect "equal").
    fig_w_in = 183 / 25.4
    label_margin_in = 1.30   # left room for "RNA–small molecule (n=15)" labels
    right_margin_in = 0.06
    axes_w_in = fig_w_in - label_margin_in - right_margin_in

    x_lo, x_hi = -0.2, max_cols + 1.9  # right room for the per-row ok/n count
    y_lo, y_hi = -0.4, n_rows + 0.2
    unit_in = axes_w_in / (x_hi - x_lo)
    axes_h_in = unit_in * (y_hi - y_lo)
    bottom_margin_in = 0.30  # tick labels + xlabel
    top_margin_in = 0.05
    fig_h_in = axes_h_in + bottom_margin_in + top_margin_in

    fig = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor="white")
    ax = fig.add_axes([
        label_margin_in / fig_w_in,
        bottom_margin_in / fig_h_in,
        axes_w_in / fig_w_in,
        axes_h_in / fig_h_in,
    ])

    for ri, (wf, recs) in enumerate(rows):
        y = n_rows - 1 - ri
        color = WORKFLOW_COLORS[wf]
        for ci, rec in enumerate(recs):
            if rec.get("success"):
                ax.add_patch(Rectangle((ci, y), TILE, TILE, facecolor=color,
                                       edgecolor="none"))
            else:
                ax.add_patch(Rectangle((ci, y), TILE, TILE, facecolor="white",
                                       edgecolor=NEUTRAL_GRID, linewidth=0.4))
        ax.text(-0.55, y + TILE / 2, f"{WORKFLOW_LABELS[wf]} (n={len(recs)})",
                ha="right", va="center", fontsize=FONT)
        n_ok_row = sum(1 for r in recs if r.get("success"))
        ax.text(len(recs) + 0.3, y + TILE / 2, f"{n_ok_row}/{len(recs)}",
                ha="left", va="center", fontsize=FONT)

    # tile-semantics legend: one row, two entries, in the empty bottom-right
    # corner (right of the short bottom rows), so the row-end ok/n counts
    # read as successes/tasks. A single black swatch stands for a filled tile
    # (the carpet fills tiles with each workflow's own colour); the "failed"
    # swatch matches the white failure tile exactly (none occurs in the
    # 2026-08-25 reset run). Legend texts carry a white bbox so the vertical
    # count guides never cross them.
    sw = 0.55                      # legend swatch side (smaller than a tile)
    leg_y = 0.9                    # centred in the empty bottom-right corner
    leg_x = max_cols - 6.6         # block left edge; block ends near x_hi
    leg_bbox = dict(facecolor="white", edgecolor="none", pad=1.2)
    ax.add_patch(Rectangle((leg_x, leg_y - sw / 2), sw, sw,
                           facecolor=TEXT, edgecolor="none"))
    tx = leg_x + sw + 0.35
    ax.text(tx, leg_y, "task succeeded", ha="left", va="center",
            fontsize=FONT, bbox=leg_bbox)
    leg_x2 = tx + 3.9              # entry gap past "task succeeded" (~14 chars)
    ax.add_patch(Rectangle((leg_x2, leg_y - sw / 2), sw, sw, facecolor="white",
                           edgecolor=NEUTRAL_GRID, linewidth=0.4))
    ax.text(leg_x2 + sw + 0.35, leg_y, "task failed", ha="left", va="center",
            fontsize=FONT, bbox=leg_bbox)

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.set_aspect("equal")
    ax.set_yticks([])
    ax.set_xticks(list(range(0, max_cols + 1, 5)))
    ax.set_xlabel("Tasks per workflow", fontsize=FONT, labelpad=2)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1.5)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    # vertical count guides, drawn only up to the carpet top so they never
    # cross the tile legend on the strip above
    for gx in range(0, max_cols + 1, 5):
        ax.plot([gx, gx], [y_lo, n_rows - 0.2], color=NEUTRAL_GRID,
                linewidth=0.4, alpha=0.6, zorder=0, solid_capstyle="butt")
    ax.set_axisbelow(True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2a_coverage.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    per_wf = ", ".join(
        f"{WORKFLOW_LABELS[w]} {sum(1 for r in rs if r.get('success'))}/{len(rs)}"
        for w, rs in rows
    )
    print(f"{n_ok}/{total} successful across {n_rows} workflows ({per_wf})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
