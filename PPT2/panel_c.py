"""Fig 1c — Platform at a glance: KPI radar + production-audit donut.

Left: five scale spokes (11 workflows · 41 tools · 21 services · 210 tasks ·
210/210 completed). Right: audit-trail composition from the frozen Exp-24
production slice (24,897 events = 19,848 tool calls + 4,862 gate decisions +
187 ranking assemblies). 57 × 46 mm.
"""
import math
import style as S
from matplotlib.patches import Wedge, Circle

KPIS = [
    ("workflows", 11, 11.0),
    ("tools", 41, 45.0),
    ("services", 21, 25.0),
    ("tasks", 210, 210.0),
    ("completed", 210, 210.0),
]
AUDIT = [
    ("tool calls", 19848, S.C_SLATE),
    ("gate decisions", 4862, S.C_TERRACOTTA),
    ("assemblies", 187, S.C_SAND),
]


def main():
    W, H = 57, 46
    fig, ax = S.canvas(W, H)

    # ---- radar (drawn manually on the mm axes) -----------------------------
    cx, cy, r = 16.5, 26.5, 7.6
    n = len(KPIS)
    S.txt(ax, cx, 42.8, "scale", size=6.0, weight="bold", color=S.C_SLATE)
    for grid_frac in (0.33, 0.66, 1.0):
        pts = []
        for i in range(n):
            a = math.pi / 2 - 2 * math.pi * i / n
            pts.append((cx + r * grid_frac * math.cos(a), cy + r * grid_frac * math.sin(a)))
        pts.append(pts[0])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=S.GRID, lw=0.4,
                zorder=2)
    vals, labels = [], []
    for i, (name, v, mx) in enumerate(KPIS):
        a = math.pi / 2 - 2 * math.pi * i / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        S.plain_line(ax, (cx, cy), (x, y), color=S.GRID, lw=0.4)
        vals.append(v / mx)
        lx, ly = cx + (r + 1.1) * math.cos(a), cy + (r + 1.1) * math.sin(a)
        ha = "center"
        if math.cos(a) > 0.3:
            ha = "left"
        elif math.cos(a) < -0.3:
            ha = "right"
        va = "center"
        if math.sin(a) > 0.3:
            va = "bottom"
        elif math.sin(a) < -0.3:
            va = "top"
        vtxt = f"{v}" + ("/210" if name == "completed" else "")
        S.txt(ax, lx, ly + 0.85, vtxt, size=5.4, weight="bold", ha=ha, va=va,
              color=S.C_SLATE)
        S.txt(ax, lx, ly - 0.85, name, size=5.0, ha=ha, va=va, color=S.C_DARK)
    poly = [(cx + r * f * math.cos(math.pi / 2 - 2 * math.pi * i / n),
             cy + r * f * math.sin(math.pi / 2 - 2 * math.pi * i / n))
            for i, f in enumerate(vals)]
    poly.append(poly[0])
    ax.plot([p[0] for p in poly], [p[1] for p in poly], color=S.C_GREY_BLUE,
            lw=1.0, zorder=4)
    ax.fill([p[0] for p in poly], [p[1] for p in poly],
            color=S.C_GREY_BLUE, alpha=0.22, zorder=3)

    # ---- audit donut ---------------------------------------------------------
    dx, dy, ro, ri = 41.0, 29.5, 6.6, 3.7
    total = sum(c for _, c, _ in AUDIT)
    S.txt(ax, dx, 42.8, "audit trail", size=6.0, weight="bold", color=S.C_SLATE)
    a0 = 90.0
    for name, count, col in AUDIT:
        sweep = 360.0 * count / total
        w = Wedge((dx, dy), ro, a0 - sweep, a0, facecolor=col, edgecolor="white",
                  lw=0.5, zorder=3)
        ax.add_patch(w)
        a0 -= sweep
    ax.add_patch(Circle((dx, dy), ri, facecolor="white", edgecolor="none", zorder=4))
    S.txt(ax, dx, dy + 0.8, "24,897", size=5.6, weight="bold", zorder=5)
    S.txt(ax, dx, dy - 1.3, "events", size=5.0, color=S.C_DARK, zorder=5)

    # legend
    ly = 17.0
    for name, count, col in AUDIT:
        ax.add_patch(Circle((31.6, ly), 0.62, facecolor=col, edgecolor="none",
                            zorder=5))
        pct = 100.0 * count / total
        S.txt(ax, 33.2, ly, f"{name} · {count:,} ({pct:.1f}%)", size=4.9,
              ha="left", zorder=5)
        ly -= 2.9

    # ---- source note ----------------------------------------------------------
    S.txt(ax, 28.5, 3.2, "frozen Exp-24 production slice · 241 runs",
          size=5.0, color=S.C_DARK, style="italic")

    __import__("qa_check").qa(fig, ax, W, H)
    S.save(fig, "c")


if __name__ == "__main__":
    main()
