#!/usr/bin/env python3
"""Consolidated driver for PA_006–PA_024 form-driven regression benchmarks.

Each benchmark is defined by an entry in ``pa_benchmarks.json``.  The driver
loads the requested PA number, derives a session ID, and invokes the shared
form workflow runner for every turn.

Usage:
    python run_pa_test.py 006
    python run_pa_test.py 020 --session-id pa020_custom_20260716_120000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from run_pa_form import run_form_workflow

PROJECT_ROOT = Path(__file__).resolve().parent
BENCHMARKS_PATH = PROJECT_ROOT / "pa_benchmarks.json"


def load_benchmarks() -> dict[str, dict[str, Any]]:
    """Load the PA benchmark registry."""
    data = BENCHMARKS_PATH.read_text(encoding="utf-8")
    return json.loads(data)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a single PA end-to-end regression benchmark.",
    )
    parser.add_argument(
        "pa",
        metavar="PA",
        help="Benchmark number, e.g. 006 or 024.",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Override the auto-generated session ID.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Override the default log directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    benchmarks = load_benchmarks()

    pa = args.pa
    if pa not in benchmarks:
        print(f"[PA driver] Unknown benchmark: PA_{pa}", file=sys.stderr)
        print(f"[PA driver] Available: {', '.join(sorted(benchmarks))}", file=sys.stderr)
        return 2

    entry = benchmarks[pa]
    workflow: str = entry["workflow"]
    params_by_turn: list[dict[str, Any]] = entry["params_by_turn"]

    session_id = args.session_id or f"pa{pa}_{time.strftime('%Y%m%d_%H%M%S')}"
    log_dir = args.log_dir or PROJECT_ROOT / "workspace" / "sessions" / session_id

    print(f"[PA_{pa} driver] workflow={workflow} turns={len(params_by_turn)} session={session_id}")
    failed = run_form_workflow(
        workflow,
        params_by_turn,
        session_id=session_id,
        log_dir=log_dir,
    )
    print(f"[PA_{pa} driver] Done. Failed turns: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
