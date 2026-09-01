#!/usr/bin/env python3
"""Fig. 4f — production gate decisions by oracle (horizontal Cleveland dot
plot; §2.4 实验 5, Exp 24).

One row per oracle (rows ordered by total decision count, descending — the
Cleveland ordered-dot-plot convention), one marker per gate-decision class
(reject / require_profiling / downgrade), thin light-grey dumbbell connectors
spanning each row's markers, and the decision count printed adjacent to every
marker (CASCADE Fig. 5d/e convention). X axis = decisions issued by the
production DecisionGate across the 241-run production campaign (Exp 24:
210 RNADesign-210 tasks + 31 PA form sessions, CapGate advisory — verdicts are
logged identically under advisory and enforce; only enforcement differs).
Counts come from the frozen audit-slice corpus (SHA-256 manifest, see
experiments/exp24_audit_gate_stats.py).

Style (reset programme, Nature convention): no in-figure title — the headline
lives in the caption and the assembler adds the panel letter; every text
element is one 6-pt ink-black style; the verdict legend is a centred row
block directly under the x-axis label (fig2i/fig3b convention); absolute-mm
geometry; 1200-dpi PNG + vector PDF (fonttype 42).

Colours (palette rev 7): verdict colours follow the fig2h/fig4e gate
convention — reject terracotta (#C08B7C), require_profiling sand (#D9C3A9),
downgrade mauve grey (#A99AAF); dumbbell connectors and gridlines non-data
grey; all text ink black.

Data  : experiments/results/exp24_audit_gate_stats/stats.json
Usage : python experiments/plots/fig4f_gate_decisions.py
Output : experiments/plots/output/fig4f_gate_decisions.{pdf,png}
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATS = PROJECT_ROOT / "experiments" / "results" / "exp24_audit_gate_stats" / "stats.json"
if os.environ.get("FIG4F_SUMMARY"):
    STATS = Path(os.environ["FIG4F_SUMMARY"]).resolve()
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FS = 6  # the programme's single text size

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FS,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

VERDICTS = ("reject", "require_profiling", "downgrade")
VERDICT_LABELS = {
    "reject": "reject",
    "require_profiling": "require profiling",
    "downgrade": "downgrade",
}
VERDICT_COLOR = {
    "reject": PALETTE_BY_NAME["terracotta"],     # #C08B7C (fig2h convention)
    "require_profiling": PALETTE_BY_NAME["sand"],  # #D9C3A9
    "downgrade": PALETTE_BY_NAME["mauve_grey"],  # #A99AAF
}
VERDICT_MARKER = {
    "reject": "o",
    "require_profiling": "D",
    "downgrade": "s",
}

ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS native prob.",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold pLDDT",
    "rnasmol": "RNAsmol",
    "gernabind_probability": "GerNA-Bind prob.",
    "gemorna_5utr_mrl": "GEMORNA 5\u2032UTR MRL",
    "gemorna_3utr_stability": "GEMORNA 3\u2032UTR stability",
    "iresfinder_score": "IRESfinder score",
    "rnastop_stability": "RNASTOP stability",
    "crisot_off_target_score": "CRISOT off-target",
    "crgpt_handle_score": "CRGPT handle score",
    "junction_metric": "Junction metric",
    "cai_metric": "CAI",
    "mfe_metric": "MFE (LinearFold)",
    "gc_content": "GC content",
    "u_content": "U content",
    "purine_content": "Purine content",
}


def oracle_label(name: str) -> str:
    return ORACLE_LABELS.get(name, name)


def main() -> int:
    stats = json.loads(STATS.read_text(encoding="utf-8"))
    by_oracle: dict[str, dict[str, int]] = stats["gate_decisions"]["by_oracle"]
    # Rows: oracles ordered by total charted decisions, most first (top).
    rows = sorted(
        by_oracle,
        key=lambda o: (-sum(by_oracle[o].get(v, 0) for v in VERDICTS), o),
    )
    n_rows = len(rows)
    x_max = max(
        (by_oracle[o].get(v, 0) for o in rows for v in VERDICTS), default=1
    )

    # ---- geometry (absolute mm) -----------------------------------------
    fig_w_mm = 88.0                       # single column (fig3b/fig3g convention)
    left_mm = 30.0                        # oracle row labels
    right_mm = 8.0
    row_mm = 5.4
    top_mm = 6.0
    bottom_mm = 13.5                      # x label + verdict legend row
    fig_h_mm = top_mm + bottom_mm + row_mm * n_rows

    fig = plt.figure(figsize=(fig_w_mm / 25.4, fig_h_mm / 25.4), facecolor="white")
    ax = fig.add_axes([
        left_mm / fig_w_mm,
        bottom_mm / fig_h_mm,
        (fig_w_mm - left_mm - right_mm) / fig_w_mm,
        (fig_h_mm - top_mm - bottom_mm) / fig_h_mm,
    ])

    # Marker vertical offsets so three same-row markers at close counts stay
    # legible (small fixed offsets in row units; value labels sit beside).
    dy = {"reject": 0.16, "require_profiling": 0.0, "downgrade": -0.16}

    for i, o in enumerate(rows):
        y_row = n_rows - 1 - i  # top row first
        counts = {v: by_oracle[o].get(v, 0) for v in VERDICTS}
        present = [(v, c) for v, c in counts.items()]
        lo = min(c for _, c in present)
        hi = max(c for _, c in present)
        if hi > lo:
            ax.plot([lo, hi], [y_row, y_row], color=NEUTRAL_GRID,
                    linewidth=0.7, zorder=1, solid_capstyle="round")
        elif hi > 0:
            # single visible class: a short anchor tick keeps the row readable
            ax.plot([0, hi], [y_row, y_row], color=NEUTRAL_GRID,
                    linewidth=0.7, zorder=1, solid_capstyle="round")
        for v, c in present:
            if c <= 0:
                continue
            ax.scatter([c], [y_row + dy[v]], s=16, marker=VERDICT_MARKER[v],
                       c=VERDICT_COLOR[v], edgecolors="white", linewidths=0.3,
                       zorder=4)
            ax.annotate(
                f"{c}", (c, y_row + dy[v]),
                xytext=(2.6, 0), textcoords="offset points",
                ha="left", va="center", fontsize=FS, color=TEXT, zorder=5,
            )

    ax.set_yticks([n_rows - 1 - i for i in range(n_rows)])
    ax.set_yticklabels([oracle_label(o) for o in rows], fontsize=FS)
    ax.set_ylim(-0.75, n_rows - 0.25)

    x_ticks = _nice_ticks(x_max)
    ax.set_xlim(0, x_max * 1.16)  # headroom for the largest value label
    ax.set_xticks(x_ticks)
    ax.tick_params(axis="both", labelsize=FS, length=1.5, pad=1)
    ax.set_xlabel("Gate decisions in the production campaign (count)",
                  fontsize=FS, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="x", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    handles = [
        Line2D([0], [0], linestyle="none", marker=VERDICT_MARKER[v],
               markersize=3.4, markerfacecolor=VERDICT_COLOR[v],
               markeredgecolor="white", markeredgewidth=0.3,
               label=VERDICT_LABELS[v])
        for v in VERDICTS
    ]
    leg = fig.legend(handles, [h.get_label() for h in handles], ncol=3,
                     loc="lower center", bbox_to_anchor=(0.5, 0.035),
                     frameon=False, fontsize=FS, handlelength=1.2,
                     handletextpad=0.35, columnspacing=1.1, borderaxespad=0.0)
    for t in leg.get_texts():
        t.set_color(TEXT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig4f_gate_decisions.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    totals = stats["gate_decisions"]["verdict_totals"]
    print(f"rows (oracles): {n_rows}; verdict totals: {totals}")
    return 0


def _nice_ticks(x_max: int) -> list[int]:
    step = 1
    for s in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000, 5000):
        step = s
        if x_max / s <= 6:
            break
    t = step
    ticks = [0]
    while t <= x_max * 1.16 and len(ticks) < 30:
        ticks.append(t)
        t += step
    return ticks


if __name__ == "__main__":
    sys.exit(main())
