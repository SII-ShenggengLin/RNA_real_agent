#!/usr/bin/env python3
"""Fig 1 (paper draft): RNADesignAgent system architecture schematic.

Pure matplotlib-patches schematic, no data dependencies.

Layout (180 mm wide canvas):
  a  Seven-layer stack (L0 tools .. L6 entry), left ~2/3 of the canvas.
  b  Tool-first data flow with the two deterministic gates, top right.
     (Bottom right: the bounded coordination loop, shown de-emphasized as
     auditable budget allocation — paper v2 no longer presents BMC as a
     strategy, so it carries no panel letter; v2 legend has only a/b.)

Content follows docs/ARCHITECTURE.md, docs/PAPER_DRAFT.md (Results §1) and
AGENTS.md. All counts verified in docs/PAPER_FACT_SHEET.md:
54 tools / 22 microservices / ports 8003-8024 / 11 workflows.

Output: experiments/plots/paper/fig1.png (300 dpi).

Usage (from `rna_agent_system/`):
    python experiments/plots/plot_paper_fig1.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / "paper" / "fig1.png"

# ---------------------------------------------------------------- style ----
PALETTE = {
    "blue": "#4C72B0",
    "orange": "#DD8452",
    "green": "#55A868",
    "red": "#C44E52",
    "purple": "#8172B3",
    "teal": "#64A9A0",
    "gray": "#8C8C8C",
}
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.0,
        "text.color": "#222222",
    }
)

FIG_W, FIG_H = 7.1, 8.4
CW, CH = 100.0, 118.0


def box(ax, x, y, w, h, color, alpha=0.16, lw=0.9, rounding=0.8, z=2):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={rounding}",
        facecolor=color, alpha=alpha, edgecolor=color, linewidth=lw, zorder=z,
    )
    ax.add_patch(p)
    return p


def text(ax, x, y, s, size=7.0, weight="normal", color="#222222", ha="center",
         va="center", z=5, style="normal", rotation=0, spacing=1.3):
    ax.text(
        x, y, s, fontsize=size, fontweight=weight, color=color, ha=ha, va=va,
        zorder=z, style=style, rotation=rotation, linespacing=spacing,
    )


def arrow(ax, x1, y1, x2, y2, color="#555555", lw=1.1, ms=7, rad=0.0, z=4):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms, color=color,
        lw=lw, connectionstyle=f"arc3,rad={rad}", zorder=z,
    )
    ax.add_patch(a)


fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, CW)
ax.set_ylim(0, CH)
ax.axis("off")

# ============================================================== Panel a ====
LBL_X = 3.2                    # layer-tag column centre
BOX_L, BOX_R = 6.5, 61.5       # layer boxes

layers = [
    ("L0", 17.5, "Tool layer — 54 tools · 22 local microservices (ports 8003–8024)",
     "LinearDesign · LinearFold · ViennaRNA · RhoFold · Protenix · EGARPS · ODesign\n"
     "GemORNA · RNASTOP · BLAST+ · Bowtie2 · CRISOT · EvitAR …\n"
     "(20 vendored external codes behind uniform, versioned contracts)",
     PALETTE["blue"]),
    ("L1", 9.0, "Capabilities",
     "output validation against specs · per-call audit write-back",
     PALETTE["teal"]),
    ("L2", 10.5, "Workflows — 11 domain workflows",
     "deterministic generate → evaluate → score → rank skeleton",
     PALETTE["green"]),
    ("L3", 9.0, "Service orchestration",
     "capability→service map · health check · auto-start · file lock",
     PALETTE["orange"]),
    ("L4", 21.0, "Multi-agent execution", None, PALETTE["purple"]),
    ("L5", 9.0, "Session & workspace",
     "per-session workspace · cross-turn result history",
     PALETTE["gray"]),
    ("L6", 10.5, "Entry — form-driven CLI / FastAPI",
     "explicit workflow selection · user parameters protected",
     PALETTE["red"]),
]

SEP = 1.3
total_h = sum(l[1] for l in layers) + SEP * (len(layers) - 1)
y0 = 4.0
text(ax, (BOX_L + BOX_R) / 2, y0 + total_h + 3.2,
     "Seven-layer tool-first stack", size=8.5, weight="bold")

y = y0
for label, h, title, body, color in layers:
    band = FancyBboxPatch(
        (BOX_L - 0.7, y - 0.35), BOX_R - BOX_L + 1.4, h + 0.7,
        boxstyle="round,pad=0,rounding_size=0.4",
        facecolor="#F2F2F2", edgecolor="none", zorder=1,
    )
    ax.add_patch(band)
    text(ax, LBL_X, y + h / 2, label, size=8, weight="bold", color=color)
    box(ax, BOX_L, y, BOX_R - BOX_L, h, color)
    text(ax, BOX_L + 1.3, y + h - 1.9, title, size=7.2, weight="bold",
         ha="left", color="#1a1a1a")
    if label == "L4":
        agents = [
            "PipelineAgent — deterministic scheduling",
            "SpecialistAgent — per-workflow strategy / retry",
            "CoordinatorAgent — bounded coordination loop",
            "QualityAgent — advisory review only",
            "SynthesisAgent — multi-node synthesis",
        ]
        ax_x, ax_w = BOX_L + 1.3, 33.5
        ax_y = y + 1.4
        ax_h = (h - 5.4) / len(agents)
        for i, labeltxt in enumerate(agents):
            yy = ax_y + (len(agents) - 1 - i) * ax_h
            box(ax, ax_x, yy + 0.2, ax_w, ax_h - 0.4, "#FFFFFF", alpha=0.9,
                lw=0.6, rounding=0.35, z=3)
            name, role = labeltxt.split(" — ")
            text(ax, ax_x + 0.9, yy + ax_h / 2, name, size=6.3,
                 weight="bold", ha="left", z=5)
            text(ax, ax_x + ax_w - 0.9, yy + ax_h / 2, role, size=6.0,
                 ha="right", color="#444444", z=5)
        cs_x = ax_x + ax_w + 1.4
        cs_w = BOX_R - 1.3 - cs_x
        box(ax, cs_x, ax_y, cs_w, h - 5.4, PALETTE["purple"], alpha=0.32,
            lw=0.9, rounding=0.5, z=3)
        text(ax, cs_x + cs_w / 2, ax_y + h - 5.4 - 1.7, "Calibrated stack",
             size=6.7, weight="bold", z=5)
        for j, item in enumerate(["SelfModel", "CapabilityProfiler",
                                  "DecisionGate", "ClaimGate", "AuditTrail"]):
            text(ax, cs_x + cs_w / 2, ax_y + h - 5.4 - 4.2 - j * 2.5, item,
                 size=6.3, z=5)
    elif body is not None:
        text(ax, (BOX_L + BOX_R) / 2, y + (h - 2.2) / 2 - 0.2, body,
             size=6.4, color="#333333")
    y += h + SEP

# ============================================================== Panel b ====
BX_L, BX_R = 65.5, 99.5
BX_C = (BX_L + BX_R) / 2
text(ax, BX_C, 114.0, "Tool-first data flow", size=8.5, weight="bold")

flow = [
    ("User form — target + parameters", PALETTE["red"]),
    ("L6 Entry · CLI / FastAPI", PALETTE["red"]),
    ("L4 Agents — orchestrate & review", PALETTE["purple"]),
    ("L2 Workflow — fixed tool pipeline", PALETTE["green"]),
    ("L0 Services — 22 microservices", PALETTE["blue"]),
    ("Candidates + metrics", PALETTE["teal"]),
]
fh, fg = 4.6, 2.0
fy = 109.0
centers = []
for label, color in flow:
    box(ax, BX_L + 1.5, fy - fh, BX_R - BX_L - 3, fh, color, alpha=0.18)
    text(ax, BX_C, fy - fh / 2, label, size=6.6, weight="bold")
    centers.append(fy - fh / 2)
    fy -= fh + fg
for i in range(len(flow) - 1):
    arrow(ax, BX_C, centers[i] - fh / 2, BX_C, centers[i + 1] + fh / 2)

gate_y = fy - fh
gw = (BX_R - BX_L - 4.5) / 2
for k, (gname, gsub) in enumerate(
        [("DecisionGate", "action vs self-model"),
         ("ClaimGate", "claim vs evidence")]):
    gx = BX_L + 1.5 + k * (gw + 1.5)
    box(ax, gx, gate_y, gw, fh, PALETTE["orange"], alpha=0.38, lw=1.2)
    text(ax, gx + gw / 2, gate_y + fh / 2 + 0.8, gname, size=6.7,
         weight="bold")
    text(ax, gx + gw / 2, gate_y + fh / 2 - 1.2, gsub, size=5.8,
         color="#444444")
arrow(ax, BX_C, centers[-1] - fh / 2, BX_C, gate_y + fh)

rep_y = gate_y - fg - fh
box(ax, BX_L + 1.5, rep_y, BX_R - BX_L - 3, fh, PALETTE["green"], alpha=0.30,
    lw=1.1)
text(ax, BX_C, rep_y + fh / 2, "Report + append-only audit trail", size=6.6,
     weight="bold")
arrow(ax, BX_C, gate_y, BX_C, rep_y + fh)

text(ax, BX_C, rep_y - 2.8,
     "LLM never writes sequences — every molecule\n"
     "comes from a validated generator",
     size=6.4, weight="bold", color=PALETTE["red"], style="italic")

# ====================================================== Coordination loop ===
# De-emphasized (paper v2): no panel letter, muted title — the loop is retained
# as auditable budget allocation, not presented as a strategy.
CX_L, CX_R = 65.5, 99.5
CX_C = (CX_L + CX_R) / 2
text(ax, CX_C, 46.5, "Bounded coordination loop\n(auditable budget allocation)",
     size=7.5, weight="bold", color="#555555")

cnodes = [
    ("1 · Independent module generation", PALETTE["blue"]),
    ("2 · Assembly + ASF / Pareto evaluation", PALETTE["green"]),
    ("3 · Bounded feedback (deterministic)", PALETTE["orange"]),
]
ch, cgap = 5.0, 3.2
cy = 41.0
NB_L, NB_R = CX_L + 1.5, CX_R - 7.0   # leave a lane on the right for the loop
c_centers = []
for label, color in cnodes:
    box(ax, NB_L, cy - ch, NB_R - NB_L, ch, color, alpha=0.20, lw=1.0)
    text(ax, (NB_L + NB_R) / 2, cy - ch / 2, label, size=6.4, weight="bold")
    c_centers.append(cy - ch / 2)
    cy -= ch + cgap
arrow(ax, (NB_L + NB_R) / 2, c_centers[0] - ch / 2, (NB_L + NB_R) / 2,
      c_centers[1] + ch / 2)
arrow(ax, (NB_L + NB_R) / 2, c_centers[1] - ch / 2, (NB_L + NB_R) / 2,
      c_centers[2] + ch / 2)
# return edge 3 -> 1 (round loop) on the right side
rx = CX_R - 4.2
arrow(ax, rx, c_centers[2], rx, c_centers[0], color="#666666", lw=1.2,
      rad=-0.35)
text(ax, CX_R - 0.6, (c_centers[0] + c_centers[2]) / 2, "next round",
     size=5.8, color="#666666", ha="center", rotation=90)

# bounds strip
bnd_y = c_centers[2] - ch / 2 - 1.8
box(ax, CX_L + 2.5, bnd_y - 7.6, CX_R - CX_L - 5, 7.6, "#DDDDDD", alpha=0.5,
    lw=0.7, rounding=0.4)
text(ax, CX_C, bnd_y - 3.8,
     "bounds: hard round cap · λ ∈ [0, 20] clamped\n"
     "≤ 24 new candidates / round · Pareto front ≤ 10\n"
     "convergence threshold 0.05 (normalized ASF space)",
     size=6.2, color="#333333")

# ---------------------------------------------------------- panel letters --
for letter, (lx, ly) in zip("ab", [(0.5, 117.0), (64.5, 117.0)]):
    text(ax, lx, ly, letter, size=11, weight="bold", ha="left", va="top")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=300, facecolor="white")
print(f"wrote {OUT}")
