#!/usr/bin/env python3
"""Shared helper for PA end-to-end regression drivers using the form-driven CLI.

Each PA driver now writes per-turn parameters to JSON files and invokes
``cli/form_chat.py --workflow <name> --params-file <path> --session-id <id>``
for every turn. This removes the old pexpect/pexpect-based natural-language
clarification loop.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent


def write_params(path: Path, params: dict[str, Any]) -> None:
    """Serialize form parameters to JSON, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    with path.open("w", encoding="utf-8") as f:
        json.dump(params, f, ensure_ascii=False, indent=2)


def run_form_round(
    workflow: str,
    params: dict[str, Any],
    *,
    session_id: str,
    turn: int,
    log_dir: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a single form-driven turn via ``cli/form_chat.py``.

    Parameters are written to a temporary JSON file and the CLI is invoked
    non-interactively. stdout/stderr are tee'd to a per-turn log file.
    """
    import json

    if log_dir is None:
        log_dir = PROJECT_ROOT / "workspace" / "sessions" / session_id
    log_dir.mkdir(parents=True, exist_ok=True)

    params_file = log_dir / f"pa_params_turn{turn}.json"
    write_params(params_file, params)

    log_file = log_dir / f"pa_turn{turn}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "cli" / "form_chat.py"),
        "--workflow",
        workflow,
        "--params-file",
        str(params_file),
        "--session-id",
        session_id,
    ]

    print(f"[PA driver] Turn {turn}: {' '.join(cmd)}")
    with log_file.open("w", encoding="utf-8", errors="replace") as log_fp:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        log_fp.write(proc.stdout)
        sys.stdout.write(proc.stdout)
        sys.stdout.flush()

    if proc.returncode != 0:
        print(f"[PA driver] Turn {turn} failed with exit code {proc.returncode}. See {log_file}")
    else:
        print(f"[PA driver] Turn {turn} completed. Log: {log_file}")
    return proc


def run_form_workflow(
    workflow: str,
    params_by_turn: list[dict[str, Any]],
    *,
    session_id: str,
    log_dir: Path | None = None,
) -> int:
    """Run all turns for a PA benchmark and return the number of failed turns."""
    failed = 0
    for turn, params in enumerate(params_by_turn, start=1):
        proc = run_form_round(
            workflow,
            params,
            session_id=session_id,
            turn=turn,
            log_dir=log_dir,
        )
        if proc.returncode != 0:
            failed += 1
    return failed
