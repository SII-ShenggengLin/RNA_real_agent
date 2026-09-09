"""Native-PowerPoint drawing backend for the Fig 1 panels.

Implements the same backend API as style.MplBackend, but every primitive
becomes an editable PowerPoint shape (rounded rectangle, connector, text box,
oval, freeform) instead of a matplotlib artist. Coordinates are mm, origin at
the panel's bottom-left (y up), converted to slide EMU (y down) via the page
height and the panel offset (ox, oy).
"""
import math

from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.oxml.ns import qn

import style as S

EMU_PER_MM = 36000


def _mm(v):
    return Emu(int(round(v * EMU_PER_MM)))


def _rgb(hexcolor):
    if not hexcolor.startswith("#"):
        from matplotlib.colors import to_hex
        hexcolor = to_hex(hexcolor)
    return RGBColor.from_string(hexcolor.lstrip("#"))


def _fill_alpha(shape, alpha):
    """Set transparency on a solid fill via <a:alpha> in the srgbClr node."""
    if alpha >= 0.999:
        return
    sF = shape.fill._xPr.find(qn("a:solidFill"))
    if sF is None:
        return
    clr = sF.find(qn("a:srgbClr"))
    if clr is None:
        return
    clr.append(clr.makeelement(qn("a:alpha"),
                               {"val": str(int(alpha * 100000))}))


def _line_xml(shape_or_conn, dash=None, arrow_tail=False, arrow_head=False):
    ln = shape_or_conn.line._get_or_add_ln()
    if dash:
        ln.append(ln.makeelement(qn("a:prstDash"), {"val": dash}))
    if arrow_head:
        ln.append(ln.makeelement(qn("a:headEnd"),
                                 {"type": "triangle", "w": "med", "len": "med"}))
    if arrow_tail:
        ln.append(ln.makeelement(qn("a:tailEnd"),
                                 {"type": "triangle", "w": "med", "len": "med"}))


_FLOW_STYLE = {
    "data": (S.C_SLATE, None),
    "gate": (S.C_TERRACOTTA, "dash"),
    "advisory": (S.C_DARK, "sysDot"),
}


class PptxBackend:
    """Same API as style.MplBackend; draws editable shapes on a slide."""

    def __init__(self, slide, page_h_mm, ox=0.0, oy=0.0):
        self.slide = slide
        self.H = page_h_mm
        self.ox = ox
        self.oy = oy

    # -- coordinate mapping ------------------------------------------------
    def _pt(self, x, y):
        """panel mm (y up) -> slide EMU (y down)."""
        return _mm(self.ox + x), _mm(self.H - (self.oy + y))

    # -- primitives --------------------------------------------------------
    def card(self, x, y, w, h, *, face, alpha=0.16, edge=None, dashed=False,
             lw=0.8, radius=0.9):
        left = _mm(self.ox + x)
        top = _mm(self.H - (self.oy + y + h))
        sp = self.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                         left, top, _mm(w), _mm(h))
        try:
            sp.adjustments[0] = max(0.0, min(0.5, radius / min(w, h)))
        except Exception:
            pass
        if face is None:
            sp.fill.background()
        else:
            sp.fill.solid()
            sp.fill.fore_color.rgb = _rgb(face)
            _fill_alpha(sp, alpha)
        if edge is False:
            sp.line.fill.background()
        else:
            sp.line.color.rgb = _rgb(face if edge is None else edge)
            sp.line.width = Pt(lw)
            if dashed:
                _line_xml(sp, dash="dash")
        sp.shadow.inherit = False
        return sp

    def txt(self, x, y, s, *, size=6, weight="normal", color=S.INK,
            ha="center", va="center", style=None, rotation=0):
        lines = s.split("\n")
        wch = max(len(l) for l in lines)
        est_w = max(6.0, wch * size * 0.185 * (1.06 if weight == "bold" else 1.0) + 2.0)
        est_h = len(lines) * size * 0.42 + 1.6
        cx = self.ox + x
        cy = self.H - (self.oy + y)
        left = cx - est_w / 2 if ha == "center" else (cx if ha == "left" else cx - est_w)
        top = cy - est_h / 2 if va == "center" else (cy if va == "top" else cy - est_h)
        tb = self.slide.shapes.add_textbox(_mm(left), _mm(top),
                                           _mm(est_w), _mm(est_h))
        tf = tb.text_frame
        tf.word_wrap = False
        tf.auto_size = MSO_AUTO_SIZE.NONE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"center": MSO_ANCHOR.MIDDLE, "top": MSO_ANCHOR.TOP,
                              "bottom": MSO_ANCHOR.BOTTOM}[va]
        align = {"center": PP_ALIGN.CENTER, "left": PP_ALIGN.LEFT,
                 "right": PP_ALIGN.RIGHT}[ha]
        for i, line_txt in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line_txt
            p.alignment = align
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(size)
                run.font.bold = weight == "bold"
                run.font.italic = style == "italic"
                run.font.color.rgb = _rgb(color)
        if rotation:
            tb.rotation = (-rotation) % 360
        return tb

    def flow(self, x0, y0, x1, y1, *, kind="data", lw=1.0, both=False, ms=7.5,
             rad=0.0):
        color, dash = _FLOW_STYLE[kind]
        X0, Y0 = self._pt(x0, y0)
        X1, Y1 = self._pt(x1, y1)
        conn = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                               X0, Y0, X1, Y1)
        conn.line.color.rgb = _rgb(color)
        conn.line.width = Pt(lw)
        conn.shadow.inherit = False
        _line_xml(conn, dash=dash, arrow_tail=True, arrow_head=both)
        return conn

    def line(self, x0, y0, x1, y1, *, color=S.C_SLATE, lw=0.5, dash=None):
        X0, Y0 = self._pt(x0, y0)
        X1, Y1 = self._pt(x1, y1)
        conn = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                               X0, Y0, X1, Y1)
        conn.line.color.rgb = _rgb(color)
        conn.line.width = Pt(lw)
        conn.shadow.inherit = False
        if dash:
            _line_xml(conn, dash={"dash": "dash", "dot": "sysDot"}[dash])
        return conn

    def dot(self, cx, cy, r, *, face, edge=None, lw=0.5):
        left, top = self._pt(cx - r, cy + r)
        sp = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top,
                                         _mm(2 * r), _mm(2 * r))
        if face:
            sp.fill.solid()
            sp.fill.fore_color.rgb = _rgb(face)
        else:
            sp.fill.background()
        if edge:
            sp.line.color.rgb = _rgb(edge)
            sp.line.width = Pt(lw)
        else:
            sp.line.fill.background()
        sp.shadow.inherit = False
        return sp

    # -- icons ---------------------------------------------------------------
    def _freeform(self, pts_mm, color, lw, close=False):
        """Polyline through panel-mm points -> editable freeform shape."""
        pts_emu = [self._pt(px, py) for px, py in pts_mm]
        fb = self.slide.shapes.build_freeform(pts_emu[0][0], pts_emu[0][1],
                                              scale=1.0)
        fb.add_line_segments(pts_emu[1:], close=close)
        sp = fb.convert_to_shape()
        sp.fill.background()
        sp.line.color.rgb = _rgb(color)
        sp.line.width = Pt(lw)
        sp.shadow.inherit = False
        return sp

    def icon(self, name, cx, cy, s, color, lw=0.7):
        getattr(self, "_icon_" + name)(cx, cy, s, color, lw)

    def _icon_doc(self, cx, cy, s, color, lw):
        w = s * 0.78
        left, top = self._pt(cx - w / 2, cy + s / 2)
        sp = self.slide.shapes.add_shape(MSO_SHAPE.FOLDED_CORNER, left, top,
                                         _mm(w), _mm(s))
        sp.fill.background()
        sp.line.color.rgb = _rgb(color)
        sp.line.width = Pt(lw)
        sp.shadow.inherit = False

    def _icon_db(self, cx, cy, s, color, lw):
        w = s * 0.85
        left, top = self._pt(cx - w / 2, cy + s / 2)
        sp = self.slide.shapes.add_shape(MSO_SHAPE.CAN, left, top,
                                         _mm(w), _mm(s))
        sp.fill.background()
        sp.line.color.rgb = _rgb(color)
        sp.line.width = Pt(lw)
        sp.shadow.inherit = False

    def _icon_person(self, cx, cy, s, color, lw):
        r = s * 0.20
        left, top = self._pt(cx - r, cy + s * 0.26 + r)
        head = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top,
                                           _mm(2 * r), _mm(2 * r))
        head.fill.background()
        head.line.color.rgb = _rgb(color)
        head.line.width = Pt(lw)
        head.shadow.inherit = False
        pts = []
        for k in range(13):
            a = math.radians(20 + (160 - 20) * k / 12)
            pts.append((cx + s * 0.36 * math.cos(a), cy - s * 0.22 + s * 0.36 * math.sin(a)))
        self._freeform(pts, color, lw)

    def _icon_rna(self, cx, cy, s, color, lw):
        u = s / 2.2
        stem_l, stem_r = cx - u * 0.55, cx + u * 0.55
        pts = [(stem_l, cy - s / 2), (stem_l, cy + s * 0.10)]
        for k in range(13):
            a = math.pi - math.pi * k / 12
            pts.append((cx + u * 0.8 * math.cos(a), cy + s * 0.32 + s * 0.25 * math.sin(a)))
        pts += [(stem_r, cy + s * 0.10), (stem_r, cy - s / 2)]
        self._freeform(pts, color, lw)
        for yy in (cy + s * 0.10, cy - s * 0.28, cy):
            self.line(stem_l, yy, stem_r, yy, color=color, lw=lw * 0.7)
        self.dot(stem_l, cy - s / 2, lw * 0.45, face=color)
        self.dot(stem_r, cy - s / 2, lw * 0.45, face=color)

    def _icon_check(self, cx, cy, s, color, lw):
        r = s
        left, top = self._pt(cx - r, cy + r)
        ring = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top,
                                           _mm(2 * r), _mm(2 * r))
        ring.fill.solid()
        ring.fill.fore_color.rgb = _rgb("#FFFFFF")
        ring.line.color.rgb = _rgb(color)
        ring.line.width = Pt(lw * 0.9)
        ring.shadow.inherit = False
        self._freeform([(cx - r * 0.5, cy + r * 0.02), (cx - r * 0.1, cy - r * 0.38),
                        (cx + r * 0.55, cy + r * 0.45)], color, lw)

    def _icon_cross(self, cx, cy, s, color, lw):
        r = s
        left, top = self._pt(cx - r, cy + r)
        ring = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top,
                                           _mm(2 * r), _mm(2 * r))
        ring.fill.solid()
        ring.fill.fore_color.rgb = _rgb("#FFFFFF")
        ring.line.color.rgb = _rgb(color)
        ring.line.width = Pt(lw * 0.9)
        ring.shadow.inherit = False
        d = r * 0.5
        self.line(cx - d, cy - d, cx + d, cy + d, color=color, lw=lw)
        self.line(cx - d, cy + d, cx + d, cy - d, color=color, lw=lw)
