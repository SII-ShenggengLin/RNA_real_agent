"""Fig 4e — selective gating decision matrix (Exp 23, §2.4 实验 4).

One tile per query condition: the two production gate layers reviewed the
MRL expression oracle and the 3'UTR stability oracle across certified /
never-profiled target families, and every verdict lands in exactly one
column. DecisionGate (pre-action, ranking-objective requests): allow on all
three Exp-14-certified families, downgrade (conservative transfer,
confidence 1.0 -> 0.5) on the never-profiled family, require_profiling for
the unprofiled 3'UTR oracle. ClaimGate (pre-publication, absolute-scope
claims): pass / downgrade to within-target relative / reject. Right-hand
annotations carry the SelfModel confidence and the tool-layer consequence
measured by the enforcement cells (E1 executed with the score reproducing
the Exp-14 cache; E2 executed; E3 blocked as GatedActionError before any
service call).

Colours (palette rev 7): sage = allow/pass, mauve grey = downgrade (the
fig2h gate-verdict convention: reject terracotta / require-profiling sand /
downgrade mauve), sand = require-profiling, terracotta = reject; oracle
strips grey blue = GEMORNA 5'UTR MRL (the fig3f oracle colour), dark warm
grey = GEMORNA 3'UTR stability.

Style (Nature conventions, the fig3/fig4 house style): no in-figure title;
every text element one 6-pt pure-black style; absolute-mm geometry; 1200-dpi
PNG + vector PDF (fonttype 42).

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
from palette import PALETTE_BY_NAME  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CELLS_JSONL = PROJECT_ROOT / "experiments" / "results" / "exp23_selective_gating" / "cells.jsonl"
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

INK = "#000000"
GRID = "#D9D9D3"
FONT = 6
CHAR_MM = 1.2  # conservative 6-pt glyph advance for fit checks (DejaVu Sans)

VERDICT_COLOR = {
    "allow": PALETTE_BY_NAME["sage_green"],
    "pass": PALETTE_BY_NAME["sage_green"],
    "downgrade": PALETTE_BY_NAME["mauve_grey"],
    "require_profiling": PALETTE_BY_NAME["sand"],
    "reject": PALETTE_BY_NAME["terracotta"],
}
ORACLE_STRIP = {
    "mrl": PALETTE_BY_NAME["grey_blue"],        # fig3f GEMORNA MRL oracle colour
    "utr3": PALETTE_BY_NAME["dark_warm_grey"],  # reserved neutral-dark semantic
}
ORACLE_ROTATED = {"mrl": "5′UTR MRL", "utr3": "3′UTR"}

COL_KEYS = ["allow_pass", "downgrade", "blocked"]
COL_HEADERS = {  # header lines, centred over each tile column
    "allow_pass": ["allow · pass"],
    "downgrade": ["downgrade"],
    "blocked": ["require-profiling", "· reject"],
}
COL_OF_VERDICT = {
    "allow": "allow_pass", "pass": "allow_pass",
    "downgrade": "downgrade",
    "require_profiling": "blocked", "reject": "blocked",
}

# mm geometry (canvas 120 x 72, y up; header-driven column pitch)
W, H = 120.0, 72.0
X_ROT_C = 3.4            # rotated oracle-label centre
X_STRIP0, STRIP_W = 5.0, 1.0
X_LABEL = 6.8            # row-label left edge (budget to 36.8 mm)
X_COL = [44.0, 58.5, 78.0]
TILE_W, TILE_H = 8.5, 3.4
X_ANN = 94.0             # annotation left edge (budget to 118 mm)
ROW_H = 4.8
Y_COLHDR = 68.0          # column-header centre (col3 two lines at +/-1.5)
Y_HDRRULE = 64.6
Y_DHDR = 62.4            # DecisionGate block header centre
Y_D1 = 57.8              # first DecisionGate row centre
Y_CHDR = 28.2            # ClaimGate block header centre
Y_CHDR_RULE = 25.6
Y_C1 = 21.4              # first ClaimGate row centre
Y_LEG = 4.2              # legend row centre

ROWS = [
    # cell, block, oracle, row label, annotation lines
    ("D1", "decision", "mrl", "certified · random-50",
     ["conf 1.0 · executed", "score = Exp-14"]),
    ("D2", "decision", "mrl", "certified · var-len random",
     ["conf 1.0", "not blocked"]),
    ("D3", "decision", "mrl", "certified · var-len human",
     ["conf 1.0", "not blocked"]),
    ("D4", "decision", "mrl", "never-profiled family",
     ["conf 0.5 = 1.0×0.5", "executed"]),
    ("D5", "decision", "utr3", "certified family",
     ["no anchor set", "blocked"]),
    ("D6", "decision", "utr3", "never-profiled family",
     ["no anchor set", "blocked"]),
    ("C1", "claim", "mrl", "MRL claim · certified",
     ["dep. verified", "scope absolute"]),
    ("C2", "claim", "mrl", "MRL claim · never-prof.",
     ["dep. transferred", "→ within-target"]),
    ("C3", "claim", "utr3", "3′UTR claim · never-prof.",
     ["dep. unprofiled", "no publishable basis"]),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": FONT,
    "text.color": INK,
    "pdf.fonttype": 42,
})


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

    fig = plt.figure(figsize=(W / 25.4, H / 25.4), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")

    def text(x, y, s, **kw):
        kw.setdefault("fontsize", FONT)
        kw.setdefault("color", INK)
        ax.text(x, y, s, **kw)

    ys = {}
    for i, (cid, block, _o, _l, _a) in enumerate(ROWS):
        ys[cid] = (Y_D1 - i * ROW_H) if block == "decision" else (Y_C1 - (i - 6) * ROW_H)

    # column headers (col3 stacked two lines) + light rule under them
    for key, x0 in zip(COL_KEYS, X_COL):
        cx = x0 + TILE_W / 2
        lines = COL_HEADERS[key]
        if len(lines) == 1:
            text(cx, Y_COLHDR, lines[0], ha="center", va="center")
        else:
            text(cx, Y_COLHDR + 1.5, lines[0], ha="center", va="center")
            text(cx, Y_COLHDR - 1.5, lines[1], ha="center", va="center")
    ax.plot([X_COL[0] - 1.0, X_COL[2] + TILE_W + 1.0],
            [Y_HDRRULE, Y_HDRRULE], color=GRID, linewidth=0.3)

    # block headers + block separator
    text(X_STRIP0, Y_DHDR, "DecisionGate — pre-action review", ha="left", va="center")
    text(X_STRIP0, Y_CHDR, "ClaimGate — pre-publication review", ha="left", va="center")
    ax.plot([X_STRIP0, W - 2.0], [Y_CHDR_RULE, Y_CHDR_RULE], color=INK, linewidth=0.4)

    # faint inter-row rules within each block
    for y0, n in ((Y_D1, 6), (Y_C1, 3)):
        for k in range(1, n):
            yy = y0 - k * ROW_H + ROW_H / 2
            ax.plot([X_STRIP0, X_ANN - 1.5], [yy, yy], color=GRID, linewidth=0.3, zorder=0)

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
            label = ORACLE_ROTATED[block_rows[i][2]]
            if top - bot >= len(label) * 1.05:
                text(X_ROT_C, (top + bot) / 2, label, ha="center", va="center", rotation=90)
            i = j + 1

    # rows: strip, label, tile, annotations
    for cid, _block, oracle, label, ann in ROWS:
        y = ys[cid]
        ax.add_patch(plt.Rectangle((X_STRIP0, y - TILE_H / 2), STRIP_W, TILE_H,
                                   facecolor=ORACLE_STRIP[oracle], edgecolor="none", zorder=2))
        text(X_LABEL, y, label, ha="left", va="center")
        verdict = cells[cid]["actual_verdict"]
        x0 = X_COL[COL_KEYS.index(COL_OF_VERDICT[verdict])]
        ax.add_patch(plt.Rectangle((x0, y - TILE_H / 2), TILE_W, TILE_H,
                                   facecolor=VERDICT_COLOR[verdict], edgecolor="none", zorder=2))
        if len(ann) == 1:
            text(X_ANN, y, ann[0], ha="left", va="center")
        else:
            text(X_ANN, y + 1.1, ann[0], ha="left", va="center")
            text(X_ANN, y - 1.1, ann[1], ha="left", va="center")

    # verdict key: one centred row under the panel (fig2i/fig4a convention)
    key_items = [
        (VERDICT_COLOR["allow"], "allow / pass"),
        (VERDICT_COLOR["downgrade"], "downgrade"),
        (VERDICT_COLOR["require_profiling"], "require-profiling"),
        (VERDICT_COLOR["reject"], "reject"),
    ]
    sw_w, sw_h, gap_k, pitch = 2.4, 1.6, 1.2, 3.0
    widths = [sw_w + gap_k + len(lab) * CHAR_MM for _c, lab in key_items]
    x = W / 2 - (sum(widths) + pitch * (len(key_items) - 1)) / 2
    for (colour, lab), w_it in zip(key_items, widths):
        ax.add_patch(plt.Rectangle((x, Y_LEG - sw_h / 2), sw_w, sw_h,
                                   facecolor=colour, edgecolor="none"))
        text(x + sw_w + gap_k, Y_LEG, lab, ha="left", va="center")
        x += w_it + pitch

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT_DIR / f"fig4e_selective_gating.{ext}", format=ext,
                    dpi=1200 if ext == "png" else None,
                    facecolor="white", pad_inches=0)
    plt.close(fig)
    print(f"fig4e -> {OUT_DIR / 'fig4e_selective_gating.pdf'} (+png 1200 dpi); "
          f"12 frozen cells, all expectations met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
