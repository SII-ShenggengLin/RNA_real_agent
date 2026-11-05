#!/usr/bin/env python3
"""Build Nature-Methods-style DOCX (and PDF via LibreOffice) from the paper markdown.

Main text : docs/PAPER_DRAFT.md          -> RNADesignAgent_manuscript.docx
Supplement: docs/SUPPLEMENTARY_INFORMATION.md -> RNADesignAgent_supplementary_information.docx

- Header edit-log notes (the marker block before `## Abstract`) are skipped.
- Main-text figures are placed right after the paragraph of their first citation,
  with the full legend under the image (the trailing `## Figure legends` section
  is dissolved); no main-text tables exist.
- SI figures are inserted into their own caption sections; SI Tables S1-S4 are
  rendered as Nature-style ruled tables.
"""
import os
import re
import sys
import math

from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

REPO = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
DOCS = os.path.join(REPO, "rna_agent_system", "docs")
OUT = os.path.join(DOCS, "submission_docx_pdf")
PLOTS = os.path.join(REPO, "rna_agent_system", "experiments", "plots", "output")

MAIN_FIGS = {
    1: os.path.join(REPO, "PPT2", "panels", "fig1_composite.png"),
    2: os.path.join(PLOTS, "fig2_composite.png"),
    3: os.path.join(PLOTS, "fig3_composite.png"),
    4: os.path.join(PLOTS, "fig4_composite.png"),
    5: os.path.join(PLOTS, "fig5_composite.png"),
    6: os.path.join(PLOTS, "fig6_composite.png"),
}
SUPP_FIGS = {
    1: os.path.join(PLOTS, "figS1_tertiary_validity_pool.png"),
    2: os.path.join(PLOTS, "figS2_scoring_direction.png"),
    3: os.path.join(PLOTS, "figS3_ires_panel.png"),
    4: os.path.join(PLOTS, "figS4_aptamer_budget_sweep.png"),
    5: os.path.join(PLOTS, "figS5_advisory_strip.png"),
    6: os.path.join(PLOTS, "figS6_llm_usage_bubble.png"),
}

TEXT_W_MM = 166.0          # A4 210mm - 2 x 22mm margins
USABLE_H_MM = 253.0        # 297 - 2 x 22
CAP_PT = 8.5               # caption font size
CAP_LINE_MM = 3.9          # caption line height estimate

SERIF = "Times New Roman"
SANS = "Arial"
MONO = "Courier New"

# ---------------------------------------------------------------- inline parse
SUP_RE = re.compile(r"<sup>(.*?)</sup>")
MD_RE = re.compile(r"(\*\*.+?\*\*|\*[^*\n]+?\*|`[^`\n]+`)")


def _md_runs(text, sup=False):
    runs = []
    for part in MD_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            runs.append((part[2:-2], {"bold": True, "sup": sup}))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            runs.append((part[1:-1], {"italic": True, "sup": sup}))
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            runs.append((part[1:-1], {"code": True, "sup": sup}))
        else:
            runs.append((part, {"sup": sup}))
    return runs


def tokenize(text):
    """Split text into (text, fmt) runs honouring <sup>, **bold**, *italic*, `code`."""
    out = []
    pos = 0
    for m in SUP_RE.finditer(text):
        if m.start() > pos:
            out.extend(_md_runs(text[pos:m.start()]))
        out.extend(_md_runs(m.group(1), sup=True))
        pos = m.end()
    if pos < len(text):
        out.extend(_md_runs(text[pos:]))
    return out


def plain(text):
    """Markdown/HTML source -> plain text (for length heuristics)."""
    t = SUP_RE.sub(r"\1", text)
    t = MD_RE.sub(lambda m: m.group(0).strip("*`"), t)
    return t

# ---------------------------------------------------------------- doc helpers
def set_font(run, name=SERIF, size=None, bold=None, italic=None):
    run.font.name = name
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), name)


def emit_runs(p, text, size=10.5, font=SERIF):
    for tok, fmt in tokenize(text):
        r = p.add_run(tok)
        if fmt.get("sup"):
            r.font.superscript = True
            set_font(r, font, size)
        elif fmt.get("code"):
            set_font(r, MONO, max(size - 0.5, 6.5))
        else:
            set_font(r, font, size, bold=True if fmt.get("bold") else None,
                     italic=True if fmt.get("italic") else None)


def para(doc, text="", size=10.5, font=SERIF, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
         before=0, after=6, line=1.15, keep_next=False, style=None,
         bold=None, italic=None):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.keep_with_next = keep_next
    if text:
        emit_runs(p, text, size=size, font=font)
        if bold is not None or italic is not None:
            for r in p.runs:
                if bold is not None:
                    r.bold = bold
                if italic is not None:
                    r.italic = italic
    return p


def add_page_number_footer(doc):
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    set_font(run, SANS, 9)
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run._r.append(fld1); run._r.append(instr); run._r.append(fld2)


def enable_line_numbers(doc, count_by="1"):
    sectPr = doc.sections[0]._sectPr
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:countBy"), count_by)
    ln.set(qn("w:restart"), "continuous")
    ln.set(qn("w:distance"), "360")
    cols = sectPr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(ln)
    else:
        sectPr.append(ln)


def setup_styles(doc):
    st = doc.styles["Normal"]
    st.font.name = SERIF
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SERIF)
    st.paragraph_format.widow_control = True

    def heading(name, size, bold=True, italic=False, before=14, after=5):
        h = doc.styles[name]
        h.font.name = SANS
        h.font.size = Pt(size)
        h.font.bold = bold
        h.font.italic = italic
        h.font.color.rgb = RGBColor(0, 0, 0)
        rpr = h.element.get_or_add_rPr()
        rf = rpr.find(qn("w:rFonts"))
        if rf is None:
            rf = OxmlElement("w:rFonts"); rpr.append(rf)
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            rf.set(qn(a), SANS)
        h.paragraph_format.space_before = Pt(before)
        h.paragraph_format.space_after = Pt(after)
        h.paragraph_format.keep_with_next = True

    heading("Heading 1", 11, before=16, after=6)
    heading("Heading 2", 10, before=12, after=4)
    heading("Heading 3", 9.5, italic=True, before=10, after=3)


def setup_page(doc):
    sec = doc.sections[0]
    sec.page_width = Mm(210)
    sec.page_height = Mm(297)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Mm(22))

# ---------------------------------------------------------------- figures
def png_size_mm(path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        w, h = im.size
        dpi = im.info.get("dpi", (1200, 1200))[0] or 1200
    return w / dpi * 25.4, h / dpi * 25.4


def emit_figure(doc, path, caption, native=False):
    """Image + legend as one block, sized so image + caption fit a single page."""
    w_mm, h_mm = png_size_mm(path)
    # conservative caption-height estimate (chars/line and line height tuned so
    # that LibreOffice's justified breaks never push the legend tail overleaf)
    cap_chars_per_line = max(int(TEXT_W_MM / 1.65), 40)
    cap_lines = max(math.ceil(len(plain(caption)) / cap_chars_per_line), 1)
    cap_h = cap_lines * 4.4 + 6
    max_img_h = min(USABLE_H_MM - cap_h - 10, 225.0)
    scale = min(TEXT_W_MM / w_mm, max_img_h / h_mm)
    if native:
        scale = min(scale, 1.0)
    w, h = w_mm * scale, h_mm * scale

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    run = p.add_run()
    run.add_picture(path, width=Mm(w), height=Mm(h))

    cp = para(doc, caption, size=CAP_PT, align=WD_ALIGN_PARAGRAPH.LEFT,
              before=0, after=12, line=1.05)
    cp.paragraph_format.keep_together = True

# ---------------------------------------------------------------- SI tables
def _cell_borders(cell, top=None, bottom=None):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge, sz in (("top", top), ("bottom", bottom)):
        el = OxmlElement(f"w:{edge}")
        if sz is None:
            el.set(qn("w:val"), "nil")
        else:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")
        borders.append(el)
    for edge in ("left", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tcPr.append(borders)


WORD_RE = re.compile(r"[A-Za-z0-9′]+")
CODE_SPAN_RE = re.compile(r"`[^`]+`")
# 8-pt Times: ~1.75 mm per character of the widest word + cell padding, capped
# so one long identifier cannot starve the other columns
WORD_MM_PER_CHAR, WORD_MIN_PAD, WORD_MIN_CAP = 1.75, 4.5, 24.0


def _word_min(rows, c):
    """Width (mm) needed to keep the column's longest plain word on one line
    (code spans excluded -- long registered names may wrap)."""
    longest = 0
    for r in rows:
        text = CODE_SPAN_RE.sub(" ", r[c])
        text = SUP_RE.sub(r"\1", text)
        for w in WORD_RE.findall(text):
            longest = max(longest, len(w))
    return min(longest * WORD_MM_PER_CHAR + WORD_MIN_PAD, WORD_MIN_CAP)


def emit_table(doc, rows):
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    # column width heuristic: longest cell text per column, capped
    weights = []
    for c in range(ncols):
        m = max(len(plain(r[c])) for r in rows)
        weights.append(min(m, 46) ** 0.75)
    total = sum(weights)
    word_mins = [_word_min(rows, c) for c in range(ncols)]
    if sum(word_mins) < TEXT_W_MM:
        # hand each column its no-word-wrap minimum, split the slack by weight
        slack = TEXT_W_MM - sum(word_mins)
        widths = [word_mins[c] + slack * weights[c] / total for c in range(ncols)]
    else:
        widths = [max(TEXT_W_MM * w / total, 10.0) for w in weights]
        over = sum(widths) - TEXT_W_MM
        if over > 0:
            widths[weights.index(max(weights))] -= over

    t = doc.add_table(rows=len(rows), cols=ncols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)

    for ri, row in enumerate(rows):
        tr = t.rows[ri]
        trPr = tr._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit"); trPr.append(cant)
        if ri == 0:
            th = OxmlElement("w:tblHeader"); trPr.append(th)
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.width = Mm(widths[ci])
            if ri == 0:
                _cell_borders(cell, top=8, bottom=4)
            elif ri == len(rows) - 1:
                _cell_borders(cell, bottom=8)
            else:
                _cell_borders(cell)
            p = cell.paragraphs[0]
            pf = p.paragraph_format
            pf.space_before = Pt(1.5)
            pf.space_after = Pt(1.5)
            pf.line_spacing = 1.0
            pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
            emit_runs(p, val, size=8, font=SERIF)
            if ri == 0:
                for r in p.runs:
                    r.bold = True
    para(doc, "", after=8)

# ---------------------------------------------------------------- markdown parse
def read_blocks(path, start_line=None):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if start_line is not None:
        lines = lines[start_line - 1:]
    blocks, table = [], None
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if table is None:
                table = [cells]
            else:
                table.append(cells)
            continue
        if table is not None:
            blocks.append(("table", table)); table = None
        if not line.strip() or line.strip() == "---":
            continue
        if line.startswith("#### "):
            blocks.append(("h3", line[5:].strip()))
        elif line.startswith("### "):
            blocks.append(("h2", line[4:].strip()))
        elif line.startswith("## "):
            blocks.append(("h1", line[3:].strip()))
        elif line.startswith("# "):
            blocks.append(("title", line[2:].strip()))
        elif line.startswith("- "):
            blocks.append(("li", line[2:].strip()))
        else:
            blocks.append(("p", line.strip()))
    if table is not None:
        blocks.append(("table", table))
    return blocks


CAP_RE = re.compile(r"^\*\*Fig\. (\d+) \| (.+?)\*\*\s*(.*)$")
REF_RE = re.compile(r"^(\d{1,2})\. (.*)$")

# ---------------------------------------------------------------- main paper
def build_main():
    doc = Document()
    setup_page(doc)
    setup_styles(doc)
    add_page_number_footer(doc)
    enable_line_numbers(doc)

    md_path = os.path.join(DOCS, "PAPER_DRAFT.md")
    with open(md_path, encoding="utf-8") as f:
        md_lines = f.read().split("\n")
    # from `## Abstract` (skip the header edit-log block, located dynamically)
    blocks = read_blocks(md_path, start_line=md_lines.index("## Abstract") + 1)
    title = md_lines[0].lstrip("# ").strip()
    para(doc, title, size=16, font=SERIF, align=WD_ALIGN_PARAGRAPH.LEFT,
         after=14, line=1.1)

    # dissolve the trailing Figure-legends section into per-figure captions
    caps, body = {}, []
    in_leg = False
    for kind, val in blocks:
        if kind == "h1" and val == "Figure legends":
            in_leg = True
            continue
        if in_leg:
            if kind == "p":
                m = CAP_RE.match(val)
                if m:
                    caps[int(m.group(1))] = f"**Fig. {m.group(1)} | {m.group(2)}** {m.group(3)}".strip()
            continue
        if kind == "p" and val.startswith("*End of draft"):
            continue
        body.append((kind, val))

    assert set(caps) == set(MAIN_FIGS), f"captions found: {sorted(caps)}"

    placed = set()
    in_refs = False
    for kind, val in body:
        if kind == "h1" and val == "References":
            in_refs = True
            doc.add_heading(val, level=1)
            continue
        if kind == "h1":
            doc.add_heading(val, level=1)
            continue
        if kind == "h2":
            doc.add_heading(val, level=2)
            continue
        if kind == "h3":
            doc.add_heading(val, level=3)
            continue
        if kind == "table":
            emit_table(doc, val)
            continue
        # paragraph
        if in_refs and REF_RE.match(val):
            m = REF_RE.match(val)
            p = para(doc, f"{m.group(1)}. {m.group(2)}", size=9,
                     align=WD_ALIGN_PARAGRAPH.LEFT, after=3, line=1.05)
            p.paragraph_format.left_indent = Mm(5.5)
            p.paragraph_format.first_line_indent = Mm(-5.5)
            continue
        para(doc, val)
        # first-citation figure placement
        for n in sorted(MAIN_FIGS):
            if n in placed:
                continue
            if re.search(rf"Fig\. {n}(?!\d)", val):
                emit_figure(doc, MAIN_FIGS[n], caps[n])
                placed.add(n)

    missing = set(MAIN_FIGS) - placed
    assert not missing, f"figures never cited in body: {sorted(missing)}"
    return doc

# ---------------------------------------------------------------- supplementary
def build_supp():
    doc = Document()
    setup_page(doc)
    setup_styles(doc)
    add_page_number_footer(doc)

    blocks = read_blocks(os.path.join(DOCS, "SUPPLEMENTARY_INFORMATION.md"))
    fig_stage = {}  # fig number awaiting image insertion (current H3 figure section)
    in_refs = False
    seen_title = False
    for i, (kind, val) in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else (None, None)
        if kind == "title":
            para(doc, val, size=14, font=SANS, bold=True,
                 align=WD_ALIGN_PARAGRAPH.LEFT, after=8)
            seen_title = True
            continue
        if kind == "h1":
            in_refs = val == "References"
            doc.add_heading(val, level=1)
            continue
        if kind == "h2":
            m = re.match(r"Supplementary Fig\. S(\d+)\.", val)
            fig_stage = {}
            if m:
                fig_stage = {"n": int(m.group(1)), "title": val}
            doc.add_heading(val, level=2)
            continue
        if kind == "h3":
            doc.add_heading(val, level=3)
            continue
        if kind == "li":
            para(doc, "•  " + val, size=10, align=WD_ALIGN_PARAGRAPH.LEFT,
                 after=2, line=1.1)
            continue
        if kind == "table":
            emit_table(doc, val)
            continue
        # paragraph
        if seen_title:  # paper-title subtitle line
            seen_title = False
            para(doc, val, size=12, font=SERIF, bold=True,
                 align=WD_ALIGN_PARAGRAPH.LEFT, after=12)
            continue
        if in_refs and REF_RE.match(val):
            m = REF_RE.match(val)
            p = para(doc, f"{m.group(1)}. {m.group(2)}", size=9,
                     align=WD_ALIGN_PARAGRAPH.LEFT, after=3, line=1.05)
            p.paragraph_format.left_indent = Mm(5.5)
            p.paragraph_format.first_line_indent = Mm(-5.5)
            continue
        if fig_stage.get("n"):  # first paragraph in this figure section = caption
            n = fig_stage.pop("n")
            assert n in SUPP_FIGS, f"no image for Suppl. Fig. S{n}"
            emit_figure(doc, SUPP_FIGS[n], val, native=True)
            continue
        para(doc, val)

    return doc

# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = [("RNADesignAgent_manuscript", build_main),
            ("RNADesignAgent_supplementary_information", build_supp)]
    for name, builder in jobs:
        doc = builder()
        doc.core_properties.title = {
            "RNADesignAgent_manuscript":
                "A multi-agent system for RNA design with capability-gated "
                "prediction and constraint-navigated generation",
            "RNADesignAgent_supplementary_information":
                "Supplementary information: A multi-agent system for RNA design "
                "with capability-gated prediction and constraint-navigated generation",
        }[name]
        path = os.path.join(OUT, f"{name}.docx")
        doc.save(path)
        print(f"saved {path} ({os.path.getsize(path)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
