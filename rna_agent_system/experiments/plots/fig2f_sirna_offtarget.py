#!/usr/bin/env python3
"""Fig. 2f — siRNA off-target scanning: predicted off-target hits per task.

Lollipop chart against the zero line: one lollipop per benchmark task
(x = task index), stem height = predicted off-target hit count of the
delivered (best-ranked) candidate against the species reference transcriptome
(homo_sapiens = GENCODE v46 all transcripts).

Colours (palette rev 7): zero-off-target lollipops in the siRNA workflow's
slate blue; nonzero in the held-out dark warm grey (the palette's
neutral-dark semantic, matching the fig2d miss convention). Marker shape
flags the audited scan status: circles = scan skipped (the task input
disabled the scan), diamonds = transcriptome scan executed (BLAST/bowtie2,
trace-verified). Legend entries are built from the marker/colour combos
actually present in the data.

Data  : experiments/results/exp6_sirna_offtarget/records.jsonl
        (+ summary.json for the annotated counts)

Usage : python experiments/plots/fig2f_sirna_offtarget.py
Output : experiments/plots/output/fig2f_sirna_offtarget.{pdf,png}
"""
from __future__ import annotations

import json
import re
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
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp6_sirna_offtarget"
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

# Palette roles: zero = the siRNA workflow's slate blue; nonzero = held-out
# dark warm grey (neutral-dark semantic); scanned tasks flagged as diamonds.
C_ZERO = WORKFLOW_COLORS["sirna_design"]          # #6B7B8D
C_NONZERO = PALETTE_BY_NAME["dark_warm_grey"]      # #7A7672


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
        print("no records found — run experiments/exp6_sirna_offtarget.py first")
        return 1
    n_total = len(records)
    counts = [int(r["best_off_target_count"]) for r in records]
    scanned = [bool(r.get("scan_executed")) for r in records]
    n_zero = sum(c == 0 for c in counts)

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel (fig2b–e geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([0.14, 0.21, 0.77, 0.68])

    xs = np.arange(1, n_total + 1)
    ymax = max(max(counts), 1)

    # zero reference line (the panel's headline reference)
    ax.axhline(0, color=TEXT, linewidth=0.6, zorder=2)

    def short_id(task_id: str) -> str:
        m = re.search(r"_(\d{3})_", task_id)
        return m.group(1) if m else task_id

    combo_counts: dict[tuple[str, bool], int] = {}
    for x, c, s, r in zip(xs, counts, scanned, records):
        zero = c == 0
        color = C_ZERO if zero else C_NONZERO
        if c > 0:  # lollipop stem rising from the zero line
            ax.plot([x, x], [0, c], color=color, linewidth=1.1, zorder=3)
        # diamond = trace-verified transcriptome scan; circle = scan skipped
        marker = "D" if s else "o"
        ax.scatter(
            x, c, s=17 if marker == "D" else 13, marker=marker,
            c=color, edgecolors="white", linewidths=0.35, zorder=4,
        )
        combo_counts[("zero" if zero else "nonzero", s)] = (
            combo_counts.get(("zero" if zero else "nonzero", s), 0) + 1
        )
        if c > 0:  # annotate nonzero tasks (index + scan tool)
            label = short_id(r["task_id"]) + " · " + "/".join(
                t.removeprefix("run_").split("_")[0]
                for t in (r.get("scan_tools") or ["noscan"])
            )
            ax.annotate(
                label,
                xy=(x, c), xytext=(0, 3), textcoords="offset points",
                fontsize=5, ha="center", va="bottom", color=C_NONZERO,
            )

    ax.set_xlim(0.3, n_total + 0.7)
    ax.set_ylim(-0.35, ymax + max(0.8, ymax * 0.18))
    ax.set_yticks(list(range(0, ymax + 1)))
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{i:03d}" for i in xs], fontsize=4.6, rotation=90)
    ax.tick_params(axis="both", labelsize=5.5, length=1.5, pad=1)
    ax.set_xlabel("siRNA benchmark task", fontsize=6, labelpad=2)
    ax.set_ylabel("predicted off-target hits\n(best candidate)", fontsize=6,
                  labelpad=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # legend: marker/colour combos actually present in the data
    # (zero = slate blue, nonzero = dark warm grey; diamond = scan executed)
    combo_style = {
        # (outcome, scanned): (marker, size, color)
        ("zero", False): ("o", 13, C_ZERO),
        ("zero", True): ("D", 17, C_ZERO),
        ("nonzero", False): ("o", 13, C_NONZERO),
        ("nonzero", True): ("D", 17, C_NONZERO),
    }
    combo_label = {
        ("zero", False): "zero, scan skipped",
        ("zero", True): "zero, scan executed",
        ("nonzero", False): "nonzero, scan skipped",
        ("nonzero", True): "nonzero, scan executed",
    }
    for combo in (("zero", False), ("zero", True), ("nonzero", True), ("nonzero", False)):
        if combo not in combo_counts:
            continue
        marker, size, color = combo_style[combo]
        ax.scatter([], [], s=size, marker=marker, c=color,
                   edgecolors="white", linewidths=0.35,
                   label=f"{combo_label[combo]} ({combo_counts[combo]})")
    ax.legend(loc="upper left", fontsize=5.2, frameon=False,
              handletextpad=0.2, borderaxespad=0.1, markerfirst=True,
              labelspacing=0.25)

    ax.set_title("siRNA designs — predicted off-targets per task",
                 loc="left", fontsize=6.5, pad=3)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2f_sirna_offtarget.{ext}"
        fig.savefig(out, format=ext, dpi=600 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"n = {n_total}, zero = {n_zero}, counts = {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
