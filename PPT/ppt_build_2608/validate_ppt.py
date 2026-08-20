# -*- coding: utf-8 -*-
"""Validate the generated PPTX: in-bounds shapes, picture overlaps, rough text
overflow estimate (CJK=1em, latin≈0.52em per char, line height 1.35×size)."""
import math
from pptx import Presentation
from pptx.util import Emu

PATH = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent/PPT/组会报告-林圣庚-2026年8月-智能体进展汇报.pptx"
PAGE_W, PAGE_H = 13.333, 7.5

def emu2in(v):
    return Emu(v).inches

def est_lines(text, size, box_w_in):
    """rough estimate of wrapped line count"""
    width_pt = sum(size if ord(c) > 0x2E7F else size * 0.52 for c in text)
    box_pt = (box_w_in - 0.16) * 72  # minus margins
    return max(1, math.ceil(width_pt / max(box_pt, 1)))

prs = Presentation(PATH)
issues = []
for si, slide in enumerate(prs.slides, 1):
    pics = []
    for shp in slide.shapes:
        x, y = emu2in(shp.left), emu2in(shp.top)
        w, h = emu2in(shp.width), emu2in(shp.height)
        # bounds
        if x < -0.01 or y < -0.01 or x + w > PAGE_W + 0.01 or y + h > PAGE_H + 0.01:
            issues.append(f"S{si}: OUT-OF-BOUNDS {shp.shape_type} at ({x:.2f},{y:.2f},{w:.2f},{h:.2f})")
        if shp.shape_type == 13:  # picture
            pics.append((x, y, w, h))
        # text overflow estimate
        if shp.has_text_frame and shp.text_frame.word_wrap:
            box_w = w
            total_h = 0.0
            for p in shp.text_frame.paragraphs:
                text = "".join(r.text for r in p.runs)
                if not text:
                    continue
                size = max((r.font.size.pt if r.font.size else 18) for r in p.runs)
                ls = p.line_spacing if p.line_spacing else 1.12
                n = est_lines(text, size, box_w)
                total_h += n * size * ls / 72 + (p.space_after.pt if p.space_after else 6) / 72
            if total_h > h + 0.05:
                issues.append(f"S{si}: TEXT-OVERFLOW? need~{total_h:.2f}in > box {h:.2f}in :: {text[:30]}...")
    # picture-picture overlap
    for i in range(len(pics)):
        for j in range(i + 1, len(pics)):
            a, b = pics[i], pics[j]
            ox = min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0])
            oy = min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1])
            if ox > 0.02 and oy > 0.02:
                issues.append(f"S{si}: PIC OVERLAP {a} vs {b}")

print(f"slides: {len(prs.slides.__iter__.__self__._sldIdLst)}")
if issues:
    print(f"{len(issues)} potential issues:")
    for it in issues:
        print(" -", it)
else:
    print("OK: all shapes in bounds, no picture overlaps, no estimated text overflow")
