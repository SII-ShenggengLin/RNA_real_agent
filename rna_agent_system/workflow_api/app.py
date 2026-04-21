"""FastAPI entry for workflow orchestration (not a replacement for tool microservices)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from agent_core.workflow_dispatch import normalize_task_type

from workflow_api.mrna_handler import execute_mrna_workflow_http
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse
from workflow_api.rna_unified_handler import execute_rna_workflow_http

app = FastAPI(
    title="RNA Agent workflow API",
    version="0.1.0",
    description=(
        "HTTP entry for agent-side workflows (e.g. mRNA candidate ranking). "
        "Individual RNA tools remain in microservices under ``microservices/*``."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "workflow_api"}


@app.post("/v1/workflows/mrna/run", response_model=MrnaWorkflowHttpResponse)
def post_mrna_workflow(req: MrnaWorkflowHttpRequest) -> MrnaWorkflowHttpResponse:
    """Run the mRNA ranking workflow; returns structured JSON (including ``success=false`` cases)."""

    if normalize_task_type(req.task_type) != "mrna":
        raise HTTPException(
            status_code=422,
            detail=(
                "This endpoint only supports task_type=mrna (default). "
                "Use POST /v1/workflows/run for other task_type values."
            ),
        )
    return execute_mrna_workflow_http(req)


@app.post("/v1/workflows/run", response_model=MrnaWorkflowHttpResponse)
def post_rna_workflow(req: MrnaWorkflowHttpRequest) -> MrnaWorkflowHttpResponse:
    """Unified entry: ``task_type`` selects workflow (only ``mrna`` implemented)."""

    return execute_rna_workflow_http(req)
