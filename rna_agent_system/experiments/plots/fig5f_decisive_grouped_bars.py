"""Fig 5f — Aptamer decisive campaign: delivered cells, end-to-end targets
and discordance (Experiment 29, segment 3; the pre-registered primary
endpoint panel).

Main panel — grouped bars, three metric groups on the x axis, each with the
navigation arm (sage) against the static-grid arm (terracotta):
  delivered profile cells  (navigation n/36 vs static m/36, counts printed);
  targets with end-to-end delivery (all three profiles delivered, of the
  panel's targets);
  discordant cells (b navigation-only vs c rule-only) with the exact
  two-sided McNemar P and the pre-registered GO verdict annotated above.
Inset — the pair-outcome composition as one horizontal stacked bar (both
pass / navigation-only / rule-only / neither) with printed counts, the same
four categories the Fig 5g mosaic tiles carry.

Style (the fig5b/5c house style): no in-figure title — the panel letter is
added at assembly; every text element one 6-pt pure-black style; colours
exclusively from palette rev 7; absolute-mm geometry, single column;
1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/seg3_decisive/
        {runs.jsonl, verdict.json}
Usage : python experiments/plots/fig5f_decisive_grouped_bars.py
Output : experiments/plots/output/fig5f_decisive_grouped_bars.{pdf,png}
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
RUNS = (PROJECT_ROOT / "experiments" / "results"
        / "exp29_aptamer_campaign_arc" / "seg3_decisive" / "runs.jsonl")
VERDICT = (PROJECT_ROOT / "experiments" / "results"
           / "exp29_aptamer_campaign_arc" / "seg3_decisive" / "verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 56.0

C_NAV = PALETTE_BY_NAME["sage_green"]     # navigation arm
C_RULE = PALETTE_BY_NAME["terracotta"]    # static-grid arm
C_BOTH = PALETTE_BY_NAME["grey_blue"]     # both pass
C_NONE = PALETTE_BY_NAME["dark_warm_grey"]  # neither

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
W_PX = round(W_MM / 25.4 * DPI)
H_PX = round(H_MM / 25.4 * DPI)


def fmt_p(p: float) -> str:
    if p >= 0.01:
        return f"P = {p:.3f}".rstrip("0").rstrip(".")
    return f"P = {p:.2e}" if p > 0 else "P < 1e-300"


def main() -> int:
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    n_cells = verdict["n_cells"]
    n_targets = verdict["n_targets"]
    del_c = verdict["delivered_cells"]["C"]
    del_a = verdict["delivered_cells"]["A"]
    e2e_c = verdict["e2e_targets"]["C"]
    e2e_a = verdict["e2e_targets"]["A"]
    b = verdict["mcnemar"]["b_nav_only"]
    c_ = verdict["mcnemar"]["c_rule_only"]
    p = verdict["mcnemar"]["p_exact"]
    go = (verdict.get("go_rule") or {}).get("verdict", "—")
    po = verdict["pair_outcomes"]

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.115, 0.335, 0.60, 0.565])
    groups = [
        (f"Delivered cells\n(of {n_cells})", del_c, del_a, ""),
        (f"Targets e2e\n(of {n_targets})", e2e_c, e2e_a, ""),
        ("Discordant\ncells", b, c_, fmt_p(p)),
    ]
    ymax = max(del_c, del_a, e2e_c, e2e_a, b, c_, 1)
    for gi, (label, v_c, v_a, note) in enumerate(groups):
        for dx, val, color in ((-0.17, v_c, C_NAV), (0.17, v_a, C_RULE)):
            ax.bar(gi + dx, val, width=0.30, facecolor=color,
                   edgecolor="none", zorder=2)
            ax.annotate(str(val), (gi + dx, val),
                        textcoords="offset points", xytext=(0, 2),
                        ha="center", fontsize=FONT, color=INK)
        if note:
            ax.annotate(note, (gi, max(v_c, v_a)),
                        textcoords="offset points", xytext=(0, 11),
                        ha="center", fontsize=FONT, color=INK)
    ax.annotate(f"{go} (pre-registered)", (2, ymax * 0.98),
                ha="center", va="top", fontsize=FONT, color=INK)
    ax.set_xlim(-0.62, 2.62)
    ax.set_ylim(0, ymax * 1.38 + 1.0)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g[0] for g in groups], fontsize=FONT,
                       linespacing=1.25)
    ax.set_ylabel("Count", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── inset: pair-outcome stacked bar (the Fig 5g categories) ──
    axi = fig.add_axes([0.115, 0.105, 0.77, 0.085])
    cats = [("both", C_BOTH), ("nav", C_NAV), ("rule", C_RULE),
            ("none", C_NONE)]
    total = sum(po[k] for k, _ in cats) or 1
    x0 = 0.0
    for key, color in cats:
        frac = po[key] / total
        axi.add_patch(Rectangle((x0, 0.0), frac, 1.0, facecolor=color,
                                edgecolor="white", linewidth=0.4))
        if po[key] > 0 and frac > 0.05:
            axi.annotate(str(po[key]), (x0 + frac / 2, 0.5), ha="center",
                         va="center", fontsize=FONT, color=INK)
        x0 += frac
    axi.set_xlim(0, 1)
    axi.set_ylim(0, 1)
    axi.set_xticks([])
    axi.set_yticks([])
    for s in axi.spines.values():
        s.set_visible(False)
    axi.set_ylabel("Pairs", fontsize=FONT, rotation=0, ha="right",
                   va="center", labelpad=1.0)

    # key: arm + pair-outcome swatch row, renderer-measured widths
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [
        (C_NAV, "navigation"), (C_RULE, "static grid"),
        (C_BOTH, "both"), (C_NONE, "neither"),
    ]
    swatch_w = 0.014
    gap_in, gap_out = 0.006, 0.022
    parts = [("swatch", c) for c, _ in key_items[:2]] + \
            [("label", key_items[0][1]), ("label", key_items[1][1])] + \
            [("swatch", key_items[2][0]), ("label", key_items[2][1])] + \
            [("swatch", key_items[3][0]), ("label", key_items[3][1])]
    widths = [swatch_w + gap_in if k == "swatch" else
              text_w(v) + gap_out for k, v in parts]
    total_w = sum(widths)
    assert total_w < 0.90, f"key row overflows canvas: {total_w:.3f}"
    x = 0.5 - total_w / 2
    y = 0.028
    from matplotlib.axes import Axes  # noqa: E402
    for (kind, val), w in zip(parts, widths):
        if kind == "swatch":
            sax = fig.add_axes([x, y - 0.008, swatch_w, 0.014])
            sax.set_xticks([]), sax.set_yticks([])
            for s in sax.spines.values():
                s.set_visible(False)
            sax.set_facecolor(val)
        else:
            fig.text(x, y - 0.003, val, fontsize=FONT, color=INK,
                     va="center_baseline")
        x += w

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5f_decisive_grouped_bars.{ext}", dpi=1200)
    plt.close(fig)
    print(f"wrote fig5f_decisive_grouped_bars "
          f"(delivered {del_c}:{del_a} of {n_cells}, "
          f"e2e {e2e_c}:{e2e_a} of {n_targets}, "
          f"b:c = {b}:{c_}, {fmt_p(p)}, {go})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
