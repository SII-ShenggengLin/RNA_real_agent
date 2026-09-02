"""Fig 4g — Exp 25: advisory quality review, paired strip (31 PA sessions × 3 arms).

One row per process-aware regression session (31 sessions PA_006–PA_036,
grouped by workflow in the canonical workflow order, reviewed workflows
above and the three deterministic-exempt ones below a category divider),
three column blocks — Review off / Review on / Review on with the LLM
failure injected — and one outcome tile per session × arm:

  sage fill    = every turn of the session succeeds
  terracotta   = at least one failed turn (none expected — the panel's point)

Review-state glyphs (the governance layer the panel measures):
  filled ink dot   = review calls completed normally (Review-on arm,
                     reviewed workflows)
  open ink ring    = review recorded unavailable — audit metadata only
                     (failure-injected arm, reviewed workflows)
  no glyph         = no review applicable (deterministic-exempt workflows,
                     or the whole Review-off arm)

Hard-failure retry counts per arm are annotated on the right only for the
rows that have any (format off·on·fail); the totals live in the caption.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles;
every text element one 6-pt pure-black style; colours only from palette
rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm geometry; exact
canvas (no tight crop); renderer-measured label widths inside a canvas-
overflow assert (the fig4b/fig4e convention).

Data  : experiments/results/exp25_quality_review_advisory/{records.jsonl,summary.json}
        (+ pa_benchmarks.json for session order/workflows)
Usage : python experiments/plots/fig4g_quality_advisory_strip.py
Output : experiments/plots/output/fig4g_quality_advisory_strip.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import WORKFLOW_COLORS, WORKFLOW_LABELS, WORKFLOW_ORDER  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "experiments" / "results" / "exp25_quality_review_advisory"
BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

EXEMPT_WORKFLOWS = {
    "mrna_sequence_scoring",
    "aso_target_screening",
    "rna_small_molecule_interaction",
}
ARM_ORDER = ("off", "on", "fail")
ARM_HEADERS = {"off": "Review off", "on": "Review on", "fail": "Review on, outage"}
# explicit header lines (the automatic min-max wrap split "Review"/"on,
# outage" awkwardly — split at the semantic break instead)
ARM_HEADER_LINES = {
    "off": ["Review off"],
    "on": ["Review on"],
    "fail": ["Review on,", "API outage"],
}
PALETTE_INK = {"sage": "#A3B18A", "terracotta": "#C08B7C"}

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
    """Renderer-measured 6-pt string width in mm (the fig4b/fig4e convention)."""
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, s, fontsize=FONT, color=INK)
    bb = probe.get_window_extent(r)
    probe.remove()
    return bb.width / fig.dpi * 25.4


def load_rows() -> list[dict]:
    """Session rows in canonical workflow order → PA id order."""
    benchmarks = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    records = [
        json.loads(l)
        for l in (RESULTS / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    by_key = {(r["arm"], r["pa_id"]): r for r in records if not r.get("pilot")}

    def wf_rank(pa: str) -> tuple[int, int, str]:
        # two-band layout: reviewed workflows above, deterministic-exempt
        # below (WORKFLOW_ORDER kept within each band — a single divider)
        wf = benchmarks[pa]["workflow"]
        return (0 if wf not in EXEMPT_WORKFLOWS else 1,
                WORKFLOW_ORDER.index(wf), pa)

    rows = []
    for pa in sorted(benchmarks, key=wf_rank):
        wf = benchmarks[pa]["workflow"]
        rows.append({
            "pa": pa,
            "workflow": wf,
            "reviewed": wf not in EXEMPT_WORKFLOWS,
            "arms": {arm: by_key.get((arm, pa)) for arm in ARM_ORDER},
        })
    return rows


def main() -> int:
    rows = load_rows()
    missing = [(arm, r["pa"]) for r in rows for arm in ARM_ORDER if r["arms"][arm] is None]
    assert not missing, f"missing records for {missing[:5]} — run the full campaign first"

    # ── label-column widths, renderer-measured ───────────────────────────
    probe = plt.figure(figsize=(4, 4))
    wf_w = max(text_w_mm(probe, WORKFLOW_LABELS[r["workflow"]]) for r in rows)
    pa_w = max(text_w_mm(probe, f"PA_{r['pa']}") for r in rows)
    hdr_w = max(text_w_mm(probe, line) for a in ARM_ORDER for line in ARM_HEADER_LINES[a])
    retry_w = text_w_mm(probe, "8·8·8")  # retry-annotation column probe
    # key = four mini-tile exemplars merging the two channels (outcome fill ×
    # review-state glyph) — no glyph-less legend entry
    key_parts = [
        ("tile_dot", "Succeeds · review completed"),
        ("tile_ring", "Succeeds · review unavailable (metadata only)"),
        ("tile_plain", "Succeeds · no review applicable"),
        ("tile_fail", "Fails"),
    ]
    # exact emulation of the key-render walk below (swatch 3.4 + gap 1.2,
    # then label, then 3.4 before the next swatch; no trailing gap)
    _x = 0.0
    for _, t in key_parts:
        _x += 3.4 + 1.2
        _x += text_w_mm(probe, t) + 3.4
    key_w = _x - 3.4
    plt.close(probe)

    ML = 1.2
    IND = 2.5
    label_right = ML + max(wf_w, IND + pa_w)
    GAP_TB = 2.2
    block_w = 14.0
    block_gap = 6.0
    retry_gap = 4.0
    retry_x = label_right + GAP_TB + 3 * block_w + 2 * block_gap + retry_gap
    fig_w = max(retry_x + retry_w + ML, key_w + 2 * ML)

    row_h, row_gap = 1.7, 0.7
    pitch = row_h + row_gap
    wf_header_h = 2.5
    wf_gap = 1.0
    sep_extra = 3.0
    header_y = 4.6   # arm-header first-line centre
    rows_y0 = 9.6    # top edge of the first workflow header (2-line headers)

    # ── vertical walk: workflow headers + session rows + category divider ─
    layout: list[dict] = []
    headers: list[tuple[str, float, bool]] = []
    sep_y = None
    y = rows_y0
    prev_reviewed = None
    for r in rows:
        if prev_reviewed is not None and r["reviewed"] != prev_reviewed:
            sep_y = y + sep_extra / 2
            y += sep_extra
        if not headers or headers[-1][0] != r["workflow"]:
            headers.append((r["workflow"], y + wf_header_h / 2, r["reviewed"]))
            y += wf_header_h
        layout.append({**r, "y": y})
        y += pitch
        prev_reviewed = r["reviewed"]
    panel_bottom = y + 1.0
    key_y = panel_bottom + 3.2
    fig_h = key_y + 3.0

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")

    # arm block headers — horizontal, explicit lines (never rotated; a
    # rotated header was caught overflowing by the canvas assert)
    for i, arm in enumerate(ARM_ORDER):
        bx = label_right + GAP_TB + i * (block_w + block_gap)
        for j, line in enumerate(ARM_HEADER_LINES[arm]):
            ax.text(bx + block_w / 2, header_y + j * 2.0, line, ha="center", va="center")

    # workflow headers + PA row labels + category divider
    for wf, cy, reviewed in headers:
        ax.text(ML, cy, WORKFLOW_LABELS[wf], ha="left", va="center",
                color=WORKFLOW_COLORS[wf] if reviewed else "#7A7672")
    for rec in layout:
        ax.text(ML + IND, rec["y"] + row_h / 2, f"PA_{rec['pa']}", ha="left", va="center")
    if sep_y is not None:
        ax.plot([ML, fig_w - ML], [sep_y, sep_y], color="#7A7672", lw=0.5, ls=(0, (2, 2)))

    # tiles + review-state glyphs + retry annotations
    any_retries = False
    for rec in layout:
        for i, arm in enumerate(ARM_ORDER):
            arm_rec = rec["arms"][arm]
            bx = label_right + GAP_TB + i * (block_w + block_gap)
            success = arm_rec.get("session_success")
            cx, cy = bx + block_w / 2, rec["y"] + row_h / 2
            ax.add_patch(Rectangle((bx, rec["y"]), block_w, row_h,
                                   facecolor=PALETTE_INK["sage"] if success else PALETTE_INK["terracotta"],
                                   edgecolor="none"))
            if arm == "on" and rec["reviewed"]:
                ax.add_patch(Circle((cx, cy), 0.42, facecolor=INK, edgecolor="none"))
            elif arm == "fail" and rec["reviewed"]:
                ax.add_patch(Circle((cx, cy), 0.55, facecolor="none", edgecolor=INK, lw=0.6))
        retries = [rec["arms"][a].get("total_retry_count", 0) or 0 for a in ARM_ORDER]
        if any(retries):
            any_retries = True
            ax.text(retry_x, rec["y"] + row_h / 2, "·".join(str(v) for v in retries),
                    ha="left", va="center")
    if any_retries:
        ax.text(retry_x, header_y, "Retries", ha="left", va="center")

    # centred one-row key (the fig4c convention: legend attached under the
    # panel) — four mini tiles merging outcome fill × review-state glyph
    x = (fig_w - key_w) / 2
    ky = key_y
    for kind, label in key_parts:
        fill = PALETTE_INK["terracotta"] if kind == "tile_fail" else PALETTE_INK["sage"]
        ax.add_patch(Rectangle((x, ky - 0.85), 3.4, 1.7, facecolor=fill, edgecolor="none"))
        if kind == "tile_dot":
            ax.add_patch(Circle((x + 1.7, ky), 0.42, facecolor=INK, edgecolor="none"))
        elif kind == "tile_ring":
            ax.add_patch(Circle((x + 1.7, ky), 0.55, facecolor="none", edgecolor=INK, lw=0.6))
        x += 3.4 + 1.2
        ax.text(x, ky, label, ha="left", va="center")
        x += text_w_mm(fig, label) + 3.4

    # canvas-overflow assert (renderer-measured, the fig4b convention)
    r = fig.canvas.get_renderer()
    for t in ax.texts:
        bb = t.get_window_extent(r)
        assert bb.x0 >= -0.5 and bb.x1 <= fig.bbox.x1 + 0.5, f"text overflows: {t.get_text()!r}"
        assert bb.y0 >= -0.5 and bb.y1 <= fig.bbox.y1 + 0.5, f"text overflows: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4g_quality_advisory_strip.{ext}", dpi=1200)
    plt.close(fig)

    # raster QA: exact canvas, no ink on the outer border
    from PIL import Image
    im = Image.open(OUT_DIR / "fig4g_quality_advisory_strip.png")
    assert abs(im.width / 1200 * 25.4 - fig_w) < 0.05 and abs(im.height / 1200 * 25.4 - fig_h) < 0.05, \
        f"canvas mismatch: {im.size} vs {fig_w:.1f}×{fig_h:.1f} mm"
    px = im.convert("L")
    w, h = px.size
    for edge in (px.crop((0, 0, w, 1)), px.crop((0, h - 1, w, h)),
                 px.crop((0, 0, 1, h)), px.crop((w - 1, 0, w, h))):
        assert edge.getextrema()[0] == 255, "ink at the outer border"
    print(f"[fig4g] {fig_w:.1f} × {fig_h:.1f} mm, {len(rows)} sessions × 3 arms — "
          f"raster QA green → {OUT_DIR / 'fig4g_quality_advisory_strip.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
