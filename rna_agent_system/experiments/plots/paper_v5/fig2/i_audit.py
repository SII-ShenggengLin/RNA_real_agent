"""Fig 2i - Production audit trail composition (every tool call recorded)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

st = D.audit_trail_stats()
tool_ok = st["n_success"]
tool_fail = st["n_fail"] - 0
gate = st["n_gate_decisions"]
total = st["n_tool_calls"] + gate

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1], height_ratios=[1.35, 1],
                      left=0.03, right=0.97, top=0.86, bottom=0.16, wspace=0.5,
                      hspace=1.0)

# top-left: composition donut
axd = fig.add_subplot(gs[0, 0])
vals = [tool_ok, st["n_fail"], gate]
labs = [f"tool calls ok\n{tool_ok:,}", f"failed\n{st['n_fail']}", f"gate decisions\n{gate}"]
cols = [S.MORANDI["blue"], S.MORANDI["terra"], S.MORANDI["lavender"]]
w, _ = axd.pie(vals, colors=cols, startangle=90, counterclock=False,
               wedgeprops=dict(width=0.42, edgecolor="white", linewidth=0.8))
axd.text(0, 0.08, f"{total:,}", ha="center", fontsize=7.5, color=S.INK,
         weight="bold")
axd.text(0, -0.26, "events", ha="center", fontsize=5.2, color=S.INK_SOFT)
axd.set_title("Append-only platform audit trail", fontsize=6.2, loc="left", pad=5.0)

# top-right: KPI text
axk = fig.add_subplot(gs[0, 1]); axk.axis("off")
lines = [
    f"{st['n_tools']} tools called",
    f"{st['n_sessions']} sessions",
    f"{st['n_task_types']} workflow types",
    "100% calls recorded",
]
for i, t in enumerate(lines):
    axk.text(0.0, 0.86 - i * 0.22, t, fontsize=5.6, color=S.INK,
             va="center", transform=axk.transAxes)

# bottom: gate verdicts
axv = fig.add_subplot(gs[1, :])
verd = st["verdicts"]
names = {"reject": "reject", "require_profiling": "require profiling",
         "downgrade": "downgrade"}
ks = [k for k in ("reject", "require_profiling", "downgrade") if k in verd]
vals = [verd[k] for k in ks]
axv.bar(range(len(ks)), vals, width=0.55,
        color=[S.MORANDI["terra"], S.MORANDI["sand"], S.MORANDI["lavender"]])
for i, v in enumerate(vals):
    axv.text(i, v + max(vals) * 0.04, str(v), ha="center", fontsize=5.2,
             color=S.INK)
axv.set_xticks(range(len(ks)))
axv.set_xticklabels([names[k] for k in ks], fontsize=5.2)
axv.set_xlim(-0.55, len(ks) - 0.45)
axv.set_ylim(0, max(vals) * 1.22)
axv.set_yticks([])
S.despine(axv)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "i"))
