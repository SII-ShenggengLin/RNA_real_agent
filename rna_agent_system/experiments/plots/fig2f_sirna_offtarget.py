#!/usr/bin/env python3
"""Fig. 2f — siRNA off-target scanning: predicted off-target hits per task.

Single panel, stacked dot plot (Wilkinson): one dot per benchmark task,
stacked above the predicted off-target hit count of the delivered
(best-ranked) candidate against the species reference transcriptome
(homo_sapiens = GENCODE v46 all transcripts), with the stack count printed
on top — the tall column at 0 is the clean tasks (the siRNA workflow's
slate blue), the single dot at 3 is the sole nonzero task (held-out dark
warm grey — the palette's neutral-dark semantic, matching the fig2d miss
convention). Marker shape flags the audited scan status: circles = scan
skipped (the task input disabled the scan), diamonds = transcriptome scan
executed (BLAST/bowtie2, trace-verified). Legend entries are built from
the marker/colour combos actually present in the data.

Figure revision 2026-08-28 (user-directed): replaced the per-task lollipop
with the fig2d stacked-dot encoding — 21 identical zeros spread along a
task axis read as noise at first glance, while stacking one dot per task
above its hit count makes the distribution itself the headline. In-figure
title removed (Nature style — the headline lives in the caption, panels
carry letters only); every text element shares one font size and colour;
legend labels shortened to "<hits> hits, <scan status> (n)".

Data  : experiments/results/exp6_sirna_offtarget/records.jsonl
        (+ summary.json for the annotated counts)

Usage : python experiments/plots/fig2f_sirna_offtarget.py
Output : experiments/plots/output/fig2f_sirna_offtarget.{pdf,png}
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

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
    n_zero = sum(c == 0 for c in counts)
    nz_hits = max(counts)  # the observed nonzero hit count (3)
    by_count: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        by_count[int(r["best_off_target_count"])].append(r)

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel (fig2b–g geometry)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([
        0.40 / fig_w, 0.32 / fig_h,
        (fig_w - 0.46) / fig_w, (fig_h - 0.38) / fig_h,
    ])

    def short_id(task_id: str) -> str:
        m = re.search(r"_(\d{3})_", task_id)
        return m.group(1) if m else task_id

    # ── stacked dots: one per task, stack count printed on top ──
    combo_counts: dict[tuple[str, bool], int] = {}
    for c, recs in sorted(by_count.items()):
        zero = c == 0
        color = C_ZERO if zero else C_NONZERO
        for y, r in enumerate(recs, start=1):
            scanned = bool(r.get("scan_executed"))
            # diamond = trace-verified transcriptome scan; circle = skipped
            marker = "D" if scanned else "o"
            ax.scatter(
                c, y, s=16 if scanned else 12, marker=marker,
                c=color, edgecolors="white", linewidths=0.35, zorder=3,
            )
            key = ("zero" if zero else "nonzero", scanned)
            combo_counts[key] = combo_counts.get(key, 0) + 1
            if c > 0:  # name nonzero tasks (index + scan tool)
                label = short_id(r["task_id"]) + " · " + "/".join(
                    t.removeprefix("run_").split("_")[0]
                    for t in (r.get("scan_tools") or ["noscan"])
                )
                ax.annotate(
                    label, xy=(c, y), xytext=(-4, -1),
                    textcoords="offset points", fontsize=FONT,
                    ha="right", va="center", color=TEXT, zorder=4,
                )
        ax.text(c, len(recs) + 0.7, str(len(recs)), ha="center", va="bottom",
                fontsize=FONT, color=TEXT, zorder=4)

    ax.set_xlim(-0.6, nz_hits + 0.6)
    ax.set_ylim(0, n_total + 2.2)
    ax.set_xticks(list(range(0, nz_hits + 1)))
    ax.set_yticks(list(range(0, n_total + 1, 5)))
    ax.set_xlabel("predicted off-target hits (best candidate)",
                  fontsize=FONT, labelpad=2)
    ax.set_ylabel("number of tasks", fontsize=FONT, labelpad=2)
    ax.tick_params(axis="both", labelsize=FONT, length=1.5, pad=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # legend in the empty upper-right region (columns 1..xmax stay short)
    # (zero = slate blue, nonzero = dark warm grey; diamond = scan executed)
    combo_style = {
        # (outcome, scanned): (marker, size, color)
        ("zero", False): ("o", 12, C_ZERO),
        ("zero", True): ("D", 16, C_ZERO),
        ("nonzero", False): ("o", 12, C_NONZERO),
        ("nonzero", True): ("D", 16, C_NONZERO),
    }
    combo_label = {
        ("zero", False): "0 hits, no scan",
        ("zero", True): "0 hits, scanned",
        ("nonzero", False): f"{nz_hits} hits, no scan",
        ("nonzero", True): f"{nz_hits} hits, scanned",
    }
    for combo in (("zero", False), ("zero", True), ("nonzero", True), ("nonzero", False)):
        if combo not in combo_counts:
            continue
        marker, size, color = combo_style[combo]
        ax.scatter([], [], s=size, marker=marker, c=color,
                   edgecolors="white", linewidths=0.35,
                   label=f"{combo_label[combo]} ({combo_counts[combo]})")
    leg = ax.legend(loc="upper right", fontsize=FONT, frameon=False,
                    handletextpad=0.2, borderaxespad=0.1, markerfirst=True,
                    labelspacing=0.3, bbox_to_anchor=(1.0, 0.98))
    for t in leg.get_texts():
        t.set_color(TEXT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2f_sirna_offtarget.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    print(f"n = {n_total}, zero = {n_zero}, counts = {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
