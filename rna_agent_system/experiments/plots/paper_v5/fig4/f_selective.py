"""Fig 4f - Selective gating: allow / downgrade / require-profiling by evidence."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import style as S
import data as D

W, H = 55, 42

demo = D.load_jsonl("e7_gate_demo.jsonl")
rows = []
for r in demo:
    label = r["demo"]
    verdict = r.get("actual_verdict")
    rows.append((label, verdict))

COL = {"allow": S.MORANDI["green"], "downgrade": S.MORANDI["sand"],
       "require_profiling": S.MORANDI["grey"], "reject": S.MORANDI["terra"]}
SYM = {"allow": "\u2713", "downgrade": "\u2193", "require_profiling": "?",
       "reject": "\u2715"}

DEMO_LABEL = {
    "a_ranking_action_on_verified_family": "MRL oracle, verified family\n(DecisionGate)",
    "b_ranking_action_on_unprofiled_family": "MRL oracle, new family\n(DecisionGate)",
    "c_ranking_action_unprofiled_oracle_3utr_stability": "3'UTR stability, no anchors\n(DecisionGate)",
    "d_absolute_expression_claim_downgrade": "absolute expression claim\n(ClaimGate)",
}

fig = plt.figure(figsize=(W * S.MM, H * S.MM))
ax = fig.add_axes((0.42, 0.14, 0.55, 0.68))
ax.set_xlim(0, 1)
ax.set_ylim(0, len(rows))
ax.invert_yaxis()
ax.axis("off")
fig.text(0.03, 0.90, "Gates are selective, not prohibitive", fontsize=6.2,
         weight="bold", color=S.INK)
fig.text(0.03, 0.83, "ranking action \u2192 verdict (E7 gate demo)", fontsize=5.0,
         color=S.INK_SOFT)
for i, (oracle, verdict) in enumerate(rows):
    y = i + 0.5
    fig.text(0.40, y * 0.68 / len(rows) + 0.17, DEMO_LABEL.get(oracle, oracle),
             fontsize=4.5, ha="right", va="center", color=S.INK)
    ax.add_patch(Rectangle((0.06, i + 0.12), 0.62, 0.76, fc=COL.get(verdict, S.GRID),
                           ec="white", lw=0.6, alpha=0.85))
    ax.text(0.37, y, f"{SYM.get(verdict, '-')}  {str(verdict).replace('_', ' ')}",
            fontsize=4.8, ha="center", va="center", color=S.INK)
fig.text(0.46, 0.10, "verified power passes; transfers decay; absent evidence blocks",
         fontsize=4.6, color=S.INK_SOFT, style="italic")
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "f"))
