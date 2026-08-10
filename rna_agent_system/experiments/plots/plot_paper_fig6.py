#!/usr/bin/env python3
"""Fig 6 (paper draft): quantified failure analysis and system boundaries.

Data sources (all read from experiments/results/, nothing recomputed):
  - failure_taxonomy.json                    (panel a)
  - p1_v2_stability_sweep_summary.json       (panel b, route 1)
  - junction_integrated_optimizer_summary.json (panel b, route 2)
  - junction_ddg_pilot_summary.json          (panel b, route 3)
  - e4_full_summary.json                     (panel c)

Panels:
  a  Failure funnel: 214 transient events (all recovered) vs 35 final
     failures, all deterministic boundaries / governance outcomes.
  b  Junction repair "no free lunch": three pre-registered NO-GO routes
     plotted against their pre-registered acceptance gates.
  c  E4 cross-campaign memory: 74.2% budget saving but no learning
     (all three seed-group slopes positive, one-sided t p = 0.912).

Output: experiments/plots/paper/fig6.png (300 dpi).

Usage (from `rna_agent_system/`):
    python experiments/plots/plot_paper_fig6.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
OUT = HERE / "paper" / "fig6.png"

PALETTE = {
    "blue": "#4C72B0",
    "orange": "#DD8452",
    "green": "#55A868",
    "red": "#C44E52",
    "purple": "#8172B3",
    "gray": "#8C8C8C",
}
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "axes.labelsize": 7.5,
    }
)


def style_ax(ax):
    ax.grid(axis="y", color="#E6E6E6", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=0.8)


def main() -> None:
    taxonomy = json.loads((RESULTS / "failure_taxonomy.json").read_text())
    p1v2 = json.loads((RESULTS / "p1_v2_stability_sweep_summary.json").read_text())
    integ = json.loads(
        (RESULTS / "junction_integrated_optimizer_summary.json").read_text()
    )
    ddg = json.loads((RESULTS / "junction_ddg_pilot_summary.json").read_text())
    e4 = json.loads((RESULTS / "e4_full_summary.json").read_text())

    fig = plt.figure(figsize=(7.1, 9.0), dpi=300)
    gs = fig.add_gridspec(
        3, 3, height_ratios=[1.0, 1.0, 0.9], hspace=0.55, wspace=0.55,
        left=0.13, right=0.97, top=0.94, bottom=0.07,
    )

    # ------------------------------------------------------ panel a --------
    axa = fig.add_subplot(gs[0, :])
    style_ax(axa)
    axa.grid(axis="x", color="#E6E6E6", lw=0.6, zorder=0)
    axa.grid(axis="y", visible=False)

    tev = taxonomy["totals"]["failure_events"]
    fin = taxonomy["totals"]["final_failures"]
    rows = [
        ("Transient infrastructure — recovered by resumable sweeps",
         tev["transient_infra_recovered"], PALETTE["blue"]),
        ("Transient timeout — recovered",
         tev["transient_timeout"], PALETTE["blue"]),
        ("Driver chain bug — fixed in place, rerun",
         tev["driver_chain_bug_fixed"], PALETTE["blue"]),
        ("ODesign zero-output boundary (Ferritin family)",
         fin["boundary_odesign_zero_output"], PALETTE["red"]),
        ("Endpoint misconfiguration (nominal 2nd-LLM arm)",
         fin["endpoint_misconfig"], PALETTE["red"]),
        ("LinearDesign memory boundary (Zika / Factor VIII)",
         fin["boundary_lineardesign_oom"], PALETTE["red"]),
        ("Correct advisory quality abort (GC-rich siRNA)",
         fin["llm_abort_correct"], PALETTE["red"]),
    ]
    ypos = list(range(len(rows)))[::-1]
    for (label, val, color), yp in zip(rows, ypos):
        axa.barh(yp - 0.12, val, height=0.5, color=color, alpha=0.85,
                 zorder=3)
        axa.text(val + 2.5, yp - 0.12, str(val), va="center", ha="left",
                 fontsize=7, fontweight="bold", color=color)
        axa.text(0, yp + 0.32, label, va="center", ha="left", fontsize=6.6,
                 color="#333333")
    axa.set_yticks([])
    axa.set_xlim(0, 215)
    axa.set_ylim(-0.75, len(rows) - 0.1)
    axa.set_xlabel("failure events (count)")
    # group braces / annotations
    axa.axhline(3.5, color="#BBBBBB", lw=0.8, ls=(0, (4, 3)))
    axa.text(212, 4.7, "transient — 214 events, all recovered",
             ha="right", va="center", fontsize=6.8, color=PALETTE["blue"],
             fontweight="bold")
    axa.text(212, 1.35, "final — 35 failures, all deterministic\n"
             "boundaries or governance outcomes",
             ha="right", va="center", fontsize=6.8, color=PALETTE["red"],
             fontweight="bold")
    axa.set_title("Failure taxonomy across the legacy platform campaigns (~1,400 runs)",
                  loc="left", fontsize=8, fontweight="bold", pad=8)
    axa.text(-0.155, 1.10, "a", transform=axa.transAxes, fontsize=11,
             fontweight="bold", va="top")

    # ------------------------------------------------------ panel b --------
    # b1: P1 v2 stability sweep — stability cost per nt vs gate
    axb1 = fig.add_subplot(gs[1, 0])
    style_ax(axb1)
    w_keys = ["0.0", "0.1", "0.25", "0.5", "1.0"]
    costs = [p1v2["per_weight"][w]["median_stability_cost_per_nt"]
             for w in w_keys]
    xs = range(len(w_keys))
    axb1.plot(xs, costs, "o-", color=PALETTE["blue"], lw=1.2, ms=4,
              zorder=3)
    gate_cost = 0.5 * p1v2["v1_median_stability_cost_per_nt"]  # = 0.0110
    axb1.axhline(gate_cost, color=PALETTE["red"], lw=1.0, ls="--", zorder=2)
    axb1.text(2.0, gate_cost - 0.0012, "gate ≤ 0.011", color=PALETTE["red"],
              fontsize=6.2, ha="center", va="top")
    axb1.set_xticks(list(xs))
    axb1.set_xticklabels(w_keys)
    axb1.set_xlabel("P1 v2 stability weight $w_{stab}$", fontsize=7)
    axb1.set_ylabel("median stability cost / nt", fontsize=7)
    axb1.set_ylim(0, 0.028)
    axb1.set_title("Route 1 · post-hoc shuffle\nhard repair 7/7, cost never "
                   "≤ gate → NO-GO", fontsize=6.6, loc="left")
    axb1.tick_params(labelsize=6.2)

    # b2: junction-integrated optimizer — repair rate vs gate + window pairs
    axb2 = fig.add_subplot(gs[1, 1])
    style_ax(axb2)
    w_jun = ["0", "0.5", "1", "2"]
    rates = [integ["per_weight"][w]["hard_repair_rate"] for w in w_jun]
    pairs = [integ["per_weight"][w]["median_junction_window_pair_count"]
             for w in w_jun]
    xs2 = range(len(w_jun))
    axb2.bar(xs2, rates, width=0.58, color=PALETTE["orange"], alpha=0.85,
             zorder=3)
    for x, r in zip(xs2, rates):
        axb2.text(x, r + 0.02, f"{r * 7:.0f}/7", ha="center", fontsize=6.2,
                  color=PALETTE["orange"], fontweight="bold")
    axb2.axhline(2 / 3, color=PALETTE["red"], lw=1.0, ls="--", zorder=2)
    axb2.text(1.5, 2 / 3 + 0.03, "gate ≥ 2/3", color=PALETTE["red"],
              fontsize=6.2, ha="center")
    axb2.set_xticks(list(xs2))
    axb2.set_xticklabels(w_jun)
    axb2.set_xlabel("P2 junction penalty $w_{jun}$", fontsize=7)
    axb2.set_ylabel("hard repair rate", fontsize=7)
    axb2.set_ylim(0, 0.8)
    axb2.tick_params(labelsize=6.2)
    axb2_t = axb2.twinx()
    axb2_t.plot(xs2, pairs, "s--", color=PALETTE["gray"], lw=1.0, ms=3.5,
                zorder=4)
    axb2_t.set_ylabel("window pairs\n(global fold)", fontsize=6.0,
                      color=PALETTE["gray"])
    axb2_t.set_ylim(-3, 62)
    axb2_t.tick_params(labelsize=6.0, colors=PALETTE["gray"])
    axb2_t.spines["right"].set_visible(True)
    axb2_t.spines["right"].set_color(PALETTE["gray"])
    axb2.set_title("Route 2 · junction-integrated optimizer\n"
                   "window pairs 43→0, burial persists → NO-GO",
                   fontsize=6.6, loc="left")

    # b3: ddG Route C — targets passing vs gate
    axb3 = fig.add_subplot(gs[1, 2])
    style_ax(axb3)
    n_pass = ddg["gate2_route_c"]["n_targets_pass"]
    epo_imp = ddg["gate2_route_c"]["per_target"]["EPO"]["median_improvement_w1"]
    axb3.bar([0], [n_pass / 3], width=0.45, color=PALETTE["purple"],
             alpha=0.85, zorder=3)
    axb3.text(0, n_pass / 3 + 0.025, "1/3\n(EPO only)", ha="center",
              fontsize=6.2, color=PALETTE["purple"], fontweight="bold")
    axb3.axhline(2 / 3, color=PALETTE["red"], lw=1.0, ls="--", zorder=2)
    axb3.text(0, 2 / 3 + 0.025, "gate ≥ 2/3", color=PALETTE["red"],
              fontsize=6.2, ha="center")
    axb3.set_xticks([0])
    axb3.set_xticklabels(["targets passing\nRoute C"], fontsize=6.2)
    axb3.set_ylabel("fraction of targets", fontsize=6.5)
    axb3.set_ylim(0, 0.85)
    axb3.tick_params(labelsize=6.2)
    axb3.set_title("Route 3 · ddG generate-and-select\n"
                   f"EPO ΔW1 {epo_imp:.3f} kcal/mol → NO-GO",
                   fontsize=6.6, loc="left")
    g1 = ddg["gate1_metric_validity"]
    axb3.text(0.5, 0.60,
              "metric gate itself GO:\n"
              f"obedience {g1['n_obedience_checks']}/{g1['n_obedience_checks']}"
              f", r = {g1['linearfold_vs_vienna_parent_pearson_r']:.3f}",
              transform=axb3.transAxes, ha="center", fontsize=6.0,
              color="#555555")

    fig.text(0.02, 0.645, "b", fontsize=11, fontweight="bold", va="top")
    fig.text(0.13, 0.645, "Junction repair has no free lunch — three "
             "pre-registered NO-GOs", fontsize=8, fontweight="bold", va="top")

    # ------------------------------------------------------ panel c --------
    # c1: budget bars
    axc1 = fig.add_subplot(gs[2, 0])
    style_ax(axc1)
    sav = e4["endpoints"]["efficiency"]["cumulative_budget_saving"]
    vals = [sav["nomem_total"], sav["memory_total"]]
    axc1.bar([0, 1], vals, width=0.55,
             color=[PALETTE["gray"], PALETTE["green"]], alpha=0.85, zorder=3)
    for x, v in zip([0, 1], vals):
        axc1.text(x, v + 60, f"{v:.0f}", ha="center", fontsize=7,
                  fontweight="bold")
    axc1.annotate("", xy=(1, vals[1] + 330), xytext=(0, vals[0] + 330),
                  arrowprops=dict(arrowstyle="->", color=PALETTE["green"],
                                  lw=1.1))
    axc1.text(0.5, vals[0] + 400, "saving 74.2%", ha="center", fontsize=7.2,
              color=PALETTE["green"], fontweight="bold")
    axc1.set_xticks([0, 1])
    axc1.set_xticklabels(["no memory", "memory"], fontsize=6.8)
    axc1.set_ylabel("total evaluations (55 paired cells)", fontsize=7)
    axc1.set_ylim(0, 4200)
    axc1.set_title("budget: memory cuts evaluations", fontsize=6.8,
                   loc="left")

    # c2: learning slopes
    axc2 = fig.add_subplot(gs[2, 1:])
    style_ax(axc2)
    axc2.grid(axis="y", color="#E6E6E6", lw=0.6)
    eff = e4["endpoints"]["efficiency"]
    slopes = eff["memory_slopes"]
    groups = ["seed group A", "seed group B", "seed group C"]
    xs3 = range(3)
    axc2.axhline(0.0, color="#444444", lw=1.0, zorder=2)
    axc2.plot(xs3, slopes, "o", color=PALETTE["blue"], ms=6, zorder=3)
    labels = ["+1.228e-04", "+2.381e-05", "+2.429e-04"]
    for x, (s, lab) in enumerate(zip(slopes, labels)):
        axc2.annotate(lab, (x, s), textcoords="offset points",
                      xytext=(10, -3), fontsize=6.6, color=PALETTE["blue"])
    axc2.set_xticks(list(xs3))
    axc2.set_xticklabels(groups, fontsize=6.8)
    axc2.set_xlim(-0.6, 2.6)
    axc2.set_ylim(-1.2e-4, 3.4e-4)
    axc2.set_ylabel("memory-arm learning slope\n(evaluations per campaign "
                    "index)", fontsize=7)
    t_p = eff["memory_slope_t"]["p_one_sided_less"]
    axc2.text(0.03, 0.95,
              f"all 3 slopes positive — no learning\n"
              f"one-sided t p = {t_p:.3f} (pre-reg. needs p < 0.05, negative)\n"
              "design quality: 0/4 metrics pass (all NS) → NO-GO",
              transform=axc2.transAxes, va="top", fontsize=6.6,
              color="#333333")
    axc2.set_title("learning curve: saves budget, does not learn",
                   fontsize=6.8, loc="left")

    fig.text(0.02, 0.315, "c", fontsize=11, fontweight="bold", va="top")
    fig.text(0.13, 0.315, "E4 cross-campaign memory — pre-registered dual "
             "endpoints, 120 campaigns", fontsize=8, fontweight="bold",
             va="top")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=300, facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
