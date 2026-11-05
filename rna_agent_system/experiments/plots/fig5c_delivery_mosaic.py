"""Fig 5c — GenNav mRNA delivery map: the 25 × 3 pair-outcome mosaic
(Experiment 28 registered 20-target cohort + Experiment 40 deployment
completion — the pooled 25-target analysis).

One tile per (target, profile) pair, coloured by the paired delivery
outcome of the two conditions — navigation-only (sage), both-pass (grey
blue), static-only (terracotta), both-fail (dark warm grey; the Fig. 5c
legend's class names).  A marker row underneath the mosaic carries the
target-level navigation end-to-end glyph (filled = navigation delivered a
passing batch in all three profiles — the primary endpoint's c_e2e_gene
term).  Columns follow the registered target order (alphabetical) with
the five deployment targets (Exp-30 form-entry campaigns, static arm
completed by Exp 40) right of a divider; the three profile rows are
labelled Expression / Stability / Balanced down the left edge; the key
below carries the per-class pair counts and a second row explaining the
end-to-end glyph.

2026-10-10 transposed re-render (user-directed Fig. 5 composite-length
batch): the mosaic transposed to a full-width, short panel — targets on
the x axis (25 columns, 45°-rotated labels — the fig3a house idiom),
profiles on the y axis, the end-to-end marker column becoming a marker
row (the legend's "end-to-end column" wording became "end-to-end row" in
the same batch); canvas 89 × 127.8 → 183 × 50 mm so the panel takes a
full composite row at a third of its former height.  One shared axes
now carries the three profile rows and the marker row (uniform 4.6-mm
unit row pitch, a 0.3-unit gap band between mosaic and marker row), so
all four left row labels align on one right edge by construction.  No
number, colour or class assignment changed; every tile, divider, glyph
and key item is the same information re-oriented.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch): the
one-line context strip deleted (the key's class names now self-decode the
tile colours — "Tile colour marks the delivering arm(s)" carried the
retired "arm" wording); the key labels aligned to the legend's class
names — "navigation only" → "navigation-only", "both arms" → "both-pass",
"rule only" → "static-only", "neither" → "both-fail"; the fourth column
header and the key's glyph row decoded "Gene e2e" → "End-to-end" (the
legend's term, the fig5g convention); no number, colour or geometry
changed.

2026-09-08 figure-repair pass (user direction):
- row labels (gene names) restored — the marker-column axes previously
  shared y with the mosaic and its set_yticks([]) call wiped the shared
  y-axis ticks, deleting every row label from the rendered canvas;
- "Gene e2e" is no longer a floating two-line axes title (its first line
  sat a full line above the profile headers); it is now a single-line
  column header on the same baseline as Expression / Stability / Balanced;
- margins rebalanced — the content block (row labels + mosaic + marker
  column) is horizontally centred, tiles widened 11.5 → 14.7 mm;
- the key gains per-class cell counts and a second row explaining the
  e2e glyph; the open-marker outline moved off-palette #D9D9D9 → palette
  warm grey;
- canvas 89 × 118 → 89 × 106 mm.

2026-09-12 pooled re-render (user-directed merge): 20 → 25 rows (the five
Exp-30 deployment targets appended below a labelled divider line; their
navigation cells are the frozen form-session traces evaluated by Exp 40
under the identical full-length stack); canvas 89 × 106 → 89 × 127.8 mm
(25 rows at the unchanged 4.35-mm row pitch).

2026-10-02 legend-sync re-render (figure-backlog batch): the deployment
asterisks removed — the row-label "*"-suffix and the context strip's
"* marks the five deployment targets" clause lost their legend referent
when the cohort disclosure retired to the Methods and frozen records (the
2026-10-02 legend batches); the cohort divider line stays (the columns
still group registered 20 left, deployment 5 right).  No number, colour
or geometry changed.

Style (the fig4d/fig4g carpet house style): no in-figure title (the panel
letter is added at assembly); every text element one 6-pt pure-black
style; colours exclusively from palette rev 7; absolute-mm geometry,
double column; 1200-dpi PNG + vector PDF (fonttype 42).  Programmatic
guards: every text in-canvas, pairwise text non-collision (rotated
column labels checked by the pitch-clearance and key-clearance asserts —
their axis-aligned boxes overlap by construction at a 6.5-mm pitch while
the labels themselves stay 4.6 mm apart perpendicular), left row labels
clear of the mosaic, exact canvas pixels, the frozen legend counts, raster
palette purity (greys + palette↔white/black blends only), white outer
border.

Data  : experiments/results/exp28_gennav_mrna_endpoint_v2/full/runs.jsonl
        + experiments/results/exp40_static_completion/mrna/runs.jsonl
        + experiments/results/exp40_static_completion/pooled/
          mrna_pooled_verdict.json
Usage : python experiments/plots/fig5c_delivery_mosaic.py
Output : experiments/plots/output/fig5c_delivery_mosaic.{pdf,png}

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
RUNS_E28 = (PROJECT_ROOT / "experiments" / "results"
            / "exp28_gennav_mrna_endpoint_v2" / "full" / "runs.jsonl")
RUNS_E40 = (PROJECT_ROOT / "experiments" / "results"
            / "exp40_static_completion" / "mrna" / "runs.jsonl")
POOLED = (PROJECT_ROOT / "experiments" / "results"
          / "exp40_static_completion" / "pooled" / "mrna_pooled_verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 183.0, 50.0

C_BOTH = PALETTE_BY_NAME["grey_blue"]       # both-pass
C_NAV = PALETTE_BY_NAME["sage_green"]       # navigation-only
C_RULE = PALETTE_BY_NAME["terracotta"]      # static-only
C_NONE = PALETTE_BY_NAME["dark_warm_grey"]  # both-fail
C_OPEN = PALETTE_BY_NAME["warm_grey"]       # open e2e-marker outline

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
PROFILES = ["expression", "stability", "balanced"]
PROFILE_LABELS = ["Expression", "Stability", "Balanced"]

# absolute-mm horizontal layout (transposed: one target per column)
MOSAIC_W_MM = 162.0     # 25 columns ≈ 6.5 mm each
GAP_LABEL_MM = 1.2      # left row-label block → mosaic
# absolute-mm vertical layout (data units are 4.6 mm each; y grows down)
UNIT_MM = 4.6
Y_MARK0 = 3.3           # marker row band [3.3, 4.3); gap band [3.0, 3.3)
Y_LIM = 4.3
LEG1_Y_MM = 7.8         # key row 1 (tile outcomes) baseline
LEG2_Y_MM = 3.9         # key row 2 (end-to-end glyph) baseline
TOP_MM = 1.3            # white above the mosaic
XLBL_PAD_PT = 2.8       # mosaic bottom → rotated-label anchors

N_REGISTERED = 20
# the legend's frozen counts (Fig. 5c legend, verbatim)
FROZEN_COUNTS = {"nav": 20, "both": 26, "rule": 6, "none": 23}
FROZEN_E2E = 12


def main() -> int:
    records = {}
    for path in (RUNS_E28, RUNS_E40):
        for ln in path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                if rec.get("success") and rec["target_id"] not in records:
                    records[rec["target_id"]] = rec
    verdict = json.loads(POOLED.read_text(encoding="utf-8"))
    targets = [t for t in FULL_TARGET_ORDER if t in records]

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
        jc = {p["profile"]: p["JCD"] for p in rec["evaluations"]["C"]["profiles"]}
        ja = {p["profile"]: p["JCD"] for p in rec["evaluations"]["A"]["profiles"]}
        for row, profile in enumerate(PROFILES):
            c_pass = jc.get(profile, False)
            a_pass = ja.get(profile, False)
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

    # gene-level navigation end-to-end marker row (underneath the mosaic)
    n_e2e = 0
    for col, target in enumerate(targets):
        rec = records[target]
        e2e_all = all(p["e2e_pass"] for p in rec["evaluations"]["C"]["profiles"])
        n_e2e += e2e_all
        ax.add_patch(Rectangle((col + 0.12, Y_MARK0 + 0.28), 0.76, 0.44,
                               facecolor=(C_NAV if e2e_all else "white"),
                               edgecolor=(INK if e2e_all else C_OPEN),
                               linewidth=0.6))

    # cohort divider between the registered 20 and the deployment 5 (the
    # inter-column gap: registered tiles end at 19.94, deployment start
    # 20.06) — spanning mosaic + marker row
    if n > N_REGISTERED:
        ax.plot([N_REGISTERED, N_REGISTERED], [-0.02, Y_LIM + 0.02],
                color=C_OPEN, lw=0.6, zorder=4, clip_on=False)

    # ── key: two centred rows under the labels, renderer-measured widths
    #    under a canvas-overflow assert (the fig4g house convention) ──
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
    #    axis-aligned boxes overlap by construction at a 6.5-mm pitch —
    #    adjacent 45° baselines stay pitch × sin 45° ≈ 4.6 mm apart,
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
        fig.savefig(OUT_DIR / f"fig5c_delivery_mosaic.{ext}", dpi=DPI)
    plt.close(fig)

    # ── raster QA: exact canvas, white outer border, and every colour
    #    either greyscale (pure-black text + antialiasing) or on a
    #    palette↔white / palette↔black blend segment ──
    img = mpimg.imread(OUT_DIR / "fig5c_delivery_mosaic.png")
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
    print(f"wrote fig5c_delivery_mosaic (n={n}; "
          f"nav {counts['nav']} / both {counts['both']} / "
          f"rule {counts['rule']} / none {counts['none']}; "
          f"gene e2e {n_e2e}/{n}; "
          f"c_e2e_gene={verdict['c_e2e_gene']:.3f}; "
          f"raster QA green → {W_PX}x{H_PX} px @ {DPI} dpi)")
    return 0


FULL_TARGET_ORDER = [
    "A1AT", "Albumin", "Beta_galactosidase", "EPO", "GFP",
    "Growth_hormone", "HER2", "HIV-1_Env_gp120", "HPV16_L1", "IFN_alpha_2a",
    "IL-2", "Influenza_HA_H1N1", "Insulin", "Luciferase", "OTC",
    "Ovalbumin", "PDGFB", "RSV_F_protein", "SARS-CoV-2_Spike_WT",
    "Transferrin",
    # deployment cohort (Exp-30 form entry; static arm completed by Exp 40)
    "CSF3", "LEP", "PLAT", "PTH", "THPO",
]

_SHORT = {
    "Beta_galactosidase": "β-galactosidase",
    "HIV-1_Env_gp120": "HIV-1 gp120",
    "HPV16_L1": "HPV16 L1",
    "IFN_alpha_2a": "IFN-α2a",
    "IL-2": "IL-2",
    "Influenza_HA_H1N1": "Influenza HA",
    "SARS-CoV-2_Spike_WT": "SARS-CoV-2 spike",
    "RSV_F_protein": "RSV F",
    "Growth_hormone": "Growth hormone",
}


def short_name(t: str) -> str:
    return _SHORT.get(t, t)


if __name__ == "__main__":
    raise SystemExit(main())
