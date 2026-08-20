"""Fig 2e - IRES prediction: ROC on the literature panel (3 positives / 49 negatives)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = [r for r in D.load_jsonl("fig2_literature_panels.jsonl")
        if r.get("panel") == "ires" and r.get("success")
        and r.get("best_ires_probability") is not None]
pos = np.array([r["best_ires_probability"] for r in rows if r["label"] == "positive"])
neg = np.array([r["best_ires_probability"] for r in rows if r["label"] == "negative"])
scores = np.concatenate([pos, neg])
labels = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
order = np.argsort(-scores)
labels = labels[order]

tpr = np.concatenate([[0], np.cumsum(labels) / max(len(pos), 1)])
fpr = np.concatenate([[0], np.cumsum(1 - labels) / max(len(neg), 1)])
auroc = float(np.trapezoid(tpr, fpr)) if hasattr(np, "trapezoid") else float(np.trapz(tpr, fpr))

rng = np.random.default_rng(0)
boot = []
for _ in range(10000):
    idx = rng.integers(0, len(scores), len(scores))
    s, l = scores[idx], labels[idx]
    o = np.argsort(-s)
    l = l[o]
    n_pos = max(int(l.sum()), 1)
    n_neg = max(int((1 - l).sum()), 1)
    t = np.concatenate([[0], np.cumsum(l)]) / n_pos
    f = np.concatenate([[0], np.cumsum(1 - l)]) / n_neg
    boot.append(np.trapezoid(t, f) if hasattr(np, "trapezoid") else np.trapz(t, f))
lo, hi = np.percentile(boot, [2.5, 97.5])

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.15, right=0.96, top=0.88, bottom=0.18)
ax.plot(fpr, tpr, color=S.MORANDI["blue"], lw=1.1)
ax.fill_between(fpr, tpr, 0, color=S.MORANDI["blue"], alpha=0.12, lw=0)
ax.plot([0, 1], [0, 1], color=S.MORANDI["grey"], lw=0.6, ls=(0, (3, 2)))
ax.text(0.62, 0.36, "chance", fontsize=5.2, color=S.MORANDI["grey_dk"], rotation=45,
        rotation_mode="anchor", ha="center")
ax.text(0.97, 0.06, f"AUROC {auroc:.2f}\n[{lo:.2f}, {hi:.2f}]", fontsize=5.2,
        ha="right", color=S.INK)
ax.set_xlabel("False-positive rate")
ax.set_ylabel("True-positive rate")
ax.set_xlim(-0.02, 1.02)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_ylim(-0.02, 1.05)
ax.set_title(f"IRES finder on literature panel (n = {len(pos)}+{len(neg)})",
             fontsize=6.2, loc="left", pad=5.0)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "e"))
