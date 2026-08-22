"""mRNA sequence scoring workflow — evaluate existing sequences (Layer 2).

Existing mRNA sequences → GC + fold + CAI → scoring → ranking → WorkflowResult.


v1.1.0: the constructor now takes ``CapabilityRegistry`` like every other
workflow (previously ``ToolExecutor``); the registry's executor is still used
internally for tool trace records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agent_core.capabilities.base import CapabilityRegistry, build_default_capability_registry
from agent_core.constants.species import DEFAULT_CAI_SPECIES
from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import normalize_rna_sequence
from agent_core.tool_executor import ToolExecutor, build_default_tool_registry
from agent_core.workflow_models import Candidate, TaskState, WorkflowResult, sort_candidates_by_score
from agent_core.workflow_run_storage import build_public_summary
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.sequence_utils import compute_mrna_metric_bundle, score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.mrna_sequence_scoring")


class MrnaSequenceScoringInput(BaseModel):
    """Inputs for ``MrnaSequenceScoringWorkflow`` — pure scoring of existing sequence(s)."""
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    gc_filepath: str = Field(default=None, description="[gc] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    gc_timeout_seconds: float = Field(default=120.0, description="[gc] timeout_seconds: HTTP request timeout in seconds.")
    linearfold_filepath: str = Field(default=None, description="[linearfold] filepath: Path to a workspace file containing RNA sequence (plain or FASTA).")
    linearfold_beam_size: int = Field(default=100, description="[linearfold] beam_size: Beam size for LinearFold (0 = infinite beam).")
    linearfold_use_vienna: bool = Field(default=False, description="[linearfold] use_vienna: If true, request LinearFold-V (Vienna energy parameters).")
    linearfold_dangles: int = Field(default=2, description="[linearfold] dangles: Dangling-end model: 0 or 2 (LinearFold --dangles).")
    linearfold_sharpturn: bool = Field(default=False, description="[linearfold] sharpturn: Enable sharpturn in prediction.")
    linearfold_constraints: Optional[str] = Field(default=None, description="[linearfold] constraints: Optional constraint string (? . ( ) ) for constrained prediction. If provided, length must match the sequence.")
    linearfold_shape_file_path: Optional[str] = Field(default=None, description="[linearfold] shape_file_path: Optional path to SHAPE reactivity data file (mutually exclusive with constraints).")
    linearfold_service_url: str = Field(default='http://127.0.0.1:8015/fold', description="[linearfold] service_url: REST endpoint for the LinearFold microservice.")
    linearfold_fasta: bool = Field(default=False, description="[linearfold] --fasta: 上游 --fasta，声明输入为 FASTA 格式。")
    linearfold_verbose: bool = Field(default=False, description="[linearfold] --verbose: 上游 -v/--verbose，输出每个 loop 的能量。")
    vienna_fold_filepath: str = Field(default=None, description="[vienna_fold] filepath: Path to RNA sequence file in workspace, e.g. workspace/seq_xxx.fasta.")
    vienna_fold_temp_c: float = Field(default=37.0, description="[vienna_fold] temp_c: Folding temperature (Celsius).")
    vienna_fold_dangles: int = Field(default=2, description="[vienna_fold] dangles: Dangling-end model.")
    vienna_fold_no_lp: bool = Field(default=False, description="[vienna_fold] no_lp: Disallow lonely pairs.")
    vienna_fold_no_gu: bool = Field(default=False, description="[vienna_fold] no_gu: Disallow GU pairs.")
    vienna_fold_no_closing_gu: bool = Field(default=False, description="[vienna_fold] no_closing_gu: Disallow GU closing pairs.")
    vienna_fold_salt: Optional[float] = Field(default=None, description="[vienna_fold] salt: Salt concentration (M).")
    vienna_fold_no_tetra: bool = Field(default=False, description="[vienna_fold] no_tetra: Omit special hairpin loop energies.")
    vienna_fold_energy_model: Optional[int] = Field(default=None, description="[vienna_fold] energy_model: Energy model index.")
    vienna_fold_nsp: Optional[str] = Field(default=None, description="[vienna_fold] nsp: Non-standard pair specification.")
    vienna_fold_param_file: Optional[str] = Field(default=None, description="[vienna_fold] param_file: Custom parameter file.")
    vienna_fold_constraint: Optional[str] = Field(default=None, description="[vienna_fold] constraint: Hard constraint dot-bracket string.")
    vienna_fold_shape_file: Optional[str] = Field(default=None, description="[vienna_fold] shape_file: Path to SHAPE reactivity data file.")
    vienna_fold_shape_method: str = Field(default='D', description="[vienna_fold] shape_method: SHAPE method: D, Z, or W.")
    vienna_fold_partfunc: bool = Field(default=False, description="[vienna_fold] partfunc: Compute partition function and centroid.")
    vienna_fold_circ: bool = Field(default=False, description="[vienna_fold] circ: Assume circular RNA.")
    vienna_fold_gquad: bool = Field(default=False, description="[vienna_fold] gquad: Include G-quadruplex formation.")
    vienna_fold_service_url: str = Field(default='http://127.0.0.1:8003/fold', description="[vienna_fold] service_url: ViennaRNA fold endpoint.")
    vienna_fold_noDP: bool = Field(default=False, description="[vienna_fold] --noDP: 上游 --noDP，禁止生成 dot-plot PostScript。")
    vienna_fold_maxBPspan: int = Field(default=-1, description="[vienna_fold] --maxBPspan: 上游 --maxBPspan，默认 -1 无限制。")
    vienna_fold_MEA: Any = Field(default=None, description="[vienna_fold] --MEA: 上游 --MEA[=gamma]，基于最大期望精度预测结构。")
    vienna_fold_batch: bool = Field(default=False, description="[vienna_fold] --batch: 上游 --batch，批量使用约束。")
    vienna_fold_canonicalBPonly: bool = Field(default=False, description="[vienna_fold] --canonicalBPonly: 上游 --canonicalBPonly，从约束中移除非规范碱基对。")
    vienna_fold_enforceConstraint: bool = Field(default=False, description="[vienna_fold] --enforceConstraint: 上游 --enforceConstraint，强制约束中圆括号表示的碱基对必须形成。")
    vienna_fold_shapeConversion: str = Field(default='O', description="[vienna_fold] --shapeConversion: 上游 --shapeConversion，SHAPE 到配对概率的转换方法。")
    vienna_fold_verbose: bool = Field(default=False, description="[vienna_fold] --verbose: 上游 -v，输出详细日志。")
    cai_filepath: str = Field(default=None, description="[cai] filepath: Path to CDS sequence file (workspace or absolute); FASTA or plain text. Must be in-frame (length multiple of 3).")
    cai_species: str = Field(default=DEFAULT_CAI_SPECIES, description="[cai] species: Species name for the reference codon usage table. Built-in aliases: human, mouse, rat, fly, worm, zebrafish, arabidopsis, yeast, ecoli, bsubtilis, cho. If no built-in table matches, a custom_codon_table_path must be provided.")
    cai_custom_codon_table_path: Optional[str] = Field(default=None, description="[cai] custom_codon_table_path: Optional path to a custom codon usage JSON file. Format: {\"codon\": {\"aa\": \"X\", \"fraction\": 0.42}, ...}. When provided, ``species`` is used only for metadata/labeling.")
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
    run_gc_tool: bool = Field(default=True, description="Whether to run the GC-content tool on the input sequence(s).")
    run_fold_tool: bool = Field(default=True, description="Whether to run the folding tool on the input sequence(s).")

class MrnaSequenceScoringWorkflow(BaseDomainWorkflow[MrnaSequenceScoringInput, WorkflowResult]):
    input_model = MrnaSequenceScoringInput
    """Score existing mRNA sequences via ``CapabilityRegistry``-driven tools.

    Takes a ``CapabilityRegistry`` like every other workflow; the registry's
    ``ToolExecutor`` performs the actual tool dispatch so trace records are
    still attached to candidates/tasks.  Workflow code does not invoke
    subprocess or HTTP directly; tools remain in ``agent_core.tools``.
    """

    name = "mrna_sequence_scoring"
    task_type = "mrna_sequence_scoring"
    description = "Score existing mRNA sequences with GC, fold, and CAI metrics."
    required_capabilities = [
        "compute_rna_sequence_gc_content",
        "predict_rna_secondary_structure_with_linearfold",
        "predict_rna_secondary_structure",
        "compute_cai_for_cds_sequence",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self.executor = capability_registry.executor

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
            species=getattr(self._current_input, "cai_species", DEFAULT_CAI_SPECIES),
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

        # Service pre-flight: auto-start required microservices when enabled.
        preflight = self._service_preflight_result()
        if preflight is not None:
            preflight.task_id = str(task_id).strip() if task_id is not None and str(task_id).strip() else ""
            return preflight

        candidates = self.generate_candidates(inp)
        if progress_callback:
            progress_callback({
                "event": "generate_complete",
                "candidate_count": len(candidates),
                "workflow": self.name,
            })

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
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

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
    capability_registry: Optional[CapabilityRegistry] = None,
    task_id: Optional[str] = None,
    auto_start_services: bool = True,
) -> WorkflowResult:
    """Functional entry point: builds a default capability registry if omitted.

    ``auto_start_services`` defaults to ``True`` so the standalone entry point
    behaves like ``AgentRunner``-managed workflows.  When passing a custom
    ``capability_registry`` in unit tests or other managed environments, set
    ``auto_start_services=False`` to skip the service pre-flight.
    """
    if capability_registry is None:
        executor = ToolExecutor(build_default_tool_registry(include_demo=False))
        capability_registry = build_default_capability_registry(executor)
    wf = MrnaSequenceScoringWorkflow(capability_registry)
    wf.auto_start_services = auto_start_services
    return wf.run(inp, task_id=task_id)


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