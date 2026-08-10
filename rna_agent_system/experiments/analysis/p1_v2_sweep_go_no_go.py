#!/usr/bin/env python3
"""P1 v2 stability-weight sweep — go/no-go analysis (2026-08-04).

Pre-registration: experiments/junction_aware_codon_optimizer.py docstring
(P1 v2 section), approved in REDESIGN_2026-08-03_CALIBRATED_AGENT.md §4.1.

Per weight w_stab in {0 (v1), 0.1, 0.25, 0.5, 1.0} over the same 18 cells
(6 targets x 3 reps, identical serial seeds / iters=3000 / sa_seed per rep):
  (a) hard-target AUG/Kozak burial repair rate (baseline buried -> optimized
      not buried; denominator = hard cells buried at baseline);
  (b) median stability cost = optimized full_construct_mfe_per_nt
      - baseline_serial full_mfe_per_nt (positive = stability degraded);
  (c) median delta CAI (optimized - baseline_serial);
  (d) median delta junction_5utr_cds_mfe_per_nt (optimized - baseline_serial).

GO: exists weight with hard-target repair >= 2/3 AND stability cost <= 50%
of the v1 (w=0) cost AND CAI drop <= 0.02 (vs baseline; i.e. delta >= -0.02).

Inputs:
  - v1 (w=0): experiments/results/p1_junction_optimizer.jsonl (18 cells)
  - sweep:  experiments/results/p1_v2_stability_sweep_<target>.jsonl (72 cells)
Output: experiments/results/p1_v2_stability_sweep_summary.json
"""
from __future__ import annotations

import json
import statistics as stats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402

RESULTS = PROJECT_ROOT / "experiments" / "results"
TARGETS = ["HER2", "Beta_galactosidase", "Influenza_HA_H1N1", "Insulin", "EPO", "Growth_hormone"]

GO_REPAIR_MIN = 2 / 3
GO_COST_FRAC = 0.5
GO_CAI_DROP = 0.02


def load_rows() -> dict[float, list[dict]]:
    rows: dict[float, list[dict]] = {0.0: []}
    for line in (RESULTS / "p1_junction_optimizer.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("success"):
            rows[0.0].append(r)
    for t in TARGETS:
        fp = RESULTS / f"p1_v2_stability_sweep_{t}.jsonl"
        for line in fp.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("success"):
                rows.setdefault(float(r["w_stab"]), []).append(r)
    return rows


def per_weight(recs: list[dict]) -> dict:
    hard = [r for r in recs if r["target_class"] == "hard"]

    def buried(r, side):
        b = r["baseline_serial"]
        return bool(b.get(f"junction_5utr_cds_{side}_buried"))

    denom = [r for r in hard if buried(r, "aug") or buried(r, "kozak")]
    repaired = [
        r for r in denom
        if not r["optimized"]["junction_5utr_cds_aug_buried"]
        and not r["optimized"]["junction_5utr_cds_kozak_buried"]
    ]
    costs, dcai, dj1 = [], [], []
    for r in recs:
        base = r["baseline_serial"]
        opt = r["optimized"]
        if base.get("full_mfe_per_nt") is not None and opt.get("full_construct_mfe_per_nt") is not None:
            costs.append(opt["full_construct_mfe_per_nt"] - base["full_mfe_per_nt"])
        if base.get("cds_cai") is not None and opt.get("cds_cai") is not None:
            dcai.append(opt["cds_cai"] - base["cds_cai"])
        if base.get("junction_5utr_cds_mfe_per_nt") is not None and opt.get("junction_5utr_cds_mfe_per_nt") is not None:
            dj1.append(opt["junction_5utr_cds_mfe_per_nt"] - base["junction_5utr_cds_mfe_per_nt"])
    return {
        "n_cells": len(recs),
        "hard_buried_at_baseline": len(denom),
        "hard_repaired": len(repaired),
        "hard_repair_rate": (len(repaired) / len(denom)) if denom else None,
        "median_stability_cost_per_nt": stats.median(costs) if costs else None,
        "median_delta_cai": stats.median(dcai) if dcai else None,
        "median_delta_j1_mfe_per_nt": stats.median(dj1) if dj1 else None,
    }


def main() -> int:
    rows = load_rows()
    table = {w: per_weight(recs) for w, recs in sorted(rows.items())}
    v1_cost = table[0.0]["median_stability_cost_per_nt"]

    verdicts = {}
    go_weights = []
    for w, m in table.items():
        if w == 0.0:
            continue
        ok = (
            m["hard_repair_rate"] is not None and m["hard_repair_rate"] >= GO_REPAIR_MIN
            and m["median_stability_cost_per_nt"] is not None
            and v1_cost is not None and v1_cost > 0
            and m["median_stability_cost_per_nt"] <= GO_COST_FRAC * v1_cost
            and m["median_delta_cai"] is not None and m["median_delta_cai"] >= -GO_CAI_DROP
        )
        verdicts[str(w)] = ok
        if ok:
            go_weights.append(w)

    decision = "GO" if go_weights else "NO-GO"
    summary = {
        "analysis": "P1 v2 stability-weight sweep go/no-go",
        "date": "2026-08-04",
        "preregistration": "junction_aware_codon_optimizer.py docstring (P1 v2); "
                           "REDESIGN_2026-08-03_CALIBRATED_AGENT.md §4.1",
        "criteria": {
            "hard_repair_rate_min": GO_REPAIR_MIN,
            "stability_cost_max_frac_of_v1": GO_COST_FRAC,
            "cai_drop_max": GO_CAI_DROP,
        },
        "per_weight": {str(w): m for w, m in table.items()},
        "v1_median_stability_cost_per_nt": v1_cost,
        "go_weights": go_weights,
        "decision": decision,
    }
    out = RESULTS / "p1_v2_stability_sweep_summary.json"
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")

    print(f"v1 (w=0) median stability cost/nt: {v1_cost:+.4f}")
    for w, m in table.items():
        print(
            f"w={w:<4} repair {m['hard_repaired']}/{m['hard_buried_at_baseline']} "
            f"({(m['hard_repair_rate'] or 0):.2f}) "
            f"cost {m['median_stability_cost_per_nt']:+.4f}/nt "
            f"dCAI {m['median_delta_cai']:+.4f} "
            f"dj1/nt {m['median_delta_j1_mfe_per_nt']:+.4f}"
            + ("  GO" if verdicts.get(str(w)) else "")
        )
    print(f"\nDecision: {decision} (go_weights={go_weights}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
