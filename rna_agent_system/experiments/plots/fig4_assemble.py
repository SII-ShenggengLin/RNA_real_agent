#!/usr/bin/env python3
"""Fig. 4 composite — assemble the eight finished panels (a–h) into one figure.

2026-10-02 cut to a–h (figure-backlog batch, registered 2026-09-28): the
governance-ablation paragraph moved from section 2.4 to Supplementary
Note 3, so the quality-advisory strip (former i) and the LLM-usage strip
(former j) migrated to Supplementary Figs. S5/S6
(`figS5_advisory_strip.py`, `figS6_llm_usage_bubble.py`); rows 5–6
retired with them. No remaining panel changed.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–5, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned so the letters sit on one line per row.

2026-10-10 composite-grid batch (user-directed row/column alignment): the
former "fit"/"group" row machinery is retired — it fit-scaled each row to
the content width, so the sibling panels rendered at different text sizes
(panel b at 73%, panel d at 146%) and the second column's left edges
trailed by up to 32 mm across rows. Every panel now re-renders on an
exact cell of a strict two-column grid (see the panel scripts) and this
assembler places them all at scale 1.0, so the 6-pt text size, every row's
top and bottom edges, every column's left and right edges, and the panel
letters' per-row baselines and per-column x positions all align:

    column 1 (a, c, e, g)   82.5 mm
    gutter                   4.0 mm
    column 2 (b, d, f, h)   96.5 mm
                             ------
    content width          183.0 mm  (Nature double column)
    row heights            72.0 / 50.0 / 66.2 / 72.4 mm

Rows pair the subsection's evidence-semantics panels a|b, fidelity c with
the gating headline d, the aptamer verdict bars e with the overreach
events f (the tall-layout render, `FIG4F_LAYOUT=tall python
experiments/plots/fig4f_overreach_events.py`, same frozen data — the
fig3c composite-layout convention), and the mRNA verdict bars g with the
production gate verdicts h. A per-panel assert pins every panel PDF to
its grid cell (±0.05 mm), so a drifted render fails the assembly.

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed up-left of each panel corner (Nature style — no period, no
brackets). 2026-10-10 tightening (user-directed, the fig5 convention):
each ROW's letters share one baseline placed ~0.7 mm above the row's
highest first-ink row (detected on each panel's own 1200-dpi PNG), so no
letter floats far above blank canvas bands; 'g' carries a descender,
compensated so its glyph bottom — not its baseline — clears the ink.
Column 1 letters hang the classic 11 pt left of their panels (into the
page margin); column 2 letters hang only 1.5 mm (user-directed: the 4-mm
grid gutter is too narrow for the classic hang — the letters read as
belonging to the previous column), keeping one x per column. A
post-placement assert pins every letter's glyph bottom 0.3–12 mm above
its panel's first ink.

Assembly preserves vectors: each panel PDF is embedded as a Form XObject
via PyMuPDF `show_pdf_page` (no rasterization); the PNG is rendered from
the finished composite at 1200 dpi (Nature Methods line-art minimum at
final print size).

Usage : python experiments/plots/fig4_assemble.py
Output : experiments/plots/output/fig4_composite.{pdf,png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

# Panel PDFs in lettering order. Panel f is the tall-layout render (see the
# module docstring); all other panels are the standalone reset-programme
# panels. Re-lettered 2026-09-11 (user-directed, the CapGate-subsection
# merge): the selective-gating matrix moves from g to b, next to the MRL
# certification panel (a) whose capability grades it exercises; fidelity
# b→c, headline c→d, claim matrix d→e, overreach e→f, mRNA strip f→g;
# h/i/j keep their letters. No panel content changed, only letters and
# file names. 2026-10-02: i/j left for Supplementary Figs. S5/S6 (see the
# module docstring); a–h unchanged.
PANELS: dict[str, str] = {
    "a": "fig4a_mrl_certification.pdf",
    "b": "fig4b_selective_gating.pdf",
    "c": "fig4c_rnasmol_fidelity.pdf",
    "d": "fig4d_claim_gating.pdf",
    "e": "fig4e_claim_verdict_bars.pdf",
    "f": "fig4f_overreach_events_tall.pdf",
    "g": "fig4g_mrna_verdict_bars.pdf",
    "h": "fig4h_gate_decisions.pdf",
}

# The strict two-column grid (mm): rows in reading order, each row one
# shared canvas height, both columns one shared width each — every panel
# drawn at scale 1.0 (the fig5 "grid" convention, hardened to equal
# heights and asserted cell sizes).
MM = 25.4 / 72
COL1_W, COL2_W, COL_GAP_MM = 82.5, 96.5, 4.0
ROWS: list[tuple[str, str, float]] = [   # (left letter, right letter, row height mm)
    ("a", "b", 72.0),
    ("c", "d", 50.0),
    ("e", "f", 66.2),
    ("g", "h", 72.4),
]
COL_W = {0: COL1_W, 1: COL2_W}

# Grid constants (PDF points) — the fig2/fig3/fig4 composite frame.
CONTENT_W = (COL1_W + COL_GAP_MM + COL2_W) * 72 / 25.4   # = 183 mm
COL_GAP = COL_GAP_MM * 72 / 25.4
ROW_GAP = 16.0          # hosts the 8 pt label band above each row
MARGIN_L = 14.0         # labels hang 11 pt left of their panel
MARGIN_R = 6.0
MARGIN_T = 12.0         # label band for row 1
MARGIN_B = 8.0
LABEL_SIZE = 8.0
LETTER_GAP_PT = 2.0     # glyph bottom → panel first-ink clearance (~0.7 mm)
DESCENT_PT = {"g": 2.0}  # Helvetica-Bold descender at 8 pt (letters a-f/h sit
                         # on the baseline; only g dips below it)
SIZE_TOL = 0.05 * 72 / 25.4   # panel-vs-cell tolerance (0.05 mm)
INK = tuple(int(TEXT[i : i + 2], 16) / 255 for i in (1, 3, 5))


def first_ink_pt(png: Path) -> float:
    """Distance (pt) from a panel PNG's top edge to its first ink row —
    the panel's own top blank band, measured on the 1200-dpi raster."""
    import numpy as np
    from PIL import Image

    img = np.asarray(Image.open(png).convert("L"))
    inked = (img < 250).any(axis=1)
    assert inked.any(), f"blank raster: {png}"
    return float(np.argmax(inked)) / 1200.0 * 72.0


def main() -> None:
    # every lettered panel must be placed exactly once (guards the row plan
    # against dropped panels when letters shift)
    placed_letters: list[str] = [l for row in ROWS for l in row[:2]]
    assert sorted(placed_letters) == sorted(PANELS), (
        f"row plan places {sorted(placed_letters)} but panels are {sorted(PANELS)}"
    )

    sources: dict[str, fitz.Document] = {}
    for letter, name in PANELS.items():
        sources[letter] = fitz.open(OUT_DIR / name)

    # strict grid: every panel must match its cell exactly (a drifted
    # render fails the assembly instead of silently scaling)
    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for left, right, row_h_mm in ROWS:
        row_h = row_h_mm * 72 / 25.4
        for col_idx, letter in enumerate((left, right)):
            r = sources[letter][0].rect
            cell_w = COL_W[col_idx] * 72 / 25.4
            assert abs(r.width - cell_w) <= SIZE_TOL, (
                f"panel {letter} width {r.width / 72 * 25.4:.2f} mm "
                f"!= cell {COL_W[col_idx]:.2f} mm")
            assert abs(r.height - row_h) <= SIZE_TOL, (
                f"panel {letter} height {r.height / 72 * 25.4:.2f} mm "
                f"!= row {row_h_mm:.2f} mm")
            x0 = MARGIN_L + sum(COL_W[c] * 72 / 25.4 for c in range(col_idx)) \
                + col_idx * COL_GAP
            placed.append((letter, x0, y, r.width, r.height))
        y += row_h + ROW_GAP

    page_w = MARGIN_L + CONTENT_W + MARGIN_R
    page_h = y - ROW_GAP + MARGIN_B

    out = fitz.open()
    page = out.new_page(width=page_w, height=page_h)
    ink_offsets = {letter: first_ink_pt(OUT_DIR / name.replace(".pdf", ".png"))
                   for letter, name in PANELS.items()}
    pos = {letter: (x0, y0, w, h) for letter, x0, y0, w, h in placed}
    # one letter baseline per row (the fig5 convention): the line sits
    # LETTER_GAP_PT above the row's HIGHEST first-ink row, so the letters
    # share one horizontal line while hugging the row's content. Column 1
    # letters hang the classic 11 pt into the page margin; column 2 letters
    # hang 1.5 mm (the 4-mm grid gutter cannot host the classic hang).
    for left, right, _row_h in ROWS:
        for letter in (left, right):
            x0, y0, w, h = pos[letter]
            page.show_pdf_page(fitz.Rect(x0, y0, x0 + w, y0 + h),
                               sources[letter], 0)
            label_dx = -11.0 if letter == left else -1.5 * 72 / 25.4
            descent = DESCENT_PT.get(letter, 0.0)
            baseline_y = y0 + min(ink_offsets[left], ink_offsets[right]) \
                - LETTER_GAP_PT - descent
            page.insert_text(
                (x0 + label_dx, baseline_y),
                letter,
                fontname="hebo",
                fontsize=LABEL_SIZE,
                color=INK,
            )
            glyph_bottom = baseline_y + descent
            gap_mm = (y0 + ink_offsets[letter] - glyph_bottom) / 72 * 25.4
            assert 0.3 <= gap_mm <= 12.0, \
                f"letter {letter} sits {gap_mm:.2f} mm from its panel's ink"

    pdf_path = OUT_DIR / "fig4_composite.pdf"
    png_path = OUT_DIR / "fig4_composite.png"
    out.save(pdf_path, deflate=True, garbage=3)
    pix = page.get_pixmap(dpi=1200)
    pix.save(png_path)
    print(f"wrote {pdf_path} ({page_w:.1f} x {page_h:.1f} pt "
          f"= {page_w / 72 * 25.4:.1f} x {page_h / 72 * 25.4:.1f} mm)")
    print(f"wrote {png_path} ({pix.width} x {pix.height} px @ 1200 dpi)")


if __name__ == "__main__":
    main()
