#!/usr/bin/env python3
"""Fig 3 driver: BMC Type-I coordination ablation on 20 full-length mRNA targets.

Implements `docs/MANUSCRIPT.md` §5.1 run matrix A:
20 targets × `bmc_max_rounds` ∈ {0 (Serial), 1, 2, 3} × 3 repeats = 240 runs.

Common params per run (from the target JSON): design_tool="all", lambda_value=2.0,
utr_mode="all", cai_species=<species_for_codon_optimization>,
bmc_improvement_threshold=0.05, reference_point omitted (utopian mode).

Output: `experiments/results/fig3_type1_runs.jsonl` — one record per run with the
best candidate's dimension scores, junction metrics, burial flags, ASF distance,
Pareto size, and the full `_bmc_trace`.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type1_ablation.py \
        [--targets T1,T2] [--rounds 0,1,2,3] [--reps 3] [--limit N] [--resume] [--timeout SEC]

OPS NOTE (2026-07 campaign): use `--timeout 9000` for large proteins
(HER2, SARS-CoV-2_Spike_WT — serial rounds alone approach the 5400s ceiling
under shared-machine load; BMC rounds push past it). 5400s was sufficient for
all other fig3 targets. Zika/Factor_VIII can hit the deterministic
LinearDesign ≥7 kb OOM boundary — expected, see RESUME_CHECKPOINT §4.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT, run_task_dict  # noqa: E402

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-FullLength-mRNA" / "targets"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig3_type1_runs.jsonl"

BEST_SCORE_KEYS = [
    "asf_distance", "cds_component", "utr5_mrl", "utr3_stability", "full_mfe_score",
    "junction_5utr_cds_score", "junction_cds_3utr_score",
    "cds_cai", "cds_mfe", "full_length_mfe", "full_mfe_per_nt",
    "utr5_predicted_mrl", "utr3_predicted_stability",
    "junction_5utr_cds_mfe", "junction_5utr_cds_mfe_per_nt",
    "junction_cds_3utr_mfe", "junction_cds_3utr_mfe_per_nt",
    "junction_5utr_cds_gc_diff", "junction_cds_3utr_gc_diff",
    "junction_5utr_cds_aug_buried", "junction_5utr_cds_kozak_buried",
]


def load_done_keys(output: Path) -> set[tuple]:
    done = set()
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("success"):
                done.add((r["target_id"], r["bmc_max_rounds"], r["rep"]))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=None, help="comma-separated target ids (default: all 20)")
    parser.add_argument("--rounds", default="0,1,2,3", help="comma-separated bmc_max_rounds values")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None, help="max number of runs (after filtering)")
    parser.add_argument("--resume", action="store_true", help="skip (target, rounds, rep) already successful")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    target_files = sorted(TARGETS_DIR.glob("*.json"))
    if args.targets:
        wanted = set(args.targets.split(","))
        target_files = [p for p in target_files if p.stem in wanted]
    rounds_list = [int(x) for x in args.rounds.split(",")]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done = load_done_keys(args.output) if args.resume else set()

    jobs = [
        (tf, r, rep)
        for tf in target_files
        for r in rounds_list
        for rep in range(args.reps)
    ]
    if args.limit:
        jobs = jobs[: args.limit]

    n_ok = n_fail = 0
    for i, (tf, rounds, rep) in enumerate(jobs, 1):
        meta = json.loads(tf.read_text())
        target_id = meta["target_id"]
        if (target_id, rounds, rep) in done:
            continue
        params = {
            "protein_sequence": meta["protein_sequence"].upper(),
            "design_tool": "all",
            "lambda_value": 2.0,
            "cai_species": meta.get("species_for_codon_optimization") or "human",
            "utr_mode": "all",
            "bmc_max_rounds": rounds,
            "bmc_improvement_threshold": 0.05,
        }
        task = {
            "task_id": f"t1_{target_id}_r{rounds}_rep{rep}",
            "workflow": "full_length_mrna_design",
            "category": "bmc_type1_ablation",
            "description": f"{target_id} bmc_max_rounds={rounds} rep{rep}",
            "input": params,
            "evaluation_rubric": None,
        }
        print(f"[{i}/{len(jobs)}] {target_id} rounds={rounds} rep={rep} ...", flush=True)
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig3t1")
        best = rec.get("best_candidate") or {}
        best_scores = best.get("scores") or {}
        out = {
            "target_id": target_id,
            "bmc_max_rounds": rounds,
            "rep": rep,
            "success": rec["success"],
            "error": rec.get("error"),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "candidate_count": rec.get("candidate_count"),
            "pareto_frontier_size": rec.get("pareto_frontier_size"),
            "bmc_rounds_executed": rec.get("bmc_rounds"),
            "quality_actions": rec.get("quality_actions"),
            "best_candidate_id": best.get("id"),
            "best": {k: best_scores.get(k) for k in BEST_SCORE_KEYS},
            "bmc_trace": rec.get("bmc_trace"),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        if rec["success"]:
            n_ok += 1
        else:
            n_fail += 1
        print(f"      -> {'OK' if rec['success'] else 'FAIL(' + str(rec.get('error')) + ')'} "
              f"in {rec.get('elapsed_seconds', 0):.0f}s, asf={best_scores.get('asf_distance')}", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
