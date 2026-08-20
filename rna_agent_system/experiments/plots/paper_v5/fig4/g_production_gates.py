"""Fig 4g - Production gate decisions from the live audit trail, by oracle."""
import sys, pathlib
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

st = D.audit_trail_stats()
import json
p = D.SYSTEM / "workspace" / "audit" / "platform_audit.jsonl"
by_oracle = {}
with open(p) as f:
    for line in f:
        r = json.loads(line)
        if r["event_type"] != "gate_decision":
            continue
        pay = r["payload"]
        orc = pay.get("oracle", "?")
        by_oracle.setdefault(orc, Counter())[pay.get("verdict", "?")] += 1

COL = {"reject": S.MORANDI["terra"], "require_profiling": S.MORANDI["sand"],
       "downgrade": S.MORANDI["lavender"]}
NAME = {"crgpt_handle_score": "CRGPT (sgRNA)", "egarps_native_probability":
        "EGARPS (aptamer)", "proteinx_iptm": "Protenix ipTM", "rhofold_plddt":
        "RhoFold pLDDT", "gemorna_5utr_mrl": "GEMORNA 5'UTR MRL",
        "gemorna_3utr_stability": "GEMORNA 3'UTR stab.",
        "rnasmol_score": "RNAsmol", "gerna_bind": "GerNA-Bind"}

rows = sorted(by_oracle.items(), key=lambda kv: sum(kv[1].values()))
fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.32, right=0.95, top=0.84, bottom=0.17)
ys = range(len(rows))
left = [0] * len(rows)
for verdict in ("reject", "require_profiling", "downgrade"):
    vals = [c.get(verdict, 0) for _, c in rows]
    ax.barh(list(ys), vals, left=left, height=0.6, color=COL[verdict],
            label=verdict.replace("_", " "))
    for y, (v, l) in enumerate(zip(vals, left)):
        if v > 120:
            ax.text(l + v / 2, y, str(v), va="center", ha="center", fontsize=4.6,
                    color="white")
    left = [l + v for l, v in zip(left, vals)]
ax.set_yticks(list(ys))
ax.set_yticklabels([NAME.get(k, k) for k, _ in rows], fontsize=4.6)
ax.set_xlabel("Gate decisions (live platform)")
ax.set_title("Production behaviour: 1,217 decisions", fontsize=6.2, loc="left",
             pad=5.0)
ax.legend(fontsize=4.6, loc="lower right")
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "g"))
