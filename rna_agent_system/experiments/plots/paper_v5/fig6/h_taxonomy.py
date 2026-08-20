"""Fig 6h - Failure taxonomy across all campaigns (35 final, all deterministic)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

ft = D.failure_taxonomy()
final = ft["totals"]["final_failures"]
events = ft["totals"]["failure_events"]

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], left=0.42, right=0.95,
                      top=0.84, bottom=0.16, hspace=1.0)

items = sorted(final.items(), key=lambda kv: kv[1])
NAME = {"boundary_odesign_zero_output": "ODesign zero-output",
        "endpoint_misconfig": "endpoint misconfig",
        "boundary_lineardesign_oom": "LinearDesign OOM",
        "llm_abort_correct": "LLM abort (pre-fix rule)"}

ax1 = fig.add_subplot(gs[0])
ys = range(len(items))
ax1.barh(list(ys), [v for _, v in items], height=0.55,
         color=[S.MORANDI["terra"], S.MORANDI["sand"], S.MORANDI["grey"],
                S.MORANDI["lavender"]][:len(items)])
for y, (k, v) in zip(ys, items):
    ax1.text(v + 0.5, y, str(v), va="center", fontsize=5.0, color=S.INK)
ax1.set_yticks(list(ys))
ax1.set_yticklabels([NAME.get(k, k) for k, _ in items], fontsize=4.8)
ax1.set_xlim(0, max(v for _, v in items) * 1.25)
ax1.set_title("35 final failures - all deterministic boundaries", fontsize=5.8,
              loc="left", pad=5.0)
S.style_cat_ax(ax1)

ax2 = fig.add_subplot(gs[1])
ev = sorted(events.items(), key=lambda kv: kv[1])
ax2.barh(range(len(ev)), [v for _, v in ev], height=0.55,
         color=S.MORANDI["blue"])
for i, (k, v) in enumerate(ev):
    ax2.text(v + 2, i, str(v), va="center", fontsize=4.6, color=S.INK)
ax2.set_yticks(range(len(ev)))
ax2.set_yticklabels([k.replace("_", " ") for k, _ in ev], fontsize=4.4)
ax2.set_xlim(0, max(v for _, v in ev) * 1.30)
ax2.set_title("228 transient events - every one recovered by resume", fontsize=5.8,
              loc="left", pad=5.0)
S.style_cat_ax(ax2)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "h"))
