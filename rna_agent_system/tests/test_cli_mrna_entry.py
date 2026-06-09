"""CLI entry smoke tests (subprocess; no microservices needed)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.known_issue
def test_cli_mrna_workflow_json_smoke():
    env = {**os.environ, "PYTHONPATH": str(APP_ROOT)}
    cmd = [
        sys.executable,
        str(APP_ROOT / "cli" / "mrna_workflow.py"),
        "--sequence",
        "AUGCAUGCAUGCAU",
        "--json",
        "--constraints",
        '{}',
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(APP_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=90)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert data["task_id"]
    assert data["summary"]
    assert data.get("best_candidate") is not None
