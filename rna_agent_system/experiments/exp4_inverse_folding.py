#!/usr/bin/env python3
"""Experiment 4 (paper §2.2, Fig. 2d): secondary-structure inverse folding —
per-benchmark structure-recovery distance on the RNADesign-210 sub-benchmark.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Hypothesis: the platform's secondary-structure golden path —
  ``rna_secondary_structure_design`` as designed (ViennaRNA RNAinverse
  × ``num_invocations`` → RNAfold fold-back validation + GC → scoring →
  ranking; every parameter at its benchmark-specified value, defaults
  elsewhere) — recovers the exact target secondary structure for the large
  majority of the 25 inverse-folding benchmarks in RNADesign-210
  (``06_rna_secondary_structure``; lengths 9–54 nt, temperatures 4–70 °C,
  start-sequence constraints, RNAinverse function modes m/p/mp).
* Zero-intervention rule (user directive, 2026-08-25): the platform is
  measured as-is — no threshold presets, no objective tuning, no parameter
  sweeps, no retries beyond the SpecialistAgent's own hard-failure policy.
  Task inputs are fed verbatim from the benchmark files.
* Primary metric: per-benchmark structure distance of the delivered
  (best-ranked) candidate — the platform's own metric of record:
  position-wise dot-bracket Hamming distance between the ViennaRNA re-fold
  of the designed sequence and the target structure. Exact recovery =
  distance 0. Historical reference: the pre-reset run and the Exp-1 lane
  both observed 22/25; this run re-derives the number from scratch.
* Secondary (descriptive, analysis-side): base-pair distance
  (symmetric-difference pair count between re-folded and target pair sets),
  per-candidate distance profile of the full ranked list, whether any
  candidate in the set is exact (generation vs delivery), MFE and GC of the
  delivered candidate, per-category (basic/edge/full) exact counts.
* Arms: single arm (the golden path above). No null arm — the target
  structure itself defines perfection (distance 0).
* Gate: pilot = tasks 001–005 (n = 5) must produce 5/5 complete records
  (workflow success AND a measured best-candidate distance) before the full
  matrix. The full-run exact count is reported as measured, never adjusted.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1/exp2): the workflow's deterministic
  ViennaRNA/GC tools are not gated.
* Budget: one run per task; ``--resume`` skips tasks with a successful
  record on disk.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp4_inverse_folding.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp4_inverse_folding.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp4_inverse_folding.py --summary

Outputs under ``experiments/results/exp4_inverse_folding/``:
    pilot.jsonl, records.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TASKS_DIR = (
    PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform"
    / "tasks" / "06_rna_secondary_structure"
)
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp4_inverse_folding"

PILOT_TASK_IDS = [
    "06_rna_secondary_structure_001_basic_hairpin",
    "06_rna_secondary_structure_002_complex_structure",
    "06_rna_secondary_structure_003_ires_mimic",
    "06_rna_secondary_structure_004_bulge",
    "06_rna_secondary_structure_005_internal_loop",
]


# ------------------------------------------------------------------ structure

def dotbracket_pairs(structure: str) -> set[tuple[int, int]]:
    """Opening/closing pair set of a dot-bracket string (pseudoknot-free)."""
    stack: list[int] = []
    pairs: set[tuple[int, int]] = set()
    for i, ch in enumerate(structure):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if not stack:
                return pairs  # unbalanced; caller treats via length check
            j = stack.pop()
            pairs.add((j, i))
    return pairs


def base_pair_distance(a: str, b: str) -> int | None:
    """Base-pair distance |P(a) Δ P(b)| (None if lengths differ).

    Each pair present in only one structure counts once — the standard
    ViennaRNA structure-distance definition; no halving (pair-set sizes
    may differ when one structure extends a stem).
    """
    if len(a) != len(b) or not a or not b:
        return None
    return len(dotbracket_pairs(a) ^ dotbracket_pairs(b))


# ----------------------------------------------------------------- task load

def load_tasks(only: list[str] | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for p in sorted(TASKS_DIR.glob("06_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if only is None or d["task_id"] in only:
            tasks.append(d)
    if only is not None:
        missing = set(only) - {t["task_id"] for t in tasks}
        if missing:
            raise SystemExit(f"unknown pilot tasks: {sorted(missing)}")
    return tasks


# ------------------------------------------------------------------- CLI run

def find_results_file(session_dir: Path) -> Path | None:
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def run_cli(
    task: dict[str, Any],
    *,
    timeout: int,
    capgate: str,
    session_prefix: str,
) -> dict[str, Any]:
    task_id = task["task_id"]
    session_id = f"{session_prefix}_{task_id}"
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    params_file = session_dir / "params.json"
    params_file.write_text(
        json.dumps(task["input"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["RNADA_CAPGATE"] = capgate

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow", task["workflow"],
        "--params-file", str(params_file),
        "--session-id", session_id,
    ]
    log_path = session_dir / "driver.log"
    started = time.monotonic()
    exit_code, error = -1, None
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        try:
            proc = subprocess.run(
                cmd, cwd=PROJECT_ROOT, env=env,
                stdout=log_fp, stderr=subprocess.STDOUT,
                input="y\n", text=True, timeout=timeout,  # auto-answer pre-flight prompt
            )
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            error = "timeout"
    elapsed = time.monotonic() - started

    results: dict[str, Any] | None = None
    results_file = find_results_file(session_dir)
    if error is None and exit_code != 0:
        error = "cli_failure"
    if error is None and results_file is None:
        error = "no_results_file"
    if results_file is not None:
        try:
            results = json.loads(results_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            error = error or "parse_error"
    return build_record(
        task, results,
        session_id=session_id, exit_code=exit_code, elapsed=elapsed, error=error,
    )


# ------------------------------------------------------------------ records

def candidate_row(c: dict[str, Any], target: str) -> dict[str, Any]:
    metrics = c.get("metrics") or {}
    scores = c.get("scores") or {}
    folded = metrics.get("folded_structure")
    return {
        "rank": c.get("rank"),
        "id": c.get("id"),
        "source": c.get("source"),
        "sequence": c.get("sequence"),
        "structure_distance": metrics.get("structure_distance"),
        "structure_distance_ratio": scores.get("structure_distance_ratio"),
        "base_pair_distance": base_pair_distance(folded, target) if folded else None,
        "folded_structure": folded,
        "vienna_mfe": metrics.get("vienna_mfe"),
        "gc_content": metrics.get("gc_content"),
        "total_score": c.get("total_score"),
    }


def build_record(
    task: dict[str, Any],
    results: dict[str, Any] | None,
    *,
    session_id: str,
    exit_code: int,
    elapsed: float,
    error: str | None,
) -> dict[str, Any]:
    target = task["input"]["target_structure"]
    record: dict[str, Any] = {
        "task_id": task["task_id"],
        "workflow": task["workflow"],
        "category": task.get("category"),
        "description": task.get("description"),
        "target_structure": target,
        "target_length_nt": len(target),
        "temp_c": task["input"].get("temp_c"),
        "function_mode": task["input"].get("function_mode"),
        "has_start_sequence": task["input"].get("start_sequence") is not None,
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is None:
        return record

    record["workflow_success"] = bool(results.get("success"))
    record["retry_count"] = results.get("retry_count", 0)

    rows = [candidate_row(c, target) for c in (results.get("candidates") or [])]
    record["candidate_count"] = len(rows)
    record["candidates"] = rows

    best = results.get("best_candidate")
    if best is not None:
        best_row = candidate_row(best, target)
    else:
        best_row = rows[0] if rows else None
    record["best"] = best_row

    if best_row is not None:
        d = best_row["structure_distance"]
        record["best_structure_distance"] = d
        record["best_base_pair_distance"] = best_row["base_pair_distance"]
        record["exact_recovery"] = d == 0
        record["any_candidate_exact"] = any(
            r["structure_distance"] == 0 for r in rows
        )
        # a delivered distance requires the fold-back validation to have run
        record["success"] = bool(results.get("success")) and d is not None
    else:
        record["best_structure_distance"] = None
        record["best_base_pair_distance"] = None
        record["exact_recovery"] = False
        record["any_candidate_exact"] = False
        record["success"] = False
        error = error or "no_candidates"

    if not record["success"] and error is None:
        error = "workflow_success_false" if not results.get("success") else "no_distance"
    record["error"] = error
    return record


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def load_successful_task_ids(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("success"):
            done.add(rec["task_id"])
    return done


def run_batch(
    tasks: list[dict[str, Any]],
    *,
    output: Path,
    capgate: str,
    session_prefix: str,
    resume: bool,
    timeout: int,
) -> int:
    if resume:
        done = load_successful_task_ids(output)
        tasks = [t for t in tasks if t["task_id"] not in done]
    n_ok = n_fail = 0
    total = len(tasks)
    batch_start = time.monotonic()
    for i, task in enumerate(tasks, start=1):
        print(f"[{i}/{total}] {task['task_id']} ...", flush=True)
        record = run_cli(
            task, timeout=timeout, capgate=capgate, session_prefix=session_prefix
        )
        append_record(output, record)
        dist = record.get("best_structure_distance")
        status = (
            f"OK dist={dist}" if record["success"]
            else f"FAIL({record['error']})"
        )
        n_ok += bool(record["success"])
        n_fail += not record["success"]
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s "
              f"(candidates={record.get('candidate_count')})", flush=True)
    wall = time.monotonic() - batch_start
    print(f"\nDone: {n_ok} succeeded, {n_fail} failed, {total} total, "
          f"wall {wall / 60:.1f} min")
    print(f"Records -> {output}")
    return 0 if n_fail == 0 else 1


# -------------------------------------------------------------------- summary

def latest_records(path: Path) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return by_id
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        by_id[rec["task_id"]] = rec  # later lines win
    return by_id


def write_summary() -> int:
    records = latest_records(RESULTS_DIR / "records.jsonl")
    if not records:  # pilot-only state
        records = latest_records(RESULTS_DIR / "pilot.jsonl")
    recs = sorted(records.values(), key=lambda r: r["task_id"])

    ok = [r for r in recs if r.get("success")]
    exact = [r for r in ok if r.get("exact_recovery")]
    any_exact = [r for r in ok if r.get("any_candidate_exact")]
    dists = [r["best_structure_distance"] for r in ok
             if r.get("best_structure_distance") is not None]
    bp = [r["best_base_pair_distance"] for r in ok
          if r.get("best_base_pair_distance") is not None]

    per_task = [
        {
            "task_id": r["task_id"],
            "category": r.get("category"),
            "target_length_nt": r.get("target_length_nt"),
            "temp_c": r.get("temp_c"),
            "function_mode": r.get("function_mode"),
            "has_start_sequence": r.get("has_start_sequence"),
            "structure_distance": r.get("best_structure_distance"),
            "base_pair_distance": r.get("best_base_pair_distance"),
            "exact": bool(r.get("exact_recovery")),
            "any_candidate_exact": bool(r.get("any_candidate_exact")),
            "candidate_count": r.get("candidate_count"),
            "elapsed_seconds": r.get("elapsed_seconds"),
        }
        for r in recs
    ]
    by_cat: dict[str, dict[str, int]] = {}
    for r in ok:
        cat = r.get("category") or "?"
        slot = by_cat.setdefault(cat, {"n": 0, "exact": 0})
        slot["n"] += 1
        slot["exact"] += bool(r.get("exact_recovery"))

    nonzero = [d for d in dists if d > 0]
    summary = {
        "experiment": "exp4_inverse_folding",
        "panel": "fig2d_inverse_folding",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy_primary_arm": "advisory",
        "benchmark": "RNADesign-210 / 06_rna_secondary_structure (25 tasks)",
        "metric": "best-ranked candidate dot-bracket Hamming distance to target "
                  "(platform structure_distance; 0 = exact recovery)",
        "n_tasks": len(recs),
        "n_success": len(ok),
        "n_exact": len(exact),
        "exact_rate": round(len(exact) / len(recs), 4) if recs else None,
        "n_any_candidate_exact": len(any_exact),
        "distances": sorted(dists),
        "distance_median_nonzero": statistics.median(nonzero) if nonzero else None,
        "distance_max": max(dists) if dists else None,
        "base_pair_distance_sum_nonzero": sum(
            d for d in bp if d > 0
        ) if bp else None,
        "by_category": by_cat,
        "historical_reference_exact": "22/25 (pre-reset run; Exp-1 lane "
                                      "06_rna_secondary_structure re-observed 22/25)",
        "non_exact_tasks": [
            {
                "task_id": r["task_id"],
                "structure_distance": r.get("best_structure_distance"),
                "base_pair_distance": r.get("best_base_pair_distance"),
                "any_candidate_exact": r.get("any_candidate_exact"),
            }
            for r in ok if not r.get("exact_recovery")
        ],
        "failures": [
            {"task_id": r["task_id"], "error": r.get("error")}
            for r in recs if not r.get("success")
        ],
        "per_task": per_task,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "summary.json"
    out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"exact recovery: {len(exact)}/{len(recs)} "
          f"(any-candidate exact: {len(any_exact)}/{len(recs)})")
    print(f"distances: {sorted(dists)}")
    for cat, slot in sorted(by_cat.items()):
        print(f"  category {cat}: {slot['exact']}/{slot['n']} exact")
    print(f"summary -> {out}")
    return 0


# ----------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true",
                      help="run pilot tasks 001-005 (machinery gate)")
    mode.add_argument("--run", action="store_true",
                      help="run all 25 benchmark tasks")
    mode.add_argument("--summary", action="store_true",
                      help="write summary.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--capgate", default="advisory",
                        choices=["advisory", "enforce", "off"])
    args = parser.parse_args()

    if args.summary:
        return write_summary()
    if args.pilot:
        tasks = load_tasks(PILOT_TASK_IDS)
        return run_batch(tasks, output=RESULTS_DIR / "pilot.jsonl",
                         capgate=args.capgate, session_prefix="exp4p",
                         resume=args.resume, timeout=args.timeout)
    return run_batch(load_tasks(), output=RESULTS_DIR / "records.jsonl",
                     capgate=args.capgate, session_prefix="exp4",
                     resume=args.resume, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
