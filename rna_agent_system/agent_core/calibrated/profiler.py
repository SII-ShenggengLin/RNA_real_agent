"""CapabilityProfiler: anchor-set measurement -> CASF grading -> SelfModel.

Two deterministic backends (no LLM anywhere in this module):

- ``e1_driver``: structural oracles on aptamer anchor sets. Delegates scoring
  to the pre-registered E1 driver as a subprocess (zero modification to the
  driver), then grades the resulting JSONL rows with ``profiling_metrics``.
- ``deterministic``: pure-Python metric oracles (e.g. GC/U content) scored
  directly over anchor-set entries; used by tests and by E3 trusted-oracle
  tasks.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from agent_core.calibrated import profiling_metrics as pm
from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    EvidencePointer,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.file_manager import PROJECT_ROOT

_LOGGER = logging.getLogger(__name__)

E1_DRIVER = PROJECT_ROOT / "experiments" / "run_e1_capability_profiling.py"

# Oracle keys used in the E1 Part A ``raw`` block.
STRUCTURAL_ORACLE_KEYS = (
    "rhofold_mean_plddt",
    "proteinx_ipTM",
    "egarps_native_probability",
)

# Built-in deterministic scorers: sequence -> float.
DETERMINISTIC_SCORERS: dict[str, Callable[[str], float]] = {
    "gc_content": lambda seq: (seq.count("G") + seq.count("C")) / max(len(seq), 1),
    "u_content": lambda seq: seq.count("U") / max(len(seq), 1),
    "purine_content": lambda seq: (seq.count("A") + seq.count("G")) / max(len(seq), 1),
}


class ProfileRequest(BaseModel):
    """One profiling job: grade *capabilities* of *oracle* on an anchor set."""

    oracle: str
    task_type: str
    target_family: str
    anchor_set: str  # path to anchor-set JSON (ANCHORS.md §2 schema)
    capabilities: list[str] = Field(default_factory=lambda: ["screening", "ranking"])
    backend: Literal["e1_driver", "deterministic"] = "deterministic"
    targets: list[str] | None = None  # optional per-target filter (e1_driver)
    work_dir: str | None = None  # subprocess outputs (e1_driver); required there
    skip_docking: bool = True


class CapabilityProfiler:
    """Deterministic profiler; writes results into a SelfModel with audit."""

    def __init__(
        self,
        self_model: SelfModel,
        *,
        audit: AuditTrail | None = None,
        scorers: dict[str, Callable[[str], float]] | None = None,
    ) -> None:
        self._self_model = self_model
        self._audit = audit
        self._scorers = dict(DETERMINISTIC_SCORERS)
        if scorers:
            self._scorers.update(scorers)

    def profile(self, request: ProfileRequest) -> CapabilityRecord:
        if request.backend == "e1_driver":
            record = self._profile_e1_driver(request)
        else:
            record = self._profile_deterministic(request)
        self._self_model.update(record)
        if self._audit is not None:
            self._audit.record(
                "profiling_run",
                {
                    "oracle": request.oracle,
                    "backend": request.backend,
                    "anchor_set": request.anchor_set,
                    "capabilities": request.capabilities,
                    "grades": {k: v.grade for k, v in record.capabilities.items()},
                },
            )
        return record

    # ------------------------------------------------------------------ backends

    def _profile_deterministic(self, request: ProfileRequest) -> CapabilityRecord:
        scorer = self._scorers.get(request.oracle)
        if scorer is None:
            raise KeyError(
                f"no deterministic scorer registered for oracle {request.oracle!r}; "
                f"available: {sorted(self._scorers)}"
            )
        entries = _load_entries(request.anchor_set, request.targets)
        rows = []
        for entry in entries:
            try:
                score = float(scorer(entry["sequence"].upper().replace("T", "U")))
                rows.append({**entry, "success": True, "raw": {request.oracle: score}})
            except Exception as exc:  # noqa: BLE001 - record and continue
                _LOGGER.warning("deterministic scoring failed id=%s err=%s", entry.get("id"), exc)
                rows.append({**entry, "success": False, "error": str(exc), "raw": {}})
        return self._grade_rows(request, rows, evidence_path=request.anchor_set)

    def _profile_e1_driver(self, request: ProfileRequest) -> CapabilityRecord:
        if request.oracle not in STRUCTURAL_ORACLE_KEYS:
            raise ValueError(
                f"e1_driver backend only profiles {STRUCTURAL_ORACLE_KEYS}, got {request.oracle!r}"
            )
        work_dir = Path(request.work_dir) if request.work_dir else None
        if work_dir is None:
            raise ValueError("e1_driver backend requires work_dir for subprocess outputs")
        work_dir.mkdir(parents=True, exist_ok=True)
        out_a = work_dir / "part_a.jsonl"
        out_b = work_dir / "part_b.jsonl"
        cmd = [
            sys.executable,
            str(E1_DRIVER),
            "--anchor-set",
            request.anchor_set,
            "--output-a",
            str(out_a),
            "--output-b",
            str(out_b),
            "--resume",
        ]
        if request.skip_docking:
            cmd.append("--skip-docking")
        if request.targets:
            cmd += ["--targets", ",".join(request.targets)]
        _LOGGER.info("e1_driver profiling run: %s", " ".join(cmd))
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"E1 driver exited {proc.returncode}; stderr tail:\n{proc.stderr[-2000:]}"
            )
        rows = _read_jsonl(out_a)
        return self._grade_rows(request, rows, evidence_path=str(out_a))

    # ------------------------------------------------------------------ grading

    def _grade_rows(
        self, request: ProfileRequest, rows: list[dict[str, Any]], *, evidence_path: str
    ) -> CapabilityRecord:
        now = datetime.now(timezone.utc).isoformat()
        evidence = [EvidencePointer(kind="jsonl", path=evidence_path, note="profiling rows")]
        capabilities: dict[str, CapabilityAssessment] = {}
        for capability in request.capabilities:
            if capability == "screening":
                metrics = pm.screening_metrics(rows, request.oracle)
            elif capability == "ranking":
                metrics = pm.ranking_metrics(rows, request.oracle)
            else:
                capabilities[capability] = CapabilityAssessment(
                    grade="unprofiled", evidence=evidence, profiled_at=now
                )
                continue
            grade = pm.grade_capability(capability, metrics)
            metrics = {k: v for k, v in metrics.items() if v == v}  # drop NaN for JSON
            capabilities[capability] = CapabilityAssessment(
                grade=grade or "unprofiled",
                confidence=1.0 if grade else 0.0,
                metrics=metrics,
                evidence=evidence,
                profiled_at=now,
            )
        return CapabilityRecord(
            oracle=request.oracle,
            task_type=request.task_type,
            target_family=request.target_family,
            capabilities=capabilities,
        )


def _load_entries(anchor_set: str, targets: list[str] | None) -> list[dict[str, Any]]:
    payload = json.loads(Path(anchor_set).read_text(encoding="utf-8"))
    entries = payload.get("entries", [])
    if targets:
        wanted = set(targets)
        entries = [e for e in entries if e.get("target") in wanted]
    return entries


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
