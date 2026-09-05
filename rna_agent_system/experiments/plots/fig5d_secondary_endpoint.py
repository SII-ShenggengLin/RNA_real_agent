"""Fig 5d — the Exp-28 mRNA secondary endpoint, disclosed (Experiment 31,
§2.5; figure-only — data frozen by Exp 28).

Three stacked blocks on one 89-mm column (the Exp-31 re-registration of
the FIGURE_PLAN_V5 row-d encoding):

* bullet bars — the registered criteria on a 0–1 scale: the gene-e2e
  conjunct (GenNav 0.45 = 9/20 against the ≥ 0.8 legacy-era gate; the rule
  pool's 1.00 = 20/20 drawn as delivery context) and the navigation
  constraint rate (0.944 mean over the 60 delivered cells against the
  ≥ 0.9 gate — the one secondary criterion that holds); light 0–1 tracks,
  arm-coloured measures, dashed gates, values and counts printed at the
  bars;
* Δ-composite stacked dots — one dot per paired cell (n = 60), stacked
  above its Δ = composite(navigation) − composite(rule); sage =
  navigation-favouring, grey blue = tied, terracotta = rule-favouring
  (the Fig-5b direction semantics); paired Wilcoxon P annotated;
* budget strip — one dot per target at its navigation raw generator spend
  (coincident values stacked), the matched 35-call cap dashed, the mean
  ticked, zero-violation / zero-LLM annotated.

Style (the fig2d/2f/fig5b house style): no in-figure title — the panel
letter lands at assembly; single 6-pt pure-black text; palette rev 7
only; absolute-mm geometry; 1200-dpi PNG + vector PDF (fonttype 42).

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
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = (PROJECT_ROOT / "experiments" / "results" / "exp31_fig5d_secondary"
        / "panel_data.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 74.0

C_NAV = PALETTE_BY_NAME["sage_green"]      # navigation arm / nav-favouring
C_RULE = PALETTE_BY_NAME["terracotta"]     # rule arm / rule-favouring
C_TIE = PALETTE_BY_NAME["grey_blue"]       # tied cells
C_TRACK = NEUTRAL_GRID                     # bullet 0–1 tracks (non-data grey)

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

LEFT, WIDTH = 0.245, 0.610


def stacked_dots(values: list[float], ndigits: int = 3):
    """Group coincident values (rounded) → [(value, count)] in value order."""
    counts: dict[float, int] = {}
    for v in values:
        key = round(v, ndigits)
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items())


def main() -> int:
    d = json.loads(DATA.read_text(encoding="utf-8"))
    gene, cons, comp, budget = (d["gene_e2e"], d["constraint_rate"],
                                d["composite_delta"], d["budget"])

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))

    # ── block A: registered-criteria bullet bars ────────────────────────
    axA = fig.add_axes([LEFT, 0.700, WIDTH, 0.240])
    rows = [  # y = 0, 1, 2 bottom → top
        (cons["nav_mean"], f"{cons['nav_mean']:.2f} (60 cells)", C_NAV),
        (gene["nav_rate"], f"{gene['nav_rate']:.2f} ({gene['nav_count']}/20)", C_NAV),
        (gene["rule_rate"], f"{gene['rule_rate']:.2f} ({gene['rule_count']}/20)", C_RULE),
    ]
    for y, (value, label, color) in enumerate(rows):
        axA.barh(y, 1.0, height=0.30, color=C_TRACK, edgecolor="none", zorder=1)
        axA.barh(y, value, height=0.18, color=color, edgecolor="none", zorder=3)
        axA.text(value / 2, y + 0.22, label, ha="center", va="bottom",
                 fontsize=FONT, color=INK, zorder=4)
    # dashed gates per criterion group: 0.8 spans the two gene-e2e rows,
    # 0.9 the constraint row; labels at each dash head
    axA.plot([gene["gate"]] * 2, [0.74, 2.26], ls=(0, (2, 2)), lw=0.7,
             color=INK, zorder=2)
    axA.text(gene["gate"], 2.30, f"gate {gene['gate']:.1f}", ha="center",
             va="bottom", fontsize=FONT, color=INK)
    axA.plot([cons["gate"]] * 2, [-0.26, 0.26], ls=(0, (2, 2)), lw=0.7,
             color=INK, zorder=2)
    axA.text(cons["gate"], 0.30, f"gate {cons['gate']:.1f}", ha="center",
             va="bottom", fontsize=FONT, color=INK)
    axA.set_xlim(0, 1.03)
    axA.set_ylim(-0.62, 2.78)
    axA.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    axA.set_yticks([0, 1, 2])
    axA.set_yticklabels(["constraint rate\nGenNav", "gene-e2e conjunct\nGenNav",
                         "gene-e2e conjunct\nrule pool"])
    axA.set_xlabel("rate")
    axA.spines[["top", "right"]].set_visible(False)
    axA.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── block B: Δ-composite stacked dots (fig2d/2f convention); the
    #    direction colours carry the Fig-5b semantics and are read from the
    #    paper legend — no in-figure key (the fig5b convention) ──────────
    axB = fig.add_axes([LEFT, 0.360, WIDTH, 0.285])
    deltas = comp["deltas"]
    axB.axvline(0, color=INK, lw=0.5, zorder=1)
    for value, count in stacked_dots(deltas):
        color = C_TIE if value == 0 else (C_NAV if value > 0 else C_RULE)
        ys = range(1, count + 1)
        axB.plot([value] * count, list(ys), "o", ms=1.7, mfc=color, mec=color,
                 zorder=3, clip_on=False)
        if count >= 3:  # the tall stacks only — small-stack labels crowd the
            axB.text(value, count + 0.7, str(count), ha="center", va="bottom",
                     fontsize=FONT, color=INK, zorder=4,  # ±0.2 cluster
                     bbox=dict(fc="white", ec="none", pad=0.5))  # the zero
            # stack's label sits on the zero reference line — white-backed
            # (the fig3f value-label convention)
    axB.text(-0.88, 23.6, f"Wilcoxon P = {comp['wilcoxon_p']:.2f} · NS · "
             f"n = {d['n_pairs']}", ha="left", va="top", fontsize=FONT,
             color=INK)
    axB.text(0.53, 23.6, f"+{comp['n_pos']} / ={comp['n_zero']} / "
             f"−{comp['n_neg']}", ha="right", va="top", fontsize=FONT,
             color=INK)
    axB.set_xlim(-0.9, 0.55)
    axB.set_ylim(0, 24)
    axB.set_yticks([])
    axB.set_xlabel("Δ composite (navigation − rule)")
    axB.spines[["top", "right", "left"]].set_visible(False)
    axB.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── block C: per-target navigation raw spend ─────────────────────────
    axC = fig.add_axes([LEFT, 0.060, WIDTH, 0.185])
    spends = list(budget["per_target"].values())
    cap, mean = budget["cap"], budget["mean"]
    n_at_cap = sum(1 for s in spends if s == cap)
    for value, count in stacked_dots(spends, ndigits=6):
        axC.plot([value] * count, list(range(1, count + 1)), "o", ms=1.8,
                 mfc=C_NAV, mec=C_NAV, zorder=3, clip_on=False)
        if count >= 2 and value != cap:
            axC.text(value, count + 0.8, str(count), ha="center", va="bottom",
                     fontsize=FONT, color=INK, zorder=4,
                     bbox=dict(fc="white", ec="none", pad=0.5))
    # reference lines stop below the top annotations; the cap label carries
    # the cap-stack count
    axC.plot([cap] * 2, [0, 9.3], color=INK, lw=0.7, ls=(0, (2, 2)), zorder=2)
    axC.plot([mean] * 2, [0, 9.3], color=INK, lw=0.9, zorder=2)
    axC.text(0.6, 13.2, "0 violations · 0 LLM calls", ha="left", va="top",
             fontsize=FONT, color=INK)
    axC.text(34.2, 13.2, f"cap {cap} · {n_at_cap} at cap", ha="right",
             va="top", fontsize=FONT, color=INK)
    axC.text(mean + 0.8, 5.2, f"mean {mean:.1f}", ha="left", va="center",
             fontsize=FONT, color=INK, zorder=4)
    axC.set_xlim(0, 37.5)
    axC.set_ylim(0, 13.5)
    axC.set_xticks([0, 10, 20, 30])
    axC.set_yticks([])
    axC.set_xlabel("navigation raw generator spend (calls per target)")
    axC.spines[["top", "right", "left"]].set_visible(False)
    axC.tick_params(length=1.6, width=0.5, pad=1.6)

    # ── renderer-measured overflow guards (the house pattern): every text
    #    inside the canvas and no text–text collision anywhere ───────────
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    for t in [t for ax in fig.axes for t in ax.texts] + list(fig.texts):
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.x1 <= fig.bbox.width
                and bb.y0 >= 0 and bb.y1 <= fig.bbox.height), \
            f"text overflows canvas: {t.get_text()!r}"
        boxes.append((t, bb))
    for i, (t1, b1) in enumerate(boxes):
        for t2, b2 in boxes[i + 1:]:
            assert not b1.overlaps(b2), \
                f"text collision: {t1.get_text()!r} vs {t2.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5d_secondary_endpoint.{ext}", dpi=1200)
    plt.close(fig)
    print(f"wrote {OUT_DIR / 'fig5d_secondary_endpoint'}.{{pdf,png}} "
          f"({W_MM}x{H_MM} mm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
