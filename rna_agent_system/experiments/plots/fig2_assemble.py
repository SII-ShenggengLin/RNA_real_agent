#!/usr/bin/env python3
"""Fig. 2 composite — assemble the eight finished panels (a–h) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare Fig. 2 / Fig. 4): bold lowercase panel
letters at the top-left corner of each panel, panels packed onto a strict
column grid, rows top-aligned so the letters sit on one line per row.
Every panel carries the reset programme's single 6-pt ink-black text
style, so all panels share one scale unless a row must shrink to fit.

Layout (2026-09-11, user-directed re-lettering): the former panel e (IRES
literature-panel ROC) moved out of Fig. 2 to Supplementary Fig. S3
(`figS3_ires_panel.py`, same frozen data and rendering); the former f–i
panels are re-lettered e–h. a (tile carpet) spans the full width; b c,
d e and f g flow two per row at scale 1.0, each centred in its column —
with only two panels left on the old f g h equal-height "fit" row, that
row reverts to the standard two-per-row convention, so every panel now
draws at its natural size on one uniform text scale; h (ECDF) closes the
figure full width. The composite reads in strict lettering order a → h.
(The generic "fit" row machinery below is retained but currently unused.)

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (#1A1A1A),
placed just above-left of each panel corner (Nature style — no period,
no brackets); drawn by this assembler, so they keep one size at any row
scale.

Assembly preserves vectors: each panel PDF is embedded as a Form XObject
via PyMuPDF `show_pdf_page` (no rasterization); the PNG is rendered from
the finished composite at 1200 dpi (Nature Methods line-art minimum at
final print size).

Usage : python experiments/plots/fig2_assemble.py
Output : experiments/plots/output/fig2_composite.{pdf,png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

# Panel PDFs in lettering order.
PANELS: dict[str, str] = {
    "a": "fig2a_coverage.pdf",
    "b": "fig2b_cai.pdf",
    "c": "fig2c_mfe_per_nt.pdf",
    "d": "fig2d_inverse_folding.pdf",
    "e": "fig2e_sirna_offtarget.pdf",
    "f": "fig2f_rnasmol_boundary.pdf",
    "g": "fig2g_audit_trail.pdf",
    "h": "fig2h_runtime_ecdf.pdf",
}

# Row plan: (panels, scale). Panels are (letter, span) with span 2 =
# full content width, 1 = one column. scale 1.0 keeps the panel's natural
# size (uniform text scale across rows); "fit" shrinks the whole row so
# its panels plus column gaps fill the content width exactly.
ROWS: list[tuple[list[tuple[str, int]], float | str]] = [
    ([("a", 2)], 1.0),
    ([("b", 1), ("c", 1)], 1.0),
    ([("d", 1), ("e", 1)], 1.0),
    ([("f", 1), ("g", 1)], 1.0),
    ([("h", 2)], 1.0),
]

# Grid constants (PDF points).
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
    sources: dict[str, fitz.Document] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for letter, name in PANELS.items():
        doc = fitz.open(OUT_DIR / name)
        sources[letter] = doc
        r = doc[0].rect
        sizes[letter] = (r.width, r.height)

    content_w = max(
        sizes[letter][0]
        for row, _ in ROWS
        for letter, span in row
        if span == 2
    )
    col_w = (content_w - COL_GAP) / 2.0

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, scaled_w, scaled_h). Rows are top-aligned.
    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for row, scale in ROWS:
        if scale == "fit":
            # Equal-size row: one drawn height for every panel, so the row
            # reads as a band of identical panels (user-directed: f's
            # squarer aspect made it look bigger than g/i at a uniform
            # scale). Per-panel scales differ — the aspects differ — so
            # widths vary slightly; leftover width becomes even gutters.
            # Height = the median panel height at the uniform fit scale,
            # so no panel is squeezed to the smallest one's proportions.
            n = len(row)
            s0 = (content_w - (n - 1) * COL_GAP) / sum(sizes[l][0] for l, _ in row)
            row_h = sorted(sizes[l][1] * s0 for l, _ in row)[n // 2]
            total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l, _ in row)
            gap = (content_w - total_w) / (n - 1)
            if gap < 6.0:  # keep the gutters sane if aspects ever widen
                row_h *= (content_w - (n - 1) * 6.0) / total_w
                total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l, _ in row)
                gap = (content_w - total_w) / (n - 1)
            x = MARGIN_L
            row_placed = []
            for letter, _span in row:
                w, h = sizes[letter]
                s = row_h / h
                row_placed.append((letter, x, y, w * s, h * s))
                x += w * s + gap
        else:
            row_placed = []
            for col_idx, (letter, span) in enumerate(row):
                w, h = sizes[letter]
                limit = content_w if span == 2 else col_w
                if w > limit + 0.5:
                    raise ValueError(
                        f"panel {letter} width {w:.1f} breaks the grid (limit {limit:.1f})"
                    )
                if span == 2:
                    x0 = MARGIN_L + (content_w - w) / 2.0
                else:
                    x0 = MARGIN_L + col_idx * (col_w + COL_GAP) + (col_w - w) / 2.0
                row_placed.append((letter, x0, y, w, h))
        placed.extend(row_placed)
        y += max(p[4] for p in row_placed) + ROW_GAP

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

    pdf_path = OUT_DIR / "fig2_composite.pdf"
    png_path = OUT_DIR / "fig2_composite.png"
    out.save(pdf_path, deflate=True, garbage=3)
    pix = page.get_pixmap(dpi=1200)
    pix.save(png_path)
    print(f"wrote {pdf_path} ({page_w:.1f} x {page_h:.1f} pt)")
    print(f"wrote {png_path} ({pix.width} x {pix.height} px)")


if __name__ == "__main__":
    main()
