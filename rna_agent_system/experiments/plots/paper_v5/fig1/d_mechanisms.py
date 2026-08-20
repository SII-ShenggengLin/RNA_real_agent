"""Fig 1d - Calibrated agency: where CapGate and GenNav sit (mechanism strip)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import style as S
import schematic as sch

W, H = 119, 46
X, Y = 100.0, 100.0

fig, ax = sch.canvas(W, H, X, Y)
sch.label(ax, 0.5, 95.5, "Calibrated agency: evidence gating (CapGate) + constraint navigation (GenNav)",
          fs=6.0, bold=True)

# CapGate side
sch.label(ax, 1.5, 87, "CapGate - capability layer", fs=4.8, bold=True,
          color=S.MORANDI["slate"])
sch.box(ax, 1.0, 66, 20, 16, "anchor sets\n(assertion-curated,\nliterature-derived)",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.0)
sch.box(ax, 24.5, 66, 20, 16, "profiler\n(oracle x task x\nfamily grades)", fc=S.CREAM,
        ec=S.CREAM_DK, fs=4.0)
sch.box(ax, 48.0, 66, 20, 16, "SelfModel\npackaged with\nthe platform", fc="white",
        ec=S.MORANDI["blue"], fs=4.0)
sch.arrow(ax, 21.2, 74, 24.2, 74)
sch.arrow(ax, 44.7, 74, 47.7, 74)
sch.box(ax, 1.0, 38, 30, 20, "DecisionGate - blocks actions whose\nevidentiary basis is absent\n(reject / require profiling)",
        fc="white", ec=S.MORANDI["blue"], fs=4.0)
sch.box(ax, 36.0, 38, 32, 20, "ClaimGate - downgrades claims to\nvalidated scope (absolute \u2192 relative \u2192\ntrend \u2192 suppressed)",
        fc="white", ec=S.MORANDI["blue"], fs=4.0)
sch.arrow(ax, 55, 65.5, 18, 58.8, color=S.MORANDI["blue"])
sch.arrow(ax, 60, 65.5, 52, 58.8, color=S.MORANDI["blue"])
sch.box(ax, 1.0, 12, 67, 16, "deterministic (zero LLM); every decision joins the audit trail;\nFP claims 57.9% \u2192 0% with TP retention 112.5% (Fig 4)",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.0)

# GenNav side
sch.label(ax, 71.5, 87, "GenNav - generation layer", fs=4.8, bold=True,
          color=S.MORANDI["sage"])
sch.box(ax, 71.0, 66, 28, 16, "feasibility probe over the\ngear lattice (mRNA \u03bb /\naptamer length-seed)",
        fc=S.CREAM, ec=S.CREAM_DK, fs=4.0)
sch.box(ax, 71.0, 38, 28, 20, "guarantee-round budget\nallocation (48-raw cap,\nrepair every band first)",
        fc="white", ec=S.MORANDI["green"], fs=4.0)
sch.box(ax, 71.0, 12, 28, 16, "per-profile delivery 5x3\nor declared degrade",
        fc="white", ec=S.MORANDI["terra"], fs=4.0)
sch.arrow(ax, 85, 65.5, 85, 58.5, color=S.MORANDI["green"])
sch.arrow(ax, 85, 37.5, 85, 28.5, color=S.MORANDI["terra"])
sch.label(ax, 71.0, 6.5, "mRNA 30:0 discordant, P = 1.9 \u00d7 10$^{-9}$;\naptamers 14:3 at equal budget (Fig 5)",
          fs=4.0, color=S.INK_SOFT)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
