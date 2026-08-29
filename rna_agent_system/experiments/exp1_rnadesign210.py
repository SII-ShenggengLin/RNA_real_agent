#!/usr/bin/env python3
"""Experiment 1 (paper §2.2, Fig. 2a): RNADesign-210 full-platform benchmark.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2)
-----------------------------------------------------
* Hypothesis: the gated platform (post-2026-08-22 architecture) completes all
  210 RNADesign-210 tasks across the 11 workflows with successful workflow
  results and biologically structured outputs.
* Primary metric: task success = workflow ``success=True`` AND
  (≥1 candidate OR the task's rubric expects an empty result,
  ``min_candidates == 0``).
* Gate: 210/210. A single failure is triaged (driver/tool vs task defect)
  and either fixed-and-rerun or reported as a platform defect — never silently
  dropped.
* Pilot: n = 11 (one task per workflow, the ``001`` task of each directory).
  Pilot gate: ≥ 10/11 before the full matrix.
* CapGate policy: primary arm runs ``RNADA_CAPGATE=advisory`` — the
  documented regression convention (run_pa_form.py, e2e audits): enforce-mode
  gating intentionally blocks decertified oracles (IRESfinder, GerNA-Bind,
  RNASTOP-ranking; DECISIONS (l)) and would refuse whole workflows whose core
  deliverable is a decertified prediction. An ``--enforce-probe`` arm runs a
  4-task subset under ``enforce`` to document that boundary as data.
* Budget: single run per task (no sampling arms), ``--resume`` skips tasks
  that already have a successful record.

Lanes (run as separate processes against the GPU-pinned services):
    gpu_aptamer  08_rna_aptamer_design          (GPU 0 lane)
    gpu_tertiary 07_rna_tertiary_structure      (GPU 1 lane)
    cpu          the remaining nine workflows    (GPU 2 / CPU lane)

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp1_rnadesign210.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp1_rnadesign210.py --lane cpu
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp1_rnadesign210.py --summary
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp1_rnadesign210.py --enforce-probe

Outputs under ``experiments/results/exp1_rnadesign210/``:
    pilot.jsonl, lane_<name>.jsonl, enforce_probe.jsonl, summary.json
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

TASKS_ROOT = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp1_rnadesign210"

LANES: dict[str, list[str]] = {
    "gpu_aptamer": ["08_rna_aptamer_design"],
    "gpu_tertiary": ["07_rna_tertiary_structure"],
    "cpu": [
        "01_mrna_cds_design",
        "02_full_length_mrna_design",
        "03_mrna_sequence_scoring",
        "04_sirna_design",
        "05_sgrna_design",
        "06_rna_secondary_structure",
        "09_rna_small_molecule",
        "10_aso_target_screening",
        "11_ires_prediction",
    ],
}

GPU_LANE_DIRS = {"08_rna_aptamer_design", "07_rna_tertiary_structure"}

# 4-task enforce probe: the two workflows whose core oracle is decertified.
ENFORCE_PROBE_TASKS = [
    "11_ires_prediction_001_basic",
    "11_ires_prediction_007_mode2_default_window",
    "09_rna_small_molecule_001_basic",
    "09_rna_small_molecule_002_multi_tool",
]


def discover_tasks(dirs: list[str] | None = None) -> list[Path]:
    paths = sorted(
        p for p in TASKS_ROOT.glob("*/*.json") if p.name != "dataset_manifest.json"
    )
    if dirs:
        paths = [p for p in paths if p.parent.name in dirs]
    return paths


def load_tasks(dirs: list[str] | None = None) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in discover_tasks(dirs)]


def load_successful_task_ids(output_path: Path) -> set[str]:
    done: set[str] = set()
    if not output_path.exists():
        return done
    for line in output_path.read_text(encoding="utf-8").splitlines():
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


def find_results_file(session_dir: Path) -> Path | None:
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def trim_candidate(c: dict[str, Any], *, keep_sequence: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "rank": c.get("rank"),
        "id": c.get("id"),
        "source": c.get("source"),
        "total_length": c.get("total_length"),
        "total_score": c.get("total_score"),
        "scores": c.get("scores") or {},
        "metrics": c.get("metrics") or {},
    }
    if keep_sequence:
        out["sequence"] = c.get("sequence")
    return out


def evaluate_rubric(task: dict[str, Any], results: dict[str, Any] | None) -> dict[str, Any]:
    """Cheap deterministic rubric checks against the workflow result."""
    rub = task.get("evaluation_rubric") or {}
    if not rub or results is None:
        return {}
    ev: dict[str, Any] = {}
    n = len(results.get("candidates") or [])
    if "min_candidates" in rub:
        ev["min_candidates"] = {"expected": rub["min_candidates"], "observed": n,
                                "pass": n >= rub["min_candidates"]}
    best = results.get("best_candidate") or {}
    scores = best.get("scores") or {}
    metrics = best.get("metrics") or {}
    if "cai_threshold" in rub:
        val = scores.get("cai_score") or metrics.get("cai_score") or scores.get("cai")
        ev["cai_threshold"] = {"expected_min": rub["cai_threshold"], "observed": val,
                               "pass": val is not None and val >= rub["cai_threshold"]}
    if "mfe_threshold" in rub:
        val = scores.get("mfe_kcal_per_mol") or metrics.get("mfe_kcal_per_mol")
        ev["mfe_threshold"] = {"expected_max": rub["mfe_threshold"], "observed": val,
                               "pass": val is not None and val <= rub["mfe_threshold"]}
    if "gc_range" in rub:
        seq = (best.get("sequence") or "").upper()
        val = (seq.count("G") + seq.count("C")) / len(seq) if seq else None
        lo, hi = rub["gc_range"]
        ev["gc_range"] = {"expected": [lo, hi], "observed": val,
                          "pass": val is not None and lo <= val <= hi}
    return ev


def build_record(
    task: dict[str, Any],
    results: dict[str, Any] | None,
    *,
    session_id: str,
    exit_code: int,
    elapsed: float,
    error: str | None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "task_id": task["task_id"],
        "workflow": task["workflow"],
        "category": task.get("category"),
        "description": task.get("description"),
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is None:
        return record

    rubric = task.get("evaluation_rubric") or {}
    expects_empty = rubric.get("min_candidates") == 0
    n_candidates = len(results.get("candidates") or [])
    record["candidate_count"] = n_candidates
    record["workflow_success"] = bool(results.get("success"))
    record["success"] = bool(results.get("success")) and (n_candidates > 0 or expects_empty)
    record["summary"] = results.get("summary")
    record["retry_count"] = results.get("retry_count", 0)
    record["ranking_note"] = results.get("asf_ranking_note") or results.get("ranking_note")

    best = results.get("best_candidate")
    record["best_candidate"] = trim_candidate(best, keep_sequence=True) if best else None

    trace = results.get("trace") or []
    record["n_trace_steps"] = len(trace)
    record["tools_used"] = sorted({t.get("tool_name", "") for t in trace if t.get("tool_name")})
    expected = task.get("expected_tool_chain") or []
    record["expected_tool_chain"] = expected
    record["tool_chain_match"] = (
        all(t in record["tools_used"] for t in expected) if expected else None
    )

    diagnosis = results.get("_diagnosis_history") or []
    record["quality_actions"] = [
        (d.get("quality_report") or {}).get("action") for d in diagnosis if isinstance(d, dict)
    ]
    record["rubric_eval"] = evaluate_rubric(task, results)

    if not record["success"] and error is None:
        error = "workflow_success_false" if not results.get("success") else "empty_candidates"
        record["error"] = error
    return record


def run_task_dict(
    task: dict[str, Any],
    *,
    timeout: int,
    capgate: str,
    session_prefix: str,
) -> dict[str, Any]:
    task_id: str = task["task_id"]
    session_id = f"{session_prefix}_{task_id}"
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    params_file = session_dir / "params.json"
    params_file.write_text(json.dumps(task["input"], ensure_ascii=False, indent=2), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["RNADA_CAPGATE"] = capgate

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow",
        task["workflow"],
        "--params-file",
        str(params_file),
        "--session-id",
        session_id,
    ]
    log_path = session_dir / "driver.log"
    started = time.monotonic()
    exit_code, error = -1, None
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        try:
            proc = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                # Auto-answer the CLI's interactive "是否继续? (y/n)" prompt
                # raised when a pre-flight check partially fails; a genuinely
                # dead service fails the run properly and --resume retries it.
                input="y\n",
                text=True,
                timeout=timeout,
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


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def run_batch(
    tasks: list[dict[str, Any]],
    *,
    output: Path,
    capgate: str,
    session_prefix: str,
    resume: bool,
    default_timeout: int,
) -> int:
    if resume:
        done = load_successful_task_ids(output)
        tasks = [t for t in tasks if t["task_id"] not in done]
    n_ok = n_fail = 0
    total = len(tasks)
    batch_start = time.monotonic()
    for i, task in enumerate(tasks, start=1):
        timeout = max(default_timeout, 3600) if task["workflow"] in {
            "rna_aptamer_design", "rna_tertiary_structure_design",
        } else default_timeout
        print(f"[{i}/{total}] {task['task_id']} (timeout={timeout}s) ...", flush=True)
        record = run_task_dict(task, timeout=timeout, capgate=capgate, session_prefix=session_prefix)
        append_record(output, record)
        status = "OK" if record["success"] else f"FAIL({record['error']})"
        n_ok += bool(record["success"])
        n_fail += not record["success"]
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s "
              f"(candidates={record.get('candidate_count')})", flush=True)
    wall = time.monotonic() - batch_start
    print(f"\nDone: {n_ok} succeeded, {n_fail} failed, {total} total, wall {wall/60:.1f} min")
    print(f"Records -> {output}")
    return 0 if n_fail == 0 else 1


# --------------------------------------------------------------------- summary

def latest_records(paths: list[Path]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_id[rec["task_id"]] = rec  # later files win; append-order = latest
    return by_id


def write_summary() -> int:
    lane_files = sorted(RESULTS_DIR.glob("lane_*.jsonl"))
    records = latest_records([RESULTS_DIR / "pilot.jsonl", *lane_files])
    by_wf: dict[str, list[dict[str, Any]]] = {}
    for rec in records.values():
        by_wf.setdefault(rec["workflow"], []).append(rec)

    wf_summary = {}
    for wf, recs in sorted(by_wf.items()):
        successes = [r for r in recs if r.get("success")]
        elapsed = [r["elapsed_seconds"] for r in recs]
        wf_summary[wf] = {
            "n_tasks": len(recs),
            "n_success": len(successes),
            "success_rate": round(len(successes) / len(recs), 4) if recs else None,
            "median_elapsed_s": round(statistics.median(elapsed), 1) if elapsed else None,
            "max_elapsed_s": round(max(elapsed), 1) if elapsed else None,
            "tool_chain_ground_truth": sorted(
                {t for r in recs for t in r.get("tools_used") or []}
            ),
            "failures": [
                {"task_id": r["task_id"], "error": r.get("error")}
                for r in recs if not r.get("success")
            ],
        }

    total = len(records)
    n_success = sum(1 for r in records.values() if r.get("success"))
    summary = {
        "experiment": "exp1_rnadesign210",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy_primary_arm": "advisory",
        "total_tasks": total,
        "n_success": n_success,
        "all_pass": total == 210 and n_success == 210,
        "per_workflow": wf_summary,
        "enforce_probe": summarize_probe(),
    }
    out = RESULTS_DIR / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_workflow"}, indent=2))
    for wf, s in wf_summary.items():
        print(f"  {wf}: {s['n_success']}/{s['n_tasks']} (median {s['median_elapsed_s']}s)")
    print(f"summary -> {out}")
    return 0


def summarize_probe() -> dict[str, Any] | None:
    probe_file = RESULTS_DIR / "enforce_probe.jsonl"
    if not probe_file.exists():
        return None
    recs = latest_records([probe_file])
    return {
        "policy": "enforce",
        "n_tasks": len(recs),
        "outcomes": {tid: {"success": r.get("success"), "error": r.get("error")}
                     for tid, r in recs.items()},
    }


# ------------------------------------------------------------------------ main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true",
                        help="run the 001 task of every workflow (n=11 pilot)")
    parser.add_argument("--lane", choices=sorted(LANES), default=None,
                        help="run one lane's workflows")
    parser.add_argument("--workflow", default=None,
                        help="run a single workflow directory (any lane)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--capgate", default="advisory", choices=["advisory", "enforce", "off"])
    parser.add_argument("--enforce-probe", action="store_true",
                        help="run the 4-task enforce-mode probe")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        return write_summary()

    if args.enforce_probe:
        tasks = [t for t in load_tasks() if t["task_id"] in ENFORCE_PROBE_TASKS]
        return run_batch(tasks, output=RESULTS_DIR / "enforce_probe.jsonl",
                         capgate="enforce", session_prefix="exp1_probe",
                         resume=args.resume, default_timeout=args.timeout)

    if args.pilot:
        tasks = []
        for d in sorted({p.parent.name for p in discover_tasks()}):
            first = sorted(p for p in (TASKS_ROOT / d).glob("*.json")
                           if p.name != "dataset_manifest.json")
            if first:
                tasks.append(json.loads(first[0].read_text(encoding="utf-8")))
        if args.limit:
            tasks = tasks[: args.limit]
        return run_batch(tasks, output=RESULTS_DIR / "pilot.jsonl",
                         capgate=args.capgate, session_prefix="exp1_pilot",
                         resume=args.resume, default_timeout=args.timeout)

    dirs = LANES.get(args.lane or "", [])
    if args.workflow:
        dirs = [args.workflow]
    if not dirs:
        parser.error("choose --pilot, --lane, --workflow, --enforce-probe or --summary")
    tasks = load_tasks(dirs)
    if args.limit:
        tasks = tasks[: args.limit]
    lane_name = args.lane or args.workflow
    return run_batch(tasks, output=RESULTS_DIR / f"lane_{lane_name}.jsonl",
                     capgate=args.capgate, session_prefix="exp1",
                     resume=args.resume, default_timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
