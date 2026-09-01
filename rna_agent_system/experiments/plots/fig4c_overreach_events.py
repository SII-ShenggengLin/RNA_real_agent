"""Fig 4c — decision-layer overreach events of the E3 dual-arm re-run.

Paired bars per oracle x intended use (plan requests of a structural oracle
as ranking objective / screening evaluation): ungated control arm (Exp 5,
59 events, terracotta) vs gated treatment arm (Exp 17, 0 events, sage) —
arm colours as Fig. 4a; a bracket annotation carries the registered delta
(59 -> 0). Use is carried by the x-axis cells (ranking / screening), oracle
labels centred on their cell pairs (the fig3e group-label convention). The
gated arm's 71 blocked plan requests (the mechanism behind the zero) are
stated in the caption, not drawn.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles
or summary statistics beyond the registered delta annotation; every text
element one 6-pt pure-black style; colours only from palette rev 7; 1200-dpi
PNG + vector PDF (fonttype 42); absolute-mm geometry, single-column width.

Data  : experiments/results/exp5_claim_overreach/runs_summary.json (ungated)
        experiments/results/exp17_claim_gating/summary.json (gated)
Usage : python experiments/plots/fig4c_overreach_events.py
Output : experiments/plots/output/fig4c_overreach_events.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXP5_SUMMARY = (PROJECT_ROOT / "experiments" / "results" / "exp5_claim_overreach"
                / "runs_summary.json")
EXP17_SUMMARY = (PROJECT_ROOT / "experiments" / "results" / "exp17_claim_gating"
                 / "summary.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

ARM_COLORS = {"ungated": PALETTE_BY_NAME["terracotta"],
              "gated": PALETTE_BY_NAME["sage_green"]}
ORACLE_ORDER = ["rhofold_mean_plddt", "proteinx_ipTM", "egarps_native_probability"]
ORACLE_LABELS = {"rhofold_mean_plddt": "RhoFold", "proteinx_ipTM": "ProteinX",
                 "egarps_native_probability": "EGARPS"}
USES = ["ranking_objective", "screening_evaluation"]
USE_LABELS = {"ranking_objective": "Ranking", "screening_evaluation": "Screening"}

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


def main() -> int:
    exp5 = json.loads(EXP5_SUMMARY.read_text(encoding="utf-8"))
    exp17 = json.loads(EXP17_SUMMARY.read_text(encoding="utf-8"))

    # cell layout: x positions 0,1 | 2.5,3.5 | 5,6 (oracle groups gapped)
    xs = [0.0, 1.0, 2.5, 3.5, 5.0, 6.0]
    cells = [(o, u) for o in ORACLE_ORDER for u in USES]
    ungated = [exp5["overreach_by_oracle_use"][f"{o}:{u}"] for o, u in cells]
    gated_total = exp17["arms"]["gated"]["overreach_events"]
    assert gated_total == 0 and sum(ungated) == exp5["overreach_total"]

    fig_w, fig_h = 89 / 25.4, 44 / 25.4
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    ax = fig.add_axes([16 / 25.4 / fig_w, 12.5 / 25.4 / fig_h,
                       68 / 25.4 / fig_w, 23.5 / 25.4 / fig_h])

    w = 0.34
    y_top = max(ungated) * 1.45
    for x, n in zip(xs, ungated):
        ax.bar(x - w / 2 - 0.01, n, width=w, color=ARM_COLORS["ungated"],
               edgecolor="none")
        ax.text(x - w / 2 - 0.01, n + 0.28, str(n), ha="center", va="bottom",
                fontsize=FONT, color=INK)
        ax.bar(x + w / 2 + 0.01, 0, width=w, color=ARM_COLORS["gated"],
               edgecolor="none")
        ax.text(x + w / 2 + 0.01, 0.28, "0", ha="center", va="bottom",
                fontsize=FONT, color=INK)

    ax.set_xticks(xs)
    ax.set_xticklabels([USE_LABELS[u] for _, u in cells], fontsize=FONT)
    ax.tick_params(axis="x", length=0, pad=1.5)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=1)
    # oracle labels centred on their cell pairs (fig3e group-label convention)
    for gx, o in zip((0.5, 3.0, 5.5), ORACLE_ORDER):
        ax.text(gx, -0.175, ORACLE_LABELS[o], ha="center", va="top",
                fontsize=FONT, color=INK, transform=ax.get_xaxis_transform())
    ax.set_xlim(-0.75, 6.75)
    ax.set_ylim(0, y_top)
    ax.set_yticks(range(0, 12, 3))
    ax.set_ylabel("Decision-layer overreach events", fontsize=FONT, labelpad=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # registered delta annotation: bracket spanning the axis, 59 -> 0
    bx0, bx1 = -0.6, 6.6
    by = max(ungated) * 1.30
    ax.plot([bx0, bx1], [by, by], color=INK, linewidth=0.4)
    for bx in (bx0, bx1):
        ax.plot([bx, bx], [by - 0.35, by], color=INK, linewidth=0.4)
    ax.text((bx0 + bx1) / 2, by + 0.35, f"{sum(ungated)} → 0",
            ha="center", va="bottom", fontsize=FONT, color=INK)

    # arm key: one centred row under the panel (the fig4a arm-colour key)
    def _fx(v: float) -> float: return v / 25.4 / fig_w
    def _fy(v: float) -> float: return 1 - v / 25.4 / fig_h
    key_y = 4.0
    sw_w, sw_h, pitch, gap_k, label_w = 2.4, 1.6, 3.0, 1.8, 10.0
    row_w = 2 * (sw_w + gap_k + label_w) + pitch - gap_k
    x = (16 + 68 / 2) - row_w / 2
    for arm, lab in (("ungated", "Ungated"), ("gated", "Gated")):
        fig.patches.append(plt.Rectangle(
            (_fx(x), _fy(key_y + sw_h / 2)), _fx(sw_w),
            _fy(key_y - sw_h / 2) - _fy(key_y + sw_h / 2),
            facecolor=ARM_COLORS[arm], edgecolor="none",
            transform=fig.transFigure))
        fig.text(_fx(x + sw_w + gap_k), _fy(key_y), lab, ha="left", va="center",
                 fontsize=FONT, color=INK)
        x += sw_w + gap_k + label_w + pitch

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4c_overreach_events.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"fig4c -> {OUT_DIR / 'fig4c_overreach_events.pdf'} (+png 1200 dpi); "
          f"overreach {sum(ungated)} -> 0 by oracle x use "
          f"({', '.join(str(n) for n in ungated)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
