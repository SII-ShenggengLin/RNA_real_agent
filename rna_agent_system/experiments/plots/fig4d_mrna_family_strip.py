"""Fig 4d — E3-M mRNA-side dual-arm re-run: per-task-family verdict strips.

One row per audit task (20 tasks grouped into the eight task families,
trusted-deterministic families above, untrusted-oracle families below), two
column blocks (Ungated control arm / Gated treatment arm); one colour tile
per published claim — sage = true positive, terracotta = false claim, warm
grey = neutral relative-scope claim; an empty cell means the arm published
no claim on that task (the gated arm's plan-layer blocks make the model
abstain on the utr3/junction families — the mechanism this panel shows).
A summary mosaic inset (arm columns × verdict segments, heights proportional
to claim counts) sits at the panel's right over the empty claim space.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles;
every text element one 6-pt pure-black style; colours only from palette
rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm geometry.

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
    "TP": PALETTE_BY_NAME["sage_green"],   # retained (true positive)
    "FP": PALETTE_BY_NAME["terracotta"],   # false claim
    "neutral": PALETTE_BY_NAME["warm_grey"],
    "suppressed": PALETTE_BY_NAME["dark_warm_grey"],
}
VERDICT_LABELS = {"TP": "True positive", "FP": "False claim",
                  "neutral": "Neutral", "suppressed": "Suppressed"}
VERDICT_ORDER = ("TP", "FP", "neutral", "suppressed")
ARM_ORDER = ("ungated", "gated")
ARM_LABELS = {"ungated": "Ungated", "gated": "Gated"}

# Family display names and row labels (target / seed) in task-set order.
FAMILY_LABELS = {
    "cds_cai_report": "CAI report",
    "cds_mfe_report": "MFE report",
    "cds_constraint_report": "Constraints",
    "cds_relative_compare": "Relative compare",
    "utr3_stability_rank": "3\u2032UTR rank",
    "cross_family_expression": "Cross-family MRL",
    "junction_quality": "Junction quality",
    "mrl_optimum": "MRL optimum",
}

_ROW_LABEL_OVERRIDES = {
    "sample2019_egfp_random50": "EGFP random50",
    "sample2019_varying_length_human": "VL human",
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
            label = f"seed {raw_label.rsplit('_', 1)[1]}"
        rows.append({
            "family": t["task_family"],
            "category": t["category"],
            "task_id": t["id"],
            "label": label,
        })
    return rows


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    matrix = summary["per_task_matrix"]
    rows = task_rows()
    arms = summary["arms"]

    n_rows = len(rows)
    max_claims = max((max([sum(v.values()) for v in matrix.get(r["task_id"], {}).values()]
                          or [0]) for r in rows), default=1)

    # Fixed block widths; claim tiles shrink to fit denser rows.
    block_w = 12.0                          # mm per arm block
    tile = min(2.0, (block_w - 1.0) / max(1, max_claims) - 0.5)
    gap_tile = 0.5 if tile >= 1.2 else 0.3
    row_h, row_gap = 1.55, 0.55             # mm per task row
    block_gap = 5.0                         # mm between the two arm blocks
    fam_w, tgt_w = 24.0, 16.0               # family + target label columns
    left_x = fam_w + tgt_w + 2.0
    gated_x = left_x + block_w + block_gap
    mx_w = 16.0
    fig_w = gated_x + block_w + 4.0 + mx_w + 2.0
    fig_h = 10.0 + n_rows * (row_h + row_gap) + 8.0

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4), facecolor="white")

    # mm → figure fraction helpers
    def _fx(v: float) -> float: return v / fig_w
    def _fy(v: float) -> float: return 1 - v / fig_h
    def _h_mm(v: float) -> float: return v / fig_h

    y = 10.0
    fam_spans: dict[str, list[float]] = {}
    det_end = sum(1 for r in rows if r["category"] == "trusted_deterministic")
    for r in rows:
        fig.text(_fx(fam_w), _fy(y + row_h / 2), r["label"], ha="right",
                 va="center", fontsize=FONT, color=INK)
        for b, arm in enumerate(ARM_ORDER):
            counts = (matrix.get(r["task_id"], {}).get(arm) or {})
            seq = [v for v in VERDICT_ORDER for _ in range(counts.get(v, 0))]
            bx = (left_x if b == 0 else gated_x)
            span = len(seq) * tile + max(0, len(seq) - 1) * gap_tile
            tx = bx + (block_w - span) / 2 if span else bx
            if not seq:
                # no published claim: outlined placeholder tile (key-matched)
                fig.patches.append(Rectangle(
                    (_fx(bx + block_w / 2 - tile / 2), _fy(y + row_h)),
                    _fx(tile), _h_mm(row_h),
                    facecolor="white", edgecolor=INK, linewidth=0.4,
                    transform=fig.transFigure, zorder=2))
            for i, verdict in enumerate(seq):
                fig.patches.append(Rectangle(
                    (_fx(tx + i * (tile + gap_tile)), _fy(y + row_h)),
                    _fx(tile), _h_mm(row_h),
                    facecolor=VERDICT_COLORS[verdict], edgecolor="none",
                    transform=fig.transFigure, zorder=2))
        fam_spans.setdefault(r["family"], []).append(y)
        y += row_h + row_gap

    # family labels centred on their row groups
    for fam, ys in fam_spans.items():
        cy = (min(ys) + max(ys) + row_h) / 2
        fig.text(_fx(1.0), _fy(cy), FAMILY_LABELS[fam], ha="left", va="center",
                 fontsize=FONT, color=INK)

    # category-block separator between the deterministic and oracle blocks
    sep_y = 10.0 + det_end * (row_h + row_gap) - row_gap / 2
    fig.lines.append(plt.Line2D(
        [_fx(left_x - 1.0), _fx(gated_x + block_w + 1.0)],
        [_fy(sep_y), _fy(sep_y)], color=INK, linewidth=0.4,
        transform=fig.transFigure, zorder=1))

    # block headers (arm labels centred above each block)
    for b, arm in enumerate(ARM_ORDER):
        bx = left_x if b == 0 else gated_x
        fig.text(_fx(bx + block_w / 2), _fy(6.0), ARM_LABELS[arm],
                 ha="center", va="center", fontsize=FONT, color=INK)

    # group bracket labels (rotated) at the two category-block boundaries
    y_det = 10.0 + (det_end * (row_h + row_gap) - row_gap) / 2
    y_unt = 10.0 + det_end * (row_h + row_gap) + \
        ((n_rows - det_end) * (row_h + row_gap) - row_gap) / 2
    for yy, lab in ((y_det, "Trusted-deterministic"), (y_unt, "Untrusted-oracle")):
        fig.text(_fx(left_x - 6.5), _fy(yy), lab, ha="center", va="center",
                 rotation=90, fontsize=FONT, color=INK)

    # ── mosaic inset: claim composition per arm ───────────────────────────
    mx_h = min(22.0, fig_h - 14.0)
    mx_x = fig_w - mx_w - 3.0
    mx_y = 9.5
    col_w = 5.2
    totals = {a: sum(arms[a][v] for v in VERDICT_ORDER) for a in ARM_ORDER}
    max_total = max(totals.values())
    for b, arm in enumerate(ARM_ORDER):
        cx = mx_x + b * (col_w + 2.2)
        yy = mx_y
        for v in VERDICT_ORDER:
            n = arms[arm][v]
            if not n:
                continue
            seg_h = mx_h * n / max_total
            fig.patches.append(Rectangle(
                (_fx(cx), _fy(yy + seg_h)), _fx(col_w),
                _fy(yy) - _fy(yy + seg_h),
                facecolor=VERDICT_COLORS[v], edgecolor="white",
                linewidth=0.4, transform=fig.transFigure, zorder=3))
            if n / max_total > 0.10:
                fig.text(_fx(cx + col_w / 2), _fy(yy + seg_h / 2), str(n),
                         ha="center", va="center", fontsize=FONT, color=INK,
                         zorder=4)
            yy += seg_h
        fig.text(_fx(cx + col_w / 2), _fy(mx_y - 2.6), ARM_LABELS[arm],
                 ha="center", va="center", fontsize=FONT, color=INK)

    # ── verdict key: one centred row under the matrix ─────────────────────
    key_verdicts = [v for v in VERDICT_ORDER
                    if any(matrix.get(r["task_id"], {}).get(a, {}).get(v)
                           for r in rows for a in ARM_ORDER)] + ["none"]
    key_labels = dict(VERDICT_LABELS)
    key_labels["none"] = "No published claim"
    key_colors = dict(VERDICT_COLORS)
    key_colors["none"] = "white"
    key_y = fig_h - 4.6
    sw_w, sw_h, pitch, gap_k = 2.4, 1.6, 3.0, 1.6
    label_w = {"TP": 16.5, "FP": 14.5, "neutral": 12.0, "suppressed": 16.0,
               "none": 24.0}
    row_w = sum(pitch + label_w[v] + gap_k for v in key_verdicts) - gap_k
    x = (fig_w - row_w) / 2
    for v in key_verdicts:
        fig.patches.append(Rectangle(
            (_fx(x), _fy(key_y + sw_h / 2)), _fx(sw_w),
            _fy(key_y - sw_h / 2) - _fy(key_y + sw_h / 2),
            facecolor=key_colors[v],
            edgecolor=INK if v == "none" else "none",
            linewidth=0.4, transform=fig.transFigure))
        fig.text(_fx(x + pitch), _fy(key_y), key_labels[v],
                 ha="left", va="center", fontsize=FONT, color=INK)
        x += pitch + label_w[v] + gap_k

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4d_mrna_family_strip.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
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
