#!/usr/bin/env python3
"""Experiment 8 (paper §2.2, Fig. 2h): end-to-end runtime by workflow.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2; zero-intervention rule)
---------------------------------------------------------------------------
* Question: what is the wall-clock end-to-end runtime per target of each of
  the 11 platform workflows, measured on the frozen gated platform exactly
  as it ships?
* Instrument: one ``cli/form_chat.py`` subprocess per task — the user form
  entry the Exp-1 coverage run and the PA regressions both use. Task inputs
  verbatim from the benchmark JSONs; no thresholds, no parameter presets, no
  objective tuning. Microservices pre-warmed by
  ``experiments/exp1_bring_up_services.sh`` (GPU-pinned 0/1/2), so per-task
  time measures the delivered workflow (pre-flight check → generate →
  evaluate → score → rank → writeout → advisory quality review), not
  cold-start model loads — registered as the measurement boundary.
* CapGate policy: ``advisory`` — the documented regression convention
  (run_pa_form.py, Exp-1 primary arm): enforce-mode gating intentionally
  refuses workflows whose core oracle is decertified (DECISIONS (l)), and a
  refused run has no meaningful delivery time.
* Sample: (a) all 210 RNADesign-210 tasks (11 workflows, basic/edge/full);
  (b) PA_006–PA_036 — all 31 form regressions, each timed as one whole user
  session through its documented entry ``run_pa_test.py`` (multi-turn
  sessions time turn 1..N summed).
* Metric: ``elapsed_seconds`` = subprocess wall clock (start → exit).
  ECDF/box population: successful runs only; failures are triaged and
  reported in the summary, never silently dropped.
* Contamination control: lanes run strictly sequentially
  (gpu_aptamer → gpu_tertiary → cpu → pa-batch) so no cross-lane GPU/CPU
  contention inflates the timings; nothing else runs on GPUs 0/1/2.
* Timeout: 3600 s per suite task and per PA session (2.2× the Exp-1 observed
  maximum, 1604 s); a timeout is recorded as a failure, not a data point.
  AMENDMENT (2026-08-27, registered before the PA_028 re-run): the PA-arm
  budget was under-calibrated for multi-turn GenNav navigation sessions —
  PA_027 finished at 3593 s (7 s under the budget) and PA_028 (aptamer,
  navigation=true, 2 turns) was killed at 3600 s while still progressing
  normally (turn 1 delivered at ~3010 s; the orphaned turn 2 completed at
  ~5740 s total, after the driver's kill had leaked past the direct child).
  The PA-arm timeout is amended to 10800 s and the driver now kills the whole
  process group on timeout (no orphaned grandchildren). PA_028 is re-run once
  under the amended budget with a fresh session id (exp8_r2_pa028); the
  original censored record stays in pa_batch.jsonl (never deleted;
  latest-record-wins). Contamination check for the orphan overlap window
  (00:58–01:34, PA_029 concurrent with the orphaned turn 2): PA_029
  (rna_small_molecule, 42.63 s) matches its same-workflow siblings PA_010
  (42.15 s) / PA_021 (42.52 s) — no detectable contamination; PA_029 is not
  re-run.
* Pilot: 4 runs covering the driver mechanics on cheap CPU, slow CPU, GPU
  and PA arms (``03_..._001_basic``, ``01_..._001_basic``,
  ``08_..._001_basic``, PA_006). Pilot gate: 4/4 success with timings
  recorded. Pilot records are superseded by the full-matrix re-runs of the
  same ids (latest record wins, Exp-1 convention).
* Budget: single run per task/session (``--resume`` skips ids that already
  have a successful record).

Usage (from ``rna_agent_system/``; or all lanes sequentially via
``experiments/exp8_run_all.sh``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp8_runtime.py --pilot
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp8_runtime.py --lane cpu
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp8_runtime.py --pa-batch
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp8_runtime.py --summary

Outputs under ``experiments/results/exp8_runtime/``:
    pilot.jsonl, lane_<name>.jsonl, pa_batch.jsonl, summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import signal
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
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp8_runtime"
PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"

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

PILOT_TASKS = [
    "03_mrna_sequence_scoring_001_basic",
    "01_mrna_cds_design_001",
    "08_rna_aptamer_design_001_basic",
]
PILOT_PA = "006"

TIMEOUT_SUITE_S = 3600
TIMEOUT_PA_S = 10800  # amended 2026-08-27 (see docstring): multi-turn GenNav
                      # navigation sessions legitimately exceed 1 h (PA_028
                      # true time ~5740 s); 10800 s ≈ 1.9× that headroom.


def _run_timed(cmd: list[str], *, cwd: Path, env: dict[str, str],
               log_fp, timeout: int, stdin_text: str | None = None,
               ) -> tuple[int, str | None]:
    """Run a subprocess under a timeout that kills the whole process group.

    Killing only the direct child (subprocess.run's behaviour) leaks orphaned
    grandchildren — the PA_028 lesson registered in the docstring.
    """
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=log_fp, stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        text=True, errors="replace", start_new_session=True,
    )
    try:
        proc.communicate(input=stdin_text, timeout=timeout)
        return proc.returncode, None
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()
        return -1, "timeout"


# ------------------------------------------------------------------- suite arm

def discover_tasks(dirs: list[str] | None = None) -> list[Path]:
    paths = sorted(
        p for p in TASKS_ROOT.glob("*/*.json") if p.name != "dataset_manifest.json"
    )
    if dirs:
        paths = [p for p in paths if p.parent.name in dirs]
    return paths


def load_tasks(dirs: list[str] | None = None) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in discover_tasks(dirs)]


def find_results_file(session_dir: Path) -> Path | None:
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def run_suite_task(task: dict[str, Any], *, session_prefix: str) -> dict[str, Any]:
    task_id: str = task["task_id"]
    session_id = f"{session_prefix}_{task_id}"
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    params_file = session_dir / "params.json"
    params_file.write_text(json.dumps(task["input"], ensure_ascii=False, indent=2), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env["RNADA_CAPGATE"] = "advisory"

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
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        # Auto-answer the CLI's interactive "是否继续? (y/n)" prompt raised
        # when a pre-flight check partially fails; a genuinely dead service
        # fails the run properly and --resume retries it.
        exit_code, error = _run_timed(
            cmd, cwd=PROJECT_ROOT, env=env, log_fp=log_fp,
            timeout=TIMEOUT_SUITE_S, stdin_text="y\n",
        )
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

    record: dict[str, Any] = {
        "task_id": task_id,
        "workflow": task["workflow"],
        "category": task.get("category"),
        "source": "rnadesign210",
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is not None:
        rubric = task.get("evaluation_rubric") or {}
        expects_empty = rubric.get("min_candidates") == 0
        n_candidates = len(results.get("candidates") or [])
        record["candidate_count"] = n_candidates
        record["workflow_success"] = bool(results.get("success"))
        record["success"] = bool(results.get("success")) and (
            n_candidates > 0 or expects_empty
        )
        if not record["success"] and error is None:
            error = (
                "workflow_success_false" if not results.get("success")
                else "empty_candidates"
            )
            record["error"] = error
    return record


# ---------------------------------------------------------------------- PA arm

def run_pa(pa_id: str, *, workflow: str, n_turns: int, session_prefix: str) -> dict[str, Any]:
    session_id = f"{session_prefix}_pa{pa_id}"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    # RNADA_CAPGATE deliberately NOT set here: run_pa_form defaults its own
    # subprocesses to advisory (the documented regression convention).

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_pa_test.py"),
        pa_id,
        "--session-id",
        session_id,
    ]
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    log_path = session_dir / "driver.log"
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        exit_code, error = _run_timed(
            cmd, cwd=PROJECT_ROOT, env=env, log_fp=log_fp,
            timeout=TIMEOUT_PA_S,
        )
    elapsed = time.monotonic() - started

    return {
        "task_id": f"pa_{pa_id}",
        "pa_id": pa_id,
        "workflow": workflow,
        "n_turns": n_turns,
        "source": "pa_regression",
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error if error is not None else (
            None if exit_code == 0 else "pa_driver_failure"
        ),
        "success": error is None and exit_code == 0,
    }


# --------------------------------------------------------------------- batches

def load_successful_ids(output_path: Path) -> set[str]:
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


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def run_suite_batch(
    tasks: list[dict[str, Any]], *, output: Path, session_prefix: str, resume: bool,
) -> int:
    if resume:
        done = load_successful_ids(output)
        tasks = [t for t in tasks if t["task_id"] not in done]
    n_ok = n_fail = 0
    total = len(tasks)
    batch_start = time.monotonic()
    for i, task in enumerate(tasks, start=1):
        print(f"[{i}/{total}] {task['task_id']} ...", flush=True)
        record = run_suite_task(task, session_prefix=session_prefix)
        append_record(output, record)
        status = "OK" if record["success"] else f"FAIL({record['error']})"
        n_ok += bool(record["success"])
        n_fail += not record["success"]
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s", flush=True)
    wall = time.monotonic() - batch_start
    print(f"\nDone: {n_ok} succeeded, {n_fail} failed, {total} total, wall {wall/60:.1f} min")
    print(f"Records -> {output}")
    return 0 if n_fail == 0 else 1


def run_pa_batch(pa_ids: list[str], *, output: Path, session_prefix: str, resume: bool) -> int:
    registry = json.loads(PA_BENCHMARKS.read_text(encoding="utf-8"))
    if resume:
        done = load_successful_ids(output)
        pa_ids = [p for p in pa_ids if f"pa_{p}" not in done]
    n_ok = n_fail = 0
    total = len(pa_ids)
    batch_start = time.monotonic()
    for i, pa_id in enumerate(pa_ids, start=1):
        entry = registry[pa_id]
        print(f"[{i}/{total}] PA_{pa_id} ({entry['workflow']}, {len(entry['params_by_turn'])} turn(s)) ...",
              flush=True)
        record = run_pa(
            pa_id,
            workflow=entry["workflow"],
            n_turns=len(entry["params_by_turn"]),
            session_prefix=session_prefix,
        )
        append_record(output, record)
        status = "OK" if record["success"] else f"FAIL({record['error']})"
        n_ok += bool(record["success"])
        n_fail += not record["success"]
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s", flush=True)
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


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    if not s:
        return float("nan")
    idx = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
    return s[idx]


def write_summary() -> int:
    lane_files = sorted(RESULTS_DIR.glob("lane_*.jsonl"))
    records = latest_records(
        [RESULTS_DIR / "pilot.jsonl", *lane_files, RESULTS_DIR / "pa_batch.jsonl"]
    )
    by_wf: dict[str, list[dict[str, Any]]] = {}
    for rec in records.values():
        by_wf.setdefault(rec["workflow"], []).append(rec)

    wf_summary = {}
    for wf, recs in sorted(by_wf.items()):
        ok = [r for r in recs if r.get("success")]
        elapsed = [r["elapsed_seconds"] for r in ok]
        wf_summary[wf] = {
            "n_runs": len(recs),
            "n_success": len(ok),
            "n_rnadesign210": sum(1 for r in recs if r.get("source") == "rnadesign210"),
            "n_pa_regression": sum(1 for r in recs if r.get("source") == "pa_regression"),
            "failures": [
                {"task_id": r["task_id"], "error": r.get("error")}
                for r in recs if not r.get("success")
            ],
            "elapsed_s": {
                "min": round(min(elapsed), 1) if elapsed else None,
                "median": round(statistics.median(elapsed), 1) if elapsed else None,
                "mean": round(statistics.fmean(elapsed), 1) if elapsed else None,
                "p90": round(pct(elapsed, 0.90), 1) if elapsed else None,
                "max": round(max(elapsed), 1) if elapsed else None,
            },
        }

    all_ok = [r for r in records.values() if r.get("success")]
    all_elapsed = [r["elapsed_seconds"] for r in all_ok]
    summary = {
        "experiment": "exp8_runtime",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "capgate_policy": "advisory (regression convention; see docstring)",
        "services": "pre-warmed via experiments/exp1_bring_up_services.sh (GPU-pinned 0/1/2)",
        "measurement": "subprocess wall clock per task/session; successful runs only",
        "total_runs": len(records),
        "n_success": len(all_ok),
        "all_pass": len(records) == 241 and len(all_ok) == 241,
        "grand_elapsed_s": {
            "median": round(statistics.median(all_elapsed), 1),
            "mean": round(statistics.fmean(all_elapsed), 1),
            "min": round(min(all_elapsed), 1),
            "max": round(max(all_elapsed), 1),
        },
        "per_workflow": wf_summary,
    }
    out = RESULTS_DIR / "summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_workflow"}, indent=2))
    for wf, s in wf_summary.items():
        e = s["elapsed_s"]
        print(f"  {wf}: {s['n_success']}/{s['n_runs']} "
              f"(median {e['median']}s, max {e['max']}s)")
    print(f"summary -> {out}")
    return 0


# ------------------------------------------------------------------------ main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pilot", action="store_true",
                        help="run the 4-run pilot (2 CPU suite tasks, 1 GPU suite task, PA_006)")
    parser.add_argument("--lane", choices=sorted(LANES), default=None,
                        help="run one lane's workflows (suite arm)")
    parser.add_argument("--workflow", default=None,
                        help="run a single workflow directory (any lane)")
    parser.add_argument("--pa-batch", action="store_true",
                        help="run the PA_006–PA_036 regression batch (PA arm)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--session-prefix", default="exp8",
                        help="session-id prefix (fresh prefix = fresh sessions, "
                             "e.g. exp8_r2 for the disclosed PA_028 re-run)")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        return write_summary()

    if args.pilot:
        tasks = [t for t in load_tasks() if t["task_id"] in PILOT_TASKS]
        rc = run_suite_batch(tasks, output=RESULTS_DIR / "pilot.jsonl",
                             session_prefix="exp8_pilot", resume=args.resume)
        rc += run_pa_batch([PILOT_PA], output=RESULTS_DIR / "pilot.jsonl",
                           session_prefix="exp8_pilot", resume=args.resume)
        return 0 if rc == 0 else 1

    if args.pa_batch:
        pa_ids = sorted(json.loads(PA_BENCHMARKS.read_text(encoding="utf-8")))
        if args.limit:
            pa_ids = pa_ids[: args.limit]
        return run_pa_batch(pa_ids, output=RESULTS_DIR / "pa_batch.jsonl",
                            session_prefix=args.session_prefix, resume=args.resume)

    dirs = LANES.get(args.lane or "", [])
    if args.workflow:
        dirs = [args.workflow]
    if not dirs:
        parser.error("choose --pilot, --lane, --workflow, --pa-batch or --summary")
    tasks = load_tasks(dirs)
    if args.limit:
        tasks = tasks[: args.limit]
    lane_name = args.lane or args.workflow
    return run_suite_batch(tasks, output=RESULTS_DIR / f"lane_{lane_name}.jsonl",
                           session_prefix=args.session_prefix, resume=args.resume)


if __name__ == "__main__":
    sys.exit(main())
