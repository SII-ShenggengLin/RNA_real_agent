"""Tiny schematic helpers shared by the Fig 1 architecture panels."""
from __future__ import annotations
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import style as S


def canvas(w_mm: float, h_mm: float, xlim=100.0, ylim=100.0):
    fig = S.new_free(w_mm, h_mm)
    ax = fig.add_axes((0.005, 0.005, 0.99, 0.99))
    ax.set_xlim(0, xlim)
    ax.set_ylim(0, ylim)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc=None, ec=None, fs=4.3, tc=None, lw=0.7,
        alpha=1.0, bold=False, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.10,rounding_size=0.6",
                                fc=fc or "white", ec=ec or S.INK_SOFT, lw=lw,
                                alpha=alpha, linestyle=ls))
    ax.text(x + w / 2, y + h / 2, text, fontsize=fs, ha="center", va="center",
            color=tc or S.INK, linespacing=1.3,
            weight="bold" if bold else "normal")


def arrow(ax, x0, y0, x1, y1, color=None, lw=0.8, style="-|>", ls="-",
          mutation=6, rad=0.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style,
                                 mutation_scale=mutation, lw=lw,
                                 color=color or S.INK_SOFT, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))


def label(ax, x, y, text, fs=4.3, color=None, ha="left", va="center",
          bold=False, style=None):
    ax.text(x, y, text, fontsize=fs, ha=ha, va=va, color=color or S.INK,
            weight="bold" if bold else "normal", style=style, linespacing=1.3)
