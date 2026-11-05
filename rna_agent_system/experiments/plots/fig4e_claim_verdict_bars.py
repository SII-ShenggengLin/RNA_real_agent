"""Fig 4e — per-task-group claim-verdict diverging stacked bars (E3 dual-arm).

2026-10-07 user-directed chart-type change (same frozen Exp-5/Exp-17
summaries, no re-run): the per-claim task × arm colour-tile matrix retired
— Fig. 4's two per-claim verdict panels shared the tile-mosaic idiom with
Figs. 5c/5g and 6a, and the user asked for a distinct chart type. One row
per task group (the three trusted-deterministic families above the
divider, the nine untrusted-predictor targets below); from the centre
spine the ungated condition's stacked bar grows left and the gated
condition's grows right, the segments coloured by adjudicated verdict —
sage = true positive, terracotta = false positive, warm grey = borderline,
dark warm grey = suppressed (the panel's established class colours) — with
the claim count printed inside every segment and a printed 0 where a
task group × condition adjudicated no claim at all (the gated arm's
plan-level blocks; the retired panel's outlined empty cell). The class
selectivity reads directly off the geometry: the trusted block is all-sage
on both sides, the untrusted block carries terracotta only on the ungated
side. Panels e and g share one 3.5-mm-per-claim bar scale, so lengths
compare across the pair (the 2026-10-10 composite-grid batch moved the
shared scale 4.0 -> 3.5 and re-rendered both panels on their exact grid
cells — 82.5 x 66.2 mm here, the column-1 cell whose height fig4f's tall
variant shares — so the Fig. 4 assembler places every panel at scale 1.0;
the shared-scale contract itself is unchanged).

Data are aggregated per task group from the same frozen per-task matrix
the retired panel drew; built-in asserts re-derive the per-category and
per-arm totals against the frozen summary and against the registered
headline numbers (ungated 25 TP / 30 FP / 1 borderline; gated 20 TP /
0 FP / 7 suppressed / 4 borderline).

Style (Nature conventions, the fig3/fig4 house style): no in-figure
title; every text element one 6-pt pure-black style; colours only from
palette rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm
geometry with renderer-measured text extents; exact canvas (no tight
crop); post-draw asserts — no text pair overlaps, every text inside the
canvas.

Data  : experiments/results/exp17_claim_gating/summary.json
        (+ experiments/e5_audit_tasks.json for group order/labels)
Usage : python experiments/plots/fig4e_claim_verdict_bars.py
Output : experiments/plots/output/fig4e_claim_verdict_bars.{pdf,png}
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
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUMMARY = PROJECT_ROOT / "experiments" / "results" / "exp17_claim_gating" / "summary.json"
TASKS_JSON = PROJECT_ROOT / "experiments" / "e5_audit_tasks.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

MM_PER_CLAIM = 3.5                # shared with fig4g — lengths compare
                                  # (2026-10-07: 3.0 → 4.0, widening the
                                  # panel for the e|f row's equal-width
                                  # four-row composite layout; 2026-10-10
                                  # composite-grid batch: → 3.5, the
                                  # column-1 grid cell is 82.5 mm)
BAR_H = 2.0                       # bar thickness
TARGET_W_MM = 82.5                # the Fig. 4 grid's column-1 cell width
TARGET_H_MM = 66.2                # row 3's shared height (fig4f tall)

VERDICT_COLORS = {
    "TP": PALETTE_BY_NAME["sage_green"],
    "FP": PALETTE_BY_NAME["terracotta"],
    "borderline": PALETTE_BY_NAME["warm_grey"],
    "suppressed": PALETTE_BY_NAME["dark_warm_grey"],
}
VERDICT_LABELS = {"TP": "True positive", "FP": "False positive",
                  "borderline": "Borderline", "suppressed": "Suppressed"}
# stacking order from the centre spine outward, identical on both sides
VERDICT_ORDER = ("TP", "FP", "borderline", "suppressed")
ARM_ORDER = ("ungated", "gated")

# display labels; untrusted rows are the aptamer target names (the fig3
# target-label convention), trusted rows the deterministic family names
GROUP_LABELS = {"gc_target": "GC target", "u_reduce": "U reduction",
                "purine_band": "Purine band",
                "IFN-gamma": "IFN-γ", "Influenza H3N2 HA": "swine H3 HA"}
BLOCK_LABELS = {"trusted_deterministic": "Trusted-deterministic",
                "untrusted_oracle": "Untrusted-predictor"}

# the registered headline contract (Fig. 4e legend / §2.4)
REGISTERED_TOTALS = {"ungated": {"TP": 25, "FP": 30, "borderline": 1, "suppressed": 0},
                     "gated": {"TP": 20, "FP": 0, "borderline": 4, "suppressed": 7}}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "pdf.fonttype": 42,
})


def group_rows() -> list[dict]:
    """Per-group rows with per-arm verdict counts, in first-occurrence
    order (the task file interleaves the trusted families)."""
    payload = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    matrix = json.loads(SUMMARY.read_text(encoding="utf-8"))["per_task_matrix"]
    rows: list[dict] = []
    by_key: dict[str, dict] = {}
    for t in payload["tasks"]:
        key = t["task_family"] if t["category"] == "trusted_deterministic" \
            else t["target_family"]
        row = by_key.get(key)
        if row is None:
            row = {"key": key, "category": t["category"],
                   "label": GROUP_LABELS.get(key, key),
                   "counts": {a: {v: 0 for v in VERDICT_ORDER} for a in ARM_ORDER}}
            by_key[key] = row
            rows.append(row)
        for arm in ARM_ORDER:
            for verdict, n in (matrix.get(t["id"], {}).get(arm) or {}).items():
                row["counts"][arm][verdict] += n
    return rows


def text_w_mm(fig, s: str) -> float:
    """Renderer-measured 6-pt string width in mm (the fig4b/fig4g convention)."""
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, s, fontsize=FONT, color=INK)
    bb = probe.get_window_extent(r)
    probe.remove()
    return bb.width / fig.dpi * 25.4


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = group_rows()

    # ── data asserts: aggregates == frozen summary == registered contract ──
    totals = {a: {v: 0 for v in VERDICT_ORDER} for a in ARM_ORDER}
    blocks = {a: {} for a in ARM_ORDER}   # per-arm per-category sums
    for row in rows:
        for arm in ARM_ORDER:
            cat = blocks[arm].setdefault(row["category"],
                                         {v: 0 for v in VERDICT_ORDER})
            for v in VERDICT_ORDER:
                n = row["counts"][arm][v]
                totals[arm][v] += n
                cat[v] += n
    for arm in ARM_ORDER:
        assert totals[arm] == REGISTERED_TOTALS[arm], (arm, totals[arm])
        frozen = summary["arms"][arm]
        for v in VERDICT_ORDER:
            assert totals[arm][v] == frozen[v], (arm, v)
        for cat, sums in blocks[arm].items():
            frozen_cat = summary["by_category"][arm][cat]
            for v in VERDICT_ORDER:
                assert sums[v] == frozen_cat[v], (arm, cat, v)

    max_count = max(sum(row["counts"][a].values()) for row in rows for a in ARM_ORDER)

    # ── measured label column ─────────────────────────────────────────────
    probe = plt.figure(figsize=(4, 4))
    label_w = max([text_w_mm(probe, r["label"]) for r in rows]
                  + [text_w_mm(probe, b) for b in BLOCK_LABELS.values()])
    key_w = {v: text_w_mm(probe, VERDICT_LABELS[v]) for v in VERDICT_ORDER}
    digit_w = text_w_mm(probe, "8")
    plt.close(probe)
    assert digit_w + 0.8 <= MM_PER_CLAIM, "count label does not fit a 1-claim segment"

    ML = 1.2                        # outer margin (left = right)
    GAP_LB = 2.2                    # label column -> bar zone
    # the bar zones fill the grid cell: zone_w solved from the target width
    # (bars unchanged — the per-claim scale stays MM_PER_CLAIM)
    zone_w = (TARGET_W_MM - 2 * ML - GAP_LB - label_w) / 2.0
    assert zone_w >= max_count * MM_PER_CLAIM + 0.5, \
        f"bar zone {zone_w:.2f} mm cannot hold the {max_count}-claim bar"
    spine_x = ML + label_w + GAP_LB + zone_w
    fig_w = TARGET_W_MM

    header_cy = 2.3                 # arm-header centre
    caption_h = 2.4                 # block-caption line
    cap_gap = 1.0                   # caption -> first row
    div_gap = 1.8                   # extra gap at the block divider
    y0 = header_cy + 1.1 + 1.6      # top of the first block caption
    key_gap = 3.0                   # content -> verdict key
    key_pitch = 3.2                 # verdict-key row pitch
    bottom = 1.2                    # canvas floor margin
    # row pitch solved from the target height (the fig4g convention): the
    # vertical walk contributes (n-1)*pitch + BAR_H between y0 and the key
    row_pitch = (TARGET_H_MM - y0 - (2 * (caption_h + cap_gap) + div_gap)
                 - BAR_H - (key_gap + 2 * key_pitch + bottom)) / (len(rows) - 1)

    # ── vertical walk: caption + rows per block, divider between blocks ────
    layout: list[tuple[dict, float]] = []       # (row, bar-top y)
    captions: list[tuple[str, float]] = []      # (label, centre y)
    dividers: list[float] = []
    y = y0
    prev_cat = None
    for row in rows:
        if row["category"] != prev_cat:
            if prev_cat is not None:
                y += div_gap
                dividers.append(y - div_gap / 2)
            captions.append((BLOCK_LABELS[row["category"]], y + caption_h / 2))
            y += caption_h + cap_gap
            prev_cat = row["category"]
        layout.append((row, y))
        y += row_pitch
    content_bottom = y - (row_pitch - BAR_H)

    key_top = content_bottom + key_gap
    key_rows = (("TP", "FP"), ("suppressed", "borderline"))
    fig_h = key_top + len(key_rows) * key_pitch + bottom
    assert abs(fig_h - TARGET_H_MM) < 0.02, f"panel height {fig_h:.2f} != {TARGET_H_MM}"

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4), facecolor="white")

    def fx(v): return v / fig_w
    def fy(v): return 1 - v / fig_h
    def hm(v): return v / fig_h

    # ── bars ───────────────────────────────────────────────────────────────
    for row, y_top in layout:
        fig.text(fx(ML), fy(y_top + BAR_H / 2), row["label"],
                 ha="left", va="center", fontsize=FONT, color=INK)
        for arm, sign, _ in (("ungated", -1, ""), ("gated", +1, "")):
            counts = row["counts"][arm]
            total = sum(counts.values())
            if total == 0:
                # no adjudicated claim on this side (plan-level blocks):
                # an explicit printed 0 at the spine (the legend decodes it)
                fig.text(fx(spine_x + sign * 1.0), fy(y_top + BAR_H / 2), "0",
                         ha="left" if sign > 0 else "right", va="center",
                         fontsize=FONT, color=INK)
                continue
            run = 0.0
            for v in VERDICT_ORDER:
                n = counts[v]
                if not n:
                    continue
                x0 = spine_x + sign * run if sign > 0 else spine_x - run - n * MM_PER_CLAIM
                fig.patches.append(Rectangle(
                    (fx(x0), fy(y_top + BAR_H)), fx(n * MM_PER_CLAIM), hm(BAR_H),
                    facecolor=VERDICT_COLORS[v], edgecolor="none",
                    transform=fig.transFigure, zorder=2))
                fig.text(fx(x0 + n * MM_PER_CLAIM / 2), fy(y_top + BAR_H / 2),
                         str(n), ha="center", va="center", fontsize=FONT,
                         color=INK)
                run += n * MM_PER_CLAIM

    # centre spine over the bar rows
    first_bar_top = layout[0][1]
    fig.lines.append(plt.Line2D(
        [fx(spine_x), fx(spine_x)], [fy(first_bar_top), fy(content_bottom)],
        color=INK, linewidth=0.6, transform=fig.transFigure, zorder=3))

    # block captions + divider
    for label, cy in captions:
        fig.text(fx(ML), fy(cy), label, ha="left", va="center",
                 fontsize=FONT, color=INK)
    for dy in dividers:
        fig.lines.append(plt.Line2D(
            [fx(ML), fx(fig_w - ML)], [fy(dy), fy(dy)],
            color=INK, linewidth=0.6, transform=fig.transFigure, zorder=1))

    # arm headers centred over their bar zones
    fig.text(fx(ML + label_w + GAP_LB + zone_w / 2), fy(header_cy), "Ungated",
             ha="center", va="center", fontsize=FONT, color=INK)
    fig.text(fx(spine_x + zone_w / 2), fy(header_cy), "Gated",
             ha="center", va="center", fontsize=FONT, color=INK)

    # ── verdict key: two centred rows on a shared column grid ─────────────
    sw_w, sw_h, gap_st, gap_e = 2.4, 1.6, 0.8, 3.0
    col_ws = [max(key_w[row[c]] for row in key_rows) for c in range(2)]
    key_block_w = sum(sw_w + gap_st + w for w in col_ws) + gap_e
    assert key_block_w <= fig_w - 2 * ML, f"verdict key {key_block_w:.1f} mm > canvas"
    for r, row in enumerate(key_rows):
        cy = key_top + 1.0 + r * 3.2
        x = (fig_w - key_block_w) / 2
        for c, v in enumerate(row):
            fig.patches.append(Rectangle(
                (fx(x), fy(cy + sw_h / 2)), fx(sw_w), hm(sw_h),
                facecolor=VERDICT_COLORS[v], edgecolor="none",
                transform=fig.transFigure))
            fig.text(fx(x + sw_w + gap_st), fy(cy), VERDICT_LABELS[v],
                     ha="left", va="center", fontsize=FONT, color=INK)
            x += sw_w + gap_st + col_ws[c] + gap_e

    # ── post-draw QA: texts pure black, inside canvas, pairwise disjoint ───
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for txt in fig.texts:
        assert txt.get_color() == INK, f"non-black text: {txt.get_text()!r}"
        bb = txt.get_window_extent(renderer)
        x0, y0 = bb.x0 / fig.dpi * 25.4, bb.y0 / fig.dpi * 25.4
        x1, y1 = bb.x1 / fig.dpi * 25.4, bb.y1 / fig.dpi * 25.4
        assert x0 >= -0.05 and x1 <= fig_w + 0.05, f"text off canvas: {txt.get_text()!r}"
        assert y0 >= -0.05 and y1 <= fig_h + 0.05, f"text off canvas: {txt.get_text()!r}"
        boxes.append((x0, y0, x1, y1, txt.get_text()))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            assert ox < 0.15 or oy < 0.15, f"text overlap: {a[4]!r} x {b[4]!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4e_claim_verdict_bars.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None, facecolor="white")
    plt.close(fig)
    print(f"fig4e -> {OUT_DIR / 'fig4e_claim_verdict_bars.pdf'} (+png 1200 dpi); "
          f"canvas {fig_w:.1f} x {fig_h:.1f} mm; "
          f"ungated TP {totals['ungated']['TP']}/FP {totals['ungated']['FP']}, "
          f"gated TP {totals['gated']['TP']}/FP {totals['gated']['FP']}/"
          f"supp {totals['gated']['suppressed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
