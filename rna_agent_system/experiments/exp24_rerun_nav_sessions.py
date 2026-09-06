#!/usr/bin/env python3
"""Exp 24 re-run — navigation-session replacement pass (2026-09-06).

The fresh campaign (241/241) revealed a platform defect: the GenNav-λ probe
phase submits its capability calls through ThreadPoolExecutor worker threads,
and the session id (a contextvars.ContextVar) does not follow thread-pool
submissions — 184 probe-phase tool_calls (64 LinearDesign + 60 CAI + 60
LinearFold) landed in the platform audit trail without their session stamp,
failing the analyzer's quiet-trail assertion.

FIX (agent_core/workflows/mrna_cds_design.py, same day): the parent context
is copied per submission (``ctx.run``), so every probe-thread call is
stamped. This driver re-runs the six corpus sessions that contain a
navigation turn under the FIXED code, appending their records to the
campaign's lane/pa jsonl files (latest-record-wins semantics, exp24_r3
session prefix — the campaign's registered retry convention), after which
``exp24_audit_gate_stats.py`` freezes the corpus from the records as
originally designed.

Two workflow-exclusive chains run in parallel (mrna_cds: CDS 009 → PA_015 →
PA_034; full_length: FULL 009 → PA_024 → PA_036) — same-workflow sessions
never overlap, preserving the gate-event attribution the analyzer requires.

Usage: PYTHONPATH="$(pwd):$PYTHONPATH" RNADA_CAPGATE=advisory \
    python experiments/exp24_rerun_nav_sessions.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiments"))

import exp24_production_campaign as camp  # noqa: E402

RESULTS_DIR = camp.RESULTS_DIR
PREFIX = "exp24_r3"

CHAIN_CDS = [("task", "01_mrna_cds_design_009"), ("pa", "015"), ("pa", "034")]
CHAIN_FL = [("task", "02_full_length_mrna_design_009_ovalbumin"), ("pa", "024"), ("pa", "036")]


def _tasks_by_id() -> dict:
    return {t["task_id"]: t for t in camp.load_tasks()}


def _pa_meta(pa_id: str) -> dict:
    registry = json.loads(camp.PA_BENCHMARKS.read_text(encoding="utf-8"))
    entry = registry[pa_id]
    return {
        "workflow": entry["workflow"],
        "n_turns": len(entry.get("params_by_turn", [])),
    }


def _chain(kind_items: list, lane_file: Path, pa_file: Path) -> None:
    tasks = _tasks_by_id()
    for kind, ident in kind_items:
        started = time.monotonic()
        if kind == "task":
            task = tasks[ident]
            rec = camp.run_suite_task(task, session_prefix=PREFIX)
            camp.append_record(lane_file, rec)
            print(f"[{threading.current_thread().name}] task {ident}: "
                  f"success={rec.get('success')} in {time.monotonic()-started:.0f}s",
                  flush=True)
        else:
            meta = _pa_meta(ident)
            rec = camp.run_pa(ident, workflow=meta["workflow"],
                              n_turns=meta["n_turns"], session_prefix=PREFIX)
            camp.append_record(pa_file, rec)
            print(f"[{threading.current_thread().name}] pa {ident}: "
                  f"success={rec.get('success')} in {time.monotonic()-started:.0f}s",
                  flush=True)


def main() -> int:
    lane_cds = RESULTS_DIR / "lane_01_mrna_cds_design.jsonl"
    lane_fl = RESULTS_DIR / "lane_02_full_length_mrna_design.jsonl"
    # the campaign's parallel driver writes pa batches per worker; find or
    # create the files the summary globs (pa_batch*.jsonl)
    pa_files = sorted(RESULTS_DIR.glob("pa_batch*.jsonl"))
    pa_file = pa_files[0] if pa_files else RESULTS_DIR / "pa_batch.jsonl"

    t1 = threading.Thread(target=_chain, args=(CHAIN_CDS, lane_cds, pa_file),
                          name="chain-cds")
    t2 = threading.Thread(target=_chain, args=(CHAIN_FL, lane_fl, pa_file),
                          name="chain-fl")
    t1.start(); t2.start()
    t1.join(); t2.join()
    print("[rerun-nav] both chains complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
