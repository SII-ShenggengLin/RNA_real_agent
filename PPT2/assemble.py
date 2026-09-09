"""Assemble Fig 1 composite (183 × 197 mm) from the vector panel PDFs.

Panel grid (mm, origin bottom-left), 3 mm gaps, 1 mm margins:
    a  181 × 50  at (1, 146)   platform overview
    b  181 × 44  at (1, 99)    Layer-4 multi-agent execution
    c  181 × 50  at (1, 46)    CapGate evidence gating
    d  181 × 42  at (1, 1)     GenNav constraint navigation
Panel letters a–d drawn at assembly (8 pt Helvetica-Bold ink, Nature style).
"""
import fitz  # PyMuPDF
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = os.path.join(HERE, "panels")

PAGE_W, PAGE_H = 183.0, 200.0
LAYOUT = {  # letter -> (x, y, w, h) mm
    "a": (1, 146.5, 181, 50),
    "b": (1, 99.5, 181, 44),
    "c": (1, 46.5, 181, 50),
    "d": (1, 1, 181, 42),
}
MM = 72.0 / 25.4


def build(pdf_out=None, png_out=None, ppt_png_out=None):
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W * MM, height=PAGE_H * MM)
    for letter, (x, y, w, h) in LAYOUT.items():
        src = fitz.open(os.path.join(PANELS, f"{letter}.pdf"))
        rect = fitz.Rect(x * MM, (PAGE_H - y - h) * MM,
                         (x + w) * MM, (PAGE_H - y) * MM)
        page.show_pdf_page(rect, src, 0)
        src.close()
        # panel letter, top-left, 8 pt Helvetica-Bold
        page.insert_text(fitz.Point((x - 0.4) * MM, (PAGE_H - y - h - 0.8) * MM),
                         letter, fontsize=8, fontname="hebo",
                         color=(0.102, 0.102, 0.102))
    pdf_out = pdf_out or os.path.join(PANELS, "fig1_composite.pdf")
    doc.save(pdf_out, garbage=4, deflate=True)
    doc.close()

    # raster versions
    doc = fitz.open(pdf_out)
    pix = doc[0].get_pixmap(dpi=1200)
    pix.save(png_out or os.path.join(PANELS, "fig1_composite.png"))
    pix2 = doc[0].get_pixmap(dpi=300)
    pix2.save(ppt_png_out or os.path.join(PANELS, "fig1_composite_ppt.png"))
    doc.close()
    print("assembled:", pdf_out)


if __name__ == "__main__":
    build()
