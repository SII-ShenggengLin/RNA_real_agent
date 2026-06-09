"""Baseline dataset + shared stub evaluation (regression anchor for new tools/workflows)."""

from __future__ import annotations

from pathlib import Path

from agent_core.workflow_baseline_eval import (
    DEFAULT_SAMPLES_PATH,
    evaluate_sample,
    load_baseline_samples,
    run_baseline_batch)
from agent_core.workflows.mrna_sequence_scoring import MrnaSequenceScoringInput


def test_load_default_baseline_samples():
    rows = load_baseline_samples(DEFAULT_SAMPLES_PATH)
    assert len(rows) >= 3
    assert all("sequence" in r and "id" in r for r in rows)


def test_run_baseline_batch_produces_scores_and_stable_ordering():
    rows = run_baseline_batch()
    assert len(rows) >= 3
    assert all(r["success"] for r in rows)
    scores = [r["best_total_score"] for r in rows if r["best_total_score"] is not None]
    assert len(scores) == len(rows)
    # Stub fold favors longer sequences slightly differently; scores must be finite and comparable.
    assert len(set(round(s, 6) for s in scores)) >= 1


def test_compare_candidates_within_sample():
    inp = MrnaSequenceScoringInput(
        sequences=[
            "AAAAAAAAUGCCCCCCCCCCUUUUUUUUUUUUUUAAAAAAAAAA",
            "GCCGCCGCCGCC",
        ])
    row = evaluate_sample("pair", inp)
    assert row["success"]
    assert len(row["ordered_scores"]) == 2
    assert row["ordered_scores"][0]["rank"] == 1


def test_samples_json_path_exists():
    p = Path(DEFAULT_SAMPLES_PATH)
    assert p.is_file()
    assert "examples" in p.parts and "data" in p.parts


def test_examples_batch_demo_script_exit_zero():
    import json
    import os
    import subprocess
    import sys

    app_root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(app_root)}
    proc = subprocess.run(
        [sys.executable, str(app_root / "examples" / "mrna_workflow_batch_demo.py"), "--json"],
        cwd=str(app_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120)
    assert proc.returncode == 0, proc.stderr
    rows = json.loads(proc.stdout)
    assert isinstance(rows, list) and len(rows) >= 3
    assert all(r["success"] for r in rows)
