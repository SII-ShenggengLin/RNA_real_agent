"""Fig 2f - siRNA designs: predicted off-target counts (21/22 at zero)."""
import sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = [r for r in D.load_jsonl("fig2_cpu_a.jsonl")
        if r.get("workflow") == "sirna_design" and r.get("success")]
off = []
for r in rows:
    m = re.search(r"#1 .*?offTarget=(\d+)", r.get("summary") or "")
    if m:
        off.append(int(m.group(1)))
off = np.array(sorted(off))
n = len(off)
zero = int((off == 0).sum())

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.96, top=0.88, bottom=0.18)
x = np.arange(1, n + 1)
ax.vlines(x, 0, np.maximum(off, 0.18), color=S.MORANDI["teal"], lw=1.4)
ax.scatter(x, np.maximum(off, 0.18), s=6, color=np.where(off == 0,
           S.MORANDI["blue"], S.MORANDI["terra"]), zorder=3, clip_on=False)
ax.axhline(0, color=S.INK_SOFT, lw=0.6)
ax.set_xlim(0.3, n + 0.7)
ax.set_xticks([1, 5, 10, 15, 20])
ax.set_xlabel("siRNA design task (sorted)")
ax.set_ylabel("Predicted off-targets (best candidate)")
ax.set_ylim(-0.35, max(2, off.max() * 1.5))
ax.set_yticks([0, 1] + ([off.max()] if off.max() > 1 else []))
ax.set_title(f"siRNA off-target profile: {zero}/{n} tasks at zero", fontsize=6.2,
             loc="left", pad=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
