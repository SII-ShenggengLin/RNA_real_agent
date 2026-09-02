"""Fig 4h — per-campaign LLM usage, bubble strip (Exp 25 companion panel).

Campaigns re-run to date as rows; one bubble per task (suite task, PA session
or decision-matrix cell) placed at its index within the campaign; bubble
AREA encodes the measured LLM calls consumed by that task (successful calls;
the failure-injected arm's errored attempts are annotated, not bubbled —
they consume no model output). Right-hand annotations give n and the mean
calls per task. The registered exclusion (Fig-5 GenNav navigation campaigns,
not yet re-run under the reset) is stated in the caption, not the panel.

Bubble style borrows the BioMedAgent Fig. 3e bubble-strip convention; data
encodings: size = calls per task (area-proportional, sqrt radius scale),
colour = grey blue for every campaign (the size channel carries the data —
one encoding, one colour, the fig3f single-channel convention).

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles;
every text element one 6-pt pure-black style; colours only from palette
rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm geometry; exact
canvas (no tight crop); renderer-measured label widths inside a canvas-
overflow assert.

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
BUBBLE_COLOR = PALETTE_BY_NAME["grey_blue"]

ROW_LABELS = {
    "exp5_ungated_control": "Ungated control (Exp 5)",
    "exp17_gated": "Gated treatment (Exp 17)",
    "exp18_mrna_dual_arm": "mRNA dual arm (Exp 18)",
    "exp23_selective_gating": "Decision matrix (Exp 23)",
    "exp24_production_campaign": "Production campaign (Exp 24)",
    "exp25_quality_off": "Quality review off (Exp 25)",
    "exp25_quality_on": "Quality review on (Exp 25)",
    "exp25_quality_fail": "Review on, outage (Exp 25)",
}
ROW_ORDER = list(ROW_LABELS)

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
    """Area-proportional radius in mm; zero renders as a minimal open dot."""
    if calls <= 0:
        return 0.30
    return min(1.9, 0.75 * math.sqrt(calls))


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    by_key = {c["campaign"]: c for c in payload["campaigns"]}
    campaigns = [by_key[k] for k in ROW_ORDER if k in by_key]
    assert campaigns, f"no campaigns found in {DATA}"

    probe = plt.figure(figsize=(4, 4))
    label_w = max(text_w_mm(probe, ROW_LABELS[c["campaign"]]) for c in campaigns)
    ann_examples = ["n = 241 · 2.0 calls/task", "n = 31 · 0.0 (attempts: 144 failed)"]
    ann_w = max(text_w_mm(probe, s) for s in ann_examples)
    key_labels = ["0", "1", "2", "4", "8", "calls per task"]
    key_w = sum(text_w_mm(probe, s) for s in key_labels) + 5 * 4.6 + 6 * 1.4
    plt.close(probe)

    ML = 1.2
    GAP_L = 2.6          # labels → strip
    strip_w = 52.0       # mm of task axis
    GAP_R = 2.6          # strip → annotations
    strip_x0 = ML + label_w + GAP_L
    strip_x1 = strip_x0 + strip_w
    ann_x = strip_x1 + GAP_R
    fig_w = max(ann_x + ann_w + ML, ML + key_w + ML)

    row_h, row_gap = 4.2, 2.4
    pitch = row_h + row_gap
    axis_y = 6.5          # x-axis line
    rows_y = [axis_y + 2.0 + i * pitch for i in range(len(campaigns))]
    fig_h = rows_y[-1] + row_h / 2 + 5.2

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")

    # x-axis: task index within campaign (no ticks — n differs per row)
    ax.plot([strip_x0, strip_x1], [axis_y, axis_y], color=INK, lw=0.5)
    ax.text((strip_x0 + strip_x1) / 2, axis_y - 1.8, "Tasks within the campaign →",
            ha="center", va="center")

    for c, cy in zip(campaigns, rows_y):
        n = c["n_tasks"]
        per = c["per_task_llm_calls"]
        ax.text(ML, cy, ROW_LABELS[c["campaign"]], ha="left", va="center")
        for i, calls in enumerate(per):
            x = strip_x0 + (i + 0.5) / n * strip_w
            if calls <= 0:
                # zero-call task: a short dash — "task present, zero calls"
                # (hollow dots at this scale read as placeholder data points)
                ax.plot([x - 0.45, x + 0.45], [cy, cy], color=BUBBLE_COLOR, lw=0.5,
                        solid_capstyle="butt")
            else:
                ax.add_patch(Circle((x, cy), bubble_r(calls),
                                    facecolor=BUBBLE_COLOR, edgecolor="none"))
        mean = c["mean_llm_calls_per_task"]
        unit = "runs" if c["campaign"] == "exp24_production_campaign" else "tasks"
        ann = f"n = {n} {unit} · {mean:.1f} calls/{unit[:-1]}"
        failed = c.get("failed_review_attempts")
        if failed:
            ann = f"n = {n} · {mean:.1f} (attempts: {failed} failed)"
        ax.text(ann_x, cy, ann, ha="left", va="center")

    # centred size key (the fig4c convention: legend attached under the panel)
    key_y = fig_h - 3.0
    x = (fig_w - key_w) / 2
    for v, lab in zip((0, 1, 2, 4, 8), key_labels[:-1]):
        if v == 0:
            ax.plot([x + 0.9, x + 1.9], [key_y, key_y], color=BUBBLE_COLOR, lw=0.5,
                    solid_capstyle="butt")
        else:
            ax.add_patch(Circle((x + 1.4, key_y), bubble_r(v), facecolor=BUBBLE_COLOR, edgecolor="none"))
        ax.text(x + 3.1, key_y, lab, ha="left", va="center")
        x += 3.1 + text_w_mm(fig, lab) + 1.4
    ax.text(x + 0.6, key_y, key_labels[-1], ha="left", va="center")

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
