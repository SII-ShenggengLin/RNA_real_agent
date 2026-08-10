#!/usr/bin/env python3
"""Fig 2 driver: run all RNA-BioBench-Platform tasks and collect quality records.

Implements the runbook in `docs/MANUSCRIPT.md` §4:
- iterates the 210 Platform task JSONs,
- invokes the form-driven CLI once per task (services auto-start via pre-flight),
- parses the saved ``workflow_results_*.json`` from the session workspace,
- appends one compact record per run to ``experiments/results/fig2_platform_quality.jsonl``.

Usage (from ``rna_agent_system/``):

    PYTHONPATH="$(pwd):$PYTHONPATH" python experiments/run_platform_quality_benchmark.py \
        [--workflow NAME] [--limit N] [--resume] [--dry-run] [--timeout SECONDS]

Options:
    --workflow NAME   only run tasks of one workflow directory (e.g. 03_mrna_sequence_scoring
                      or its workflow name mrna_sequence_scoring)
    --limit N         run at most N tasks (after filtering)
    --resume          skip task_ids that already have a successful record in the output file
    --dry-run         list the tasks that would run, then exit
    --timeout SEC     per-task subprocess timeout (default: 1800; GPU workflows may need 3600)
    --output PATH     output JSONL path (default: experiments/results/fig2_platform_quality.jsonl)

Notes:
- Records are appended; analysis should take the *latest* record per task_id.
- A failed task is recorded with ``success=false`` and an ``error`` tag; the driver
  never aborts the batch because of a single task.
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
TASKS_ROOT = PROJECT_ROOT / "data" / "benchmarks" / "RNA-BioBench-Platform" / "tasks"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "results" / "fig2_platform_quality.jsonl"

# Workflows that rely on GPU-heavy microservices (ODesign / ProteinX / RhoFold / ...).
GPU_WORKFLOWS = {"rna_aptamer_design", "rna_tertiary_structure_design"}


def discover_tasks(workflow_filter: str | None) -> list[Path]:
    """Return sorted task JSON paths (excluding per-directory manifests)."""
    paths = sorted(
        p
        for p in TASKS_ROOT.glob("*/*.json")
        if p.name != "dataset_manifest.json"
    )
    if workflow_filter:
        paths = [
            p
            for p in paths
            if p.parent.name == workflow_filter
            or workflow_filter in p.parent.name
        ]
    return paths


def load_successful_task_ids(output_path: Path) -> set[str]:
    done: set[str] = set()
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
                done.add(rec["task_id"])
    return done


def find_results_file(session_dir: Path) -> Path | None:
    """Newest workflow_results_*.json written inside the session workspace."""
    candidates = sorted(
        session_dir.glob("workflow_results_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def trim_candidate(c: dict[str, Any], *, keep_sequence: bool) -> dict[str, Any]:
    """Keep the analysis-relevant fields of one candidate dict."""
    out: dict[str, Any] = {
        "rank": c.get("rank"),
        "id": c.get("id"),
        "source": c.get("source"),
        "total_length": c.get("total_length"),
        "total_score": c.get("total_score"),
        "scores": c.get("scores") or {},
        "metrics": c.get("metrics") or {},
        "metadata": c.get("metadata") or {},
    }
    if keep_sequence:
        out["sequence"] = c.get("sequence")
    # Drop bulky/derived metadata fields; keep the rest verbatim.
    out["metadata"] = {
        k: v for k, v in out["metadata"].items() if k not in {"structure", "dot_bracket"}
    }
    return out


def build_record(
    task: dict[str, Any],
    results: dict[str, Any] | None,
    *,
    session_id: str,
    exit_code: int,
    elapsed: float,
    error: str | None,
    keep_candidate_sequences: bool = False,
) -> dict[str, Any]:
    """Assemble the compact JSONL record for one run."""
    record: dict[str, Any] = {
        "task_id": task["task_id"],
        "workflow": task["workflow"],
        "category": task.get("category"),
        "description": task.get("description"),
        "evaluation_rubric": task.get("evaluation_rubric"),
        "session_id": session_id,
        "exit_code": exit_code,
        "elapsed_seconds": round(elapsed, 2),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "error": error,
        "success": False,
    }
    if results is None:
        return record

    record["success"] = bool(results.get("success"))
    record["candidate_count"] = results.get("candidate_count")
    record["summary"] = results.get("summary")
    record["retry_count"] = results.get("retry_count", 0)

    candidates = results.get("candidates") or []
    record["candidates"] = [
        trim_candidate(c, keep_sequence=keep_candidate_sequences) for c in candidates
    ]
    if results.get("best_candidate"):
        record["best_candidate"] = trim_candidate(results["best_candidate"], keep_sequence=True)
    else:
        record["best_candidate"] = None

    pf = results.get("pareto_frontier")
    record["pareto_frontier_size"] = len(pf) if isinstance(pf, list) else None

    bmc_trace = results.get("_bmc_trace") or []
    record["bmc_rounds"] = len(bmc_trace)
    if bmc_trace:
        record["bmc_trace"] = bmc_trace

    trace = results.get("trace") or []
    record["n_trace_steps"] = len(trace)
    record["tools_used"] = sorted({t.get("tool_name", "") for t in trace if t.get("tool_name")})
    expected = task.get("expected_tool_chain") or []
    record["tool_chain_match"] = (
        all(t in record["tools_used"] for t in expected) if expected else None
    )

    diagnosis = results.get("_diagnosis_history") or []
    record["quality_actions"] = [
        (d.get("quality_report") or {}).get("action") for d in diagnosis if isinstance(d, dict)
    ]
    if not record["success"] and record["error"] is None:
        record["error"] = "workflow_success_false"
    return record


def run_task_dict(
    task: dict[str, Any],
    *,
    timeout: int,
    env: dict[str, str],
    session_prefix: str = "fig2",
    keep_candidate_sequences: bool = False,
) -> dict[str, Any]:
    """Run one task dict (with ``task_id``, ``workflow``, ``input``) and return the record.

    Shared by the Fig-2 driver, the null generator, and the literature panels.
    """
    task_id: str = task["task_id"]
    session_id = f"{session_prefix}_{task_id}"
    session_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    params_file = session_dir / "params.json"
    params_file.write_text(json.dumps(task["input"], ensure_ascii=False, indent=2), encoding="utf-8")

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
                # Auto-answer the CLI's interactive "是否继续? (y/n)" prompt that
                # appears when a service pre-flight partially fails; answering "y"
                # lets the run proceed (a genuinely dead service fails the run
                # properly and is retried later via --resume). Without this, the
                # prompt's input() hits EOF and crashes the job in seconds.
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
        task,
        results,
        session_id=session_id,
        exit_code=exit_code,
        elapsed=elapsed,
        error=error,
        keep_candidate_sequences=keep_candidate_sequences,
    )


def run_one_task(
    task_path: Path,
    *,
    timeout: int,
    env: dict[str, str],
) -> dict[str, Any]:
    task = json.loads(task_path.read_text(encoding="utf-8"))
    return run_task_dict(task, timeout=timeout, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workflow", default=None, help="workflow directory or name filter")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="skip tasks with a successful record")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=1800, help="per-task timeout in seconds")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    task_paths = discover_tasks(args.workflow)
    if args.limit is not None:
        task_paths = task_paths[: args.limit]
    if args.resume:
        done = load_successful_task_ids(args.output)
        task_paths = [p for p in task_paths if json.loads(p.read_text(encoding="utf-8"))["task_id"] not in done]

    if args.dry_run:
        for p in task_paths:
            t = json.loads(p.read_text(encoding="utf-8"))
            print(f"{t['task_id']}\t{t['workflow']}\t{t.get('category')}")
        print(f"# {len(task_paths)} tasks")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"

    n_ok = n_fail = 0
    total = len(task_paths)
    batch_start = time.monotonic()
    for i, task_path in enumerate(task_paths, start=1):
        task_id = json.loads(task_path.read_text(encoding="utf-8"))["task_id"]
        workflow = json.loads(task_path.read_text(encoding="utf-8"))["workflow"]
        timeout = max(args.timeout, 3600) if workflow in GPU_WORKFLOWS else args.timeout
        print(f"[{i}/{total}] {task_id} (timeout={timeout}s) ...", flush=True)
        record = run_one_task(task_path, timeout=timeout, env=env)
        with args.output.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        status = "OK" if record["success"] else f"FAIL({record['error']})"
        if record["success"]:
            n_ok += 1
        else:
            n_fail += 1
        print(f"      -> {status} in {record['elapsed_seconds']:.1f}s", flush=True)

    wall = time.monotonic() - batch_start
    print(f"\nDone: {n_ok} succeeded, {n_fail} failed, {total} total, wall {wall/60:.1f} min")
    print(f"Records -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
