"""Minimal mRNA design workflow: candidates → tools → metrics → scoring → ranking."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.tool_registry import ToolRegistry
from agent_core.tool_runtime import ToolResult
from agent_core.workflow_models import Candidate, TaskState, WorkflowResult, sort_candidates_by_score
from agent_core.workflow_run_storage import build_public_summary, persist_mrna_workflow_run

from agent_core.sequence_utils import normalize_rna_sequence
from .mrna_scoring import MrnaScoreWeights, compute_mrna_metric_bundle, score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.mrna")


class MrnaWorkflowInput(BaseModel):
    """Inputs for ``MrnaWorkflow`` — pure scoring of existing sequence(s)."""

    model_config = ConfigDict(extra="forbid")

    sequence: Optional[str] = Field(default=None, description="Single RNA/DNA sequence string.")
    sequences: Optional[List[str]] = Field(default=None, description="Multiple sequences.")
    score_weights: Optional[MrnaScoreWeights] = None

    gc_tool_name: str = Field(
        default="compute_rna_sequence_gc_content",
        description="Registry name for GC tool (LangChain tool in agent_core.tools).",
    )
    fold_tool_name: str = Field(
        default="predict_rna_secondary_structure_with_linearfold",
        description="Registry name for folding / MFE tool.",
    )
    fold_service_url: str = Field(
        default="http://127.0.0.1:8015/fold",
        description="Passed to fold tool kwargs (LinearFold microservice).",
    )
    gc_service_url: str = Field(
        default="http://127.0.0.1:8020/gc-content",
        description="Passed to GC tool kwargs.",
    )

    run_gc_tool: bool = Field(default=True)
    run_fold_tool: bool = Field(default=True)

    persist_run: bool = Field(
        default=True,
        description="Write request.json / result.json under workspace/workflow_runs/<run_id>/.",
    )
    artifact_runs_parent: Optional[str] = Field(
        default=None,
        description="Optional parent directory for workflow_runs (absolute or repo-relative).",
    )
    copy_tool_artifacts_to_run: bool = Field(
        default=True,
        description="Copy referenced workspace files from tool artifacts into the run artifacts/ folder.",
    )


class MrnaWorkflow:
    """Orchestrate candidate generation and tool evaluation via ``ToolExecutor``.

    Workflow code does not invoke subprocess or HTTP directly; tools remain in ``agent_core.tools``.
    """

    def __init__(
        self,
        executor: ToolExecutor,
        *,
        weights: Optional[MrnaScoreWeights] = None,
    ):
        self.executor = executor
        self.weights = weights or MrnaScoreWeights()

    @classmethod
    def from_default_registry(
        cls,
        *,
        include_demo: bool = False,
        weights: Optional[MrnaScoreWeights] = None,
    ) -> MrnaWorkflow:
        """Build workflow with ``build_default_tool_registry()`` + executor."""

        reg = build_default_tool_registry(include_demo=include_demo)
        return cls(ToolExecutor(reg), weights=weights)

    def run(
        self,
        inp: MrnaWorkflowInput,
        *,
        task_id: Optional[str] = None,
        audit_http_request: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc)
        inp_dict = inp.model_dump(mode="json")

        raw_seqs: List[str] = []
        if inp.sequences:
            raw_seqs = [normalize_rna_sequence(s) for s in inp.sequences if s]
        elif inp.sequence:
            one = normalize_rna_sequence(inp.sequence)
            if one:
                raw_seqs = [one]
        _LOGGER.info("mrna_scoring input_seqs=%d candidates=%d", len(inp.sequences or []) + (1 if inp.sequence else 0), len(raw_seqs))
        candidates = [
            Candidate(sequence=s, sequence_type="mrna", source="mrna:direct", metadata={"generator": "normalize"})
            for s in raw_seqs if s
        ]

        task_kwargs: Dict[str, Any] = {
            "task_type": "mrna_ranking_minimal",
            "input_payload": inp_dict,
            "candidates": candidates,
            "status": "running",
        }
        if task_id is not None and str(task_id).strip():
            task_kwargs["task_id"] = str(task_id).strip()
        task = TaskState(**task_kwargs)

        _LOGGER.info(
            "mrna_task_start task_id=%s persist=%s",
            task.task_id,
            inp.persist_run,
        )

        errors: List[str] = []
        if not candidates:
            task.status = "failed"
            wf = WorkflowResult(
                success=False,
                task_id=task.task_id,
                best_candidate=None,
                all_candidates=[],
                summary="No candidates produced from inputs.",
                errors=["empty_candidate_list"],
                trace=list(task.logs),
                completed_at=datetime.now(timezone.utc),
            )
            wf.public_summary = build_public_summary(wf)
            self._finalize_persist(inp, wf, inp_dict, started_at, audit_http_request, operational_summary=wf.summary)
            _LOGGER.error("mrna_task_failed task_id=%s reason=no_candidates", task.task_id)
            return wf

        _LOGGER.info(
            "mrna_candidates_generated task_id=%s count=%s",
            task.task_id,
            len(candidates),
        )

        for cand in candidates:
            filepath = save_sequence(cand.sequence, prefix="mrna_wf")
            cand.metadata["workspace_filepath"] = filepath

            gc_content: Optional[float] = None
            seq_len_tool: Optional[int] = None
            mfe: Optional[float] = None

            if inp.run_gc_tool:
                t0 = time.perf_counter()
                _LOGGER.info(
                    "mrna_tool_start task_id=%s candidate_id=%s tool=%s",
                    task.task_id,
                    cand.id,
                    inp.gc_tool_name,
                )
                gc_res = self.executor.run_tool_for_workflow(
                    inp.gc_tool_name,
                    task=task,
                    candidate=cand,
                    step_name="gc_content",
                    filepath=filepath,
                    service_url=inp.gc_service_url,
                )
                _log_tool_end(task.task_id, cand.id, inp.gc_tool_name, gc_res, time.perf_counter() - t0)
                if gc_res.success:
                    gc_content = _pick_float(gc_res.metrics, gc_res.artifacts.get("result"), "gc_content")
                    seq_len_tool = _pick_int(gc_res.metrics, gc_res.artifacts.get("result"), "sequence_length")
                else:
                    errors.append(f"{cand.id}:gc:{_err_summary(gc_res.error)}")

            if inp.run_fold_tool:
                t0 = time.perf_counter()
                _LOGGER.info(
                    "mrna_tool_start task_id=%s candidate_id=%s tool=%s",
                    task.task_id,
                    cand.id,
                    inp.fold_tool_name,
                )
                fold_res = self.executor.run_tool_for_workflow(
                    inp.fold_tool_name,
                    task=task,
                    candidate=cand,
                    step_name="secondary_structure",
                    filepath=filepath,
                    service_url=inp.fold_service_url,
                )
                _log_tool_end(task.task_id, cand.id, inp.fold_tool_name, fold_res, time.perf_counter() - t0)
                if fold_res.success:
                    result_obj = fold_res.artifacts.get("result")
                    mfe = _pick_float(fold_res.metrics, result_obj, "mfe")
                    if mfe is None:
                        mfe = _pick_float(fold_res.metrics, result_obj, "mfe_kcal_per_mol")
                else:
                    errors.append(f"{cand.id}:fold:{_err_summary(fold_res.error)}")

            bundle = compute_mrna_metric_bundle(
                sequence=cand.sequence,
                gc_from_tools=gc_content,
                sequence_length_from_tools=seq_len_tool,
                mfe_kcal_per_mol=mfe,
            )
            cand.metadata["metrics_bundle"] = bundle

            scored = score_mrna_candidate(
                bundle,
                weights=inp.score_weights or self.weights,
            )
            cand.scores.clear()
            cand.scores.update(scored)
            cand.scores.update(
                {
                    "gc_content": bundle["gc_content"],
                    "sequence_length": float(bundle["sequence_length"]),
                }
            )
            if bundle.get("mfe_kcal_per_mol") is not None:
                cand.scores["mfe_kcal_per_mol"] = float(bundle["mfe_kcal_per_mol"])

        _LOGGER.info("mrna_scoring_ranking task_id=%s score_key=total_score", task.task_id)

        ranked = sort_candidates_by_score(task.candidates, score_key="total_score", descending=True)
        task.candidates = ranked
        best = ranked[0] if ranked else None
        task.best_candidate = best
        task.status = "completed"

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
        ]
        if errors:
            summary_parts.append(f"tool_warnings={len(errors)}")
        operational_summary = "; ".join(summary_parts)

        completed_at = datetime.now(timezone.utc)
        wf = WorkflowResult(
            success=True,
            task_id=task.task_id,
            best_candidate=best,
            all_candidates=ranked,
            summary=operational_summary,
            errors=errors,
            trace=list(task.logs),
            completed_at=completed_at,
        )
        wf.public_summary = build_public_summary(wf)
        self._finalize_persist(inp, wf, inp_dict, started_at, audit_http_request, operational_summary=operational_summary)

        _LOGGER.info(
            "mrna_task_complete task_id=%s best_total_score=%s warnings=%s",
            task.task_id,
            best.scores.get("total_score") if best else None,
            len(errors),
        )
        return wf

    def _finalize_persist(
        self,
        inp: MrnaWorkflowInput,
        wf: WorkflowResult,
        inp_dict: Dict[str, Any],
        started_at: datetime,
        audit_http_request: Optional[Dict[str, Any]],
        *,
        operational_summary: str,
    ) -> None:
        if not inp.persist_run:
            _LOGGER.debug("mrna_persist_skip task_id=%s", wf.task_id)
            return
        completed = wf.completed_at or datetime.now(timezone.utc)
        try:
            _, _, res_path = persist_mrna_workflow_run(
                wf,
                inp_dict,
                operational_summary=operational_summary,
                started_at=started_at,
                completed_at=completed,
                artifact_runs_parent=inp.artifact_runs_parent,
                audit_http_request=audit_http_request,
                copy_artifacts=inp.copy_tool_artifacts_to_run,
            )
            wf.run_result_json_path = res_path
            wf.run_artifact_dir = str(Path(res_path).parent.as_posix())
        except OSError as exc:
            _LOGGER.warning("mrna_persist_failed task_id=%s err=%s", wf.task_id, exc)


def _log_tool_end(task_id: str, cand_id: str, tool_name: str, res: ToolResult, elapsed: float) -> None:
    _LOGGER.info(
        "mrna_tool_end task_id=%s candidate_id=%s tool=%s success=%s elapsed_s=%.4f",
        task_id,
        cand_id,
        tool_name,
        res.success,
        elapsed,
    )


def run_mrna_workflow(
    inp: MrnaWorkflowInput,
    *,
    registry: Optional[ToolRegistry] = None,
    executor: Optional[ToolExecutor] = None,
    task_id: Optional[str] = None,
    audit_http_request: Optional[Dict[str, Any]] = None,
) -> WorkflowResult:
    """Functional entry point: builds registry/executor if omitted."""

    if executor is not None:
        wf = MrnaWorkflow(executor, weights=inp.score_weights)
        return wf.run(inp, task_id=task_id, audit_http_request=audit_http_request)
    reg = registry or build_default_tool_registry(include_demo=False)
    ex = ToolExecutor(reg)
    wf = MrnaWorkflow(ex, weights=inp.score_weights)
    return wf.run(inp, task_id=task_id, audit_http_request=audit_http_request)


def _pick_float(metrics: Dict[str, Any], result_obj: Any, key: str) -> Optional[float]:
    if isinstance(metrics, dict) and key in metrics:
        try:
            return float(metrics[key])
        except (TypeError, ValueError):
            pass
    if isinstance(result_obj, dict) and key in result_obj:
        try:
            return float(result_obj[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    return None


def _pick_int(metrics: Dict[str, Any], result_obj: Any, key: str) -> Optional[int]:
    if isinstance(metrics, dict) and key in metrics:
        try:
            return int(metrics[key])
        except (TypeError, ValueError):
            pass
    if isinstance(result_obj, dict) and key in result_obj:
        try:
            return int(result_obj[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    return None


def _err_summary(err: Any) -> str:
    if isinstance(err, dict):
        return str(err.get("message") or err.get("type") or err)
    return str(err)
