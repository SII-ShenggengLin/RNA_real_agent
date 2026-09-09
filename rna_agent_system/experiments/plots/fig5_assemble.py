#!/usr/bin/env python3
"""Fig. 5 composite — assemble the eight finished panels (a–h) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–4, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned so the letters sit on one line per row.
Every panel carries the reset programme's single 6-pt text style, so
every panel is placed at scale 1.0 — no row is fit-scaled.

Layout (2026-09-08): all eight panels are 89 mm single-column renders on
the 183 mm Nature double-column content width (the fig3/fig4 composite
width). Row 1 pairs the two near-matched mRNA-campaign panels a (52 mm)
and b (56 mm) on the half-width column grid (the fig2/fig3 convention).
Row 2 places the tall delivery mosaic c (106 mm) on the left against a
right-column stack of d over e (35 + 58 mm — the fig4 stack convention
mirrored, so the short panels fill the row beside c instead of leaving a
blank band; reading order c → d → e is preserved). Row 3 closes with the
aptamer-campaign panels as the fig4 stack: f over h in the left column
(40 + 52.5 mm) against the decisive mosaic g (71.2 mm) on the right
(reading order f → g → h). The only residual blank is the bottom-right
corner under g, the conventional ragged bottom edge of a Nature
composite — no interior blank bands.

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed just above-left of each panel corner (Nature style — no period, no
brackets); drawn by this assembler, so they keep one size at any row scale.

Assembly preserves vectors: each panel PDF is embedded as a Form XObject
via PyMuPDF `show_pdf_page` (no rasterization); the PNG is rendered from
the finished composite at 1200 dpi (Nature Methods line-art minimum at
final print size).

Usage : python experiments/plots/fig5_assemble.py
Output : experiments/plots/output/fig5_composite.{pdf,png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

# Panel PDFs in lettering order — the standalone reset-programme panels.
PANELS: dict[str, str] = {
    "a": "fig5a_selection_pool_pass.pdf",
    "b": "fig5b_gennav_mcnemar.pdf",
    "c": "fig5c_delivery_mosaic.pdf",
    "d": "fig5d_secondary_endpoint.pdf",
    "e": "fig5e_campaign_arc_lollipop.pdf",
    "f": "fig5f_decisive_grouped_bars.pdf",
    "g": "fig5g_decisive_mosaic.pdf",
    "h": "fig5h_production_navigation_pareto.pdf",
}

# Row plan in strict reading order. "grid" centres each panel in its
# half-width column (the fig2/fig3 composite convention); "stack" piles the
# left-column letters top-to-bottom beside the single right-column panel
# (the fig4 convention); "stack_right" is the mirror — the single panel on
# the left, the letter stack in the right column — so a tall panel can sit
# beside two short ones without a blank band. Both stack modes join the
# columns by one COL_GAP and centre the whole block on the content width.
ROWS: list[tuple[str, object]] = [
    ("grid", ["a", "b"]),
    ("stack_right", ("c", ["d", "e"])),
    ("stack", (["f", "h"], "g")),
]

# Grid constants (PDF points) — identical to the fig2/fig3/fig4 composites.
CONTENT_W = 183.0 / 25.4 * 72   # Nature double column (fig3/fig4 width)
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

    content_w = CONTENT_W
    col_w = (content_w - COL_GAP) / 2.0

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, w, h) — all panels at scale 1.0 (uniform text scale).
    # Rows are top-aligned so the panel letters sit on one line per row.
    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for mode, spec in ROWS:
        row_placed: list[tuple[str, float, float, float, float]] = []
        if mode == "grid":
            letters = spec  # type: ignore[assignment]
            for col_idx, letter in enumerate(letters):
                w, h = sizes[letter]
                if w > col_w + 0.5:
                    raise ValueError(
                        f"panel {letter} width {w:.1f} breaks the grid "
                        f"(limit {col_w:.1f})"
                    )
                x0 = MARGIN_L + col_idx * (col_w + COL_GAP) + (col_w - w) / 2.0
                row_placed.append((letter, x0, y, w, h))
            row_h = max(p[4] for p in row_placed)
        elif mode == "stack":
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
        elif mode == "stack_right":
            left, col_letters = spec  # type: ignore[misc]
            col2_w = max(sizes[l][0] for l in col_letters)
            block_w = sizes[left][0] + COL_GAP + col2_w
            x1 = MARGIN_L + max(0.0, (content_w - block_w) / 2.0)
            wl, hl = sizes[left]
            row_placed.append((left, x1, y, wl, hl))
            x2 = x1 + wl + COL_GAP
            yy = y
            for letter in col_letters:
                w, h = sizes[letter]
                row_placed.append((letter, x2 + (col2_w - w) / 2.0, yy, w, h))
                yy += h + ROW_GAP
            stack_h = yy - ROW_GAP - y
            row_h = max(hl, stack_h)
        else:
            raise ValueError(f"unknown row mode {mode!r}")
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

    pdf_path = OUT_DIR / "fig5_composite.pdf"
    png_path = OUT_DIR / "fig5_composite.png"
    out.save(pdf_path, deflate=True, garbage=3)
    pix = page.get_pixmap(dpi=1200)
    pix.save(png_path)
    print(f"wrote {pdf_path} ({page_w:.1f} x {page_h:.1f} pt "
          f"= {page_w / 72 * 25.4:.1f} x {page_h / 72 * 25.4:.1f} mm)")
    print(f"wrote {png_path} ({pix.width} x {pix.height} px @ 1200 dpi)")


if __name__ == "__main__":
    main()
