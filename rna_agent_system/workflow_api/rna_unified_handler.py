"""Unified ``task_type`` dispatch for RNA workflows (single HTTP envelope)."""

from __future__ import annotations

from typing import Optional

from agent_core.tool_executor import ToolExecutor
from agent_core.workflow_dispatch import (
    KNOWN_TASK_TYPES,
    classify_task_type,
    normalize_task_type,
)

from workflow_api.mrna_handler import execute_mrna_workflow_http
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse


def execute_rna_workflow_http(
    req: MrnaWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> MrnaWorkflowHttpResponse:
    """Route by ``task_type``: only ``mrna`` runs today; others return structured errors."""

    kind = classify_task_type(req.task_type)
    canonical = normalize_task_type(req.task_type)

    if kind == "unknown":
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=str(req.task_type),
            errors=[
                f"unknown task_type {req.task_type!r}; "
                f"known types: {sorted(KNOWN_TASK_TYPES)}",
            ],
            summary="dispatch_error:unknown_task_type",
        )

    if kind == "placeholder":
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=canonical,
            errors=[f"task_type={canonical!r} is reserved but not implemented yet"],
            summary=f"not_implemented:{canonical}",
        )

    return execute_mrna_workflow_http(req, executor=executor)
