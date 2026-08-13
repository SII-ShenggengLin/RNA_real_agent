#!/usr/bin/env python3
"""RNAsmol boundary panel: in-distribution vs out-of-distribution scoring power.

Pre-registered expectations (recorded before the run, per MANUSCRIPT.md §2):
  - In-distribution arms (RNAsmol's own held-out test splits and decoy case
    studies, scored with the matching dataset checkpoint) should show clear
    screening power: test AUROC > 0.8 gate; decoy true binder in top 5%.
  - The out-of-distribution arm (the Fig-2h short-aptamer panel: theophylline
    aptamer 1O15 / HIV-1 TAR 1ANR / guanine riboswitch 1Y27 vs their ligands)
    is expected at chance (AUROC ~ 0.5), reproducing the registered Fig-2h
    tool boundary with the RNAsmol component alone.

Verdict rule: GO if every in-distribution AUROC > 0.8 (CI excluding 0.5) AND
the OOD panel AUROC CI includes 0.5. The point is a two-sided boundary
statement: the oracle works inside its training distribution and only there.

Arms:
  1. robin_test  — full robin_molperturbation data_test.csv (1492 rows),
                   dataset="robin", perturbation_type="molperturbation".
  2. pdb_test    — full pdb_molperturbation data_test.csv (170 rows),
                   dataset="pdb", perturbation_type="molperturbation".
                   (>500-nt rows are truncated service-side; count reported,
                   plus a <=500-nt subset AUROC as sensitivity.)
  3. decoys      — FMN_ribocil_decoy (1601 rows, 1 true binder; pdb checkpoint)
                   and MALAT1_furamidine_decoy (robin checkpoint): rank of the
                   true binder among all rows.
  4. ood_aptamer — the 17 Fig-2h pairs from
                   data/benchmarks/external_anchors/small_molecule/pairs.json,
                   rescored through RNAsmol (pdb checkpoint, the deployed
                   default) for a same-oracle comparison.

Outputs:
  experiments/results/rnasmol_boundary_panel.jsonl  (per-pair scores)
  experiments/results/rnasmol_boundary_panel.json   (summary + verdict)

Usage (from `rna_agent_system/`):
    python experiments/run_rnasmol_boundary_panel.py [--service http://127.0.0.1:8007/score]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RNASMOL_DATA = PROJECT_ROOT / "external_repos" / "RNAsmol" / "rnasmol" / "data"
RESULTS = PROJECT_ROOT / "experiments" / "results"
PAIRS_JSON = PROJECT_ROOT / "data" / "benchmarks" / "external_anchors" / "small_molecule" / "pairs.json"

ARMS = {
    "robin_test": {
        "csv": RNASMOL_DATA / "robin_molperturbation" / "raw" / "data_test.csv",
        "dataset": "robin", "perturbation_type": "molperturbation",
    },
    "pdb_test": {
        "csv": RNASMOL_DATA / "pdb_molperturbation" / "raw" / "data_test.csv",
        "dataset": "pdb", "perturbation_type": "molperturbation",
    },
    "FMN_ribocil_decoy": {
        "csv": RNASMOL_DATA / "FMN_ribocil_decoy" / "raw" / "data_test.csv",
        "dataset": "pdb", "perturbation_type": "molperturbation",
    },
    "MALAT1_furamidine_decoy": {
        "csv": RNASMOL_DATA / "MALAT1_furamidine_decoy" / "raw" / "data_test.csv",
        "dataset": "robin", "perturbation_type": "molperturbation",
    },
}


def score_pair(url: str, rna: str, smiles: str, dataset: str, perturbation: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps({"rna_sequence": rna, "smiles": smiles, "dataset": dataset,
                         "perturbation_type": perturbation}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as fh:
        return json.loads(fh.read())


def auroc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def bootstrap_auroc_ci(pos: list[float], neg: list[float], n_boot: int = 10000,
                       seed: int = 0) -> tuple[float, float, float]:
    point = auroc(pos, neg)
    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        ps = [pos[rng.randrange(len(pos))] for _ in pos]
        ns = [neg[rng.randrange(len(neg))] for _ in neg]
        stats.append(auroc(ps, ns))
    stats.sort()
    return point, stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--service", default="http://127.0.0.1:8007/score")
    args = parser.parse_args()

    jsonl_path = RESULTS / "rnasmol_boundary_panel.jsonl"
    summary: dict = {"service": args.service, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    fh = jsonl_path.open("w", encoding="utf-8")

    for arm, spec in ARMS.items():
        rows = list(csv.DictReader(spec["csv"].open()))
        t0 = time.time()
        records = []
        for r in rows:
            res = score_pair(args.service, r["target_sequence"], r["compound_iso_smiles"],
                             spec["dataset"], spec["perturbation_type"])
            rec = {"arm": arm, "rna_len": len(r["target_sequence"]),
                   "label": float(r["affinity"]),
                   "probability_positive": res["probability_positive"],
                   "checkpoint": Path(res["checkpoint_path"]).name}
            records.append(rec)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        pos = [r["probability_positive"] for r in records if r["label"] == 1.0]
        neg = [r["probability_positive"] for r in records if r["label"] == 0.0]
        n_trunc = sum(1 for r in records if r["rna_len"] > 500)
        entry = {"n": len(records), "n_pos": len(pos), "n_neg": len(neg),
                 "n_rna_over_500nt_truncated": n_trunc,
                 "elapsed_seconds": round(time.time() - t0, 1)}
        if arm.endswith("decoy"):
            ranked = sorted(records, key=lambda r: -r["probability_positive"])
            binder_rank = next(i + 1 for i, r in enumerate(ranked) if r["label"] == 1.0)
            entry.update({"true_binder_rank": binder_rank,
                          "true_binder_percentile": round(100 * binder_rank / len(records), 3),
                          "top5pct_gate_pass": binder_rank <= 0.05 * len(records)})
        else:
            point, lo, hi = bootstrap_auroc_ci(pos, neg)
            entry.update({"auroc": round(point, 4), "auroc_ci95": [round(lo, 4), round(hi, 4)],
                          "auroc_gate_0.8_pass": point > 0.8 and lo > 0.5})
            if arm == "pdb_test" and n_trunc:
                sub = [r for r in records if r["rna_len"] <= 500]
                sp = [r["probability_positive"] for r in sub if r["label"] == 1.0]
                sn = [r["probability_positive"] for r in sub if r["label"] == 0.0]
                p2, l2, h2 = bootstrap_auroc_ci(sp, sn)
                entry["subset_le500nt"] = {"n": len(sub), "auroc": round(p2, 4),
                                           "auroc_ci95": [round(l2, 4), round(h2, 4)]}
        summary[arm] = entry
        print(f"{arm}: {json.dumps(entry)}", flush=True)

    # OOD arm: the Fig-2h short-aptamer panel, rescored through RNAsmol alone.
    pairs = json.loads(PAIRS_JSON.read_text())
    ood_records = []
    for p in pairs:
        res = score_pair(args.service, p["rna_sequence"], p["smiles"], "pdb", "molperturbation")
        rec = {"arm": "ood_aptamer", "pair_id": p.get("pair_id"), "expected": p.get("expected"),
               "negative_class": p.get("negative_class"),
               "probability_positive": res["probability_positive"]}
        ood_records.append(rec)
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    b = [r["probability_positive"] for r in ood_records if r["expected"] == "binder"]
    nc = [r["probability_positive"] for r in ood_records if r.get("negative_class") == "near_cognate"]
    rc = [r["probability_positive"] for r in ood_records if r.get("negative_class") == "random_chemistry"]
    # pairs.json may lack explicit negative_class on the 4 near-cognate rows
    # (the Fig-2h driver defaulted them); replicate that default here.
    if not nc:
        nc = [r["probability_positive"] for r in ood_records
              if r["expected"] != "binder" and r.get("negative_class") is None]
        rc = [r["probability_positive"] for r in ood_records if r.get("negative_class") == "random_chemistry"]
    p_rc, lo_rc, hi_rc = bootstrap_auroc_ci(b, rc)
    p_nc, lo_nc, hi_nc = bootstrap_auroc_ci(b, nc)
    summary["ood_aptamer"] = {
        "n": len(ood_records), "n_binders": len(b), "n_near_cognate": len(nc), "n_random_chem": len(rc),
        "auroc_vs_random_chem": round(p_rc, 4), "auroc_vs_random_chem_ci95": [round(lo_rc, 4), round(hi_rc, 4)],
        "auroc_vs_near_cognate": round(p_nc, 4), "auroc_vs_near_cognate_ci95": [round(lo_nc, 4), round(hi_nc, 4)],
        "chance_consistent": lo_rc <= 0.5 <= hi_rc,
        "per_pair": ood_records,
    }
    fh.close()

    in_dist_ok = all(summary[a].get("auroc_gate_0.8_pass") for a in ("robin_test", "pdb_test"))
    decoy_ok = all(summary[a]["top5pct_gate_pass"] for a in ("FMN_ribocil_decoy", "MALAT1_furamidine_decoy"))
    summary["verdict"] = {
        "in_distribution_auroc_gt_0.8_all": in_dist_ok,
        "decoy_top5pct_all": decoy_ok,
        "ood_chance_consistent": summary["ood_aptamer"]["chance_consistent"],
        "go": bool(in_dist_ok and decoy_ok and summary["ood_aptamer"]["chance_consistent"]),
    }
    out = RESULTS / "rnasmol_boundary_panel.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary["verdict"], indent=2))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
