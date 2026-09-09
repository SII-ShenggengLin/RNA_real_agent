"""Fig 4d — E3-M mRNA-side dual-arm re-run: per-task-family verdict strips.

One row per audit task (20 tasks grouped into the eight task families,
trusted-deterministic families above the divider, untrusted-oracle families
below), two column blocks (Ungated control arm / Gated treatment arm); one
colour tile per published claim — sage = true positive, terracotta = false
claim, warm grey = neutral relative-scope claim, dark warm grey = suppressed
at the claim gate (the fig4b convention; one gated 3′UTR-stability claim in
the DECISIONS-(bb) re-run); an outlined empty cell means
the arm published no claim on that task (the gated arm's plan-layer blocks
make the model abstain on the utr3/junction families — the mechanism this
panel shows).

2026-09-01 user-directed repair pass:
  - the arm × verdict mosaic inset was removed (its counts are stated in the
    Fig. 4d caption and main text — the fig4b precedent);
  - all left labels rebuilt with renderer-measured text extents so family /
    target / category labels can never overlap; the four longest family
    labels wrap onto two lines;
  - labels: "seed 7/11/13" relabelled to "Novel UTR 7/11/13", libraries
    relabelled "Random-50" / "Var-len human"; rotated category labels moved
    to the far left.

2026-09-01 user-directed revision (second; same frozen Exp-18 summary, no
re-run):
  - the left label zone is now a single hierarchical text column — a family
    header line above its indented per-target rows replaces the rotated
    category column plus the separate family column (the trusted/untrusted
    split stays visible as the full-width divider and is stated in the
    caption), answering the "two left columns read too wide" review;
  - row labels made biologically explicit and cross-figure consistent:
    "Novel 5′UTR 7/11/13" (the prime the repair pass had dropped), and the
    Sample-2019 libraries under their Fig. 3f names "Random 50-nt 5′UTRs" /
    "Varying-length human 5′UTRs"; family headers unwrapped to single lines
    ("3′UTR stability rank", "Cross-family MRL", "Junction quality", "MRL
    optimum", "Relative comparison");
  - every cell carries at most one claim, so the arm blocks narrow 18 →
    10 mm around the centred tile and the arm headers sit directly over
    their tile column; the verdict key wraps to two centred rows to fit the
    narrower canvas; the divider and the empty-cell outlines draw at 0.5–
    0.6 lw so no ink renders as de-facto grey;
  - every text element remains one 6-pt pure-black style (verified by raster
    QA: the only dark pixels are pure black plus antialiasing greys).

2026-09-01 user-directed revision (third — chart-type change, reverted the
same day): a transposed task × arm verdict carpet (oncoprint-style) was
drawn and judged less readable than the strip by the user; the panel
reverted to the second revision's hierarchical family strip above. The
carpet's rotated-label anchor semantics probe (matplotlib rotation=90 needs
ha="center", va="top" for downward-hanging column labels) stays recorded in
the CHANGELOG for reuse.

2026-09-01 user-directed revision (fourth — label trim; same frozen summary,
no re-run): the two Sample-2019 library row labels shortened from the fig3f
full names ("Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs") to the
compact fig4e short-name convention ("EGFP random-50" / "Var-len human") —
they alone set the label-column width; with them trimmed, the "Novel 5′UTR"
rows set the floor and the canvas narrows accordingly.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles —
the headline lives in the caption and the arm names are plain column
headers; every text element one 6-pt pure-black style; colours only from
palette rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm
geometry; exact canvas (no tight crop).

Data  : experiments/results/exp18_mrna_claim_gating/summary.json
        (+ experiments/e18_audit_tasks_mrna.json for task order/labels)
Usage : python experiments/plots/fig4d_mrna_family_strip.py
Output : experiments/plots/output/fig4d_mrna_family_strip.{pdf,png}
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
SUMMARY = PROJECT_ROOT / "experiments" / "results" / "exp18_mrna_claim_gating" / "summary.json"
TASKS_JSON = PROJECT_ROOT / "experiments" / "e18_audit_tasks_mrna.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

VERDICT_COLORS = {
    "TP": PALETTE_BY_NAME["sage_green"],
    "FP": PALETTE_BY_NAME["terracotta"],
    "neutral": PALETTE_BY_NAME["warm_grey"],
    "suppressed": PALETTE_BY_NAME["dark_warm_grey"],  # the fig4b convention
}
VERDICT_LABELS = {"TP": "True positive", "FP": "False claim", "neutral": "Neutral",
                  "suppressed": "Suppressed"}
VERDICT_ORDER = ("TP", "FP", "neutral", "suppressed")
ARM_ORDER = ("ungated", "gated")
ARM_LABELS = {"ungated": "Ungated", "gated": "Gated"}

# Family header labels (single line — the hierarchical layout gives them the
# full label-column width).
FAMILY_LABELS = {
    "cds_cai_report": "CAI report",
    "cds_mfe_report": "MFE report",
    "cds_constraint_report": "Constraints",
    "cds_relative_compare": "Relative comparison",
    "utr3_stability_rank": "3′UTR stability rank",
    "cross_family_expression": "Cross-family MRL",
    "junction_quality": "Junction quality",
    "mrl_optimum": "MRL optimum",
}

# Per-row target labels: protein targets keep the benchmark display names;
# the two Sample-2019 libraries carry the compact fig4e short names (the
# fig3f full names "Random 50-nt 5′UTRs" / "Varying-length human 5′UTRs"
# alone set a 22.5-mm label column — shortened on same-day user review;
# their full names remain in Fig. 3f and the Fig. 4e legend), and the
# never-profiled families their e18 production numbering, with the 5′ prime.
_ROW_LABEL_OVERRIDES = {
    "sample2019_egfp_random50": "EGFP random-50",
    "sample2019_varying_length_human": "Var-len human",
}

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


def task_rows() -> list[dict]:
    """Task-set order -> rows of (family, category, row label, task_id)."""
    payload = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    rows = []
    for t in payload["tasks"]:
        raw_label = t["target_family"]
        label = _ROW_LABEL_OVERRIDES.get(raw_label, raw_label)
        if raw_label.startswith("novel_"):
            label = f"Novel 5′UTR {raw_label.rsplit('_', 1)[1]}"
        rows.append({
            "family": t["task_family"],
            "category": t["category"],
            "task_id": t["id"],
            "label": label,
        })
    return rows


def text_w_mm(fig, s: str) -> float:
    """Renderer-measured 6-pt string width in mm (the fig4b/fig4e convention)."""
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, s, fontsize=FONT, color=INK)
    bb = probe.get_window_extent(r)
    probe.remove()
    return bb.width / fig.dpi * 25.4


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    matrix = summary["per_task_matrix"]
    rows = task_rows()
    arms = summary["arms"]

    # consecutive family groups in task-set order
    groups: list[dict] = []
    for r in rows:
        if not groups or groups[-1]["family"] != r["family"]:
            groups.append({"family": r["family"], "category": r["category"],
                           "rows": []})
        groups[-1]["rows"].append(r)

    max_claims = max((max([sum(v.values()) for v in matrix.get(r["task_id"], {}).values()]
                          or [0]) for r in rows), default=1)

    # ── measured-width single hierarchical label column ──────────────────
    probe = plt.figure(figsize=(4, 4))
    fam_w = max(text_w_mm(probe, FAMILY_LABELS[g["family"]]) for g in groups)
    tgt_w = max(text_w_mm(probe, r["label"]) for r in rows)
    key_w = {v: text_w_mm(probe, VERDICT_LABELS[v]) for v in VERDICT_ORDER}
    none_w = text_w_mm(probe, "No published claim")
    plt.close(probe)

    ML = 1.2                                # outer margin (left = right)
    IND = 2.5                               # target-row indent under headers
    label_right = ML + max(fam_w, IND + tgt_w)
    GAP_TB = 2.2                            # labels -> first block clearance
    block_w = 10.0                          # mm per arm block (≤1 claim/cell)
    block_gap = 7.0                         # mm between the two arm blocks
    ungated_x = label_right + GAP_TB
    gated_x = ungated_x + block_w + block_gap
    fig_w = gated_x + block_w + ML

    tile = min(5.0, (block_w - 2.0 - (max_claims - 1) * 0.6) / max_claims)
    gap_tile = 0.6
    row_h, row_gap = 1.7, 0.7               # mm per task row
    pitch = row_h + row_gap
    fam_header_h = 2.5                      # family header line height
    fam_gap = 1.0                           # extra gap between families
    sep_extra = 0.8                         # extra gap at the category divider

    header_y = 4.2                          # arm-header centre
    rows_y0 = 7.2                           # top edge of the first header

    # ── vertical walk: headers + rows, divider between the categories ────
    layout: list[dict] = []                 # per-row geometry records
    headers: list[tuple[str, float]] = []   # family header (label, centre y)
    sep_y = None
    y = rows_y0
    for gi, g in enumerate(groups):
        if gi:
            gap = fam_gap
            if g["category"] != groups[gi - 1]["category"]:
                gap += sep_extra
                sep_y = y + gap / 2
            y += gap
        headers.append((FAMILY_LABELS[g["family"]], y + fam_header_h / 2))
        y += fam_header_h
        for r in g["rows"]:
            layout.append({"row": r, "y": y})
            y += pitch
        y -= row_gap
    content_bottom = y

    key_top = content_bottom + 3.2
    key_cy = (key_top + 1.0, key_top + 3.2, key_top + 5.4)  # three centred key rows
    fig_h = key_top + 6.4 + ML

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4), facecolor="white")

    def fx(v): return v / fig_w
    def fy(v): return 1 - v / fig_h
    def hm(v): return v / fig_h

    # ── tiles + row (target) labels ──────────────────────────────────────
    for item in layout:
        r, y = item["row"], item["y"]
        fig.text(fx(ML + IND), fy(y + row_h / 2), r["label"], ha="left",
                 va="center", fontsize=FONT, color=INK)
        for b, arm in enumerate(ARM_ORDER):
            counts = (matrix.get(r["task_id"], {}).get(arm) or {})
            seq = [v for v in VERDICT_ORDER for _ in range(counts.get(v, 0))]
            bx = ungated_x if b == 0 else gated_x
            span = len(seq) * tile + max(0, len(seq) - 1) * gap_tile
            tx = bx + (block_w - span) / 2 if span else bx
            if not seq:
                # no published claim: outlined placeholder tile (key-matched)
                fig.patches.append(Rectangle(
                    (fx(bx + block_w / 2 - tile / 2), fy(y + row_h)),
                    fx(tile), hm(row_h),
                    facecolor="white", edgecolor=INK, linewidth=0.5,
                    transform=fig.transFigure, zorder=2))
            for k, verdict in enumerate(seq):
                fig.patches.append(Rectangle(
                    (fx(tx + k * (tile + gap_tile)), fy(y + row_h)),
                    fx(tile), hm(row_h),
                    facecolor=VERDICT_COLORS[verdict], edgecolor="none",
                    transform=fig.transFigure, zorder=2))

    # family headers, left-aligned on their own line above each group
    for label, cy in headers:
        fig.text(fx(ML), fy(cy), label, ha="left", va="center",
                 fontsize=FONT, color=INK)

    # category-block divider between the deterministic and oracle blocks
    assert sep_y is not None
    fig.lines.append(plt.Line2D(
        [fx(ML), fx(fig_w - ML)], [fy(sep_y), fy(sep_y)],
        color=INK, linewidth=0.6, transform=fig.transFigure, zorder=1))

    # block headers (arm labels centred exactly above each tile column)
    for b, arm in enumerate(ARM_ORDER):
        bx = ungated_x if b == 0 else gated_x
        fig.text(fx(bx + block_w / 2), fy(header_y), ARM_LABELS[arm],
                 ha="center", va="center", fontsize=FONT, color=INK)

    # ── verdict key: three rows on a shared column grid, block centred ────
    key_rows = [
        [("TP", VERDICT_LABELS["TP"]), ("FP", VERDICT_LABELS["FP"])],
        [("neutral", VERDICT_LABELS["neutral"]),
         ("suppressed", VERDICT_LABELS["suppressed"])],
        [("none", "No published claim")],
    ]
    sw_w, sw_h, gap_st, gap_e = 2.4, 1.6, 0.8, 3.0
    # column widths shared across the rows -> swatch/label left edges align
    n_cols = max(len(row) for row in key_rows)
    widths = {(v, lbl): key_w.get(v, none_w) for row in key_rows for v, lbl in row}
    col_ws = [max(widths[row[c]] for row in key_rows if c < len(row)) for c in range(n_cols)]
    key_block_w = sum(sw_w + gap_st + w for w in col_ws) + gap_e
    assert key_block_w <= fig_w - 2 * ML, f"verdict key {key_block_w:.1f} mm > canvas"
    for entries, cy in zip(key_rows, key_cy):
        x = (fig_w - key_block_w) / 2
        for c, (v, lbl) in enumerate(entries):
            fig.patches.append(Rectangle(
                (fx(x), fy(cy + sw_h / 2)), fx(sw_w), hm(sw_h),
                facecolor=VERDICT_COLORS.get(v, "white"),
                edgecolor=INK if v == "none" else "none",
                linewidth=0.5, transform=fig.transFigure))
            fig.text(fx(x + sw_w + gap_st), fy(cy), lbl,
                     ha="left", va="center", fontsize=FONT, color=INK)
            x += sw_w + gap_st + col_ws[c] + gap_e

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4d_mrna_family_strip.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None, facecolor="white")
    plt.close(fig)
    u, g = arms["ungated"], arms["gated"]
    print(f"fig4d -> {OUT_DIR / 'fig4d_mrna_family_strip.pdf'} (+png 1200 dpi); "
          f"canvas {fig_w:.1f} x {fig_h:.1f} mm; "
          f"ungated TP {u['TP']}/FP {u['FP']}/neutral {u['neutral']}, "
          f"gated TP {g['TP']}/FP {g['FP']}/neutral {g['neutral']}; "
          f"fp {u['fp_rate']:.3f} -> {g['fp_rate']:.3f}, "
          f"tp_retention {summary['tp_retention']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
