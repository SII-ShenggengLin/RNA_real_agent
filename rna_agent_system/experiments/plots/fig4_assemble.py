#!/usr/bin/env python3
"""Fig. 4 composite — assemble the ten finished panels (a–j) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–5, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned so the letters sit on one line per row.
Every panel carries the reset programme's single 6-pt text style, so
panels are placed at scale 1.0 unless a row must shrink to fit (the one
exception below).

Layout (2026-09-11, second same-day revision — the CapGate subsection merge,
user-directed: the selective-gating matrix panel moves up next to the
certification panel it operationalizes, b = selective gating):
row 1 pairs the subsection's two evidence-semantics panels — a (MRL
certification) and b (selective-gating matrix) — one equal-height fit row
(per-panel scales ≈ 1.15/0.73; the cert forest is drawn up and the matrix
down to the shared band height, the widest aspect spread of any fit row in
the figure set, accepted to keep the merged narrative on one band); row 2
pairs fidelity c with the gating headline d as a second equal-height fit
row (scales ≈ 0.95/0.84); row 3 pairs the tall claim matrix e with the
overreach panel f — f is the tall-layout render
(`FIG4F_LAYOUT=tall python experiments/plots/fig4f_overreach_events.py`,
same frozen data, axes stretched vertically, no data change — the fig3c
composite-layout convention) — top-aligned at scale 1.0, the ≈ 39 mm band
under f the row's accepted underhang (the claim matrix is the tallest
panel in the figure and no in-order partner matches its 105 mm height;
the previous composite's stack workaround needed the headline panel,
which now fills row 2). Row 4 pairs the campaign panels g (mRNA family
strip) and h (production gate decisions) as one centred group at scale
1.0 (≈ 16 mm underhang under h, the previous composite's accepted
group-row underhang). Rows 5–6 close with the two wide strips at native
scale — the 31-session quality strip i and the LLM-usage strip j — each
centred on the content width (the fig2 full-span convention; the pair no
longer shares a fit row because h moved up to row 4, and a shared fit
band would shrink both to ≈ 0.6×). Content width = 183 mm
(Nature double column, the fig3 composite width); every gutter is one
COL_GAP.

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed just above-left of each panel corner (Nature style — no period, no
brackets); drawn by this assembler, so they keep one size at any row scale.

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
# file names (the 2026-09-11 first re-lettering had moved a/b in from
# Fig. 3's 3g/3h and shifted the gating panels +2; frozen data files keep
# their as-written names).
PANELS: dict[str, str] = {
    "a": "fig4a_mrl_certification.pdf",
    "b": "fig4b_selective_gating.pdf",
    "c": "fig4c_rnasmol_fidelity.pdf",
    "d": "fig4d_claim_gating.pdf",
    "e": "fig4e_claim_matrix.pdf",
    "f": "fig4f_overreach_events_tall.pdf",
    "g": "fig4g_mrna_family_strip.pdf",
    "h": "fig4h_gate_decisions.pdf",
    "i": "fig4i_quality_advisory_strip.pdf",
    "j": "fig4j_llm_usage_bubble.pdf",
}

# Row plan in strict reading order. "stack" piles the left-column letters
# top-to-bottom (one ROW_GAP between them, each centred on the column
# centreline) beside the single right-column panel, the two columns joined
# by one COL_GAP and the whole block centred on the content width; "group"
# places the letters left to right with one COL_GAP between them, the whole
# row centred; "fit" draws the whole row at one equal height and lets the
# leftover width become the gutter (the fig2/fig3 fgh-row convention);
# "full" centres one panel on the content width.
ROWS: list[tuple[str, object]] = [
    ("fit", ["a", "b"]),
    ("fit", ["c", "d"]),
    ("group", ["e", "f"]),
    ("group", ["g", "h"]),
    ("full", ["i"]),
    ("full", ["j"]),
]

# Grid constants (PDF points) — identical to the fig2/fig3 composites.
CONTENT_W = 183.0 / 25.4 * 72   # Nature double column (fig3 composite width)
COL_GAP = 11.0
ROW_GAP = 16.0          # hosts the 8 pt label band above each row
MARGIN_L = 14.0         # labels hang 11 pt left of their panel
MARGIN_R = 6.0
MARGIN_T = 12.0         # label band for row 1
MARGIN_B = 8.0
LABEL_SIZE = 8.0
LABEL_DX = -11.0        # letter anchor relative to the panel corner
LABEL_DY = -4.0         # baseline this far above the panel top edge
INK = tuple(int(TEXT[i : i + 2], 16) / 255 for i in (1, 3, 5))


def main() -> None:
    # every lettered panel must be placed exactly once (guards the row plan
    # against dropped panels when letters shift)
    placed_letters: list[str] = []
    for mode, spec in ROWS:
        if mode == "stack":
            col_letters, right = spec  # type: ignore[misc]
            placed_letters.extend([*col_letters, right])
        else:
            placed_letters.extend(spec)  # type: ignore[arg-type]
    assert sorted(placed_letters) == sorted(PANELS), (
        f"row plan places {sorted(placed_letters)} but panels are {sorted(PANELS)}"
    )

    sources: dict[str, fitz.Document] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for letter, name in PANELS.items():
        doc = fitz.open(OUT_DIR / name)
        sources[letter] = doc
        r = doc[0].rect
        sizes[letter] = (r.width, r.height)

    content_w = CONTENT_W

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, w, h). Rows are top-aligned so the panel letters sit
    # on one line per row.
    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for mode, spec in ROWS:
        row_placed: list[tuple[str, float, float, float, float]] = []
        if mode == "stack":
            col_letters, right = spec  # type: ignore[misc]
            col1_w = max(sizes[l][0] for l in col_letters)
            block_w = col1_w + COL_GAP + sizes[right][0]
            x1 = MARGIN_L + max(0.0, (content_w - block_w) / 2.0)
            yy = y
            for letter in col_letters:
                w, h = sizes[letter]
                row_placed.append((letter, x1 + (col1_w - w) / 2.0, yy, w, h))
                yy += h + ROW_GAP
            stack_h = yy - ROW_GAP - y
            wr, hr = sizes[right]
            row_placed.append((right, x1 + col1_w + COL_GAP, y, wr, hr))
            row_h = max(stack_h, hr)
        elif mode == "group":
            letters = spec  # type: ignore[assignment]
            total = sum(sizes[l][0] for l in letters) + COL_GAP * (len(letters) - 1)
            x = MARGIN_L + max(0.0, (content_w - total) / 2.0)
            for letter in letters:
                w, h = sizes[letter]
                row_placed.append((letter, x, y, w, h))
                x += w + COL_GAP
            row_h = max(p[4] for p in row_placed)
        elif mode == "fit":
            # Equal-size row (the fig2/fig3 fgh-row convention): one drawn
            # height for every panel, so the row reads as a band of
            # identical panels. Per-panel scales differ — the aspects
            # differ — so widths vary slightly; leftover width becomes the
            # gutter. Height = the median panel height at the uniform fit
            # scale, so no panel is squeezed to the smallest one's
            # proportions.
            letters = spec  # type: ignore[assignment]
            n = len(letters)
            s0 = (content_w - (n - 1) * COL_GAP) / sum(sizes[l][0] for l in letters)
            row_h = sorted(sizes[l][1] * s0 for l in letters)[n // 2]
            total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l in letters)
            gap = (content_w - total_w) / (n - 1)
            if gap < 6.0:  # keep the gutters sane if aspects ever widen
                row_h *= (content_w - (n - 1) * 6.0) / total_w
                total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l in letters)
                gap = (content_w - total_w) / (n - 1)
            x = MARGIN_L + max(0.0, (content_w - total_w - (n - 1) * gap) / 2.0)
            for letter in letters:
                w, h = sizes[letter]
                s = row_h / h
                row_placed.append((letter, x, y, w * s, h * s))
                x += w * s + gap
        else:  # full
            (letter,) = spec  # type: ignore[misc]
            w, h = sizes[letter]
            x0 = MARGIN_L + max(0.0, (content_w - w) / 2.0)
            row_placed.append((letter, x0, y, w, h))
            row_h = h
        placed.extend(row_placed)
        y += row_h + ROW_GAP

    page_w = MARGIN_L + content_w + MARGIN_R
    page_h = y - ROW_GAP + MARGIN_B

    out = fitz.open()
    page = out.new_page(width=page_w, height=page_h)
    for letter, x0, y0, w, h in placed:
        page.show_pdf_page(fitz.Rect(x0, y0, x0 + w, y0 + h), sources[letter], 0)
        page.insert_text(
            (x0 + LABEL_DX, y0 + LABEL_DY),
            letter,
            fontname="hebo",
            fontsize=LABEL_SIZE,
            color=INK,
        )

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
