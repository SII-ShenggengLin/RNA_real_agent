"""Build fig1_panels.pptx — one slide per sub-panel + one composite slide.

16:9 slides; each panel slide: small header (letter + short title), panel
image centred at max size; final slide: the assembled Fig 1 composite.
Images: panels/<x>_ppt.png (300 dpi) + fig1_composite_ppt.png.
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = os.path.join(HERE, "panels")

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
HEADER_H = Inches(0.85)
MARGIN = Inches(0.45)
INK = RGBColor(0x1A, 0x1A, 0x1A)
SLATE = RGBColor(0x6B, 0x7B, 0x8D)

TITLES = {
    "a": "a · 端到端循环与七层平台脊柱  |  end-to-end cycle & seven-layer spine",
    "b": "b · 多智能体执行层（各智能体贡献被测量）  |  multi-agent layer, measured",
    "c": "c · 平台一览：规模与审计构成  |  platform at a glance",
    "d": "d · CapGate：证据门控循环  |  capability-layer evidence gating",
    "e": "e · GenNav：约束导航  |  generation-layer constraint navigation",
    "f": "f · RNADesign-210 基准组成  |  benchmark composition",
}


def add_slide(prs, title, img_path, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # header
    tb = slide.shapes.add_textbox(MARGIN, Inches(0.18), SLIDE_W - 2 * MARGIN,
                                  Inches(0.55))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.LEFT
    for run in p.runs:
        run.font.size = Pt(20)
        run.font.bold = True
        run.font.color.rgb = INK
    if subtitle:
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.alignment = PP_ALIGN.LEFT
        for run in p2.runs:
            run.font.size = Pt(11)
            run.font.color.rgb = SLATE
    # image, centred under header
    iw, ih = Image.open(img_path).size
    avail_w = SLIDE_W - 2 * MARGIN
    avail_h = SLIDE_H - HEADER_H - MARGIN
    scale = min(avail_w / iw, avail_h / ih)
    w, h = iw * scale, ih * scale
    left = (SLIDE_W - w) / 2
    top = HEADER_H + (avail_h - h) / 2
    slide.shapes.add_picture(img_path, left, top, width=w, height=h)
    return slide


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    # cover
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    tb = slide.shapes.add_textbox(MARGIN, Inches(2.2), SLIDE_W - 2 * MARGIN,
                                  Inches(3.0))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Fig 1 · RNADesignAgent 系统示意图"
    p.alignment = PP_ALIGN.CENTER
    for run in p.runs:
        run.font.size = Pt(34)
        run.font.bold = True
        run.font.color.rgb = INK
    p2 = tf.add_paragraph()
    p2.text = "六面板（a–f）· 双栏 183 × 188 mm · palette rev 7 · Nature Methods 体例"
    p2.alignment = PP_ALIGN.CENTER
    for run in p2.runs:
        run.font.size = Pt(16)
        run.font.color.rgb = SLATE
    p3 = tf.add_paragraph()
    p3.text = ("第 1–6 页：各子图（可单独修改）· 第 7 页：整图组合\n"
               "重建：python panel_a.py … panel_f.py && python assemble.py && python build_pptx.py")
    p3.alignment = PP_ALIGN.CENTER
    for run in p3.runs:
        run.font.size = Pt(12)
        run.font.color.rgb = SLATE

    for letter in "abcdef":
        add_slide(prs, TITLES[letter],
                  os.path.join(PANELS, f"{letter}_ppt.png"))

    add_slide(prs, "Fig 1 · 整图  |  composite (183 × 188 mm)",
              os.path.join(PANELS, "fig1_composite_ppt.png"))

    out = os.path.join(HERE, "fig1_panels.pptx")
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
