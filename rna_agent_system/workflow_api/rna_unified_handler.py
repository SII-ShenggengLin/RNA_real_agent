"""Unified ``task_type`` dispatch for RNA workflows (single HTTP envelope)."""

from __future__ import annotations

from typing import Optional

from agent_core.planning.factory import build_planner
from agent_core.runner import AgentRunner
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from workflow_api.ires_handler import execute_ires_workflow_http
from workflow_api.ires_schemas import IresWorkflowHttpRequest
from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse
from workflow_api.sirna_handler import execute_sirna_workflow_http
from workflow_api.sirna_schemas import SirnaWorkflowHttpRequest


def _run_sirna_via_dedicated_handler(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the siRNA workflow through the dedicated Layer-2 handler.

    Maps the legacy ``MrnaWorkflowHttpRequest`` envelope to
    ``SirnaWorkflowHttpRequest`` and invokes ``SirnaDesignWorkflow`` directly.
    """
    constraints = dict(req.constraints or {})
    sirna_req = SirnaWorkflowHttpRequest(
        mode=constraints.get("mode", "generic"),
        target_sequence=req.sequence,
        target_fasta_path=constraints.get("target_fasta_path"),
        candidate_count=constraints.get("candidate_count", 10),
        species=constraints.get("species", "homo_sapiens"),
        off_target_scan=constraints.get("off_target_scan", True),
        transcriptome_fasta_path=constraints.get("transcriptome_fasta_path"),
        evitar_mode=constraints.get("evitar_mode", "existing"),
        evitar_predict=constraints.get("evitar_predict", "predsi"),
        task_id=req.task_id,
        top_k=req.top_k,
        debug=req.debug,
    )
    sirna_resp = execute_sirna_workflow_http(sirna_req)
    return MrnaWorkflowHttpResponse(
        task_id=sirna_resp.task_id,
        success=sirna_resp.success,
        task_type=sirna_resp.task_type,
        best_candidate=sirna_resp.best_candidate,
        candidates=sirna_resp.candidates,
        summary=sirna_resp.summary,
        operational_summary=sirna_resp.operational_summary,
        errors=sirna_resp.errors,
        warnings=sirna_resp.warnings,
        trace=sirna_resp.trace,
        debug_detail=sirna_resp.debug_detail,
    )


def _run_ires_via_dedicated_handler(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the IRES workflow through the dedicated Layer-2 handler.

    Maps the legacy ``MrnaWorkflowHttpRequest`` envelope to
    ``IresWorkflowHttpRequest`` and invokes ``IresPredictionWorkflow`` directly.
    """
    constraints = dict(req.constraints or {})
    ires_req = IresWorkflowHttpRequest(
        sequence=req.sequence,
        sequence_filepath=constraints.get("sequence_filepath"),
        iresfinder_mode=constraints.get("iresfinder_mode", 2),
        probability_threshold=constraints.get("probability_threshold", 0.5),
        window_size=constraints.get("window_size", 174),
        step_size=constraints.get("step_size", 50),
        top_n_candidates=constraints.get("top_n_candidates", 5),
        run_structural_validation=constraints.get("run_structural_validation", True),
        task_id=req.task_id,
        top_k=req.top_k,
        debug=req.debug,
    )
    ires_resp = execute_ires_workflow_http(ires_req)

    # Convert IresWorkflowHttpResponse -> MrnaWorkflowHttpResponse for union endpoint
    best_dict = ires_resp.best_candidate.model_dump(mode="json") if ires_resp.best_candidate else None
    cand_dicts = [c.model_dump(mode="json") for c in ires_resp.candidates]

    return MrnaWorkflowHttpResponse(
        task_id=ires_resp.task_id,
        success=ires_resp.success,
        task_type=ires_resp.task_type,
        best_candidate=best_dict,
        candidates=cand_dicts,
        summary=ires_resp.summary,
        operational_summary=ires_resp.operational_summary,
        errors=ires_resp.errors,
        warnings=ires_resp.warnings,
        trace=ires_resp.trace,
        debug_detail=ires_resp.debug_detail,
    )


def _run_aptamer_via_agent_runner(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the aptamer workflow through AgentRunner (Layer 5).

    The aptamer workflow requires protein-structure inputs that do not fit the
    legacy ``MrnaWorkflowHttpRequest`` schema, so we build a natural-language
    prompt from the request fields and let the planner route to the workflow.
    """
    try:
        runner = AgentRunner(
            planner=build_planner(),
            executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        )
    except Exception as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="aptamer",
            errors=[f"Failed to initialize AgentRunner: {exc}"],
            summary="aptamer_workflow:init_error",
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

    try:
        state = runner.run(user_text, session_id=req.task_id or "")
    except Exception as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type="aptamer",
            errors=[f"AgentRunner execution failed: {exc}"],
            summary="aptamer_workflow:execution_error",
        )

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


def _run_structure_workflow_via_agent_runner(
    req: MrnaWorkflowHttpRequest,
    task_type: str,
    user_text: str,
) -> MrnaWorkflowHttpResponse:
    """Generic Layer-5 runner for structure-design workflows.

    Builds a natural-language prompt and lets ``AgentRunner`` + ``LLMPlanner``
    route to the correct workflow.
    """
    try:
        runner = AgentRunner(
            planner=build_planner(),
            executor=ToolExecutor(build_default_tool_registry(include_demo=False)),
        )
    except Exception as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=task_type,
            errors=[f"Failed to initialize AgentRunner: {exc}"],
            summary=f"{task_type}:init_error",
        )

    try:
        state = runner.run(user_text, session_id=req.task_id or "")
    except Exception as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=task_type,
            errors=[f"AgentRunner execution failed: {exc}"],
            summary=f"{task_type}:execution_error",
        )

    wf_result = state.get("workflow_result")
    if wf_result is None:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=task_type,
            errors=["AgentRunner did not produce a workflow_result."],
            summary=f"{task_type}:no_result",
        )

    best_dict = wf_result.best_candidate.model_dump(mode="json") if wf_result.best_candidate else None
    cand_dicts = [c.model_dump(mode="json") for c in wf_result.all_candidates]
    if req.top_k is not None:
        cand_dicts = cand_dicts[: req.top_k]

    return MrnaWorkflowHttpResponse(
        task_id=wf_result.task_id,
        success=wf_result.success,
        task_type=task_type,
        best_candidate=best_dict,
        candidates=cand_dicts,
        summary=wf_result.public_summary or wf_result.summary,
        operational_summary=wf_result.summary,
        errors=[],
        warnings=list(wf_result.errors),
        trace=None,
        debug_detail=None,
    )


def _run_secondary_structure_via_agent_runner(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the RNA secondary structure design workflow through AgentRunner (Layer 5)."""
    constraints = dict(req.constraints or {})
    target_structure = constraints.get("target_structure", "")
    if not target_structure and req.sequence:
        # Fallback: treat the provided sequence as a target structure hint
        target_structure = req.sequence

    user_text_parts: list[str] = ["Design RNA secondary structure"]
    if target_structure:
        user_text_parts.append(f"for target structure {target_structure}")
    if "start_sequence" in constraints:
        user_text_parts.append(f"with start sequence {constraints['start_sequence']}")
    if "repeats" in constraints:
        user_text_parts.append(f"repeats={constraints['repeats']}")
    if "num_invocations" in constraints:
        user_text_parts.append(f"num_invocations={constraints['num_invocations']}")

    user_text = " ".join(user_text_parts)
    return _run_structure_workflow_via_agent_runner(req, "secondary_structure_design", user_text)


def _run_tertiary_structure_via_agent_runner(
    req: MrnaWorkflowHttpRequest,
) -> MrnaWorkflowHttpResponse:
    """Run the RNA tertiary structure design workflow through AgentRunner (Layer 5)."""
    constraints = dict(req.constraints or {})
    structure_path = constraints.get("structure_filepath", "")

    user_text_parts: list[str] = ["Design RNA tertiary structure"]
    if structure_path:
        user_text_parts.append(f"from structure file {structure_path}")
    if "design_tools" in constraints:
        user_text_parts.append(f"using tools {constraints['design_tools']}")
    if "n_samples_per_tool" in constraints:
        user_text_parts.append(f"n_samples={constraints['n_samples_per_tool']}")

    user_text = " ".join(user_text_parts)
    return _run_structure_workflow_via_agent_runner(req, "tertiary_structure_design", user_text)


def execute_rna_workflow_http(
    req: MrnaWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> MrnaWorkflowHttpResponse:
    """Run a workflow via AgentRunner using a natural-language prompt.

    This replaces the old hard-coded ``task_type`` dispatch.  The prompt is
    built from the request fields and routed by ``LLMPlanner``.
    """

    constraints = dict(req.constraints or {})

    # Build natural-language prompt from legacy request fields
    if req.protein is not None and str(req.protein).strip():
        user_text = f"Design mRNA for protein {req.protein}"
        design_tool_hint = constraints.get("design_tool", "")
        if design_tool_hint:
            user_text += f" using {design_tool_hint}"
    elif req.sequence is not None and str(req.sequence).strip():
        user_text = f"Evaluate sequence {req.sequence}"
    elif req.sequences:
        user_text = f"Evaluate {len(req.sequences)} sequences"
    else:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=str(req.task_type or "unknown"),
            errors=["Provide protein, sequence, or sequences."],
            summary="dispatch_error:missing_input",
        )

    return _run_structure_workflow_via_agent_runner(
        req, req.task_type or "rna", user_text
    )
