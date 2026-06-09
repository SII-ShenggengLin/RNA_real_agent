"""Shared orchestration for CLI + FastAPI siRNA workflow entry."""

from __future__ import annotations

import json
import traceback
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate
from agent_core.workflow_models import WorkflowResult as WFResult
from agent_core.workflows.sirna_design import SirnaDesignInput, SirnaDesignWorkflow

from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest, SirnaWorkflowHttpResponse


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


def _build_sirna_design_input(req: SirnaWorkflowHttpRequest) -> SirnaDesignInput:
    """Map HTTP request fields to ``SirnaDesignInput``."""

    return SirnaDesignInput(
        mode=req.mode,
        target_sequence=req.target_sequence,
        target_fasta_path=req.target_fasta_path,
        candidate_count=req.candidate_count,
        species=req.species,
        off_target_scan=req.off_target_scan,
        transcriptome_fasta_path=req.transcriptome_fasta_path,
        evitar_mode=req.evitar_mode,
        evitar_predict=req.evitar_predict,
    )


def execute_sirna_workflow_http(
    req: SirnaWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> SirnaWorkflowHttpResponse:
    """Run siRNA workflow and map to HTTP/CLI response; catch exceptions into friendly payloads."""

    ex = executor or ToolExecutor(build_default_tool_registry(include_demo=False))
    cap_reg = CapabilityRegistry(ex)
    for name in SirnaDesignWorkflow.required_capabilities:
        cap_reg.register(name)

    try:
        inp = _build_sirna_design_input(req)
        wf = SirnaDesignWorkflow(cap_reg)
        result = wf.run(inp)

        # Respect caller-supplied task_id if provided
        if req.task_id:
            result.task_id = req.task_id

        warnings = list(result.errors)
        ranked = list(result.all_candidates)
        if req.top_k is not None:
            ranked = ranked[: req.top_k]

        best_dict = _candidate_to_dict(result.best_candidate) if result.best_candidate else None
        cand_dicts = [_candidate_to_dict(c) for c in ranked]

        return SirnaWorkflowHttpResponse(
            task_id=result.task_id,
            success=result.success,
            task_type="sirna",
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
        return SirnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="sirna",
            best_candidate=None,
            candidates=[],
            summary="Invalid workflow parameters.",
            errors=[json.dumps(exc.errors(include_url=False), ensure_ascii=True)],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
    except ValueError as exc:
        return SirnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="sirna",
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
        return SirnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="sirna",
            best_candidate=None,
            candidates=[],
            summary="Internal workflow error.",
            errors=[friendly],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
