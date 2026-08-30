"""Fig 3f — claim overreach of the ungated agent (bar panel).

Horizontal bars — decision-layer overreach events of the ungated control
arm (Experiment 5) by oracle and intended use (plan requests of a
structural oracle as ranking objective / screening evaluation); oracle
colours as in Figs 3b–3e (EGARPS terracotta, ProteinX slate blue, RhoFold
sage green); solid = ranking objective, 55% alpha = screening evaluation.

The per-claim adjudication waffle was dropped on user direction
(2026-08-30, second revision): the class selectivity it encoded — 23/23
claims true on the trusted-deterministic tasks versus 30/32 false on the
untrusted-oracle tasks — is stated in one sentence in the Fig. 3f caption
and the main text; the FP-rate headline likewise lives in the caption.

Style (2026-08-30 user-directed revisions, Nature conventions): no
in-figure titles or summary statistics — the panel letter is added at
figure assembly and the headline numbers live in the Fig. 3f caption; the
legend is a single-row six-swatch style key centred on the axes directly
under the panel — the three oracle colours solid (ranking objective) then
light (screening evaluation), one swatch per bar style; oracle
labels are centred on their bar pairs; every text element one 6-pt
pure-black style; colours only from palette rev 7; 1200-dpi PNG (Nature
Methods line-art guidance) + vector PDF (fonttype 42).

Data: experiments/results/exp5_claim_overreach/runs.jsonl (+
_summary.json). Output: experiments/plots/output/fig3f_claim_overreach.
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
USE_LABELS = {"ranking_objective": "ranking objective",
              "screening_evaluation": "screening evaluation"}

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
    ax.set_xlabel("Decision-layer overreach events", fontsize=FONT, labelpad=2)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)


def main() -> int:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    summary, runs_rows = load_data(results_dir)

    # absolute-mm geometry (the fig3g convention): single-column 89 mm wide
    fig_w, fig_h = 89 / 25.4, 34 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax_b = fig.add_axes([15 / 25.4 / fig_w, 11 / 25.4 / fig_h,
                         71 / 25.4 / fig_w, 21 / 25.4 / fig_h])

    draw_bars(ax_b, runs_rows)

    # style key under the panel, one row centred on the axes (2026-08-30 user
    # direction): one swatch per bar style — the three oracle colours solid
    # (ranking objective) then light (screening evaluation)
    def _fx(v: float) -> float: return v / 25.4 / fig_w   # mm → figure frac
    def _fy(v: float) -> float: return v / 25.4 / fig_h
    sw_w, sw_h, pitch, gap, group_gap = 2.4, 1.6, 3.0, 1.6, 3.5
    trio_w = sw_w + 2 * pitch
    label_w = {"ranking_objective": 19.0, "screening_evaluation": 23.0}
    row_w = 2 * (trio_w + gap) + group_gap + sum(label_w.values())
    x0 = (15 + 71 / 2) - row_w / 2                        # row centred on the axes
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
        out = OUT_DIR / f"fig3f_claim_overreach.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    ov = summary["overall"]
    print(f"fig3f -> {OUT_DIR / 'fig3f_claim_overreach.pdf'} "
          f"(+png 1200 dpi); FP={ov['FP']}, TP={ov['TP']}, "
          f"events={summary['overreach_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
