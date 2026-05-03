"""Unified ``task_type`` dispatch for RNA workflows (single HTTP envelope)."""

from __future__ import annotations

from typing import Optional

from agent_core.planning.rule_based.planner import RuleBasedPlanner
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_dispatch import (
    KNOWN_TASK_TYPES,
    classify_task_type,
    normalize_task_type,
)

from workflow_api.mrna_handler import execute_mrna_workflow_http
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse


def _run_aptamer_via_agent_runner(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the aptamer workflow through AgentRunner (Layer 5).

    The aptamer workflow requires protein-structure inputs that do not fit the
    legacy ``MrnaWorkflowHttpRequest`` schema, so we build a natural-language
    prompt from the request fields and let the planner route to the workflow.
    """
    runner = AgentRunner(
        planner=RuleBasedPlanner(),
        executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
    )

    constraints = dict(req.constraints or {})
    user_text_parts: list[str] = ["Design RNA aptamer"]
    if req.protein is not None and str(req.protein).strip():
        user_text_parts.append(f"against protein {req.protein}")
    else:
        user_text_parts.append("against target protein")

    if "protein_structure_path" in constraints:
        user_text_parts.append(f"using structure {constraints['protein_structure_path']}")
    if "hotspot_residues" in constraints:
        user_text_parts.append(f"with hotspot {constraints['hotspot_residues']}")
    if "aptamer_length" in constraints:
        user_text_parts.append(f"length {constraints['aptamer_length']} nt")
    if "chain_id" in constraints:
        user_text_parts.append(f"chain {constraints['chain_id']}")

    user_text = " ".join(user_text_parts)
    state = runner.run(user_text, session_id=req.task_id or "")
    wf_result = state.get("workflow_result")

    if wf_result is None:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="aptamer",
            errors=["AgentRunner did not produce a workflow_result."],
            summary="aptamer_workflow:no_result",
        )

    best_dict = wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None
    cand_dicts = [c.model_dump(mode="json") for c in wf_result.all_candidates]
    if req.top_k is not None:
        cand_dicts = cand_dicts[: req.top_k]

    return MrnaWorkflowHttpResponse(
        task_id=wf_result.task_id,
        success=wf_result.success,
        task_type="aptamer",
        best_candidate=best_dict,
        candidates=cand_dicts,
        summary=wf_result.public_summary or wf_result.summary,
        operational_summary=wf_result.summary,
        errors=[],
        warnings=list(wf_result.errors),
        trace=None,
        debug_detail=None,
    )


def execute_rna_workflow_http(
    req: MrnaWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> MrnaWorkflowHttpResponse:
    """Route by ``task_type``: ``mrna`` and ``aptamer`` are implemented."""

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

    if canonical == "aptamer":
        return _run_aptamer_via_agent_runner(req)

    return execute_mrna_workflow_http(req, executor=executor)
