"""Programmatic text-collision QA for schematic panels.

Import-free helper: run as a module inside each panel script after building
`fig, ax` (call `qa(fig, ax, W, H)` before save) — reports text-text overlaps
and out-of-canvas text. Line/patch collisions remain for visual QA.
"""
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox


def _union_bbox(b1, b2):
    return Bbox.intersection(b1, b2)


def qa(fig, ax, W, H, verbose=True):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    items = []
    for t in ax.texts:
        bb = t.get_window_extent(renderer=renderer)
        items.append((t.get_text(), bb))
    problems = []
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = items[i][1], items[j][1]
            inter = Bbox.intersection(a, b)
            if inter is not None and inter.width > 0 and inter.height > 0:
                # shrink slightly to ignore pure anti-alias touching
                aw, ah = a.width, a.height
                ix, iy = inter.width, inter.height
                if ix > 1.0 and iy > 1.0:  # >1 px overlap
                    problems.append((items[i][0], items[j][0],
                                     round(ix, 1), round(iy, 1)))
    # out of canvas (text bboxes partially outside the axes bbox in px)
    ax_bb = ax.get_window_extent(renderer=renderer)
    for txts, bb in items:
        if bb.x0 < ax_bb.x0 - 1 or bb.x1 > ax_bb.x1 + 1 or \
           bb.y0 < ax_bb.y0 - 1 or bb.y1 > ax_bb.y1 + 1:
            problems.append((txts, "<<OUT-OF-CANVAS>>", 0, 0))
    if verbose:
        if not problems:
            print("QA text: OK (no text-text overlap, nothing clipped)")
        else:
            print(f"QA text: {len(problems)} problem(s):")
            for p in problems:
                print("   ", p)
    return problems
