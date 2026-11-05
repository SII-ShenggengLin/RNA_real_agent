"""Fig 3e — claim overreach of the ungated agent (bar panel).

Horizontal bars — plan-level overreach events of the ungated control
arm (Experiment 5) by oracle and intended use (plan requests of a
structural oracle in ranking / screening use); oracle
colours as in Figs 3b–3e (EGARPS terracotta, ProteinX slate blue, RhoFold
sage green); solid = ranking use, 55% alpha = screening use.

The per-claim adjudication waffle was dropped on user direction
(2026-08-30, second revision): the class selectivity it encoded — 23/23
claims true on the trusted-deterministic tasks versus 30/32 false on the
untrusted-oracle tasks — is stated in one sentence in the Fig. 3e caption
and the main text; the FP-rate headline likewise lives in the caption.

Style (2026-08-30 user-directed revisions, Nature conventions): no
in-figure titles or summary statistics — the panel letter is added at
figure assembly and the headline numbers live in the Fig. 3e caption; the
legend is a single-row six-swatch style key centred on the axes directly
under the panel — the three oracle colours solid (ranking use) then
light (screening use), one swatch per bar style; oracle
labels are centred on their bar pairs; every text element one 6-pt
pure-black style; colours only from palette rev 7; 1200-dpi PNG (Nature
Methods line-art guidance) + vector PDF (fonttype 42).

2026-10-02 revision (Fig. 3 text-sync batch, user-adjudicated): the x-axis
label "Decision-layer overreach events" retired to bare "Overreach events"
(the fig4f precedent — the qualifier lives in the Fig. 3e caption's
"plan-level events"; "decision-layer" collides with the L0–L6 layer names)
and the key labels synced to the caption's "ranking and screening use";
the canvas narrowed to 57.2 mm so d, e and f share one three-column row
(the user-directed 2026-10-02 layout; fonts unchanged 6-pt, no data
change).
2026-10-10 revision (Fig. 3 row-3 alignment batch, user-directed): the
canvas and axes moved to the shared exact-millimetre row-3 geometry
(`fig3_row3_layout.py` — 54.0 x 52.0 mm canvas, axes 12.0/12.0/41.0/36.0,
identical with panels d and f so the three axes land on the same lines at
assembly) and the tight-crop save retired (the figS house convention).
The taller shared axes (24 → 36 mm) spreads the six bars; the style-key
row below was tightened (swatch 2.4 → 2.2 mm, pitch 3.0 → 2.7, gaps
1.4/3.0 → 1.2/2.2, label widths re-measured) so it stays a single row
within the 54.0 mm canvas, clamped to the canvas edge after centring on
the axes (1.0 mm residual offset, imperceptible); fonts unchanged 6-pt,
no data change.

Data: experiments/results/exp5_claim_overreach/runs.jsonl (+
_summary.json). Output: experiments/plots/output/fig3e_claim_overreach.
{pdf,png}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fig3_row3_layout import (  # noqa: E402
    AX_B_MM, AX_H_MM, AX_L_MM, AX_W_MM, CANVAS_H_MM, CANVAS_W_MM)
from palette import PALETTE_BY_NAME  # noqa: E402

RESULTS = PROJECT_ROOT / "experiments" / "results" / "exp5_claim_overreach"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"   # 2026-08-30 user direction: every text element pure black
FONT = 6          # single font size for every in-figure text element

ORACLE_COLORS = {
    "rhofold_mean_plddt": PALETTE_BY_NAME["sage_green"],
    "proteinx_ipTM": PALETTE_BY_NAME["slate_blue"],
    "egarps_native_probability": PALETTE_BY_NAME["terracotta"],
}
ORACLE_LABELS = {
    "rhofold_mean_plddt": "RhoFold",
    "proteinx_ipTM": "ProteinX",
    "egarps_native_probability": "EGARPS",
}
ORACLE_ORDER = ["rhofold_mean_plddt", "proteinx_ipTM", "egarps_native_probability"]
USE_ALPHA = {"ranking_objective": 1.0, "screening_evaluation": 0.55}
USE_LABELS = {"ranking_objective": "ranking use",
              "screening_evaluation": "screening use"}

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


def load_data(results_dir: Path) -> tuple[dict, list[dict]]:
    sum_path = results_dir / "runs_summary.json"
    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    runs_rows = [json.loads(l) for l in (results_dir / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    return summary, runs_rows


def draw_bars(ax, runs_rows: list[dict]) -> None:
    events = [ev for r in runs_rows if not r.get("error") for ev in r.get("overreach_events", [])]
    counts: dict[tuple[str, str], int] = {}
    for ev in events:
        counts[(ev["oracle"], ev["use"])] = counts.get((ev["oracle"], ev["use"]), 0) + 1

    group_centers: list[float] = []
    group_labels: list[str] = []
    y = 0.0
    for oracle in ORACLE_ORDER:
        pair: list[float] = []
        for use in ("ranking_objective", "screening_evaluation"):
            n = counts.get((oracle, use), 0)
            ax.barh(y, n, height=0.62, color=ORACLE_COLORS[oracle],
                    alpha=USE_ALPHA[use], edgecolor="none")
            if n > 0:
                ax.text(n + 0.25, y, str(n), va="center", ha="left",
                        fontsize=FONT, color=INK)
            pair.append(y)
            y -= 1.0
        group_centers.append(sum(pair) / len(pair))  # label centred on the pair
        group_labels.append(ORACLE_LABELS[oracle])
        y -= 0.4

    ax.set_yticks(group_centers)
    ax.set_yticklabels(group_labels, fontsize=FONT, color=INK)
    ax.tick_params(axis="y", length=0, pad=2)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
    ax.set_xlim(0, 13)
    ax.set_xticks(range(0, 13, 2))
    ax.set_ylim(-6.8, 0.7)
    ax.set_xlabel("Overreach events", fontsize=FONT, labelpad=2)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)


def main() -> int:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    summary, runs_rows = load_data(results_dir)

    # shared row-3 geometry (fig3_row3_layout.py) — exact canvas, no tight
    # crop, so the axes rectangle is identical in panels d, e and f
    fig_w, fig_h = CANVAS_W_MM / 25.4, CANVAS_H_MM / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_b = fig.add_axes([AX_L_MM / CANVAS_W_MM, AX_B_MM / CANVAS_H_MM,
                         AX_W_MM / CANVAS_W_MM, AX_H_MM / CANVAS_H_MM])

    draw_bars(ax_b, runs_rows)

    # style key under the panel, one row centred on the axes (2026-08-30 user
    # direction): one swatch per bar style — the three oracle colours solid
    # (ranking objective) then light (screening evaluation).  2026-10-10:
    # metrics tightened for the shared row-3 canvas (swatch 2.4 → 2.2 mm,
    # pitch 3.0 → 2.7, gap 1.4 → 1.2, group gap 3.0 → 2.2, label widths
    # re-measured at 6 pt) and the centred position clamped to the canvas —
    # the axes sit right of the canvas centre (the y-label stack), so the
    # 44 mm key row can no longer centre on them unclamped
    def _fx(v: float) -> float: return v / 25.4 / fig_w   # mm → figure frac
    def _fy(v: float) -> float: return v / 25.4 / fig_h
    sw_w, sw_h, pitch, gap, group_gap = 2.2, 1.6, 2.7, 1.2, 2.2
    trio_w = sw_w + 2 * pitch
    label_w = {"ranking_objective": 11.0, "screening_evaluation": 13.2}
    row_w = 2 * (trio_w + gap) + group_gap + sum(label_w.values())
    x0 = (AX_L_MM + AX_W_MM / 2) - row_w / 2              # row centred on the axes
    x0 = min(x0, CANVAS_W_MM - 0.5 - row_w)               # …clamped to the canvas
    assert x0 >= 0.5, (
        f"style key overflows the canvas: {x0:.2f} .. {x0 + row_w:.2f} mm")
    x = x0
    for use in ("ranking_objective", "screening_evaluation"):
        for i, oracle in enumerate(ORACLE_ORDER):
            fig.patches.append(plt.Rectangle(
                (_fx(x + i * pitch), _fy(2.6 - sw_h / 2)),
                _fx(sw_w), _fy(sw_h),
                facecolor=ORACLE_COLORS[oracle], alpha=USE_ALPHA[use],
                edgecolor="none", transform=fig.transFigure))
        x += trio_w + gap
        fig.text(_fx(x), _fy(2.6), USE_LABELS[use],
                 ha="left", va="center", fontsize=FONT, color=INK)
        x += label_w[use] + group_gap

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3e_claim_overreach.{ext}"
        # exact-canvas save (no tight crop) — the row-3 alignment convention
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white")
    plt.close(fig)
    ov = summary["overall"]
    print(f"fig3e -> {OUT_DIR / 'fig3e_claim_overreach.pdf'} "
          f"(+png 1200 dpi); FP={ov['FP']}, TP={ov['TP']}, "
          f"events={summary['overreach_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
