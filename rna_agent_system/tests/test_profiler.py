"""Tests for agent_core.calibrated.profiler."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.profiler import CapabilityProfiler, ProfileRequest
from agent_core.calibrated.self_model import SelfModel


def _anchor_set(path: Path) -> Path:
    entries = []
    for i, seq in enumerate(("GCGCGC", "GCGCAU", "GCAUAU", "GUAUAU")):
        entries.append({
            "id": f"b{i}", "name": f"binder{i}", "target": "t1",
            "sequence": seq, "alphabet": "rna", "length_nt": len(seq),
            "kd_nm": float(10 ** i), "role": "binder", "ranking_eligible": True,
        })
    for i, seq in enumerate(("AUAUAU", "AUAAUA", "AAUUAA")):
        entries.append({
            "id": f"n{i}", "name": f"neg{i}", "target": "t1",
            "sequence": seq, "alphabet": "rna", "length_nt": len(seq),
            "kd_nm": None, "role": "negative",
        })
    payload = {"description": "test", "entries": entries, "n_entries": len(entries)}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_deterministic_backend_end_to_end(tmp_path):
    anchor = _anchor_set(tmp_path / "anchors.json")
    trail = AuditTrail(tmp_path / "audit.jsonl")
    model = SelfModel(audit=trail)
    profiler = CapabilityProfiler(model, audit=trail)

    rec = profiler.profile(ProfileRequest(
        oracle="gc_content",
        task_type="aptamer_affinity",
        target_family="t1",
        anchor_set=str(anchor),
        capabilities=["screening", "ranking"],
    ))

    assert rec.assessment("screening").grade == "verified"  # GC separates perfectly
    assert rec.assessment("screening").confidence == 1.0
    assert rec.assessment("ranking").grade == "verified"  # GC tracks Kd monotonically
    # SelfModel was updated and both audit events fired.
    got = model.query("gc_content", "aptamer_affinity", "t1")
    assert got.assessment("screening").grade == "verified"
    assert [e.event_type for e in trail.events()] == ["self_model_update", "profiling_run"]


def test_deterministic_backend_unknown_oracle(tmp_path):
    profiler = CapabilityProfiler(SelfModel())
    with pytest.raises(KeyError):
        profiler.profile(ProfileRequest(
            oracle="nope", task_type="t", target_family="f",
            anchor_set=str(_anchor_set(tmp_path / "a.json")),
        ))


def test_e1_driver_backend_validation():
    profiler = CapabilityProfiler(SelfModel())
    with pytest.raises(ValueError, match="only profiles"):
        profiler.profile(ProfileRequest(
            oracle="gc_content", task_type="t", target_family="f",
            anchor_set="x.json", backend="e1_driver", work_dir="w",
        ))
    with pytest.raises(ValueError, match="work_dir"):
        profiler.profile(ProfileRequest(
            oracle="proteinx_ipTM", task_type="t", target_family="f",
            anchor_set="x.json", backend="e1_driver",
        ))


def test_e1_driver_backend_subprocess(monkeypatch, tmp_path):
    anchor = _anchor_set(tmp_path / "anchors.json")

    def fake_run(cmd, **kwargs):
        out_a = Path(cmd[cmd.index("--output-a") + 1])
        rows = []
        for i, s in enumerate((0.9, 0.8, 0.85, 0.95)):
            rows.append({"id": f"b{i}", "target": "t1", "role": "binder",
                         "kd_nm": float(10 ** i), "ranking_eligible": True,
                         "success": True, "raw": {"proteinx_ipTM": s}})
        for i, s in enumerate((0.1, 0.2, 0.15)):
            rows.append({"id": f"n{i}", "target": "t1", "role": "negative",
                         "kd_nm": None, "success": True, "raw": {"proteinx_ipTM": s}})
        out_a.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    model = SelfModel()
    profiler = CapabilityProfiler(model)
    rec = profiler.profile(ProfileRequest(
        oracle="proteinx_ipTM",
        task_type="aptamer_affinity",
        target_family="t1",
        anchor_set=str(anchor),
        capabilities=["screening"],
        backend="e1_driver",
        work_dir=str(tmp_path / "work"),
    ))
    assert rec.assessment("screening").grade == "verified"
    assert rec.assessment("screening").evidence[0].path.endswith("part_a.jsonl")
