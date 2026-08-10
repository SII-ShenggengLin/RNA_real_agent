#!/usr/bin/env python3
"""Pilot P0 (2026-08-03): budget-matched serial control for the Fig-4 Type-II effect.

MOTIVATION (confound check)
---------------------------
In the Fig-4 campaign every BMC round regenerates a fresh batch of ODesign
candidates (seeds+1 or expanded hotspot), so a BMCx1 run evaluates ~2x the
sequences of a Serial run (pool medians: serial=8, bmc_x1/x2/x3=16 — see
fig4_type2_shard_{a,b}.jsonl). The reported Type-II main effect
(egarps_component p=2.1e-4, hypervolume all-significant) may therefore be a
pure SAMPLING-BUDGET effect rather than a coordination effect.

This driver runs the missing control arm: Serial with the generation budget
matched to BMCx1 (n_odesign_samples=16, same 2 seeds, bmc_max_rounds=0),
on a pilot subset of 4 targets x 3 seed sets = 12 runs.

GO/NO-GO (pre-registered, pilot-scale)
--------------------------------------
Compare per (target, seed_idx) cells, using the existing shard records for
serial / bmc_x1 / bmc_x2 and this file for serial_ext16:
  - GO (coordination has value beyond budget): bmc_x1 vs serial_ext16 on
    egarps_component best-of-pool shows Cliff's delta >= 0.3 in favour of
    bmc_x1 across the 12 cells.
  - NO-GO (budget explains the effect): delta ~ 0 -> narrative pivots to
    "adaptive budget allocation" and pilot P3 (guided vs unguided regeneration
    at matched budget) becomes the main battleground.

Records intentionally keep the fig4 schema (plus `condition` /
`n_odesign_samples`) so `analysis/summarize_fig4.py`-style tooling can be
reused. Same-job dedupe key: (target_id, condition, seed_idx), latest wins.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_budget_matched_control.py \
        [--targets BSA,Lysozyme,Thrombin,VEGF] [--resume] [--timeout 5400]
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
from run_bmc_type2_ablation import (  # noqa: E402
    OBJECTIVE_KEYS,
    SEED_SETS,
    TARGETS_DIR,
    find_structure,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig4_budget_matched.jsonl"
PILOT_TARGETS = ["BSA", "Lysozyme", "Thrombin", "VEGF"]
# Serial baseline generates 8 candidates (n_odesign_samples=8); BMCx1 adds one
# regeneration batch of the same size -> matched budget = 16.
MATCHED_N_SAMPLES = 16
CONDITION = "serial_ext16"


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
                done.add((r["target_id"], r["condition"], r["seed_idx"]))
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=",".join(PILOT_TARGETS), help="comma-separated target ids")
    parser.add_argument("--seed-sets", type=int, default=3, help="number of seed sets (max 3)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    wanted = set(args.targets.split(","))
    target_files = [p for p in sorted(TARGETS_DIR.glob("*.json")) if p.stem in wanted]
    if not target_files:
        print(f"no targets matched {wanted} under {TARGETS_DIR}")
        return 1
    seed_sets = SEED_SETS[: args.seed_sets]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    done = load_done_keys(args.output) if args.resume else set()

    jobs = [(tf, si) for tf in target_files for si in range(len(seed_sets))]
    if args.limit:
        jobs = jobs[: args.limit]

    n_ok = n_fail = n_skip = 0
    for i, (tf, si) in enumerate(jobs, 1):
        meta = json.loads(tf.read_text())
        target_id = meta["target_id"]
        if (target_id, CONDITION, si) in done:
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
            # Budget-matched: 2x the serial sample count in ONE undirected batch
            # with the SAME seeds -> same generator, double budget, no coordination.
            "n_odesign_samples": MATCHED_N_SAMPLES,
            "odesign_seeds": seed_sets[si],
            "bmc_max_rounds": 0,
            "bmc_improvement_threshold": 0.05,
        }
        task = {
            "task_id": f"t2bm_{target_id}_{CONDITION}_s{si}",
            "workflow": "rna_aptamer_design",
            "category": "bmc_budget_matched_control",
            "description": f"{target_id} {CONDITION} seed_set={si}",
            "input": params,
            "evaluation_rubric": None,
        }
        print(f"[{i}/{len(jobs)}] {target_id} {CONDITION} seeds={seed_sets[si]} ...", flush=True)
        rec = run_task_dict(task, timeout=args.timeout, env=env, session_prefix="fig4bm")
        best = (rec.get("best_candidate") or {}).get("scores") or {}
        pool_objectives = [
            {k: (c.get("scores") or {}).get(k) for k in OBJECTIVE_KEYS}
            for c in (rec.get("candidates") or [])
        ]
        out = {
            "target_id": target_id,
            "pdb_id": meta["pdb_id"],
            "condition": CONDITION,
            "bmc_max_rounds": 0,
            "n_odesign_samples": MATCHED_N_SAMPLES,
            "seed_idx": si,
            "seeds": seed_sets[si],
            "success": rec["success"],
            "error": rec.get("error"),
            "elapsed_seconds": rec.get("elapsed_seconds"),
            "candidate_count": rec.get("candidate_count"),
            "pareto_frontier_size": rec.get("pareto_frontier_size"),
            "best": {k: best.get(k) for k in OBJECTIVE_KEYS + ["asf_distance"]},
            "pool_objectives": pool_objectives,
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
