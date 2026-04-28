"""FastAPI entry for workflow orchestration (not a replacement for tool microservices)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from agent_core.planning.rule_based.planner import RuleBasedPlanner
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
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

# Layer-5 unified runner (new path)
_agent_runner = AgentRunner(
    planner=RuleBasedPlanner(),
    executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
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


@app.post("/v1/agent/run")
def post_agent_run(req: MrnaWorkflowHttpRequest) -> dict[str, Any]:
    """**New** unified agent runner entry (Layer 5).

    Uses ``AgentRunner`` with ``RuleBasedPlanner`` instead of the legacy
    LangGraph ``compiled_graph`` path.  Supports natural-language design
    requests (e.g. ``protein=...``) by routing through the mRNA CDS design
    workflow.
    """
    from typing import Any

    # Build a natural-language prompt from the request
    constraints = dict(req.constraints or {})
    design_tool_hint = constraints.get("design_tool", "")
    user_text = ""
    if req.protein is not None and str(req.protein).strip():
        user_text = f"Design mRNA for protein {req.protein}"
        if design_tool_hint:
            user_text += f" using {design_tool_hint}"
    elif req.sequence is not None and str(req.sequence).strip():
        user_text = f"Evaluate sequence {req.sequence}"
    else:
        raise HTTPException(status_code=422, detail="Provide protein or sequence")

    state = _agent_runner.run(user_text, session_id=req.task_id or "")
    wf_result = state.get("workflow_result")
    if wf_result is not None:
        return {
            "success": wf_result.success,
            "task_id": req.task_id or state.get("task_id", ""),
            "summary": wf_result.summary if hasattr(wf_result, "summary") else "",
            "best_candidate": wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None,
            "all_candidates": [c.model_dump(mode="json") for c in wf_result.all_candidates],
        }

    # Fallback: return raw state summary for non-workflow paths
    return {
        "success": True,
        "task_id": req.task_id or "",
        "summary": state.get("final_report", ""),
        "route": state.get("route", ""),
        "tool_results": {k: str(v)[:200] for k, v in state.get("tool_results", {}).items()},
    }
