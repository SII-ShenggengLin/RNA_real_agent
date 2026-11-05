#!/usr/bin/env python3
"""Fig. 3 composite — assemble the six finished panels (a–f) into one figure.

Panel composition follows the Nature conventions surveyed in
`relevant_references/` (DeepRare main Figs. 2–4, Nature 651, 2026): bold
lowercase panel letters at the top-left corner of each panel (no period,
no brackets), panels lettered in strict reading order (left to right, top
to bottom), rows top-aligned so the letters sit on one line per row, and
one fixed column grid. Every panel carries the reset programme's single
6-pt text style, so every panel is placed at scale 1.0 — no row is
fit-scaled.

Layout (2026-09-11, user-directed revision — one figure per subsection): a
(screening balloon matrix) spans the full width; **b and c share row 2** —
b is the tall 27-cell ranking dot plot, so panel c is embedded in its
two-sub-row composite layout (`fig3c_docking_lollipop_composite.pdf`,
rendered by `FIG3C_LAYOUT=composite python experiments/plots/fig3c_docking_lollipop.py`;
the 19 lollipops wrap 11 + 8 at the SARS-CoV-2 RBD | PSMA group boundary)
so the two fill the row edge to edge at uniform text scale.
Layout (2026-10-02, user-directed — d, e and f on one row): d, e and f were
re-rendered to the three-column width (~58 mm; f narrowed from 77 mm, d and
e from ~86 mm, all at the unchanged 6-pt text size, no data change) and now
share row 3 in a three-column grid; the former matched-height d|e row and
the full-width centred f row are retired. Text sync in the same batch:
3a's colour-bar label pluralized, 3b's x-label oracle → predictor and its
ring key "nominal pass" → "reaches ρ ≥ 0.6", 3d's legend "thrombin series"
→ "thrombin Kd anchors" (body §2.3 synced), 3e's x-label "Decision-layer
overreach events" → "Overreach events" (the fig4f precedent; the Fig. 3e
caption carries "plan-level") with its key → "ranking use"/"screening use",
3f's stage labels → "Apparent advantage"/"Budget matching", its gate tag
→ "pre-registered gate δ ≥ 0.3" (moved below the line), its inset head
→ "null distribution" and its y-label → "coordination-loop advantage".

Letters: Helvetica-Bold 8 pt (Arial-equivalent), ink black (palette TEXT),
placed just above-left of each panel corner (Nature style — no period, no
brackets); drawn by this assembler, so they keep one size at any row scale.

Row gaps are ink-measured (2026-10-10 alignment batch, user-directed):
each row advances by the distance from its panels' top edge to their
lowest ink plus one fixed gap, not by the bounding-box height.  Panel a
keeps ~13 pt of designed blank below its rotated x labels (its exact-mm
canvas), the row-2 panels ~3 pt — the box-height rule had made the
a→b/c gap 10 pt larger than the b/c→d/e/f gap; the ink rule makes both
transitions equal.  Same batch: d, e and f re-rendered on the shared
exact-mm row-3 geometry (`fig3_row3_layout.py`), so the three axes land
on the same lines in their grid3 columns.

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
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import TEXT  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = PROJECT_ROOT / "experiments" / "plots" / "output"

# Panel PDFs in lettering order. Panel c is the composite-layout render
# (see the module docstring); all other panels are the standalone
# reset-programme panels (d and e re-rendered as matched-height panels for
# row 3, same day, no data change). Re-lettered 2026-09-11 (user-directed):
# confounded improvement h→f (last §2.3 panel), MRL certification f→g and
# RNAsmol deployed-artifact fidelity g→h (both first cited in the CapGate
# section §2.4) — panels stay in first-citation alphabetical order; no
# panel content changed, only letters and file names. Same-day second
# revision (the one-figure-per-subsection principle): the certification and
# fidelity panels moved out of Fig. 3 into Fig. 4 (a/b there), leaving Fig. 3
# the six failure-mode panels a–f.
PANELS: dict[str, str] = {
    "a": "fig3a_oracle_screening.pdf",
    "b": "fig3b_oracle_ranking.pdf",
    "c": "fig3c_docking_lollipop_composite.pdf",
    "d": "fig3d_affinity_calibration.pdf",
    "e": "fig3e_claim_overreach.pdf",
    "f": "fig3f_dissolution.pdf",
}

# Row plan in strict reading order. Mode "full" centres one panel on the
# content width; "flush" places the two panels at the row's left and right
# edges (row 2: b + the wide two-sub-row c exactly tile the content width
# with one column gap between them); "grid" centres each panel in its
# half-width column (the fig2 composite convention); "grid3" centres each
# panel in its third-width column (row 3: d, e, f — 2026-10-02); "fit" draws
# the whole row at one equal height and lets the leftover width become even
# gutters (the fig2 fgh-row convention).
ROWS: list[tuple[str, list[str]]] = [
    ("full", ["a"]),
    ("flush", ["b", "c"]),
    ("grid3", ["d", "e", "f"]),
]

# Grid constants (PDF points) — identical to the fig2 composite.
COL_GAP = 11.0
INK_ROW_GAP = 19.0      # lowest ink of a row → top edge of the next row;
                        # hosts the 8 pt label band above each row (2026-10-10:
                        # measured on ink, not bounding boxes — see module
                        # docstring; 19 pt ≈ the previous b/c→d/e/f spacing)
MARGIN_L = 14.0         # labels hang 11 pt left of their panel
MARGIN_R = 6.0
MARGIN_T = 12.0         # label band for row 1
MARGIN_B = 8.0
LABEL_SIZE = 8.0
LABEL_DX = -11.0        # letter anchor relative to the panel corner
LABEL_DY = -4.0         # baseline this far above the panel top edge
INK = tuple(int(TEXT[i : i + 2], 16) / 255 for i in (1, 3, 5))


def ink_bottom_extent(doc: fitz.Document) -> float:
    """Distance from a panel's top edge to its lowest ink, in points.

    Renders the panel's first page and scans for non-paper pixels (any
    channel below 245 — the light NEUTRAL_GRID grey still counts).  A
    panel's bounding box can trail its ink by designed bottom margins, so
    equal visual row gaps are measured on the ink, not the box.
    """
    pix = doc[0].get_pixmap(dpi=150)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)[:, :, :3]
    rows = np.where((arr < 245).any(axis=(1, 2)))[0]
    if len(rows) == 0:
        return doc[0].rect.height
    return (rows[-1] + 1) * 72.0 / 150.0


def main() -> None:
    sources: dict[str, fitz.Document] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for letter, name in PANELS.items():
        doc = fitz.open(OUT_DIR / name)
        sources[letter] = doc
        r = doc[0].rect
        sizes[letter] = (r.width, r.height)

    content_w = max(sizes["a"][0], sizes["b"][0] + sizes["c"][0] + COL_GAP)
    # 2026-10-02 second pass: panel a is narrower than the b+c row (its
    # rotated labels let it shrink to ~145 mm), so the content width is the
    # widest ROW, no longer panel a alone; row 1's "full" mode then centres
    # a within it.
    col_w = (content_w - COL_GAP) / 2.0
    col_w3 = (content_w - 2 * COL_GAP) / 3.0

    # Lay out rows top to bottom; each placed panel is
    # (letter, x, y, w, h) — all panels at scale 1.0 (uniform text scale).
    # Rows are top-aligned so the panel letters sit on one line per row;
    # each row advances by its lowest ink (see ink_bottom_extent), so the
    # visual gap between rows is the same at every transition.
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
        elif mode == "grid3":
            for col_idx, letter in enumerate(letters):
                w, h = sizes[letter]
                if w > col_w3 + 0.5:
                    raise ValueError(
                        f"panel {letter} width {w:.1f} breaks the 3-column "
                        f"grid (limit {col_w3:.1f})"
                    )
                x0 = MARGIN_L + col_idx * (col_w3 + COL_GAP) + (col_w3 - w) / 2.0
                row_placed.append((letter, x0, y, w, h))
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
        y += max(ink_bottom_extent(sources[l]) for l in letters) + INK_ROW_GAP

    page_w = MARGIN_L + content_w + MARGIN_R
    page_h = y - INK_ROW_GAP + MARGIN_B

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
