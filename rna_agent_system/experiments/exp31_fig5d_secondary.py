#!/usr/bin/env python3
"""EXP 31 — Fig 5d: the Exp-28 mRNA secondary-endpoint panel (figure-only;
fourth programme reset, 2026-09-05, §2.5, user-directed).

No new measurement: every number is recomputed from the frozen Exp-28
records (``exp28_gennav_mrna_endpoint_v2/full/``) and cross-checked against
its stored verdict — the registered panel renders the disclosed secondary
block of the repaired-navigator endpoint re-run (the paper's citation):

* gene-e2e conjunct  c_e2e = 0.45 (9/20 targets deliver all three
  five-candidate passing batches) against the registered ≥ 0.8 gate — a
  legacy-era calibration; the rule pool's a_e2e = 1.0 is drawn as context
  (its failures are JCD-level, Fig. 5b/5c, not batch delivery);
* constraint rate (navigation) mean 0.944 over the 60 delivered profile
  cells against the registered ≥ 0.9 gate — the one secondary criterion
  that holds;
* secondary composite  Δ = composite(nav) − composite(rule) per paired
  cell (n = 60): +24 / =18 / −18, paired Wilcoxon P = 0.731 — does not
  separate, disclosed;
* budget ledger: per-target navigation raw spend 11–35 of the matched
  35-call cap (mean 24.55), rule spend 35, violations 0, LLM calls 0.

REGISTERED PANEL ENCODING (re-registration of the FIGURE_PLAN_V5 row-d
encoding, pending since 2026-09-03; single-view repair 2026-09-08, user
direction): the Δ-composite stacked-dot distribution alone on one 89-mm
column — one dot per paired cell, the fig2d/2f stacking convention,
colours by direction with the Fig-5b semantics (sage = navigation-
favouring, terracotta = rule-favouring, grey blue = tied), tall-stack
counts printed, the sign counts + Wilcoxon P annotated as one line in a
reserved strip above the axes.  The original three-block stack
(registered-criteria bullet bars above, per-target spend strip below) was
removed in the 2026-09-08 figure-repair pass — one plot per panel (the
fig5a/5b/5c same-day convention); the removed blocks shared neither axis
nor observation unit with the Δ distribution (rates vs per-cell score
differences vs per-target call counts), so their numbers (gene-e2e
0.45 = 9/20 vs the ≥ 0.8 legacy-era gate, rule-pool 1.00 = 20/20 context;
constraint rate 0.944 ≥ 0.9; spend mean 24.55 of the 35-call cap,
0 violations · 0 LLM) are text-reported verbatim in the Fig. 5d caption
and §2.5.  House style: no in-figure title (the panel letter lands at
assembly), single 6-pt pure-black text style, palette rev 7 only,
absolute-mm geometry, 1200-dpi PNG + vector PDF (fonttype 42).

Outputs: results/exp31_fig5d_secondary/panel_data.json (the plot script's
single data source) + experiments/plots/fig5d_secondary_endpoint.{pdf,png}
(rendered by experiments/plots/fig5d_secondary_endpoint.py; raster QA by
experiments/plots/qa_exp31_figs.py).

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp31_fig5d_secondary.py
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp31_fig5d_secondary.py --verify
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXP28_DIR = (PROJECT_ROOT / "experiments" / "results"
             / "exp28_gennav_mrna_endpoint_v2" / "full")
OUT_DIR = PROJECT_ROOT / "experiments" / "results" / "exp31_fig5d_secondary"
OUT_PATH = OUT_DIR / "panel_data.json"

GATE_GENE_E2E = 0.8
GATE_CONSTRAINT = 0.9
NAV_CAP = 35


def build_panel_data() -> dict[str, Any]:
    records = [json.loads(ln) for ln in
               (EXP28_DIR / "runs.jsonl").read_text(encoding="utf-8").splitlines()
               if ln.strip()]
    records = [r for r in records if r.get("success")]
    assert len(records) == 20, f"expected 20 successful records, got {len(records)}"
    verdict = json.loads((EXP28_DIR / "verdict.json").read_text(encoding="utf-8"))

    nav_targets_3of3: list[str] = []
    nav_profile_dist = {0: 0, 1: 0, 2: 0, 3: 0}
    rule_gene_e2e = 0
    constraint_cells: list[float] = []
    deltas: list[float] = []
    nav_composites: list[float] = []
    rule_composites: list[float] = []
    per_target_spend: dict[str, int] = {}
    for rec in records:
        profiles_nav = rec["evaluations"]["C"]["profiles"]
        profiles_rule = rec["evaluations"]["A"]["profiles"]
        n_e2e = sum(1 for p in profiles_nav if p["e2e_pass"])
        nav_profile_dist[n_e2e] += 1
        if n_e2e == 3:
            nav_targets_3of3.append(rec["target_id"])
        if all(p["e2e_pass"] for p in profiles_rule):
            rule_gene_e2e += 1
        for p in profiles_nav:
            constraint_cells.append(p["constraint_rate"])
            nav_composites.append(p["composite"])
        for p_nav, p_rule in zip(profiles_nav, profiles_rule):
            deltas.append(p_nav["composite"] - p_rule["composite"])
            rule_composites.append(p_rule["composite"])
        per_target_spend[rec["target_id"]] = rec["budget_matching"]["nav_raw_spent"]

    n = len(deltas)
    assert n == 60, f"expected 60 paired cells, got {n}"
    n_pos = sum(1 for d in deltas if d > 1e-12)
    n_zero = sum(1 for d in deltas if abs(d) <= 1e-12)
    n_neg = sum(1 for d in deltas if d < -1e-12)
    from scipy.stats import wilcoxon
    non_tied = [d for d in deltas if abs(d) > 1e-12]
    wilcoxon_p = float(wilcoxon(non_tied).pvalue)

    nav_rate = len(nav_targets_3of3) / len(records)
    rule_rate = rule_gene_e2e / len(records)
    constraint_mean = sum(constraint_cells) / len(constraint_cells)

    # cross-checks against the stored Exp-28 verdict — the panel may not
    # render a number the campaign's own verdict disagrees with
    assert abs(nav_rate - verdict["c_e2e_gene"]) < 1e-12, (nav_rate, verdict["c_e2e_gene"])
    assert abs(rule_rate - verdict["a_e2e_gene"]) < 1e-12, (rule_rate, verdict["a_e2e_gene"])
    assert abs(wilcoxon_p - verdict["wilcoxon_C_vs_A_p"]) < 1e-9, (wilcoxon_p, verdict["wilcoxon_C_vs_A_p"])
    assert (constraint_mean >= GATE_CONSTRAINT) == verdict["constraint_rate_C_ge_0.9"]
    bm = verdict["budget_matching"]
    assert bm["nav_raw_spent_max"] == max(per_target_spend.values())
    assert abs(bm["nav_raw_spent_mean"]
               - sum(per_target_spend.values()) / len(per_target_spend)) < 1e-9
    assert bm["violations"] == 0 and bm["nav_cap"] == NAV_CAP

    return {
        "source": "exp28_gennav_mrna_endpoint_v2/full",
        "n_targets": len(records),
        "n_pairs": n,
        "gene_e2e": {
            "gate": GATE_GENE_E2E,
            "nav_rate": nav_rate,
            "nav_count": len(nav_targets_3of3),
            "nav_targets_3of3": nav_targets_3of3,
            "nav_profile_count_dist": {str(k): v for k, v in nav_profile_dist.items()},
            "rule_rate": rule_rate,
            "rule_count": rule_gene_e2e,
        },
        "constraint_rate": {
            "gate": GATE_CONSTRAINT,
            "nav_mean": constraint_mean,
            "nav_min": min(constraint_cells),
            "nav_cells": constraint_cells,
            "pass": constraint_mean >= GATE_CONSTRAINT,
        },
        "composite_delta": {
            "deltas": deltas,
            "n_pos": n_pos,
            "n_zero": n_zero,
            "n_neg": n_neg,
            "n_non_tied": len(non_tied),
            "wilcoxon_p": wilcoxon_p,
            "nav_mean": sum(nav_composites) / len(nav_composites),
            "rule_mean": sum(rule_composites) / len(rule_composites),
        },
        "budget": {
            "cap": NAV_CAP,
            "rule_raw_spend": bm["rule_raw_spend"],
            "per_target": per_target_spend,
            "mean": bm["nav_raw_spent_mean"],
            "max": bm["nav_raw_spent_max"],
            "violations": bm["violations"],
            "llm_calls": 0,
        },
        "notes": (
            "Figure-only re-registration of the FIGURE_PLAN_V5 row-d encoding; "
            "every value recomputed from the Exp-28 records and asserted equal "
            "to the stored verdict (rates, Wilcoxon P, constraint gate, budget "
            "ledger). Quality bundle (endpoint2 third term) is False and stays "
            "text-register-only per the registered panel content."
        ),
    }


def main() -> int:
    data = build_panel_data()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_PATH).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    print(f"  gene-e2e nav {data['gene_e2e']['nav_count']}/20 = "
          f"{data['gene_e2e']['nav_rate']:.2f} (gate "
          f"{GATE_GENE_E2E}); rule {data['gene_e2e']['rule_count']}/20")
    print(f"  constraint rate nav mean {data['constraint_rate']['nav_mean']:.4f} "
          f">= {GATE_CONSTRAINT}: {data['constraint_rate']['pass']}")
    print(f"  composite delta +{data['composite_delta']['n_pos']} / "
          f"={data['composite_delta']['n_zero']} / "
          f"-{data['composite_delta']['n_neg']}, "
          f"Wilcoxon P = {data['composite_delta']['wilcoxon_p']:.4f}")
    print(f"  budget mean {data['budget']['mean']:.2f} / cap {data['budget']['cap']}, "
          f"violations {data['budget']['violations']}, llm {data['budget']['llm_calls']}")
    return 0


def verify() -> int:
    stored = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    fresh = build_panel_data()
    if json.dumps(stored, sort_keys=True) == json.dumps(fresh, sort_keys=True):
        print(f"VERIFY OK — {OUT_PATH} byte-identical on recomputation")
        return 0
    print("VERIFY FAIL — panel_data.json differs from recomputation")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="recompute and byte-compare the stored panel data")
    args = ap.parse_args()
    raise SystemExit(verify() if args.verify else main())
