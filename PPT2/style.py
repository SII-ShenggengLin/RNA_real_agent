"""Shared schematic style for Fig 1 (PPT2) — palette rev 7, mm-coordinate canvas.

Conventions (fig1_design_notes.md):
  * every colour from the mandated twelve-colour Morandi set (verbatim);
  * arrow semantics: solid slate = data/execution flow, dashed terracotta =
    governance/gating, dotted dark-warm-grey = advisory-only;
  * cards: rounded rectangles, tinted fills (palette colour at low alpha),
    same-family 0.8-pt edges;
  * text: Arial, 6 pt ink for labels (5 pt secondary), panel letters drawn at
    assembly time only.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Ellipse, Arc, Rectangle, Wedge, PathPatch
from matplotlib.path import Path
import math
import os

# ---------------------------------------------------------------- palette ---
PALETTE = ["#B5838D", "#D3B5B0", "#C08B7C", "#D9C3A9", "#CDBF9E", "#A3B18A",
           "#8DA290", "#8FA6BB", "#6B7B8D", "#A99AAF", "#B7B0A2", "#7A7672"]
C_MAUVE_PINK = "#B5838D"
C_ROSE = "#D3B5B0"
C_TERRACOTTA = "#C08B7C"
C_SAND = "#D9C3A9"
C_KHAKI = "#CDBF9E"
C_SAGE = "#A3B18A"
C_GREY_GREEN = "#8DA290"
C_GREY_BLUE = "#8FA6BB"
C_SLATE = "#6B7B8D"
C_MAUVE_GREY = "#A99AAF"
C_WARM_GREY = "#B7B0A2"
C_DARK = "#7A7672"

INK = "#000000"          # all text pure black (house rule)
INK_HEAD = "#1A1A1A"     # panel letters
GRID = "#D9D9D9"

# Workflow colours (palette.py WORKFLOW_COLORS, unchanged).
WORKFLOW_COLORS = {
    "mrna_cds_design": "#C08B7C", "full_length_mrna_design": "#A3B18A",
    "mrna_sequence_scoring": "#D9C3A9", "sirna_design": "#6B7B8D",
    "sgrna_design": "#D3B5B0", "rna_secondary_structure_design": "#8DA290",
    "rna_tertiary_structure_design": "#B5838D", "rna_aptamer_design": "#8FA6BB",
    "rna_small_molecule_interaction": "#CDBF9E", "aso_target_screening": "#A99AAF",
    "ires_prediction": "#B7B0A2",
}

matplotlib.rcParams.update({
    "font.family": "Arial",
    "font.size": 6,
    "text.color": INK,
    "axes.edgecolor": INK,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

PANELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panels")
os.makedirs(PANELS_DIR, exist_ok=True)


# ---------------------------------------------------------------- canvas ---
def canvas(w_mm: float, h_mm: float):
    """Full-bleed figure whose axes use mm coordinates (isotropic)."""
    fig = plt.figure(figsize=(w_mm / 25.4, h_mm / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_mm)
    ax.set_ylim(0, h_mm)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    return fig, ax


def save(fig, name: str, dpi: int = 1200, ppt_dpi: int = 300):
    """Save panels/<name>.pdf (vector) + .png (1200 dpi) + _ppt.png (300 dpi)."""
    pdf = os.path.join(PANELS_DIR, name + ".pdf")
    png = os.path.join(PANELS_DIR, name + ".png")
    ppt = os.path.join(PANELS_DIR, name + "_ppt.png")
    fig.savefig(pdf)
    fig.savefig(png, dpi=dpi)
    fig.savefig(ppt, dpi=ppt_dpi)
    plt.close(fig)
    print("saved", pdf, png, ppt)


# ------------------------------------------------------------- primitives ---
def txt(ax, x, y, s, *, size=6, weight="normal", color=INK, ha="center",
        va="center", style=None, rotation=0, zorder=6, linespacing=1.25):
    return ax.text(x, y, s, fontsize=size, fontweight=weight, color=color,
                   ha=ha, va=va, fontstyle=style, rotation=rotation,
                   zorder=zorder, linespacing=linespacing)


def card(ax, x, y, w, h, *, face="#FFFFFF", alpha=0.18, edge=None, lw=0.8,
         radius=0.9, dashed=False, zorder=3, fill=True):
    """Rounded card in mm; edge defaults to the face colour at full strength."""
    edge = edge or face
    box = FancyBboxPatch((x + radius, y + radius), w - 2 * radius, h - 2 * radius,
                         boxstyle=f"round,pad={radius}",
                         facecolor=to_rgba(face, alpha) if fill else "none",
                         edgecolor=edge, linewidth=lw,
                         linestyle=(0, (2.2, 1.4)) if dashed else "solid",
                         zorder=zorder, joinstyle="round")
    ax.add_patch(box)
    return box


def zone(ax, x, y, w, h, *, face, alpha=0.07, radius=1.4, lw=0.0, zorder=1):
    """Soft background region grouping related cards."""
    box = FancyBboxPatch((x + radius, y + radius), w - 2 * radius, h - 2 * radius,
                         boxstyle=f"round,pad={radius}",
                         facecolor=to_rgba(face, alpha), edgecolor="none",
                         linewidth=lw, zorder=zorder)
    ax.add_patch(box)
    return box


def flow(ax, p0, p1, *, kind="data", lw=1.0, ms=7.5, rad=0.0,
         both=False, zorder=4, shrink=0.6):
    """Semantic arrows. kind: data | gate | advisory."""
    styles = {
        "data": dict(color=C_SLATE, linestyle="solid"),
        "gate": dict(color=C_TERRACOTTA, linestyle=(0, (2.6, 1.6))),
        "advisory": dict(color=C_DARK, linestyle=(0, (1.0, 1.5))),
    }
    kw = styles[kind]
    arr = FancyArrowPatch(p0, p1, arrowstyle="-|>" if not both else "<|-|>",
                          mutation_scale=ms, linewidth=lw, shrinkA=shrink,
                          shrinkB=shrink, connectionstyle=f"arc3,rad={rad}",
                          zorder=zorder, **kw)
    ax.add_patch(arr)
    return arr


def plain_line(ax, p0, p1, *, color=C_SLATE, lw=0.5, linestyle="solid", zorder=4):
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=color, lw=lw,
            linestyle=linestyle, zorder=zorder, solid_capstyle="round")


# ------------------------------------------------------------------ icons ---
def icon_rna(ax, cx, cy, s, color, lw=0.7, zorder=5):
    """Stylized RNA stem-loop, height s (mm)."""
    u = s / 2.2  # horizontal half-width
    stem_l, stem_r = cx - u * 0.55, cx + u * 0.55
    top = cy + s / 2
    ax.plot([stem_l, stem_l], [cy - s / 2, cy + s * 0.10], color=color, lw=lw,
            zorder=zorder, solid_capstyle="round")
    ax.plot([stem_r, stem_r], [cy - s / 2, cy + s * 0.10], color=color, lw=lw,
            zorder=zorder, solid_capstyle="round")
    ax.add_patch(Arc((cx, cy + s * 0.32), u * 1.6, s * 0.5, theta1=0, theta2=180,
                     edgecolor=color, lw=lw, zorder=zorder))
    ax.plot([stem_l, stem_r], [cy + s * 0.10, cy + s * 0.10], color=color, lw=lw * 0.8, zorder=zorder)
    for yy in (cy - s * 0.28, cy):
        ax.plot([stem_l, stem_r], [yy, yy], color=color, lw=lw * 0.7, zorder=zorder)
    ax.plot([stem_l], [cy - s / 2], marker="o", ms=lw * 1.6, color=color, zorder=zorder)
    ax.plot([stem_r], [cy - s / 2], marker="o", ms=lw * 1.6, color=color, zorder=zorder)


def icon_doc(ax, cx, cy, s, color, lw=0.7, zorder=5, fold=0.22):
    w = s * 0.78
    x0, y0 = cx - w / 2, cy - s / 2
    f = s * fold
    verts = [(x0, y0), (x0, y0 + s), (x0 + w - f, y0 + s), (x0 + w, y0 + s - f),
             (x0 + w, y0), (x0, y0)]
    ax.add_patch(PathPatch(Path(verts), facecolor="none", edgecolor=color,
                           lw=lw, zorder=zorder))
    ax.plot([x0 + w - f, x0 + w - f], [y0 + s - f, y0 + s], color=color, lw=lw * 0.8, zorder=zorder)
    for i in range(3):
        yy = y0 + s * (0.28 + 0.19 * i)
        ax.plot([x0 + w * 0.18, x0 + w * (0.82 if i == 2 else 0.62)], [yy, yy],
                color=color, lw=lw * 0.7, zorder=zorder)


def icon_db(ax, cx, cy, w, h, color, lw=0.7, zorder=5):
    """Database cylinder."""
    ry = h * 0.16
    body = Rectangle((cx - w / 2, cy - h / 2 + ry), w, h - 2 * ry,
                     facecolor="none", edgecolor="none", zorder=zorder)
    ax.add_patch(body)
    ax.plot([cx - w / 2, cx - w / 2], [cy - h / 2 + ry, cy + h / 2 - ry], color=color, lw=lw, zorder=zorder)
    ax.plot([cx + w / 2, cx + w / 2], [cy - h / 2 + ry, cy + h / 2 - ry], color=color, lw=lw, zorder=zorder)
    ax.add_patch(Ellipse((cx, cy + h / 2 - ry), w, 2 * ry, facecolor="none",
                         edgecolor=color, lw=lw, zorder=zorder))
    ax.add_patch(Arc((cx, cy - h / 2 + ry), w, 2 * ry, theta1=180, theta2=360,
                     edgecolor=color, lw=lw, zorder=zorder))
    ax.add_patch(Arc((cx, cy + ry * 0.2), w, 2 * ry, theta1=180, theta2=360,
                     edgecolor=color, lw=lw * 0.7, zorder=zorder))


def icon_gear(ax, cx, cy, r, color, lw=0.7, zorder=5, teeth=8):
    ax.add_patch(Circle((cx, cy), r * 0.52, facecolor="none", edgecolor=color,
                        lw=lw, zorder=zorder))
    ax.add_patch(Circle((cx, cy), r * 0.16, facecolor=color, edgecolor=color,
                        lw=0, zorder=zorder))
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        x0, y0 = r * 0.62 * math.cos(a), r * 0.62 * math.sin(a)
        x1, y1 = r * 0.95 * math.cos(a), r * 0.95 * math.sin(a)
        ax.plot([cx + x0, cx + x1], [cy + y0, cy + y1], color=color, lw=lw * 1.6,
                zorder=zorder, solid_capstyle="butt")


def icon_person(ax, cx, cy, s, color, lw=0.7, zorder=5):
    ax.add_patch(Circle((cx, cy + s * 0.26), s * 0.20, facecolor="none",
                        edgecolor=color, lw=lw, zorder=zorder))
    ax.add_patch(Arc((cx, cy - s * 0.22), s * 0.72, s * 0.72, theta1=20, theta2=160,
                     edgecolor=color, lw=lw, zorder=zorder))


def icon_check(ax, cx, cy, r, color=C_SAGE, lw=1.0, zorder=6):
    ax.add_patch(Circle((cx, cy), r, facecolor="white", edgecolor=color,
                        lw=lw * 0.9, zorder=zorder))
    ax.plot([cx - r * 0.5, cx - r * 0.1, cx + r * 0.55],
            [cy + r * 0.02, cy - r * 0.38, cy + r * 0.45],
            color=color, lw=lw, zorder=zorder + 1, solid_joinstyle="round")


def icon_cross(ax, cx, cy, r, color=C_TERRACOTTA, lw=1.0, zorder=6):
    ax.add_patch(Circle((cx, cy), r, facecolor="white", edgecolor=color,
                        lw=lw * 0.9, zorder=zorder))
    d = r * 0.5
    ax.plot([cx - d, cx + d], [cy - d, cy + d], color=color, lw=lw, zorder=zorder + 1)
    ax.plot([cx - d, cx + d], [cy + d, cy - d], color=color, lw=lw, zorder=zorder + 1)


def ref_chip(ax, x, y, letter, r=1.05, color=C_SLATE):
    """Circled cross-reference letter pointing at another panel."""
    ax.add_patch(Circle((x, y), r, facecolor="white", edgecolor=color,
                        lw=0.6, zorder=7))
    txt(ax, x, y - 0.05, letter, size=5.5, weight="bold", color=color, zorder=8)


def badge(ax, x, y, w, h, text, *, color, icon=None, size=5.4, weight="bold", alpha=0.15):
    card(ax, x, y, w, h, face=color, alpha=alpha, lw=0.6, radius=0.7)
    tx = x + w / 2 + (1.4 if icon else 0)
    if icon == "check":
        icon_check(ax, x + 2.0, y + h / 2, 1.0, color=C_SAGE, lw=0.9)
        tx = x + w / 2 + 1.4
    txt(ax, tx, y + h / 2, text, size=size, weight=weight)
