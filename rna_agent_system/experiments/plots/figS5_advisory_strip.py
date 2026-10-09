"""Supplementary Fig. S5 — Exp 25: advisory quality review, paired strip (31 PA sessions × 3 arms).

2026-10-02 re-homing (figure-backlog batch, registered 2026-09-28): the
governance-ablation paragraph moved from main-text section 2.4 to
Supplementary Note 3, so this panel and the LLM-usage strip (Supplementary
Fig. S6) left main Fig. 4, which is cut to a–h; script and outputs renamed
from fig4i_quality_advisory_strip (content, data and geometry unchanged).

One row per process-aware regression session (31 sessions PA_006–PA_036,
grouped by workflow in the canonical workflow order, reviewed workflows
above and the three deterministic-exempt ones below a category divider),
three column blocks — Review off / Review on / Review on, all review calls
made to fail — and one colour tile per session × arm. The tile colour directly
encodes the session's combined outcome × review state (no overlaid glyphs):

  sage green   = review completed               (Review-on arm, reviewed
                                                 workflows — 145 calls)
  grey blue    = review unavailable             (outage arm, reviewed
                                                 workflows — 144 attempted
                                                 calls absorbed, audit
                                                 metadata only)
  warm grey    = no review                      (Review-off arm, and the
                                                 deterministic-exempt
                                                 workflows in every arm)

Every tile is a succeeding session — the per-block header lines carry
"31/31 succeed" — so the key needs only the review-state half.

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

2026-10-09 repair pass (user-directed; same merged records, no re-run):
  - the retry-annotation column is retired — the data's only non-zero
    value was the single on-arm retry (0/1/0, the PA_012 turn-3 re-run),
    which stays carried verbatim by the FACT_SHEET exp-25 exact-numbers
    line and the frozen records, so the panel no longer reserves a
    mostly-empty right column;
  - the third arm header is re-worded to the registered SI-legend phrase
    ("review on with all review calls made to fail" since the 2026-10-09
    user-adjudicated grammar pass, earlier "failing") as a two-line centred
    header, replacing "Review on, endpoint failed";
  - the per-block numbers are split over two short lines ("31/31
    succeed" + the per-arm call count) and the blocks are sized by those
    numbers lines, so the tile columns narrow (the two-line header name
    may overhang its block symmetrically);
  - the key drops the repeated "Succeeds ·" prefix (the outcome half
    lives in the per-block "31/31 succeed" lines) and is one row of
    three swatches, centred under the panel;
  - workflow group labels are vertically centred on their group's rows
    (the old top-of-group header bands left the left text visually
    misaligned with the tile block beside it);
  - no data, colour or count changed.

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
    colour per state, plain colour swatches in the key.

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
Usage : python experiments/plots/figS5_advisory_strip.py
Output : experiments/plots/output/figS5_advisory_strip.{pdf,png}
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
# third header = the registered SI-legend phrase ("review on with all review
# calls made to fail"), wrapped to two centred lines so the blocks stay narrow
ARM_HEADER_LINES = {
    "off": ("Review off",),
    "on": ("Review on",),
    "fail": ("Review on,", "all review calls made to fail"),
}

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
    "completed": "review completed",
    "unavailable": "review unavailable",
    "none": "no review",
    "fail": "failed",
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


def arm_stat_lines(rows: list[dict]) -> dict[str, tuple[str, str]]:
    """Per-block numbers lines under the header name: succeed + calls.

    Computed from the merged records (frozen 30 + PA_023 addendum) and
    asserted against the merged-reporting registration: 31/31 succeed per
    arm, on-arm 145 completed calls, outage-arm 144 failed attempts (both
    unchanged by the merge — review runs even on failed turns, so PA_023
    contributed 6 on-arm calls and 6 outage-arm attempts in both eras).
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
        calls = {"off": "0 calls", "on": f"{ok} calls",
                 "fail": f"{failed} failed calls"}[arm]
        lines[arm] = (f"{s}/{n} succeed", calls)
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

    # colour-only key: one row of three swatches, centred under the panel
    TILE_W, TILE_H, SW_LABEL_GAP, ENTRY_GAP = 3.4, 1.7, 1.2, 3.4

    # ── label-column + header + key widths, renderer-measured ────────────
    probe = plt.figure(figsize=(4, 4))
    wf_w = max(text_w_mm(probe, WORKFLOW_LABELS[r["workflow"]]) for r in rows)
    hdr_w = max(text_w_mm(probe, t) for lines in ARM_HEADER_LINES.values() for t in lines)
    stat_w = max(text_w_mm(probe, t) for pair in stat_lines.values() for t in pair)
    state_w = {s: text_w_mm(probe, STATE_LABELS[s]) for s in STATE_ORDER}
    key_w = (sum(TILE_W + SW_LABEL_GAP + state_w[s] for s in STATE_ORDER)
             + ENTRY_GAP * (len(STATE_ORDER) - 1))
    plt.close(probe)

    ML = 1.2
    label_right = ML + wf_w
    GAP_TB = 2.0
    # blocks sized by their numbers lines; a header name line may overhang
    # its block symmetrically (the pairwise text-collision assert guards the
    # neighbouring headers, the canvas-overflow assert guards the edges)
    block_w = max(14.0, stat_w + 2.2)
    block_gap = 3.0

    def panel_w(gap: float) -> float:
        return label_right + GAP_TB + 3 * block_w + 2 * gap + ML

    # canvas takes the wider of panel and key; a wider key is absorbed by
    # widening the inter-block gaps so the panel never leaves a right void
    fig_w = panel_w(block_gap)
    if key_w + 2 * ML > fig_w:
        block_gap += (key_w + 2 * ML - fig_w) / 2
        fig_w = panel_w(block_gap)
    # the last block's widest header line may reach past the panel edge —
    # extend the canvas so it keeps a real margin
    hdr_right = label_right + GAP_TB + 2 * (block_w + block_gap) + block_w / 2 + hdr_w / 2
    fig_w = max(fig_w, hdr_right + 0.7)

    row_h, row_gap = 1.7, 0.7
    pitch = row_h + row_gap
    sep_extra = 3.0
    name_ys = (2.7, 5.1)   # two-line name zone; single-line names centre at 3.9
    succeed_y = 7.6        # "31/31 succeed" line (aligned across all arms)
    calls_y = 9.9          # per-arm call-count line (aligned across all arms)
    rows_y0 = 12.4         # top edge of the first session row

    # ── vertical walk: session rows + workflow groups + category divider ──
    layout: list[dict] = []
    groups: list[tuple[str, list[dict]]] = []
    sep_y = None
    y = rows_y0
    prev_reviewed = None
    for r in rows:
        if prev_reviewed is not None and r["reviewed"] != prev_reviewed:
            sep_y = y + sep_extra / 2
            y += sep_extra
        if not groups or groups[-1][0] != r["workflow"]:
            groups.append((r["workflow"], []))
        rec = {**r, "y": y}
        layout.append(rec)
        groups[-1][1].append(rec)
        y += pitch
        prev_reviewed = r["reviewed"]
    panel_bottom = y + 0.6
    key_cy = panel_bottom + 3.0
    fig_h = key_cy + 1.5 + ML

    fig = plt.figure(figsize=(fig_w / 25.4, fig_h / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)
    ax.axis("off")

    # arm block headers: name (one or two centred lines) + two numbers
    # lines, both numbers lines at fixed y so the three blocks align (never
    # rotated)
    for i, arm in enumerate(ARM_ORDER):
        bx = label_right + GAP_TB + i * (block_w + block_gap)
        lines = ARM_HEADER_LINES[arm]
        ys = name_ys if len(lines) > 1 else (sum(name_ys) / 2,)
        for t, cy in zip(lines, ys):
            ax.text(bx + block_w / 2, cy, t, ha="center", va="center")
        succeed, calls = stat_lines[arm]
        ax.text(bx + block_w / 2, succeed_y, succeed, ha="center", va="center")
        ax.text(bx + block_w / 2, calls_y, calls, ha="center", va="center")

    # workflow group labels, each vertically centred on its group's rows;
    # session rows carry no per-row identifier (the de-coding house rule —
    # internal session ids stay out of reader-facing panels, the Fig. 2e
    # 2026-10-02 precedent); category divider in ink
    for wf, recs in groups:
        cy = (recs[0]["y"] + recs[-1]["y"] + row_h) / 2
        ax.text(ML, cy, WORKFLOW_LABELS[wf], ha="left", va="center")
    if sep_y is not None:
        ax.plot([ML, fig_w - ML], [sep_y, sep_y], color=INK, lw=0.6)

    # state-coloured tiles
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

    # ── colour key: one centred row under the panel ───────────────────────
    x = (fig_w - key_w) / 2
    for state in STATE_ORDER:
        ax.add_patch(Rectangle((x, key_cy - TILE_H / 2), TILE_W, TILE_H,
                               facecolor=STATE_COLORS[state], edgecolor="none"))
        ax.text(x + TILE_W + SW_LABEL_GAP, key_cy, STATE_LABELS[state],
                ha="left", va="center")
        x += TILE_W + SW_LABEL_GAP + state_w[state] + ENTRY_GAP

    # canvas-overflow assert (renderer-measured, the fig4b convention) and a
    # pairwise text-collision assert (labels must never overlap each other)
    r = fig.canvas.get_renderer()
    bbs = []
    for t in ax.texts:
        bb = t.get_window_extent(r)
        assert bb.x0 >= -0.5 and bb.x1 <= fig.bbox.x1 + 0.5, f"text overflows: {t.get_text()!r}"
        assert bb.y0 >= -0.5 and bb.y1 <= fig.bbox.y1 + 0.5, f"text overflows: {t.get_text()!r}"
        bbs.append((t.get_text(), bb))
    for i in range(len(bbs)):
        for j in range(i + 1, len(bbs)):
            a, b = bbs[i][1], bbs[j][1]
            assert not (a.x0 < b.x1 and b.x0 < a.x1 and a.y0 < b.y1 and b.y0 < a.y1), (
                f"text collision: {bbs[i][0]!r} vs {bbs[j][0]!r}"
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"figS5_advisory_strip.{ext}", dpi=1200)
    plt.close(fig)

    # raster QA: exact canvas, no ink on the outer border
    from PIL import Image
    im = Image.open(OUT_DIR / "figS5_advisory_strip.png")
    assert abs(im.width / 1200 * 25.4 - fig_w) < 0.05 and abs(im.height / 1200 * 25.4 - fig_h) < 0.05, \
        f"canvas mismatch: {im.size} vs {fig_w:.1f}×{fig_h:.1f} mm"
    px = im.convert("L")
    w, h = px.size
    for edge in (px.crop((0, 0, w, 1)), px.crop((0, h - 1, w, h)),
                 px.crop((0, 0, 1, h)), px.crop((w - 1, 0, w, h))):
        assert edge.getextrema()[0] == 255, "ink at the outer border"
    print(f"[figS5] {fig_w:.1f} × {fig_h:.1f} mm, {len(rows)} sessions × 3 arms — "
          f"raster QA green → {OUT_DIR / 'figS5_advisory_strip.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
