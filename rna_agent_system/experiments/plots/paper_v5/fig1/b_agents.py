"""Fig 1b - Multi-agent execution layer with measured contributions."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import style as S
import schematic as sch

W, H = 119, 46
X, Y = 100.0, 100.0

fig, ax = sch.canvas(W, H, X, Y)
sch.label(ax, 0.5, 95.5, "Multi-agent execution layer (L4) - each contribution measured",
          fs=6.0, bold=True)

sch.box(ax, 1.0, 62, 20, 24, "PipelineAgent\ndeterministic\nscheduling\n(no LLM)",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.1)
sch.box(ax, 26.5, 62, 20, 24, "SpecialistAgent\nstrategy + retry\non hard failures\nonly",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.1)
sch.box(ax, 52.0, 62, 20, 24, "QualityAgent\nadvisory review\n19/19 with and\nwithout",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.1)
sch.box(ax, 77.5, 62, 20, 24, "SynthesisAgent\nmulti-node reports\n(ClaimGate-\ngated)",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.1)
for x0 in (21.2, 46.7, 72.2):
    sch.arrow(ax, x0, 74, x0 + 5.0, 74)

sch.box(ax, 1.0, 34, 96.5, 18,
        "measured accounting:  coordination loop removed after its benefit dissolved under\n"
        "budget matching (P0, P3);  mechanized ranking reduces the LLM to tie arbitration\n"
        "(Kendall \u03c4 = 1.0);  an LLM review outage can never fail a successful run",
        fc="white", ec=S.INK_SOFT, fs=4.2)
sch.arrow(ax, 50, 61.5, 50, 52.5)

sch.box(ax, 1.0, 6, 46.5, 22, "ASF reference-point ranking\n(full-length mRNA + aptamer\nworkflows)",
        fc="white", ec=S.MORANDI["blue"], fs=4.2)
sch.box(ax, 51.0, 6, 46.5, 22, "CapGate runtime: every tool call\nrecorded; managed oracles gated\n(RNADA_CAPGATE, default enforce)",
        fc="white", ec=S.MORANDI["lavender"], fs=4.2)
sch.arrow(ax, 24, 33.5, 24, 28.5)
sch.arrow(ax, 74, 33.5, 74, 28.5)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "b"))
