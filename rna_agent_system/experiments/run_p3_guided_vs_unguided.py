#!/usr/bin/env python3
"""Pilot P3 (2026-08-03): diagnosis-guided vs UNGUIDED regeneration at matched budget.

MOTIVATION (isolating the diagnosis ingredient)
-----------------------------------------------
P0 (`run_budget_matched_control.py`) matched the TOTAL budget: bmc_x1 vs
serial_ext16 gave Cliff's delta = 0.278 (NS) — under the pre-registered 0.3
threshold, so the budget confound explains most of the Fig-4 Type-II effect.
But serial_ext16 differs from bmc_x1 in TWO ways: (a) no diagnosis between
batches, and (b) different mechanics (one-pass 16 samples, same seeds vs
two-pass 8+8 with the second batch regenerated under changed parameters).
P3 isolates ingredient (a): the unguided arm below reproduces bmc_x1's
two-pass mechanics EXACTLY — same initial batch (8, same seeds), then a
forced second batch of 8 with seeds+1 (the "seed_change" regeneration path)
— but with the diagnosis REPLACED by a fixed, content-free resampling
instruction. Any quality gap between bmc_x1 (guided) and this arm is then
attributable to the diagnosis content itself (hotspot expansion / length
adjustment / when-to-regenerate), not to the sampling budget or mechanics.

ARMS (per cell: 4 pilot targets x 3 seed sets = 12 cells)
---------------------------------------------------------
  - guided        : existing bmc_x1 records in fig4_type2_shard_{a,b}.jsonl
                    (same seeds, same n=8+batch, diagnosis-driven 2nd batch).
  - unguided_2pass: THIS driver, condition="unguided_2pass". In-process
                    RnaAptamerDesignWorkflow: run_initial -> bmc_prepare ->
                    coordinator instance patched (diagnose -> one fixed
                    violation issue; broadcast_feedback -> fixed Aptamer
                    seed_change+1) -> bmc_run_round(1) -> bmc_finalize.
                    No agent_core changes; no LLM calls (zero QualityAgent).

GO/NO-GO (pre-registered, pilot-scale)
--------------------------------------
  Primary: egarps_component best-of-pool per (target, seed_idx) cell,
  guided vs unguided_2pass across the 12 cells.
    GO   : Cliff's delta >= 0.3 in favour of guided -> the diagnosis content
           (not budget, not mechanics) carries measurable value; the
           "diagnosis-guided adaptive search" narrative is supported.
    NO-GO: delta < 0.3 -> diagnosis content unsupported at pilot scale;
           BMC's defensible value reduces to adaptive budget allocation
           (converged round-0 stops save budget) + resampling mechanics;
           manuscript presents it as such.
  Secondary (reported either way): budget spent per arm (guided may stop at
  pool 8 when round-0 converges; unguided always spends 16).

CAVEAT (P2): the egarps objective itself failed calibration (rho=0.40,
AUROC=0.356). P3's verdict is therefore about the mechanism UNDER THE
CURRENT OBJECTIVE and must be revisited if the objective is recalibrated.
This caveat is part of the pre-registration.

Records keep the fig4 schema (plus `condition`) for reuse of
analysis/summarize_fig4.py-style tooling. Same-job dedupe key:
(target_id, condition, seed_idx), latest wins.

Usage (from `rna_agent_system/`):
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_p3_guided_vs_unguided.py \
        [--targets BSA,Lysozyme,Thrombin,VEGF] [--resume]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_platform_quality_benchmark import PROJECT_ROOT  # noqa: E402
from run_bmc_type2_ablation import (  # noqa: E402
    OBJECTIVE_KEYS,
    SEED_SETS,
    TARGETS_DIR,
    find_structure,
)

from agent_core.capabilities.base import build_default_capability_registry  # noqa: E402
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry  # noqa: E402
from agent_core.workflows.coordinator import (  # noqa: E402
    Issue,
    ModuleFeedback,
    ParamAdjustment,
)
from agent_core.workflows.rna_aptamer_design import (  # noqa: E402
    RnaAptamerDesignInput,
    RnaAptamerDesignWorkflow,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "p3_guided_vs_unguided.jsonl"
PILOT_TARGETS = ["BSA", "Lysozyme", "Thrombin", "VEGF"]
CONDITION = "unguided_2pass"

# Fixed, content-free replacements for the diagnosis stage. The forced issue
# guarantees the round always regenerates (budget = 16 for every cell); the
# fixed feedback is exactly bmc_x1's "seed_change" mechanical path with no
# diagnosis-derived content (no hotspot expansion, no length adjustment).
FORCED_ISSUE = Issue(
    issue_type="p3_forced_regeneration",
    value=1.0,
    target=0.0,
    affected_modules=("Aptamer",),
    evidence="P3 unguided control: regeneration forced without diagnosis",
    violation=1.0,
)
UNGUIDED_FEEDBACK = {
    "Aptamer": ModuleFeedback(
        priority="low",
        adjustments=[
            ParamAdjustment(
                param="seed_change",
                delta=1,
                reason="P3 unguided control: random resampling (seeds+1), no diagnosis",
            )
        ],
    )
}


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


def run_unguided_cell(target_id: str, pdb_id: str, struct: Path, chain_id: str,
                      seed_idx: int) -> dict:
    """One unguided_2pass run: bmc_x1 mechanics with the diagnosis patched out."""
    t0 = time.perf_counter()
    rec: dict = {
        "target_id": target_id,
        "pdb_id": pdb_id,
        "condition": CONDITION,
        "bmc_max_rounds": 1,
        "seed_idx": seed_idx,
        "seeds": SEED_SETS[seed_idx],
        "success": False,
        "error": None,
    }
    try:
        executor = ToolExecutor(build_default_tool_registry(include_demo=False))
        registry = build_default_capability_registry(executor)
        wf = RnaAptamerDesignWorkflow(registry)
        wf.auto_start_services = True

        inp = RnaAptamerDesignInput(
            protein_structure_path=str(struct.relative_to(PROJECT_ROOT)),
            chain_id=chain_id,
            aptamer_length=30,
            n_odesign_samples=8,
            odesign_seeds=SEED_SETS[seed_idx],
            bmc_max_rounds=1,
            bmc_improvement_threshold=0.05,
        )

        result = wf.run_initial(inp)
        if not result.success or not result.all_candidates:
            rec["error"] = f"run_initial failed: {result.errors or result.summary}"
            return rec

        bmc_state = wf.bmc_prepare(result)

        # Patch THIS coordinator instance only: force regeneration and replace
        # the diagnosis-derived feedback with the fixed unguided one.
        coordinator = bmc_state["coordinator"]
        coordinator.diagnose = lambda *a, **k: [FORCED_ISSUE]
        coordinator.broadcast_feedback = lambda *a, **k: dict(UNGUIDED_FEEDBACK)

        result, bmc_state, _stop, stop_reason = wf.bmc_run_round(1, result, bmc_state)
        result = wf.bmc_finalize(result)

        best = (result.best_candidate.scores if result.best_candidate else {}) or {}
        rec.update({
            "success": result.success and bool(result.all_candidates),
            "error": None if result.success else (result.errors or ["unknown"]),
            "stop_reason": stop_reason,
            "candidate_count": len(result.all_candidates),
            "pareto_frontier_size": getattr(result, "pareto_frontier_size", None),
            "bmc_rounds_executed": len(getattr(wf, "_bmc_trace", []) or []),
            "best": {k: best.get(k) for k in OBJECTIVE_KEYS + ["asf_distance"]},
            "pool_objectives": [
                {k: (c.scores or {}).get(k) for k in OBJECTIVE_KEYS}
                for c in result.all_candidates
            ],
            "bmc_trace": [t.to_dict() for t in (getattr(wf, "_bmc_trace", []) or [])],
        })
        # Budget guarantee check: the forced round must have doubled the pool.
        if rec["success"] and rec["candidate_count"] != 16:
            rec["success"] = False
            rec["error"] = f"budget_mismatch pool={rec['candidate_count']} != 16"
    except Exception as exc:  # noqa: BLE001 - record and continue to next cell
        rec["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        rec["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    return rec


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--targets", default=",".join(PILOT_TARGETS), help="comma-separated target ids")
    parser.add_argument("--seed-sets", type=int, default=3, help="number of seed sets (max 3)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true", help="skip cells already recorded as success")
    args = parser.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    seed_sets = SEED_SETS[: args.seed_sets]
    done = load_done_keys(args.output) if args.resume else set()

    target_files = []
    for tid in targets:
        tf = TARGETS_DIR / f"{tid}.json"
        if not tf.exists():
            print(f"[skip] {tid}: no target file {tf}")
            continue
        target_files.append(tf)

    jobs = [(tf, si) for tf in target_files for si in range(len(seed_sets))]
    args.output.parent.mkdir(parents=True, exist_ok=True)

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
        print(f"[{i}/{len(jobs)}] {target_id} {CONDITION} seeds={SEED_SETS[si]} ...", flush=True)
        rec = run_unguided_cell(
            target_id, meta["pdb_id"], struct, meta.get("pdb_chain") or "A", si,
        )
        rec["timestamp"] = datetime.now().isoformat(timespec="seconds")
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        if rec["success"]:
            n_ok += 1
        else:
            n_fail += 1
        print(f"      -> {'OK' if rec['success'] else 'FAIL(' + str(rec.get('error')) + ')'} "
              f"pool={rec.get('candidate_count')} in {rec.get('elapsed_seconds', 0):.0f}s", flush=True)

    print(f"\nDone: {n_ok} ok, {n_fail} failed, {n_skip} resumed-skip -> {args.output}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
