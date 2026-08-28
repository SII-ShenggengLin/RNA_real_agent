#!/usr/bin/env python3
"""Fig. 2i — end-to-end runtime by workflow (log-axis ECDF).

One cumulative-distribution step curve per workflow (SeFMol Fig. 2b/c style):
x = wall-clock minutes per run on a log axis, y = fraction of runs completed
within x. Samples pool the two Exp-8 arms — the RNADesign-210 suite tasks and
the PA_006–PA_036 regression sessions — both driven end-to-end through the
same user form entry on the pre-warmed platform (see
experiments/exp8_runtime.py docstring for the registered measurement
boundary). Successful runs only.

Reference line: 1 h per run (the programme's stated upper operating scale),
dashed. The legend (one row block centred under the axis) carries each
workflow's colour, median runtime and sample size.

Figure revisions 2026-08-28 (user-directed): removed the in-figure title —
Nature style, the headline lives in the caption and panels carry letters only
(the fig2d/fig2f revision convention); every text element now shares one font
size (6 pt) and one colour (ink black — the legend entries were previously set
in their pale workflow colours); the box inset — which overlapped the ECDF
curves — dropped entirely (it summarized the same samples the ECDF already
shows in full, and the legend carries the medians); the legend moved from
floating at the figure's right margin to a centred block under the x-axis, so
it reads as part of the panel; axis wording corrected target → run (the
241-run sample times whole PA sessions as single runs, not per target);
y-range headroom added above the y = 1 step so the curve tops no longer touch
the panel edge.

Colours (palette rev 7): each workflow's canonical WORKFLOW_COLORS entry;
reference line and all text in ink black.

Data  : experiments/results/exp8_runtime/{pilot,lane_*,pa_batch}.jsonl
Usage : python experiments/plots/fig2i_runtime_ecdf.py
Output : experiments/plots/output/fig2i_runtime_ecdf.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import (  # noqa: E402
    NEUTRAL_GRID,
    TEXT,
    WORKFLOW_COLORS,
    WORKFLOW_LABELS,
    WORKFLOW_ORDER,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp8_runtime"
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


def latest_records(paths: list[Path]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_id[rec["task_id"]] = rec  # later files win; append-order = latest
    return by_id


def fmt_min(minutes: float) -> str:
    if minutes < 1:
        return f"{minutes * 60:.0f} s"
    if minutes < 10:
        return f"{minutes:.1f} min"
    return f"{minutes:.0f} min"


def median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def main() -> int:
    lane_files = sorted(RESULTS_DIR.glob("lane_*.jsonl"))
    records = latest_records(
        [RESULTS_DIR / "pilot.jsonl", *lane_files, RESULTS_DIR / "pa_batch.jsonl"]
    )
    by_wf: dict[str, list[float]] = {}
    for rec in records.values():
        if rec.get("success"):
            by_wf.setdefault(rec["workflow"], []).append(rec["elapsed_seconds"] / 60.0)
    if not by_wf:
        print("no successful exp8 records — run experiments/exp8_run_all.sh first")
        return 1

    missing = [wf for wf in WORKFLOW_ORDER if wf not in by_wf]
    if missing:
        print(f"warning: no records yet for: {missing}")

    # order by median descending (longest first in the legend)
    wfs = [wf for wf in WORKFLOW_ORDER if wf in by_wf]
    wfs.sort(key=lambda wf: median(by_wf[wf]), reverse=True)

    all_vals = [v for wf in wfs for v in by_wf[wf]]
    x_lo = min(all_vals) * 0.75
    x_hi = max(max(all_vals) * 1.3, 75.0)  # keep the 1 h line inside

    fig_w, fig_h = 183 / 25.4, 62 / 25.4  # double-column panel (fig2a geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")

    # Single ECDF panel spanning the panel width; the legend sits in a
    # centred row block under the x-axis (geometry in inches).
    left, bottom, width, height = 0.42, 0.70, 6.55, 1.66
    ax = fig.add_axes([left / fig_w, bottom / fig_h, width / fig_w, height / fig_h])

    for wf in wfs:
        xs = sorted(by_wf[wf])
        ys = [(i + 1) / len(xs) for i in range(len(xs))]
        # start at 0 before the first observation, rise to 1 after the last
        ax.step([xs[0]] + xs, [0.0] + ys, where="post",
                color=WORKFLOW_COLORS[wf], linewidth=1.1)

    ax.axvline(60.0, color=TEXT, linewidth=0.6, linestyle=(0, (3, 2)), zorder=1)
    ax.text(60.0, 1.02, "1 h", transform=ax.get_xaxis_transform(),
            fontsize=FONT, ha="center", va="bottom", color=TEXT)

    ax.set_xscale("log")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0, 1.06)  # headroom so the y = 1 steps clear the panel top
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)
    ax.tick_params(axis="x", which="minor", length=1, width=0.3, color=NEUTRAL_GRID)
    ax.set_xlabel("End-to-end runtime per run (min, log scale)",
                  fontsize=FONT, labelpad=2)
    ax.set_ylabel("Fraction of runs completed", fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # --- legend: centred row block under the axis, colour + median + n ----
    handles, labels = [], []
    for wf in wfs:
        vals = by_wf[wf]
        handles.append(Line2D([0], [0], color=WORKFLOW_COLORS[wf], linewidth=1.6))
        labels.append(f"{WORKFLOW_LABELS[wf]} · {fmt_min(median(vals))} (n={len(vals)})")
    leg = fig.legend(handles, labels, ncol=4, loc="lower center",
                     bbox_to_anchor=(0.5, 0.0), frameon=False, fontsize=FONT,
                     handlelength=1.4, handletextpad=0.45, columnspacing=0.9,
                     borderaxespad=0.0)
    for t in leg.get_texts():
        t.set_color(TEXT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2i_runtime_ecdf.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for wf in wfs:
        vals = sorted(by_wf[wf])
        print(f"{wf}: n={len(vals)} min={vals[0]:.2f} med={median(vals):.2f} max={vals[-1]:.2f} (min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
