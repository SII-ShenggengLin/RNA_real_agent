"""Fig 4h — per-campaign LLM usage, bubble strip (Exp 25 companion panel).

Campaigns re-run to date as rows; one bubble per executed unit (suite task,
task×arm run, decision-matrix cell or PA session — the right-hand annotation
names each campaign's own unit) placed at its index within the campaign;
bubble AREA encodes the measured successful LLM calls consumed by that unit.
The failure-injected arm's errored attempts are annotated, not bubbled —
they consume no model output. The reset re-runs of the navigation campaigns
(Exp 27/28/29, deterministic zero-LLM) and the production-entry navigation
and case-study runs (Exp 30/37, quality review on) joined the strip on
2026-09-09, retiring the earlier exclusion note.

Bubble style borrows the BioMedAgent Fig. 3e bubble-strip convention.
Encodings: bubble area = LLM calls per unit (sqrt radius scale); colour =
campaign, decorative and redundant with the row labels — the three Exp 25
arms share the blue-grey family and the injected-outage arm takes the
reserved dark warm grey (zero successful calls, 144 failed attempts). The
size key draws every size class in five of the row colours side by side —
colour is decorative in this panel (rows are identified by their text
labels), and repeating the colour sampler per size makes the colour ⊥ size
independence explicit; the numbers under each group carry the scale.

Style (Nature conventions, the fig3/fig4 house style): no in-figure panel
title — the panel letter and description live in the composite/caption; the
only axis is the bottom task-order axis with its label centred beneath it;
every text element one 6-pt pure-black style; colours only from palette
rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm geometry; exact
canvas (no tight crop); renderer-measured label widths inside a
canvas-overflow assert.

Data  : experiments/results/exp25_quality_review_advisory/fig4h_llm_usage.json
Usage : python experiments/plots/fig4h_llm_usage_bubble.py
Output : experiments/plots/output/fig4h_llm_usage_bubble.{pdf,png}
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA = (PROJECT_ROOT / "experiments" / "results" / "exp25_quality_review_advisory"
        / "fig4h_llm_usage.json")
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

# campaign key → (row label, unit noun, row colour). Colours are decorative
# per-campaign accents, redundant with the row labels; dash-only zero-call
# rows get mid tones, the three Exp 25 arms share the blue-grey family, and
# the injected-outage arm takes the reserved dark warm grey.
ROWS = {
    "exp5_ungated_control": ("Ungated (Exp 5)", "tasks", PALETTE_BY_NAME["dusty_mauve_pink"]),
    "exp17_gated": ("Gated (Exp 17)", "tasks", PALETTE_BY_NAME["terracotta"]),
    "exp18_mrna_dual_arm": ("mRNA dual-arm (Exp 18)", "runs", PALETTE_BY_NAME["khaki"]),
    "exp23_selective_gating": ("Decision matrix (Exp 23)", "cells", PALETTE_BY_NAME["mauve_grey"]),
    "exp24_production_campaign": ("Production (Exp 24)", "runs", PALETTE_BY_NAME["sage_green"]),
    "exp25_quality_off": ("Review off (Exp 25)", "sessions", PALETTE_BY_NAME["grey_blue"]),
    "exp25_quality_on": ("Review on (Exp 25)", "sessions", PALETTE_BY_NAME["slate_blue"]),
    "exp25_quality_fail": ("Review outage (Exp 25)", "sessions", PALETTE_BY_NAME["dark_warm_grey"]),
    "exp27_gennav_mrna_boundary": ("GenNav mRNA boundary (Exp 27)", "targets", PALETTE_BY_NAME["grey_green"]),
    "exp28_gennav_mrna_endpoint": ("GenNav mRNA endpoint (Exp 28)", "targets", PALETTE_BY_NAME["warm_grey"]),
    "exp29_aptamer_arc": ("GenNav aptamer arc (Exp 29)", "campaigns", PALETTE_BY_NAME["pale_dusty_rose"]),
    "exp29_expanded_sweep": ("Aptamer budget sweep (Exp 29)", "campaigns", PALETTE_BY_NAME["sand"]),
    "exp30_production_navigation": ("Production navigation (Exp 30)", "sessions", PALETTE_BY_NAME["grey_blue"]),
    "exp37_case_studies": ("Case studies (Exp 37)", "cases", PALETTE_BY_NAME["slate_blue"]),
}
ROW_ORDER = list(ROWS)
# Size-key colour sampler: five of the row colours, shown for every size
# class — colour is decorative in this panel, and repeating the sampler per
# size keeps the key semantically neutral (no colour → size reading).
KEY_SET = [PALETTE_BY_NAME[n] for n in
           ("dusty_mauve_pink", "terracotta", "mauve_grey", "sage_green", "slate_blue")]
AXIS_LABEL = "Task index"
KEY_TAIL = "LLM calls"

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


def text_w_mm(fig, s: str) -> float:
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, s, fontsize=FONT, color=INK)
    bb = probe.get_window_extent(r)
    probe.remove()
    return bb.width / fig.dpi * 25.4


def bubble_r(calls: float) -> float:
    """Area-proportional radius in mm; zero renders as a short dash."""
    if calls <= 0:
        return 0.30
    return min(1.9, 0.75 * math.sqrt(calls))


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    by_key = {c["campaign"]: c for c in payload["campaigns"]}
    campaigns = [by_key[k] for k in ROW_ORDER if k in by_key]
    assert campaigns, f"no campaigns found in {DATA}"

    def annotation(c) -> str:
        _, unit, _ = ROWS[c["campaign"]]
        ann = f"{c['n_tasks']} {unit} · {c['mean_llm_calls_per_task']:.1f} calls/{unit[:-1]}"
        failed = c.get("failed_review_attempts")
        if failed:
            ann += f" · {failed} failed"
        return ann

    anns = {c["campaign"]: annotation(c) for c in campaigns}

    probe = plt.figure(figsize=(4, 4))
    label_w = max(text_w_mm(probe, ROWS[c["campaign"]][0]) for c in campaigns)
    ann_w = max(text_w_mm(probe, s) for s in anns.values())
    plt.close(probe)

    ML = 1.2
    GAP_L = 2.6          # labels → strip
    strip_w = 48.0       # mm of task-order axis
    GAP_R = 2.6          # strip → annotations
    strip_x0 = ML + label_w + GAP_L
    strip_x1 = strip_x0 + strip_w
    ann_x = strip_x1 + GAP_R
    fig_w = ann_x + ann_w + ML

    row_h, row_gap = 4.2, 2.4
    pitch = row_h + row_gap
    rows_y = [1.4 + row_h / 2 + i * pitch for i in range(len(campaigns))]
    axis_y = rows_y[-1] + row_h / 2 + 2.4          # bottom task-order axis
    axis_lab_y = axis_y + 2.5
    key_y = axis_lab_y + 1.05 + 1.2 + 1.9          # axis label → key markers (max radius)
    num_y = key_y + 1.9 + 1.3                      # key markers → size numbers
    fig_h = num_y + 0.9 + 1.2

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")

    for c, cy in zip(campaigns, rows_y):
        label, _, color = ROWS[c["campaign"]]
        n = c["n_tasks"]
        ax.text(ML, cy, label, ha="left", va="center", color=INK)
        for i, calls in enumerate(c["per_task_llm_calls"]):
            x = strip_x0 + (i + 0.5) / n * strip_w
            if calls <= 0:
                # zero-call unit: a short dash — "unit present, zero calls"
                # (hollow dots at this scale read as placeholder data points)
                ax.plot([x - 0.45, x + 0.45], [cy, cy], color=color, lw=0.5,
                        solid_capstyle="butt")
            else:
                ax.add_patch(Circle((x, cy), bubble_r(calls),
                                    facecolor=color, edgecolor="none"))
        ax.text(ann_x, cy, anns[c["campaign"]], ha="left", va="center", color=INK)

    # bottom task-order axis (no ticks — n differs per row)
    ax.plot([strip_x0, strip_x1], [axis_y, axis_y], color=INK, lw=0.5)
    ax.text((strip_x0 + strip_x1) / 2, axis_lab_y, AXIS_LABEL,
            ha="center", va="center", color=INK)

    # centred size key (the fig4c convention: legend attached under the panel).
    # Every size class is a group of five markers — one per key colour — with
    # its number centred beneath the group, so the key cannot be read as
    # colour → size; per-marker spacing is radius-aware.
    key_vals = (0, 1, 2, 4, 8)
    marker_w = {v: (1.0 if v == 0 else 2 * bubble_r(v)) for v in key_vals}
    G1, G2, GAP_T = 0.4, 2.5, 2.8   # intra-group, group→group, last group→tail
    group_w = {v: len(KEY_SET) * marker_w[v] + (len(KEY_SET) - 1) * G1 for v in key_vals}
    key_w = (sum(group_w.values()) + G2 * (len(key_vals) - 1)
             + GAP_T + text_w_mm(fig, KEY_TAIL))
    x = max(ML, (fig_w - key_w) / 2)   # centred on the full panel width
    for v in key_vals:
        w = marker_w[v]
        for j, kcolor in enumerate(KEY_SET):
            mx = x + j * (w + G1)
            if v == 0:
                ax.plot([mx, mx + w], [key_y, key_y], color=kcolor, lw=0.5,
                        solid_capstyle="butt")
            else:
                ax.add_patch(Circle((mx + w / 2, key_y), w / 2,
                                    facecolor=kcolor, edgecolor="none"))
        ax.text(x + group_w[v] / 2, num_y, str(v), ha="center", va="center", color=INK)
        x += group_w[v] + (GAP_T if v == key_vals[-1] else G2)
    ax.text(x, num_y, KEY_TAIL, ha="left", va="center", color=INK)

    # canvas-overflow assert (renderer-measured, the fig4b convention)
    r_ = fig.canvas.get_renderer()
    for t in ax.texts:
        bb = t.get_window_extent(r_)
        assert bb.x0 >= -0.5 and bb.x1 <= fig.bbox.x1 + 0.5, f"text overflows: {t.get_text()!r}"
        assert bb.y0 >= -0.5 and bb.y1 <= fig.bbox.y1 + 0.5, f"text overflows: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4h_llm_usage_bubble.{ext}", dpi=1200)
    plt.close(fig)

    # raster QA: exact canvas, no ink on the outer border
    from PIL import Image
    im = Image.open(OUT_DIR / "fig4h_llm_usage_bubble.png")
    assert abs(im.width / 1200 * 25.4 - fig_w) < 0.05 and abs(im.height / 1200 * 25.4 - fig_h) < 0.05, \
        f"canvas mismatch: {im.size} vs {fig_w:.1f}×{fig_h:.1f} mm"
    px = im.convert("L")
    w, h = px.size
    for edge in (px.crop((0, 0, w, 1)), px.crop((0, h - 1, w, h)),
                 px.crop((0, 0, 1, h)), px.crop((w - 1, 0, w, h))):
        assert edge.getextrema()[0] == 255, "ink at the outer border"
    print(f"[fig4h] {fig_w:.1f} × {fig_h:.1f} mm, {len(campaigns)} campaign rows — "
          f"raster QA green → {OUT_DIR / 'fig4h_llm_usage_bubble.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
