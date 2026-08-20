"""Assemble Fig 1 (mixed grid: a full-width, b+d double, c/e single, f full-width)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assemble import assemble

HERE = pathlib.Path(__file__).resolve().parent
layout = [
    ("a", (0, 0, 1, 2)),
    ("b", (1, 0, 1, 1)),
    ("c", (1, 1, 1, 1)),
    ("d", (2, 0, 1, 1)),
    ("e", (2, 1, 1, 1)),
    ("f", (3, 0, 1, 2)),
]
assemble(HERE, layout, page_w_mm=183.0, gap_mm=4.0)
