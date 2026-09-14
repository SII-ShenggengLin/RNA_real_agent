#!/usr/bin/env python3
"""Fig. 6 composite — assemble the four baseline-comparison panels (a–d).

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (bold lowercase panel letters at the top-left corner,
strict reading order, rows top-aligned).  Every panel is an 89-mm
single-column render at scale 1.0 (uniform text scale).

Layout: row 1 pairs the tall delivery mosaic a (92 mm) with the failure-
mode decomposition b (50 mm) on the half-width column grid (the fig2/fig3
convention); row 2 pairs the claim adjudication c (50 mm) with the
cost-delivery frontier d (50 mm).

Letters: Helvetica-Bold 8 pt, ink black, drawn by this assembler.

Assembly preserves vectors (PyMuPDF Form XObjects); the PNG renders from
the finished composite at 1200 dpi.

Usage : python experiments/plots/fig6_assemble.py
Output : experiments/plots/output/fig6_composite.{pdf,png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

PANELS: dict[str, str] = {
    "a": "fig6a_baseline_delivery_mosaic.pdf",
    "b": "fig6b_failure_modes.pdf",
    "c": "fig6c_claims.pdf",
    "d": "fig6d_cost_delivery.pdf",
}

ROWS: list[tuple[str, object]] = [
    ("grid", ["a", "b"]),
    ("grid", ["c", "d"]),
]

CONTENT_W = 183.0 / 25.4 * 72   # Nature double column (the fig3-5 width)
COL_GAP = 11.0
ROW_GAP = 16.0
MARGIN_L = 14.0
MARGIN_R = 6.0
MARGIN_T = 12.0
MARGIN_B = 8.0
LABEL_SIZE = 8.0
LABEL_DX = -11.0
LABEL_DY = -4.0
INK = tuple(int(TEXT[i:i + 2], 16) / 255 for i in (1, 3, 5))


def main() -> None:
    sources: dict[str, fitz.Document] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for letter, name in PANELS.items():
        doc = fitz.open(OUT_DIR / name)
        sources[letter] = doc
        r = doc[0].rect
        sizes[letter] = (r.width, r.height)

    content_w = CONTENT_W
    col_w = (content_w - COL_GAP) / 2.0

    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for mode, spec in ROWS:
        row_placed: list[tuple[str, float, float, float, float]] = []
        assert mode == "grid"
        for col_idx, letter in enumerate(spec):  # type: ignore[union-attr]
            w, h = sizes[letter]
            if w > col_w + 0.5:
                raise ValueError(
                    f"panel {letter} width {w:.1f} breaks the grid "
                    f"(limit {col_w:.1f})"
                )
            x0 = MARGIN_L + col_idx * (col_w + COL_GAP) + (col_w - w) / 2.0
            row_placed.append((letter, x0, y, w, h))
        row_h = max(p[4] for p in row_placed)
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

    pdf_path = OUT_DIR / "fig6_composite.pdf"
    png_path = OUT_DIR / "fig6_composite.png"
    out.save(pdf_path, deflate=True, garbage=3)
    pix = page.get_pixmap(dpi=1200)
    pix.save(png_path)
    print(f"wrote {pdf_path} ({page_w:.1f} x {page_h:.1f} pt "
          f"= {page_w / 72 * 25.4:.1f} x {page_h / 72 * 25.4:.1f} mm)")
    print(f"wrote {png_path} ({pix.width} x {pix.height} px @ 1200 dpi)")


if __name__ == "__main__":
    main()
