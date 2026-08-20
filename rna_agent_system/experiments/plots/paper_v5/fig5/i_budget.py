"""Fig 5i - Budget compliance + production navigation runs."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
import style as S
import data as D

W, H = 55, 42

rows = D.load_jsonl("e14_runs_s2.jsonl")
spend = {}
for r in rows:
    if r["arm"] == "C":
        spend[r["target_id"]] = r["pool"]["n_raw_samples"]
BUDGET = 48

prod = D.gennav_production_runs()
prod_spend = []
for p in prod:
    tr = p["data"].get("_gennav_trace") or {}
    if tr.get("raw_spent") is not None:
        prod_spend.append((p["target"], tr["raw_spent"]))

fig, ax = S.new_panel(W, H)
fig.subplots_adjust(left=0.27, right=0.95, top=0.84, bottom=0.30)
ys = range(len(spend))
ax.axvline(BUDGET, color=S.MORANDI["sage"], lw=0.7, ls=(0, (4, 2)))
ax.text(BUDGET + 0.4, len(spend) - 0.6, "cap 48", fontsize=5.0,
        color=S.MORANDI["sage"])
ax.barh(list(ys), [spend[t] for t in spend], height=0.55,
        color=S.MORANDI["blue"], alpha=0.85)
for y, t in zip(ys, spend):
    ax.text(spend[t] + 0.6, y, str(spend[t]), va="center", fontsize=4.6,
            color=S.INK)
ax.set_yticks(list(ys))
ax.set_yticklabels([t.replace("SARS-CoV-2_Nucleocapsid", "SARS-N")
                    .replace("Carbonic_anhydrase_II", "CAII")
                    .replace("Chymotrypsinogen", "Chymotr.").replace("_", " ")
                    for t in spend], fontsize=4.2)
ax.set_xlim(0, 56)
ax.set_xlabel("Raw candidates spent (E14, navigation arm)")
ax.set_title("Budget never violated; 1 LLM call", fontsize=6.2, loc="left",
             pad=5.0)
txt = "production runs: " + ", ".join(f"{t} {v}/48" for t, v in prod_spend)
ax.text(0.99, -0.24, txt, transform=ax.transAxes, ha="right", fontsize=4.6,
        color=S.INK_SOFT, style="italic", va="top")
S.style_cat_ax(ax)
S.save_panel(fig, str(pathlib.Path(__file__).parent / "panels" / "i"))
