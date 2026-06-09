"""mRNA sequence scoring workflow — evaluate existing sequences (Layer 2).

Existing mRNA sequences → GC + fold + CAI → scoring → ranking → WorkflowResult.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  MrnaSequenceScoringWorkflow INTERFACE LOCK (v1.0.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 mrna_sequence_scoring workflow 的权威实现。任何字段增删、           ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/mrna_sequence_scoring.py  ← 本文件                 ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/workflows/registry.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/sequence_utils.py                                             ║
║    - agent_core/workflow_models.py                                            ║
║    - agent_core/tool_executor.py                                              ║
║    - agent_core/tool_registry.py                                              ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - agent_core/file_manager.py                                               ║
║    - tests/test_mrna_sequence_scoring_layer3.py                               ║
║    - tests/test_mrna_workflow.py                                              ║
║    - tests/test_mrna_sequence_scoring_comprehensive.py                        ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import normalize_rna_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.tool_registry import ToolRegistry
from agent_core.workflow_models import Candidate, TaskState, WorkflowResult, sort_candidates_by_score
from agent_core.workflow_run_storage import build_public_summary
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.sequence_utils import compute_mrna_metric_bundle, score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.mrna_sequence_scoring")


class MrnaSequenceScoringInput(BaseModel):
    """Inputs for ``MrnaSequenceScoringWorkflow`` — pure scoring of existing sequence(s)."""

    model_config = ConfigDict(extra="forbid")

    sequence: Optional[str] = Field(default=None, description="Single RNA/DNA sequence string.")
    sequences: Optional[List[str]] = Field(default=None, description="Multiple sequences.")

    gc_tool_name: str = Field(
        default="compute_rna_sequence_gc_content",
        description="Registry name for GC tool (LangChain tool in agent_core.tools).",
    )
    fold_tool_name: str = Field(
        default="predict_rna_secondary_structure_with_linearfold",
        description="Registry name for folding / MFE tool.",
    )
    fold_service_url: str = Field(
        default="http://127.0.0.1:8015/fold",
        description="Passed to fold tool kwargs (LinearFold microservice).",
    )
    gc_service_url: str = Field(
        default="http://127.0.0.1:8020/gc-content",
        description="Passed to GC tool kwargs.",
    )

    run_gc_tool: bool = Field(default=True)
    run_fold_tool: bool = Field(default=True)


class MrnaSequenceScoringWorkflow(BaseDomainWorkflow[MrnaSequenceScoringInput, WorkflowResult]):
    """Score existing mRNA sequences via ToolExecutor-driven tools.

    Orchestrates candidate generation and tool evaluation via ``ToolExecutor``.
    Workflow code does not invoke subprocess or HTTP directly; tools remain in ``agent_core.tools``.
    """

    name = "mrna_sequence_scoring"
    description = "Score existing mRNA sequences with GC, fold, and CAI metrics."
    required_capabilities = [
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure_with_linearfold",
        "predict_rna_secondary_structure",
        "compute_cai_for_cds_sequence",
    ]

    def __init__(self, executor: ToolExecutor):
        self.executor = executor

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def generate_candidates(self, inp: MrnaSequenceScoringInput) -> list[Candidate]:
        raw_seqs: list[str] = []
        if inp.sequences:
            raw_seqs = [normalize_rna_sequence(s) for s in inp.sequences if s]
        elif inp.sequence:
            one = normalize_rna_sequence(inp.sequence)
            if one:
                raw_seqs = [one]
        return [
            Candidate(sequence=s, sequence_type="mrna", source="mrna:direct", metadata={"generator": "normalize"})
            for s in raw_seqs if s
        ]

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run GC + fold + CAI on *candidate* and return raw metrics bundle."""
        # MrnaSequenceScoringWorkflow stores the current input on the instance
        # during run() so that evaluate() can access tool configuration.
        inp = getattr(self, "_current_input", None)
        if inp is None:
            raise RuntimeError("evaluate() called before run() set _current_input")

        filepath = save_sequence(candidate.sequence, prefix="mrna_wf")
        candidate.metadata["workspace_filepath"] = filepath

        gc_content: Optional[float] = None
        seq_len_tool: Optional[int] = None
        mfe: Optional[float] = None

        if inp.run_gc_tool:
            gc_res = self.executor.run_tool_for_workflow(
                inp.gc_tool_name,
                task=getattr(self, "_current_task", None),
                candidate=candidate,
                step_name="gc_content",
                filepath=filepath,
                service_url=inp.gc_service_url,
            )
            if gc_res.success:
                gc_content = _pick_float(gc_res.metrics, gc_res.artifacts.get("result"), "gc_content")
                seq_len_tool = _pick_int(gc_res.metrics, gc_res.artifacts.get("result"), "sequence_length")
            else:
                self._errors.append(f"{candidate.id}:gc:{_err_summary(gc_res.error)}")

        if inp.run_fold_tool:
            fold_res = self.executor.run_tool_for_workflow(
                inp.fold_tool_name,
                task=getattr(self, "_current_task", None),
                candidate=candidate,
                step_name="secondary_structure",
                filepath=filepath,
                service_url=inp.fold_service_url,
            )
            if fold_res.success:
                result_obj = fold_res.artifacts.get("result")
                mfe = _pick_float(fold_res.metrics, result_obj, "mfe")
                if mfe is None:
                    mfe = _pick_float(fold_res.metrics, result_obj, "mfe_kcal_per_mol")
            else:
                self._errors.append(f"{candidate.id}:fold:{_err_summary(fold_res.error)}")

        cai_score: Optional[float] = None
        cai_res = self.executor.run_tool_for_workflow(
            "compute_cai_for_cds_sequence",
            task=getattr(self, "_current_task", None),
            candidate=candidate,
            step_name="cai",
            filepath=filepath,
            species="Homo sapiens",
        )
        if cai_res.success:
            cai_score = _pick_float(cai_res.metrics, cai_res.artifacts.get("result"), "cai_score")
        else:
            self._errors.append(f"{candidate.id}:cai:{_err_summary(cai_res.error)}")

        bundle = compute_mrna_metric_bundle(
            sequence=candidate.sequence,
            gc_from_tools=gc_content,
            sequence_length_from_tools=seq_len_tool,
            mfe_kcal_per_mol=mfe,
            cai_score=cai_score,
        )
        candidate.metadata["metrics_bundle"] = bundle
        return bundle

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        return score_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates produced from inputs.")
        ranked = sort_candidates_by_score(candidates, score_key="total_score", descending=True)
        best = ranked[0] if ranked else None
        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
        ]
        if getattr(self, "_errors", None):
            summary_parts.append(f"tool_warnings={len(self._errors)}")
        return WorkflowResult(
            success=True,
            task_id=getattr(self, "_task_id", ""),
            best_candidate=best,
            all_candidates=ranked,
            summary="; ".join(summary_parts),
            errors=list(getattr(self, "_errors", [])),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Custom run() with ToolExecutor trace support
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: MrnaSequenceScoringInput | dict[str, Any],
        *,
        task_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
    ) -> WorkflowResult:
        if isinstance(inp, dict):
            inp = MrnaSequenceScoringInput(**inp)
        inp_dict = inp.model_dump(mode="json")

        candidates = self.generate_candidates(inp)

        task_kwargs: dict[str, Any] = {
            "task_type": "mrna_ranking_minimal",
            "input_payload": inp_dict,
            "candidates": candidates,
            "status": "running",
        }
        if task_id is not None and str(task_id).strip():
            task_kwargs["task_id"] = str(task_id).strip()
        task = TaskState(**task_kwargs)

        _LOGGER.info("mrna_task_start task_id=%s", task.task_id)

        self._current_input = inp
        self._current_task = task
        self._task_id = task.task_id
        self._errors: list[str] = []

        if not candidates:
            task.status = "failed"
            wf = WorkflowResult(
                success=False,
                task_id=task.task_id,
                best_candidate=None,
                all_candidates=[],
                summary="No candidates produced from inputs.",
                errors=["empty_candidate_list"],
                trace=list(task.logs),
                completed_at=datetime.now(timezone.utc),
            )
            wf.public_summary = build_public_summary(wf)
            _LOGGER.error("mrna_task_failed task_id=%s reason=no_candidates", task.task_id)
            return wf

        _LOGGER.info("mrna_candidates_generated task_id=%s count=%s", task.task_id, len(candidates))

        for i, candidate in enumerate(candidates):
            _LOGGER.info("workflow_evaluating_candidate idx=%d total=%d workflow=%s", i + 1, len(candidates), self.name)
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"

            # Attach extra score keys for backward compatibility
            candidate.scores["gc_content"] = metrics.get("gc_content", 0.0)
            candidate.scores["sequence_length"] = float(metrics.get("sequence_length", 0))
            if metrics.get("mfe_kcal_per_mol") is not None:
                candidate.scores["mfe_kcal_per_mol"] = float(metrics["mfe_kcal_per_mol"])

        result = self.rank_and_format(candidates)
        result.task_id = task.task_id
        result.trace = list(task.logs)
        result.completed_at = datetime.now(timezone.utc)
        result.public_summary = build_public_summary(result)

        _LOGGER.info(
            "mrna_task_complete task_id=%s best_total_score=%s warnings=%s",
            task.task_id,
            result.best_candidate.scores.get("total_score") if result.best_candidate else None,
            len(result.errors),
        )
        return result


def run_mrna_sequence_scoring(
    inp: MrnaSequenceScoringInput,
    *,
    registry: Optional[ToolRegistry] = None,
    executor: Optional[ToolExecutor] = None,
    task_id: Optional[str] = None,
) -> WorkflowResult:
    """Functional entry point: builds registry/executor if omitted."""
    if executor is not None:
        wf = MrnaSequenceScoringWorkflow(executor)
        return wf.run(inp, task_id=task_id)
    reg = registry or build_default_tool_registry(include_demo=False)
    ex = ToolExecutor(reg)
    wf = MrnaSequenceScoringWorkflow(ex)
    return wf.run(inp, task_id=task_id)


# ── backward-compatible aliases (deprecated, keep for transition) ──
MrnaWorkflowInput = MrnaSequenceScoringInput


def _pick_float(metrics: Dict[str, Any], result_obj: Any, key: str) -> Optional[float]:
    """Safely extract *key* as float from *metrics* or *result_obj*."""
    if isinstance(metrics, dict) and key in metrics:
        try:
            return float(metrics[key])
        except (TypeError, ValueError):
            pass
    if isinstance(result_obj, dict) and key in result_obj:
        try:
            return float(result_obj[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    return None


def _pick_int(metrics: Dict[str, Any], result_obj: Any, key: str) -> Optional[int]:
    """Safely extract *key* as int from *metrics* or *result_obj*."""
    if isinstance(metrics, dict) and key in metrics:
        try:
            return int(metrics[key])
        except (TypeError, ValueError):
            pass
    if isinstance(result_obj, dict) and key in result_obj:
        try:
            return int(result_obj[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            pass
    return None


def _err_summary(err: Any) -> str:
    """Return a short error string from a ToolResult error dict or exception."""
    if isinstance(err, dict):
        return str(err.get("message") or err.get("type") or err)
    return str(err)
