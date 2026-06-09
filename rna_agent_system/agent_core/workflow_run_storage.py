"""Minimal on-disk artifacts for workflow runs (JSON under ``workspace/workflow_runs/``).

Reuses ``file_manager.PROJECT_ROOT`` / ``workspace`` layout; no external DB.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from agent_core.file_manager import PROJECT_ROOT
from agent_core.workflow_models import ToolCallRecord, WorkflowResult

_LOGGER = logging.getLogger(__name__)

WORKFLOW_RUNS_SEGMENT = Path("workspace") / "workflow_runs"
SCHEMA_VERSION = "workflow_run_v1"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_task_slug(task_id: str) -> str:
    """Filesystem-safe fragment derived from ``task_id``."""

    s = re.sub(r"[^\w.\-]+", "_", task_id.strip())[:96]
    return s or "task"


def resolve_runs_parent(artifact_runs_parent: Optional[str]) -> Path:
    """Parent directory that will contain per-run folders (default: ``workspace/workflow_runs``)."""

    if artifact_runs_parent:
        p = Path(artifact_runs_parent)
        return p if p.is_absolute() else (PROJECT_ROOT / p)
    return PROJECT_ROOT / WORKFLOW_RUNS_SEGMENT


def allocate_run_directory(task_id: str, *, artifact_runs_parent: Optional[str] = None) -> tuple[str, Path]:
    """Return ``(relative_workspace_path, absolute_path)`` for a new run folder."""

    parent = resolve_runs_parent(artifact_runs_parent)
    slug = sanitize_task_slug(task_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder_name = f"{stamp}_{slug}_{uuid4().hex[:8]}"
    abs_dir = parent / folder_name
    abs_dir.mkdir(parents=True, exist_ok=True)
    try:
        rel = abs_dir.relative_to(PROJECT_ROOT)
    except ValueError:
        rel = Path("workspace") / "workflow_runs" / folder_name
        _LOGGER.warning(
            "artifact_runs_parent outside PROJECT_ROOT; relative path fallback=%s",
            rel,
        )
    rel_posix = rel.as_posix()
    return rel_posix, abs_dir


def _walk_workspace_paths(val: Any, acc: List[str]) -> None:
    if isinstance(val, str):
        if val.startswith("workspace/") or val.startswith("workspace\\"):
            acc.append(val.replace("\\", "/"))
        return
    if isinstance(val, dict):
        for v in val.values():
            _walk_workspace_paths(v, acc)
        return
    if isinstance(val, list):
        for v in val:
            _walk_workspace_paths(v, acc)


def collect_workspace_paths_from_trace(trace: Sequence[ToolCallRecord]) -> List[str]:
    paths: List[str] = []
    for rec in trace:
        _walk_workspace_paths(dict(rec.artifacts), paths)
        _walk_workspace_paths(dict(rec.metrics), paths)
    seen: set[str] = set()
    out: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def copy_tool_artifacts_into_run(
    trace: Sequence[ToolCallRecord],
    run_abs: Path,
    *,
    max_files: int = 64,
) -> List[str]:
    """Copy referenced ``workspace/*`` files into ``run_abs/artifacts/``.

    Best-effort; skips missing paths. Returns relative paths written under the run dir.
    """

    art_dir = run_abs / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    rel_refs = collect_workspace_paths_from_trace(trace)
    written: List[str] = []
    for ref in rel_refs[:max_files]:
        src = PROJECT_ROOT / ref if not Path(ref).is_absolute() else Path(ref)
        if not src.is_file():
            continue
        dest_name = src.name
        dest = art_dir / dest_name
        if dest.exists():
            stem, suf = dest_name, ""
            if "." in dest_name:
                stem, suf = dest_name.rsplit(".", 1)
                suf = "." + suf
            dest = art_dir / f"{stem}_{uuid4().hex[:6]}{suf}"
        shutil.copy2(src, dest)
        try:
            written.append(dest.relative_to(run_abs).as_posix())
        except ValueError:
            written.append(str(dest.name))
    return written


def build_public_summary(wf: WorkflowResult) -> str:
    """One-line summary for APIs and paper-style logs."""

    ts = wf.task_id
    if not wf.success:
        err = wf.errors[0] if wf.errors else "failed"
        return f"task_id={ts} success=false error={err[:120]}"
    bc = wf.best_candidate
    score = None
    if bc and "total_score" in bc.scores:
        score = float(bc.scores["total_score"])
    n = len(wf.all_candidates)
    nw = len(wf.errors)
    score_s = f"{score:.4f}" if score is not None else "na"
    return (
        f"task_id={ts} success=true best_total_score={score_s} candidates={n} tool_warnings={nw}"
    )


def dump_result_document(
    wf: WorkflowResult,
    *,
    workflow_input: Dict[str, Any],
    operational_summary: str,
    started_at: datetime,
    completed_at: datetime,
    audit_http_request: Optional[Dict[str, Any]],
    artifact_copies: List[str],
    execution_log: Optional[List[Dict[str, Any]]] = None,
    bmc_trace: Optional[List[Dict[str, Any]]] = None,
    diagnosis_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Full serializable audit record (written to ``result.json``)."""

    trace_json = [rec.model_dump(mode="json") for rec in wf.trace]
    fatal = list(wf.errors) if not wf.success else []
    tool_warnings = list(wf.errors) if wf.success else []
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": wf.task_id,
        "success": wf.success,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "created_at": wf.created_at.isoformat(),
        "public_summary": wf.public_summary,
        "summary": operational_summary,
        "fatal_errors": fatal,
        "tool_warnings": tool_warnings,
        "workflow_input": workflow_input or getattr(wf, '_workflow_input', None) or {},
        "http_request_audit": audit_http_request,
        "_execution_log": getattr(wf, '_execution_log', None),
        "best_candidate": wf.best_candidate.model_dump(mode="json") if wf.best_candidate else None,
        "candidates": [c.model_dump(mode="json") for c in wf.all_candidates],
        "tool_records": trace_json,
        "ranking": {
            "score_key": "total_score",
            "descending": True,
            "ordered_candidate_ids": [c.id for c in wf.all_candidates],
        },
        "artifact_file_copies": artifact_copies,
        "audit_trail": {
            "execution_log": execution_log or [],
            "bmc_trace": bmc_trace or [],
            "diagnosis_history": diagnosis_history or [],
        },
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def persist_workflow_run(
    wf: WorkflowResult,
    inp_dict: Dict[str, Any],
    *,
    operational_summary: str,
    started_at: datetime,
    completed_at: datetime,
    artifact_runs_parent: Optional[str] = None,
    audit_http_request: Optional[Dict[str, Any]] = None,
    copy_artifacts: bool = True,
    execution_log: Optional[List[Dict[str, Any]]] = None,
    bmc_trace: Optional[List[Dict[str, Any]]] = None,
    diagnosis_history: Optional[List[Dict[str, Any]]] = None,
) -> tuple[str, str, str]:
    """Write ``request.json``, ``result.json``, optional artifact copies.

    Returns ``(run_dir_relative, request_path_relative, result_path_relative)``.
    """

    rel_dir, abs_dir = allocate_run_directory(wf.task_id, artifact_runs_parent=artifact_runs_parent)
    request_path = abs_dir / "request.json"
    result_path = abs_dir / "result.json"

    req_payload = {
        "schema_version": SCHEMA_VERSION,
        "task_id": wf.task_id,
        "recorded_at": _utc_iso(),
        "workflow_input": inp_dict,
        "http_request_audit": audit_http_request,
    }
    write_json(request_path, req_payload)

    copies: List[str] = []
    if copy_artifacts and wf.trace:
        copies = copy_tool_artifacts_into_run(wf.trace, abs_dir)

    body = dump_result_document(
        wf,
        workflow_input=inp_dict,
        operational_summary=operational_summary,
        started_at=started_at,
        completed_at=completed_at,
        audit_http_request=audit_http_request,
        artifact_copies=copies,
        execution_log=execution_log,
        bmc_trace=bmc_trace,
        diagnosis_history=diagnosis_history,
    )
    write_json(result_path, body)
    rel_req = Path(rel_dir) / "request.json"
    rel_res = Path(rel_dir) / "result.json"
    _LOGGER.info(
        "workflow_run_persisted task_id=%s dir=%s result=%s",
        wf.task_id,
        rel_dir,
        rel_res.as_posix(),
    )
    return rel_dir, rel_req.as_posix(), rel_res.as_posix()


def maybe_persist_workflow_run(
    wf: WorkflowResult,
    inp_dict: Dict[str, Any],
    *,
    enabled: bool = True,
    operational_summary: str = "",
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    artifact_runs_parent: Optional[str] = None,
    audit_http_request: Optional[Dict[str, Any]] = None,
    copy_artifacts: bool = True,
    execution_log: Optional[List[Dict[str, Any]]] = None,
    bmc_trace: Optional[List[Dict[str, Any]]] = None,
    diagnosis_history: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Persist *wf* to disk when *enabled* is True; otherwise no-op.

    Side-effect: mutates *wf* in place, setting ``run_artifact_dir`` and
    ``run_result_json_path`` when persistence succeeds.
    """
    if not enabled:
        _LOGGER.debug("workflow_persist_skip task_id=%s", wf.task_id)
        return
    now = datetime.now(timezone.utc)
    sa = started_at or now
    ca = completed_at or wf.completed_at or now
    try:
        _, _, res_path = persist_workflow_run(
            wf,
            inp_dict,
            operational_summary=operational_summary or wf.summary,
            started_at=sa,
            completed_at=ca,
            artifact_runs_parent=artifact_runs_parent,
            audit_http_request=audit_http_request,
            copy_artifacts=copy_artifacts,
            execution_log=execution_log,
            bmc_trace=bmc_trace,
            diagnosis_history=diagnosis_history,
        )
        wf.run_result_json_path = res_path
        wf.run_artifact_dir = str(Path(res_path).parent.as_posix())
    except OSError as exc:
        _LOGGER.warning("workflow_persist_failed task_id=%s err=%s", wf.task_id, exc)
