"""Fig 6c - ddG metric validity: obedience 216/216, LinearFold vs Vienna r = 0.945."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = [r for r in D.load_jsonl("junction_ddg_pilot_runs.jsonl")
        if r["kind"] == "parent" and r.get("success")]
lf = np.array([r["metrics"]["mfe_unconstrained"] for r in rows], dtype=float)
vi = np.array([r["metrics"]["vienna_mfe_unconstrained"] for r in rows], dtype=float)
r_val = float(np.corrcoef(lf, vi)[0, 1])
s = D.junction_summaries()["ddg"]["gate1_metric_validity"]

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.18, right=0.96, top=0.84, bottom=0.18)
ax.scatter(vi, lf, s=10, color=S.MORANDI["blue"], zorder=3)
lim = [min(vi.min(), lf.min()) * 1.06, max(vi.max(), lf.max()) * 1.04]
ax.plot(lim, lim, color=S.MORANDI["grey"], lw=0.6, ls=(0, (3, 2)))
ax.set_xlabel("ViennaRNA MFE (kcal/mol)")
ax.set_ylabel("LinearFold MFE (kcal/mol)")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.text(0.04, 0.93, f"parents (n = {len(rows)}), r = {r_val:.2f}",
        transform=ax.transAxes, fontsize=5.2, color=S.INK)
ax.text(0.04, 0.84, f"constraint obedience {s['n_obedience_checks']}/"
        f"{s['n_obedience_checks']}   ddG \u2265 0 {s['n_ddg_checks']}/"
        f"{s['n_ddg_checks']}", transform=ax.transAxes, fontsize=4.8,
        color=S.INK_SOFT)
ax.set_title("The ddG reporter itself is valid", fontsize=6.2, loc="left",
             pad=5.0)
ax.grid(color=S.GRID, lw=0.4)
S.despine(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "c"))
