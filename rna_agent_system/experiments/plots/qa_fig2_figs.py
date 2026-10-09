#!/usr/bin/env python3
"""Deterministic raster QA for the Fig. 2 figure PNGs + the Supplementary
Fig. S1 panel (the house convention, qa_exp29_30_figs.py pattern): the PNG
pixel canvas agrees with the vector PDF page (pt x 1200/72), zero ink on the
outer border, and every opaque pixel is ink-black/pure-black text or a
palette-rev-7 colour (anti-aliased blends against white allowed within
tolerance of an allowed colour).

The fig2 panels save with bbox_inches="tight", so the trimmed canvas is
smaller than the declared mm figure size — the exact-mm canvas check of the
fig5 QA scripts does not apply here; the PNG/PDF size agreement check takes
its place (both derive from the same tight bbox at save time).

Registered 2026-09-11 for the 8-panel re-lettering (a-h; the IRES panel
moved to Supplementary Fig. S3, rendered by figS3_ires_panel.py).

Usage: python experiments/plots/qa_fig2_figs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import NEUTRAL_GRID, PALETTE, TEXT  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "experiments" / "plots" / "output"
DPI = 1200

# (png name, pdf name) — panels a-h, the composite, and the S1 panel pair.
FIGS = [
    ("fig2a_coverage.png", "fig2a_coverage.pdf"),
    ("fig2b_cai.png", "fig2b_cai.pdf"),
    ("fig2c_mfe_per_nt.png", "fig2c_mfe_per_nt.pdf"),
    ("fig2d_inverse_folding.png", "fig2d_inverse_folding.pdf"),
    ("fig2e_sirna_offtarget.png", "fig2e_sirna_offtarget.pdf"),
    ("fig2f_rnasmol_boundary.png", "fig2f_rnasmol_boundary.pdf"),
    ("fig2g_audit_trail.png", "fig2g_audit_trail.pdf"),
    ("fig2h_runtime_ecdf.png", "fig2h_runtime_ecdf.pdf"),
    ("fig2_composite.png", "fig2_composite.pdf"),
    ("figS3_ires_panel.png", "figS3_ires_panel.pdf"),
    ("figS3_ires_panel_mode0.png", "figS3_ires_panel_mode0.pdf"),
]

PALETTE_RGB = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in PALETTE]
INK_RGB = tuple(int(TEXT[i:i + 2], 16) for i in (1, 3, 5))      # (26,26,26)
GRID_RGB = tuple(int(NEUTRAL_GRID[i:i + 2], 16) for i in (1, 3, 5))
ALLOWED = PALETTE_RGB + [(0, 0, 0), (255, 255, 255), INK_RGB, GRID_RGB]


def close_to_any(px: tuple[int, int, int], tol: int = 10) -> bool:
    return any(abs(px[0] - a) <= tol and abs(px[1] - b) <= tol and
               abs(px[2] - c) <= tol for a, b, c in ALLOWED)


def near_any(px: tuple[int, int, int], tol: int = 24) -> bool:
    """Anti-aliasing-tolerant variant (text/tile-edge fringes against
    black/white/palette stay within tol of an allowed colour). Pure neutral
    greys (r == g == b) are ink-on-white anti-aliasing by construction."""
    return close_to_any(px, tol) or px[0] == px[1] == px[2]


def main() -> int:
    failures = 0
    for png_name, pdf_name in FIGS:
        png_path, pdf_path = OUT / png_name, OUT / pdf_name
        if not (png_path.is_file() and pdf_path.is_file()):
            print(f"[qa] SKIP {png_name} (not rendered yet)")
            continue
        img = np.asarray(Image.open(png_path).convert("RGB"))
        h_px, w_px = img.shape[:2]
        page = fitz.open(pdf_path)[0]
        exp_w = round(page.rect.width / 72 * DPI)
        exp_h = round(page.rect.height / 72 * DPI)
        issues = []
        # PNG canvas agrees with the vector PDF page at 1200 dpi (+-2 px
        # rounding between the matplotlib tight-bbox raster and PDF paths)
        if abs(w_px - exp_w) > 2 or abs(h_px - exp_h) > 2:
            issues.append(f"canvas {w_px}x{h_px} != PDF {exp_w}x{exp_h}")
        # zero ink on the 2-px outer border
        border = np.concatenate([img[:2].reshape(-1, 3), img[-2:].reshape(-1, 3),
                                 img[:, :2].reshape(-1, 3), img[:, -2:].reshape(-1, 3)])
        inked = (border < 250).any(axis=1)
        if inked.any():
            issues.append(f"border ink {int(inked.sum())} px")
        # every opaque pixel near an allowed colour (sample grid for speed)
        sample = img[::7, ::7].reshape(-1, 3)
        bad = sum(1 for px in sample if not near_any(tuple(int(v) for v in px)))
        # anti-aliasing fringes of 6-pt text and 0.4-px tile borders are
        # inevitable at 1200 dpi; a real palette violation is a substantial
        # cluster of foreign colours
        if bad / max(1, len(sample)) > 0.005:
            issues.append(f"{bad}/{len(sample)} sampled px off-palette")
        status = "GREEN" if not issues else "FAIL " + "; ".join(issues)
        if issues:
            failures += 1
        print(f"[qa] {png_name}: {w_px}x{h_px} {status}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
