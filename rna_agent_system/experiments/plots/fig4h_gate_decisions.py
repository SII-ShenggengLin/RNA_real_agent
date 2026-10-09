#!/usr/bin/env python3
"""Fig. 4h — production gate verdicts by predictor (horizontal Cleveland dot
plot; §2.4 实验 5, Exp 24).

One row per predictor (rows ordered by total verdict count, descending — the
Cleveland ordered-dot-plot convention), one marker per verdict class
(reject / require_profiling / downgrade / allow), thin light-grey dumbbell
connectors spanning each row's markers, and the verdict count printed
adjacent to every marker (CASCADE Fig. 5d/e convention). X axis = verdicts
issued by the production DecisionGate across the 241-run production
campaign (Exp 24:
210 RNADesign-210 tasks + 31 PA form sessions, CapGate advisory — verdicts are
logged identically under advisory and enforce; only enforcement differs).
Counts come from the frozen audit-slice corpus (SHA-256 manifest, see
experiments/exp24_audit_gate_stats.py).

Style (reset programme, Nature convention): no in-figure title — Nature
panels carry a bold panel letter at the top left (added by the assembler)
with the headline in the caption, never a centred title on the panel (e.g.
LinearDesign, Nature 621, 399–404, Figs 2–3); the verdict key sits inside
the panel at the empty lower right (Nature in-panel key convention, also
fig2h); every text element is one 6-pt pure-black style (the Fig-4 panel
convention, fig4a–fig4e/fig4g — the old #1A1A1A palette TEXT read grey
against those panels); absolute-mm geometry; 1200-dpi PNG + vector PDF
(fonttype 42) — the raster exceeds the Nature Methods 300–1200-dpi
requirement and the PDF keeps text as editable TrueType.

Colours (palette rev 7): verdict colours follow the fig2h/fig4e gate
convention — reject terracotta (#C08B7C), require_profiling sand (#D9C3A9), allow sage green (#A3B18A, the fig4e allow/pass colour),
downgrade mauve grey (#A99AAF); dumbbell connectors and gridlines non-data
grey; all text pure black.

Data  : experiments/results/exp24_audit_gate_stats/stats.json
Usage : python experiments/plots/fig4h_gate_decisions.py
Output : experiments/plots/output/fig4h_gate_decisions.{pdf,png}
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
from palette import NEUTRAL_GRID, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATS = PROJECT_ROOT / "experiments" / "results" / "exp24_audit_gate_stats" / "stats.json"
if os.environ.get("FIG4F_SUMMARY"):
    STATS = Path(os.environ["FIG4F_SUMMARY"]).resolve()
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FS = 6            # the programme's single text size
INK = "#000000"   # pure black — the Fig-4 panel convention (fig4a–fig4e/fig4g)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FS,
    "axes.linewidth": 0.5,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
})

VERDICTS = ("reject", "require_profiling", "downgrade", "allow")
VERDICT_LABELS = {
    "reject": "reject",
    "require_profiling": "require-profiling",
    "downgrade": "downgrade",
    "allow": "allow",
}
VERDICT_COLOR = {
    "reject": PALETTE_BY_NAME["terracotta"],       # #C08B7C (fig2h convention)
    "require_profiling": PALETTE_BY_NAME["sand"],  # #D9C3A9
    "downgrade": PALETTE_BY_NAME["mauve_grey"],    # #A99AAF
    "allow": PALETTE_BY_NAME["sage_green"],        # #A3B18A (fig4e allow/pass)
}
VERDICT_MARKER = {
    "reject": "o",
    "require_profiling": "D",
    "downgrade": "s",
    "allow": "^",
}

# Concise row labels: tool name + the gated metric, generic suffixes dropped
# (fig4c bare-name convention). Verified against the upstream repos:
# RhoFold pLDDT, Protenix-service ipTM, EGARPS native probability, GerNA-Bind,
# GEMORNA 5'UTR mean ribosome load / 3'UTR stability, IRESfinder, RNASTOP
# stability, CRISOT off-target score, CRGPT sgRNA-handle score, RNAsmol.
ORACLE_LABELS = {
    "egarps_native_probability": "EGARPS native prob.",
    "proteinx_ipTM": "ProteinX ipTM",
    "rhofold_mean_plddt": "RhoFold pLDDT",
    "rnasmol": "RNAsmol",
    "gernabind_probability": "GerNA-Bind",
    "gemorna_5utr_mrl": "GEMORNA 5\u2032UTR MRL",
    "gemorna_3utr_stability": "GEMORNA 3\u2032UTR stab.",
    "iresfinder_score": "IRESfinder",
    "rnastop_stability": "RNASTOP stab.",
    "crisot_off_target_score": "CRISOT off-target",
    "crgpt_handle_score": "CRGPT sgRNA handle",
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
    fig_w_mm = 112.8                      # 2026-10-07: 88.0 → 112.8, the
                                          # equal-width four-row composite
                                          # layout (g|h row spans the full
                                          # content width)
    left_mm = 25.0                        # concise oracle row labels
    right_mm = 6.0
    row_mm = 5.4
    top_mm = 5.0
    bottom_mm = 8.0                       # x tick labels + axis title (key in-panel)
    fig_h_mm = top_mm + bottom_mm + row_mm * n_rows

    fig = plt.figure(figsize=(fig_w_mm / 25.4, fig_h_mm / 25.4), facecolor="white")
    ax = fig.add_axes([
        left_mm / fig_w_mm,
        bottom_mm / fig_h_mm,
        (fig_w_mm - left_mm - right_mm) / fig_w_mm,
        (fig_h_mm - top_mm - bottom_mm) / fig_h_mm,
    ])

    # Marker vertical offsets so same-row markers at close counts stay
    # legible (small fixed offsets in row units; value labels sit beside).
    dy = {"reject": 0.24, "require_profiling": 0.08, "downgrade": -0.08, "allow": -0.24}

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
                ha="left", va="center", fontsize=FS, color=INK, zorder=5,
            )

    ax.set_yticks([n_rows - 1 - i for i in range(n_rows)])
    ax.set_yticklabels([oracle_label(o) for o in rows], fontsize=FS)
    ax.set_ylim(-0.75, n_rows - 0.25)

    x_ticks = _nice_ticks(x_max)
    ax.set_xlim(0, x_max * 1.16)  # headroom for the largest value label
    ax.set_xticks(x_ticks)
    ax.tick_params(axis="both", labelsize=FS, length=1.5, pad=1)
    ax.set_xlabel("Gate verdicts", fontsize=FS, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)
    ax.grid(axis="x", color=NEUTRAL_GRID, linewidth=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    # Verdict key inside the panel (Nature in-panel key convention, also
    # fig2h): the lower right of the axes is empty — bottom rows reach only
    # count ~25 while the key occupies x ≳ 60% of the axis width. Opaque
    # white backing (edgeless) so the gridlines do not cross the key.
    handles = [
        Line2D([0], [0], linestyle="none", marker=VERDICT_MARKER[v],
               markersize=3.4, markerfacecolor=VERDICT_COLOR[v],
               markeredgecolor="white", markeredgewidth=0.3,
               label=VERDICT_LABELS[v])
        for v in VERDICTS
    ]
    leg = ax.legend(handles, [h.get_label() for h in handles], ncol=1,
                    loc="lower right", bbox_to_anchor=(0.99, 0.02),
                    frameon=True, facecolor="white", edgecolor="none",
                    framealpha=1.0, fontsize=FS, handlelength=1.0,
                    handletextpad=0.45, labelspacing=0.45, borderaxespad=0.0,
                    borderpad=0.4)
    for t in leg.get_texts():
        t.set_color(INK)

    # ---- layout self-check: text inside the figure, no overlaps ----------
    problems = _layout_check(fig, ax, leg)
    if problems:
        for p in problems:
            print(f"layout check FAIL: {p}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig4h_gate_decisions.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    totals = stats["gate_decisions"]["verdict_totals"]
    print(f"rows (oracles): {n_rows}; verdict totals: {totals}")
    return 0


def _layout_check(fig, ax, leg) -> list[str]:
    """Rendered-extent assertions: every text element (row labels, tick
    labels, axis title, value labels, legend) must lie inside the figure and
    no two text extents may intersect; the legend must clear every value
    label."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    fig_box = fig.get_window_extent(renderer=rend)
    texts = list(ax.texts)
    texts += [ax.xaxis.get_label(), ax.yaxis.get_label()]
    texts += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
    texts += list(leg.get_texts())
    problems: list[str] = []
    boxes = []
    for t in texts:
        if not t.get_text():
            continue
        bb = t.get_window_extent(renderer=rend)
        if not (fig_box.contains(bb.x0, bb.y0) and fig_box.contains(bb.x1, bb.y1)):
            problems.append(f"text outside figure: {t.get_text()!r}")
        boxes.append((t.get_text(), bb))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if boxes[i][1].overlaps(boxes[j][1]):
                problems.append(
                    f"overlap: {boxes[i][0]!r} x {boxes[j][0]!r}")
    leg_bb = leg.get_window_extent(renderer=rend)
    if not (fig_box.contains(leg_bb.x0, leg_bb.y0)
            and fig_box.contains(leg_bb.x1, leg_bb.y1)):
        problems.append("legend outside figure")
    for t in ax.texts:  # value labels
        if t.get_text() and leg_bb.overlaps(t.get_window_extent(renderer=rend)):
            problems.append(f"legend overlaps value label {t.get_text()!r}")
    return problems


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
