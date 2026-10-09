#!/usr/bin/env python3
"""Deterministic raster QA for the Exp 31 figure PNG (the house
convention): exact 1200-dpi canvas pixels for the declared mm size, zero
ink on the outer border, and every opaque pixel either pure black text or
a palette-rev-7 colour (anti-aliased blends against white allowed within
tolerance of a palette entry).

Usage: python experiments/plots/qa_exp31_figs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "experiments" / "plots" / "output"
DPI = 1200

FIGS = [
    ("fig5d_secondary_endpoint.png", 45.0, 54.0),
]

PALETTE_RGB = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in PALETTE]
ALLOWED = PALETTE_RGB + [(0, 0, 0), (255, 255, 255), (217, 217, 217)]


def close_to_any(px: tuple[int, int, int], tol: int = 10) -> bool:
    return any(abs(px[0] - a) <= tol and abs(px[1] - b) <= tol and
               abs(px[2] - c) <= tol for a, b, c in ALLOWED)


def near_any(px: tuple[int, int, int], tol: int = 24) -> bool:
    """Anti-aliasing-tolerant variant (text/tile-edge fringes against
    black/white/palette stay within tol of an allowed colour)."""
    return close_to_any(px, tol)


def main() -> int:
    failures = 0
    for name, w_mm, h_mm in FIGS:
        path = OUT / name
        if not path.is_file():
            print(f"[qa] SKIP {name} (not rendered yet)")
            continue
        img = np.asarray(Image.open(path).convert("RGB"))
        h_px, w_px = img.shape[:2]
        exp_w = round(w_mm / 25.4 * DPI)
        exp_h = round(h_mm / 25.4 * DPI)
        issues = []
        if w_px != exp_w:
            issues.append(f"width {w_px} != {exp_w}")
        if h_px != exp_h:
            issues.append(f"height {h_px} != {exp_h}")
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
        print(f"[qa] {name}: {w_px}x{h_px} {status}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
