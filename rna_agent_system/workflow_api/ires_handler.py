"""Shared orchestration for CLI + FastAPI IRES workflow entry."""

from __future__ import annotations

import json
import traceback
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate
from agent_core.workflow_models import WorkflowResult as WFResult
from agent_core.workflows.ires_prediction import IresPredictionInput, IresPredictionWorkflow

from workflow_api.ires_schemas import IresWorkflowHttpRequest, IresWorkflowHttpResponse


def _candidate_to_dict(c: Candidate) -> Dict[str, Any]:
    return c.model_dump(mode="json")


def _trace_compact(wf: WFResult, *, debug: bool) -> Optional[List[Dict[str, Any]]]:
    if not debug:
        return None
    out: List[Dict[str, Any]] = []
    for rec in wf.trace:
        out.append(
            {
                "step_name": rec.step_name,
                "tool_name": rec.tool_name,
                "success": rec.success,
                "error": rec.error,
                "elapsed_time": rec.elapsed_time,
                "metrics": dict(rec.metrics),
            }
        )
    return out


def _build_ires_input(req: IresWorkflowHttpRequest) -> IresPredictionInput:
    """Map HTTP request fields to ``IresPredictionInput``."""

    sequence_filepath = req.sequence_filepath
    if req.sequence is not None and str(req.sequence).strip():
        # Save inline sequence to workspace so IRESfinder can read it
        sequence_filepath = save_sequence(str(req.sequence).strip(), prefix="ires_input")

    if not sequence_filepath:
        raise ValueError("No sequence or sequence_filepath available.")

    return IresPredictionInput(
        sequence_filepath=sequence_filepath,
        iresfinder_mode=req.iresfinder_mode,
        probability_threshold=req.probability_threshold,
        window_size=req.window_size,
        step_size=req.step_size,
        top_n_candidates=req.top_n_candidates,
        run_structural_validation=req.run_structural_validation,
    )


def execute_ires_workflow_http(
    req: IresWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> IresWorkflowHttpResponse:
    """Run IRES workflow and map to HTTP/CLI response; catch exceptions into friendly payloads."""

    ex = executor or ToolExecutor(build_default_tool_registry(include_demo=False))
    cap_reg = CapabilityRegistry(ex)
    for name in IresPredictionWorkflow.required_capabilities:
        cap_reg.register(name)

    try:
        inp = _build_ires_input(req)
        wf = IresPredictionWorkflow(cap_reg)
        result = wf.run(inp)

        if req.task_id:
            result.task_id = req.task_id

        warnings = list(result.errors)
        ranked = list(result.all_candidates)
        if req.top_k is not None:
            ranked = ranked[: req.top_k]

        best_dict = _candidate_to_dict(result.best_candidate) if result.best_candidate else None
        cand_dicts = [_candidate_to_dict(c) for c in ranked]

        return IresWorkflowHttpResponse(
            task_id=result.task_id,
            success=result.success,
            task_type="ires",
            best_candidate=best_dict,
            candidates=cand_dicts,
            summary=getattr(result, "public_summary", None) or result.summary,
            operational_summary=result.summary,
            errors=[],
            warnings=warnings,
            trace=_trace_compact(result, debug=req.debug),
            debug_detail=None,
        )
    except ValidationError as exc:
        return IresWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="ires",
            best_candidate=None,
            candidates=[],
            summary="Invalid workflow parameters.",
            errors=[json.dumps(exc.errors(include_url=False), ensure_ascii=True)],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
    except ValueError as exc:
        return IresWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="ires",
            best_candidate=None,
            candidates=[],
            summary="Invalid sequence payload.",
            errors=[str(exc)],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
    except Exception as exc:
        friendly = f"Workflow failed: {type(exc).__name__}: {exc}"
        return IresWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="ires",
            best_candidate=None,
            candidates=[],
            summary="Internal workflow error.",
            errors=[friendly],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
