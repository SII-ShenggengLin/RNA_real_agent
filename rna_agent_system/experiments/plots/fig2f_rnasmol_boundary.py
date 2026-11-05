#!/usr/bin/env python3
"""Fig. 2f — small-molecule oracle two-sided boundary (forest dot + CI).

Re-lettered g → f on 2026-09-11 (user direction) when the IRES panel moved
out of Fig. 2 to Supplementary Fig. S1; data and rendering unchanged.

Four AUROC rows on one axis: the deployed small-molecule service on its own
official held-out test splits (in-distribution) versus the literature
short-aptamer panel (out-of-distribution). Horizontal bars are
stratified-bootstrap 95% CIs; the dot is the point AUROC, printed with its
CI directly above each dot.

Figure revision 2026-10-02 (user-adjudicated, text-consistency pass):
(i) the "(OOD)" abbreviation spelled out as "(out-of-distribution)" — the
manuscript never defines OOD (the Fig. 2f legend writes "out-of-distribution
short aptamers"); the aptamer rows now carry four-line labels and the panel
is 58 → 62 mm tall to keep the label blocks clear of each other. (ii) The
printed point estimates and CIs now use the manuscript's three-decimal
half-up rounding (0.974 (0.968–0.980), 0.983 (0.961–0.997), 0.722
(0.278–1.000), 0.563 (0.063–1.000)) — the earlier two-decimal CIs rounded
0.997 to 1.00 and the point estimate 0.5625 to 0.562 against the text's
0.563. (iii) The x-axis reads "AUROC" — plain metric name, the Fig. 4c
convention; the deployed-service provenance is carried by the body and the
caption. (iv) n prints with the manuscript's thousands separator
(n = 1,492). (v) Same-day follow-up (user-adjudicated): the out-of-
distribution rows read "Short aptamers" — the body/legend term, "panel"
being internal register vocabulary — and the two control classes read
"vs random molecules" / "vs close analogues", plain descriptions keeping
the body's word roots (the §2.2 sentence was synced to the same wording:
"against random molecules and close analogues"); the x-axis lost its
"(deployed service)" qualifier at the same time.

Colours (palette rev 7): in-distribution rows in the RNA–small-molecule
workflow's khaki; out-of-distribution rows in the held-out dark warm grey
(the palette's neutral-dark semantic for undemonstrated power, matching the
fig2d miss / fig2e nonzero convention).

Geometry (2026-10-10, user-directed three-column relayout of the Fig. 2
composite): exact 57 x 57 mm canvas (no tight crop, the shared explicit
crop retired with it), absolute-mm axes placement shared with panels
b–e and g (axes bottom 12 mm, top 3 mm) so the three-per-row panels
align; the left label column takes 23 mm (the four-line
out-of-distribution labels are the widest element), the point-plus-CI
annotation prints on two lines — same values — because one line no
longer fits beside its dot at the three-column plot width, and the row
labels draw at linespacing 1.1 so the four-line blocks clear each other
at the shorter row pitch; the 6-pt text scale is unchanged.

Data  : experiments/results/exp7_rnasmol_boundary/summary.json
Usage : python experiments/plots/fig2f_rnasmol_boundary.py
Output : experiments/plots/output/fig2f_rnasmol_boundary.{pdf,png}
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT, PALETTE_BY_NAME, WORKFLOW_COLORS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp7_rnasmol_boundary"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

FONT = 6  # single font size for every in-figure text element

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

C_IN_DIST = WORKFLOW_COLORS["rna_small_molecule_interaction"]  # khaki #CDBF9E
C_OOD = PALETTE_BY_NAME["dark_warm_grey"]                      # #7A7672

# Shared three-column geometry (panels b–g, 2026-10-10): exact canvas,
# axes placed in absolute mm so every panel in a composite row aligns.
# f's left band is wider — the four-line out-of-distribution labels.
W_MM, H_MM = 57.0, 57.0
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)
AX_L, AX_BOT, AX_R, AX_TOP = 23.0, 12.0, 2.0, 3.0

X_MAX = 1.08  # headroom so the hi = 1.0 CI caps clear the panel edge


def fmt3(v: float) -> str:
    """Manuscript three-decimal half-up rounding (0.5625 → "0.563", not
    the float half-even "0.562" — the body text writes 0.563)."""
    return str(Decimal(repr(v)).quantize(Decimal("0.001"),
                                         rounding=ROUND_HALF_UP))


def main() -> int:
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("no summary.json — run experiments/exp7_rnasmol_boundary.py --summary first")
        return 1
    s = json.loads(summary_path.read_text(encoding="utf-8"))

    def block(parent: dict, key: str) -> dict:
        b = parent[key]
        return {
            "auroc": b["point_auroc"],
            "lo": b["auroc_ci95"][0],
            "hi": b["auroc_ci95"][1],
        }

    rows = [
        {
            "label": "ROBIN test\n(in-distribution)\nn = "
                     f"{s['robin_test']['n_scored']:,}",
            "color": C_IN_DIST,
            **block(s, "robin_test"),
        },
        {
            "label": "PDB test\n(in-distribution)\nn = "
                     f"{s['pdb_test']['n_scored']:,}",
            "color": C_IN_DIST,
            **block(s, "pdb_test"),
        },
        {
            "label": "Short aptamers\n(out-of-distribution)\n"
                     "vs random molecules\nn = "
                     f"{s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_random_chem']:,}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_random_chem"),
        },
        {
            "label": "Short aptamers\n(out-of-distribution)\n"
                     "vs close analogues\nn = "
                     f"{s['ood_aptamer']['n_binders']
                           + s['ood_aptamer']['n_near_cognate']:,}",
            "color": C_OOD,
            **block(s["ood_aptamer"], "auroc_vs_near_cognate"),
        },
    ]

    fig_w, fig_h = W_PX / DPI + 1e-9, H_PX / DPI + 1e-9
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor="white")
    # absolute-mm geometry shared with panels b–e/g; wider label column
    ax = fig.add_axes([
        AX_L / W_MM, AX_BOT / H_MM,
        (W_MM - AX_L - AX_R) / W_MM, (H_MM - AX_BOT - AX_TOP) / H_MM,
    ])

    ys = list(range(len(rows)))[::-1]  # first row on top
    ax_w_mm = W_MM - AX_L - AX_R

    ann_texts = []
    for y, row in zip(ys, rows):
        ax.plot([row["lo"], row["hi"]], [y, y], color=row["color"],
                linewidth=1.4, solid_capstyle="butt", zorder=3)
        for x_edge in (row["lo"], row["hi"]):  # CI end caps
            ax.plot([x_edge, x_edge], [y - 0.09, y + 0.09], color=row["color"],
                    linewidth=0.9, zorder=3)
        ax.scatter(row["auroc"], y, s=22, c=row["color"],
                   edgecolors="white", linewidths=0.4, zorder=4)
        # point estimate over its 95% CI, both above the dot
        ann_texts.append(ax.text(
            row["auroc"], y + 0.16,
            f"{fmt3(row['auroc'])}\n({fmt3(row['lo'])}–{fmt3(row['hi'])})",
            fontsize=FONT, va="bottom", ha="center", color=TEXT,
            linespacing=1.1))

    # Clamp each annotation inside the axis: measure its real width with
    # the renderer (multi-line extents report the widest line), convert
    # to axis units, then shift the centre. (The old closed-form half
    # width divided by 25.4 instead of 72 — a pt/mm slip that the wide
    # 61-mm axis hid as a tiny nudge and the three-column axis exposes.)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for t, row in zip(ann_texts, rows):
        bb = t.get_window_extent(renderer)
        half_units = (bb.width / 2.0 / fig.dpi * 25.4) / ax_w_mm * X_MAX
        x_new = min(max(row["auroc"], half_units + 0.01),
                    X_MAX - half_units - 0.01)
        t.set_position((x_new, t.get_position()[1]))

    ax.set_yticks(ys)
    ax.set_yticklabels([r["label"] for r in rows], fontsize=FONT,
                       linespacing=1.05, color=TEXT)

    ax.set_xlim(0.0, X_MAX)
    ax.set_ylim(-0.45, len(rows) - 0.40)
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=FONT)
    ax.tick_params(axis="x", labelsize=FONT, length=1.5, pad=1)
    ax.tick_params(axis="y", labelsize=FONT, length=1.5, pad=2)
    ax.set_xlabel("AUROC", fontsize=FONT, labelpad=2)
    for s_name in ("top", "right"):
        ax.spines[s_name].set_visible(False)

    # Guards (house convention): neighbouring row-label blocks and
    # neighbouring point-plus-CI annotations must keep clear vertical
    # gaps (analytic heights — renderer extents under-report multi-line
    # text), and every text element must sit fully inside the fixed
    # canvas (the top row's two-line annotation may ride the hidden top
    # spine by design, but not the canvas edge).
    axes_h_mm = H_MM - AX_BOT - AX_TOP
    y_span = -0.45 - (len(rows) - 0.40)
    pitch_mm = axes_h_mm / abs(y_span)
    worst_block = max(len(r["label"].splitlines()) for r in rows)
    lbl_block_mm = worst_block * FONT * 1.05 / 72 * 25.4
    if pitch_mm - lbl_block_mm < 0.5:
        raise AssertionError(
            f"row labels gap {pitch_mm - lbl_block_mm:.2f} mm < 0.5 mm")
    ann_block_mm = 2 * FONT * 1.1 / 72 * 25.4
    if pitch_mm - ann_block_mm < 1.0:
        raise AssertionError(
            f"annotation gap {pitch_mm - ann_block_mm:.2f} mm < 1.0 mm")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fw, fh = fig_w * fig.dpi, fig_h * fig.dpi
    for t in (*ax.get_yticklabels(), *ax.get_xticklabels(),
              ax.xaxis.label, *ann_texts):
        tb = t.get_window_extent(renderer).expanded(1.0, 1.35)
        if tb.x0 < -0.5 or tb.y0 < -0.5 or tb.x1 > fw + 0.5 or tb.y1 > fh + 0.5:
            raise AssertionError(f"text element {t.get_text()!r} leaves "
                                 f"the canvas")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = OUT_DIR / f"fig2f_rnasmol_boundary.{ext}"
        fig.savefig(out, format=ext, dpi=DPI if ext == "png" else None,
                    facecolor="white")
        print(f"written {out}")
    for row in rows:
        print(f"{row['label'].splitlines()[0]}: {row['auroc']} "
              f"({row['lo']}–{row['hi']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
