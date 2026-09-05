"""Fig 5h — Production navigation live run: cost-delivery Pareto +
breakthrough step-line inset (Experiment 30, 2026-09-05, the paper's
citation; replaces the interim Exp-29 sweep curve registered mid-stop).

Main panel — every Exp-30 form-entry campaign on its shipped navigator,
raw generator spend (x) against delivered profile cells (0-3, y): the
mRNA arm (GenNav-lambda, 35-raw cap, grey blue circles — 5 targets, 13/15
cells, all early stops 11-28/35) against the aptamer arm (ODesign
lattice, 48-raw cap, mauve triangles — 6 targets, 8/18 cells, 47-48/48).
Dashed verticals mark the two caps; equal-capture rings mark each arm's
Pareto corner (best delivery per raw: PTH+CSF3 3/3 at 11, IFN-gamma 3/3
at 47) joined by the 4.3x same-delivery cost annotation.  swH3 HA
(48 raw, 0 cells) is the measured scarcity boundary.

Inset — aptamer breakthrough step-lines (gap-chain reconstruction, exact:
probe + round n_samples sums equal raw_spent and the final step equals
the recorded cells): IFN-gamma delivers at 29/35/47 raw, PDGF-BB only at
36/48, swH3 HA never (flat zero to the cap).  mRNA step-lines are not
drawn: their gap-to-cell mapping is cut by the delivery-stage D1 floor
(LEP/PLAT end at 2 cells with all matrix gaps zero — shown in the main
panel as 2-cell points).

Style (the fig5b-5g house style): no in-figure title; every text element
one 6-pt pure-black style; colours exclusively from palette rev 7;
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF (fonttype
42).

Data  : experiments/results/exp30_production_navigation_live/
        {aptamer,mrna}/runs.jsonl
Usage : python experiments/plots/fig5h_production_navigation_pareto.py
Output : experiments/plots/output/fig5h_production_navigation_pareto.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE = PROJECT_ROOT / "experiments" / "results" / "exp30_production_navigation_live"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 62.0

C_MRNA = PALETTE_BY_NAME["grey_blue"]        # mRNA navigation arm
C_APT = PALETTE_BY_NAME["dusty_mauve_pink"]   # aptamer navigation arm
C_STEP = {  # inset step-lines, decorative (named at line ends)
    "IFN-gamma": PALETTE_BY_NAME["slate_blue"],
    "PDGF-BB": PALETTE_BY_NAME["mauve_grey"],
    "swH3": PALETTE_BY_NAME["dark_warm_grey"],
}
C_GRID = "#D9D9D9"

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


def load_records(stage: str) -> list[dict]:
    path = BASE / stage / "runs.jsonl"
    return [json.loads(ln) for ln
            in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def staircase(rec: dict) -> tuple[list[int], list[int]]:
    """Exact aptamer gap-chain reconstruction: cumulative raw spend (x)
    against delivered cells (y) at probe end and after every round.

    Delivery gap zero == a delivered cell for the aptamer arm (verified:
    final gap-0 count == the recorded cells_pass_count for all six
    campaigns), gaps are monotone non-increasing (pool only grows), and
    probe + round n_samples sums equal raw_spent.
    """
    spend = rec["probe"]["n_lengths"]
    rounds, fg = rec["rounds"], rec["final_gaps"]
    cells0 = sum(1 for v in rounds[0]["gaps_before"].values() if v == 0) \
        if rounds else sum(1 for v in fg.values() if v == 0)
    xs, ys = [0, spend], [0, cells0]
    for i, rd in enumerate(rounds):
        spend += rd["n_samples"]
        gaps = rounds[i + 1]["gaps_before"] if i + 1 < len(rounds) else fg
        xs.append(spend)
        ys.append(sum(1 for v in gaps.values() if v == 0))
    assert spend == rec["raw_spent"], (rec["target_id"], spend)
    assert ys[-1] == rec["cells_pass_count"], (rec["target_id"], ys[-1])
    return xs, ys


def main() -> int:
    apt = load_records("aptamer")
    mrna = load_records("mrna")

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.105, 0.315, 0.545, 0.60])

    label_texts: list[tuple[str, matplotlib.text.Text]] = []

    def note(axis, s: str, xy, **kw) -> matplotlib.text.Text:
        art = axis.annotate(s, xy, **kw)
        if s:
            label_texts.append((s, art))
        return art

    # ── caps ──
    for cap, colour, ha, x_txt in ((35, C_MRNA, "right", 34.3),
                                   (48, C_APT, "left", 48.5)):
        ax.axvline(cap, color=colour, lw=0.6, ls=(0, (3, 2)), zorder=1)
        note(ax, f"cap {cap}", (x_txt, 3.54), ha=ha, va="center",
             fontsize=FONT - 0.5, color=INK)

    # ── mRNA points (dodge the coincident PTH/CSF3 pair) ──
    mrna_pts = [  # (x, y, label, dx_label_pt, dy_label_pt, ha)
        (10.5, 3, None, 0, 0, "center"),          # PTH (dodged)
        (11.5, 3, "PTH + CSF3", 0, -13, "center"),  # CSF3 (dodged) + shared label
        (12, 2, "LEP", 5, -9, "center"),
        (24, 2, "PLAT", 0, -9, "center"),
        (28, 3, "THPO", 2, -9, "center"),
    ]
    for x, y, label, dx, dy, ha in mrna_pts:
        ax.plot(x, y, "o", color=C_MRNA, ms=3.4, zorder=3)
        if label:
            note(ax, label, (x, y), xytext=(dx, dy),
                 textcoords="offset points", ha=ha,
                 fontsize=FONT - 0.5, color=INK)

    # ── aptamer points (dodge the 48/1 trio; labels left of the cap line,
    #    staggered in two rows; Ang2 sits right of the line) ──
    apt_pts = [
        (47, 3, "IFN-\u03b3", -14, -2, "right"),
        (48, 2, "PDGF-BB", -7, -9, "right"),
        (47.2, 1, "FGF2", -4, -8, "right"),
        (48.0, 1, "IL-17A", -8, -19, "right"),
        (48.8, 1, "Ang2", 4, -8, "left"),
        (48, 0, "swH3 HA", -9, -2, "right"),
    ]
    for x, y, label, dx, dy, ha in apt_pts:
        ax.plot(x, y, "^", color=C_APT, ms=3.9, zorder=3)
        note(ax, label, (x, y), xytext=(dx, dy),
             textcoords="offset points", ha=ha,
             fontsize=FONT - 0.5, color=INK)

    # ── Pareto corners + the same-delivery cost ratio ──
    for x, y in ((11.0, 3), (47, 3)):
        ax.plot(x, y, "o", ms=6.4, mfc="none", mec=INK, mew=0.7, zorder=4)
    ax.annotate("", xy=(46.0, 3.30), xytext=(12.0, 3.30),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color=INK,
                                shrinkA=0, shrinkB=0))
    note(ax, "equal 3/3 \u00b7 4.3\u00d7 raw", (23.0, 3.30),
         xytext=(0, -10), textcoords="offset points", ha="center",
         fontsize=FONT - 0.5, color=INK)

    # ── per-arm summary block (bottom-left free zone) ──
    label_texts.append(("stats-mrna", ax.text(
        6.2, 0.62, "mRNA: 13/15 cells \u00b7 mean 17.2/35 raw",
        fontsize=FONT - 0.5, color=INK)))
    label_texts.append(("stats-apt", ax.text(
        6.2, 0.18, "aptamer: 8/18 cells \u00b7 mean 47.8/48 raw",
        fontsize=FONT - 0.5, color=INK)))

    ax.set_xlim(5, 52)
    ax.set_ylim(-0.45, 3.62)
    ax.set_xticks([10, 20, 30, 40, 50])
    ax.set_yticks([0, 1, 2, 3])
    ax.set_xlabel("Raw generator spend", fontsize=FONT)
    ax.set_ylabel("Delivered cells (of 3)", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── inset: aptamer breakthrough step-lines (exact reconstruction) ──
    axi = fig.add_axes([0.700, 0.425, 0.225, 0.27])
    recs = {r["target_id"]: r for r in apt}
    inset_lines = [  # (record, colour, end label, label dx/dy, ha)
        (recs["IFN-gamma"], C_STEP["IFN-gamma"], "IFN-\u03b3 3", (-3, 1.5), "right"),
        (recs["PDGF-BB"], C_STEP["PDGF-BB"], "PDGF-BB 2", (-3, -7.5), "right"),
        (recs["Influenza H3N2 HA"], C_STEP["swH3"], "swH3 HA 0", (-3, 2.5), "right"),
    ]
    for rec, colour, label, (dx, dy), ha in inset_lines:
        xs, ys = staircase(rec)
        axi.step(xs, ys, where="post", color=colour, lw=1.0, zorder=3)
        axi.plot(xs[-1], ys[-1], "o", color=colour, ms=2.4, zorder=4)
        note(axi, label, (xs[-1], ys[-1]), xytext=(dx, dy),
             textcoords="offset points", ha=ha,
             fontsize=FONT - 0.5, color=INK)
    axi.axvline(48, color=C_APT, lw=0.5, ls=(0, (3, 2)), zorder=1)
    axi.set_xlim(0, 55)
    axi.set_ylim(-0.3, 3.45)
    axi.set_xticks([0, 24, 48])
    axi.set_yticks([0, 1, 2, 3])
    axi.set_xlabel("Cumulative raw", fontsize=FONT, labelpad=1.0)
    axi.set_ylabel("Cells", fontsize=FONT, labelpad=1.0)
    axi.tick_params(length=1.5, pad=1.2, labelsize=FONT - 0.5)
    axi.set_title("Aptamer breakthrough", fontsize=FONT, color=INK, pad=2.0)
    for s in axi.spines.values():
        s.set_linewidth(0.4)

    # ── programmatic collision check: every annotation/label text box the
    #    script created must be pairwise disjoint (1-px tol) and in-canvas
    #    (axis tick labels excluded — managed by the axis machinery) ──
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    issues = []
    for i, (t1, a1) in enumerate(label_texts):
        b1 = a1.get_window_extent(rend)
        if b1.x0 < 0 or b1.y0 < 0 or b1.x1 > fig.bbox.width or b1.y1 > fig.bbox.height:
            issues.append(f"outside canvas: {t1!r}")
        for t2, a2 in label_texts[i + 1:]:
            b2 = a2.get_window_extent(rend)
            if (b1.x0 - 1 < b2.x1 and b2.x0 - 1 < b1.x1 and
                    b1.y0 - 1 < b2.y1 and b2.y0 - 1 < b1.y1):
                issues.append(f"text overlap: {t1!r} <-> {t2!r}")
    assert not issues, "; ".join(issues)

    # key row (renderer-measured widths, canvas-overflow assert)
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [
        ("o", C_MRNA, "mRNA GenNav-\u03bb (cap 35)"),
        ("^", C_APT, "aptamer ODesign lattice (cap 48)"),
    ]
    gap = 0.030
    widths = [0.016 + 0.006 + text_w(label) + gap for _, _, label in key_items]
    total_w = sum(widths)
    assert total_w < 0.90, f"key row overflows canvas: {total_w:.3f}"
    x = 0.5 - total_w / 2
    y = 0.065
    for (marker, colour, label), w in zip(key_items, widths):
        fig.add_artist(Line2D([x, x + 0.016], [y, y], color=colour,
                              lw=0.0, marker=marker, ms=3.6))
        fig.text(x + 0.022, y - 0.003, label, fontsize=FONT, color=INK,
                 va="center_baseline")
        x += w

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5h_production_navigation_pareto.{ext}",
                    dpi=1200)
    plt.close(fig)
    print("wrote fig5h_production_navigation_pareto "
          f"(Exp 30: {len(apt)} aptamer + {len(mrna)} mRNA campaigns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
