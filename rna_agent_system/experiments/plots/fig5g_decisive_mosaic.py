"""Fig 5g — Aptamer delivery map: the 26 × 3 pair-outcome mosaic pooled over
every dual-arm target (Experiment 29 delivery-scarce + confirmation
segments + Experiment 40 deployment completion).

One tile per (target, profile) pair, coloured by the paired delivery
outcome of the two conditions — navigation-only (sage), both-pass (grey
blue), static-only (terracotta), both-fail (dark warm grey; the Fig. 5g
legend's class names).  A right-hand marker column carries the
target-level navigation end-to-end glyph (filled = navigation delivered a
passing candidate in all three length profiles).  Rows follow the segment
order — the 12 delivery-scarce targets (most delivery-scarce under the
segment-2 static condition — the pre-registered selection rule), the 8
confirmation complement, then the 6 deployment targets (Exp-30 form-entry
campaigns, static condition completed by Exp 40), with dividers between
cohorts; the three profile columns are headed Compact / Standard /
Extended (the aptamer length profiles 25–34 / 40–55 / 61–80 nt); the key
below carries the per-class pair counts and a second row explaining the
end-to-end glyph.

2026-10-03 figure-by-figure text sync (user-directed Fig. 5 batch): the
one-line context strip deleted (the key's class names self-decode the
tile colours and the dividers stay unlabelled — the strip carried the
retired "arm/cohort" wording); the key labels aligned to the legend's
class names — "navigation only" → "navigation-only", "both arms" →
"both-pass", "static grid only" → "static-only", "neither" → "both-fail";
no number, colour or geometry changed.

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
  end-to-end glyph; the open-marker outline moved off-palette #D9D9D9 →
  palette warm grey;
- canvas 89 × 80 → 89 × 71.2 mm (12 rows at the fig5c 4.35-mm row pitch).

2026-09-12 pooled re-render (user-directed merge): 12 → 26 rows (the seg4
confirmation complement + the six Exp-30 deployment targets appended below
labelled cohort dividers; the deployment navigation cells are the frozen
form-session records, the static grid is Exp 40's completion); canvas
89 × 71.2 → 89 × 132.2 mm (26 rows at the unchanged 4.35-mm row pitch).

Style (the fig5c carpet house style): no in-figure title (the panel letter
is added at assembly); every text element one 6-pt pure-black style;
colours exclusively from palette rev 7; absolute-mm geometry, single
column; 1200-dpi PNG + vector PDF (fonttype 42).  Programmatic guards:
every text in-canvas, pairwise text non-collision, header-baseline
equality, row-label/mosaic clearance, exact canvas pixels, raster palette
purity (greys + palette↔white/black blends only), white outer border.

Data  : experiments/results/exp29_aptamer_campaign_arc/
        {panels.json, seg3_decisive/runs.jsonl, seg4_confirmation/runs.jsonl}
        + experiments/results/exp40_static_completion/aptamer/runs.jsonl
Usage : python experiments/plots/fig5g_decisive_mosaic.py
Output : experiments/plots/output/fig5g_decisive_mosaic.{pdf,png}
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
W_MM, H_MM = 89.0, 132.2

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

# absolute-mm horizontal layout (the fig5c geometry)
GAP_LABEL_MM = 1.2    # row-label block → mosaic
MOSAIC_W_MM = 50.0
GAP_MID_MM = 3.5      # mosaic → marker column
MARK_W_MM = 4.5
# absolute-mm vertical layout
MOSAIC_BOT_MM = 12.5
MOSAIC_H_MM = 113.1   # 26 rows × 4.35 mm (the fig5c row pitch)
LEG1_Y_MM = 8.6       # key row 1 (tile outcomes) baseline
LEG2_Y_MM = 4.8       # key row 2 (end-to-end glyph) baseline


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

    # provisional mosaic axes — drawn once to measure the real row-label
    # widths, then repositioned so the whole content block is centred
    ax = fig.add_axes([0.3, MOSAIC_BOT_MM / H_MM, 0.5, MOSAIC_H_MM / H_MM])
    ax.set_xlim(0, 3)
    ax.set_ylim(0, n)
    ax.invert_yaxis()
    ax.set_aspect("auto")
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(PROFILE_LABELS)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks([i + 0.5 for i in range(n)])
    ax.set_yticklabels([short_name(t) for t in targets])
    ax.tick_params(length=0, pad=1.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="x", pad=2.2)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    label_w_mm = max(t.get_window_extent(renderer).width
                     for t in ax.get_yticklabels()) / fig.bbox.width * W_MM

    content_mm = (label_w_mm + GAP_LABEL_MM + MOSAIC_W_MM
                  + GAP_MID_MM + MARK_W_MM)
    left0_mm = (W_MM - content_mm) / 2
    mosaic_left = (left0_mm + label_w_mm + GAP_LABEL_MM) / W_MM
    mark_left = (left0_mm + label_w_mm + GAP_LABEL_MM
                 + MOSAIC_W_MM + GAP_MID_MM) / W_MM
    ax.set_position([mosaic_left, MOSAIC_BOT_MM / H_MM,
                     MOSAIC_W_MM / W_MM, MOSAIC_H_MM / H_MM])

    counts = {"both": 0, "nav": 0, "rule": 0, "none": 0}
    for row, target in enumerate(targets):
        rec = records[target]
        cc = nav_cells(rec)
        ca = static_cells(rec)
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
                                   facecolor=color, edgecolor="none"))

    # target-level navigation end-to-end marker column (right) — own y
    # axis, no sharing (a shared axis's set_yticks([]) would wipe the row
    # labels)
    axg = fig.add_axes([mark_left, MOSAIC_BOT_MM / H_MM,
                        MARK_W_MM / W_MM, MOSAIC_H_MM / H_MM])
    axg.set_xlim(0, 1)
    axg.set_ylim(0, n)
    axg.invert_yaxis()
    n_e2e = 0
    for row, target in enumerate(targets):
        e2e_c = nav_e2e(records[target])
        n_e2e += e2e_c
        axg.add_patch(Rectangle((0.12, row + 0.28), 0.76, 0.44,
                                facecolor=(C_NAV if e2e_c else "white"),
                                edgecolor=(INK if e2e_c else C_OPEN),
                                linewidth=0.6))
    axg.set_xticks([])
    axg.set_yticks([])
    for s in axg.spines.values():
        s.set_visible(False)

    # cohort dividers (the inter-row gaps): seg3|seg4 at 12, seg4|deployment
    # at 20 — spanning mosaic + marker column
    for y_row in (12, 20):
        if y_row < n:
            ax.plot([-0.02, 3.02], [y_row, y_row],
                    color=C_OPEN, lw=0.6, zorder=4, clip_on=False)
            axg.plot([-0.06, 1.06], [y_row, y_row],
                     color=C_OPEN, lw=0.6, zorder=4, clip_on=False)

    # ── headers: "End-to-end" as a fourth column header on the same
    #    baseline as the three profile headers (measured, not a floating
    #    title) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    hdr_bb = ax.get_xticklabels()[1].get_window_extent(renderer)  # Standard
    e2e_hdr = fig.text(mark_left + 0.5 * MARK_W_MM / W_MM,
                       hdr_bb.y0 / fig.bbox.height, "End-to-end",
                       ha="center", va="bottom", fontsize=FONT, color=INK)

    # ── key: two centred rows under the mosaic, renderer-measured widths
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

    # ── programmatic guards: every text in-canvas and pairwise
    #    non-colliding, header baselines equal, row labels clear of the
    #    mosaic (the fig5c/fig5b/fig4e house assertions) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = ([e2e_hdr] + legend_texts
             + list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
    boxes = []
    for t in texts:
        bb = t.get_window_extent(renderer)
        assert (bb.x0 >= 0 and bb.y0 >= 0
                and bb.x1 <= fig.bbox.width and bb.y1 <= fig.bbox.height), \
            f"text outside canvas: {t.get_text()!r}"
        boxes.append(bb)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].overlaps(boxes[j]), \
                f"text collision: {texts[i].get_text()!r} x {texts[j].get_text()!r}"
    assert abs(boxes[0].y0 - ax.get_xticklabels()[1]
               .get_window_extent(renderer).y0) <= 2, \
        "End-to-end header off the profile-header baseline"
    assert max(b.x1 for b in boxes[-n:]) < ax.bbox.x0, \
        "row labels cross into the mosaic"

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
