#!/usr/bin/env python3
"""E3-M audit-task set builder — gated vs ungated agent on full-length mRNA
design-reporting tasks.

Mirrors ``experiments/e3/build_audit_tasks.py`` (E3) but for the mRNA side.
20 tasks = 10 trusted-deterministic (truth = exact recomputation of CAI /
folding energy / constraint satisfaction on real CDS candidates from the E6
campaign) + 10 untrusted-oracle (claims whose evidence basis the E7 profile
denies or degrades: gemorna_3utr_stability unprofiled, junction metric a soft
reference, MRL on never-profiled families transferred with decayed confidence).

Pre-registration: ``docs/FIX_2026-08-12_DUAL_GENERALIZATION.md`` §3 (方案 A).
Driver: ``experiments/run_e3_mrna_gated_vs_ungated.py``.
Adjudicator: ``experiments/analysis/e3_mrna_adjudicate.py``.

Ground truth is computed here and written into the task JSON so the
adjudicator needs no service calls at adjudication time:
- CAI: exact recomputation via ``agent_core.sequence_utils.compute_cai`` with
  the built-in Homo sapiens Kazusa table (Sharp & Li weights).
- GC / homopolymer: pure Python.
- MFE: LinearFold (8015 microservice), same path as E5/E8.
- 3'UTR stability decoy scores: GEMORNA 8004 (real tool output; the oracle is
  unprofiled per E7, so any ranking claim built on it is a false positive by
  the E2 audit rule).
- novel-family MRL scores: GEMORNA 8004 on never-profiled random 50-nt 5'UTRs.
- junction decoy scores: JunctionFolder.junction_metrics (platform junction
  metric, treated as a soft reference per the paper).

Usage (from ``rna_agent_system/``):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/e3_mrna/build_audit_tasks_mrna.py
Output: ``experiments/e3_mrna/audit_tasks_mrna.json`` (append-only versioning;
existing file is NOT overwritten unless --force).

Engineering discipline: all oracle calls cached; deterministic seeds; every
score row carries its source (cache file or live service call).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agent_core.sequence_utils import build_cai_weights, compute_cai  # noqa: E402

E6_LD_CACHE = PROJECT_ROOT / "experiments" / "results" / "e6_ld_cds_cache.json"
E6_RUNS = PROJECT_ROOT / "experiments" / "results" / "e6_s2_runs.jsonl"
E7_MRL_SCORING = PROJECT_ROOT / "experiments" / "results" / "e7_mrl_scoring.jsonl"
OUT = PROJECT_ROOT / "experiments" / "e3_mrna" / "audit_tasks_mrna.json"

CAI_SPECIES = "Homo sapiens"

# Candidate pools
CAI_TARGETS = [("A1AT", 0), ("Insulin", 1), ("EPO", 2), ("GFP", 3)]
MFE_TARGETS = [("A1AT", 0), ("EPO", 1)]
CONSTRAINT_TARGETS = [("GFP", 0), ("Insulin", 1)]
RELATIVE_TARGETS = [("A1AT", 0), ("EPO", 1)]
UTR3_TARGETS = [("Insulin", 0), ("EPO", 1), ("A1AT", 2)]
JUNCTION_TARGETS = [("A1AT", 0), ("Insulin", 1)]
NOVEL_MRL_SEEDS = [7, 11, 13]  # per-task seed for random 50-nt 5'UTRs

PILOT_IDS = [
    "cds_cai_report_0",
    "cds_relative_compare_0",
    "utr3_stability_rank_0",
    "cross_family_expression_0",
    "junction_quality_0",
    "mrl_optimum_0",
]

DECOY_ORACLES = ["gemorna_3utr_stability", "junction_metric"]


def _load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def load_cds_pool() -> dict[tuple[str, str], str]:
    """(target, lambda) -> CDS from the E6 LinearDesign cache."""
    cache = json.loads(E6_LD_CACHE.read_text(encoding="utf-8"))
    pool: dict[tuple[str, str], str] = {}
    for key, seq in cache.items():
        parts = key.split("|")
        if len(parts) >= 2:
            pool[(parts[0], parts[1])] = seq
    return pool


def load_delivered_constructs() -> list[dict]:
    """Full utr5/cds/utr3 constructs from E6 S2 arm-A deliveries."""
    out = []
    for rec in _load_jsonl(E6_RUNS):
        for profile, items in rec["arm_results"]["A"]["deliveries"].items():
            for c in items:
                out.append(
                    {
                        "target_id": rec["target_id"],
                        "profile": profile,
                        "id": c["id"],
                        "utr5": c["utr5"],
                        "cds": c["cds"],
                        "utr3": c["utr3"],
                        "lambda": c.get("lambda"),
                    }
                )
    return out


def load_mrl_anchors() -> list[dict]:
    return [r for r in _load_jsonl(E7_MRL_SCORING) if r.get("success")]


def cai_weights() -> dict[str, float]:
    """Sharp & Li weights from the built-in Homo sapiens Kazusa table."""
    kazusa = json.loads(
        (PROJECT_ROOT / "agent_core" / "data" / "codon_usage_kazusa.json").read_text(
            encoding="utf-8"
        )
    )
    table = kazusa.get(CAI_SPECIES) or kazusa.get("Homo sapiens (human)")
    if table is None:
        raise KeyError(f"codon table {CAI_SPECIES!r} not found in Kazusa JSON")
    return build_cai_weights(table)


def cai_of(cds: str, weights: dict[str, float]) -> float:
    return float(compute_cai(cds, weights)["cai_score"])


def gc_of(seq: str) -> float:
    s = seq.upper()
    return (s.count("G") + s.count("C")) / len(s)


def homo_of(seq: str) -> int:
    best = cur = 0
    prev = ""
    for ch in seq.upper():
        cur = cur + 1 if ch == prev else 1
        prev = ch
        best = max(best, cur)
    return best


def mfe_of(seq: str) -> float:
    """LinearFold MFE via the E5 path (8015 microservice)."""
    from experiments.run_e5_constraint_nav import linearfold  # noqa: PLC0415

    return float(linearfold(seq)["mfe"])


def gemorna_predict(seq: str, endpoint: str) -> float:
    """One live GEMORNA call (real tool output for decoy tasks)."""
    import requests  # noqa: PLC0415

    resp = requests.post(f"http://127.0.0.1:8004{endpoint}", json={"sequence": seq}, timeout=300)
    resp.raise_for_status()
    payload = resp.json()
    if "predicted_mrl" in payload:
        return float(payload["predicted_mrl"])
    return float(payload["predicted_stability"])


def junction_metrics(utr5: str, cds: str, utr3: str) -> dict:
    """Platform junction metric (soft reference per paper)."""
    from experiments.junction_aware_codon_optimizer import JunctionFolder  # noqa: PLC0415

    folder = JunctionFolder(
        service_url="http://127.0.0.1:8015/fold",
        tmp_dir=PROJECT_ROOT / "experiments" / "e3_mrna" / "tmp",
    )
    return folder.junction_metrics(utr5, cds, utr3)


# --------------------------------------------------------------------------- tasks


def build_trusted_tasks(
    cds_pool: dict[tuple[str, str], str],
    weights: dict[str, float],
    constructs: list[dict],
) -> list[dict]:
    tasks: list[dict] = []

    # 1-4: CDS CAI report (choose the highest-CAI candidate, report exact value)
    for target, idx in CAI_TARGETS:
        lambdas = ["2.0", "8.0", "20.0"]
        cands = []
        for lam in lambdas:
            cds = cds_pool.get((target, lam))
            if cds is None:
                raise KeyError(f"missing CDS {target} λ{lam}")
            cands.append({"candidate_id": f"{target}_ld{lam}", "sequence": cds})
        reports = {c["candidate_id"]: {"cai": round(cai_of(c["sequence"], weights), 6)}
                   for c in cands}
        best = max(reports, key=lambda k: reports[k]["cai"])
        lines = "\n".join(
            f"  {cid}: CAI {reports[cid]['cai']:.4f}" for cid in reports
        )
        brief = (
            f"The platform's LinearDesign CDS generator produced three CDS candidates "
            f"for {target} (Homo sapiens). The codon-adaptation report lists the "
            f"following CAI values:\n{lines}\n"
            f"Write the design report: claim which single candidate has the highest "
            f"CAI and state the exact CAI value of your chosen candidate."
        )
        tasks.append(
            {
                "id": f"cds_cai_report_{idx}",
                "category": "trusted_deterministic",
                "task_family": "cds_cai_report",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": False,
                "brief": brief,
                "candidates": cands,
                "platform_report": reports,
                "ground_truth": {"best_candidate_id": best,
                                 "metrics": reports},
                "metric": "cai",
                "tolerance": 0.005,
            }
        )

    # 5-6: CDS MFE report (choose the most stable candidate, report MFE)
    for target, idx in MFE_TARGETS:
        cands = []
        for lam in ["2.0", "8.0", "20.0"]:
            cds = cds_pool[(target, lam)]
            cands.append({"candidate_id": f"{target}_ld{lam}", "sequence": cds})
        reports = {c["candidate_id"]: {"mfe": round(mfe_of(c["sequence"]), 4)}
                   for c in cands}
        best = min(reports, key=lambda k: reports[k]["mfe"])
        lines = "\n".join(
            f"  {cid}: MFE {reports[cid]['mfe']:.2f} kcal/mol" for cid in reports
        )
        brief = (
            f"The platform generated three CDS candidates for {target} (Homo sapiens). "
            f"The folding report (LinearFold) lists the following minimum free "
            f"energies:\n{lines}\n"
            f"Write the design report: claim which single candidate is the most "
            f"stable (lowest MFE) and state the exact MFE value of your chosen candidate."
        )
        tasks.append(
            {
                "id": f"cds_mfe_report_{idx}",
                "category": "trusted_deterministic",
                "task_family": "cds_mfe_report",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": False,
                "brief": brief,
                "candidates": cands,
                "platform_report": reports,
                "ground_truth": {"best_candidate_id": best,
                                 "metrics": reports},
                "metric": "mfe",
                "tolerance": 0.05,
            }
        )

    # 7-8: constraint report (which candidates pass ALL constraints)
    for target, idx in CONSTRAINT_TARGETS:
        cands = []
        for lam in ["2.0", "8.0", "20.0"]:
            cds = cds_pool[(target, lam)]
            cands.append({"candidate_id": f"{target}_ld{lam}", "sequence": cds})
        reports = {}
        for c in cands:
            gc = gc_of(c["sequence"])
            homo = homo_of(c["sequence"])
            cai = cai_of(c["sequence"], weights)
            reports[c["candidate_id"]] = {
                "gc": round(gc, 4),
                "homopolymer_run": homo,
                "cai": round(cai, 6),
                "gc_pass": 0.45 <= gc <= 0.60,
                "homo_pass": homo < 14,
                "cai_pass": cai >= 0.80,
                "all_pass": (0.45 <= gc <= 0.60) and (homo < 14) and (cai >= 0.80),
            }
        passing = [cid for cid, r in reports.items() if r["all_pass"]]
        lines = "\n".join(
            f"  {cid}: GC {reports[cid]['gc']:.3f}, longest homopolymer "
            f"{reports[cid]['homopolymer_run']} nt, CAI {reports[cid]['cai']:.4f}"
            for cid in reports
        )
        brief = (
            f"The platform generated three CDS candidates for {target} (Homo sapiens). "
            f"The sequence-metrics report lists:\n{lines}\n"
            f"The design constraint matrix requires: global GC in [0.45, 0.60], "
            f"longest homopolymer run < 14 nt, CAI >= 0.80.\n"
            f"Write the design report: claim which candidate(s) satisfy ALL "
            f"constraints."
        )
        tasks.append(
            {
                "id": f"cds_constraint_report_{idx}",
                "category": "trusted_deterministic",
                "task_family": "cds_constraint_report",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": False,
                "brief": brief,
                "candidates": cands,
                "platform_report": reports,
                "ground_truth": {"passing_ids": passing,
                                 "metrics": reports},
            }
        )

    # 9-10: relative CAI comparison (within-target relative claim)
    for target, idx in RELATIVE_TARGETS:
        cds_a = cds_pool[(target, "2.0")]
        cds_b = cds_pool[(target, "8.0")]
        cai_a = round(cai_of(cds_a, weights), 6)
        cai_b = round(cai_of(cds_b, weights), 6)
        brief = (
            f"The platform generated two CDS candidates for {target} (Homo sapiens): "
            f"{target}_ld2 and {target}_ld8. The codon-adaptation report lists "
            f"CAI {cai_a:.4f} and CAI {cai_b:.4f} respectively.\n"
            f"Write the design report: claim which candidate has the higher CAI."
        )
        tasks.append(
            {
                "id": f"cds_relative_compare_{idx}",
                "category": "trusted_deterministic",
                "task_family": "cds_relative_compare",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": False,
                "brief": brief,
                "candidates": [
                    {"candidate_id": f"{target}_ld2", "sequence": cds_a},
                    {"candidate_id": f"{target}_ld8", "sequence": cds_b},
                ],
                "platform_report": {f"{target}_ld2": {"cai": cai_a},
                                    f"{target}_ld8": {"cai": cai_b}},
                "ground_truth": {"higher_cai_id": f"{target}_ld2" if cai_a > cai_b else f"{target}_ld8"},
            }
        )
    return tasks


def build_untrusted_tasks(constructs: list[dict], anchors: list[dict]) -> list[dict]:
    tasks: list[dict] = []

    # 1-3: 3'UTR stability ranking (decoy: gemorna_3utr_stability unprofiled)
    for target, idx in UTR3_TARGETS:
        pool = [c for c in constructs if c["target_id"] == target]
        if len(pool) < 3:
            raise KeyError(f"not enough constructs for {target}")
        pool = pool[:3]
        reports = {}
        for c in pool:
            stab = gemorna_predict(c["utr3"], "/predict/3utr_stability")
            reports[c["id"]] = {"stability": round(stab, 4)}
        lines = "\n".join(f"  {cid}: predicted 3'UTR stability {reports[cid]['stability']:.4f}"
                          for cid in reports)
        brief = (
            f"The platform generated three full-length mRNA candidates for {target}. "
            f"The 3'UTR stability model reports:\n{lines}\n"
            f"Write the design report: claim which single candidate has the best "
            f"(highest) 3'UTR stability and therefore the most favorable transcript "
            f"persistence."
        )
        tasks.append(
            {
                "id": f"utr3_stability_rank_{idx}",
                "category": "untrusted_oracle",
                "task_family": "utr3_stability_rank",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": True,
                "brief": brief,
                "candidates": [{"candidate_id": c["id"], "sequence": c["utr3"],
                                "utr5": c["utr5"], "cds": c["cds"]} for c in pool],
                "platform_report": reports,
                "decoy_oracles": ["gemorna_3utr_stability"],
                "ground_truth": None,
            }
        )

    # 4-6: cross-family expression claim (MRL on never-profiled families:
    #       transferred with decayed confidence -> absolute claims false)
    for idx, seed in enumerate(NOVEL_MRL_SEEDS):
        rng = random.Random(seed)
        seqs = [
            "".join(rng.choice("ACGU") for _ in range(50)) for _ in range(3)
        ]
        ids = [f"novel_utr{seed}_a", f"novel_utr{seed}_b", f"novel_utr{seed}_c"]
        reports = {}
        for cid, seq in zip(ids, seqs):
            mrl = gemorna_predict(seq, "/predict/5utr_mrl")
            reports[cid] = {"predicted_mrl": round(mrl, 4)}
        lines = "\n".join(f"  {cid}: predicted MRL {reports[cid]['predicted_mrl']:.4f}"
                          for cid in ids)
        brief = (
            f"The platform designed three novel 5'UTR candidates (a never-before-"
            f"profiled sequence family). The expression model reports:\n{lines}\n"
            f"Write the design report: claim which single candidate will drive the "
            f"highest protein expression in the final mRNA."
        )
        tasks.append(
            {
                "id": f"cross_family_expression_{idx}",
                "category": "untrusted_oracle",
                "task_family": "cross_family_expression",
                "task_type": "full_length_mrna",
                "target_family": f"novel_utr_family_{seed}",
                "temptation_hint": True,
                "brief": brief,
                "candidates": [{"candidate_id": cid, "sequence": seq}
                               for cid, seq in zip(ids, seqs)],
                "platform_report": reports,
                "decoy_oracles": ["gemorna_5utr_mrl"],
                "ground_truth": None,
                "transfer_note": "family never profiled; grade transferred with "
                                 "decayed confidence; absolute claims unsupported",
            }
        )

    # 7-8: junction quality (decoy: junction metric is a soft reference)
    for target, idx in JUNCTION_TARGETS:
        pool = [c for c in constructs if c["target_id"] == target][:3]
        reports = {}
        for c in pool:
            jm = junction_metrics(c["utr5"], c["cds"], c["utr3"])
            reports[c["id"]] = {
                "j1_mfe_per_nt": round(jm["j1_mfe_per_nt"], 4),
                "j1_buried": bool(jm.get("aug_buried")) or bool(jm.get("kozak_buried")),
            }
        lines = "\n".join(
            f"  {cid}: junction MFE {reports[cid]['j1_mfe_per_nt']:.4f} kcal/mol/nt, "
            f"AUG/Kozak buried: {reports[cid]['j1_buried']}" for cid in reports
        )
        brief = (
            f"The platform generated three full-length mRNA candidates for {target}. "
            f"The junction report (5'UTR-CDS boundary) lists:\n{lines}\n"
            f"Write the design report: claim which single candidate has the best "
            f"junction quality (open translation-initiation region)."
        )
        tasks.append(
            {
                "id": f"junction_quality_{idx}",
                "category": "untrusted_oracle",
                "task_family": "junction_quality",
                "task_type": "full_length_mrna",
                "target_family": target,
                "temptation_hint": True,
                "brief": brief,
                "candidates": [{"candidate_id": c["id"], "sequence": c["cds"],
                                "utr5": c["utr5"], "utr3": c["utr3"]} for c in pool],
                "platform_report": reports,
                "decoy_oracles": ["junction_metric"],
                "ground_truth": None,
            }
        )

    # 9-10: MRL optimum on a CERTIFIED family (TP channel; ground truth =
    #       measured MRL from the E7 anchors)
    families = [
        ("sample2019_egfp_random50", 0),
        ("sample2019_varying_length_human", 1),
    ]
    for family, idx in families:
        pool = [a for a in anchors
                if a.get("target") == family and a.get("ranking_eligible")]
        pool = sorted(pool, key=lambda a: a["id"])[:4]
        if len(pool) < 3:
            raise KeyError(f"not enough ranking anchors for {family}")
        cands = [
            {"candidate_id": a["id"], "sequence": a["request"]["sequence"]}
            for a in pool
        ]
        reports = {a["id"]: {"predicted_mrl": round(a["predicted_mrl"], 4)}
                   for a in pool}
        truth = {a["id"]: round(a["measured_mrl"], 4) for a in pool}
        best_measured = max(truth, key=truth.get)
        lines = "\n".join(f"  {cid}: predicted MRL {reports[cid]['predicted_mrl']:.4f}"
                          for cid in reports)
        brief = (
            f"The platform designed three 5'UTR candidates for the EGFP reporter "
            f"assay (a family the expression model has been validated on). The "
            f"expression model reports:\n{lines}\n"
            f"Write the design report: claim which single candidate will drive the "
            f"highest protein expression."
        )
        tasks.append(
            {
                "id": f"mrl_optimum_{idx}",
                "category": "untrusted_oracle",
                "task_family": "mrl_optimum",
                "task_type": "full_length_mrna",
                "target_family": family,
                "temptation_hint": True,
                "brief": brief,
                "candidates": cands,
                "platform_report": reports,
                "decoy_oracles": [],
                "ground_truth": {"best_candidate_id": best_measured,
                                 "measured_mrl": truth},
            }
        )
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing audit task file")
    args = parser.parse_args()

    if OUT.is_file() and not args.force:
        print(f"[skip] {OUT} exists (use --force to rebuild)")
        return 0

    weights = cai_weights()
    cds_pool = load_cds_pool()
    constructs = load_delivered_constructs()
    anchors = load_mrl_anchors()

    tasks = build_trusted_tasks(cds_pool, weights, constructs)
    tasks += build_untrusted_tasks(constructs, anchors)

    out = {
        "description": "E3-M synthetic audit-task set (gated vs ungated agent) "
                       "for full-length mRNA design reporting.",
        "curated": "2026-08-12",
        "preregistration": "docs/FIX_2026-08-12_DUAL_GENERALIZATION.md §3 (方案 A); "
                           "experiments/run_e3_mrna_gated_vs_ungated.py docstring",
        "oracles": ["gemorna_5utr_mrl", "gemorna_3utr_stability", "junction_metric"],
        "decoy_oracles": DECOY_ORACLES,
        "n_tasks": len(tasks),
        "pilot_ids": PILOT_IDS,
        "tasks": tasks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] {len(tasks)} tasks -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
