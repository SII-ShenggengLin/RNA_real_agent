"""Fig 1a - End-to-end walkthrough: the tool-first platform spine."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import style as S
import schematic as sch

W, H = 181, 50
X, Y = 100.0, 100.0

fig, ax = sch.canvas(W, H, X, Y)

# headline
sch.label(ax, 0.5, 96, "RNADesignAgent: a calibrated, tool-first agent for RNA design",
          fs=6.6, bold=True)

# left: user input
sch.box(ax, 0.5, 60, 10, 26, "user goal\n\nprotein target /\nstructure /\ntranscript\nregion",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.0)
sch.arrow(ax, 11.0, 73, 14.0, 73)

# centre: the seven-layer platform spine
sch.box(ax, 14.5, 8.0, 56, 84, "", fc="white", ec=S.INK_SOFT, lw=0.9)
sch.label(ax, 16.0, 88.0, "platform (deterministic layers L0-L6)", fs=4.6, bold=True)
layers = [
    ("L6", "CLI / FastAPI runner"),
    ("L5", "session - workspace - files"),
    ("L4", "multi-agent execution (Fig 1b)"),
    ("L3", "service manager (health, auto-start)"),
    ("L2", "11 domain workflows: generate \u2192 evaluate \u2192 score \u2192 rank"),
    ("L1", "capability wrappers + audit records"),
    ("L0", "41 scientific tools / 21 local services (Fig 1f)"),
]
y = 78.0
for tag, txt in layers:
    sch.box(ax, 16.0, y - 8.2, 6.5, 8.2, tag, fc=S.CREAM, ec=S.CREAM_DK, fs=4.2,
            bold=True)
    sch.box(ax, 23.0, y - 8.2, 46.0, 8.2, txt, fc="white", ec=S.MORANDI["blue"],
            fs=4.1)
    y -= 9.6
sch.arrow(ax, 70.8, 73, 74.5, 73)

# right: outputs
sch.box(ax, 75.0, 62, 11.5, 22, "ranked\ncandidates\n+ quality\nreport", fc="white",
        ec=S.MORANDI["green"], fs=4.2)
sch.box(ax, 75.0, 30, 11.5, 22, "append-only\naudit trail\n(every tool\ncall)", fc="white",
        ec=S.MORANDI["lavender"], fs=4.2)
sch.arrow(ax, 70.8, 62, 74.5, 70, color=S.MORANDI["green"])
sch.arrow(ax, 70.8, 30, 74.5, 40, color=S.MORANDI["lavender"])

# bottom strip: two design commitments
sch.box(ax, 14.5, 1.0, 27.5, 5.4, "the LLM never writes sequences", fc=S.CREAM,
        ec=S.CREAM_DK, fs=4.2, bold=True)
sch.box(ax, 43.5, 1.0, 27.5, 5.4, "every comparative claim budget-matched", fc=S.CREAM,
        ec=S.CREAM_DK, fs=4.2, bold=True)
sch.label(ax, 74.0, 3.7, "\u2192 every design decision\n    traces to a tool call", fs=4.0,
          color=S.INK_SOFT)

# calibration overlay on the right of the spine
sch.box(ax, 88.0, 8.0, 11.5, 40, "calibrated\nagency\n\nCapGate\n(Fig 1d)\n\nGenNav\n(Fig 1e)",
        fc=S.CREAM, ec=S.MORANDI["blue"], fs=4.2)
sch.arrow(ax, 87.0, 73, 87.0, 60, color=S.MORANDI["blue"], rad=0.0)
sch.arrow(ax, 70.8, 45, 74.5, 45, style="-")
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "a"))
