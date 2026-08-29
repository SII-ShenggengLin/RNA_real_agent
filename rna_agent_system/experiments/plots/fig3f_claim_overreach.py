"""Fig 3f — claim overreach of the ungated agent (waffle + bar).

Top: waffle — one tile per adjudicated claim of the ungated control arm
(Experiment 5), ordered deterministic-task claims then aptamer-task claims,
coloured FP terracotta / TP sage green / borderline warm grey (figure-plan
arm→colour code: terracotta = ungated/failure side, sage = true/certified).
Bottom: horizontal bars — decision-layer overreach events by oracle and
intended use (plan requests of a structural oracle as ranking objective /
screening evaluation), oracle colours as in Figs 3b–3e (EGARPS terracotta,
ProteinX slate blue, RhoFold sage green); solid = ranking objective,
55% alpha = screening evaluation.

Style: Nature conventions per the 2026-08-27/28 user-directed revisions —
no in-figure title, every text element one 6-pt ink-black style, compact
in-panel legends; palette rev 7 only.

Data: experiments/results/exp5_claim_overreach/runs.jsonl (+ _adjudicated
.jsonl, _summary.json). Output: experiments/plots/output/fig3f_claim_
overreach.{pdf,png}.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME, TEXT  # noqa: E402

RESULTS = PROJECT_ROOT / "experiments" / "results" / "exp5_claim_overreach"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FP_COLOR = PALETTE_BY_NAME["terracotta"]          # ungated / failure side
TP_COLOR = PALETTE_BY_NAME["sage_green"]          # true / certified
BORDERLINE_COLOR = PALETTE_BY_NAME["warm_grey"]
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

TILES_PER_ROW = 10


def load_data(results_dir: Path) -> tuple[list[dict], dict, list[dict]]:
    adj_path = results_dir / "runs_adjudicated.jsonl"
    sum_path = results_dir / "runs_summary.json"
    adjudicated = [json.loads(l) for l in adj_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    runs_rows = [json.loads(l) for l in (results_dir / "runs.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    return adjudicated, summary, runs_rows


def draw_waffle(ax, adjudicated: list[dict]) -> None:
    det = [r for r in adjudicated if r["category"] == "trusted_deterministic"]
    apt = [r for r in adjudicated if r["category"] == "untrusted_oracle"]
    blocks = [("deterministic tasks", det), ("aptamer tasks", apt)]
    x_off = 0
    right_edge = 0
    total_rows = 1
    for label, records in blocks:
        for i, rec in enumerate(records):
            r, c = divmod(i, TILES_PER_ROW)
            color = {"FP": FP_COLOR, "TP": TP_COLOR, "borderline": BORDERLINE_COLOR}[rec["verdict"]]
            ax.add_patch(plt.Rectangle((x_off + c, -(r + 1)), 0.88, 0.88,
                                       facecolor=color, edgecolor="white", linewidth=0.4))
        n_rows = max(1, math.ceil(len(records) / TILES_PER_ROW))
        total_rows = max(total_rows, n_rows)
        n_cols = max(1, min(len(records), TILES_PER_ROW))
        right_edge = max(right_edge, x_off + n_cols)
        n_fp = sum(1 for r in records if r["verdict"] == "FP")
        ax.text(x_off + n_cols / 2 - 0.5, 0.55,
                f"{label}: {len(records)} claims, {n_fp} FP",
                ha="center", va="bottom", fontsize=6, color=TEXT)
        x_off += TILES_PER_ROW + 1.2
    ax.set_xlim(-0.6, right_edge + 0.6)
    ax.set_ylim(-(total_rows + 0.7), 1.05)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_bars(ax, runs_rows: list[dict]) -> None:
    events = [ev for r in runs_rows if not r.get("error") for ev in r.get("overreach_events", [])]
    counts: dict[tuple[str, str], int] = {}
    for ev in events:
        counts[(ev["oracle"], ev["use"])] = counts.get((ev["oracle"], ev["use"]), 0) + 1
    max_n = max(counts.values()) if counts else 1

    y_pos, y_labels = [], []
    y = 0
    for oracle in ORACLE_ORDER:
        for use in ("ranking_objective", "screening_evaluation"):
            n = counts.get((oracle, use), 0)
            ax.barh(y, n, height=0.62, color=ORACLE_COLORS[oracle],
                    alpha=USE_ALPHA[use], edgecolor="none")
            if n > 0:
                ax.text(n + max(0.15, 0.02 * max_n), y, str(n),
                        va="center", ha="left", fontsize=6, color=TEXT)
            y_pos.append(y)
            y_labels.append(ORACLE_LABELS[oracle] if use == "ranking_objective" else "")
            y -= 1
        y -= 0.45

    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=6, color=TEXT)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=6, colors=TEXT)
    ax.set_xlim(0, max_n * 1.12 + 0.5)
    ax.set_xlabel("decision-layer overreach events", fontsize=6, color=TEXT)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(TEXT)
    n_tasks = len({r["task_id"] for r in runs_rows
                   if r.get("overreach_events") and not r.get("error")})
    ax.text(1.0, 1.06, f"{len(events)} events on {n_tasks} tasks",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6, color=TEXT)


def main() -> int:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS
    adjudicated, summary, runs_rows = load_data(results_dir)

    fig = plt.figure(figsize=(3.504, 3.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.25, 1.0], hspace=0.42,
                          left=0.20, right=0.96, top=0.90, bottom=0.24)
    ax_w = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])

    draw_waffle(ax_w, adjudicated)
    draw_bars(ax_b, runs_rows)

    ov = summary["overall"]
    rate = ov["fp_rate"]
    lo, hi = ov["fp_rate_ci95"]
    fig.text(0.96, 0.955,
             f"FP rate {ov['FP']}/{ov['FP'] + ov['TP']} = {rate:.1%} "
             f"(95% CI {lo:.0%}–{hi:.0%})",
             ha="right", va="top", fontsize=6, color=TEXT)

    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="none")
               for c in (FP_COLOR, TP_COLOR, BORDERLINE_COLOR)]
    fig.legend(handles, ["false positive", "true positive", "borderline"],
               loc="upper left", bbox_to_anchor=(0.005, 0.995), ncol=1,
               fontsize=6, frameon=False, handlelength=1.1, handleheight=0.9,
               labelcolor=TEXT)
    # Use encoding legend (same oracle colour, solid vs 55% alpha) as a centred
    # row block at the figure bottom, fully outside the axes (fig2i convention).
    use_handles = [plt.Rectangle((0, 0), 1, 1, facecolor=PALETTE_BY_NAME["grey_blue"], alpha=a,
                                 edgecolor="none") for a in (1.0, 0.55)]
    fig.legend(use_handles, [USE_LABELS["ranking_objective"], USE_LABELS["screening_evaluation"]],
               loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2,
               fontsize=6, frameon=False, handlelength=1.1, handleheight=0.9,
               columnspacing=1.2, handletextpad=0.5, labelcolor=TEXT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig3f_claim_overreach.{ext}", dpi=300)
    plt.close(fig)
    print(f"fig3f -> {OUT_DIR / 'fig3f_claim_overreach.pdf'} "
          f"(+png); claims={len(adjudicated)}, "
          f"FP={ov['FP']}, TP={ov['TP']}, events={summary['overreach_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
