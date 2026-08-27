#!/usr/bin/env python3
"""Fig. 2h — end-to-end runtime by workflow (log-axis ECDF + box inset).

One cumulative-distribution step curve per workflow (SeFMol Fig. 2b/c style):
x = wall-clock minutes per target on a log axis, y = fraction of targets
completed within x. Samples pool the two Exp-8 arms — the RNADesign-210 suite
tasks and the PA_006–PA_036 regression sessions — both driven end-to-end
through the same user form entry on the pre-warmed platform (see
experiments/exp8_runtime.py docstring for the registered measurement
boundary). Successful runs only.

Box inset (lower right, same log x-scale): per-workflow box-and-whisker of
the same samples, indexed by colour — no inset labels, the legend carries
them.

Reference line: 1 h per target (the programme's stated upper operating
scale), dashed.

Colours (palette rev 7): each workflow's canonical WORKFLOW_COLORS entry;
reference lines in text black.

Data  : experiments/results/exp8_runtime/{pilot,lane_*,pa_batch}.jsonl
Usage : python experiments/plots/fig2h_runtime_ecdf.py
Output : experiments/plots/output/fig2h_runtime_ecdf.{pdf,png}
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

    # order by median descending (longest on top of the legend)
    wfs = [wf for wf in WORKFLOW_ORDER if wf in by_wf]
    wfs.sort(key=lambda wf: sorted(by_wf[wf])[len(by_wf[wf]) // 2], reverse=True)

    all_vals = [v for wf in wfs for v in by_wf[wf]]
    x_lo = min(all_vals) * 0.75
    x_hi = max(max(all_vals) * 1.3, 75.0)  # keep the 1 h line inside

    fig_w, fig_h = 183 / 25.4, 62 / 25.4  # double-column panel (fig2a geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.065, 0.15, 0.60, 0.74])

    for wf in wfs:
        xs = sorted(by_wf[wf])
        ys = [(i + 1) / len(xs) for i in range(len(xs))]
        # start at 0 before the first observation, rise to 1 after the last
        ax.step([xs[0]] + xs, [0.0] + ys, where="post",
                color=WORKFLOW_COLORS[wf], linewidth=1.1)

    ax.axvline(60.0, color=TEXT, linewidth=0.6, linestyle=(0, (3, 2)), zorder=1)
    ax.text(60.0, 1.06, "1 h", fontsize=5, ha="center", va="bottom", color=TEXT)

    ax.set_xscale("log")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0, 1.02)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "0.25", "0.50", "0.75", "1"], fontsize=5.5)
    ax.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)
    ax.set_xlabel("Wall-clock runtime per target (min, log scale)", fontsize=6, labelpad=2)
    ax.set_ylabel("Fraction of targets completed", fontsize=6, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", which="minor", length=1, width=0.3, color=NEUTRAL_GRID)

    # --- box inset, lower right of the main axes, same log x-scale ---------
    ins = ax.inset_axes([0.52, 0.06, 0.45, 0.40])
    data = [by_wf[wf] for wf in wfs]
    bp = ins.boxplot(
        data,
        vert=False,
        widths=0.6,
        patch_artist=True,
        showfliers=False,
        medianprops=dict(linewidth=0.7),
        whiskerprops=dict(linewidth=0.5),
        capprops=dict(linewidth=0.5),
    )
    for patch, wf in zip(bp["boxes"], wfs):
        c = WORKFLOW_COLORS[wf]
        patch.set_facecolor(c)
        patch.set_edgecolor(c)
        patch.set_alpha(0.75)
    for med in bp["medians"]:
        med.set_color("white")
    ins.set_xscale("log")
    ins.set_xlim(x_lo, x_hi)
    ins.set_ylim(0.5, len(wfs) + 0.5)
    ins.set_xticks([])
    ins.set_yticks([])
    for s_name in ("top", "right", "left"):
        ins.spines[s_name].set_visible(False)
    ins.tick_params(length=0)
    ins.set_facecolor("none")
    ins.text(0.02, 1.04, "same log scale", transform=ins.transAxes,
             fontsize=4.6, color=TEXT, va="bottom")

    # --- right-hand legend: colour + median --------------------------------
    legend_x = 0.705
    for j, wf in enumerate(wfs):
        y = 0.86 - j * (0.78 / max(len(wfs) - 1, 1))
        vals = sorted(by_wf[wf])
        med = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
        fig.lines.append(Line2D(
            [legend_x, legend_x + 0.028], [y, y],
            transform=fig.transFigure, color=WORKFLOW_COLORS[wf], linewidth=1.6,
        ))
        fig.text(
            legend_x + 0.034, y,
            f"{WORKFLOW_LABELS[wf]}  ·  {fmt_min(med)}  (n={len(vals)})",
            fontsize=5.4, va="center", color=WORKFLOW_COLORS[wf],
        )

    ax.set_title("End-to-end runtime by workflow", loc="left", fontsize=6.5, pad=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2h_runtime_ecdf.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for wf in wfs:
        vals = sorted(by_wf[wf])
        print(f"{wf}: n={len(vals)} min={vals[0]:.2f} med={vals[len(vals)//2]:.2f} max={vals[-1]:.2f} (min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
