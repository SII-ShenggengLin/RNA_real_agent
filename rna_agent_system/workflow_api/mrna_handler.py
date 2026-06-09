"""Shared orchestration for CLI + FastAPI mRNA workflow entry.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  MrnaHandler INTERFACE LOCK (v1.0.0) —— 禁止单方面变更                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 mRNA workflow HTTP/CLI 入口的权威实现。任何函数签名变动、           ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - workflow_api/mrna_handler.py  ← 本文件                                  ║
║    - workflow_api/mrna_schemas.py                                             ║
║    - workflow_api/app.py                                                      ║
║    - cli/mrna_workflow.py                                                     ║
║    - agent_core/workflows/mrna_sequence_scoring.py                            ║
║    - tests/test_mrna_layer45_integration.py                                   ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import traceback
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from agent_core.file_manager import save_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate
from agent_core.workflow_models import WorkflowResult as WFResult
from agent_core.workflow_run_storage import maybe_persist_workflow_run
from agent_core.workflows import MrnaSequenceScoringInput, run_mrna_sequence_scoring

from workflow_api.mrna_schemas import MrnaWorkflowHttpRequest, MrnaWorkflowHttpResponse


class ProteinToCdsError(RuntimeError):
    """Raised when LinearDesign cannot produce a CDS from protein input."""


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


_STRICT_INPUT_KEYS = set(MrnaSequenceScoringInput.model_fields.keys())
_STRIP_CONSTRAINT_KEYS = frozenset({
    "lineardesign_service_url",
    "lineardesign_lambda",
    "lineardesign_codon_usage_path",
    "lineardesign_verbose",
    "task_type",
})


def _sanitize_constraints(constraints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not constraints:
        return {}
    out: Dict[str, Any] = {}
    for key, val in constraints.items():
        if key in _STRIP_CONSTRAINT_KEYS:
            continue
        if key in _STRICT_INPUT_KEYS and val is not None:
            out[key] = val
    return out


def _merge_constraints_into_input(
    base: MrnaSequenceScoringInput,
    constraints: Optional[Dict[str, Any]],
) -> MrnaSequenceScoringInput:
    merged = _sanitize_constraints(constraints)
    if not merged:
        return base
    payload = base.model_dump()
    payload.update(merged)
    return MrnaSequenceScoringInput.model_validate(payload)


def _resolve_sequence_inputs(req: MrnaWorkflowHttpRequest) -> MrnaSequenceScoringInput:
    """Build ``MrnaSequenceScoringInput`` from validated HTTP request (no protein translation here)."""

    raw_c = dict(req.constraints or {})
    merge_extra = _sanitize_constraints(raw_c)

    if req.sequence is not None and str(req.sequence).strip():
        inp = MrnaSequenceScoringInput(sequence=str(req.sequence).strip())
        return _merge_constraints_into_input(inp, merge_extra)

    if req.sequences:
        inp = MrnaSequenceScoringInput(sequences=list(req.sequences))
        return _merge_constraints_into_input(inp, merge_extra)

    raise ValueError("missing sequence source")


def protein_to_cds_sequence(
    protein: str,
    *,
    executor: ToolExecutor,
    service_url: str = "http://127.0.0.1:8014/generate/cds",
    lambda_value: float = 0.0,
    codon_usage_path: Optional[str] = None,
    verbose: bool = False,
) -> str:
    """Run LinearDesign tool once; return RNA/DNA CDS string."""

    cleaned = "".join(protein.split()).upper()
    if not cleaned:
        raise ProteinToCdsError("Empty protein sequence.")
    invalid = sorted({ch for ch in cleaned if ch not in "ACDEFGHIKLMNPQRSTVWY"})
    if invalid:
        raise ProteinToCdsError(f"Invalid amino-acid characters: {''.join(invalid)}")

    fp = save_sequence(cleaned, prefix="api_protein")
    tool_kwargs: dict[str, Any] = {
        "filepath": fp,
        "service_url": service_url,
        "lambda_value": lambda_value,
    }
    if codon_usage_path is not None:
        tool_kwargs["codon_usage_path"] = codon_usage_path
    if verbose:
        tool_kwargs["verbose"] = verbose
    res = executor.run_tool("design_mrna_cds_with_lineardesign", **tool_kwargs)
    if not res.success:
        msg = str(res.error)
        raise ProteinToCdsError(f"LinearDesign failed: {msg}")
    raw = res.artifacts.get("result")
    if not isinstance(raw, dict) or "generated_sequence" not in raw:
        raise ProteinToCdsError("LinearDesign returned no generated_sequence.")
    return str(raw["generated_sequence"]).strip()


def execute_mrna_workflow_http(
    req: MrnaWorkflowHttpRequest,
    *,
    executor: Optional[ToolExecutor] = None,
) -> MrnaWorkflowHttpResponse:
    """Run workflow and map to HTTP/CLI response; catch exceptions into friendly payloads."""

    ex = executor or ToolExecutor(build_default_tool_registry(include_demo=False))

    try:
        if req.protein is not None and str(req.protein).strip():
            c_all = dict(req.constraints or {})
            ld_url = str(c_all.pop("lineardesign_service_url", "http://127.0.0.1:8014/generate/cds"))
            ld_lambda = float(c_all.pop("lineardesign_lambda", 0.0))
            ld_codon = c_all.pop("lineardesign_codon_usage_path", None)
            ld_verbose = bool(c_all.pop("lineardesign_verbose", False))
            cds = protein_to_cds_sequence(
                str(req.protein),
                executor=ex,
                service_url=ld_url,
                lambda_value=ld_lambda,
                codon_usage_path=str(ld_codon) if ld_codon is not None else None,
                verbose=ld_verbose,
            )
            inp = MrnaSequenceScoringInput(sequence=cds)
            inp = _merge_constraints_into_input(inp, c_all or None)
        else:
            inp = _resolve_sequence_inputs(req)

        wf = run_mrna_sequence_scoring(
            inp,
            executor=ex,
            task_id=req.task_id,
        )

        maybe_persist_workflow_run(
            wf,
            inp.model_dump(mode="json"),
            enabled=True,
            audit_http_request=req.model_dump(mode="json"),
        )

        warnings = list(wf.errors)
        ranked = list(wf.all_candidates)
        if req.top_k is not None:
            ranked = ranked[: req.top_k]

        best_dict = _candidate_to_dict(wf.best_candidate) if wf.best_candidate else None
        cand_dicts = [_candidate_to_dict(c) for c in ranked]

        return MrnaWorkflowHttpResponse(
            task_id=wf.task_id,
            success=wf.success,
            task_type=req.task_type,
            best_candidate=best_dict,
            candidates=cand_dicts,
            summary=wf.public_summary or wf.summary,
            operational_summary=wf.summary,
            artifact_directory=wf.run_artifact_dir,
            result_json_path=wf.run_result_json_path,
            errors=[],
            warnings=warnings,
            trace=_trace_compact(wf, debug=req.debug),
            debug_detail=None,
        )
    except ProteinToCdsError as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=req.task_type,
            best_candidate=None,
            candidates=[],
            summary="Protein→CDS step failed.",
            errors=[str(exc)],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
    except ValidationError as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=req.task_type,
            best_candidate=None,
            candidates=[],
            summary="Invalid workflow parameters.",
            errors=[json.dumps(exc.errors(include_url=False), ensure_ascii=True)],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )
    except ValueError as exc:
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=req.task_type,
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
        return MrnaWorkflowHttpResponse(
            task_id=str(req.task_id or "pending"),
            success=False,
            task_type=req.task_type,
            best_candidate=None,
            candidates=[],
            summary="Internal workflow error.",
            errors=[friendly],
            warnings=[],
            trace=None,
            debug_detail=traceback.format_exc() if req.debug else None,
        )


def validate_http_request_body(body: Dict[str, Any]) -> MrnaWorkflowHttpRequest:
    """Strict validation for JSON bodies (raises ``ValidationError``)."""

    return MrnaWorkflowHttpRequest.model_validate(body)
