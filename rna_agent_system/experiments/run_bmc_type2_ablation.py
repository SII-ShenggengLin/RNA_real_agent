#!/usr/bin/env python3
"""Fig 4 driver: BMC Type-II coordination ablation on 20 aptamer targets.

Implements `docs/MANUSCRIPT.md` §6.1 run matrix A:
20 targets × `bmc_max_rounds` ∈ {0 (Serial), 1, 2, 3} × 3 seed sets = 240 runs.

Common params per run (structure path + chain from the target JSON):
aptamer_length=30, n_odesign_samples=8, bmc_improvement_threshold=0.05,
reference_point omitted (utopian mode). Seed sets: [42,123], [7,99], [2024,31415].

Output: `experiments/results/fig4_type2_runs.jsonl` — one record per run with the
best candidate's objective components, ASF distance, Pareto size, per-candidate
objective vectors (for hypervolume), and the full `_bmc_trace`.

Analysis note (from the Fig-2 pilot): under the default utopian reference the best
candidate's stored `asf_distance` is 0 by construction. BMC-vs-Serial comparisons
must use (a) per-objective raw components, (b) Pareto hypervolume, (c) ASF against
a shared fixed reference (computed from the Serial pool per target).

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_bmc_type2_ablation.py \
        [--targets T1,T2] [--rounds 0,1,2,3] [--limit N] [--resume] [--timeout SEC]

OPS NOTE (2026-07 campaign): Ferritin (1FHA) deterministically yields zero
ODesign sequences (target-side boundary — do not retry); MBP may be aborted by
the QualityAgent (governance case, expected); Myoglobin saw one hallucinated
QualityAgent abort that passed on retry. See RESUME_CHECKPOINT §4.
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

TARGETS_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "targets"
STRUCT_DIR = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Aptamer" / "structures"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig4_type2_runs.jsonl"

SEED_SETS = [[42, 123], [7, 99], [2024, 31415]]
OBJECTIVE_KEYS = ["egarps_component", "rhofold_component", "iptm_component"]


def find_structure(pdb_id: str) -> Path | None:
    """Locate the target's structure file (case-tolerant) under structures/."""
    for cand in STRUCT_DIR.glob(f"{pdb_id.lower()}*.pdb"):
        return cand
    for cand in STRUCT_DIR.glob(f"{pdb_id.upper()}*.pdb"):
        return cand
    for cand in STRUCT_DIR.glob(f"*{pdb_id.lower()}*"):
        return cand
    return None


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
                done.add((r["target_id"], r["bmc_max_rounds"], r["seed_idx"]))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=None, help="comma-separated target ids (default: all 20)")
    parser.add_argument("--rounds", default="0,1,2,3", help="comma-separated bmc_max_rounds values")
    parser.add_argument("--seed-sets", type=int, default=3, help="number of seed sets (max 3)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    target_files = sorted(TARGETS_DIR.glob("*.json"))
    if args.targets:
        wanted = set(args.targets.split(","))
        target_files = [p for p in target_files if p.stem in wanted]
    rounds_list = [int(x) for x in args.rounds.split(",")]
    seed_sets = SEED_SETS[: args.seed_sets]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done = load_done_keys(args.output) if args.resume else set()

    jobs = [(tf, r, si) for tf in target_files for r in rounds_list for si in range(len(seed_sets))]
    if args.limit:
        jobs = jobs[: args.limit]

    n_ok = n_fail = n_skip = 0
    for i, (tf, rounds, si) in enumerate(jobs, 1):
        meta = json.loads(tf.read_text())
        target_id = meta["target_id"]
        if (target_id, rounds, si) in done:
            n_skip += 1
            continue
        struct = find_structure(meta["pdb_id"])
        if struct is None:
            print(f"[{i}/{len(jobs)}] {target_id}: NO STRUCTURE for {meta['pdb_id']}, skipped")
            continue
        params = {
            "protein_structure_path": str(struct.relative_to(PROJECT_ROOT)),
            "chain_id": meta.get("pdb_chain") or "A",
            "aptamer_length": 30,
            "n_odesign_samples": 8,
            "odesign_seeds": seed_sets[si],
            "bmc_max_rounds": rounds,
            "bmc_improvement_threshold": 0.05,
        }
        task = {
            "task_id": f"t2_{target_id}_r{rounds}_s{si}",
            "workflow": "rna_aptamer_design",
            "category": "bmc_type2_ablation",
            "description": f"{target_id} bmc_max_rounds={rounds} seed_set={si}",
            "input": params,
            "evaluation_rubric": None,
        }
        print(f"[{i}/{len(jobs)}] {target_id} rounds={rounds} seeds={seed_sets[si]} ...", flush=True)
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig4t2")
        best = (rec.get("best_candidate") or {}).get("scores") or {}
        pool_objectives = [
            {k: (c.get("scores") or {}).get(k) for k in OBJECTIVE_KEYS}
            for c in (rec.get("candidates") or [])
        ]
        out = {
            "target_id": target_id,
            "pdb_id": meta["pdb_id"],
            "bmc_max_rounds": rounds,
            "seed_idx": si,
            "seeds": seed_sets[si],
            "success": rec["success"],
            "error": rec.get("error"),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "candidate_count": rec.get("candidate_count"),
            "pareto_frontier_size": rec.get("pareto_frontier_size"),
            "bmc_rounds_executed": rec.get("bmc_rounds"),
            "best": {k: best.get(k) for k in OBJECTIVE_KEYS + ["asf_distance"]},
            "pool_objectives": pool_objectives,
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
              f"in {rec.get('elapsed_seconds', 0):.0f}s", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed, {n_skip} resumed-skip -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
