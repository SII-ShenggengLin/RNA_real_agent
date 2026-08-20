"""Fig 6i - LLM usage transparency: the sole external dependency is small."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S

W, H = 55, 42

# External-LLM call counts from MODEL_API_USAGE.md (measured; DeepSeek v4-pro).
rows = [
    ("quality ablation", 93),
    ("E3 gated-vs-ungated", 80),
    ("E4 memory matrix", 230),
    ("E5 selection", 11),
    ("E6 mRNA navigation", 72),
    ("E14 aptamer decisive", 1),
    ("E15 confirmatory", 3),
]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.30, right=0.95, top=0.84, bottom=0.27)
ys = list(range(len(rows)))[::-1]
ax.barh(ys, [r[1] for r in rows], height=0.55, color=S.MORANDI["lavender"])
for y, r in zip(ys, rows):
    ax.text(r[1] + 3, y, str(r[1]), va="center", fontsize=4.8, color=S.INK)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=4.8)
ax.set_xlim(0, 265)
ax.set_xlabel("External-LLM calls (DeepSeek v4-pro)")
ax.set_title("All structure and sequence models run locally", fontsize=6.2,
             loc="left", pad=5.0)
ax.text(0.98, -0.30, "largest measured usage: 414,088 prompt + 194,261 completion tokens",
        transform=ax.transAxes, ha="right", fontsize=4.4, color=S.INK_SOFT,
        style="italic", va="top")
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "i"))
