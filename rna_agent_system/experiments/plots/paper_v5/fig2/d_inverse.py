"""Fig 2d - Inverse folding: per-benchmark structure distance (22/25 exact)."""
import sys, pathlib, re
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = [r for r in D.load_jsonl("fig2_cpu_b.jsonl")
        if r.get("workflow") == "rna_secondary_structure_design" and r.get("success")]
dist = []
for r in rows:
    m = re.search(r"#1 .*?struc_dist=(\d+)", r.get("summary") or "")
    if m:
        dist.append(int(m.group(1)))
dist = np.array(sorted(dist))
n = len(dist)
exact = int((dist == 0).sum())

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.96, top=0.88, bottom=0.18)
x = np.arange(1, n + 1)
ax.vlines(x, 0, np.maximum(dist, 0.35), color=S.MORANDI["lavender"], lw=1.4)
ax.scatter(x, np.maximum(dist, 0.35), s=6, color=np.where(dist == 0,
           S.MORANDI["blue"], S.MORANDI["terra"]), zorder=3)
ax.axhline(0.5, color=S.MORANDI["grey"], lw=0.5, ls=(0, (3, 2)))
ax.text(n * 0.99, 0.9, "exact match", fontsize=5.2, ha="right", color=S.INK_SOFT)
ax.set_xlim(0.3, n + 0.7)
ax.set_xticks([1, 5, 10, 15, 20, 25])
ax.set_xlabel("Benchmark (sorted)")
ax.set_ylabel("Structure distance (best candidate)")
ax.set_ylim(0, max(6, dist.max() * 1.25))
ax.set_yticks([0, 1, 2, 3] + ([dist.max()] if dist.max() > 3 else []))
ax.set_title(f"Inverse folding: {exact}/{n} exact target recovery", fontsize=6.2,
             loc="left", pad=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "d"))
