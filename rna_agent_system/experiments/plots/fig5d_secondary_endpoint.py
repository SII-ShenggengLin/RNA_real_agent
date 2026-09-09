"""Fig 5d — the Exp-28 mRNA secondary endpoint, disclosed (Experiment 31,
§2.5; figure-only — data frozen by Exp 28).

Single-view Δ-composite stacked dots (the fig2d/2f stacking convention):
one dot per paired profile cell (n = 60 = 20 targets × 3 profiles),
stacked above its Δ = composite(navigation) − composite(rule); colour
marks the sign of Δ — sage navigation-favouring, terracotta
rule-favouring, grey blue tied (the Fig-5b direction semantics, defined
in the Fig. 5d caption — no in-figure key).  The paired Wilcoxon result
and the sign counts are annotated as one line in a reserved strip above
the axes; the zero reference line is drawn at Δ = 0.

2026-09-08 figure-repair pass (user direction): the criteria bullet bars
(gene-e2e conjunct 0.45 = 9/20 against the registered ≥ 0.8 legacy-era
gate, rule-pool 1.00 = 20/20 context; constraint rate 0.944 ≥ 0.9) and
the per-target spend strip (mean 24.55 of the 35-call cap, 10 at cap,
10 early-stopping 11–16, 0 violations · 0 LLM) were removed — one plot
per panel (the fig5a/5b/5c same-day convention).  The two blocks shared
neither axis nor observation unit with the Δ distribution (rates vs
per-cell score differences vs per-target call counts), so they are
text-reported: every removed number is stated verbatim in the Fig. 5d
caption and §2.5.  The floating per-block stat lines that read as
misplaced in-figure titles went with them; the two gate dashes (0.8 and
0.9 — two distinct pre-registered criteria, not one standard) leave the
panel entirely, and the solid mean tick is dropped.  All text one 6-pt
pure-black style.

Style (the fig3/fig4/fig5a/5b house style): no in-figure title — the
panel letter is added at assembly; colours exclusively from palette
rev 7; absolute-mm geometry, single column; 1200-dpi PNG + vector PDF
(fonttype 42).

Data  : experiments/results/exp31_fig5d_secondary/panel_data.json
        (built + verdict-cross-checked by experiments/exp31_fig5d_secondary.py)
Usage : python experiments/plots/fig5d_secondary_endpoint.py
Output : experiments/plots/output/fig5d_secondary_endpoint.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = (PROJECT_ROOT / "experiments" / "results" / "exp31_fig5d_secondary"
        / "panel_data.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 35.0

C_NAV = PALETTE_BY_NAME["sage_green"]      # navigation-favouring cells (Δ > 0)
C_RULE = PALETTE_BY_NAME["terracotta"]     # rule-favouring cells (Δ < 0)
C_TIE = PALETTE_BY_NAME["grey_blue"]       # tied cells (Δ = 0)

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

MM = 1 / 25.4
DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)   # exact 1200-dpi canvas pixels
H_PX = round(H_MM / 25.4 * DPI)


def stacked_dots(values: list[float], ndigits: int = 3):
    """Group coincident values (rounded) → [(value, count)] in value order."""
    counts: dict[float, int] = {}
    for v in values:
        key = round(v, ndigits)
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items())


def main() -> int:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    comp = d["composite_delta"]

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.05, 0.26, 0.90, 0.55])

    ax.axvline(0, color=INK, lw=0.5, zorder=1)
    for value, count in stacked_dots(comp["deltas"]):
        color = C_TIE if value == 0 else (C_NAV if value > 0 else C_RULE)
        ax.plot([value] * count, list(range(1, count + 1)), "o", ms=1.7,
                mfc=color, mec=color, zorder=3, clip_on=False)
        if count >= 3:  # the tall stacks only — small-stack labels crowd the
            ax.text(value, count + 0.7, str(count), ha="center", va="bottom",
                    fontsize=FONT, color=INK, zorder=4,  # ±0.2 cluster
                    bbox=dict(fc="white", ec="none", pad=0.5))  # the zero
            # stack's label sits on the zero reference line — white-backed
            # (the fig3f value-label convention)

    ax.set_xlim(-0.87, 0.47)
    ax.set_ylim(0, 21)
    ax.set_xticks([-0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4])
    ax.set_yticks([])
    ax.set_xlabel("Δ composite (navigation − rule)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── paired Wilcoxon result + sign counts: one line in the reserved
    #    strip above the axes (the fig5b convention) ──
    stat = ax.text(0.5, 1.05,
                   f"+{comp['n_pos']} / ={comp['n_zero']} / −{comp['n_neg']},"
                   f"  Wilcoxon P = {comp['wilcoxon_p']:.2f},"
                   f"  n = {d['n_pairs']}",
                   transform=ax.transAxes, ha="center", va="bottom",
                   fontsize=FONT, color=INK)

    # ── renderer-measured guards (the house pattern): every text inside the
    #    canvas, no text–text collision anywhere, the stat line clear of the
    #    axes (hence of every datum) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = ([stat, ax.xaxis.label]
             + [t for t in ax.texts if t is not stat]
             + list(ax.get_xticklabels()))
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.x1 <= fig.bbox.width
                and bb.y0 >= 0 and bb.y1 <= fig.bbox.height), \
            f"text overflows canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"
    assert boxes[0].y0 > ax.bbox.y1, "stat line dips into the axes"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5d_secondary_endpoint.{ext}", dpi=DPI)
    plt.close(fig)

    img = mpimg.imread(OUT_DIR / "fig5d_secondary_endpoint.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    print(f"wrote {OUT_DIR / 'fig5d_secondary_endpoint'}.{{pdf,png}} "
          f"({W_MM}x{H_MM} mm, {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
