"""FastAPI entry for the RNA Design Agent (form-driven).

Workflow requests are executed by ``AgentRunner.run_form()`` with structured
parameters. Natural-language parameter extraction has been removed.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_core.pipeline.models import PipelinePlan
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

app = FastAPI(
    title="RNA Agent workflow API",
    version="1.0.0",
    description="Form-driven entry for agent-side workflows.",
)

_agent_runner = AgentRunner(
    executor=ToolExecutor(build_default_tool_registry()),
)


class AgentRunRequest(BaseModel):
    """Request body for the form-driven agent endpoint."""

    model_config = ConfigDict(extra="forbid")

    workflow: str = Field(description="Workflow name, e.g. mrna_cds_design")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured workflow parameters.",
    )
    task_id: str | None = Field(
        default=None,
        description="Optional stable id for tracing (maps to session_id).",
    )
    top_k: int | None = Field(default=None, ge=1, le=256, description="Limit returned ranked candidates.")
    debug: bool = Field(default=False, description="Include trace snippets and exception detail when allowed.")


class AgentPipelineRequest(BaseModel):
    """Request body for the multi-workflow pipeline endpoint."""

    model_config = ConfigDict(extra="forbid")

    plan: dict[str, Any] = Field(description="PipelinePlan as a JSON object.")
    task_id: str | None = Field(
        default=None,
        description="Optional stable id for tracing.",
    )
    debug: bool = Field(default=False, description="Include trace snippets and exception detail when allowed.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "workflow_api"}


@app.post("/v1/agent/run")
def post_agent_run(req: AgentRunRequest) -> dict[str, Any]:
    """Form-driven agent runner entry (Layer 6)."""
    if req.workflow not in _agent_runner.workflow_registry:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown workflow: {req.workflow}. Available: {list(_agent_runner.workflow_registry.keys())}",
        )

    session_id = req.task_id or str(uuid.uuid4())
    try:
        state = _agent_runner.run_form(
            req.params,
            session_id=session_id,
            explicit_workflow=req.workflow,
        )
    except Exception as exc:
        return {
            "success": False,
            "task_id": session_id,
            "summary": f"Agent execution failed: {exc}",
            "error": str(exc),
        }

    wf_result = state.get("workflow_result")
    if wf_result is not None:
        response: dict[str, Any] = {
            "success": wf_result.success,
            # Echo the session id the run actually used so clients can locate
            # the artifacts under workspace/sessions/<task_id>/.
            "task_id": req.task_id or state.get("session_id", "") or session_id,
            "summary": wf_result.summary if hasattr(wf_result, "summary") else "",
            "best_candidate": wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None,
            "all_candidates": [c.model_dump(mode="json") for c in wf_result.all_candidates],
        }
        if req.top_k is not None:
            response["all_candidates"] = response["all_candidates"][: req.top_k]
        if hasattr(wf_result, "pareto_frontier") and wf_result.pareto_frontier:
            response["pareto_frontier"] = [
                c.model_dump(mode="json") for c in wf_result.pareto_frontier
            ]
        if hasattr(wf_result, "reference_point") and wf_result.reference_point is not None:
            response["reference_point"] = wf_result.reference_point
        if hasattr(wf_result, "best_candidate_source") and wf_result.best_candidate_source:
            response["best_candidate_source"] = wf_result.best_candidate_source
        return response

    pipeline_payload = state.get("pipeline_result") or {}
    return {
        # A node that crashed without producing a WorkflowResult must not be
        # reported as a success — derive the verdict from the pipeline result.
        "success": bool(pipeline_payload.get("success", True)),
        "task_id": session_id,
        "summary": state.get("final_report", ""),
        "route": state.get("_routing_method", ""),
        "errors": pipeline_payload.get("errors", []),
        "tool_results": {k: str(v)[:200] for k, v in state.get("tool_results", {}).items()},
    }


@app.post("/v1/agent/pipeline")
def post_agent_pipeline(req: AgentPipelineRequest) -> dict[str, Any]:
    """Execute a multi-workflow PipelinePlan through the agent engine."""
    try:
        plan = PipelinePlan.model_validate(req.plan)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid pipeline plan: {exc}",
        )

    session_id = req.task_id or str(uuid.uuid4())
    try:
        # Scope tool-level artifacts to workspace/sessions/<session_id>/ (the
        # same no-global-root-leak contract as /v1/agent/run).
        pipeline_result = _agent_runner.run_pipeline(plan, state={"session_id": session_id})
    except Exception as exc:
        error_detail = str(exc)
        if req.debug:
            import traceback
            error_detail = f"{error_detail}\n{traceback.format_exc()}"
        return {
            "success": False,
            "task_id": session_id,
            "summary": f"Pipeline execution failed: {exc}",
            "error": error_detail,
        }

    try:
        pipeline_payload = pipeline_result.model_dump(mode="json")
    except Exception:
        # If full serialization fails (e.g. non-JSON metadata), still return a summary.
        pipeline_payload = {
            "plan_id": pipeline_result.plan_id,
            "success": pipeline_result.success,
            "errors": pipeline_result.errors,
            "node_ids": list(pipeline_result.node_results.keys()),
        }

    return {
        "success": pipeline_result.success,
        "task_id": session_id,
        "plan_id": pipeline_result.plan_id,
        "final_report": pipeline_result.final_report,
        "errors": pipeline_result.errors,
        "pipeline_result": pipeline_payload,
    }
