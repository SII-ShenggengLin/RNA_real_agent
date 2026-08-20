"""Shared figure style for the RNADesignAgent paper (paper_v5).

Design contract (Nature Methods conventions + reference-paper survey):
  * Font: Arial (Nature Methods requires Arial or Helvetica), 6-8 pt at final scale.
  * Palette: Morandi (muted, grayed) tones on a white background. One dominant
    cool hue (mist blue) carries "the system / gated / ours"; terracotta carries
    the contrast arm (ungated / rule / failure); neutral grey carries baselines.
  * A strict arm-to-colour code is shared by EVERY figure (survey takeaway):
      navigation/gated  -> MORANDI["blue"]
      rule/ungated      -> MORANDI["terra"]
      designed/system   -> MORANDI["blue"]
      wild-type         -> MORANDI["green"]
      random/null       -> MORANDI["grey"]
  * Composite assembly happens in figN/assemble.py; panel letters are drawn at
    assembly time only, so single panels stay letter-free.

Every panel script imports this module (path-bootstrapped) and calls
``new_panel``/``save_panel`` so fonts, sizes and colours cannot drift.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

# ----------------------------------------------------------------------------- palette
MORANDI = {
    "blue":     "#7E9BB3",   # mist blue        - system / gated / navigation arm
    "slate":    "#5F7688",   # deep mist blue   - emphasis variant of blue
    "terra":    "#BC8E7F",   # terracotta       - contrast arm (rule / ungated)
    "brick":    "#A9756A",   # deep terracotta  - emphasis variant of terra
    "green":    "#9BAD9E",   # sage green       - wild-type / certified-oracle
    "sage":     "#7E9384",   # deep sage        - emphasis variant of green
    "lavender": "#9E9BBE",   # grey violet      - third categorical
    "sand":     "#C8B482",   # oat gold         - fourth categorical
    "teal":     "#87A6A0",   # grey teal        - fifth categorical
    "rose":     "#C79EA6",   # rose grey        - sixth categorical
    "plum":     "#A78EA3",   # plum grey        - seventh categorical
    "grey":     "#A8ABA6",   # neutral grey     - null / baseline / random
    "grey_dk":  "#7C807B",   # dark neutral     - baseline emphasis
}

# ordered categorical series (max 8 before repeating markers)
SERIES = ["blue", "terra", "green", "lavender", "sand", "teal", "rose", "plum"]
C = [MORANDI[k] for k in SERIES]

INK = "#3B4654"          # near-black slate for text and axes
INK_SOFT = "#6B7684"     # secondary text
PAPER = "#FFFFFF"
CREAM = "#F5F2EB"        # schematic panel wash
CREAM_DK = "#EAE5DA"     # schematic box fill, second level
GRID = "#E6E2D9"         # background grid

PASS = MORANDI["green"]      # gate passed
FAIL = MORANDI["terra"]      # gate failed
NULLC = MORANDI["grey"]      # null / chance

# sequential Morandi colormap: cream -> mist blue (for magnitude heatmaps)
SEQ_CMAP = LinearSegmentedColormap.from_list(
    "morandi_seq", ["#FBF9F4", "#E3E7EC", "#B7C6D4", "#7E9BB3", "#5F7688", "#43586B"])

# diverging Morandi colormap: terracotta <- off-white -> mist blue (signed effects)
DIV_CMAP = LinearSegmentedColormap.from_list(
    "morandi_div", ["#A9756A", "#D9C4BC", "#F7F4EE", "#C2D0DC", "#5F7688"])

# grade colours for the capability map (two-sided: verified vs failed vs unprofiled)
GRADE = {
    "verified":       MORANDI["green"],
    "failed":         MORANDI["terra"],
    "unprofiled":     MORANDI["grey"],
    "degraded":       MORANDI["sand"],
}

# ----------------------------------------------------------------------------- rcParams
MM = 1.0 / 25.4                       # mm -> inch
DOUBLE_COL = 183 * MM                 # Nature Methods double column
SINGLE_COL = 89 * MM

mpl.rcParams.update({
    # fonts ------------------------------------------------------------------
    "font.family": "Arial",
    "font.size": 6.0,
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "axes.titlesize": 6.5,
    "axes.labelsize": 6.0,
    "xtick.labelsize": 5.5,
    "ytick.labelsize": 5.5,
    "legend.fontsize": 5.5,
    "figure.titlesize": 7.0,
    # axes -------------------------------------------------------------------
    "axes.linewidth": 0.6,
    "axes.edgecolor": INK_SOFT,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.prop_cycle": mpl.cycler(color=C),
    "axes.spines.top": False,
    "axes.spines.right": False,
    # ticks ------------------------------------------------------------------
    "xtick.color": INK_SOFT,
    "ytick.color": INK_SOFT,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.size": 2.0,
    "ytick.major.size": 2.0,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.pad": 1.8,
    "ytick.major.pad": 1.8,
    # grid / background --------------------------------------------------------
    "axes.grid": False,
    "grid.color": GRID,
    "grid.linewidth": 0.4,
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    # lines / patches ----------------------------------------------------------
    "lines.linewidth": 1.0,
    "lines.markersize": 3.0,
    "lines.solid_capstyle": "round",
    "patch.linewidth": 0.5,
    "patch.edgecolor": "none",
    # export -------------------------------------------------------------------
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "legend.frameon": False,
    "legend.handlelength": 1.2,
    "legend.handletextpad": 0.5,
    "legend.borderaxespad": 0.2,
})

# significance asterisk convention (survey-consistent)
def stars(p: float) -> str:
    if p < 1e-4:
        return "****"
    if p < 1e-3:
        return "***"
    if p < 1e-2:
        return "**"
    if p < 0.05:
        return "*"
    return "NS"

# ----------------------------------------------------------------------------- helpers
def new_panel(w_mm: float, h_mm: float):
    """Create a single-panel figure sized in millimetres."""
    fig, ax = plt.subplots(figsize=(w_mm * MM, h_mm * MM))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.85, bottom=0.16)
    return fig, ax


def new_free(w_mm: float, h_mm: float):
    """Create a figure with no default axes (schematics / free-form panels)."""
    fig = plt.figure(figsize=(w_mm * MM, h_mm * MM))
    return fig


def save_panel(fig, out_base: str, dpi: int = 450):
    """Save one panel as PDF (vector, for assembly) + PNG (visual QA)."""
    import pathlib
    pathlib.Path(out_base).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_base + ".pdf")
    fig.savefig(out_base + ".png", dpi=dpi)
    plt.close(fig)


def style_cat_ax(ax):
    """Tidy a categorical axis: no ticks, keep left spine."""
    ax.tick_params(length=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return ax


def despine(ax, left=True, bottom=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if not left:
        ax.spines["left"].set_visible(False)
    if not bottom:
        ax.spines["bottom"].set_visible(False)
    return ax


def boxplot_morandi(ax, data, positions, colors, width=0.55, scatter=True,
                    scatter_size=2.0, whisk=0.6):
    """Muted box-and-whiskers with optional jittered points on top."""
    bp = ax.boxplot(data, positions=positions, widths=width, showfliers=False,
                    whis=1.5, patch_artist=True,
                    medianprops=dict(color=INK, lw=0.8),
                    boxprops=dict(lw=0.5), whiskerprops=dict(lw=0.5, color=INK_SOFT),
                    capprops=dict(lw=0.5, color=INK_SOFT))
    for patch, col in zip(bp["boxes"], colors):
        patch.set_facecolor(col)
        patch.set_alpha(0.45)
        patch.set_edgecolor(INK_SOFT)
    if scatter:
        import numpy as np
        rng = np.random.default_rng(7)
        for d, x, col in zip(data, positions, colors):
            if len(d) == 0:
                continue
            jitter = rng.uniform(-width * 0.32, width * 0.32, size=len(d))
            ax.scatter(np.full(len(d), x) + jitter, d, s=scatter_size, color=col,
                       edgecolors="none", zorder=3, alpha=0.85)
    return bp


def sig_bracket(ax, x0, x1, y, text, lw=0.6, text_size=5.5, color=INK):
    """Draw a significance bracket between two x positions."""
    h = 0.0
    ax.plot([x0, x0, x1, x1], [y - h, y, y, y - h], lw=lw, color=color,
            solid_capstyle="butt")
    ax.text((x0 + x1) / 2, y, text, ha="center", va="bottom", fontsize=text_size,
            color=color)


def p_str(p: float) -> str:
    """Format a P value in Nature style (mathtext exponent; Arial-safe)."""
    if p == 0:
        return "P = 0"
    if p >= 0.01:
        return f"P = {p:.2f}"
    m, e = f"{p:.0e}".split("e")
    return f"P = {float(m):g} \u00d7 10$^{{{int(e)}}}$"
