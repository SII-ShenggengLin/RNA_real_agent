#!/usr/bin/env python3
"""Experiment 25b — PA_023 restore addendum (registered 2026-09-11, user-directed).

Companion to the frozen Exp 25 (quality-review advisory, Figs 4i/4j). Exp 25
registered one workflow-level exception: PA_023 turns 1–2 reference
``workspace/pa023_5utr.fa`` — an absolute path into the ephemeral workspace
root from the pre-reset registration era; the file was never git-tracked and
was absent from the fourth-reset state onward, so the frozen corpus recorded
turns 1–2 failing with FileNotFoundError identically in all three arms (the
2026-09-01 amendment deliberately did not re-create the file, to stay aligned
with the Exp-24 anchor run). This addendum does NOT touch the frozen corpus:
it restores the input from the task's own registration and re-measures the
one session under the identical three-arm protocol, so the paper can cite the
current registered state (31/31) with a frozen measurement behind it.

Pre-registration
----------------
* Question: with ``workspace/pa023_5utr.fa`` restored byte-identically from
  the task's own ``constants.UTR5_SEQUENCE`` (canonical copy
  ``data/benchmarks/RNA-BioBench-ProcessAware/fixtures/pa023_5utr.fa``), does
  PA_023 complete and succeed at the workflow level in all three Exp-25 arms,
  with per-turn outcomes identical across arms (the paired-identity primary
  endpoint)?
* Data gate (checked before any run, fails fast): the canonical fixture, the
  workspace copy and ``constants.UTR5_SEQUENCE`` are byte-identical; the
  turn-3 fixture is the constants sequence's 100–300 window (header-checked).
* Arms: the Exp-25 protocol verbatim — ``off`` (``RNADA_QUALITY_REVIEW=off``),
  ``on`` (production default), ``fail`` (``DEEPSEEK_BASE_URL`` connection-
  refused injection) — one fresh CLI subprocess per turn through the user
  form entry (``cli/form_chat.py``), inputs verbatim from ``pa_benchmarks.json``,
  CapGate advisory (the PA regression convention). Fresh ``exp25b_`` session
  ids; the shared platform audit trail receives every call under its stamp.
* Expected outcomes (structural): (1) 3/3 turns exit 0 and workflow-success
  in every arm, outcome tuples identical across arms; (2) off-arm: zero
  diagnosis entries, zero review-error markers; (3) on-arm: exactly two
  successful review calls per turn (6 total; ires_prediction is a reviewed
  workflow); (4) fail-arm: every attempted review call fails into the
  governance path (``_quality_review_error`` retained, zero completions, 2
  failed attempts per turn = 6); (5) zero retries in every arm.
* Merged-reporting convention (the paper's citation): frozen Exp-25 corpus
  for the other 30 sessions + this addendum for PA_023, latest-record-wins —
  31/31 workflow-level success per arm; the call totals are unchanged by the
  merge (review runs even on failed turns, so PA_023 contributed 6 on-arm
  completed calls and 6 outage-arm failed attempts in both eras, keeping
  145 and 144); retries 0/1/0 (PA_012's retried on-arm turn, unchanged).
* Determinism: ``--verify`` recomputes every summary number from the frozen
  ``records.jsonl`` byte-identically.

Usage:
    PYTHONPATH=. python experiments/exp25b_pa023_restore_addendum.py --run
    PYTHONPATH=. python experiments/exp25b_pa023_restore_addendum.py --verify
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "exp25b_pa023_restore_addendum"
LOGS_DIR = RESULTS_DIR / "logs"
RECORDS_PATH = RESULTS_DIR / "records.jsonl"
SUMMARY_PATH = RESULTS_DIR / "summary.json"

PA_ID = "023"
FIXTURE = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-ProcessAware" / "fixtures" / "pa023_5utr.fa"
WORKSPACE_COPY = PROJECT_ROOT / "workspace" / "pa023_5utr.fa"
MODE1_FIXTURE = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks" / "11_ires_prediction" / "pa023_mode1_5utr.fa"


def _load_exp25_driver():
    spec = importlib.util.spec_from_file_location(
        "exp25_driver", PROJECT_ROOT / "experiments" / "exp25_quality_review_advisory.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_sequence(path: Path) -> str:
    return "".join(l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith(">"))


def data_gate(entry: dict[str, Any]) -> None:
    """Fail fast unless fixture == workspace copy == constants, turn-3 = window."""
    consts = entry["constants"]["UTR5_SEQUENCE"]
    fixture_seq = _fixture_sequence(FIXTURE)
    assert fixture_seq == consts, "canonical fixture != constants.UTR5_SEQUENCE"
    assert WORKSPACE_COPY.exists(), f"workspace copy missing: {WORKSPACE_COPY}"
    workspace_seq = _fixture_sequence(WORKSPACE_COPY)
    assert workspace_seq == consts, "workspace copy != constants.UTR5_SEQUENCE"
    mode1_seq = _fixture_sequence(MODE1_FIXTURE)
    header = MODE1_FIXTURE.read_text(encoding="utf-8").splitlines()[0]
    assert header.strip() == ">user 100 300", f"unexpected turn-3 fixture header: {header!r}"
    assert mode1_seq == consts[99:300], "turn-3 fixture != constants[99:300] (1-based 100-300)"
    print(f"[exp25b data gate] fixture == workspace == constants ({len(consts)} nt); turn-3 = 100-300 window — OK")


def run() -> None:
    benchmarks = json.loads((PROJECT_ROOT / "pa_benchmarks.json").read_text(encoding="utf-8"))
    entry = benchmarks[PA_ID]
    data_gate(entry)

    exp25 = _load_exp25_driver()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for arm in ("off", "on", "fail"):
        session_id = f"exp25b_{arm}_pa{PA_ID}_{time.strftime('%Y%m%d_%H%M%S')}_{__import__('os').getpid()}"
        log_dir = LOGS_DIR / arm
        log_dir.mkdir(parents=True, exist_ok=True)
        record: dict[str, Any] = {
            "arm": arm,
            "pa_id": PA_ID,
            "workflow": entry["workflow"],
            "reviewed_workflow": entry["workflow"] not in exp25.EXEMPT_WORKFLOWS,
            "session_id": session_id,
            "n_turns": len(entry["params_by_turn"]),
            "turns": [],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        started = time.monotonic()
        for turn, params in enumerate(entry["params_by_turn"], start=1):
            turn_log = log_dir / f"turn{turn}_{time.strftime('%Y%m%d_%H%M%S')}.log"
            rec = exp25._run_turn_subprocess(arm, PA_ID, entry["workflow"], params, turn, session_id, turn_log)
            record["turns"].append(rec)
            print(
                f"[exp25b {time.strftime('%H:%M:%S')}] {arm}/PA_{PA_ID} turn {turn}/3 "
                f"ok={rec['turn_success']} exit={rec['exit_code']} "
                f"reviews(ok/fail)={rec['successful_review_calls']}/{rec['failed_review_calls']} "
                f"{rec['elapsed_seconds']:.0f}s",
                flush=True,
            )
        record["wall_seconds"] = round(time.monotonic() - started, 1)
        record["failed_turns"] = sum(1 for t in record["turns"] if not t["turn_success"])
        record["total_retry_count"] = sum(t["retry_count"] or 0 for t in record["turns"])
        record["total_successful_review_calls"] = sum(t["successful_review_calls"] for t in record["turns"])
        record["total_failed_review_calls"] = sum(t["failed_review_calls"] for t in record["turns"])
        record["session_success"] = record["failed_turns"] == 0
        records.append(record)

    RECORDS_PATH.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    summary = analyze(records)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary["checks"], indent=1))
    if not all(summary["checks"].values()):
        print("[exp25b] EXPECTATION CHECKS FAILED — see above", file=sys.stderr)
        sys.exit(1)
    print(f"[exp25b] all expectation checks passed → {SUMMARY_PATH}")


def analyze(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm = {r["arm"]: r for r in records}
    outcome = {arm: tuple(bool(t["workflow_success"]) for t in r["turns"]) for arm, r in by_arm.items()}
    checks = {
        "three_arms_present": sorted(by_arm) == ["fail", "off", "on"],
        "all_turns_exit_zero": all(t["exit_code"] == 0 and not t["timed_out"] for r in records for t in r["turns"]),
        "all_turns_workflow_success": all(t["workflow_success"] is True for r in records for t in r["turns"]),
        "outcome_identical_across_arms": len(set(outcome.values())) == 1 and all(outcome.values()),
        "off_zero_review_calls": all(
            t["successful_review_calls"] == 0 and t["failed_review_calls"] == 0 for t in by_arm["off"]["turns"]
        ),
        "on_two_calls_per_turn": all(t["successful_review_calls"] == 2 for t in by_arm["on"]["turns"]),
        "on_six_total": by_arm["on"]["total_successful_review_calls"] == 6,
        "fail_zero_completions": by_arm["fail"]["total_successful_review_calls"] == 0,
        "fail_two_attempts_per_turn": all(t["failed_review_calls"] == 2 for t in by_arm["fail"]["turns"]),
        "fail_error_marker_every_turn": all(
            (t.get("review_error") or {}).get("type") == "APIConnectionError" for t in by_arm["fail"]["turns"]
        ),
        "zero_retries": all(r["total_retry_count"] == 0 for r in records),
    }
    return {
        "registered": "2026-09-11 PA_023 restore addendum (exp25b); frozen Exp-25 corpus untouched",
        "arms": {
            arm: {
                "session_id": r["session_id"],
                "n_turns": r["n_turns"],
                "turns_workflow_success": sum(1 for t in r["turns"] if t["workflow_success"] is True),
                "session_success": r["session_success"],
                "total_retry_count": r["total_retry_count"],
                "total_successful_review_calls": r["total_successful_review_calls"],
                "total_failed_review_calls": r["total_failed_review_calls"],
                "outcome_tuple": list(outcome[arm]),
            }
            for arm, r in by_arm.items()
        },
        "merged_reporting": {
            "note": "frozen Exp-25 corpus for the other 30 sessions + this addendum for PA_023 (latest-record-wins)",
            "workflow_level_success_per_arm": "31/31",
            "on_arm_completed_calls_total": 145,
            "outage_arm_failed_attempts_total": 144,
            "retries_by_arm": [0, 1, 0],
        },
        "checks": checks,
    }


def verify() -> None:
    records = [json.loads(l) for l in RECORDS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    summary = analyze(records)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    assert all(summary["checks"].values()), "verify: expectation checks failed"
    print(f"[exp25b --verify] {len(records)} records recomputed byte-identically — all checks green")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true", help="run the three-arm addendum (data gate first)")
    ap.add_argument("--verify", action="store_true", help="recompute the summary from frozen records")
    args = ap.parse_args()
    if args.run:
        run()
    elif args.verify:
        verify()
    else:
        ap.print_help()
