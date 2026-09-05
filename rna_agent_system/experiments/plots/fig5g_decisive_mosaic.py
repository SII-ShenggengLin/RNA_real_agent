"""Fig 5g — Aptamer decisive-campaign delivery map: the 12 × 3 pair-outcome
mosaic (Experiment 29, segment 3).

One tile per (target, profile) cell, coloured by the paired delivery outcome
of the two arms — navigation-only pass (sage), both arms pass (grey blue),
static-grid-only pass (terracotta), neither passes (dark warm grey).  A
right-hand marker column carries the target-level navigation end-to-end
glyph (filled = all three profiles delivered).  Rows follow the registered
panel-D order (most delivery-scarce under the segment-2 static arm first —
the pre-registered selection rule); the three profile columns are headed
Compact / Standard / Extended.

Style (the fig5c carpet house style): no in-figure title; every text element
one 6-pt pure-black style; colours exclusively from palette rev 7;
absolute-mm geometry, single column; 1200-dpi PNG + vector PDF (fonttype 42).

Data  : experiments/results/exp29_aptamer_campaign_arc/
        {panels.json, seg3_decisive/runs.jsonl}
Usage : python experiments/plots/fig5g_decisive_mosaic.py
Output : experiments/plots/output/fig5g_decisive_mosaic.{pdf,png}
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
BASE = PROJECT_ROOT / "experiments" / "results" / "exp29_aptamer_campaign_arc"
RUNS = BASE / "seg3_decisive" / "runs.jsonl"
PANELS = BASE / "panels.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 80.0

C_BOTH = PALETTE_BY_NAME["grey_blue"]       # both arms pass
C_NAV = PALETTE_BY_NAME["sage_green"]       # navigation-only pass
C_RULE = PALETTE_BY_NAME["terracotta"]      # static-grid-only pass
C_NONE = PALETTE_BY_NAME["dark_warm_grey"]  # neither passes
C_GRID = "#D9D9D9"

PROFILES = ["compact", "standard", "extended"]
PROFILE_LABELS = ["Compact", "Standard", "Extended"]

_SHORT = {
    "SARS-CoV-2_Nucleocapsid": "SARS-CoV-2 N",
    "Carbonic_anhydrase_II": "Carbonic anh. II",
    "TNF_alpha": "TNF-α",
    "RNase_A": "RNase A",
    "Concanavalin_A": "Concanavalin A",
    "Cytochrome_c": "Cytochrome c",
    "Chymotrypsinogen": "Chymotrypsinogen",
    "Beta_galactosidase": "β-galactosidase",
}

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


def main() -> int:
    records = [json.loads(ln) for ln in RUNS.read_text(encoding="utf-8")
               .splitlines() if ln.strip()]
    records = {r["target_id"]: r for r in records if r.get("success")}
    panels = json.loads(PANELS.read_text(encoding="utf-8"))
    targets = [t for t in panels["panel_D_decisive"] if t in records]

    n = len(targets)
    fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI))
    ax = fig.add_axes([0.315, 0.085, 0.44, 0.825])
    ax.set_xlim(0, 3)
    ax.set_ylim(0, n)
    ax.invert_yaxis()
    ax.set_aspect("auto")

    counts = {"both": 0, "nav": 0, "rule": 0, "none": 0}
    for row, target in enumerate(targets):
        rec = records[target]
        cc = rec["arms"]["C"]["cells_pass"]
        ca = rec["arms"]["A"]["cells_pass"]
        for col, profile in enumerate(PROFILES):
            c_pass, a_pass = cc.get(profile, False), ca.get(profile, False)
            if c_pass and a_pass:
                color, key = C_BOTH, "both"
            elif c_pass:
                color, key = C_NAV, "nav"
            elif a_pass:
                color, key = C_RULE, "rule"
            else:
                color, key = C_NONE, "none"
            counts[key] += 1
            ax.add_patch(Rectangle((col + 0.06, row + 0.14), 0.88, 0.72,
                                   facecolor=color, edgecolor="white",
                                   linewidth=0.4))

    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(PROFILE_LABELS)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks([i + 0.5 for i in range(n)])
    ax.set_yticklabels([_SHORT.get(t, t) for t in targets])
    ax.tick_params(length=0, pad=1.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="x", pad=2.2)

    # target-level navigation e2e marker column (right)
    axg = fig.add_axes([0.775, 0.085, 0.045, 0.825], sharey=ax)
    axg.set_xlim(0, 1)
    axg.set_ylim(0, n)
    axg.invert_yaxis()
    for row, target in enumerate(targets):
        e2e_c = records[target]["arms"]["C"]["e2e"]
        axg.add_patch(Rectangle((0.12, row + 0.30), 0.76, 0.40,
                                facecolor=(C_NAV if e2e_c else "white"),
                                edgecolor=(INK if e2e_c else C_GRID),
                                linewidth=0.5))
    axg.set_xticks([])
    axg.set_yticks([])
    for s in axg.spines.values():
        s.set_visible(False)
    axg.set_title("Target\ne2e", fontsize=FONT, color=INK, pad=2.2)

    # key: single centred row under the mosaic, renderer-measured widths
    key_items = [
        (C_NAV, "navigation-only"),
        (C_BOTH, "both"),
        (C_RULE, "grid-only"),
        (C_NONE, "neither"),
    ]
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    swatch_w = 0.014
    gap_in, gap_out = 0.006, 0.018
    parts = []
    for color, label in key_items:
        parts.append(("swatch", color))
        parts.append(("label", label))
    widths = [swatch_w + gap_in if k == "swatch" else
              text_w(v) + gap_out for k, v in parts]
    total_w = sum(widths)
    assert total_w < 0.90, f"key row overflows canvas: {total_w:.3f}"
    x = 0.5 - total_w / 2
    y = 0.035
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
        fig.savefig(OUT_DIR / f"fig5g_decisive_mosaic.{ext}", dpi=1200)
    plt.close(fig)
    print(f"wrote fig5g_decisive_mosaic (n={n} targets; "
          f"nav {counts['nav']} / both {counts['both']} / "
          f"rule {counts['rule']} / none {counts['none']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
