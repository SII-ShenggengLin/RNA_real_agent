#!/usr/bin/env python3
"""Fig 6 panel a driver: QualityAgent value ablation over the PA benchmark suite.

Implements `docs/MANUSCRIPT.md` §8.1 (panel a) / §8.2 item 1:

- drives ``AgentRunner(quality_review_enabled=True|False)`` through the Python
  API (``AgentRunner.run_form`` — no CLI subprocess) over every task in
  ``pa_benchmarks.json`` (``params_by_turn``);
- multi-turn tasks are fed turn-by-turn with a fresh ``SessionMemory`` per
  (task, arm) and a stable session_id, mirroring the CLI session semantics
  (cross-turn ``_previous_workflow_result`` quality context preserved);
- records per-turn quality-report presence/action, retry counts, hard-failure
  recoveries, final success, best-candidate metrics (for cross-arm best-metric
  deltas), elapsed seconds and errors
  -> ``experiments/results/fig6_quality_ablation.jsonl``.

Ablation semantics (see `agent_core/agents/quality_agent.py` and
`agent_core/agents/specialist_agent.py`):
- arm ``quality_on``: ``QualityAgent`` runs its LLM diagnosis; in advisory mode
  (``quality_auto_retry=False``) ``SpecialistAgent`` auto-retries only hard
  failures (``success=False`` / empty candidates / tool errors).
- arm ``quality_off``: ``QualityAgent.review`` short-circuits to a synthetic
  ``pass`` report without any LLM call, so hard failures are never retried.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_quality_ablation.py \
        [--tasks 006,009] [--limit N] [--resume] [--dry-run] [--timeout SEC]

Options:
    --tasks LIST    comma-separated PA numbers (default: all tasks in pa_benchmarks.json)
    --limit N       run at most N (task, arm) jobs (after filtering)
    --resume        skip (task_id, arm) pairs that already have a successful record
    --dry-run       list the (task, arm) jobs that would run, then exit
    --timeout SEC   per-turn wall-clock limit (default: 3600; SIGALRM-based, main thread)
    --output PATH   output JSONL path (default: experiments/results/fig6_quality_ablation.jsonl)

Notes:
- Records are appended; analysis should take the *latest* record per (task_id, arm).
- A failed task is recorded with ``success=false`` and an ``errors`` list; the
  driver never aborts the batch because of a single task.
- Importing this module has no side effects: all ``agent_core`` imports are
  deferred to the run path, and nothing executes outside ``main()``.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_PATH = PROJECT_ROOT / "pa_benchmarks.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig6_quality_ablation.jsonl"

ARMS = ("quality_on", "quality_off")
ARM_ENABLED = {"quality_on": True, "quality_off": False}

# Reasoning prefixes of QualityAgent._pass_report() shortcuts that bypass the
# LLM (disabled by state flag, or deterministic workflow without
# evaluation_dimensions). Used to tell synthetic pass reports from real LLM
# diagnoses.
_SYNTHETIC_PASS_PREFIXES = ("Quality review disabled", "Workflow ")


def load_pa_tasks(path: Path = BENCHMARKS_PATH) -> list[dict[str, Any]]:
    """Return PA tasks sorted by PA number: [{task_id, pa, workflow, params_by_turn}]."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks: list[dict[str, Any]] = []
    for pa in sorted(raw):
        entry = raw[pa]
        tasks.append({
            "task_id": f"PA_{pa}",
            "pa": pa,
            "workflow": entry["workflow"],
            "params_by_turn": entry["params_by_turn"],
        })
    return tasks


def load_successful_keys(output_path: Path, key_fields: tuple[str, ...]) -> set[tuple]:
    """Keys of records with ``success=true`` already present in the JSONL output."""
    done: set[tuple] = set()
    if not output_path.exists():
        return done
    with output_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("success"):
                done.add(tuple(rec.get(f) for f in key_fields))
    return done


class TurnTimeout(Exception):
    """Raised when a single turn exceeds the configured wall-clock limit."""


@contextlib.contextmanager
def _turn_time_limit(seconds: int | None) -> Iterator[None]:
    """SIGALRM-based per-turn timeout (POSIX, main thread only).

    NOTE (2026-07-30 campaign observation): this is NOT a hard kill. The
    TurnTimeout raised by the SIGALRM handler can be swallowed by broad
    `except Exception` handlers further down the call stack (workflow / tool
    layers), converting the timeout into step-level failures while the turn
    keeps running — observed on fig6b PA_020 (rna_aptamer_design), which ran
    ~146 min under a 5400 s limit while still making real progress (active
    ProteinX connections + CPU growth). This is tolerated by design: the
    record eventually lands (success or step failures) and `--resume` sweeps
    genuine failures. Do NOT "fix" a long-running turn by killing the driver
    unless logs show no forward progress.
    """
    if not seconds:
        yield
        return

    def _handler(signum: int, frame: Any) -> None:
        raise TurnTimeout(f"turn exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def build_runner(*, quality_review_enabled: bool) -> Any:
    """Construct an AgentRunner with default (DeepSeek) LLM configuration.

    Imports are deferred so that importing this module never touches
    agent_core / the LLM config (import-safe; see module docstring).
    """
    from agent_core.runner import AgentRunner
    from agent_core.session_memory import SessionMemory
    from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

    return AgentRunner(
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        session_memory=SessionMemory(),
        quality_review_enabled=quality_review_enabled,
        quality_auto_retry=False,  # advisory mode (INTERFACE_LOCKS §19 default)
    )


def best_metrics_snapshot(wf_result: Any) -> dict[str, Any] | None:
    """Numeric scores/metrics of the best candidate (for cross-arm deltas)."""
    if wf_result is None:
        return None
    best = getattr(wf_result, "best_candidate", None)
    if best is None:
        return None
    scores = {
        k: v for k, v in (getattr(best, "scores", None) or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    meta = getattr(best, "metadata", None) or {}
    mb = meta.get("metrics_bundle", {}) if isinstance(meta, dict) else {}
    metrics = {
        k: v for k, v in mb.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    return {
        "candidate_id": getattr(best, "id", None),
        "source": getattr(best, "source", None),
        "scores": scores,
        "metrics": metrics,
    }


def extract_turn_record(state: dict[str, Any], *, turn: int, elapsed: float) -> dict[str, Any]:
    """Pull the Fig-6 per-turn signals out of a finished AgentState."""
    wf = state.get("workflow_result")
    reports: list[dict[str, Any]] = []
    for d in state.get("_diagnosis_history") or []:
        if not isinstance(d, dict):
            continue
        reasoning = d.get("reasoning") or ""
        synthetic = reasoning.startswith(_SYNTHETIC_PASS_PREFIXES)
        reports.append({
            "action": d.get("action"),
            "quality_score": d.get("quality_score"),
            "n_issues": len(d.get("issues") or []),
            "parameter_overrides": d.get("parameter_overrides") or {},
            "evaluator_only": bool(d.get("evaluator_only")),
            # QualityAgent appends this marker when it converts a hard-failure
            # pass into a retry; signals that a hard failure occurred pre-retry.
            "hard_failure_signal": "Hard failure detected" in reasoning,
            "synthetic_pass": synthetic,
        })
    retry_count = state.get("retry_count", 0)
    success = bool(getattr(wf, "success", False)) if wf is not None else False
    return {
        "turn": turn,
        "success": success,
        "candidate_count": len(getattr(wf, "all_candidates", []) or []) if wf is not None else 0,
        "retry_count": retry_count,
        "n_quality_reports": len(reports),
        "quality_actions": [r["action"] for r in reports],
        "quality_reports": reports,
        # True when at least one report came from a real LLM diagnosis.
        "llm_reviewed": any(not r["synthetic_pass"] for r in reports),
        # Advisory mode retries only hard failures, so retry>0 + success means
        # the quality loop recovered a hard failure.
        "hard_failure_recovered": bool(retry_count > 0 and success),
        "quality_review_error": state.get("_quality_review_error"),
        "best": best_metrics_snapshot(wf),
        "elapsed_seconds": round(elapsed, 2),
        "errors": (list(getattr(wf, "errors", []) or []) if wf is not None else ["no_workflow_result"]),
    }


def run_pa_task(
    runner: Any,
    task: dict[str, Any],
    *,
    session_id: str,
    turn_timeout: int = 3600,
    turn_observer: Any | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Feed ``params_by_turn`` turn-by-turn through ``runner.run_form``.

    A fresh ``SessionMemory`` is installed for the duration of the task so
    multi-turn context matches CLI behaviour without leaking state across
    tasks. ``turn_observer`` (optional) receives ``before_turn(turn_index)``
    and ``after_turn(record)`` callbacks — used by the backend-comparison
    driver to attach per-turn LLM usage deltas.

    Returns ``(turn_records, errors)``; the task aborts on the first turn that
    raises (remaining turns would inherit a broken session anyway).
    """
    from agent_core.session_memory import SessionMemory

    runner.memory = SessionMemory()
    turns: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, params in enumerate(task["params_by_turn"], start=1):
        if turn_observer is not None:
            turn_observer.before_turn(i)
        started = time.monotonic()
        try:
            with _turn_time_limit(turn_timeout):
                state = runner.run_form(
                    params,
                    session_id=session_id,
                    explicit_workflow=task["workflow"],
                    user_text="",
                )
        except TurnTimeout as exc:
            errors.append(f"turn {i}: timeout ({exc})")
            turns.append({
                "turn": i, "success": False, "retry_count": 0,
                "n_quality_reports": 0, "quality_actions": [], "quality_reports": [],
                "llm_reviewed": False, "hard_failure_recovered": False,
                "quality_review_error": None, "best": None,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "errors": ["timeout"],
            })
            break
        except Exception as exc:  # noqa: BLE001 - record and move to next task
            errors.append(f"turn {i}: {type(exc).__name__}: {exc}")
            turns.append({
                "turn": i, "success": False, "retry_count": 0,
                "n_quality_reports": 0, "quality_actions": [], "quality_reports": [],
                "llm_reviewed": False, "hard_failure_recovered": False,
                "quality_review_error": None, "best": None,
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "errors": [f"{type(exc).__name__}: {exc}"],
            })
            break
        rec = extract_turn_record(state, turn=i, elapsed=time.monotonic() - started)
        if turn_observer is not None:
            turn_observer.after_turn(rec)
        turns.append(rec)
    return turns, errors


def build_task_record(
    task: dict[str, Any],
    arm: str,
    turns: list[dict[str, Any]],
    errors: list[str],
    *,
    session_id: str,
    elapsed: float,
) -> dict[str, Any]:
    """Aggregate per-turn records into one (task, arm) JSONL record."""
    action_counts: dict[str, int] = {}
    for t in turns:
        for a in t.get("quality_actions", []):
            action_counts[a] = action_counts.get(a, 0) + 1
    success = bool(turns) and not errors and all(t["success"] for t in turns)
    return {
        "task_id": task["task_id"],
        "arm": arm,
        "quality_review_enabled": ARM_ENABLED[arm],
        "workflow": task["workflow"],
        "n_turns": len(task["params_by_turn"]),
        "turns_executed": len(turns),
        "turns": turns,
        "total_retry_count": sum(t.get("retry_count", 0) for t in turns),
        "hard_failure_recoveries": sum(1 for t in turns if t.get("hard_failure_recovered")),
        "quality_action_counts": action_counts,
        "final_success": turns[-1]["success"] if turns else False,
        "all_turns_success": all(t["success"] for t in turns) if turns else False,
        "success": success,  # resume key
        "elapsed_seconds": round(elapsed, 2),
        "session_id": session_id,
        "errors": errors,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tasks", default=None, help="comma-separated PA numbers (default: all)")
    parser.add_argument("--limit", type=int, default=None, help="max number of (task, arm) jobs")
    parser.add_argument("--resume", action="store_true", help="skip (task_id, arm) already successful")
    parser.add_argument("--dry-run", action="store_true", help="list jobs and exit")
    parser.add_argument("--timeout", type=int, default=3600, help="per-turn timeout in seconds")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    tasks = load_pa_tasks()
    if args.tasks:
        wanted = {t.strip().upper().replace("PA_", "") for t in args.tasks.split(",")}
        tasks = [t for t in tasks if t["pa"] in wanted]

    jobs = [(task, arm) for task in tasks for arm in ARMS]
    if args.resume:
        done = load_successful_keys(args.output, ("task_id", "arm"))
        jobs = [(t, a) for (t, a) in jobs if (t["task_id"], a) not in done]
    if args.limit is not None:
        jobs = jobs[: args.limit]

    if args.dry_run:
        for task, arm in jobs:
            print(f"{task['task_id']}\t{task['workflow']}\t{arm}\tturns={len(task['params_by_turn'])}")
        print(f"# {len(jobs)} runs ({len(tasks)} tasks x {len(ARMS)} arms)")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    runners: dict[str, Any] = {}  # one runner per arm, built lazily

    n_ok = n_fail = 0
    total = len(jobs)
    batch_start = time.monotonic()
    for i, (task, arm) in enumerate(jobs, start=1):
        session_id = f"fig6q_{task['pa']}_{arm}"
        print(f"[{i}/{total}] {task['task_id']} ({task['workflow']}) arm={arm} ...", flush=True)
        if arm not in runners:
            runners[arm] = build_runner(quality_review_enabled=ARM_ENABLED[arm])
        started = time.monotonic()
        turns, errors = run_pa_task(
            runners[arm],
            task,
            session_id=session_id,
            turn_timeout=args.timeout,
        )
        record = build_task_record(
            task, arm, turns, errors,
            session_id=session_id, elapsed=time.monotonic() - started,
        )
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        if record["success"]:
            n_ok += 1
        else:
            n_fail += 1
        status = "OK" if record["success"] else f"FAIL({'; '.join(errors) or 'turn_failed'})"
        print(
            f"      -> {status} in {record['elapsed_seconds']:.1f}s "
            f"(retries={record['total_retry_count']}, actions={record['quality_action_counts']})",
            flush=True,
        )

    wall = time.monotonic() - batch_start
    print(f"\nDone: {n_ok} succeeded, {n_fail} failed, {total} total, wall {wall / 60:.1f} min")
    print(f"Records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
