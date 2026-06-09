"""CLI entry smoke tests for siRNA workflow (subprocess; no microservices when stubs are used)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
@pytest.mark.slow
def test_cli_sirna_workflow_json_smoke():
    env = {**os.environ, "PYTHONPATH": str(APP_ROOT)}
    cmd = [
        sys.executable,
        str(APP_ROOT / "cli" / "sirna_workflow.py"),
        "--mode",
        "generic",
        "--target-sequence",
        "AUGC" * 30,
        "--candidate-count",
        "3",
        "--output-json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(APP_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert data["task_type"] == "sirna"
    assert data.get("best_candidate") is not None


@pytest.mark.slow
def test_cli_sirna_workflow_text_output():
    env = {**os.environ, "PYTHONPATH": str(APP_ROOT)}
    cmd = [
        sys.executable,
        str(APP_ROOT / "cli" / "sirna_workflow.py"),
        "--mode",
        "generic",
        "--target-sequence",
        "AUGC" * 30,
        "--candidate-count",
        "2",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(APP_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert proc.returncode == 0, proc.stderr
    assert "task_id:" in proc.stdout
    assert "success:" in proc.stdout
    assert "candidates:" in proc.stdout


def test_cli_sirna_missing_target_error():
    env = {**os.environ, "PYTHONPATH": str(APP_ROOT)}
    cmd = [
        sys.executable,
        str(APP_ROOT / "cli" / "sirna_workflow.py"),
        "--mode",
        "generic",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(APP_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "Error" in proc.stderr
