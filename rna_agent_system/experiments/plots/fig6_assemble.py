#!/usr/bin/env python3
"""Fig. 6 composite — assemble the four baseline-comparison panels (a–d).

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (bold lowercase panel letters at the top-left corner,
strict reading order, rows top-aligned).  Every panel is rendered at scale
1.0 (uniform 6-pt text across the figure).

Layout (2026-09-14 user-directed re-arrangement, the compact form): the
tall delivery mosaic a (89 x 109 mm) fills the full-height left column;
the right block (90.1 mm) stacks the failure-mode decomposition b
(89 x 50.5 mm) on top and pairs the claim adjudication c with the
cost-delivery frontier d (43.1 x 55 mm each) side by side below it, the
c/d row bottom-aligned with a.

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

CONTENT_W = 183.0 / 25.4 * 72   # Nature double column (the fig3-5 width)
COL_GAP = 11.0
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
    a_w, a_h = sizes["a"]
    b_w, b_h = sizes["b"]
    c_w, c_h = sizes["c"]
    d_w, d_h = sizes["d"]

    x0_right = MARGIN_L + a_w + COL_GAP
    w_right = content_w - a_w - COL_GAP
    assert b_w <= w_right + 0.5, f"panel b {b_w:.1f} exceeds the right block {w_right:.1f}"
    assert c_w + COL_GAP + d_w <= w_right + 0.5, \
        f"panels c+d {c_w + COL_GAP + d_w:.1f} exceed the right block {w_right:.1f}"
    assert abs(c_h - d_h) < 0.5, f"panels c/d heights differ: {c_h:.1f} vs {d_h:.1f}"
    row2_y = MARGIN_T + a_h - c_h  # the c/d row bottom-aligned with a
    assert row2_y >= MARGIN_T + b_h + 8.0, "no real gap between b and the c/d row"

    placed = [
        ("a", MARGIN_L, MARGIN_T, a_w, a_h),
        ("b", x0_right + (w_right - b_w) / 2.0, MARGIN_T, b_w, b_h),
        ("c", x0_right, row2_y, c_w, c_h),
        ("d", x0_right + c_w + COL_GAP, row2_y, d_w, d_h),
    ]

    page_w = MARGIN_L + content_w + MARGIN_R
    page_h = MARGIN_T + a_h + MARGIN_B

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
