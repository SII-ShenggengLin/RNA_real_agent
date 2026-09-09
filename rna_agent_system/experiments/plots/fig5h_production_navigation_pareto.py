"""Fig 5h — Production navigation live run: cost–delivery Pareto
(Experiment 30, 2026-09-05, the paper's citation).

Single-view scatter (the 2026-09-08 one-plot-per-panel user-directed
convention, as applied to fig5d/5f/5g): every Exp-30 form-entry campaign
on its shipped navigator — raw generator spend (x) against delivered
profile cells (0–3, y).  The mRNA arm (GenNav-λ, 35-raw cap, grey blue
circles — 5 targets, 13/15 cells, all early stops 11–28/35) against the
aptamer arm (ODesign lattice, 48-raw cap, mauve triangles — 6 targets,
8/18 cells, 47–48/48).  Dashed verticals mark the two caps
(arm-coloured); black rings mark each arm's Pareto corner (best delivery
per raw: PTH + CSF3 3/3 at 11, IFN-γ 3/3 at 47) joined by the 4.3×
same-delivery cost annotation.  swine H3 HA (48 raw, 0 cells) is the
measured scarcity boundary.

2026-09-08 figure-repair pass (user direction): the aptamer
breakthrough step-line inset was removed — one plot per panel, and the
inset shared neither axis nor observation unit with the Pareto scatter
(per-round cumulative trajectories vs per-campaign final coordinates).
Its numbers are text-reported verbatim in the Fig. 5h caption and §2.5
(IFN-γ steps up at 29/35/47 raw, PDGF-BB only at 36/48, swine H3 HA flat
to the cap; the mRNA gap→cell mapping is cut by the delivery-stage D1
floor, so no mRNA step-line exists).  The in-axes inset title ("Aptamer
breakthrough") went with it — Nature-style panels carry no in-figure
title (the panel letter is added at assembly).  All text unified to one
6-pt pure-black style; the arm key (the fig5g two-row convention, one
marker per row) carries the per-arm delivery/spend summary; the separate
cap labels and the in-axes stat lines are gone; the coincident PTH/CSF3
pair is drawn as one marker with a shared label instead of a dodge.

Style (the fig5b–5g house style): no in-figure title; every text element
one 6-pt pure-black style; colours exclusively from palette rev 7;
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF (fonttype
42); renderer-measured guards — every text inside the canvas, no
text–text collision, no text–marker collision.

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
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE = PROJECT_ROOT / "experiments" / "results" / "exp30_production_navigation_live"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 52.5

C_MRNA = PALETTE_BY_NAME["grey_blue"]         # mRNA navigation arm
C_APT = PALETTE_BY_NAME["dusty_mauve_pink"]   # aptamer navigation arm

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

DPI = 1200
W_PX = round(W_MM / 25.4 * DPI)   # exact 1200-dpi canvas pixels
H_PX = round(H_MM / 25.4 * DPI)


def load_records(stage: str) -> list[dict]:
    path = BASE / stage / "runs.jsonl"
    return [json.loads(ln) for ln
            in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> int:
    apt = load_records("aptamer")
    mrna = load_records("mrna")

    # ── every drawn coordinate and printed number derived from the records ──
    pts = {r["target_id"]: (r["raw_spent"], r["cells_pass_count"])
           for r in mrna + apt}
    assert pts == {
        "PTH": (11, 3), "CSF3": (11, 3), "LEP": (12, 2), "PLAT": (24, 2),
        "THPO": (28, 3), "IFN-gamma": (47, 3), "PDGF-BB": (48, 2),
        "FGF2": (48, 1), "IL-17A": (48, 1), "Angiopoietin-2": (48, 1),
        "Influenza H3N2 HA": (48, 0),
    }
    mrna_cells = sum(r["cells_pass_count"] for r in mrna)
    apt_cells = sum(r["cells_pass_count"] for r in apt)
    mrna_mean = sum(r["raw_spent"] for r in mrna) / len(mrna)
    apt_mean = sum(r["raw_spent"] for r in apt) / len(apt)
    assert (mrna_cells, apt_cells) == (13, 8)
    assert f"{mrna_mean:.1f}" == "17.2" and f"{apt_mean:.1f}" == "47.8"

    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.105, 0.335, 0.86, 0.615])

    texts: list[matplotlib.text.Text] = []

    def note(s: str, xy, va: str = "center", **kw) -> None:
        art = ax.annotate(s, xy, va=va, fontsize=FONT, color=INK, **kw)
        texts.append(art)

    # ── caps (arm-coloured; identified by the key, no separate labels) ──
    for cap, colour in ((35, C_MRNA), (48, C_APT)):
        ax.axvline(cap, color=colour, lw=0.6, ls=(0, (3, 2)), zorder=1)

    # ── points + target labels (PTH/CSF3 coincide at (11, 3) → one marker,
    #    shared label; the three 48-raw 1-cell aptamer campaigns fanned
    #    ±0.8 for visibility) ──
    markers: list[tuple[float, float, float]] = []  # (x, y, ms) for guards
    mrna_pts = [  # (x, y, label, dx_pt, dy_pt, ha)
        (11, 3, "PTH + CSF3", 0, -11, "center"),
        (12, 2, "LEP", 0, -10, "center"),
        (24, 2, "PLAT", 0, -10, "center"),
        (28, 3, "THPO", 0, -10, "center"),
    ]
    for x, y, label, dx, dy, ha in mrna_pts:
        ax.plot(x, y, "o", color=C_MRNA, ms=3.6, zorder=3)
        markers.append((x, y, 3.6))
        note(label, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha)

    apt_pts = [
        (47, 3, "IFN-\u03b3", -8, 0, "right"),
        (48, 2, "PDGF-BB", -7, 0, "right"),
        (47.2, 1, "FGF2", -6, 0, "right"),
        (48, 1, "IL-17A", -8, -8, "right"),
        (48.8, 1, "Ang2", 6, 0, "left"),
        (48, 0, "swine H3 HA", -7, -1, "right"),
    ]
    for x, y, label, dx, dy, ha in apt_pts:
        ax.plot(x, y, "^", color=C_APT, ms=4.0, zorder=3)
        markers.append((x, y, 4.0))
        note(label, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha)

    # ── Pareto corners + the same-delivery cost ratio ──
    for x, y in ((11, 3), (47, 3)):
        ax.plot(x, y, "o", ms=7, mfc="none", mec=INK, mew=0.7, zorder=4)
        markers.append((x, y, 7))
    ax.annotate("", xy=(45.5, 3.3), xytext=(12.5, 3.3),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color=INK,
                                shrinkA=0, shrinkB=0))
    note("equal 3/3 \u00b7 4.3\u00d7 raw", (27, 3.3), xytext=(0, 3),
         textcoords="offset points", ha="center", va="bottom")

    ax.set_xlim(5, 53.5)
    ax.set_ylim(-0.5, 3.75)
    ax.set_xticks([10, 20, 30, 40, 50])
    ax.set_yticks([0, 1, 2, 3])
    ax.set_xlabel("Raw generator spend", fontsize=FONT)
    ax.set_ylabel("Delivered profile cells (of 3)", fontsize=FONT)
    ax.tick_params(length=2.0, pad=1.8, labelsize=FONT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # ── arm key (the fig5g two-row convention: one marker per row, per-arm
    #    summary appended; renderer-measured, block-centred) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    key_items = [
        ("o", C_MRNA,
         f"mRNA GenNav-\u03bb (cap 35) \u00b7 {mrna_cells}/15 cells "
         f"\u00b7 mean {mrna_mean:.1f} raw"),
        ("^", C_APT,
         f"aptamer ODesign lattice (cap 48) \u00b7 {apt_cells}/18 cells "
         f"\u00b7 mean {apt_mean:.1f} raw"),
    ]
    row_w = [0.014 + 0.008 + text_w(label) for _, _, label in key_items]
    assert max(row_w) < 0.92, f"key row overflows canvas: {max(row_w):.3f}"
    x0 = 0.5 - max(row_w) / 2
    key_texts = []
    for (marker, colour, label), y in zip(key_items, (0.128, 0.053)):
        fig.add_artist(Line2D([x0], [y], color=colour, lw=0.0,
                              marker=marker, ms=3.6))
        key_texts.append(fig.text(x0 + 0.022, y, label, fontsize=FONT,
                                  color=INK, va="center"))

    # ── renderer-measured guards (the house pattern): every text inside the
    #    canvas, no text–text collision, no text–marker collision ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    all_texts = (texts + key_texts + [ax.xaxis.label, ax.yaxis.label]
                 + list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
    boxes = []
    for t in all_texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.x1 <= fig.bbox.width
                and bb.y0 >= 0 and bb.y1 <= fig.bbox.height), \
            f"text overflows canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {all_texts[i].get_text()!r} x " \
                f"{all_texts[j].get_text()!r}"
    pad = 0.4 / 25.4 * fig.dpi  # 0.4 mm clearance around every marker
    for x, y, ms in markers:
        px, py = ax.transData.transform((x, y))
        r = ms / 2 / 72 * fig.dpi + pad
        mb = Bbox([[px - r, py - r], [px + r, py + r]])
        for t, bb in zip(all_texts, boxes):
            assert not mb.overlaps(bb), \
                f"text on marker ({x}, {y}): {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5h_production_navigation_pareto.{ext}",
                    dpi=DPI)
    plt.close(fig)

    img = mpimg.imread(OUT_DIR / "fig5h_production_navigation_pareto.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    print(f"wrote {OUT_DIR / 'fig5h_production_navigation_pareto'}.{{pdf,png}} "
          f"({W_MM}x{H_MM} mm, {W_PX}x{H_PX} px @ {DPI} dpi; "
          f"Exp 30: {len(apt)} aptamer + {len(mrna)} mRNA campaigns)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
