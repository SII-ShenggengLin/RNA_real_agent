"""Fig 4b — per-claim adjudication matrix of the E3 dual-arm re-run.

One row per audit task (45 tasks; trusted-deterministic block above,
untrusted-oracle block below), two column blocks (Ungated control arm =
Exp 5, Gated treatment arm = Exp 17); one colour tile per published claim,
green (sage) = retained true positive, red (terracotta) = false claim —
the Biomni Fig. 2C–E correct/incorrect matrix encoding; suppressed claims
dark warm grey; borderline claims warm grey. A summary mosaic inset (arm
columns x verdict segments, heights proportional to claim counts) sits at
the panel's top right over the empty claim space of low-claim rows.

Style (Nature conventions, the fig3-panel house style): no in-figure
titles; every text element one 6-pt pure-black style; colours only from
palette rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm
geometry.

Data  : experiments/results/exp17_claim_gating/summary.json
        (+ experiments/e5_audit_tasks.json for task order/labels)
Usage : python experiments/plots/fig4b_claim_matrix.py
Output : experiments/plots/output/fig4b_claim_matrix.{pdf,png}
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

VERDICT_COLORS = {
    "TP": PALETTE_BY_NAME["sage_green"],          # retained (true positive)
    "FP": PALETTE_BY_NAME["terracotta"],          # false claim
    "suppressed": PALETTE_BY_NAME["dark_warm_grey"],
    "borderline": PALETTE_BY_NAME["warm_grey"],
}
VERDICT_LABELS = {"TP": "True positive", "FP": "False claim",
                  "suppressed": "Suppressed", "borderline": "Borderline"}
VERDICT_ORDER = ("TP", "FP", "suppressed", "borderline")
ARM_ORDER = ("ungated", "gated")
ARM_LABELS = {"ungated": "Ungated", "gated": "Gated"}

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


def task_rows() -> list[tuple[str, str]]:
    payload = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    det = [t for t in payload["tasks"] if t["category"] == "trusted_deterministic"]
    unt = [t for t in payload["tasks"] if t["category"] == "untrusted_oracle"]
    fam = {"gc_target": "GC target", "u_reduce": "U reduce",
           "purine_band": "Purine band"}
    rows = [(t["id"], fam.get(t["task_family"], t["id"])) for t in det]
    rows += [(t["id"], t["target_family"]) for t in unt]
    return rows


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    matrix = summary["per_task_matrix"]
    rows = task_rows()

    n_rows = len(rows)
    max_claims = max((max([sum(v.values()) for v in matrix.get(tid, {}).values()]
                          or [0]) for tid, _ in rows), default=1)

    # Fixed block widths; claim tiles shrink to fit denser rows.
    block_w = 12.0                          # mm per arm block
    tile = min(2.0, (block_w - 1.0) / max(1, max_claims) - 0.5)
    gap_tile = 0.5 if tile >= 1.2 else 0.3
    row_h, row_gap = 1.55, 0.55             # mm per task row
    block_gap = 5.0                         # mm between the two arm blocks
    label_w = 24.0                          # row-label column
    left_x = label_w + 2.0
    gated_x = left_x + block_w + block_gap
    mx_w, mx_col = 16.0, 5.2                # mosaic inset
    fig_w = gated_x + block_w + 4.0 + mx_w + 2.0
    fig_h = 10.0 + n_rows * (row_h + row_gap) + 8.0

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4), facecolor="white")

    # mm → figure fraction (fig_w/fig_h are millimetres here; unlike the
    # fig3e convention of inch-sized variables, no extra /25.4)
    def _fx(v: float) -> float: return v / fig_w
    def _fy(v: float) -> float: return 1 - v / fig_h
    def _h_mm(v: float) -> float: return v / fig_h

    y = 10.0
    det_end = sum(1 for tid, _ in rows if not tid.startswith("aptamer_"))
    for tid, label in rows:
        fig.text(_fx(2.0), _fy(y + row_h / 2), label, ha="left", va="center",
                 fontsize=FONT, color=INK)
        for b, arm in enumerate(ARM_ORDER):
            counts = (matrix.get(tid, {}).get(arm) or {})
            seq = [v for v in VERDICT_ORDER for _ in range(counts.get(v, 0))]
            bx = (left_x if b == 0 else gated_x)
            span = len(seq) * tile + max(0, len(seq) - 1) * gap_tile
            tx = bx + (block_w - span) / 2 if span else bx
            for i, verdict in enumerate(seq):
                fig.patches.append(Rectangle(
                    (_fx(tx + i * (tile + gap_tile)), _fy(y + row_h)),
                    _fx(tile), _h_mm(row_h),
                    facecolor=VERDICT_COLORS[verdict], edgecolor="none",
                    transform=fig.transFigure, zorder=2))
        y += row_h + row_gap

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
        fig.text(_fx(left_x - 4.5), _fy(yy), lab, ha="center", va="center",
                 rotation=90, fontsize=FONT, color=INK)

    # ── mosaic inset: claim composition per arm ───────────────────────────
    mx_w, mx_h = 16.0, min(22.0, fig_h - 14.0)
    mx_x = fig_w - mx_w - 3.0
    mx_y = 9.5
    arms = summary["arms"]
    col_w = 5.2
    totals = {a: sum(arms[a][v] for v in VERDICT_ORDER) for a in ARM_ORDER}
    max_total = max(totals.values())
    for b, arm in enumerate(ARM_ORDER):
        cx = mx_x + b * (col_w + 1.6)
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
    key_y = fig_h - 4.6
    sw_w, sw_h, pitch, gap_k = 2.4, 1.6, 3.0, 1.6
    label_w = {"TP": 16.5, "FP": 14.5, "suppressed": 16.0, "borderline": 14.0}
    row_w = sum(pitch + label_w[v] + gap_k for v in VERDICT_ORDER) - gap_k
    x = (fig_w - row_w) / 2
    for v in VERDICT_ORDER:
        fig.patches.append(Rectangle(
            (_fx(x), _fy(key_y + sw_h / 2)), _fx(sw_w),
            _fy(key_y - sw_h / 2) - _fy(key_y + sw_h / 2),
            facecolor=VERDICT_COLORS[v], edgecolor="none",
            transform=fig.transFigure))
        fig.text(_fx(x + pitch), _fy(key_y), VERDICT_LABELS[v],
                 ha="left", va="center", fontsize=FONT, color=INK)
        x += pitch + label_w[v] + gap_k

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4b_claim_matrix.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    u, g = arms["ungated"], arms["gated"]
    print(f"fig4b -> {OUT_DIR / 'fig4b_claim_matrix.pdf'} (+png 1200 dpi); "
          f"ungated TP {u['TP']}/FP {u['FP']}, gated TP {g['TP']}/FP {g['FP']}/"
          f"supp {g['suppressed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
