"""FastAPI entry for the RNA Design Agent (natural-language only).

All workflow requests are routed through ``AgentRunner`` + ``LLMPlanner``
(DeepSeek-powered).  There are no hard-coded ``task_type`` dispatch endpoints.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent_core.planning.factory import build_planner
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry

app = FastAPI(
    title="RNA Agent workflow API",
    version="0.2.0",
    description="Natural-language entry for agent-side workflows. No task_type dispatch.",
)

# Layer-5 unified runner (sole path)
_agent_runner = AgentRunner(
    planner=build_planner(),
    executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
)


class AgentRunRequest(BaseModel):
    """Request body for the unified natural-language agent endpoint.

    Either ``user_text`` (preferred) or one of ``protein`` / ``sequence``
    must be provided.
    """

    model_config = ConfigDict(extra="forbid")

    user_text: Optional[str] = Field(
        default=None,
        description="Natural-language request. If provided, used directly.",
    )
    protein: Optional[str] = Field(
        default=None,
        description="Amino-acid sequence; used to build a prompt when user_text is absent.",
    )
    sequence: Optional[str] = Field(
        default=None,
        description="RNA/DNA sequence; used to build a prompt when user_text is absent.",
    )
    sequences: Optional[List[str]] = Field(
        default=None,
        description="Multiple sequences; used to build a prompt when user_text is absent.",
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Optional stable id for tracing (maps to session_id).",
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional workflow knobs passed through to the agent.",
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=256, description="Limit returned ranked candidates.")
    debug: bool = Field(default=False, description="Include trace snippets and exception detail when allowed.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "workflow_api"}


@app.post("/v1/agent/run")
def post_agent_run(req: AgentRunRequest) -> dict[str, Any]:
    """Unified natural-language agent runner entry (Layer 5).

    Uses ``AgentRunner`` with ``LLMPlanner`` (DeepSeek-powered) to support
    arbitrary RNA bioinformatics design and analysis requests.
    """

    constraints = dict(req.constraints or {})

    # 1. Determine user_text
    if req.user_text is not None and str(req.user_text).strip():
        user_text = str(req.user_text).strip()
    elif req.protein is not None and str(req.protein).strip():
        user_text = f"Design mRNA for protein {req.protein}"
        design_tool_hint = constraints.get("design_tool", "")
        if design_tool_hint:
            user_text += f" using {design_tool_hint}"
    elif req.sequence is not None and str(req.sequence).strip():
        user_text = f"Evaluate sequence {req.sequence}"
    elif req.sequences:
        user_text = f"Evaluate {len(req.sequences)} sequences"
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide user_text, protein, sequence, or sequences.",
        )

    # 2. Run via AgentRunner
    try:
        state = _agent_runner.run(user_text, session_id=req.task_id or "")
    except Exception as exc:
        return {
            "success": False,
            "task_id": req.task_id or "",
            "summary": f"Agent execution failed: {exc}",
            "error": str(exc),
        }

    # 3. Format response
    wf_result = state.get("workflow_result")
    if wf_result is not None:
        response: dict[str, Any] = {
            "success": wf_result.success,
            "task_id": req.task_id or state.get("task_id", "") or str(uuid.uuid4()),
            "summary": wf_result.summary if hasattr(wf_result, "summary") else "",
            "best_candidate": wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None,
            "all_candidates": [c.model_dump(mode="json") for c in wf_result.all_candidates],
        }
        if req.top_k is not None:
            response["all_candidates"] = response["all_candidates"][: req.top_k]
        return response

    # Fallback: return raw state summary for non-workflow paths
    return {
        "success": True,
        "task_id": req.task_id or str(uuid.uuid4()),
        "summary": state.get("final_report", ""),
        "route": state.get("route", ""),
        "tool_results": {k: str(v)[:200] for k, v in state.get("tool_results", {}).items()},
    }
