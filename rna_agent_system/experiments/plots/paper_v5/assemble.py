"""Composite-figure assembly for paper_v5.

Each figure directory contains one script per panel (exporting ``panels/<letter>.pdf``
+ ``.png``) and an ``assemble.py`` that builds the figure layout. Panel scripts
create their figures at the exact grid-cell size specified in
``docs/FIGURE_PLAN_V5.md``, so assembly is a lossless 1:1 placement: the bold
lowercase panel letters (Nature style) are drawn here and only here.

Exports both ``figN.png`` (450 dpi proof) and ``figN.pdf`` (vector composite).
"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

MM = 72.0 / 25.4                     # PDF points per mm
LETTER_FONT = "Helvetica-Bold"       # metric twin of Arial Bold
INK_RGB = (0.231, 0.275, 0.329)      # style.INK as rgb tuple


def _ink_rgb() -> tuple[float, float, float]:
    sys.path.insert(0, str(HERE.parent))
    from style import INK
    ink = INK.lstrip("#")
    return tuple(int(ink[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def assemble(figure_dir: Path, layout: list[tuple[str, tuple[int, int, int, int]]],
             page_w_mm: float = 183.0, letter_pt: float = 10,
             gap_mm: float = 3.0, margins_mm: float = 5.0, pad_top_mm: float = 4.0,
             out_name: str | None = None) -> None:
    """Compose panels into one figure page.

    ``layout`` lists ``(letter, (row, col, rowspan, colspan))`` on a dense grid.
    Cell sizes are read from the actual panel PDFs (row height = tallest panel
    of the row, col width = widest of the column), the grid is uniformly scaled
    to fit the page width, and panels are placed aspect-preserved.
    """
    pages = {}
    for letter, _ in layout:
        p = figure_dir / "panels" / f"{letter}.pdf"
        if not p.exists():
            raise FileNotFoundError(f"missing panel PDF {p} - run its script first")
        doc = fitz.open(p)
        pages[letter] = (p, doc[0].rect.width / MM, doc[0].rect.height / MM)
        doc.close()

    rows = sorted({pos[0] for _, pos in layout})
    cols = sorted({pos[1] for _, pos in layout})
    row_of = {r: i for i, r in enumerate(rows)}
    col_of = {c: i for i, c in enumerate(cols)}
    n_row, n_col = len(rows), len(cols)
    row_h = [0.0] * n_row
    col_w = [0.0] * n_col
    for letter, (r, c, rs, cs) in layout:
        _, w, h = pages[letter]
        ri, ci = row_of[r], col_of[c]
        nr = max(rs, 1)
        nc = max(cs, 1)
        for k in range(nr):
            row_h[ri + k] = max(row_h[ri + k], h / nr)
        for k in range(nc):
            col_w[ci + k] = max(col_w[ci + k], w / nc)

    gap = gap_mm
    grid_w = sum(col_w) + gap * (n_col - 1)
    grid_h = sum(row_h) + gap * (n_row - 1)
    avail_w = page_w_mm - 2 * margins_mm
    scale = min(avail_w / grid_w, 1.0)
    col_w = [w * scale for w in col_w]
    row_h = [h * scale for h in row_h]
    gap *= scale
    grid_w = sum(col_w) + gap * (n_col - 1)
    grid_h = sum(row_h) + gap * (n_row - 1)
    ox = margins_mm
    oy = margins_mm + pad_top_mm

    page_h_mm = grid_h + 2 * margins_mm + pad_top_mm
    out = fitz.open()
    page = out.new_page(width=page_w_mm * MM, height=page_h_mm * MM)
    for letter, (r, c, rs, cs) in layout:
        _, w, h = pages[letter]
        ri, ci = row_of[r], col_of[c]
        nr, nc = max(rs, 1), max(cs, 1)
        x0 = ox + sum(col_w[:ci]) + gap * ci
        y0 = oy + sum(row_h[:ri]) + gap * ri
        cw = sum(col_w[ci:ci + nc]) + gap * (nc - 1)
        ch = sum(row_h[ri:ri + nr]) + gap * (nr - 1)
        # centre the (aspect-preserved) panel inside its cell
        s = min(cw / w, ch / h)
        pw, ph = w * s, h * s
        rect = fitz.Rect((x0 + (cw - pw) / 2) * MM, (y0 + (ch - ph) / 2) * MM,
                         (x0 + (cw + pw) / 2) * MM, (y0 + (ch + ph) / 2) * MM)
        doc = fitz.open(pages[letter][0])
        page.show_pdf_page(rect, doc, 0, keep_proportion=True)
        doc.close()

    ink = _ink_rgb()
    for letter, (r, c, rs, cs) in layout:
        ri, ci = row_of[r], col_of[c]
        x0 = ox + sum(col_w[:ci]) + gap * ci
        y0 = oy + sum(row_h[:ri]) + gap * ri
        fs = letter_pt
        tw = fitz.get_text_length(letter, fontname=LETTER_FONT, fontsize=fs) / MM
        page.insert_text(fitz.Point(x0 - tw / 2, y0 + fs / MM * 0.9), letter,
                         fontname=LETTER_FONT, fontsize=fs, color=ink)

    name = out_name or figure_dir.name
    out.save(figure_dir.parent / f"{name}.pdf", garbage=4, deflate=True)
    pix = page.get_pixmap(dpi=450)
    pix.save(figure_dir.parent / f"{name}.png")
    out.close()
    print(f"assembled {figure_dir.name}: {page_w_mm:.0f} x {page_h_mm:.0f} mm")


def run_all() -> None:
    import runpy
    for figdir in sorted(HERE.glob("fig*")):
        asm = figdir / "assemble.py"
        if asm.exists():
            print(f"== {figdir.name} ==")
            runpy.run_path(str(asm), run_name="__main__")


if __name__ == "__main__":
    run_all()
