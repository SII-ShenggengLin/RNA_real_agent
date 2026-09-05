#!/usr/bin/env python3
"""Experiment 24 — parallel campaign orchestrator (user-directed amendment,
2026-09-01; registered before the parallel re-launch).

Replaces the strictly sequential exp24_run_all.sh after the user judged the
~17.5 h sequential wall too slow and directed maximum practical parallelism
with CPU/GPU utilization monitored and driven up.

Design (pre-registered in this docstring):
* SIX-plus parallel workflow-exclusive workers (one per workflow, eleven in
  the final plan) run concurrently. A workflow's suite tasks AND its PA
  sessions always belong to exactly one worker and execute sequentially
  inside it — no two sessions of the same workflow ever overlap in time.
  This is the condition the amended audit attribution relies on: unstamped
  gate/ranking events carry a payload workflow key (reason string / ranking
  task_type), and with same-workflow serialization the key maps to exactly
  one active session (hard-asserted by the analyzer; ambiguity fails the
  analysis rather than corrupting it).
* Worker plan (load-balanced from the second-reset campaign's per-workflow
  totals; the mRNA CDS and full-length workflows were verified disjoint in
  gate-event keys on the legacy frozen corpus, so every workflow gets its
  own worker — eleven workers in total):
    Wapt  08_rna_aptamer_design                    (~353 legacy min incl. PA)
    Wfl   02_full_length_mrna_design               (~154)
    Wsg   05_sgrna_design                          (~134)
    Wter  07_rna_tertiary_structure                (~123)
    Wcds  01_mrna_cds_design                       (~111)
    Wsi   04_sirna_design                          (~84)
    Wsec  06_rna_secondary_structure               (~37)
    Wires 11_ires_prediction                       (~36)
    Waso  10_aso_target_screening                  (~13)
    Wsm   09_rna_small_molecule                    (~5)
    Wsc   03_mrna_sequence_scoring                 (~1)
* Services stay exactly as shipped (exp1_bring_up_services.sh topology —
  one replica per service, GPU-pinned 0/1/2); parallelism is task-level
  only. Concurrent requests queue inside services; utilization rises,
  per-run wall times measure the delivered workflow under concurrent
  campaign load (disclosed; the Fig-2i reading states it).
* Retries: each worker re-runs its failed tasks/PA sessions for up to three
  attempt rounds; every attempt uses a fresh session-id prefix
  (exp24, exp24_r2, exp24_r3), so a failed attempt's audit events never
  merge into the successful session (failed-attempt sids are inventoried as
  analyzer exclusions). A task whose base session id already appears in the
  audit trail without a success record (the killed sequential-phase partial
  session) starts at the r2 prefix.
* Records: lane_<workflow-dir>.jsonl (one writer per file) and
  pa_batch_w<K>.jsonl per worker; the campaign driver's --summary globs
  both patterns (latest-record-wins).

RE-RUN AMENDMENT (2026-09-06, platform default change DECISIONS (aa), user-
directed): the campaign re-runs on the platform whose mRNA design flows now
default to GenNav-λ navigation (mrna_cds_design v2.0.0 tristate). Task inputs
are unchanged verbatim — the suite's design_tool="all" tasks and the PA
"all"-turns now exercise the default navigation flow, pinned-engine tasks
keep their registered protocols; every other workflow is untouched. The
static-default era's outputs are archived at
experiments/results/exp24_production_campaign_static/ (audit stats at
exp24_audit_gate_stats_static/). Session prefixes unchanged (exp24).

Usage:
    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/exp24_run_parallel.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

import exp24_production_campaign as camp  # noqa: E402

RESULTS_DIR = camp.RESULTS_DIR
AUDIT_TRAIL = PROJECT_ROOT / "workspace" / "audit" / "platform_audit.jsonl"

WORKER_DIRS: dict[str, list[str]] = {
    "Wapt": ["08_rna_aptamer_design"],
    "Wfl": ["02_full_length_mrna_design"],
    "Wsg": ["05_sgrna_design"],
    "Wter": ["07_rna_tertiary_structure"],
    "Wcds": ["01_mrna_cds_design"],
    "Wsi": ["04_sirna_design"],
    "Wsec": ["06_rna_secondary_structure"],
    "Wires": ["11_ires_prediction"],
    "Waso": ["10_aso_target_screening"],
    "Wsm": ["09_rna_small_molecule"],
    "Wsc": ["03_mrna_sequence_scoring"],
}

WORKFLOW_TO_DIR = {
    "rna_aptamer_design": "08_rna_aptamer_design",
    "full_length_mrna_design": "02_full_length_mrna_design",
    "ires_prediction": "11_ires_prediction",
    "sgrna_design": "05_sgrna_design",
    "rna_small_molecule_interaction": "09_rna_small_molecule",
    "rna_tertiary_structure_design": "07_rna_tertiary_structure",
    "aso_target_screening": "10_aso_target_screening",
    "mrna_cds_design": "01_mrna_cds_design",
    "sirna_design": "04_sirna_design",
    "rna_secondary_structure_design": "06_rna_secondary_structure",
    "mrna_sequence_scoring": "03_mrna_sequence_scoring",
}

MAX_ATTEMPTS = 3

_print_lock = threading.Lock()


def wlog(worker: str, msg: str) -> None:
    with _print_lock:
        print(f"[{worker}] {msg}", flush=True)


def trail_session_ids() -> set[str]:
    sids: set[str] = set()
    with open(AUDIT_TRAIL, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = (rec.get("payload") or {}).get("session_id")
            if sid:
                sids.add(sid)
    return sids


def all_successful_task_ids() -> set[str]:
    """Successful ids in the FORMAL campaign records only (lane + pa files).

    Pilot records are deliberately excluded: the four pilot ids are re-run
    under exp24_* session ids so the corpus derivation stays exactly as
    pre-registered (pilot sessions excluded; latest record supersedes pilot,
    the Exp-1 convention)."""
    done: set[str] = set()
    for p in [*sorted(RESULTS_DIR.glob("lane_*.jsonl")),
              *sorted(RESULTS_DIR.glob("pa_batch*.jsonl"))]:
        if p.exists():
            done |= camp.load_successful_ids(p)
    return done


def all_records_by_task() -> dict[str, list[dict]]:
    by_task: dict[str, list[dict]] = defaultdict(list)
    for p in [*sorted(RESULTS_DIR.glob("lane_*.jsonl")),
              *sorted(RESULTS_DIR.glob("pa_batch*.jsonl"))]:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_task[rec["task_id"]].append(rec)
    return by_task


def fresh_prefix(task_id: str, records_by_task: dict[str, list[dict]],
                 trail_sids: set[str], pa: bool = False) -> str:
    """Next unused session-id prefix for this task: exp24, exp24_r2, ...

    A sid is "used" if it appears in any record (successful or failed) or in
    the audit trail (dead partial session from a killed orchestrator) — every
    attempt therefore gets a fresh sid, so a failed attempt's audit events
    never merge into the successful session."""
    suffix = f"pa{task_id.removeprefix('pa_')}" if pa else task_id
    used = {rec["session_id"] for rec in records_by_task.get(task_id, [])}
    used |= {s for s in trail_sids if s.endswith(f"_{suffix}")}
    for n in range(1, 20):
        prefix = "exp24" if n == 1 else f"exp24_r{n}"
        if f"{prefix}_{suffix}" not in used:
            return prefix
    raise RuntimeError(f"ran out of session prefixes for {task_id}")


def run_workflow_tasks(worker: str, wf_dir: str, trail_sids: set[str]) -> None:
    lane_file = RESULTS_DIR / f"lane_{wf_dir}.jsonl"
    tasks = camp.load_tasks([wf_dir])
    for attempt in range(1, MAX_ATTEMPTS + 1):
        done = all_successful_task_ids()
        pending = [t for t in tasks if t["task_id"] not in done]
        if not pending:
            if attempt == 1:
                wlog(worker, f"{wf_dir}: all {len(tasks)} tasks already successful")
            return
        wlog(worker, f"{wf_dir}: attempt {attempt}, {len(pending)} task(s) to run")
        for i, task in enumerate(pending, start=1):
            records_by_task = all_records_by_task()
            prefix = fresh_prefix(task["task_id"], records_by_task, trail_sids)
            wlog(worker, f"{wf_dir} [{i}/{len(pending)}] {task['task_id']} ({prefix}) ...")
            rec = camp.run_suite_task(task, session_prefix=prefix)
            camp.append_record(lane_file, rec)
            status = "OK" if rec["success"] else f"FAIL({rec['error']})"
            wlog(worker, f"{wf_dir}      -> {status} in {rec['elapsed_seconds']:.1f}s")


def run_worker_pa(worker: str, pa_ids: list[str], trail_sids: set[str]) -> None:
    if not pa_ids:
        return
    registry = json.loads(camp.PA_BENCHMARKS.read_text(encoding="utf-8"))
    out_file = RESULTS_DIR / f"pa_batch_{worker.lower()}.jsonl"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        done = all_successful_task_ids()
        pending = [p for p in pa_ids if f"pa_{p}" not in done]
        if not pending:
            return
        wlog(worker, f"PA arm attempt {attempt}: {len(pending)} session(s)")
        for i, pa_id in enumerate(pending, start=1):
            entry = registry[pa_id]
            records_by_task = all_records_by_task()
            prefix = fresh_prefix(f"pa_{pa_id}", records_by_task, trail_sids, pa=True)
            wlog(worker, f"PA [{i}/{len(pending)}] PA_{pa_id} "
                         f"({entry['workflow']}, {len(entry['params_by_turn'])} turn(s), {prefix}) ...")
            rec = camp.run_pa(
                pa_id, workflow=entry["workflow"],
                n_turns=len(entry["params_by_turn"]), session_prefix=prefix,
            )
            camp.append_record(out_file, rec)
            status = "OK" if rec["success"] else f"FAIL({rec['error']})"
            wlog(worker, f"PA      -> {status} in {rec['elapsed_seconds']:.1f}s")


def worker_main(worker: str, trail_sids: set[str]) -> None:
    try:
        for wf_dir in WORKER_DIRS[worker]:
            run_workflow_tasks(worker, wf_dir, trail_sids)
        # PA sessions of this worker's workflows. Same-workflow serialization
        # holds: the suite tasks above are already finished inside this
        # worker, and no other worker ever touches these workflows.
        worker_dirs = set(WORKER_DIRS[worker])
        registry = json.loads(camp.PA_BENCHMARKS.read_text(encoding="utf-8"))
        pa_ids = sorted(
            pid for pid, entry in registry.items()
            if WORKFLOW_TO_DIR.get(entry["workflow"]) in worker_dirs
        )
        run_worker_pa(worker, pa_ids, trail_sids)
        wlog(worker, "DONE")
    except Exception as exc:  # noqa: BLE001 — surface and continue other workers
        wlog(worker, f"WORKER ERROR: {exc!r}")


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    wlog("main", "scanning audit trail for existing exp24 session ids ...")
    trail_sids = trail_session_ids()
    wlog("main", f"{len(trail_sids)} session ids in trail; launching "
                 f"{len(WORKER_DIRS)} workers")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(WORKER_DIRS)) as pool:
        futures = [pool.submit(worker_main, w, trail_sids) for w in WORKER_DIRS]
        for f in futures:
            f.result()
    wall_min = (time.monotonic() - t0) / 60.0
    wlog("main", f"all workers finished in {wall_min:.1f} min; writing summary")
    return camp.write_summary()


if __name__ == "__main__":
    sys.exit(main())
