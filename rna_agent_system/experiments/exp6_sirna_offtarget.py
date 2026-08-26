#!/usr/bin/env python3
"""Experiment 6 (paper §2.2, Fig. 2f): siRNA off-target scanning — predicted
off-target hits per task on the RNADesign-210 siRNA sub-benchmark.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Hypothesis: the platform's siRNA golden path — ``sirna_design`` as
  designed (sliding-window / Evitar generation → GC + duplex-MFE +
  self-structure evaluation → rank-based scoring → ranking; off-target
  evaluation via BLAST/bowtie2 against the species reference transcriptome
  where the task input enables it) — delivers siRNA candidates with zero
  predicted transcriptome off-target hits for the large majority of the 22
  tasks in RNADesign-210 (``04_sirna_design``).
* Zero-intervention rule (user directive, 2026-08-25): the platform is
  measured as-is — task inputs verbatim, no threshold presets, no parameter
  sweeps, no retries beyond the SpecialistAgent's own hard-failure policy.
  The off-target-scan flags come from the task inputs themselves (19 of 22
  inputs disable the scan; 3 enable it: 003 BLAST, 013 bowtie2 identity-70,
  021 bowtie2 with ``species=sars_cov_2``). No input is modified.
* Primary metric: per-task predicted off-target hit count of the delivered
  (best-ranked) candidate — the platform's own metric of record
  (``off_target_count`` from the candidate metrics bundle; 0 = no predicted
  off-target). Historical reference: the Exp-1 lane observed 21/22 at zero
  (task 013 best candidate = 3 hits); this run re-derives the number from
  scratch.
* Secondary (descriptive, analysis-side): per-candidate off-target profiles
  of the full ranked list, whether the transcriptome scan actually executed
  per task (counted from the audited trace's ``*_blast_off_target`` /
  ``*_bowtie2_off_target`` tool calls — scan-skipped tasks are distinguished
  from scanned-and-zero tasks), specificity score, per-category counts.
* Arms: single arm (the golden path above). No null arm — zero predicted
  off-targets is the point estimate of interest, and the input matrix
  itself defines which tasks scan.
* Gate: pilot = tasks 001/003/013/016/021 (n = 5; covers generic mode,
  BLAST scan, bowtie2 scan, antiviral Evitar mode, and the sars_cov_2
  species edge) must produce 5/5 complete records (workflow success AND a
  measured best-candidate off-target count) before the full matrix. The
  full-run counts are reported as measured, never adjusted.
* CapGate policy: ``RNADA_CAPGATE=advisory`` — the documented regression
  convention (run_pa_test.py, exp1–exp5): the workflow's deterministic
  tools are not gated.
* Budget: one run per task; ``--resume`` skips tasks with a successful
  record on disk.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp6_sirna_offtarget.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp6_sirna_offtarget.py --run
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp6_sirna_offtarget.py --summary

Outputs under ``experiments/results/exp6_sirna_offtarget/``:
    pilot.jsonl, records.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import os
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
    / "tasks" / "04_sirna_design"
)
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp6_sirna_offtarget"

PILOT_TASK_IDS = [
    "04_sirna_design_001_basic",
    "04_sirna_design_003_with_offtarget",
    "04_sirna_design_013_blast_identity_70",
    "04_sirna_design_016_antiviral_existing_predsi",
    "04_sirna_design_021_species_sars_cov_2",
]

SCAN_TOOL_NAMES = {
    "run_blastn_similarity_search",
    "run_bowtie2_short_alignment",
}


# ----------------------------------------------------------------- task load

def load_tasks(only: list[str] | None = None) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for p in sorted(TASKS_DIR.glob("04_*.json")):
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

def candidate_row(c: dict[str, Any]) -> dict[str, Any]:
    metrics = c.get("metrics") or {}
    return {
        "rank": c.get("rank"),
        "id": c.get("id"),
        "source": c.get("source"),
        "sequence": c.get("sequence"),
        "off_target_count": metrics.get("off_target_count"),
        "specificity_score": metrics.get("specificity_score"),
        "gc_content": metrics.get("gc_content"),
        "duplex_mfe": metrics.get("duplex_mfe"),
    }


def scan_evidence(trace: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Count transcriptome-scan tool calls in the audited trace.

    Distinguishes scanned tasks (>=1 successful off-target tool call) from
    scan-skipped tasks (the input disabled the scan, or no transcriptome
    reference resolved for the species).
    """
    n_calls = n_ok = 0
    tools: set[str] = set()
    for t in trace or []:
        name = t.get("tool_name") or ""
        if name in SCAN_TOOL_NAMES:
            n_calls += 1
            tools.add(name)
            if t.get("success"):
                n_ok += 1
    return {
        "scan_tool_calls": n_calls,
        "scan_tool_successes": n_ok,
        "scan_tools": sorted(tools),
        "scan_executed": n_ok > 0,
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
    inp = task["input"]
    record: dict[str, Any] = {
        "task_id": task["task_id"],
        "workflow": task["workflow"],
        "category": task.get("category"),
        "description": task.get("description"),
        "mode": inp.get("mode"),
        "species": inp.get("species"),
        "off_target_scan_requested": bool(inp.get("off_target_scan", False)),
        "alignment_tool": inp.get("alignment_tool"),
        "requested_candidate_count": inp.get("candidate_count"),
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
    record.update(scan_evidence(results.get("trace")))

    rows = [candidate_row(c) for c in (results.get("candidates") or [])]
    record["candidate_count"] = len(rows)
    record["candidates"] = rows

    best = results.get("best_candidate")
    best_row = candidate_row(best) if best is not None else (rows[0] if rows else None)
    record["best"] = best_row

    if best_row is not None and best_row["off_target_count"] is not None:
        record["best_off_target_count"] = int(best_row["off_target_count"])
        record["max_off_target_count"] = max(
            (int(r["off_target_count"]) for r in rows
             if r["off_target_count"] is not None),
            default=None,
        )
        record["success"] = bool(results.get("success"))
    else:
        record["best_off_target_count"] = None
        record["max_off_target_count"] = None
        error = error or "no_candidates"

    if not record["success"] and error is None:
        error = "workflow_success_false" if not results.get("success") else "no_count"
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
        off = record.get("best_off_target_count")
        status = (
            f"OK off_target={off}" if record["success"]
            else f"FAIL({record['error']})"
        )
        n_ok += bool(record["success"])
        n_fail += not record["success"]
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s "
              f"(candidates={record.get('candidate_count')}, "
              f"scan={'yes' if record.get('scan_executed') else 'no'})",
              flush=True)
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
    zero = [r for r in ok if r.get("best_off_target_count") == 0]
    scanned = [r for r in ok if r.get("scan_executed")]
    scanned_zero = [r for r in scanned if r.get("best_off_target_count") == 0]
    skip_zero = [
        r for r in ok
        if not r.get("scan_executed") and r.get("best_off_target_count") == 0
    ]

    per_task = [
        {
            "task_id": r["task_id"],
            "category": r.get("category"),
            "mode": r.get("mode"),
            "species": r.get("species"),
            "off_target_scan_requested": r.get("off_target_scan_requested"),
            "scan_executed": r.get("scan_executed"),
            "scan_tools": r.get("scan_tools"),
            "best_off_target_count": r.get("best_off_target_count"),
            "max_off_target_count": r.get("max_off_target_count"),
            "candidate_count": r.get("candidate_count"),
            "elapsed_seconds": r.get("elapsed_seconds"),
        }
        for r in recs
    ]
    by_cat: dict[str, dict[str, int]] = {}
    for r in ok:
        cat = r.get("category") or "?"
        slot = by_cat.setdefault(cat, {"n": 0, "zero": 0})
        slot["n"] += 1
        slot["zero"] += r.get("best_off_target_count") == 0

    summary = {
        "experiment": "exp6_sirna_offtarget",
        "panel": "fig2f_sirna_offtarget",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy_primary_arm": "advisory",
        "benchmark": "RNADesign-210 / 04_sirna_design (22 tasks)",
        "metric": "best-ranked candidate predicted off-target hits against the "
                  "species reference transcriptome (platform off_target_count; "
                  "homo_sapiens = GENCODE v46 all transcripts, 254,070)",
        "n_tasks": len(recs),
        "n_success": len(ok),
        "n_zero_offtarget": len(zero),
        "zero_rate": round(len(zero) / len(recs), 4) if recs else None,
        "n_scan_requested": sum(
            1 for r in ok if r.get("off_target_scan_requested")
        ),
        "n_scan_executed": len(scanned),
        "n_scan_executed_zero": len(scanned_zero),
        "n_scan_skipped_zero": len(skip_zero),
        "best_off_target_counts": sorted(
            r["best_off_target_count"] for r in ok
        ),
        "max_off_target_count_overall": max(
            (r["max_off_target_count"] for r in ok
             if r.get("max_off_target_count") is not None),
            default=None,
        ),
        "by_category": by_cat,
        "historical_reference": "Exp-1 lane 04_sirna_design observed 21/22 at "
                                "zero (task 013 best candidate = 3 hits); this "
                                "run re-derives the number from scratch",
        "nonzero_tasks": [
            {
                "task_id": r["task_id"],
                "best_off_target_count": r.get("best_off_target_count"),
                "max_off_target_count": r.get("max_off_target_count"),
                "scan_tools": r.get("scan_tools"),
            }
            for r in ok if r.get("best_off_target_count") != 0
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
    print(f"zero predicted off-targets: {len(zero)}/{len(recs)}")
    print(f"scanned (trace-verified): {len(scanned)} tasks "
          f"({len(scanned_zero)} at zero); scan-skipped zero: {len(skip_zero)}")
    print(f"best-candidate counts: {summary['best_off_target_counts']}")
    for cat, slot in sorted(by_cat.items()):
        print(f"  category {cat}: {slot['zero']}/{slot['n']} zero")
    print(f"summary -> {out}")
    return 0


# ----------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true",
                      help="run pilot tasks 001/003/013/016/021 (machinery gate)")
    mode.add_argument("--run", action="store_true",
                      help="run all 22 benchmark tasks")
    mode.add_argument("--summary", action="store_true",
                      help="write summary.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=2400)
    parser.add_argument("--capgate", default="advisory",
                        choices=["advisory", "enforce", "off"])
    args = parser.parse_args()

    if args.summary:
        return write_summary()
    if args.pilot:
        tasks = load_tasks(PILOT_TASK_IDS)
        return run_batch(tasks, output=RESULTS_DIR / "pilot.jsonl",
                         capgate=args.capgate, session_prefix="exp6p",
                         resume=args.resume, timeout=args.timeout)
    return run_batch(load_tasks(), output=RESULTS_DIR / "records.jsonl",
                     capgate=args.capgate, session_prefix="exp6",
                     resume=args.resume, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
