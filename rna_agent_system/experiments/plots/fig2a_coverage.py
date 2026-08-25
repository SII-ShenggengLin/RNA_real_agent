#!/usr/bin/env python3
"""Fig. 2a — RNADesign-210 task-success carpet + per-workflow summary bars.

Left  : per-task tile carpet — one row per workflow (canonical order), one
        tile per task in task-id order, filled with the workflow colour on
        success (failed tiles would be drawn white with a grey edge).
Right : horizontal bars — task count per workflow, annotated with the
        success rate; the panel title carries the overall n/n.

Data  : experiments/results/exp1_rnadesign210/summary.json (+ lane JSONLs).

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

TILE = 1.0        # tile size in data units
GAP = 0.28        # tile gap
ROW_GAP = 0.62    # extra gap between workflow rows


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

    total = sum(len(v) for v in by_wf.values())
    n_ok = sum(1 for v in by_wf.values() for r in v if r.get("success"))
    n_wf = len([wf for wf, v in by_wf.items() if v])
    max_cols = max(len(v) for v in by_wf.values())

    # ---- layout ---------------------------------------------------------
    # 183 mm double-column width; use a 62 mm-tall panel suited to 11 rows.
    fig_w, fig_h = 183 / 25.4, 62 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_left = fig.add_axes([0.215, 0.16, 0.50, 0.74])
    ax_right = fig.add_axes([0.760, 0.16, 0.150, 0.74])

    rows: list[tuple[str, list[dict]]] = [
        (wf, by_wf[wf]) for wf in WORKFLOW_ORDER if by_wf.get(wf)
    ]
    n_rows = len(rows)

    for ri, (wf, recs) in enumerate(rows):
        y = (n_rows - 1 - ri) * (TILE + ROW_GAP)
        color = WORKFLOW_COLORS[wf]
        for ci, rec in enumerate(recs):
            x = ci * (TILE + GAP)
            if rec.get("success"):
                ax_left.add_patch(Rectangle((x, y), TILE, TILE, facecolor=color,
                                            edgecolor="none"))
            else:
                ax_left.add_patch(Rectangle((x, y), TILE, TILE, facecolor="white",
                                            edgecolor=NEUTRAL_GRID, linewidth=0.4))

    ax_left.set_xlim(-GAP, max_cols * (TILE + GAP))
    ax_left.set_ylim(-TILE - ROW_GAP, n_rows * (TILE + ROW_GAP) - ROW_GAP + TILE)
    ax_left.set_aspect("equal")
    ax_left.axis("off")
    ax_left.set_title(f"Per-task outcome ({total} tasks, {n_wf} workflows)", loc="left",
                      fontsize=6.5, pad=3)

    # row labels
    for ri, (wf, recs) in enumerate(rows):
        y = (n_rows - 1 - ri) * (TILE + ROW_GAP) + TILE / 2
        ax_left.text(-0.6, y, WORKFLOW_LABELS[wf], ha="right", va="center", fontsize=5.5)
        ax_left.text(-0.6, y - 0.78, f"n={len(recs)}", ha="right", va="center",
                     fontsize=4.6, color="#666666")

    # ---- right: horizontal bar summary -----------------------------------
    wf_names = [wf for wf, _ in rows]
    counts = [len(recs) for _, recs in rows]
    rates = [sum(1 for r in recs if r.get("success")) / len(recs) if recs else 0
             for _, recs in rows]
    ypos = [i for i in range(n_rows)][::-1]
    ax_right.barh(ypos, counts, height=0.62,
                  color=[WORKFLOW_COLORS[wf] for wf in wf_names],
                  edgecolor="none")
    for y, c, r in zip(ypos, counts, rates):
        ax_right.text(c + 0.6, y, f"{r * 100:.0f}%", va="center", fontsize=5.5)
    ax_right.set_yticks([])
    ax_right.set_xlim(0, max(counts) * 1.30)
    ax_right.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax_right.set_xlabel("Tasks (success rate)", fontsize=5.5, labelpad=1.5)
    ax_right.tick_params(axis="x", labelsize=5, length=1.5, pad=1)
    for s in ("top", "right"):
        ax_right.spines[s].set_visible(False)
    ax_right.grid(axis="x", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax_right.set_axisbelow(True)
    ax_right.set_title("Tasks per workflow", loc="left", fontsize=6.5, pad=3)

    # overall KPI
    ax_left.text(0.5, 1.045,
                 f"RNADesign-210:  {n_ok}/{total} tasks successful  ·  {n_wf} workflows",
                 transform=ax_left.transAxes, ha="center", va="bottom",
                 fontsize=7, fontweight="bold")

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
    print(f"{n_ok}/{total} successful across {n_wf} workflows ({per_wf})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
