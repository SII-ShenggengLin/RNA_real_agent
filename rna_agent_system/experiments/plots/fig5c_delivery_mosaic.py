"""Fig 5c — GenNav mRNA delivery map: the 20 × 3 pair-outcome mosaic
(Experiment 28, paper registry E6).

One tile per (target, profile) cell, coloured by the paired JCD outcome of
the two arms — navigation-only pass (sage), both arms pass (grey blue),
rule-only pass (terracotta), neither passes (dark warm grey).  A right-hand
marker column carries the gene-level navigation end-to-end delivery glyph
(filled = navigation delivered a passing batch in all three profiles — the
primary endpoint's c_e2e_gene term).  Rows follow the registered target
order (alphabetical); the three profile columns are headed Expression /
Stability / Balanced; a one-line context strip above the panel states the
tile semantics; the key below carries the per-class cell counts and a
second row explaining the gene-e2e glyph.

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

Style (the fig4d/fig4g carpet house style): no in-figure title (the panel
letter is added at assembly); every text element one 6-pt pure-black
style; colours exclusively from palette rev 7; absolute-mm geometry,
single column; 1200-dpi PNG + vector PDF (fonttype 42).  Programmatic
guards: every text in-canvas, pairwise text non-collision, header-baseline
equality, row-label/mosaic clearance, exact canvas pixels, raster palette
purity (greys + palette↔white/black blends only), white outer border.

Data  : experiments/results/exp28_gennav_mrna_endpoint_v2/full/
        {runs.jsonl, verdict.json}
Usage : python experiments/plots/fig5c_delivery_mosaic.py
Output : experiments/plots/output/fig5c_delivery_mosaic.{pdf,png}
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
RUNS = (PROJECT_ROOT / "experiments" / "results"
        / "exp28_gennav_mrna_endpoint_v2" / "full" / "runs.jsonl")
VERDICT = (PROJECT_ROOT / "experiments" / "results"
           / "exp28_gennav_mrna_endpoint_v2" / "full" / "verdict.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6
W_MM, H_MM = 89.0, 106.0

C_BOTH = PALETTE_BY_NAME["grey_blue"]       # both arms pass
C_NAV = PALETTE_BY_NAME["sage_green"]       # navigation-only pass
C_RULE = PALETTE_BY_NAME["terracotta"]      # rule-only pass
C_NONE = PALETTE_BY_NAME["dark_warm_grey"]  # neither passes
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

# absolute-mm horizontal layout
GAP_LABEL_MM = 1.2    # row-label block → mosaic
MOSAIC_W_MM = 50.0
GAP_MID_MM = 3.5      # mosaic → marker column
MARK_W_MM = 4.5
# absolute-mm vertical layout
MOSAIC_BOT_MM = 12.5
MOSAIC_H_MM = 87.0
LEG1_Y_MM = 8.6       # key row 1 (tile outcomes) baseline
LEG2_Y_MM = 4.8       # key row 2 (gene-e2e glyph) baseline

CONTEXT = ("One tile per gene × constraint-profile cell — "
           "colour marks the delivering arm(s)")


def main() -> int:
    records = [json.loads(ln) for ln in RUNS.read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    records = {r["target_id"]: r for r in records if r.get("success")}
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    targets = [t for t in FULL_TARGET_ORDER if t in records]

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
        jc = {p["profile"]: p["JCD"] for p in rec["evaluations"]["C"]["profiles"]}
        ja = {p["profile"]: p["JCD"] for p in rec["evaluations"]["A"]["profiles"]}
        for col, profile in enumerate(PROFILES):
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

    # gene-level navigation e2e marker column (right) — own y axis, no
    # sharing (a shared axis's set_yticks([]) would wipe the row labels)
    axg = fig.add_axes([mark_left, MOSAIC_BOT_MM / H_MM,
                        MARK_W_MM / W_MM, MOSAIC_H_MM / H_MM])
    axg.set_xlim(0, 1)
    axg.set_ylim(0, n)
    axg.invert_yaxis()
    n_e2e = 0
    for row, target in enumerate(targets):
        rec = records[target]
        e2e_all = all(p["e2e_pass"] for p in rec["evaluations"]["C"]["profiles"])
        n_e2e += e2e_all
        axg.add_patch(Rectangle((0.12, row + 0.28), 0.76, 0.44,
                                facecolor=(C_NAV if e2e_all else "white"),
                                edgecolor=(INK if e2e_all else C_OPEN),
                                linewidth=0.6))
    axg.set_xticks([])
    axg.set_yticks([])
    for s in axg.spines.values():
        s.set_visible(False)

    # ── headers: "Gene e2e" as a fourth column header on the same baseline
    #    as the three profile headers (measured, not a floating title) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    hdr_bb = ax.get_xticklabels()[1].get_window_extent(renderer)  # Stability
    e2e_hdr = fig.text(mark_left + 0.5 * MARK_W_MM / W_MM,
                       hdr_bb.y0 / fig.bbox.height, "Gene e2e",
                       ha="center", va="bottom", fontsize=FONT, color=INK)
    ctx = fig.text(0.5, hdr_bb.y1 / fig.bbox.height + 1.4 / H_MM, CONTEXT,
                   ha="center", va="bottom", fontsize=FONT, color=INK)

    # ── key: two centred rows under the mosaic, renderer-measured widths
    #    under a canvas-overflow assert (the fig4g house convention) ──
    def text_w(s: str) -> float:
        t = fig.text(0, 0, s, fontsize=FONT)
        w = t.get_window_extent(renderer).width / fig.bbox.width
        t.remove()
        return w

    SW_W, SW_H = 1.3 / W_MM, 1.3 / H_MM      # tile-outcome swatch (square)
    MK_W, MK_H = 2.2 / W_MM, 1.0 / H_MM      # e2e-marker swatch
    GAP_IN, GAP_OUT = 0.6 / W_MM, 1.7 / W_MM

    row1 = [("swatch", C_NAV), ("label", f"navigation only ({counts['nav']})"),
            ("swatch", C_BOTH), ("label", f"both arms ({counts['both']})"),
            ("swatch", C_RULE), ("label", f"rule only ({counts['rule']})"),
            ("swatch", C_NONE), ("label", f"neither ({counts['none']})")]
    row2 = ([("label", "Gene e2e (navigation):"), ("gap", 1.0 / W_MM)]
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
    #    mosaic (the fig5b/fig4e house assertions) ──
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = ([ctx, e2e_hdr] + legend_texts
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
    assert abs(boxes[1].y0 - ax.get_xticklabels()[1]
               .get_window_extent(renderer).y0) <= 2, \
        "Gene e2e header off the profile-header baseline"
    assert max(b.x1 for b in boxes[-n:]) < ax.bbox.x0, \
        "row labels cross into the mosaic"

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
