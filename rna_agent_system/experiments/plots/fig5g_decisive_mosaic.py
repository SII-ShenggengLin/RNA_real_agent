"""Fig 5g — Aptamer delivery map: the 26 × 3 pair-outcome mosaic pooled over
every dual-arm target (Experiment 29 delivery-scarce + confirmation
segments + Experiment 40 deployment completion).

One tile per (target, profile) pair, coloured by the paired delivery
outcome of the two conditions — navigation-only (sage), both-pass (grey
blue), static-only (terracotta), both-fail (dark warm grey; the Fig. 5g
legend's class names).  A marker row underneath the mosaic carries the
target-level navigation end-to-end glyph (filled = navigation delivered a
passing candidate in all three length profiles).  Columns follow the
segment order — the 12 delivery-scarce targets (most delivery-scarce
under the segment-2 static condition — the pre-registered selection
rule), the 8 confirmation complement, then the 6 deployment targets
(Exp-30 form-entry campaigns, static condition completed by Exp 40),
with dividers between cohorts; the three profile rows are labelled
Compact / Standard / Extended down the left edge (the aptamer length
profiles 25–34 / 40–55 / 61–80 nt); the key below carries the per-class
pair counts and a second row explaining the end-to-end glyph.

2026-10-10 transposed re-render (user-directed Fig. 5 composite-length
batch): the mosaic transposed to a full-width, short panel — targets on
the x axis (26 columns, 45°-rotated labels — the fig3a house idiom),
profiles on the y axis, the end-to-end marker column becoming a marker
row (the legend's "end-to-end column" wording became "end-to-end row" in
the same batch); canvas 89 × 132.2 → 183 × 50 mm (the fig5c geometry)
so the panel takes a full composite row at a third of its former height.
One shared axes carries the three profile rows and the marker row
(uniform 4.6-mm unit row pitch, a 0.3-unit gap band between mosaic and
marker row), so all four left row labels align on one right edge by
construction.  No number, colour or class assignment changed; every
tile, divider, glyph and key item is the same information re-oriented.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch): the
one-line context strip deleted (the key's class names self-decode the
tile colours and the dividers stay unlabelled — the strip carried the
retired "arm/cohort" wording); the key labels aligned to the legend's
class names — "navigation only" → "navigation-only", "both arms" →
"both-pass", "static grid only" → "static-only", "neither" →
"both-fail"; no number, colour or geometry changed.

2026-09-08 figure-repair pass (user direction):
- row labels (target names) restored — the marker-column axes previously
  shared y with the mosaic and its set_yticks([]) call wiped the shared
  y-axis ticks, deleting every row label from the rendered canvas (the same
  defect repaired in fig5c);
- "Target e2e" is no longer a floating two-line axes title (its first line
  sat a full line above the profile headers); spelt out per the fig5f
  convention, it is now "End-to-end", a single-line column header on the
  same baseline as Compact / Standard / Extended;
- margins rebalanced — the content block (row labels + mosaic + marker
  column) is horizontally centred, tiles widened 11.5 → 14.7 mm (the fig5c
  tile geometry);
- the key gains per-class cell counts and a second row explaining the
  e2e glyph; the open-marker outline moved off-palette #D9D9D9 → palette
  warm grey;
- canvas 89 × 80 → 89 × 71.2 mm (12 rows at the fig5c 4.35-mm row pitch).

2026-09-12 pooled re-render (user-directed merge): 12 → 26 rows (the seg4
confirmation complement + the six Exp-30 deployment targets appended below
labelled cohort dividers; the deployment navigation cells are the frozen
form-session records, the static grid is Exp 40's completion); canvas
89 × 71.2 → 89 × 132.2 mm (26 rows at the unchanged 4.35-mm row pitch).

Style (the fig5c carpet house style): no in-figure title (the panel letter
is added at assembly); every text element one 6-pt pure-black style;
colours exclusively from palette rev 7; absolute-mm geometry, double
column; 1200-dpi PNG + vector PDF (fonttype 42).  Programmatic guards:
every text in-canvas, pairwise text non-collision (rotated column labels
checked by the pitch-clearance and key-clearance asserts — their
axis-aligned boxes overlap by construction at a 6.2-mm pitch while the
labels themselves stay 4.4 mm apart perpendicular), left row labels clear
of the mosaic, exact canvas pixels, the frozen legend counts, raster
palette purity (greys + palette↔white/black blends only), white outer
border.

Data  : experiments/results/exp29_aptamer_campaign_arc/
        {panels.json, seg3_decisive/runs.jsonl, seg4_confirmation/runs.jsonl}
        + experiments/results/exp40_static_completion/aptamer/runs.jsonl
Usage : python experiments/plots/fig5g_decisive_mosaic.py
Output : experiments/plots/output/fig5g_decisive_mosaic.{pdf,png}

2026-10-10 tile colours: back to the original pairing (user-directed,
after five exploration rounds — lighter tints, a sand/mauve ladder, a
cool-trio candidate, an f-harmonised grey-blue/terracotta set and a
mauve-grey swap, all user-rejected): sage navigation-only, grey-blue
both-pass, terracotta static-only, dark-warm-grey both-fail, light
warm-grey cohort dividers and open marker outlines — the constants the
2026-09 carpet shipped with.  The transposed layout above is unaffected;
no number, class assignment or geometry change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE = PROJECT_ROOT / "experiments" / "results" / "exp29_aptamer_campaign_arc"
RUNS_SEG3 = BASE / "seg3_decisive" / "runs.jsonl"
RUNS_SEG4 = BASE / "seg4_confirmation" / "runs.jsonl"
RUNS_E40 = (PROJECT_ROOT / "experiments" / "results"
            / "exp40_static_completion" / "aptamer" / "runs.jsonl")
PANELS = BASE / "panels.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 183.0, 50.0

C_BOTH = PALETTE_BY_NAME["grey_blue"]       # both-pass
C_NAV = PALETTE_BY_NAME["sage_green"]       # navigation-only
C_RULE = PALETTE_BY_NAME["terracotta"]      # static-only
C_NONE = PALETTE_BY_NAME["dark_warm_grey"]  # both-fail
C_OPEN = PALETTE_BY_NAME["warm_grey"]       # open e2e-marker outline

PROFILES = ["compact", "standard", "extended"]
PROFILE_LABELS = ["Compact", "Standard", "Extended"]

_SHORT = {
    "SARS-CoV-2_Nucleocapsid": "SARS-CoV-2 N",
    "TNF_alpha": "TNF-α",
}


def short_name(t: str) -> str:
    return _SHORT.get(t, t.replace("_", " "))


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

# absolute-mm horizontal layout (transposed: one target per column; the
# fig5c geometry — same mosaic width, one more column)
MOSAIC_W_MM = 162.0     # 26 columns ≈ 6.2 mm each
GAP_LABEL_MM = 1.2      # left row-label block → mosaic
# absolute-mm vertical layout (data units are 4.6 mm each; y grows down)
UNIT_MM = 4.6
Y_MARK0 = 3.3           # marker row band [3.3, 4.3); gap band [3.0, 3.3)
Y_LIM = 4.3
LEG1_Y_MM = 7.8         # key row 1 (tile outcomes) baseline
LEG2_Y_MM = 3.9         # key row 2 (end-to-end glyph) baseline
TOP_MM = 1.3            # white above the mosaic
XLBL_PAD_PT = 2.8       # mosaic bottom → rotated-label anchors

# cohort divider columns: seg3|seg4 at 12, seg4|deployment at 20
DIVIDER_COLS = (12, 20)
# the legend's frozen counts (Fig. 5g legend, verbatim)
FROZEN_COUNTS = {"nav": 18, "both": 30, "rule": 12, "none": 18}
FROZEN_E2E = 7


def nav_cells(rec: dict) -> dict:
    if "nav_frozen" in rec:
        return dict(rec["nav_frozen"]["cells_pass"])
    return dict(rec["arms"]["C"]["cells_pass"])


def static_cells(rec: dict) -> dict:
    if "static" in rec:
        return dict(rec["static"]["cells_pass"])
    return dict(rec["arms"]["A"]["cells_pass"])


def nav_e2e(rec: dict) -> bool:
    if "nav_frozen" in rec:
        return bool(rec["nav_frozen"]["e2e"])
    return bool(rec["arms"]["C"]["e2e"])


def main() -> int:
    records: dict[str, dict] = {}
    for path in (RUNS_SEG3, RUNS_SEG4, RUNS_E40):
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                if rec.get("success") and rec["target_id"] not in records:
                    records[rec["target_id"]] = rec
    panels = json.loads(PANELS.read_text(encoding="utf-8"))
    deployment = sorted(t for t in records if "nav_frozen" in records[t])
    targets = ([t for t in panels["panel_D_decisive"] if t in records]
               + [t for t in panels["panel_C_confirmation"] if t in records]
               + [t for t in deployment if t in records])

    n = len(targets)
    # +1e-9 in: defeat float truncation so the saved canvas is exactly
    # W_PX × H_PX (matplotlib takes int(figsize × dpi))
    fig = plt.figure(figsize=(W_PX / DPI + 1e-9, H_PX / DPI + 1e-9))

    # provisional axes — drawn once to measure the real left row-label
    # widths, then repositioned so the whole content block is centred
    ax = fig.add_axes([0.3, 0.3, 0.5, 0.4])
    ax.set_xlim(0, n)
    ax.set_ylim(0, Y_LIM)
    ax.invert_yaxis()
    ax.set_aspect("auto")
    ax.set_yticks([0.5, 1.5, 2.5, Y_MARK0 + 0.5])
    ax.set_yticklabels(PROFILE_LABELS + ["End-to-end"])
    ax.set_xticks([i + 0.5 for i in range(n)])
    ax.set_xticklabels(
        [short_name(t) for t in targets],
        rotation=45, ha="right", rotation_mode="anchor")
    ax.tick_params(length=0, pad=1.8)
    ax.tick_params(axis="x", pad=XLBL_PAD_PT)
    for s in ax.spines.values():
        s.set_visible(False)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(t.get_window_extent(renderer).width
                     for t in ax.get_yticklabels()) / fig.bbox.width * W_MM

    content_mm = label_w_mm + GAP_LABEL_MM + MOSAIC_W_MM
    left0_mm = (W_MM - content_mm) / 2
    mosaic_left = (left0_mm + label_w_mm + GAP_LABEL_MM) / W_MM
    axes_h_mm = Y_LIM * UNIT_MM
    axes_bot_mm = (H_MM - TOP_MM - axes_h_mm)
    ax.set_position([mosaic_left, axes_bot_mm / H_MM,
                     MOSAIC_W_MM / W_MM, axes_h_mm / H_MM])

    counts = {"both": 0, "nav": 0, "rule": 0, "none": 0}
    for col, target in enumerate(targets):
        rec = records[target]
        cc = nav_cells(rec)
        ca = static_cells(rec)
        for row, profile in enumerate(PROFILES):
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
                                   facecolor=color, edgecolor="none"))

    # target-level navigation end-to-end marker row (underneath the
    # mosaic)
    n_e2e = 0
    for col, target in enumerate(targets):
        e2e_c = nav_e2e(records[target])
        n_e2e += e2e_c
        ax.add_patch(Rectangle((col + 0.12, Y_MARK0 + 0.28), 0.76, 0.44,
                               facecolor=(C_NAV if e2e_c else "white"),
                               edgecolor=(INK if e2e_c else C_OPEN),
                               linewidth=0.6))

    # cohort dividers (the inter-column gaps): seg3|seg4 at 12,
    # seg4|deployment at 20 — spanning mosaic + marker row
    for x_col in DIVIDER_COLS:
        if x_col < n:
            ax.plot([x_col, x_col], [-0.02, Y_LIM + 0.02],
                    color=C_OPEN, lw=0.6, zorder=4, clip_on=False)

    # ── key: two centred rows under the labels, renderer-measured widths
    #    under a canvas-overflow assert (the fig5c/fig4g house convention) ──
    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    SW_W, SW_H = 1.3 / W_MM, 1.3 / H_MM      # tile-outcome swatch (square)
    MK_W, MK_H = 2.2 / W_MM, 1.0 / H_MM      # e2e-marker swatch
    GAP_IN, GAP_OUT = 0.6 / W_MM, 1.7 / W_MM

    row1 = [("swatch", C_NAV), ("label", f"navigation-only ({counts['nav']})"),
            ("swatch", C_BOTH), ("label", f"both-pass ({counts['both']})"),
            ("swatch", C_RULE), ("label", f"static-only ({counts['rule']})"),
            ("swatch", C_NONE), ("label", f"both-fail ({counts['none']})")]
    row2 = ([("label", "End-to-end (navigation):"), ("gap", 1.0 / W_MM)]
            + [("mswatch", (C_NAV, INK)),
               ("label", f"all 3 profiles delivered ({n_e2e})"),
               ("mswatch", ("white", C_OPEN)),
               ("label", f"≥1 profile undelivered ({n - n_e2e})")])

    legend_texts = []
    for y_mm, row in ((LEG1_Y_MM, row1), (LEG2_Y_MM, row2)):
        widths = []
        for kind, val in row:
            if kind == "swatch":
                widths.append(SW_W + GAP_IN)
            elif kind == "mswatch":
                widths.append(MK_W + GAP_IN)
            elif kind == "gap":
                widths.append(val)
            else:
                widths.append(text_w(val) + GAP_OUT)
        total_w = sum(widths) - GAP_OUT
        assert total_w < 0.94, f"key row overflows canvas: {total_w:.3f}"
        x = 0.5 - total_w / 2
        y = y_mm / H_MM
        for (kind, val), w in zip(row, widths):
            if kind == "swatch":
                fig.patches.append(Rectangle(
                    (x, y + (0.45 - 0.65) / H_MM), SW_W, SW_H,
                    transform=fig.transFigure, facecolor=val, edgecolor="none"))
                x += w
            elif kind == "mswatch":
                face, edge = val
                fig.patches.append(Rectangle(
                    (x, y + (0.45 - 0.5) / H_MM), MK_W, MK_H,
                    transform=fig.transFigure, facecolor=face,
                    edgecolor=edge, linewidth=0.6))
                x += w
            elif kind == "gap":
                x += w
            else:
                legend_texts.append(fig.text(x, y, val, fontsize=FONT,
                                             color=INK, va="baseline"))
                x += w

    # ── programmatic guards: every text in-canvas; the left row labels
    #    clear of the mosaic and right-aligned; the frozen legend counts;
    #    rotated column labels clear of the key by pitch geometry (their
    #    axis-aligned boxes overlap by construction at a 6.2-mm pitch —
    #    adjacent 45° baselines stay pitch × sin 45° ≈ 4.4 mm apart,
    #    twice the 6-pt cap height, so only the global clearances are
    #    asserted) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    ylabels = list(ax.get_yticklabels())
    xlabels = list(ax.get_xticklabels())
    for t in ylabels + legend_texts + xlabels:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r}"
    yb = [t.get_window_extent(renderer) for t in ylabels]
    for i in range(len(yb)):
        for j in range(i + 1, len(yb)):
            assert not yb[i].overlaps(yb[j]), \
                f"row-label collision: {ylabels[i].get_text()!r} x {ylabels[j].get_text()!r}"
    lb = [t.get_window_extent(renderer) for t in legend_texts]
    for i in range(len(lb)):
        for j in range(i + 1, len(lb)):
            assert not lb[i].overlaps(lb[j]), \
                f"key collision: {legend_texts[i].get_text()!r} x {legend_texts[j].get_text()!r}"
    assert max(b.x1 for b in yb) < ax.bbox.x0, \
        "left row labels cross into the mosaic"
    right_edges = [b.x1 for b in yb]
    assert max(right_edges) - min(right_edges) <= 2, \
        "row labels not right-aligned on one edge"
    # "End-to-end" vertically centred on its marker row
    mark_centre_px = (ax.bbox.y0 + (1 - (Y_MARK0 + 0.5) / Y_LIM) * ax.bbox.height)
    e2e_bb = ylabels[3].get_window_extent(renderer)
    assert abs((e2e_bb.y0 + e2e_bb.y1) / 2 - mark_centre_px) <= ax.bbox.height * 0.06, \
        "End-to-end label off its marker-row centre"
    # rotated labels: lowest box clears key row 1, adjacent baselines
    # stay pitch × sin 45° apart
    key1_top = max(lb[i].y1 for i in range(4))  # row 1 labels come first
    x_bottom = min(t.get_window_extent(renderer).y0 for t in xlabels)
    # display y grows upward, so the labels clearing the key means their
    # lowest box edge sits above the key's highest box edge
    gap_mm = (x_bottom - key1_top) * H_MM / fig.bbox.height
    assert gap_mm >= 0.3, \
        f"rotated labels reach into the key (gap {gap_mm:.2f} mm)"
    pitch_mm = MOSAIC_W_MM / n
    assert pitch_mm * np.sin(np.deg2rad(45)) > 2.4, \
        "column pitch too tight for 45° labels (perpendicular gap < cap height)"

    assert counts == FROZEN_COUNTS, f"counts {counts} != frozen {FROZEN_COUNTS}"
    assert n_e2e == FROZEN_E2E, f"e2e {n_e2e} != frozen {FROZEN_E2E}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig5g_decisive_mosaic.{ext}", dpi=DPI)
    plt.close(fig)

    # ── raster QA: exact canvas, white outer border, and every colour
    #    either greyscale (pure-black text + antialiasing) or on a
    #    palette↔white / palette↔black blend segment ──
    img = mpimg.imread(OUT_DIR / "fig5g_decisive_mosaic.png")
    assert img.shape[1] == W_PX and img.shape[0] == H_PX, \
        f"canvas {img.shape[1]}x{img.shape[0]} != {W_PX}x{H_PX}"
    rgb = np.rint(img[..., :3] * 255).astype(np.int16)
    for side in (rgb[:2], rgb[-2:], rgb[:, :2], rgb[:, -2:]):
        assert (side >= 251).all(), "ink on the outer border"
    uni = np.unique(rgb.reshape(-1, 3), axis=0).astype(float)
    ok = ((uni.max(axis=1) - uni.min(axis=1)) <= 2) | (uni >= 251).all(axis=1)

    def on_segment(hex1: str, hex2: str, tol: float = 8.0) -> np.ndarray:
        p = np.array([int(hex1[i:i + 2], 16) for i in (1, 3, 5)])
        q = np.array([int(hex2[i:i + 2], 16) for i in (1, 3, 5)])
        d = (q - p).astype(float)
        t = np.clip(((uni - p) @ d) / (d @ d), 0.0, 1.0)
        return np.linalg.norm(uni - (p + t[:, None] * d), axis=1) <= tol

    for hexc in (C_NAV, C_BOTH, C_RULE, C_NONE, C_OPEN):
        ok |= on_segment(hexc, "#FFFFFF") | on_segment(hexc, "#000000")
    assert ok.all(), f"off-palette colours: {uni[~ok][:8].tolist()}"
    print(f"wrote fig5g_decisive_mosaic (n={n} targets; "
          f"nav {counts['nav']} / both {counts['both']} / "
          f"rule {counts['rule']} / none {counts['none']}; "
          f"end-to-end {n_e2e}/{n}; "
          f"raster QA green → {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
