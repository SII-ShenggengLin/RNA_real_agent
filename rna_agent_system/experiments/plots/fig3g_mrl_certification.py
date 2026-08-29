#!/usr/bin/env python3
"""Fig. 3g — MRL expression-oracle certification (forest dot + CI vs gates).

The positive side of the capability profile: the GEMORNA 5'UTR MRL expression
oracle on the three measured-MRL anchor families (Sample et al. 2019 MPRA).
Two side-by-side panels sharing the family rows — left: screening AUROC
(high vs low MRL tier) against the chance 0.5 and gate 0.8 lines; right:
ranking Spearman ρ against measured MRL on the zero and gate 0.6 lines.
The dot is the point estimate, the bar its 95% CI, the value printed above
each dot; the in-distribution family (random 50-nt, the registered positive
control) is named as such in its row label.

Colours (palette rev 7): the GEMORNA MRL oracle identity colour is the
palette's grey blue (#8FA6BB) — distinct from the fig3b–f structure-oracle
trio (terracotta / slate / sage); chance / zero reference lines in the
neutral grid grey, gate lines dashed in the held-out dark warm grey (the
fig3b/fig3c gate convention).

Style: the fig2d–fig2i/fig3b–fig3f conventions — no in-figure title (the
headline lives in the caption), every text element one font size and ink
black, single-column geometry.

Data  : experiments/results/exp14_mrl_oracle_certification/summary.json
Usage : python experiments/plots/fig3g_mrl_certification.py
Output : experiments/plots/output/fig3g_mrl_certification.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME, TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp14_mrl_oracle_certification"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6          # single font size for every in-figure text element
C_ORACLE = PALETTE_BY_NAME["grey_blue"]     # #8FA6BB — GEMORNA MRL oracle
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]  # #7A7672 — gate lines (fig3b/3c)
C_REF = NEUTRAL_GRID                          # chance / zero reference lines

FAMILIES = [
    "sample2019_egfp_random50",
    "sample2019_varying_length_random",
    "sample2019_varying_length_human",
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "axes.linewidth": 0.5,
    "text.color": TEXT,
    "axes.edgecolor": TEXT,
    "xtick.color": TEXT,
    "ytick.color": TEXT,
    "pdf.fonttype": 42,
})

X_MIN, X_MAX = 0.0, 1.08  # shared 0–1 metric scale; headroom past 1.0 CIs


def ref_line(ax, x: float, *, gate: bool, label: str, y_top: float) -> None:
    """Vertical reference line (chance/zero solid grid grey, gate dashed)."""
    ax.plot([x, x], [-0.5, y_top],
            color=C_GATE if gate else C_REF,
            linewidth=0.7, linestyle=(0, (3, 2)) if gate else "-", zorder=1)
    ax.text(x, y_top + 0.06, label, fontsize=FONT, ha="center", va="bottom",
            color=TEXT if gate else C_GATE, zorder=5)


def dot_row(ax, y: float, est: float, lo: float, hi: float) -> None:
    ax.plot([lo, hi], [y, y], color=C_ORACLE, linewidth=1.4,
            solid_capstyle="butt", zorder=3)
    for x_edge in (lo, hi):  # CI end caps
        ax.plot([x_edge, x_edge], [y - 0.09, y + 0.09], color=C_ORACLE,
                linewidth=0.9, zorder=3)
    ax.scatter(est, y, s=22, c=C_ORACLE, edgecolors="white",
               linewidths=0.4, zorder=4)
    # point estimate (95% CI) above the dot, clamped inside the axis
    half_w = 0.34  # ~17 chars at FONT pt on the ~30-mm axes
    x_text = min(max(est, half_w + 0.01), X_MAX - half_w - 0.01)
    ax.text(x_text, y + 0.16, f"{est:.3f} ({lo:.2f}–{hi:.2f})",
            fontsize=FONT, va="bottom", ha="center", color=TEXT, zorder=5)


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp14_mrl_oracle_certification.py "
              "--summary first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    fam = s["per_family"]

    rows = [
        {
            "label": f"{fam[f]['label'].split(' (')[0]}\n"
                     + ("(in-distribution)\n" if f == FAMILIES[0] else "")
                     + f"n = {fam[f]['n_scored']}",
            "auroc": fam[f]["screening"]["auroc"],
            "auroc_ci": fam[f]["screening"]["auroc_ci95"],
            "rho": fam[f]["ranking"]["spearman_rho"],
            "rho_ci": fam[f]["ranking"]["rho_ci95_descriptive"],
        }
        for f in FAMILIES
    ]

    fig_w, fig_h = 88 / 25.4, 58 / 25.4  # single-column panel
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # absolute-mm geometry: 24 mm label column | two ~28-mm axes | 2 mm gap
    label_mm, ax1_w, gap_mm = 24, 29, 3
    y0_mm, h_mm = 11, 40
    ax1 = fig.add_axes([label_mm / 25.4 / fig_w, y0_mm / 25.4 / fig_h,
                        ax1_w / 25.4 / fig_w, h_mm / 25.4 / fig_h])
    ax2 = fig.add_axes([(label_mm + ax1_w + gap_mm) / 25.4 / fig_w,
                        y0_mm / 25.4 / fig_h, ax1_w / 25.4 / fig_w,
                        h_mm / 25.4 / fig_h])

    ys = list(range(len(rows)))[::-1]  # first family on top
    y_top = len(rows) - 0.35

    # left panel — screening AUROC
    for y, row in zip(ys, rows):
        dot_row(ax1, y, row["auroc"], row["auroc_ci"][0], row["auroc_ci"][1])
    ref_line(ax1, 0.5, gate=False, label="chance", y_top=y_top)
    ref_line(ax1, 0.8, gate=True, label="gate 0.8", y_top=y_top)
    ax1.set_yticks(ys)
    ax1.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                        linespacing=1.2, color=TEXT)

    # right panel — ranking ρ
    for y, row in zip(ys, rows):
        dot_row(ax2, y, row["rho"], row["rho_ci"][0], row["rho_ci"][1])
    ref_line(ax2, 0.0, gate=False, label="zero", y_top=y_top)
    ref_line(ax2, 0.6, gate=True, label="gate 0.6", y_top=y_top)
    ax2.set_yticks([])

    for ax, xlabel in ((ax1, "Screening AUROC\n(high vs low MRL tier, n = 60 + 60)"),
                       (ax2, "Ranking Spearman ρ\n(predicted vs measured MRL, n = 120)")):
        ax.set_xlim(X_MIN, X_MAX)
        ax.set_ylim(-0.5, len(rows) + 0.05)
        ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=FONT)
        ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
        ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=2)
        ax.set_xlabel(xlabel, fontsize=FONT, labelpad=2)
        for s_name in ("top", "right"):
            ax.spines[s_name].set_visible(False)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig3g_mrl_certification.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white", bbox_inches="tight", pad_inches=0.02)
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: AUROC {row['auroc']} "
              f"{tuple(row['auroc_ci'])} | rho {row['rho']} {tuple(row['rho_ci'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
