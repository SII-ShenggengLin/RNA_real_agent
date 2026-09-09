"""Build fig1_panels.pptx — fully editable native PowerPoint shapes.

No raster images: every card, arrow, text label and icon is a native shape
(rounded rectangle / connector / text box / oval / freeform), so each panel
and the whole composite can be edited by hand in PowerPoint.

Slide size = the figure page (183 × 197 mm). Slide 1: assembled composite
(panels a–d at their figure positions + panel letters). Slides 2–5: one panel
per slide, centred, same native shapes.

Rebuild: python panel_a.py … panel_d.py && python assemble.py && python build_pptx.py
"""
import importlib
import os

from pptx import Presentation
from pptx.util import Mm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE

from pptx_backend import PptxBackend
from assemble import LAYOUT, PAGE_W, PAGE_H

HERE = os.path.dirname(os.path.abspath(__file__))

PANEL_MODULES = {"a": "panel_a", "b": "panel_b", "c": "panel_c", "d": "panel_d"}
INK = RGBColor(0x1A, 0x1A, 0x1A)


def add_letter(slide, letter, x_mm, panel_top_mm):
    """Panel letter just above the panel's top-left corner.

    panel_top_mm = panel's top edge in figure mm (y up from bottom).
    """
    tb = slide.shapes.add_textbox(Mm(x_mm), Mm(PAGE_H - panel_top_mm - 3.3),
                                  Mm(6), Mm(3.2))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    p = tf.paragraphs[0]
    p.text = letter
    p.alignment = PP_ALIGN.LEFT
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(8)
        run.font.bold = True
        run.font.color.rgb = INK


def draw_panel(slide, letter, ox, oy):
    mod = importlib.import_module(PANEL_MODULES[letter])
    mod.build(PptxBackend(slide, PAGE_H, ox=ox, oy=oy))


def main():
    prs = Presentation()
    prs.slide_width = Mm(PAGE_W)
    prs.slide_height = Mm(PAGE_H)
    blank = prs.slide_layouts[6]

    # slide 1: composite
    slide = prs.slides.add_slide(blank)
    for letter, (x, y, w, h) in LAYOUT.items():
        draw_panel(slide, letter, x, y)
        add_letter(slide, letter, x - 0.4, y + h)

    # slides 2–5: one panel per slide, centred
    for letter in "abcd":
        mod = importlib.import_module(PANEL_MODULES[letter])
        slide = prs.slides.add_slide(blank)
        ox = (PAGE_W - mod.W) / 2
        oy = (PAGE_H - mod.H) / 2
        draw_panel(slide, letter, ox, oy)
        add_letter(slide, letter, ox - 0.4, oy + mod.H)

    out = os.path.join(HERE, "fig1_panels.pptx")
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
