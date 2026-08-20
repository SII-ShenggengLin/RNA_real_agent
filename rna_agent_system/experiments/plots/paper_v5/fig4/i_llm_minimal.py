"""Fig 4i - LLM minimalism: the calibrated machinery is deterministic."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S

W, H = 55, 42

# External-LLM call counts from the campaign verdict files (MODEL_API_USAGE.md +
# FACT_SHEET section 5; per-task scale in brackets).
rows = [
    ("E3 audit, ungated arm\n(20 tasks)", 2.0, "2 calls task\u207b\u00b9"),
    ("E3 audit, gated arm\n(20 tasks)", 2.0, "2 calls task\u207b\u00b9"),
    ("E6 mRNA navigation\n(18 targets)", 2.4, "43 calls total"),
    ("E14 aptamer run\n(12 targets)", 1 / 12, "1 call total"),
]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.30, right=0.95, top=0.84, bottom=0.17)
ys = list(range(len(rows)))[::-1]
vals = [r[1] for r in rows]
cols = [S.MORANDI["terra"], S.MORANDI["blue"], S.MORANDI["blue"],
        S.MORANDI["blue"]]
ax.barh(ys, vals, height=0.55, color=cols)
for y, r in zip(ys, rows):
    ax.text(r[1] + 0.05, y, r[2], va="center", fontsize=4.8, color=S.INK)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=4.6)
ax.set_xlim(0, 3.4)
ax.set_xlabel("External-LLM calls per task (lower = fewer)")
ax.set_title("Gates and guarantees add zero LLM calls", fontsize=6.2, loc="left",
             pad=5.0)
ax.axvline(2.0, color=S.GRID, lw=0.5, ls=(0, (3, 2)))
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "i"))
