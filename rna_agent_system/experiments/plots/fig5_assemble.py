#!/usr/bin/env python3
"""Fig. 5 composite — assemble the seven finished panels (a–g) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–4, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned. Every panel carries the reset programme's
single 6-pt text style, so every panel is placed at scale 1.0 — no row is
fit-scaled.

Layout (2026-10-10 strict-order revision, user-directed composite-length
batch): all panels render at 6-pt text and sit at scale 1.0 on the 183 mm
Nature double-column content width, and the seven panels now read in
strict letter order down four rows. Row 1 pairs the two near-matched
mRNA-campaign panels a (56 mm) and b (56 mm) on the half-width column
grid. Row 2 gives the mRNA delivery mosaic c its own full-width row —
the 2026-10-10 transposed re-render (fig5c script) turned the former
89 × 127.8 mm tall mosaic into a 183 × 50 mm wide one (targets on the
x axis, 45°-rotated labels; profiles on the y axis; the end-to-end
marker column became a marker row). Row 3 groups the three campaign
panels d (45 mm), e (80.5 mm) and f (48.5 mm) left-to-right with one
COL_GAP between them, the whole row centred (the fig4 "group"
convention). Row 4 gives the aptamer delivery mosaic g its own
full-width row — the same transposed re-render (89 × 132.2 → 183 × 50
mm). This retires the 2026-10-06 layout's c|g pairing and with it the
registered reading-order deviation (the eye no longer meets g before
d/e/f); the composite shrinks 190.1 × 260.6 → 190.1 × ~234 mm. The
former production Pareto panel h was retired when the deployment cohort
merged into b/c/e/g (the user-directed 2026-09-12 revision).

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed up-left of each panel (Nature style — no period, no brackets);
drawn by this assembler, so they keep one size at any row scale.
2026-10-10 tightening (user-directed): the letters no longer float above
the panel PDFs' top edges — panels a and b carry registered top blank
bands (a's canvas was padded 52 → 56 mm in the 2026-10-06
baseline-alignment batch, all of it added at the top; 8.1 / 5.4 mm
bands), which left the letters up to ~9.5 mm above the visible content.
Each ROW's letters now share one baseline, placed ~0.7 mm above the
row's highest first-ink row (detected on each panel's own 1200-dpi PNG)
— same line per row, still close to the content. 'g' carries a
descender, compensated so its glyph bottom — not its baseline — clears
the ink by the same margin; a post-placement assert pins every letter's
glyph bottom ≥ 0.3 mm above its panel's first ink.

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
import numpy as np
from PIL import Image

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
}

# Row plan. "grid" centres each panel in its half-width column (the
# fig2/fig3 composite convention); "group" places the letters left to
# right, the whole row centred (the fig4 convention; a single-letter group
# row centres one full-width panel). A "group" row may carry a per-pair
# gap list (pt); row 3 uses a wider d–e gap (user-directed 2026-10-10:
# panel e sat too close to d's right-edge text) within the 183 mm budget
# — total row width stays exactly on the content width. The rows read in
# strict letter order a→g (the 2026-10-10 revision).
ROWS: list[tuple[str, object]] = [
    ("grid", ["a", "b"]),
    ("group", ["c"]),
    ("group", ["d", "e", "f"], [5.5 / 25.4 * 72, 3.5 / 25.4 * 72]),
    ("group", ["g"]),
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
LETTER_GAP_PT = 2.0     # glyph bottom → panel first-ink clearance (~0.7 mm)
DESCENT_PT = {"g": 2.0}  # Helvetica-Bold descender at 8 pt (letters a–f sit
                         # on the baseline; only g dips below it)
INK = tuple(int(TEXT[i : i + 2], 16) / 255 for i in (1, 3, 5))


def first_ink_pt(png: Path) -> float:
    """Distance (pt) from a panel PNG's top edge to its first ink row —
    the panel's own top blank band, measured on the 1200-dpi raster."""
    img = np.asarray(Image.open(png).convert("L"))
    inked = (img < 250).any(axis=1)
    assert inked.any(), f"blank raster: {png}"
    return float(np.argmax(inked)) / 1200.0 * 72.0


def main() -> None:
    # every lettered panel must be placed exactly once (guards the row plan
    # against dropped panels when letters shift — the fig4 convention)
    placed_letters: list[str] = []
    for row in ROWS:
        placed_letters.extend(row[1])  # type: ignore[arg-type]
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
    col_w = (content_w - COL_GAP) / 2.0

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, w, h) — all panels at scale 1.0 (uniform text scale).
    # Rows are top-aligned; the letters share one baseline per row (see
    # the letter loop below).
    placed: list[tuple[str, float, float, float, float]] = []
    row_letters: list[list[str]] = []
    y = MARGIN_T
    for row in ROWS:
        mode, spec = row[0], row[1]
        gaps = row[2] if len(row) > 2 else None  # type: ignore[index]
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
        elif mode == "group":
            letters = spec  # type: ignore[assignment]
            gap_list = list(gaps) if gaps is not None else []
            gap_list += [COL_GAP] * (len(letters) - 1 - len(gap_list))
            total = sum(sizes[l][0] for l in letters) + sum(gap_list)
            x = MARGIN_L + max(0.0, (content_w - total) / 2.0)
            for letter, gap in zip(letters, gap_list + [0.0]):
                w, h = sizes[letter]
                row_placed.append((letter, x, y, w, h))
                x += w + gap
            row_h = max(p[4] for p in row_placed)
        else:
            raise ValueError(f"unknown row mode {mode!r}")
        placed.extend(row_placed)
        row_letters.append([p[0] for p in row_placed])
        y += row_h + ROW_GAP

    page_w = MARGIN_L + content_w + MARGIN_R
    page_h = y - ROW_GAP + MARGIN_B

    out = fitz.open()
    page = out.new_page(width=page_w, height=page_h)
    ink_offsets = {letter: first_ink_pt(OUT_DIR / name.replace(".pdf", ".png"))
                   for letter, name in PANELS.items()}
    pos = {letter: (x0, y0, w, h) for letter, x0, y0, w, h in placed}
    # one letter baseline per row (user-directed 2026-10-10): the line sits
    # LETTER_GAP_PT above the row's HIGHEST first-ink row, so the letters
    # share one horizontal line while still hugging the row's content
    for letters in row_letters:
        min_off = min(ink_offsets[l] for l in letters)
        for letter in letters:
            x0, y0, w, h = pos[letter]
            page.show_pdf_page(fitz.Rect(x0, y0, x0 + w, y0 + h),
                               sources[letter], 0)
            descent = DESCENT_PT.get(letter, 0.0)
            baseline_y = y0 + min_off - LETTER_GAP_PT - descent
            page.insert_text(
                (x0 + LABEL_DX, baseline_y),
                letter,
                fontname="hebo",
                fontsize=LABEL_SIZE,
                color=INK,
            )
            glyph_bottom = baseline_y + descent
            gap_mm = (y0 + ink_offsets[letter] - glyph_bottom) / 72 * 25.4
            assert 0.3 <= gap_mm <= 5.0, \
                f"letter {letter} sits {gap_mm:.2f} mm from its panel's ink"

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
