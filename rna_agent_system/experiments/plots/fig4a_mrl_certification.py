#!/usr/bin/env python3
"""Fig. 4a — MRL expression-oracle certification (forest dot + CI vs gates).

The positive side of the capability profile: the GEMORNA 5′UTR MRL expression
oracle on the three measured-MRL anchor families (Sample et al. 2019 MPRA).
Two side-by-side panels sharing the family rows — left: screening AUROC
(high vs low MRL) against the gate 0.8 line; right: ranking Spearman ρ
against measured MRL against the gate 0.6 line. The dot is the point
estimate, the bar its 95% CI, the value printed above each dot; the
in-distribution family (random 50-nt, the registered positive control) is
named as such in its row label.

Colours (palette rev 7): the GEMORNA MRL oracle identity colour is the
palette's grey blue (#8FA6BB) — distinct from the fig3a–e structure-oracle
trio (terracotta / slate / sage); gate lines dashed in the held-out dark
warm grey (the fig3a/fig3b gate convention).

Style: the fig2d–fig2i/fig3a–fig3e conventions — no in-figure title (the
headline lives in the caption, the panel letter is added at assembly), every
text element one font size and pure black, single-column geometry.

Figure revision 2026-08-30 (user-directed): every text element pure black
#000000 (the fig3e convention — the palette's TEXT #1A1A1A reads grey at
6-pt anti-aliasing); the chance/zero reference lines dropped — the
certification reading rests on the pre-registered gates (kept, dashed,
labelled in black), the chance level stays visible on the shared 0–1 metric
axis and is stated in the Fig-4a caption (the fig2g second-revision
convention); the two x-label second lines shortened — they had mutually
overlapped at the inter-panel gap (the screening tier n's moved into the
caption); row labels rewritten as the Sample-2019 5′UTR library names; value
labels carry a white backing so they no longer cross the gate dashes; layout
rebalanced (wider inter-panel gap, shorter figure). PNG at 1200 dpi (Nature
Methods line-art guidance) + vector PDF (fonttype 42).

2026-10-02 text sync (the Fig. 4 figure-by-figure pass): the left x-label's
second line "(high vs low MRL tier)" lost "tier" — the word is retired
paper-wide, and the Methods text's "split into high and low" carries the
split semantics.

2026-10-10 label-column fix (user-directed): the row labels dropped the
shared "5′UTRs" token — the right-aligned three-line labels were ragged
(one 20.3-mm line set a 22-mm column, the other lines 6.5–14.1 mm, leaving
the left of the label block blank); the caption's registered first sentence
("three 5′UTR libraries, the random 50-nucleotide library and two
never-trained varying-length libraries") carries the library identity, the
in-distribution marker and the n = counts stay. The label column narrowed
22 → 15 mm and the freed width went to the two axes (29 → 32.5 mm).

2026-10-10 composite-grid batch (user-directed row/column alignment): the
canvas is now an exact 82.5 x 72.0 mm cell of the Fig. 4 two-column grid
(column 1; row 1 shares its height with fig4b) saved without the tight
crop, so the assembler places it at scale 1.0 with the canvas edges and
the 6-pt text size shared across the whole composite. The two axes re-fit
the narrower cell (32.5 → 29.75 mm each) and stretch to the taller row
(37 → 51 mm, y0 13); labels, gates and values unchanged.

Data  : experiments/results/exp14_mrl_oracle_certification/summary.json
Usage : python experiments/plots/fig4a_mrl_certification.py
Output : experiments/plots/output/fig4a_mrl_certification.{pdf,png}
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp14_mrl_oracle_certification"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"   # 2026-08-30 user direction: every text element pure black
FONT = 6          # single font size for every in-figure text element
C_ORACLE = PALETTE_BY_NAME["grey_blue"]       # #8FA6BB — GEMORNA MRL oracle
C_GATE = PALETTE_BY_NAME["dark_warm_grey"]    # #7A7672 — gate lines (fig3a/3b)

FAMILIES = [
    ("sample2019_egfp_random50", "Random 50-nt\n(in-distribution)"),
    ("sample2019_varying_length_random", "Varying-length\nrandom"),
    ("sample2019_varying_length_human", "Varying-length\nhuman"),
]

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

X_MIN, X_MAX = 0.0, 1.08  # shared 0–1 metric scale; headroom past 1.0 CIs


def gate_line(ax, x: float, label: str, y_top: float) -> None:
    """Pre-registered gate line (dashed), labelled above in pure black."""
    ax.plot([x, x], [-0.5, y_top], color=C_GATE,
            linewidth=0.7, linestyle=(0, (3, 2)), zorder=1)
    ax.text(x, y_top + 0.06, label, fontsize=FONT, ha="center",
            va="bottom", color=INK, zorder=5)


def dot_row(ax, y: float, est: float, lo: float, hi: float,
            half_w: float) -> None:
    ax.plot([lo, hi], [y, y], color=C_ORACLE, linewidth=1.4,
            solid_capstyle="butt", zorder=3)
    for x_edge in (lo, hi):  # CI end caps
        ax.plot([x_edge, x_edge], [y - 0.09, y + 0.09], color=C_ORACLE,
                linewidth=0.9, zorder=3)
    ax.scatter(est, y, s=22, c=C_ORACLE, edgecolors="white",
               linewidths=0.4, zorder=4)
    # point estimate (95% CI) above the dot, clamped inside the axis; white
    # backing so the label never visually collides with the gate dashes
    x_text = min(max(est, half_w + 0.01), X_MAX - half_w - 0.01)
    ax.text(x_text, y + 0.16, f"{est:.3f} ({lo:.2f}–{hi:.2f})",
            fontsize=FONT, va="bottom", ha="center", color=INK, zorder=5,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.12))


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
            "label": f"{name}\nn = {fam[key]['n_scored']}",
            "auroc": fam[key]["screening"]["auroc"],
            "auroc_ci": fam[key]["screening"]["auroc_ci95"],
            "rho": fam[key]["ranking"]["spearman_rho"],
            "rho_ci": fam[key]["ranking"]["rho_ci95_descriptive"],
        }
        for key, name in FAMILIES
    ]

    fig_w, fig_h = 82.5 / 25.4, 72.0 / 25.4  # exact grid cell (composite batch)
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # absolute-mm geometry: 1 mm margin | 15 mm label column | two 29.75-mm
    # axes | 6 mm gap | 1 mm margin = 82.5 mm; axes 51 mm tall, y0 13 so the
    # top ink sits ~8 mm below the canvas top (the letter hugs the row's
    # highest ink at assembly; bottom margin ~5 mm matches fig4b's)
    x_m, label_mm, ax_w, gap_mm = 1.0, 15, 29.75, 6
    y0_mm, h_mm = 13, 51
    ax1 = fig.add_axes([(x_m + label_mm) / 25.4 / fig_w, y0_mm / 25.4 / fig_h,
                        ax_w / 25.4 / fig_w, h_mm / 25.4 / fig_h])
    ax2 = fig.add_axes([(x_m + label_mm + ax_w + gap_mm) / 25.4 / fig_w,
                        y0_mm / 25.4 / fig_h, ax_w / 25.4 / fig_w,
                        h_mm / 25.4 / fig_h])

    ys = list(range(len(rows)))[::-1]  # first family on top
    y_top = len(rows) - 0.35

    # value-label half width in data units: the printed "v (lo–hi)" string is
    # ~17 chars at FONT pt (~18 mm) over the ax_w-mm axis
    half_w = (17 * FONT * 0.5 / 72 * 25.4 / 2) / ax_w * (X_MAX - X_MIN)

    # left panel — screening AUROC
    for y, row in zip(ys, rows):
        dot_row(ax1, y, row["auroc"], row["auroc_ci"][0], row["auroc_ci"][1],
                half_w)
    gate_line(ax1, 0.8, "gate 0.8", y_top)
    ax1.set_yticks(ys)
    ax1.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                        linespacing=1.2, color=INK)

    # right panel — ranking ρ
    for y, row in zip(ys, rows):
        dot_row(ax2, y, row["rho"], row["rho_ci"][0], row["rho_ci"][1],
                half_w)
    gate_line(ax2, 0.6, "gate 0.6", y_top)
    ax2.set_yticks([])

    for ax, xlabel in ((ax1, "Screening AUROC\n(high vs low MRL)"),
                       (ax2, "Ranking Spearman ρ\n(predicted vs measured MRL)")):
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
        out = OUT_DIR / f"fig4a_mrl_certification.{ext}"
        fig.savefig(out, format=ext, dpi=1200 if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: AUROC {row['auroc']} "
              f"{tuple(row['auroc_ci'])} | rho {row['rho']} {tuple(row['rho_ci'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
