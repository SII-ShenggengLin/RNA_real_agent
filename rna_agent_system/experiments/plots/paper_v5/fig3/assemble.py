"""Assemble Fig 3 (9 panels, 3x3 grid)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from assemble import assemble

HERE = pathlib.Path(__file__).resolve().parent
layout = [(chr(ord("a") + i), (i // 3, i % 3, 1, 1)) for i in range(9)]
assemble(HERE, layout, page_w_mm=183.0)
