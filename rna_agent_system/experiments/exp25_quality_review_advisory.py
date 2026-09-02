#!/usr/bin/env python3
"""Experiment 25 (paper §2.4 实验 6, Figs 4g + 4h): governance close-out —
quality review is advisory (31/31 with and without), and an LLM review failure
is audit metadata only.

Pre-registration (pilot-first rule, MANUSCRIPT.md §2; zero-intervention rule)
---------------------------------------------------------------------------
* Question (this experiment's own): does the advisory QualityAgent review
  change any task outcome of the full process-aware regression suite, and is
  an LLM review failure recorded as audit metadata without ever converting a
  successful run into a failed one? (Fig. 4g data; the companion Fig. 4h
  assembles this experiment's measured LLM usage with the other re-run
  campaigns'.)
* DATASET ALIGNMENT (user-confirmed 2026-09-01, "与最新的数据集保持一致"): the
  full current PA suite — PA_006–PA_036, 31 form sessions / 96 user turns,
  72 turns on the 8 QualityAgent-reviewed workflows and 24 turns on the 3
  deterministic-exempt ones (mRNA sequence scoring, ASO screening,
  RNA–small-molecule interaction), including the GenNav navigation session
  PA_028 and the Fig-2h representative session PA_036. This is exactly the PA
  arm of the Exp-24 shared-instrument campaign (the latest registered
  dataset feeding Figs 2a/2h/2i/4f). The legacy "19/19" was the same suite at
  legacy era (PA_006–PA_024, before the 2026-08-19 fresh batch); the sample
  is re-registered at the full current scale and the headline becomes 31/31.
* Arms — each (arm, session) is a fresh CLI subprocess per turn through the
  user form entry (``cli/form_chat.py --workflow --params-file --session-id``),
  inputs verbatim from ``pa_benchmarks.json``, CapGate advisory (the PA
  regression convention), microservices pre-warmed on GPUs 0/1/2:
  - ``off``:  ``RNADA_QUALITY_REVIEW=off`` — a new env knob added to
    ``cli/form_chat.py`` (default "on", the RNADA_CAPGATE env-knob
    convention). DISCLOSED platform wiring: without it the registered
    off-arm cannot be driven through the production form path; the
    interactive default is unchanged.
  - ``on``:   production default (DeepSeek ``deepseek-v4-pro``, temperature
    0.2 — the QualityAgent's shipped configuration).
  - ``fail``: production default + ``DEEPSEEK_BASE_URL=http://127.0.0.1:9``
    (connection-refused injection; ``load_dotenv()`` does not override
    pre-set env, so the injection wins over ``.env``). Every attempted review
    call must fail into the governance path: ``review_unavailable``
    zero-confidence pass with ``state["_quality_review_error"]`` retained.
* Metrics per turn (parsed from the saved per-turn ``workflow_results_*.json``
  and the tee'd subprocess log): subprocess exit code; ``success``;
  ``retry_count``; successful review calls = ``len(_diagnosis_history)``;
  failed review calls = occurrences of the QualityAgent ERROR log line
  "QualityAgent LLM diagnosis failed"; ``_quality_review_error`` marker
  (type). Turn success (workflow level) = exit code 0 AND saved JSON
  ``success`` is true; turn completion = exit code 0 (the exp8/exp24
  campaign convention).
* AMENDMENT (registered 2026-09-01 18:20, mid-run BEFORE the full-run
  analysis, from exp8/exp24 frozen evidence — not from cross-arm comparison):
  dual success criteria + a paired-identity primary endpoint, because the
  registered dataset carries one long-standing input-fixture gap —
  PA_023 turns 1–2 reference ``workspace/pa023_5utr.fa``, which has ZERO
  successful reads in the entire retained audit trail (16 failures;
  identical FileNotFoundError inside the frozen exp8 and exp24 corpora, and
  exp24's PA record convention ``success = error is None and exit_code == 0``
  recorded those turns as completions). The gap is arm-independent and
  inherited; re-creating the file would diverge from the Exp-24 anchor run,
  so it is disclosed as measured, not fixed here.
* Expected outcomes (structural, pre-registered + amendment):
  (1) completion: 31/31 sessions complete in ALL THREE arms (exit-code
      convention); workflow level: every session's per-turn outcome tuple
      is IDENTICAL across the three arms (the paired-identity primary
      endpoint — review on/off/failing never changes any task outcome);
      expected 30/31 workflow-level success with the single PA_023
      exception identical in every arm;
  (1b) retries: review-on may retry hard-failure turns (the SpecialistAgent's
      own hard-failure rule needs review-suggested overrides; exp24's frozen
      PA_023 turn 2 shows exactly one such retry that could not rescue a
      missing input file) while review-off cannot retry — the legacy
      "retries 2 vs 0" mechanism; outcomes stay identical regardless;
  (2) arm ``off``: zero diagnosis entries and zero review-error markers on
      every turn;
  (3) arm ``on``: ≥1 successful review call on every reviewed-workflow turn
      (structurally 2 for a passing turn — in-loop + final review — plus one
      per hard-failure retry round; legacy comparator: 93 calls over 45
      reviewed turns), zero on exempt-workflow turns;
  (4) arm ``fail``: every REVIEWED turn records ``_quality_review_error``
      (connection-refused class) with the turn's workflow outcome unchanged
      (identical to the other arms), zero diagnosis entries; exempt turns
      carry no marker (no LLM call is ever attempted for them);
  (5) no arm flips a successful workflow result to failed (``success`` from
      the workflow result alone).
* Scheduling (disclosed; wall-time convention only — timing is NOT a metric
  here): a global pool of ≤6 concurrent sessions, with the GPU-class
  workflows (``rna_aptamer_design``, ``rna_tertiary_structure_design``)
  capped at 3 concurrent. Safety basis, verified in code: EGARPS+ writes its
  ``result.txt`` beside the input PDB and the form path writes every
  intermediate to a uuid-named file inside the per-session workspace, so
  distinct sessions cannot collide (the exp16 input isolation was needed only
  for its shared in-process paths); GPU contention affects wall time only.
* Timeout: 7200 s per turn subprocess, whole-process-group kill on expiry
  (the exp8 PA_028 orphan lesson).
* Re-run convention (exp24 amendment convention): a session demonstrably
  killed by infrastructure (timeout/OOM) may be re-run ONCE under a fresh
  session id, the censored record retained and disclosed; workflow-logic
  failures are reported as measured, never re-run.
* Pilot: 3 arms × {PA_014 (deterministic-exempt, fastest) + PA_012 (reviewed,
  fast)} = 6 sessions under ``exp25_pilot_`` session ids — excluded from the
  full corpus by construction. Pilot gate: 6/6 session success + expectations
  (2)–(4) on the pilot subset.
* Contamination control: fresh session ids per run (``exp25_<arm>_pa<PA>_*``);
  every tool call lands in the shared platform audit trail under its session
  stamp; the driver never mutates benchmark inputs.
* Determinism: ``--analyze``/``--verify`` recompute every headline number
  from the frozen ``records.jsonl`` byte-identically.

Usage:
    PYTHONPATH=. python experiments/exp25_quality_review_advisory.py --pilot
    PYTHONPATH=. python experiments/exp25_quality_review_advisory.py --full
    PYTHONPATH=. python experiments/exp25_quality_review_advisory.py --analyze
    PYTHONPATH=. python experiments/exp25_quality_review_advisory.py --verify
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp25_quality_review_advisory"
LOGS_DIR = RESULTS_DIR / "logs"
RECORDS_PATH = RESULTS_DIR / "records.jsonl"
PILOT_RECORDS_PATH = RESULTS_DIR / "pilot.jsonl"

PA_BENCHMARKS = PROJECT_ROOT / "pa_benchmarks.json"

# The three deterministic-exempt workflows (no evaluation dimensions → the
# review returns a pass report without any LLM call).
EXEMPT_WORKFLOWS = {
    "mrna_sequence_scoring",
    "aso_target_screening",
    "rna_small_molecule_interaction",
}
GPU_CLASS_WORKFLOWS = {
    "rna_aptamer_design",
    "rna_tertiary_structure_design",
}

ARMS: dict[str, dict[str, str]] = {
    "off": {"RNADA_QUALITY_REVIEW": "off"},
    "on": {},
    "fail": {"DEEPSEEK_BASE_URL": "http://127.0.0.1:9"},
}

TURN_TIMEOUT_S = 7200
MAX_CONCURRENT_SESSIONS = 6
MAX_CONCURRENT_GPU_CLASS = 3

SAVED_RESULTS_RE = re.compile(r"^\[Saved\] 完整结果已保存: (\S+)$", re.M)
REVIEW_FAIL_LOG_LINE = "QualityAgent LLM diagnosis failed"

_print_lock = threading.Lock()
_gpu_class_semaphore = threading.Semaphore(MAX_CONCURRENT_GPU_CLASS)


def _log(msg: str) -> None:
    with _print_lock:
        print(f"[exp25 {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_pa_benchmarks() -> dict[str, dict[str, Any]]:
    return json.loads(PA_BENCHMARKS.read_text(encoding="utf-8"))


def _run_turn_subprocess(
    arm: str,
    pa_id: str,
    workflow: str,
    params: dict[str, Any],
    turn: int,
    session_id: str,
    turn_log_path: Path,
) -> dict[str, Any]:
    """Run one form turn as a production CLI subprocess; return the turn record."""
    params_file = turn_log_path.parent / f"params_turn{turn}.json"
    params_file.parent.mkdir(parents=True, exist_ok=True)
    params_file.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
    env.setdefault("RNADA_CAPGATE", "advisory")
    env.update(ARMS[arm])

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow", workflow,
        "--params-file", str(params_file),
        "--session-id", session_id,
    ]

    started = time.monotonic()
    timed_out = False
    with turn_log_path.open("w", encoding="utf-8", errors="replace") as log_fp:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,  # kill the whole group on timeout (exp8 lesson)
        )
        try:
            stdout, _ = proc.communicate(timeout=TURN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), 15)
            except ProcessLookupError:
                pass
            try:
                stdout, _ = proc.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), 9)
                stdout, _ = proc.communicate()
            stdout = stdout or ""
            stdout += f"\n[exp25] TURN TIMED OUT after {TURN_TIMEOUT_S}s (process group killed)"
        log_fp.write(stdout)
    elapsed = time.monotonic() - started

    record: dict[str, Any] = {
        "turn": turn,
        "exit_code": proc.returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 1),
        "workflow_success": None,
        "retry_count": None,
        "successful_review_calls": 0,
        "failed_review_calls": stdout.count(REVIEW_FAIL_LOG_LINE),
        "review_error": None,
        "results_json": None,
    }

    m = SAVED_RESULTS_RE.search(stdout)
    if m:
        results_path = Path(m.group(1))
        record["results_json"] = str(results_path)
        try:
            data = json.loads(results_path.read_text(encoding="utf-8"))
            record["workflow_success"] = bool(data.get("success"))
            record["retry_count"] = int(data.get("retry_count", 0) or 0)
            record["successful_review_calls"] = len(data.get("_diagnosis_history") or [])
            err = data.get("_quality_review_error")
            if isinstance(err, dict):
                record["review_error"] = {"type": err.get("type"), "message": str(err.get("message"))[:300]}
        except Exception as exc:  # unreadable/corrupt results file — record as measured
            record["results_json_error"] = f"{type(exc).__name__}: {exc}"

    record["turn_success"] = (
        record["exit_code"] == 0
        and not timed_out
        and record["workflow_success"] is True
    )
    return record


def run_session(arm: str, pa_id: str, entry: dict[str, Any], *, pilot: bool) -> dict[str, Any]:
    workflow = entry["workflow"]
    params_by_turn = entry["params_by_turn"]
    prefix = "exp25_pilot" if pilot else "exp25"
    session_id = f"{prefix}_{arm}_pa{pa_id}_{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

    record: dict[str, Any] = {
        "arm": arm,
        "pa_id": pa_id,
        "workflow": workflow,
        "reviewed_workflow": workflow not in EXEMPT_WORKFLOWS,
        "session_id": session_id,
        "pilot": pilot,
        "n_turns": len(params_by_turn),
        "turns": [],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    log_dir = LOGS_DIR / ("pilot" if pilot else "full") / arm / f"pa{pa_id}"
    log_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    gpu_class = workflow in GPU_CLASS_WORKFLOWS
    if gpu_class:
        _gpu_class_semaphore.acquire()
    try:
        for turn, params in enumerate(params_by_turn, start=1):
            turn_log = log_dir / f"turn{turn}_{time.strftime('%Y%m%d_%H%M%S')}.log"
            rec = _run_turn_subprocess(arm, pa_id, workflow, params, turn, session_id, turn_log)
            record["turns"].append(rec)
            _log(
                f"{arm}/PA_{pa_id} turn {turn}/{len(params_by_turn)} "
                f"ok={rec['turn_success']} exit={rec['exit_code']} "
                f"reviews(ok/fail)={rec['successful_review_calls']}/{rec['failed_review_calls']} "
                f"{rec['elapsed_seconds']:.0f}s"
            )
    finally:
        if gpu_class:
            _gpu_class_semaphore.release()
    record["wall_seconds"] = round(time.monotonic() - started, 1)
    record["failed_turns"] = sum(1 for t in record["turns"] if not t["turn_success"])
    record["total_retry_count"] = sum(t["retry_count"] or 0 for t in record["turns"])
    record["total_successful_review_calls"] = sum(t["successful_review_calls"] for t in record["turns"])
    record["total_failed_review_calls"] = sum(t["failed_review_calls"] for t in record["turns"])
    record["session_success"] = record["failed_turns"] == 0
    return record


def _append_record(path: Path, record: dict[str, Any]) -> None:
    with _print_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


PILOT_PAS = ["014", "012"]  # PA_014 deterministic-exempt (fastest) + PA_012 reviewed (fast)


def run_batch(arms: list[str], pa_ids: list[str], *, pilot: bool, resume: bool) -> None:
    benchmarks = load_pa_benchmarks()
    out_path = PILOT_RECORDS_PATH if pilot else RECORDS_PATH
    done: set[tuple[str, str]] = set()
    if resume and not pilot:
        done = {
            (r["arm"], r["pa_id"])
            for r in _load_records(RECORDS_PATH)
            if r.get("session_success")
        }
        _log(f"resume: {len(done)} (arm, pa) already successful — skipped")

    jobs = [(arm, pa) for arm in arms for pa in pa_ids if (arm, pa) not in done]
    _log(f"launching {len(jobs)} sessions (arms={arms}, {len(pa_ids)} PA ids, pilot={pilot})")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SESSIONS) as pool:
        futures = {
            pool.submit(run_session, arm, pa, benchmarks[pa], pilot=pilot): (arm, pa)
            for arm, pa in jobs
        }
        for fut in as_completed(futures):
            arm, pa = futures[fut]
            try:
                record = fut.result()
            except Exception as exc:
                record = {
                    "arm": arm, "pa_id": pa, "pilot": pilot,
                    "session_success": False,
                    "driver_exception": f"{type(exc).__name__}: {exc}",
                }
            _append_record(out_path, record)
            _log(
                f"DONE {arm}/PA_{pa} success={record.get('session_success')} "
                f"failed_turns={record.get('failed_turns')} → {out_path.name}"
            )


# ---------------------------------------------------------------------------
# Analysis — every headline number recomputed from the frozen records.
# ---------------------------------------------------------------------------

def analyze(records: list[dict[str, Any]], *, pilot: bool) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    for r in records:
        if r.get("pilot") != pilot:
            continue
        if r["arm"] in by_arm:
            by_arm[r["arm"]].append(r)

    summary: dict[str, Any] = {"pilot": pilot, "n_sessions_expected": len(PILOT_PAS) if pilot else 31, "arms": {}}
    for arm, recs in by_arm.items():
        n = len(recs)
        turns = [t for r in recs for t in r.get("turns", [])]
        # dual criteria (the 2026-09-01 amendment): completion = exit-code 0
        # (exp8/exp24 convention); workflow = all turns workflow_success
        def _completion(r: dict[str, Any]) -> bool:
            ts = r.get("turns", [])
            return bool(ts) and all(t.get("exit_code") == 0 and not t.get("timed_out") for t in ts)

        def _workflow(r: dict[str, Any]) -> bool:
            ts = r.get("turns", [])
            return bool(ts) and all(
                t.get("exit_code") == 0 and not t.get("timed_out") and t.get("workflow_success") is True
                for t in ts
            )

        def _outcome_tuple(r: dict[str, Any]) -> tuple:
            return tuple(bool(t.get("workflow_success")) for t in r.get("turns", []))

        reviewed = [r for r in recs if r.get("reviewed_workflow")]
        exempt = [r for r in recs if not r.get("reviewed_workflow")]
        arm_summary = {
            "n_sessions": n,
            "n_session_completion": sum(1 for r in recs if _completion(r)),
            "n_session_workflow_success": sum(1 for r in recs if _workflow(r)),
            "n_turns": len(turns),
            "n_turn_workflow_success": sum(1 for t in turns if t.get("workflow_success") is True),
            "total_retry_count": sum(r.get("total_retry_count", 0) for r in recs),
            "sessions_with_retries": sum(1 for r in recs if r.get("total_retry_count", 0) > 0),
            "total_successful_review_calls": sum(r.get("total_successful_review_calls", 0) for r in recs),
            "total_failed_review_calls": sum(r.get("total_failed_review_calls", 0) for r in recs),
            "workflow_failed_sessions": sorted(r["pa_id"] for r in recs if not _workflow(r)),
            "outcome_tuples": {r["pa_id"]: _outcome_tuple(r) for r in recs},
            # expectation checks (structural)
            "checks": {},
        }
        # (2) off-arm: zero diagnosis entries, zero review-error markers
        if arm == "off":
            arm_summary["checks"]["zero_diagnosis_entries"] = all(
                t.get("successful_review_calls", 0) == 0 for t in turns
            )
            arm_summary["checks"]["zero_review_error_markers"] = all(
                t.get("review_error") is None for t in turns
            )
        # (3) on-arm: >=1 successful review on every reviewed-workflow turn,
        #     zero on exempt-workflow turns
        if arm == "on":
            rev_turns = [t for r in reviewed for t in r.get("turns", [])]
            exc_turns = [t for r in exempt for t in r.get("turns", [])]
            arm_summary["checks"]["reviewed_turns_have_review"] = bool(rev_turns) and all(
                t.get("successful_review_calls", 0) >= 1 for t in rev_turns
            )
            arm_summary["checks"]["exempt_turns_have_zero_reviews"] = all(
                t.get("successful_review_calls", 0) == 0 for t in exc_turns
            )
        # (4) fail-arm: every REVIEWED turn records the error marker, zero
        #     diagnosis entries; exempt turns carry no marker
        if arm == "fail":
            rev_rec_turns = [(r, t) for r in reviewed for t in r.get("turns", [])]
            exc_rec_turns = [(r, t) for r in exempt for t in r.get("turns", [])]
            arm_summary["checks"]["reviewed_turns_marked_unavailable"] = bool(rev_rec_turns) and all(
                t.get("review_error") is not None for _, t in rev_rec_turns
            )
            arm_summary["checks"]["zero_diagnosis_entries"] = all(
                t.get("successful_review_calls", 0) == 0 for t in turns
            )
            arm_summary["checks"]["exempt_turns_unmarked"] = all(
                t.get("review_error") is None for _, t in exc_rec_turns
            )
            # the marker stayed pure metadata: no marked turn was killed by
            # the review failure (subprocess completed; outcome equality
            # across arms is checked separately as the paired-identity gate)
            arm_summary["checks"]["no_turn_failed_from_marker"] = all(
                t.get("exit_code") == 0 and not t.get("timed_out")
                for _, t in rev_rec_turns if t.get("review_error") is not None
            )
        summary["arms"][arm] = arm_summary

    # Cross-arm paired-identity endpoint (the amendment's primary): every
    # session's per-turn workflow-outcome tuple is IDENTICAL across arms.
    common_pas = set.intersection(
        *(set(summary["arms"][a]["outcome_tuples"]) for a in ARMS if summary["arms"][a]["outcome_tuples"])
    ) if all(summary["arms"][a]["outcome_tuples"] for a in ARMS) else set()
    mismatched = sorted(
        pa for pa in common_pas
        if len({summary["arms"][a]["outcome_tuples"][pa] for a in ARMS}) > 1
    )
    summary["headline"] = {
        "n_sessions_per_arm": len(common_pas),
        "completion_counts": {arm: summary["arms"][arm]["n_session_completion"] for arm in ARMS},
        "workflow_success_counts": {arm: summary["arms"][arm]["n_session_workflow_success"] for arm in ARMS},
        "paired_outcome_identity": not mismatched,
        "paired_outcome_mismatches": mismatched,
        "workflow_failed_sessions": sorted(
            {pa for arm in ARMS for pa in summary["arms"][arm]["workflow_failed_sessions"]}
        ),
        "retry_counts": {arm: summary["arms"][arm]["total_retry_count"] for arm in ARMS},
        "advisory_holds": (
            not mismatched
            and len({summary["arms"][arm]["n_session_completion"] for arm in ARMS}) == 1
            and len({summary["arms"][arm]["n_session_workflow_success"] for arm in ARMS}) == 1
        ),
    }
    return summary


def cmd_analyze(pilot: bool) -> int:
    records = _load_records(PILOT_RECORDS_PATH if pilot else RECORDS_PATH)
    summary = analyze(records, pilot=pilot)
    out = RESULTS_DIR / ("pilot_summary.json" if pilot else "summary.json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    gate = summary["headline"]["advisory_holds"] and all(
        all(v for k, v in arm.get("checks", {}).items()) for arm in summary["arms"].values()
    )
    print(f"\n[exp25] gate {'PASS' if gate else 'FAIL'} → {out}")
    return 0 if gate else 1


def cmd_verify() -> int:
    """Recompute the frozen summary from records.jsonl; byte-identical check."""
    records = _load_records(RECORDS_PATH)
    summary = analyze(records, pilot=False)
    frozen = json.loads((RESULTS_DIR / "summary.json").read_text(encoding="utf-8"))
    ok = json.dumps(summary, sort_keys=True) == json.dumps(frozen, sort_keys=True)
    print(f"[exp25] --verify recomputation byte-identical: {ok}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--pilot", action="store_true", help="run the 6-session pilot (3 arms × PA_014+PA_012)")
    parser.add_argument("--full", action="store_true", help="run all 31 PA sessions × 3 arms")
    parser.add_argument("--resume", action="store_true", help="skip (arm, pa) pairs already successful (full run only)")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--analyze-pilot", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.pilot:
        run_batch(list(ARMS), PILOT_PAS, pilot=True, resume=False)
        return 0
    if args.full:
        pa_ids = sorted(load_pa_benchmarks().keys())
        run_batch(list(ARMS), pa_ids, pilot=False, resume=args.resume)
        return 0
    if args.analyze_pilot:
        return cmd_analyze(pilot=True)
    if args.analyze:
        return cmd_analyze(pilot=False)
    if args.verify:
        return cmd_verify()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
