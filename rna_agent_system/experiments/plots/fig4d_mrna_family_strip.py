"""Fig 4d — E3-M mRNA-side dual-arm re-run: per-task-family verdict strips.

One row per audit task (20 tasks grouped into the eight task families,
trusted-deterministic families above, untrusted-oracle families below), two
column blocks (Ungated control arm / Gated treatment arm); one colour tile
per published claim — sage = true positive, terracotta = false claim, warm
grey = neutral relative-scope claim; an empty cell means the arm published
no claim on that task (the gated arm's plan-layer blocks make the model
abstain on the utr3/junction families — the mechanism this panel shows).
Category blocks (trusted / untrusted) read left to right: rotated category
label, family label, target label, then the two tile blocks.

2026-09-01 user-directed repair pass:
  - the arm × verdict mosaic inset was removed (its counts are stated in the
    Fig. 4d caption and main text — the fig4b precedent);
  - all left labels rebuilt with renderer-measured text extents so family /
    target / category labels can never overlap; the four longest family
    labels wrap onto two lines;
  - labels: "seed 7/11/13" relabelled to "Novel 5′UTR 7/11/13", libraries
    relabelled "EGFP random-50" / "Var-len human" (fig4e conventions);
    rotated category labels moved to the far left.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles;
every text element one 6-pt pure-black style; colours only from palette
rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm geometry; exact
canvas (no tight crop).

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
    "suppressed": PALETTE_BY_NAME["dark_warm_grey"],
}
VERDICT_LABELS = {"TP": "True positive", "FP": "False claim",
                  "neutral": "Neutral", "suppressed": "Suppressed"}
VERDICT_ORDER = ("TP", "FP", "neutral", "suppressed")
ARM_ORDER = ("ungated", "gated")
ARM_LABELS = {"ungated": "Ungated", "gated": "Gated"}

# Family display names (the four longest wrap onto two lines).
FAMILY_LABELS = {
    "cds_cai_report": "CAI report",
    "cds_mfe_report": "MFE report",
    "cds_constraint_report": "Constraints",
    "cds_relative_compare": "Relative\ncompare",
    "utr3_stability_rank": "3\u2032UTR rank",
    "cross_family_expression": "Cross-family\nMRL",
    "junction_quality": "Junction\nquality",
    "mrl_optimum": "MRL\noptimum",
}

_ROW_LABEL_OVERRIDES = {
    "sample2019_egfp_random50": "Random-50",
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
    """Task-set order -> rows of (family, row_label, task_id)."""
    payload = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    rows = []
    for t in payload["tasks"]:
        raw_label = t["target_family"]
        label = _ROW_LABEL_OVERRIDES.get(raw_label, raw_label)
        if raw_label.startswith("novel_"):
            label = f"Novel UTR {raw_label.rsplit('_', 1)[1]}"
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

    n_rows = len(rows)
    max_claims = max((max([sum(v.values()) for v in matrix.get(r["task_id"], {}).values()]
                          or [0]) for r in rows), default=1)

    block_w = 18.0                          # mm per arm block
    tile = min(5.0, (block_w - 2.0) / max(1, max_claims) - 0.6)
    gap_tile = 0.6 if tile >= 1.4 else 0.4
    row_h, row_gap = 1.7, 0.7               # mm per task row
    pitch = row_h + row_gap
    block_gap = 8.0                         # mm between the two arm blocks

    # ── measured-width left-label zone, then the two tile blocks ─────────
    probe = plt.figure(figsize=(4, 4))
    fam_w = max(max(text_w_mm(probe, ln)
                    for ln in FAMILY_LABELS[r["family"]].split("\n"))
                for r in rows)
    tgt_w = max(text_w_mm(probe, r["label"]) for r in rows)
    plt.close(probe)

    ML = 1.2                                # left margin
    GRP_CX = ML + 1.5                       # rotated category-label centre
    FAM_X = GRP_CX + 1.6                    # family labels left edge
    fam_col = fam_w + 0.6
    CL_FT = 1.6                             # family -> target clearance
    tgt_right = FAM_X + fam_col + CL_FT + tgt_w  # target labels right edge
    GAP_TB = 2.2                            # target -> block clearance
    ungated_x = tgt_right + GAP_TB
    gated_x = ungated_x + block_w + block_gap
    fig_w = gated_x + block_w + ML

    top_margin = 1.8
    header_y = 4.6                          # arm-header centre
    rows_y0 = 7.6                           # top edge of the first row
    key_gap = 3.6
    fig_h = rows_y0 + n_rows * pitch - row_gap + key_gap + 2.4 + ML

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4), facecolor="white")

    def fx(v): return v / fig_w
    def fy(v): return 1 - v / fig_h
    def hm(v): return v / fig_h

    # ── tiles + row (target) labels ──────────────────────────────────────
    fam_spans: dict[str, list[float]] = {}
    for i, r in enumerate(rows):
        y = rows_y0 + i * pitch
        fig.text(fx(tgt_right), fy(y + row_h / 2), r["label"], ha="right",
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
                    facecolor="white", edgecolor=INK, linewidth=0.4,
                    transform=fig.transFigure, zorder=2))
            for k, verdict in enumerate(seq):
                fig.patches.append(Rectangle(
                    (fx(tx + k * (tile + gap_tile)), fy(y + row_h)),
                    fx(tile), hm(row_h),
                    facecolor=VERDICT_COLORS[verdict], edgecolor="none",
                    transform=fig.transFigure, zorder=2))
        fam_spans.setdefault(r["family"], []).append(y)

    # family labels centred on their row groups (two-line where long)
    for fam, ys in fam_spans.items():
        cy = (min(ys) + max(ys) + row_h) / 2
        fig.text(fx(FAM_X), fy(cy), FAMILY_LABELS[fam], ha="left", va="center",
                 fontsize=FONT, color=INK, linespacing=1.05)

    # category-block separator between the deterministic and oracle blocks
    det_end = sum(1 for r in rows if r["category"] == "trusted_deterministic")
    sep_y = rows_y0 + det_end * pitch - row_gap / 2
    fig.lines.append(plt.Line2D(
        [fx(ML), fx(gated_x + block_w)], [fy(sep_y), fy(sep_y)],
        color=INK, linewidth=0.4, transform=fig.transFigure, zorder=1))

    # rotated category labels centred on their 10-row blocks
    y_det = rows_y0 + (det_end * pitch - row_gap) / 2
    y_unt = rows_y0 + det_end * pitch + ((n_rows - det_end) * pitch - row_gap) / 2
    for yy, lab in ((y_det, "Trusted-deterministic"), (y_unt, "Untrusted-oracle")):
        fig.text(fx(GRP_CX), fy(yy), lab, ha="center", va="center",
                 rotation=90, fontsize=FONT, color=INK)

    # block headers (arm labels centred above each block)
    for b, arm in enumerate(ARM_ORDER):
        bx = ungated_x if b == 0 else gated_x
        fig.text(fx(bx + block_w / 2), fy(header_y), ARM_LABELS[arm],
                 ha="center", va="center", fontsize=FONT, color=INK)

    # ── verdict key: one centred row under the matrix ────────────────────
    key_verdicts = [v for v in VERDICT_ORDER
                    if any(matrix.get(r["task_id"], {}).get(a, {}).get(v)
                           for r in rows for a in ARM_ORDER)] + ["none"]
    key_labels = dict(VERDICT_LABELS)
    key_labels["none"] = "No published claim"
    key_colors = dict(VERDICT_COLORS)
    key_colors["none"] = "white"
    key_y = fig_h - ML - 1.2
    sw_w, sw_h, pitch_k, gap_k = 2.4, 1.6, 3.0, 1.6
    probe2 = plt.figure(figsize=(4, 4))
    kw = {v: text_w_mm(probe2, key_labels[v]) for v in key_verdicts}
    plt.close(probe2)
    row_w = sum(pitch_k + kw[v] for v in key_verdicts) + gap_k * (len(key_verdicts) - 1)
    assert row_w <= fig_w - 2 * ML, f"verdict key {row_w:.1f} mm > canvas"
    x = (fig_w - row_w) / 2
    for v in key_verdicts:
        fig.patches.append(Rectangle(
            (fx(x), fy(key_y + sw_h / 2)), fx(sw_w),
            fy(key_y - sw_h / 2) - fy(key_y + sw_h / 2),
            facecolor=key_colors[v], edgecolor=INK if v == "none" else "none",
            linewidth=0.4, transform=fig.transFigure))
        fig.text(fx(x + pitch_k), fy(key_y), key_labels[v], ha="left",
                 va="center", fontsize=FONT, color=INK)
        x += pitch_k + kw[v] + gap_k

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4d_mrna_family_strip.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None, facecolor="white")
    plt.close(fig)
    u, g = arms["ungated"], arms["gated"]
    print(f"fig4d -> {OUT_DIR / 'fig4d_mrna_family_strip.pdf'} (+png 1200 dpi); "
          f"ungated TP {u['TP']}/FP {u['FP']}/neutral {u['neutral']}, "
          f"gated TP {g['TP']}/FP {g['FP']}/neutral {g['neutral']}; "
          f"fp {u['fp_rate']:.3f} -> {g['fp_rate']:.3f}, "
          f"tp_retention {summary['tp_retention']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
