"""Fig 4e — selective gating decision matrix (Exp 23, §2.4 实验 4).

One tile per query condition: the two production gate layers reviewed the
GEMORNA 5'UTR MRL oracle and the 3'UTR stability oracle across certified /
never-profiled target families, and every verdict lands in exactly one
column. DecisionGate (pre-action, ranking-objective requests): allow on all
three Exp-14-certified families, downgrade (conservative transfer,
confidence 1.0 -> 0.5) on the never-profiled family, require_profiling for
the unprofiled 3'UTR oracle. ClaimGate (pre-publication, absolute-scope
claims): pass / downgrade to within-target relative / reject. In-tile
numbers are the SelfModel confidences (ClaimGate is rule-based and yields
none, so its tiles stay blank); the right-hand single-line annotations carry
the enforcement consequence (E1 executed with the predicted MRL reproducing
the Exp-14 cache bit-exactly, E2 executed, E3 blocked as GatedActionError
before any service call); column headers carry the per-column cell counts.

Colours (palette rev 7): sage = allow/pass, mauve grey = downgrade, sand =
require-profiling, terracotta = reject (the fig2h gate-verdict convention);
hairline rules in the non-data neutral grid grey. The per-row oracle colour
strips of the previous revision were dropped — the rotated group labels and
the row labels already carry the oracle identity.

Style (Nature conventions, the fig3/fig4 house style): no in-figure title —
the two gate layers are marked only by short left-aligned block labels;
every text element one 6-pt pure-black style; absolute-mm geometry with
renderer-measured text extents (the fig4b/fig4d convention): the horizontal
layout follows the measured label/annotation widths with fixed clearances
between the zones, so no dead whitespace; plus a post-draw audit asserting
every text is pure black, no two texts overlap, no text crosses a tile edge,
and everything sits on the canvas; 1200-dpi PNG + vector PDF (fonttype 42)
at a content-measured width x 72 mm — within Nature Methods resolution and
size guidance.

Data  : experiments/results/exp23_selective_gating/cells.jsonl (frozen)
Usage : python experiments/plots/fig4e_selective_gating_matrix.py
Output : experiments/plots/output/fig4e_selective_gating.{pdf,png}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CELLS_JSONL = PROJECT_ROOT / "experiments" / "results" / "exp23_selective_gating" / "cells.jsonl"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
FONT = 6

VERDICT_COLOR = {
    "allow": PALETTE_BY_NAME["sage_green"],
    "pass": PALETTE_BY_NAME["sage_green"],
    "downgrade": PALETTE_BY_NAME["mauve_grey"],
    "require_profiling": PALETTE_BY_NAME["sand"],
    "reject": PALETTE_BY_NAME["terracotta"],
}

COL_KEYS = ["allow_pass", "downgrade", "blocked"]
COL_HEADERS = {  # one centred line per column; the legend names the verdicts
    "allow_pass": "allow · pass",
    "downgrade": "downgrade",
    "blocked": "blocked",  # require-profiling (DecisionGate) + reject (ClaimGate)
}
COL_OF_VERDICT = {
    "allow": "allow_pass", "pass": "allow_pass",
    "downgrade": "downgrade",
    "require_profiling": "blocked", "reject": "blocked",
}
ORACLE_ROTATED = {"mrl": "5′UTR MRL", "utr3": "3′UTR"}

# cell, block, oracle, row label (family names follow the fig4d short-name
# convention); the one-line annotation is built from the frozen cells below
ROWS = [
    ("D1", "decision", "mrl", "certified · EGFP random-50"),
    ("D2", "decision", "mrl", "certified · var-len random"),
    ("D3", "decision", "mrl", "certified · var-len human"),
    ("D4", "decision", "mrl", "never-profiled family"),
    ("D5", "decision", "utr3", "certified family"),
    ("D6", "decision", "utr3", "never-profiled family"),
    ("C1", "claim", "mrl", "5′UTR claim · certified"),
    ("C2", "claim", "mrl", "5′UTR claim · never-profiled"),
    ("C3", "claim", "utr3", "3′UTR claim · never-profiled"),
]

KEY_ITEMS = [  # verdict legend, one centred row under the panel
    (VERDICT_COLOR["allow"], "allow / pass"),
    (VERDICT_COLOR["downgrade"], "downgrade"),
    (VERDICT_COLOR["require_profiling"], "require-profiling"),
    (VERDICT_COLOR["reject"], "reject"),
]

# mm geometry (canvas H 72 mm, y up; W derived from the measured content)
H = 72.0
X_ROT_C = 2.2            # rotated oracle group-label centre
X_LABEL = 5.0            # row-label left edge
TILE_W, TILE_H = 8.0, 3.4
COL_PITCH = 14.5         # tile-column pitch
GAP_LABEL = 2.5          # longest row label -> first tile column
GAP_TILE_ANN = 3.5       # last tile column -> annotations
MARGIN_R = 1.5           # right margin past the longest annotation
ROW_H = 4.8
Y_HDR1 = 68.6            # column-header line 1 centre
Y_HDR2 = 66.2            # column-header line 2 (cell counts) centre
Y_HDRRULE = 64.2
Y_DHDR = 61.8            # DecisionGate block label centre
Y_D1 = 57.4              # first DecisionGate row centre
Y_SEP = 29.6             # block separator rule
Y_CHDR = 27.0            # ClaimGate block label centre
Y_C1 = 22.6              # first ClaimGate row centre
Y_LEG = 5.2              # legend row centre

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "text.color": INK,
    "pdf.fonttype": 42,
})


def annotation(cid: str, cells: dict) -> str:
    """One-line right-hand annotation; numbers come from the frozen cells."""
    if cid == "D1":  # E1: allow executed, MRL bit-identical to the Exp-14 cache
        return f"executed · MRL {cells['E1']['detail']['predicted_mrl']:g} = Exp-14"
    if cid == "D4":  # E2: downgrade executed on the never-profiled family
        return f"executed · MRL {cells['E2']['detail']['predicted_mrl']:g}"
    return {
        "D2": "not blocked",
        "D3": "not blocked",
        "D5": "blocked pre-call",  # E3: GatedActionError before any service call
        "D6": "blocked pre-call",
        "C1": "absolute scope stands",
        "C2": "scope → within-target relative",
        "C3": "no publishable basis",
    }[cid]


def main() -> int:
    cells = {}
    for line in CELLS_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            cells[c["cell"]] = c
    assert len(cells) == 12 and all(c["expectation_met"] for c in cells.values()), (
        "fig4e draws only the frozen all-met Exp-23 result"
    )
    for e in ("E1", "E2", "E3"):
        assert cells[e]["expectation_met"]
    assert cells["E1"]["detail"]["exact_match"]
    assert cells["E3"]["detail"]["error"]["type"] == "GatedActionError"

    # renderer-measured text extents (the fig4b/fig4d convention)
    probe = plt.figure(figsize=(4, 4))

    def w_mm(s: str) -> float:
        r = probe.canvas.get_renderer()
        t = probe.text(0, 0, s, fontsize=FONT, color=INK)
        bb = t.get_window_extent(r)
        t.remove()
        return bb.width / probe.dpi * 25.4

    label_w = max(w_mm(lbl) for _c, _b, _o, lbl in ROWS)
    ann_w = max(w_mm(annotation(cid, cells)) for cid, _b, _o, _l in ROWS)
    hdr_w = {k: w_mm(COL_HEADERS[k]) for k in COL_KEYS}
    rot_w = {k: w_mm(v) for k, v in ORACLE_ROTATED.items()}
    key_w = {lab: w_mm(lab) for _c, lab in KEY_ITEMS}
    plt.close(probe)

    # horizontal layout follows the measured text: row labels -> tile
    # columns -> annotations -> right margin, fixed clearances between zones
    X_COL = [X_LABEL + label_w + GAP_LABEL + i * COL_PITCH for i in range(3)]
    X_ANN = X_COL[2] + TILE_W + GAP_TILE_ANN
    W = X_ANN + ann_w + MARGIN_R
    for ka, kb in zip(COL_KEYS, COL_KEYS[1:]):
        ca = X_COL[COL_KEYS.index(ka)] + TILE_W / 2
        cb = X_COL[COL_KEYS.index(kb)] + TILE_W / 2
        assert ca + hdr_w[ka] / 2 + 1.5 <= cb - hdr_w[kb] / 2, "column headers collide"

    fig = plt.figure(figsize=(W / 25.4, H / 25.4), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    def text(x, y, s, **kw):
        kw.setdefault("fontsize", FONT)
        kw.setdefault("color", INK)
        return ax.text(x, y, s, **kw)

    ys = {}
    for i, (cid, block, _o, _l) in enumerate(ROWS):
        ys[cid] = (Y_D1 - i * ROW_H) if block == "decision" else (Y_C1 - (i - 6) * ROW_H)

    # column headers (verdict + cell count) + light rule under them
    col_n = {k: 0 for k in COL_KEYS}
    for cid, _b, _o, _l in ROWS:
        col_n[COL_OF_VERDICT[cells[cid]["actual_verdict"]]] += 1
    for key, x0 in zip(COL_KEYS, X_COL):
        cx = x0 + TILE_W / 2
        text(cx, Y_HDR1, COL_HEADERS[key], ha="center", va="center")
        text(cx, Y_HDR2, f"n = {col_n[key]}", ha="center", va="center")
    ax.plot([X_COL[0] - 1.0, X_COL[2] + TILE_W + 1.0],
            [Y_HDRRULE, Y_HDRRULE], color=NEUTRAL_GRID, linewidth=0.3)

    n_met = sum(1 for c in cells.values() if c["expectation_met"])

    # block labels + block separator rule
    text(X_LABEL, Y_DHDR, "DecisionGate (pre-action)", ha="left", va="center")
    text(X_LABEL, Y_CHDR, "ClaimGate (pre-publication)", ha="left", va="center")
    ax.plot([X_LABEL, W - MARGIN_R], [Y_SEP, Y_SEP], color=NEUTRAL_GRID, linewidth=0.3)

    # faint inter-row rules within each block
    for y0, n in ((Y_D1, 6), (Y_C1, 3)):
        for k in range(1, n):
            yy = y0 - k * ROW_H + ROW_H / 2
            ax.plot([X_LABEL, X_ANN - 1.5], [yy, yy], color=NEUTRAL_GRID,
                    linewidth=0.3, zorder=0)

    # rotated oracle group labels over contiguous same-oracle runs
    for block in ("decision", "claim"):
        block_rows = [r for r in ROWS if r[1] == block]
        i = 0
        while i < len(block_rows):
            j = i
            while j + 1 < len(block_rows) and block_rows[j + 1][2] == block_rows[i][2]:
                j += 1
            top = ys[block_rows[i][0]] + ROW_H / 2 - 0.6
            bot = ys[block_rows[j][0]] - ROW_H / 2 + 0.6
            oracle = block_rows[i][2]
            if top - bot >= rot_w[oracle] + 1.0:
                text(X_ROT_C, (top + bot) / 2, ORACLE_ROTATED[oracle],
                     ha="center", va="center", rotation=90)
            i = j + 1

    # rows: label, verdict tile (with SelfModel confidence where the gate
    # reports one), one-line annotation
    tiles = []        # verdict-tile bounds (x0, y0, x1, y1), mm
    conf_texts = []   # in-tile confidence labels (allowed inside a tile)
    for cid, _block, _oracle, label in ROWS:
        y = ys[cid]
        text(X_LABEL, y, label, ha="left", va="center")
        verdict = cells[cid]["actual_verdict"]
        x0 = X_COL[COL_KEYS.index(COL_OF_VERDICT[verdict])]
        ax.add_patch(plt.Rectangle((x0, y - TILE_H / 2), TILE_W, TILE_H,
                                   facecolor=VERDICT_COLOR[verdict],
                                   edgecolor="none", zorder=2))
        tiles.append((x0, y - TILE_H / 2, x0 + TILE_W, y + TILE_H / 2))
        conf = cells[cid]["detail"].get("confidence")
        if conf is not None:  # DecisionGate rows only; ClaimGate is rule-based
            conf_texts.append(text(x0 + TILE_W / 2, y, f"{conf:.1f}",
                                   ha="center", va="center"))
        text(X_ANN, y, annotation(cid, cells), ha="left", va="center")

    # verdict legend: one centred row under the panel (fig2i/fig4a convention)
    sw_w, sw_h, gap_k, pitch = 2.4, 1.6, 1.2, 3.0
    widths = [sw_w + gap_k + key_w[lab] for _c, lab in KEY_ITEMS]
    x = W / 2 - (sum(widths) + pitch * (len(KEY_ITEMS) - 1)) / 2
    for (colour, lab), w_it in zip(KEY_ITEMS, widths):
        ax.add_patch(plt.Rectangle((x, Y_LEG - sw_h / 2), sw_w, sw_h,
                                   facecolor=colour, edgecolor="none"))
        text(x + sw_w + gap_k, Y_LEG, lab, ha="left", va="center")
        x += w_it + pitch

    # post-draw audit: pure-black text, no text/text or text/tile-edge
    # overlap, everything on the canvas
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def bounds_mm(t) -> tuple[float, float, float, float]:
        bb = t.get_window_extent(renderer)
        return (bb.x0 / fig.dpi * 25.4, bb.y0 / fig.dpi * 25.4,
                bb.x1 / fig.dpi * 25.4, bb.y1 / fig.dpi * 25.4)

    def overlaps(a, b, tol: float = 0.15) -> bool:
        return (min(a[2], b[2]) - max(a[0], b[0]) > tol
                and min(a[3], b[3]) - max(a[1], b[1]) > tol)

    boxes = []
    for t in ax.texts:
        assert t.get_color() == INK, f"non-black text: {t.get_text()!r}"
        b = bounds_mm(t)
        assert b[0] >= 0 and b[2] <= W and b[1] >= 0 and b[3] <= H, (
            f"text off canvas: {t.get_text()!r}")
        boxes.append((t, b))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not overlaps(boxes[i][1], boxes[j][1]), (
                f"text overlap: {boxes[i][0].get_text()!r} x "
                f"{boxes[j][0].get_text()!r}")
    conf_ids = {id(t) for t in conf_texts}
    for t, b in boxes:
        for tl in tiles:
            if overlaps(b, tl):
                assert id(t) in conf_ids and (
                    b[0] >= tl[0] and b[2] <= tl[2]
                    and b[1] >= tl[1] and b[3] <= tl[3]
                ), f"text crosses a tile edge: {t.get_text()!r}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4e_selective_gating.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", pad_inches=0)
    plt.close(fig)
    print(f"fig4e -> {OUT_DIR / 'fig4e_selective_gating.pdf'} (+png 1200 dpi); "
          f"{n_met}/{len(cells)} frozen cells, all expectations met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
