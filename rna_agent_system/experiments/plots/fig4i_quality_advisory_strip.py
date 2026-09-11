"""Fig 4i — Exp 25: advisory quality review, paired strip (31 PA sessions × 3 arms).

One row per process-aware regression session (31 sessions PA_006–PA_036,
grouped by workflow in the canonical workflow order, reviewed workflows
above and the three deterministic-exempt ones below a category divider),
three column blocks — Review off / Review on / Review on with the LLM
API outage injected — and one colour tile per session × arm. The tile
colour directly encodes the session's combined outcome × review state
(no overlaid glyphs):

  sage green   = succeeds · review completed    (Review-on arm, reviewed
                                                 workflows — 145 calls)
  grey blue    = succeeds · review unavailable  (outage arm, reviewed
                                                 workflows — 144 attempted
                                                 calls absorbed, audit
                                                 metadata only)
  warm grey    = succeeds · no review           (Review-off arm, and the
                                                 deterministic-exempt
                                                 workflows in every arm)

2026-09-11 PA_023 restore merge (user-directed; frozen Exp-25 corpus
untouched): the frozen corpus's one exception — PA_023 turns 1–2 failed
identically in all three arms on a pre-reset ephemeral-workspace input
file never migrated into the tracked fixtures — is re-measured by the
Exp-25b restore addendum (`experiments/results/exp25b_pa023_restore_addendum/`),
which restores the file byte-identically from the task's own
constants.UTR5_SEQUENCE and re-runs the session under the identical
three-arm protocol: 3/3 turns succeed in every arm, per-turn outcomes
identical across arms, on-arm 6 completed calls, outage-arm 6 failed
attempts, zero retries. The panel draws the merged latest-record-wins
state (31/31 succeed in every arm; the call totals are unchanged by the
merge — review runs even on failed turns, so PA_023 contributed 6 on-arm
calls and 6 outage-arm attempts in both eras, keeping 145 and 144); the
frozen 30/31 measurement stays in the registers. No terracotta tile
remains — the failed-state colour is kept in the map only as a defensive
assert.

2026-09-02 user-directed repair pass (same frozen Exp-25 records, no
re-run):
  - every text element is pure black — the workflow group headers no
    longer pick up the workflow carpet colours and the category divider
    draws in ink at 0.6 lw instead of de-facto grey (the fig4e
    convention);
  - the arm headers were vertically misaligned (the one-line headers sat
    on the first of the two-line header's rows) and the whole panel was
    shifted left by a retry-annotation column that the zero-retry data
    never fills — the headers are now a fixed two-line block (arm name +
    a per-arm numbers line "31/31 succeed · N calls", aligned across
    arms) and the retry column is only reserved when retries exist;
  - second pass (same day, user-directed): the first repair's key split
    the encoding into tile fill × overlaid dot/ring glyphs with two
    lead-in rows — judged too complex; the encoding is now direct, one
    colour per state, plain colour swatches in a two-row key.

Style (Nature conventions, the fig3/fig4 house style): no in-figure titles —
the headline lives in the caption and the arm names are plain column
headers; every text element one 6-pt pure-black style; colours only from
palette rev 7; 1200-dpi PNG + vector PDF (fonttype 42); absolute-mm
geometry; exact canvas (no tight crop); renderer-measured label widths
inside a canvas-overflow assert (the fig4e/fig4g convention).

Data  : experiments/results/exp25_quality_review_advisory/{records.jsonl,summary.json}
        + experiments/results/exp25b_pa023_restore_addendum/records.jsonl
          (the PA_023 latest-record-wins merge; see above)
        (+ pa_benchmarks.json for session order/workflows)
Usage : python experiments/plots/fig4i_quality_advisory_strip.py
Output : experiments/plots/output/fig4i_quality_advisory_strip.{pdf,png}
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
from palette import PALETTE_BY_NAME, WORKFLOW_LABELS, WORKFLOW_ORDER  # noqa: E402

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
ARM_HEADERS = {"off": "Review off", "on": "Review on", "fail": "Review on, API outage"}

# one palette colour per combined outcome × review state
STATE_COLORS = {
    "completed": PALETTE_BY_NAME["sage_green"],   # succeeds · review completed
    "unavailable": PALETTE_BY_NAME["grey_blue"],  # succeeds · review unavailable
    "none": PALETTE_BY_NAME["warm_grey"],         # succeeds · no review
    "fail": PALETTE_BY_NAME["terracotta"],        # failed (defensive only —
    # the merged state carries no failed session; asserted in main())
}
STATE_ORDER = ("completed", "unavailable", "none")
STATE_LABELS = {
    "completed": "Succeeds · review completed",
    "unavailable": "Succeeds · review unavailable",
    "none": "Succeeds · no review",
    "fail": "Failed",
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


def text_w_mm(fig, s: str) -> float:
    """Renderer-measured 6-pt string width in mm (the fig4b/fig4e convention)."""
    r = fig.canvas.get_renderer()
    probe = fig.text(0, 0, s, fontsize=FONT, color=INK)
    bb = probe.get_window_extent(r)
    probe.remove()
    return bb.width / fig.dpi * 25.4


def load_rows() -> list[dict]:
    """Session rows in canonical workflow order → PA id order.

    The 2026-09-11 PA_023 restore merge: the frozen Exp-25 records supply
    the 30 unaffected sessions; the three PA_023 rows come from the
    Exp-25b restore addendum (latest-record-wins). The frozen rows are
    asserted to carry the registered identical fixture-gap failure (2
    failed turns in every arm) and the addendum rows to succeed 3/3, so
    the merge can never silently mask a different failure.
    """
    benchmarks = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    records = [
        json.loads(l)
        for l in (RESULTS / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    addendum_path = (PROJECT_ROOT / "experiments" / "results"
                     / "exp25b_pa023_restore_addendum" / "records.jsonl")
    addendum = [
        json.loads(l)
        for l in addendum_path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert {a["arm"] for a in addendum} == set(ARM_ORDER) and all(
        a["pa_id"] == "023" for a in addendum
    ), "addendum must supply exactly the three PA_023 arm records"
    assert all(a["session_success"] for a in addendum), "addendum PA_023 must succeed"
    for r in records:  # the registered frozen failure, asserted not assumed
        if r.get("pilot") or r["pa_id"] != "023":
            continue
        assert r["failed_turns"] == 2 and not r["session_success"], (
            "frozen PA_023 rows must carry the registered 2-failed-turn gap"
        )
    by_key = {(r["arm"], r["pa_id"]): r for r in records if not r.get("pilot")}
    for a in addendum:  # latest-record-wins overlay
        by_key[(a["arm"], a["pa_id"])] = a

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


def arm_stat_lines(rows: list[dict]) -> dict[str, str]:
    """Per-arm numbers line under each header: successes · review calls.

    Computed from the merged records (frozen 30 + PA_023 addendum) and
    asserted against the merged-reporting registration: 31/31 succeed per
    arm, on-arm 145 completed calls (unchanged — PA_023 contributed 6 in
    both eras), outage-arm 148 failed attempts (frozen 144 with PA_023's
    2 pre-review-failure attempts replaced by 6 restored-input attempts).
    """
    lines = {}
    for arm in ARM_ORDER:
        recs = [r["arms"][arm] for r in rows]
        n = len(recs)
        s = sum(1 for r in recs if r.get("session_success"))
        ok = sum(r.get("total_successful_review_calls", 0) for r in recs)
        failed = sum(r.get("total_failed_review_calls", 0) for r in recs)
        assert n == 31 and s == 31, f"{arm}: merged state must be 31/31, got {s}/{n}"
        if arm == "on":
            assert ok == 145 and failed == 0, f"on-arm merged calls {ok}/{failed}"
        elif arm == "fail":
            assert ok == 0 and failed == 144, f"outage-arm merged attempts {ok}/{failed}"
        else:
            assert ok == 0 and failed == 0, f"off-arm merged calls {ok}/{failed}"
        suffix = {"off": "0 calls", "on": f"{ok} calls",
                  "fail": f"{failed} failed"}[arm]
        lines[arm] = f"{s}/{n} succeed · {suffix}"
    return lines


def cell_state(arm: str, reviewed: bool, success: bool) -> str:
    if not success:
        return "fail"
    if reviewed and arm == "on":
        return "completed"
    if reviewed and arm == "fail":
        return "unavailable"
    return "none"


def main() -> int:
    rows = load_rows()
    missing = [(arm, r["pa"]) for r in rows for arm in ARM_ORDER if r["arms"][arm] is None]
    assert not missing, f"missing records for {missing[:5]} — run the full campaign first"
    stat_lines = arm_stat_lines(rows)
    # the retry-annotation column only exists when the data has retries
    any_retries = any((rec["arms"][a].get("total_retry_count") or 0) > 0
                      for rec in rows for a in ARM_ORDER)

    # colour-only key: four swatches in a two-row grid, columns shared so
    # swatch/label left edges align across rows (the fig4d convention)
    key_rows = [STATE_ORDER[:2], STATE_ORDER[2:]]
    TILE_W, TILE_H, SW_LABEL_GAP, ENTRY_GAP = 3.4, 1.7, 1.2, 3.4

    # ── label-column + header + key widths, renderer-measured ────────────
    probe = plt.figure(figsize=(4, 4))
    wf_w = max(text_w_mm(probe, WORKFLOW_LABELS[r["workflow"]]) for r in rows)
    pa_w = max(text_w_mm(probe, f"PA_{r['pa']}") for r in rows)
    hdr_w = max(text_w_mm(probe, t) for t in
                list(ARM_HEADERS.values()) + list(stat_lines.values()))
    retry_w = text_w_mm(probe, "8·8·8") if any_retries else 0.0
    col_ws = [max(text_w_mm(probe, STATE_LABELS[row[c]]) for row in key_rows
                  if len(row) > c) for c in range(2)]
    key_w = sum(TILE_W + SW_LABEL_GAP + w for w in col_ws) + ENTRY_GAP
    plt.close(probe)

    ML = 1.2
    IND = 2.5
    label_right = ML + max(wf_w, IND + pa_w)
    GAP_TB = 2.2
    block_w = max(14.0, hdr_w + 2.0)   # arm headers must sit inside their block
    block_gap = 5.0
    retry_gap = 4.0

    def panel_w(gap: float) -> float:
        w = label_right + GAP_TB + 3 * block_w + 2 * gap + ML
        if any_retries:
            w += retry_gap + retry_w
        return w

    # canvas takes the wider of panel and key; a wider key is absorbed by
    # widening the inter-block gaps so the panel never leaves a right void
    fig_w = panel_w(block_gap)
    if key_w + 2 * ML > fig_w:
        block_gap += (key_w + 2 * ML - fig_w) / 2
        fig_w = panel_w(block_gap)
    # 2026-09-06: the navigation-era re-run recorded one retry (on-arm) —
    # the first non-empty retries column; widen the canvas for it.
    if any_retries:
        fig_w += 9.0
    retry_x = label_right + GAP_TB + 3 * block_w + 2 * block_gap + retry_gap

    row_h, row_gap = 1.7, 0.7
    pitch = row_h + row_gap
    wf_header_h = 2.5
    sep_extra = 3.0
    header_name_y = 4.6   # arm-name line centre
    header_stat_y = 7.0   # numbers-line centre (aligned across all arms)
    rows_y0 = 9.9         # top edge of the first workflow header

    # ── vertical walk: workflow headers + session rows + category divider ─
    layout: list[dict] = []
    headers: list[tuple[str, float]] = []
    sep_y = None
    y = rows_y0
    prev_reviewed = None
    for r in rows:
        if prev_reviewed is not None and r["reviewed"] != prev_reviewed:
            sep_y = y + sep_extra / 2
            y += sep_extra
        if not headers or headers[-1][0] != r["workflow"]:
            headers.append((r["workflow"], y + wf_header_h / 2))
            y += wf_header_h
        layout.append({**r, "y": y})
        y += pitch
        prev_reviewed = r["reviewed"]
    panel_bottom = y + 1.0
    key_top = panel_bottom + 3.2
    key_cys = (key_top + 1.0, key_top + 3.6)
    fig_h = key_top + 4.6 + ML

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")

    # arm block headers: name line + numbers line, both centred over the
    # block and aligned across arms (never rotated)
    for i, arm in enumerate(ARM_ORDER):
        bx = label_right + GAP_TB + i * (block_w + block_gap)
        ax.text(bx + block_w / 2, header_name_y, ARM_HEADERS[arm], ha="center", va="center")
        ax.text(bx + block_w / 2, header_stat_y, stat_lines[arm], ha="center", va="center")
    if any_retries:
        ax.text(retry_x, header_name_y, "Retries", ha="left", va="center")

    # workflow headers + PA row labels (pure black) + category divider (ink)
    for wf, cy in headers:
        ax.text(ML, cy, WORKFLOW_LABELS[wf], ha="left", va="center")
    for rec in layout:
        ax.text(ML + IND, rec["y"] + row_h / 2, f"PA_{rec['pa']}", ha="left", va="center")
    if sep_y is not None:
        ax.plot([ML, fig_w - ML], [sep_y, sep_y], color=INK, lw=0.6)

    # state-coloured tiles (+ retry annotations only when present)
    for rec in layout:
        for i, arm in enumerate(ARM_ORDER):
            arm_rec = rec["arms"][arm]
            bx = label_right + GAP_TB + i * (block_w + block_gap)
            state = cell_state(arm, rec["reviewed"], bool(arm_rec.get("session_success")))
            assert state != "fail", (
                f"merged state must carry no failed session, found {state} on "
                f"PA_{rec['pa']}/{arm}"
            )
            ax.add_patch(Rectangle((bx, rec["y"]), block_w, row_h,
                                   facecolor=STATE_COLORS[state], edgecolor="none"))
        if any_retries:
            retries = [rec["arms"][a].get("total_retry_count", 0) or 0 for a in ARM_ORDER]
            if any(retries):
                ax.text(retry_x, rec["y"] + row_h / 2, "·".join(str(v) for v in retries),
                        ha="left", va="center")

    # ── colour key: two centred rows on the shared column grid ───────────
    x0 = (fig_w - key_w) / 2
    col_x = [x0, x0 + TILE_W + SW_LABEL_GAP + col_ws[0] + ENTRY_GAP]
    for row, ky in zip(key_rows, key_cys):
        for state, cx in zip(row, col_x):
            ax.add_patch(Rectangle((cx, ky - TILE_H / 2), TILE_W, TILE_H,
                                   facecolor=STATE_COLORS[state], edgecolor="none"))
            ax.text(cx + TILE_W + SW_LABEL_GAP, ky, STATE_LABELS[state],
                    ha="left", va="center")

    # canvas-overflow assert (renderer-measured, the fig4b convention)
    r = fig.canvas.get_renderer()
    for t in ax.texts:
        bb = t.get_window_extent(r)
        assert bb.x0 >= -0.5 and bb.x1 <= fig.bbox.x1 + 0.5, f"text overflows: {t.get_text()!r}"
        assert bb.y0 >= -0.5 and bb.y1 <= fig.bbox.y1 + 0.5, f"text overflows: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4i_quality_advisory_strip.{ext}", dpi=1200)
    plt.close(fig)

    # raster QA: exact canvas, no ink on the outer border
    from PIL import Image
    im = Image.open(OUT_DIR / "fig4i_quality_advisory_strip.png")
    assert abs(im.width / 1200 * 25.4 - fig_w) < 0.05 and abs(im.height / 1200 * 25.4 - fig_h) < 0.05, \
        f"canvas mismatch: {im.size} vs {fig_w:.1f}×{fig_h:.1f} mm"
    px = im.convert("L")
    w, h = px.size
    for edge in (px.crop((0, 0, w, 1)), px.crop((0, h - 1, w, h)),
                 px.crop((0, 0, 1, h)), px.crop((w - 1, 0, w, h))):
        assert edge.getextrema()[0] == 255, "ink at the outer border"
    print(f"[fig4i] {fig_w:.1f} × {fig_h:.1f} mm, {len(rows)} sessions × 3 arms, "
          f"retries {'shown' if any_retries else 'none (column dropped)'} — "
          f"raster QA green → {OUT_DIR / 'fig4i_quality_advisory_strip.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
