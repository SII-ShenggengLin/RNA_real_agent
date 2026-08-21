"""Fig 1c - Platform at a glance: KPI tiles + audit-trail donut."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 46

st = D.audit_trail_stats()

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(2, 3, left=0.05, right=0.98, top=0.80, bottom=0.10,
                      hspace=0.9, wspace=0.25)

kpis = [("41", "scientific tools"), ("21", "local services"), ("11", "workflows"),
        ("210", "benchmark tasks"), (f"{st['n_tool_calls'] + st['n_gate_decisions']:,}",
         "audit events"), ("5,747", "lines, append-only")]
for i, (big, small) in enumerate(kpis):
    axk = fig.add_subplot(gs[i // 3, i % 3])
    axk.axis("off")
    axk.text(0.5, 0.62, big, fontsize=9.5, ha="center", va="center", color=S.INK,
             weight="bold")
    axk.text(0.5, 0.22, small, fontsize=4.8, ha="center", va="center",
             color=S.INK_SOFT)
    axk.add_patch(plt.Rectangle((0.06, 0.05), 0.88, 0.9, transform=axk.transAxes,
                                fc=S.CREAM, ec=S.CREAM_DK, lw=0.6, zorder=-1))
fig.suptitle("The platform at a glance (2026-08-19 state)", fontsize=6.2, x=0.05,
             ha="left", y=0.97)
fig.text(0.05, 0.865, f"{st['n_success']:,} successful / {st['n_fail']} failed tool calls; "
         f"{st['n_gate_decisions']:,} gate decisions", fontsize=4.6, color=S.INK_SOFT)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
