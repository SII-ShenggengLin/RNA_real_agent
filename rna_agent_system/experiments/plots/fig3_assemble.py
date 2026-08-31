#!/usr/bin/env python3
"""Fig. 3 composite — assemble the eight finished panels (a–h) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–4, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned so the letters sit on one line per row, and
one fixed column grid. Every panel carries the reset programme's single
6-pt text style, so every panel is placed at scale 1.0 — no row is
fit-scaled.

Layout (2026-08-31, user-directed revision): a (screening balloon matrix)
spans the full width; **b and c share row 2** — b is the tall 27-cell
ranking dot plot, so panel c is embedded in its two-sub-row composite
layout (`fig3c_docking_lollipop_composite.pdf`, rendered by
`FIG3C_LAYOUT=composite python experiments/plots/fig3c_docking_lollipop.py`;
the 19 lollipops wrap 11 + 8 at the SARS-CoV-2 RBD | PSMA group boundary)
so the two fill the row edge to edge at uniform text scale; d and e share
row 3 as **matched-height panels** (d re-rendered smaller, e re-rendered
larger — 86.7 x 44.1 mm vs 85.5 x 41.4 mm — so the earlier height-mismatch
blank band under e is gone; no data change); **f g h share one row drawn at
one equal height** (the fig2 fgh-row convention: per-panel scales differ —
≈ 0.69/0.64/0.81 — widths follow their aspects and the leftover width
becomes even gutters; user direction — h does not need the full width, so
the full-width closing panel of the first composite layout is retired).

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed just above-left of each panel corner (Nature style — no period, no
brackets); drawn by this assembler, so they keep one size at any row scale.

Assembly preserves vectors: each panel PDF is embedded as a Form XObject
via PyMuPDF `show_pdf_page` (no rasterization); the PNG is rendered from
the finished composite at 1200 dpi (Nature Methods line-art minimum at
final print size).

Usage : python experiments/plots/fig3_assemble.py
Output : experiments/plots/output/fig3_composite.{pdf,png}
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

# Panel PDFs in lettering order. Panel c is the composite-layout render
# (see the module docstring); all other panels are the standalone
# reset-programme panels (d and e re-rendered as matched-height panels for
# row 3, same day, no data change).
PANELS: dict[str, str] = {
    "a": "fig3a_oracle_screening.pdf",
    "b": "fig3b_oracle_ranking.pdf",
    "c": "fig3c_docking_lollipop_composite.pdf",
    "d": "fig3d_affinity_calibration.pdf",
    "e": "fig3e_claim_overreach.pdf",
    "f": "fig3f_mrl_certification.pdf",
    "g": "fig3g_rnasmol_fidelity.pdf",
    "h": "fig3h_dissolution.pdf",
}

# Row plan in strict reading order. Mode "full" centres one panel on the
# content width; "flush" places the two panels at the row's left and right
# edges (row 2: b + the wide two-sub-row c exactly tile the content width
# with one column gap between them); "grid" centres each panel in its
# half-width column (the fig2 composite convention); "fit" draws the whole
# row at one equal height and lets the leftover width become even gutters
# (the fig2 fgh-row convention).
ROWS: list[tuple[str, list[str]]] = [
    ("full", ["a"]),
    ("flush", ["b", "c"]),
    ("grid", ["d", "e"]),
    ("fit", ["f", "g", "h"]),
]

# Grid constants (PDF points) — identical to the fig2 composite.
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

    content_w = sizes["a"][0]  # panel a defines the full width
    col_w = (content_w - COL_GAP) / 2.0

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, w, h) — all panels at scale 1.0 (uniform text scale).
    # Rows are top-aligned so the panel letters sit on one line per row.
    placed: list[tuple[str, float, float, float, float]] = []
    y = MARGIN_T
    for mode, letters in ROWS:
        row_placed = []
        if mode == "full":
            (letter,) = letters
            w, h = sizes[letter]
            x0 = MARGIN_L + max(0.0, (content_w - w) / 2.0)
            row_placed.append((letter, x0, y, w, h))
        elif mode == "flush":
            left, right = letters
            wl, hl = sizes[left]
            wr, hr = sizes[right]
            row_placed.append((left, MARGIN_L, y, wl, hl))
            row_placed.append((right, MARGIN_L + content_w - wr, y, wr, hr))
        elif mode == "fit":
            # Equal-size row (the fig2 fgh-row convention): one drawn height
            # for every panel, so the row reads as a band of identical
            # panels. Per-panel scales differ — the aspects differ — so
            # widths vary slightly; leftover width becomes even gutters.
            # Height = the median panel height at the uniform fit scale, so
            # no panel is squeezed to the smallest one's proportions.
            n = len(letters)
            s0 = (content_w - (n - 1) * COL_GAP) / sum(sizes[l][0] for l in letters)
            row_h = sorted(sizes[l][1] * s0 for l in letters)[n // 2]
            total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l in letters)
            gap = (content_w - total_w) / (n - 1)
            if gap < 6.0:  # keep the gutters sane if aspects ever widen
                row_h *= (content_w - (n - 1) * 6.0) / total_w
                total_w = sum(sizes[l][0] * (row_h / sizes[l][1]) for l in letters)
                gap = (content_w - total_w) / (n - 1)
            x = MARGIN_L
            for letter in letters:
                w, h = sizes[letter]
                s = row_h / h
                row_placed.append((letter, x, y, w * s, h * s))
                x += w * s + gap
        else:  # grid
            for col_idx, letter in enumerate(letters):
                w, h = sizes[letter]
                if w > col_w + 0.5:
                    raise ValueError(
                        f"panel {letter} width {w:.1f} breaks the grid "
                        f"(limit {col_w:.1f})"
                    )
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

    pdf_path = OUT_DIR / "fig3_composite.pdf"
    png_path = OUT_DIR / "fig3_composite.png"
    out.save(pdf_path, deflate=True, garbage=3)
    pix = page.get_pixmap(dpi=1200)
    pix.save(png_path)
    print(f"wrote {pdf_path} ({page_w:.1f} x {page_h:.1f} pt "
          f"= {page_w / 72 * 25.4:.1f} x {page_h / 72 * 25.4:.1f} mm)")
    print(f"wrote {png_path} ({pix.width} x {pix.height} px @ 1200 dpi)")


if __name__ == "__main__":
    main()
