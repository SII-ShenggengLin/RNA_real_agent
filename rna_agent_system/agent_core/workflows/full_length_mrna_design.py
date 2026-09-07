"""Full-length mRNA design workflow — 5'UTR + CDS + 3'UTR (Layer 2).

Protein sequence → CDS candidates via MrnaCdsDesignWorkflow (generate + evaluate)
→ CDS selection → UTR pool → full-length assembly → full-length / UTR
incremental evaluation → full-length scoring → ranking → WorkflowResult.

Two-step design (DECISIONS (bb), 2026-09-07 wet-lab-preparation redesign,
following the GEMORNA Science 2025 full-length protocol "first select the
optimal CDS, then pair UTRs"):

* Step 1 — CDS generation via MrnaCdsDesignWorkflow (delegation unchanged;
  GenNav-λ navigation by default), then CDS evaluation and selection of at
  most one CDS per navigation profile (expression/stability/balanced; the
  static recipe selects its top three), ranked by the shared CDS combined
  score. UTR draws are never resampled per CDS, so CDS ranking cannot be
  confounded by UTR sampling variance.
* Step 2 — one UTR pool per run at the GEMORNA screening scale (12 generated
  5'UTRs + 10 generated 3'UTRs across the short/medium/long presets) plus the
  assertion-verified benchmark pool (BNT162b2 UTR pair, LinearDesign-paper
  5'UTR, natural HBA1 pair — ``agent_core/generation/utr_pool.py``). The pool
  passes the literature-grounded admission rules (U1 no-upstream-AUG,
  U2 no-Class-II-ARE) and the assembled constructs pass the Kozak structure
  gates (U3 cap-entry, U4 scanning-path stall); the 5'UTR shortlist is ranked
  by the certified MRL oracle and a generated UTR is therefore only selected
  when it outranks the clinical benchmarks in-silico.

Ranking governance: the ASF objective set is (cds_component, utr5_mrl,
full_mfe_score). ``utr3_stability`` was demoted from a ranking objective to a
report-only diagnostic dimension (DECISIONS (bb)): its GEMORNA predictor
oracle carries no profiling evidence under this task type (SelfModel
``unprofiled``), and ranking on an unprofiled oracle contradicted the
platform's own governance narrative. The metric is still computed and
reported for every candidate; 3'UTR selection is governed by the admission
rules and the whole-construct objectives only.

Architecture: Full-length workflow reuses MrnaCdsDesignWorkflow for CDS
generation and evaluation; only full-length and UTR metrics are computed here.
Since MrnaCdsDesignWorkflow v2.0.0 the CDS sub-design defaults to GenNav-λ
constraint navigation (the platform default recipe) — ``navigation`` is
delegated, not duplicated: the full-length input's ``navigation`` (tristate,
``None`` = inherit the CDS-layer platform default) passes straight through to
the sub-workflow, whose resolution rule decides the mode from ``design_tool``.
CapGate ranking governance (ASF objective assembly from gate verdicts) and the
per-call audit trail apply on every path.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from agent_core.constants.species import (
    DEFAULT_CAI_SPECIES,
    DEFAULT_RNARL_MODEL_TYPE,
    format_cai_species_aliases,
)
from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.generation import utr_pool
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow, SubWorkflowEvaluator
from agent_core.workflows.evaluators import (
    GCContentEvaluator,
    IRESEvaluator,
    JunctionEvaluator,
    RNASTOPEvaluator,
    SecondaryStructureEvaluator,
    UContentEvaluator,
    UTR3StabilityEvaluator,
    UTR5MrlEvaluator,
)
from agent_core.calibrated.objective_assembly import (
    ObjectiveRef,
    assemble_for_workflow,
)
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
from agent_core.workflows.multi_objective import apply_reference_point_ranking
from agent_core.workflows.scoring import FullLengthScoringFunction
from agent_core.sequence_utils import score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.full_length_mrna_design")

# UTR length presets exposed by GEMORNA
_UTR_PRESETS: list[str] = ["short", "medium", "long"]

# User-facing objectives used for reference-point (ASF) selection and the
# Pareto frontier. Junction scores and utr3_stability remain internal
# diagnostics: utr3_stability was demoted from a ranking objective to a
# report-only diagnostic (DECISIONS (bb)) because its GEMORNA predictor
# oracle carries no profiling evidence under this task type (SelfModel
# ``unprofiled``) and ranking on an unprofiled oracle contradicted the
# platform's governance narrative.
_USER_FACING_OBJECTIVES: tuple[str, ...] = (
    "cds_component",
    "utr5_mrl",
    "full_mfe_score",
)

# Ranking governance (DECISIONS (p)): oracle-backed objectives and their
# evidence sources. ``cds_component`` / ``full_mfe_score`` are deterministic
# compute (DECISIONS (j)) and never enter the mechanism. RNASTOP's
# ``overall_stability`` is a report-only diagnostic, not an ASF dimension, so
# its E18 ranking failure demotes nothing here — its blocked enforce calls
# cost a diagnostic metric only.
_ORACLE_BACKED_OBJECTIVES: dict[str, ObjectiveRef] = {
    "utr5_mrl": ObjectiveRef(
        dim="utr5_mrl",
        tool_name="predict_5utr_mrl_with_gemorna",
        oracle_id="gemorna_5utr_mrl",
    ),
}



class FullLengthMrnaDesignInput(BaseModel):
    """Input for the full-length mRNA design workflow."""
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    gemorna_5utr_utr_length: Any = Field(default='medium', description="[gemorna_5utr] utr_length: UTR length category for the 5'UTR generator. Allowed values are short, medium or long. The value is passed to the compiled UTR model's gen routine.")
    gemorna_5utr_service_url: Any = Field(default='http://127.0.0.1:8004/generate/5utr', description="[gemorna_5utr] service_url: REST endpoint of the GEMORNA 5'UTR microservice.")
    gemorna_3utr_utr_length: Any = Field(default='medium', description="[gemorna_3utr] utr_length: UTR length category for the 3'UTR generator. Allowed values are short, medium or long.")
    gemorna_3utr_service_url: Any = Field(default='http://127.0.0.1:8004/generate/3utr', description="[gemorna_3utr] service_url: REST endpoint of the GEMORNA 3'UTR microservice.")
    gemorna_5utr_pred_filepath: Any = Field(default=None, description="[gemorna_5utr_pred] filepath: Workspace file path containing the 5'UTR RNA sequence. T is converted to U before prediction.")
    gemorna_5utr_pred_service_url: Any = Field(default='http://127.0.0.1:8004/predict/5utr_mrl', description="[gemorna_5utr_pred] service_url: REST endpoint of the GEMORNA 5'UTR MRL prediction microservice.")
    gemorna_3utr_pred_filepath: Any = Field(default=None, description="[gemorna_3utr_pred] filepath: Workspace file path containing the 3'UTR RNA sequence. T is converted to U before prediction.")
    gemorna_3utr_pred_service_url: Any = Field(default='http://127.0.0.1:8004/predict/3utr_stability', description="[gemorna_3utr_pred] service_url: REST endpoint of the GEMORNA 3'UTR stability prediction microservice.")
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
    iresfinder_filepath: str = Field(default=None, description="[iresfinder] filepath: Path to a workspace or repo-relative file containing RNA/DNA sequence or FASTA. Do not pass raw sequence text directly.")
    iresfinder_mode: int = Field(default=0, description="[iresfinder] mode: IRESfinder processing mode aligned with the upstream repository:\n- 0 (default): score each complete sequence as one fragment.\n- 1: extract a subsequence from each FASTA header that ends with ``start_pos end_pos``.\n- 2: split each sequence into sliding windows (requires ``window_size`` and ``step_size``).")
    iresfinder_window_size: int = Field(default=174, description="[iresfinder] window_size: Sliding-window length used only in mode 2 (upstream default: 174).")
    iresfinder_step_size: int = Field(default=50, description="[iresfinder] step_size: Sliding-window step size used only in mode 2 (upstream default: 50).")
    iresfinder_decision_threshold: float = Field(default=0.5, description="[iresfinder] decision_threshold: Probability threshold for labeling a fragment as IRES (upstream default: 0.5).")
    iresfinder_service_url: str = Field(default='http://127.0.0.1:8013/predict', description="[iresfinder] service_url: REST endpoint for the IRESfinder microservice.")
    iresfinder_out: str = Field(default=None, description="[iresfinder] -o/--out (unexposed): 上游 IRESfinder.py 的输出文件参数。")
    rnastop_filepath: Any = Field(default=None, description="[rnastop] filepath: Workspace file path containing the RNA sequence. Non-ACGU characters are removed and T is converted to U.")
    rnastop_service_url: Any = Field(default='http://127.0.0.1:8009/predict/stability', description="[rnastop] service_url: REST endpoint of the RNASTOP stability microservice.")
    rnastop_structure: Any = Field(default=None, description="[rnastop] structure: Optional secondary structure in dot-bracket notation. Must be the same length as the normalized sequence. If omitted, the service folds the sequence with ViennaRNA.")
    rnastop_loop_type: Any = Field(default=None, description="[rnastop] loop_type: Optional loop-type annotation string in the OpenVaccine alphabet (S/M/I/H/B/E). Must match sequence length. If omitted, it is derived from the structure with RNA.db_to_element_string or a fallback S/E string.")
    rnastop_checkpoint_path: Any = Field(default=None, description="[rnastop] checkpoint_path: Optional override for the RNASTOP checkpoint. Default resolves to external_repos/RNASTOP/models/best_model_weights or best_model_weights_withoutDNABERT.")
    rnastop_device: Any = Field(default=None, description="[rnastop] device: Optional torch device string such as cuda:0 or cpu. Default is CUDA if available, otherwise cpu.")
    rnastop_rnafm_model_path: Any = Field(default=None, description="[rnastop] rnafm_model_path: Hidden service parameter not exposed by the wrapper. Default resolves to external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth.")
    rnastop_dnabert_model_path: Any = Field(default=None, description="[rnastop] dnabert_model_path: Hidden service parameter not exposed by the wrapper. Default resolves to external_repos/RNASTOP/DNABERT6 or scripts/DNABERT6.")
    u_content_filepath: str = Field(default=None, description="[u_content] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    u_content_service_url: str = Field(default='http://127.0.0.1:8020/u-content', description="[u_content] service_url: POST endpoint for U content microservice.")
    u_content_timeout_seconds: float = Field(default=120.0, description="[u_content] timeout_seconds: HTTP request timeout in seconds.")
    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    truncate_n_terminal: Optional[int] = Field(
        default=None,
        description="If set, remove the first N amino acids of protein_sequence before design.",
    )
    truncate_c_terminal: Optional[int] = Field(
        default=None,
        description="If set, remove the last N amino acids of protein_sequence before design.",
    )
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = Field(default="all", description="CDS design engine(s) to run. 'lineardesign' uses LinearDesign; 'rnarl' uses RNARL; 'gemorna' uses GEMORNA; 'all' is the platform default recipe — under the v2.0.0 default this delegates to GenNav-λ constraint navigation unless navigation is explicitly disabled.")
    navigation: Optional[bool] = Field(
        default=None,
        description=(
            "GenNav-λ constraint navigation for the CDS sub-design, delegated "
            "verbatim to MrnaCdsDesignWorkflow (single source of the default "
            "policy). None (unset) = inherit the CDS-layer platform default "
            "(navigation under the default 'all' recipe; a pinned design_tool "
            "engine runs its static path); True/False always override."
        ),
    )
    lambda_value: Optional[float] = Field(
        default=None,
        description="LinearDesign MFE/CAI balance (0-20). Required when design_tool='lineardesign'; ignored otherwise.",
    )
    model_type: str = Field(
        default=DEFAULT_RNARL_MODEL_TYPE, description="RNARL model type."
    )
    cai_species: str = Field(
        default=DEFAULT_CAI_SPECIES,
        description=f"Species for CAI computation. Built-in: {format_cai_species_aliases()}.",
    )
    utr_mode: Literal["short", "medium", "long", "all"] = Field(default="all", description="UTR pool presets drawn from GEMORNA generation (DECISIONS (bb)): 'all' draws 12 5'UTRs + 10 3'UTRs across short/medium/long (the GEMORNA paper's screening scale); a single preset draws only that preset. The assertion-verified benchmark UTR pool (BNT162b2 pair, LinearDesign-paper 5'UTR, natural HBA1 pair) is always included and competes in the same admission + ASF ranking.")
    run_fold: bool = Field(default=True, description="Whether to fold the full-length mRNA sequence for secondary-structure evaluation.")
    run_gc: bool = Field(default=True, description="Whether to compute GC-content of the full-length mRNA sequence.")
    reference_point: Optional[dict[str, float]] = Field(
        default=None,
        description=(
            "Per-objective reference point for Achievement Scalarizing Function selection. "
            "If omitted, a utopian point is derived from the candidate pool. "
            "User-facing keys: utr5_mrl, full_mfe_score. "
            "Use target_cds_mfe and target_cds_cai to specify CDS objectives; they are "
            "automatically converted into the internal cds_component. "
            "utr3_stability is no longer a ranking objective (demoted to a report-only "
            "diagnostic, DECISIONS (bb)) and is rejected here loudly."
        ),
    )
    target_cds_mfe: Optional[float] = Field(
        default=None,
        description="User-aspired CDS MFE (kcal/mol). More negative = more stable. "
                    "Must be provided together with target_cds_cai to compute cds_component reference.",
    )
    target_cds_cai: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="User-aspired CAI value. "
                    "Must be provided together with target_cds_mfe to compute cds_component reference.",
    )

    @field_validator("lambda_value")
    @classmethod
    def _require_lambda_for_lineardesign(
        cls, v: Optional[float], info: Any
    ) -> Optional[float]:
        design_tool = info.data.get("design_tool")
        if design_tool == "lineardesign" and v is None:
            raise ValueError("lambda_value is required when design_tool='lineardesign'")
        return v
    @field_validator("truncate_n_terminal", "truncate_c_terminal")
    @classmethod
    def _validate_terminal_truncation(
        cls, v: Optional[int], info: Any
    ) -> Optional[int]:
        """Truncation length must be a positive integer and not exceed the protein length."""
        if v is None:
            return v
        if not isinstance(v, int) or v <= 0:
            raise ValueError("terminal truncation length must be a positive integer")
        protein = info.data.get("protein_sequence")
        if protein and v > len(protein):
            raise ValueError(
                "truncation length " + str(v) + " exceeds protein_sequence length " + str(len(protein))
            )
        return v

    @model_validator(mode="after")
    def _check_mutually_exclusive_truncation(self) -> "FullLengthMrnaDesignInput":
        """Only one terminal truncation direction may be specified."""
        if self.truncate_n_terminal is not None and self.truncate_c_terminal is not None:
            raise ValueError("truncate_n_terminal and truncate_c_terminal are mutually exclusive")
        return self

    @model_validator(mode="after")
    def _validate_reference_point(self) -> "FullLengthMrnaDesignInput":
        """Validate reference_point keys and convert target_cds_mfe/cai.

        The internal cds_component key is not accepted directly from users;
        it is synthesized from target_cds_mfe and target_cds_cai when provided.
        """
        if self.reference_point is not None:
            allowed = {"utr5_mrl", "full_mfe_score"}
            unknown = set(self.reference_point.keys()) - allowed
            if unknown:
                if "utr3_stability" in unknown:
                    raise ValueError(
                        "reference_point key 'utr3_stability' is no longer a ranking "
                        "objective: the GEMORNA 3'UTR stability predictor is unprofiled "
                        "under this task type and was demoted to a report-only "
                        "diagnostic dimension (DECISIONS (bb)). Allowed: "
                        f"{allowed}. Use target_cds_mfe and target_cds_cai to specify "
                        "CDS objectives."
                    )
                raise ValueError(
                    f"reference_point contains unknown objectives: {unknown}. "
                    f"Allowed: {allowed}. "
                    "Use target_cds_mfe and target_cds_cai to specify CDS objectives."
                )

        # Convert target CDS MFE/CAI into internal cds_component reference point.
        has_target_mfe = self.target_cds_mfe is not None
        has_target_cai = self.target_cds_cai is not None
        if has_target_mfe or has_target_cai:
            if not (has_target_mfe and has_target_cai):
                raise ValueError(
                    "target_cds_mfe and target_cds_cai must be provided together"
                )
            if self.target_cds_cai <= 0.0:
                raise ValueError("target_cds_cai must be in (0, 1]")
            codon_count = len(self.protein_sequence)
            cds_length_nt = codon_count * 3
            if cds_length_nt > 0:
                target_cds_component = (
                    -self.target_cds_mfe
                    + codon_count * math.log(self.target_cds_cai)
                ) / cds_length_nt
                rp = dict(self.reference_point) if self.reference_point else {}
                rp["cds_component"] = target_cds_component
                self.reference_point = rp

        return self


def score_full_length_mrna_candidate(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """Return per-module raw scores for ASF-based reference-point ranking in rank_and_format.

    Args:
        metrics: Raw metrics dict produced by ``evaluate()``. Expected keys:
            - ``cds_cai`` (float | None): CAI score of the CDS.
            - ``cds_mfe`` (float | None): MFE (kcal/mol) of the CDS.
            - ``cds_length`` (int): CDS length in nucleotides.
            - ``utr5_predicted_mrl`` (float | None): Predicted mean ribosomal load of 5'UTR.
            - ``utr3_predicted_stability`` (float | None): Predicted stability of 3'UTR.

    Returns:
        dict[str, float | None]: Score components with keys:
            - ``cds_component``: ``combined_score / cds_length`` (normalized CDS score),
              or ``None`` when ``cds_length`` is 0 or CDS metrics are missing.
            - ``cds_combined_score``: Classic ``-mfe + codon_count * log(CAI)`` score.
            - ``utr5_mrl``: Raw predicted MRL value, or ``None`` if absent.
            - ``utr3_stability``: Raw predicted stability value, or ``None`` if absent.
    """

    cds_length = int(metrics.get("cds_length", 0))

    # CDS component: classic combined score (-mfe + codon_count * log(CAI))
    cds_bundle = {
        "mfe_kcal_per_mol": metrics.get("cds_mfe"),
        "cai_score": metrics.get("cds_cai"),
        "sequence_length": cds_length,
    }
    cds_scores = score_mrna_candidate(cds_bundle)
    cds_combined_score = cds_scores.get("combined_score", 0.0)
    cds_component = cds_combined_score / cds_length if cds_length > 0 else None

    # 5'UTR MRL component
    utr5_mrl = metrics.get("utr5_predicted_mrl")
    utr5_component = float(utr5_mrl) if utr5_mrl is not None else None

    # 3'UTR stability component
    utr3_stability = metrics.get("utr3_predicted_stability")
    utr3_component = float(utr3_stability) if utr3_stability is not None else None

    return {
        "cds_component": cds_component,
        "cds_combined_score": float(cds_combined_score),
        "utr5_mrl": utr5_component,
        "utr3_stability": utr3_component,
    }


class FullLengthMrnaDesignWorkflow(
    BaseDomainWorkflow[FullLengthMrnaDesignInput, WorkflowResult]
):
    """Protein → CDS (via MrnaCdsDesignWorkflow) + UTR → incremental eval → ASF rank."""

    name = "full_length_mrna_design"
    task_type = "full_length_mrna"
    input_model = FullLengthMrnaDesignInput
    description = (
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence: "
        "two-step design (DECISIONS (bb)) — CDS sub-design via "
        "MrnaCdsDesignWorkflow (GenNav-λ constraint navigation by default) "
        "with per-profile CDS selection, then one UTR pool per run (GEMORNA "
        "screening-scale draws + verified benchmark UTRs) under "
        "literature-grounded admission rules and Kozak structure gates, "
        "incremental full-length + UTR evaluation, CapGate-governed ASF "
        "ranking over (cds_component, utr5_mrl, full_mfe_score)."
    )
    required_capabilities = [
        # UTR design / prediction
        "design_5utr_with_gemorna",
        "design_3utr_with_gemorna",
        "predict_5utr_mrl_with_gemorna",
        "predict_3utr_stability_with_gemorna",
        # CDS generation / evaluation (delegated to MrnaCdsDesignWorkflow)
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "compute_cai_for_cds_sequence",
        "compute_rna_sequence_gc_content",
        "compute_dot_bracket_unpaired_fraction",
        # Shared folding / metrics
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "predict_mrna_stability_with_rnastop",
        "compute_rna_sequence_u_content",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._cds_state_writeback: dict[str, Any] = {}
        self._cds_evaluator = SubWorkflowEvaluator(
            lambda: self._create_cds_workflow(),
            sequence_key="cds_sequence",
            key_map={
                "mfe_kcal_per_mol": "cds_mfe",
                "cai_score": "cds_cai",
                "gc_content": "cds_gc",
                "sequence_length": "cds_length",
                "u_fraction": "cds_u_fraction",
            },
        )
        self._u_content_evaluator = UContentEvaluator(self.capabilities)
        self._full_gc_evaluator = GCContentEvaluator(self.capabilities)
        self._full_fold_evaluator = SecondaryStructureEvaluator(
            self.capabilities, run_fold=True
        )
        self._ires_evaluator = IRESEvaluator(self.capabilities)
        self._rnastop_evaluator = RNASTOPEvaluator(self.capabilities)
        self._utr5_fold_evaluator = SecondaryStructureEvaluator(
            self.capabilities, run_fold=True
        )
        self._utr5_mrl_evaluator = UTR5MrlEvaluator(self.capabilities)
        self._utr3_stability_evaluator = UTR3StabilityEvaluator(self.capabilities)
        self._junction_evaluator = JunctionEvaluator(self.capabilities)

    def _create_cds_workflow(self) -> MrnaCdsDesignWorkflow:
        """Factory for the CDS sub-workflow used by SubWorkflowEvaluator."""
        wf = MrnaCdsDesignWorkflow(self.capabilities)
        # Inherit the parent's auto-start policy so ad-hoc tests of the child
        # workflow also get service pre-flight.
        wf.auto_start_services = self.auto_start_services
        inp = self._workflow_state.get("_full_length_input")
        if inp:
            wf._run_fold = inp.run_fold
            wf._run_gc = inp.run_gc
        return wf

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: FullLengthMrnaDesignInput | dict[str, Any],
        *,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> WorkflowResult:
        """Generate → evaluate → score → rank, with per-run state and writeback.

        Resets per-run workflow state (which carries the tool-level parameter
        overrides from the input model), runs the base orchestration, then
        attaches the merged state writeback so every run stays auditable.
        """
        if isinstance(inp, dict):
            inp = FullLengthMrnaDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._cds_state_writeback = {}  # reset per run
        self._workflow_state["_full_length_input"] = inp

        result = super().run(inp, progress_callback=progress_callback)
        return self._finalize_result(result)

    def _finalize_result(self, result: WorkflowResult) -> WorkflowResult:
        """Attach the merged state writeback (params + sub-workflow state)."""
        inp = self._workflow_state.get("_full_length_input")
        if inp is None:
            return result

        merged_wb = dict(self._workflow_state)
        for key, value in self._cds_state_writeback.items():
            if isinstance(value, dict) and isinstance(merged_wb.get(key), dict):
                merged_wb[key].update(value)
            else:
                merged_wb[key] = value
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: FullLengthMrnaDesignInput) -> list[Candidate]:
        """Generate full-length candidates via the two-step design (DECISIONS (bb)).

        Step 1: Delegate CDS generation to MrnaCdsDesignWorkflow (GenNav-λ
        navigation by default: up to 15 delivered CDS; static recipe up to 6),
        evaluate every delivered CDS once (cached by sequence for ``evaluate()``)
        and select at most one CDS per navigation profile — the static recipe
        selects its top three — by the shared CDS combined score.
        Step 2: Build one UTR pool per run (GEMORNA screening-scale draws +
        benchmark UTRs), apply the literature-grounded admission rules, rank
        the 5'UTR shortlist by the certified MRL oracle, and assemble the
        selected CDS × shortlist combinations under the Kozak structure gates.
        Total: ≤ 3 CDS × ≤ 6 × ≤ 6 = ≤ 108 candidates (before gates).
        """
        # ── Step 1: Generate CDS candidates via the CDS workflow ──
        # navigation passes through verbatim: None = inherit the CDS-layer
        # platform default (v2.0.0 GenNav-λ under the default 'all' recipe).
        cds_inp = MrnaCdsDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=inp.design_tool,
            navigation=inp.navigation,
            lambda_value=inp.lambda_value,
            model_type=inp.model_type,
            cai_species=inp.cai_species,
            run_fold=inp.run_fold,
            run_gc=inp.run_gc,
        )
        cds_workflow = MrnaCdsDesignWorkflow(self.capabilities)
        cds_candidates = cds_workflow.generate_candidates(cds_inp)
        # Capture design-phase state writeback from the sub-workflow
        self._cds_state_writeback = dict(cds_workflow._workflow_state)

        if not cds_candidates:
            _LOGGER.warning("cds_workflow produced no candidates")
            return []

        _LOGGER.info(
            "cds_workflow_generated candidates=%d",
            len(cds_candidates),
        )

        # ── Step 1b: two-step design — evaluate and select ≤3 CDS ──
        selected_cds = self._select_cds_for_full_length(cds_candidates)
        if not selected_cds:
            _LOGGER.warning("cds_selection produced no candidates")
            return []

        # ── Step 2: UTR pool (built once per run) ──
        pool = self._build_utr_pool(inp)

        # ── Step 3: assemble full-length candidates under the Kozak gates ──
        full_candidates: list[Candidate] = []
        gate_rejects: list[dict[str, Any]] = []
        fold_cache: dict[str, Optional[float]] = {}

        def fold_mfe(seq: str) -> Optional[float]:
            if seq not in fold_cache:
                fold_cache[seq] = self._fold_mfe(seq)
            return fold_cache[seq]

        for cds_cand in selected_cds:
            cds_seq = cds_cand.sequence
            if len(cds_seq) % 3 != 0:
                _LOGGER.warning(
                    "cds_length_not_multiple_of_3 source=%s len=%d",
                    cds_cand.source,
                    len(cds_seq),
                )
                continue

            for u5 in pool["utr5_shortlist"]:
                for u3 in pool["utr3_shortlist"]:
                    full_seq = u5["sequence"] + cds_seq + u3["sequence"]
                    cap = utr_pool.check_cap_entry(full_seq, fold_mfe)
                    stall = utr_pool.check_scanning_path(full_seq, len(u5["sequence"]), fold_mfe)
                    if not (cap["ok"] and stall["ok"]):
                        gate_rejects.append(
                            {
                                "cds_source": cds_cand.source,
                                "utr5_id": u5["id"],
                                "utr3_id": u3["id"],
                                "cap_entry": cap,
                                "scanning_path": stall,
                            }
                        )
                        continue
                    candidate = Candidate(
                        sequence=full_seq,
                        sequence_type="mrna",
                        source=f"full_length:{cds_cand.source}:utr5_{u5['id']}:utr3_{u3['id']}",
                        metadata={
                            "utr5_sequence": u5["sequence"],
                            "cds_sequence": cds_seq,
                            "utr3_sequence": u3["sequence"],
                            "utr5_length": len(u5["sequence"]),
                            "utr3_length": len(u3["sequence"]),
                            "utr5_id": u5["id"],
                            "utr3_id": u3["id"],
                            "utr5_origin": u5["origin"],
                            "utr3_origin": u3["origin"],
                            "utr5_preset": u5["preset"],
                            "utr3_preset": u3["preset"],
                            "cds_length": len(cds_seq),
                            "cds_source": cds_cand.source,
                            "cds_nav_bands": list(cds_cand.metadata.get("nav_bands", [])),
                            "protein_sequence": inp.protein_sequence,
                            "cai_species": inp.cai_species,
                            "kozak_gates": {"cap_entry": cap, "scanning_path": stall},
                        },
                    )
                    full_candidates.append(candidate)
                    _LOGGER.info(
                        "full_candidate_generated cds_source=%s utr5=%s utr3=%s total_len=%d",
                        cds_cand.source,
                        u5["id"],
                        u3["id"],
                        len(full_seq),
                    )

        self._workflow_state.setdefault("_utr_pool", {})["gate_rejects"] = gate_rejects

        # Deduplicate by full sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in full_candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

        if not unique:
            # Benchmarks always pass U1–U4 (asset assertion + A-rich leaders),
            # so an empty pool is a hard anomaly — surface it loudly.
            self._workflow_state["_utr_assembly_empty"] = (
                f"all {len(gate_rejects)} assembled combinations rejected by Kozak gates"
            )
            _LOGGER.error("utr_assembly_empty rejects=%d", len(gate_rejects))

        _LOGGER.info(
            "full_candidates_generated total=%d unique=%d gate_rejects=%d",
            len(full_candidates),
            len(unique),
            len(gate_rejects),
        )
        return unique

    # ─────────────────────────────────────────────────────────────────────────
    # Two-step design helpers (DECISIONS (bb))
    # ─────────────────────────────────────────────────────────────────────────

    def _select_cds_for_full_length(
        self, cds_candidates: list[Candidate]
    ) -> list[Candidate]:
        """Step-1 CDS selection: evaluate every delivered CDS once, then keep
        at most one per navigation profile (best CDS combined score; the
        static recipe keeps its top three), deduplicated by sequence.

        The shared CDS scoring lives in the CDS layer
        (``score_full_length_mrna_candidate`` → ``score_mrna_candidate``);
        this method only decides the full-length pairing policy. Evaluation
        runs through the same cached ``SubWorkflowEvaluator`` used by
        ``evaluate()``, so no CDS is folded twice.
        """
        context: dict[str, Any] = {"workflow_state": self._workflow_state}
        scored: list[tuple[float, Candidate]] = []
        for cand in cds_candidates:
            if len(cand.sequence) % 3 != 0:
                _LOGGER.warning(
                    "cds_length_not_multiple_of_3 source=%s len=%d",
                    cand.source,
                    len(cand.sequence),
                )
                continue
            cand.metadata.setdefault("cds_sequence", cand.sequence)
            metrics = self._cds_evaluator.evaluate(cand, context)
            comp = score_full_length_mrna_candidate(metrics).get("cds_component")
            scored.append((comp if comp is not None else float("-inf"), cand))

        if not scored:
            return []

        has_nav = any(c.metadata.get("nav_bands") for _, c in scored)
        selected: list[Candidate] = []
        seen_seqs: set[str] = set()

        def _try_pick(cand: Candidate) -> None:
            if cand.sequence in seen_seqs:
                return
            seen_seqs.add(cand.sequence)
            selected.append(cand)

        if has_nav:
            bands: list[str] = []
            for _, cand in scored:
                for band in cand.metadata.get("nav_bands", []):
                    if band not in bands:
                        bands.append(band)
            for band in bands:
                group_best = max(
                    (pair for pair in scored if band in pair[1].metadata.get("nav_bands", [])),
                    key=lambda pair: pair[0],
                    default=None,
                )
                if group_best is not None:
                    _try_pick(group_best[1])
        else:
            for _, cand in sorted(scored, key=lambda pair: pair[0], reverse=True)[:3]:
                _try_pick(cand)

        # Fill up to three with the global best unselected CDS (keeps pool
        # diversity when a band's best duplicates another band's pick).
        for _, cand in sorted(scored, key=lambda pair: pair[0], reverse=True):
            if len(selected) >= 3:
                break
            _try_pick(cand)

        self._workflow_state["_cds_selection"] = {
            "policy": "two_step_best_per_band (DECISIONS (bb))",
            "pool_size": len(scored),
            "selected": [
                {
                    "source": c.source,
                    "cds_component": next(
                        (comp for comp, cc in scored if cc is c), None
                    ),
                    "nav_bands": list(c.metadata.get("nav_bands", [])),
                }
                for c in selected
            ],
        }
        _LOGGER.info(
            "cds_selected_for_full_length pool=%d selected=%d sources=%s",
            len(scored),
            len(selected),
            [c.source for c in selected],
        )
        return selected

    def _build_utr_pool(self, inp: FullLengthMrnaDesignInput) -> dict[str, Any]:
        """Build the per-run UTR pool (DECISIONS (bb)).

        GEMORNA draws at the paper's screening scale + the benchmark UTRs,
        admission-screened by U1/U2; the 5'UTR shortlist is ranked by the
        certified MRL oracle, so a generated UTR must outrank the clinical
        benchmarks in-silico to be selected. The 3'UTR shortlist is
        admission-survival order (benchmarks first, then generation order) —
        a compute cap, not a ranking: ``utr3_stability`` is a report-only
        diagnostic (DECISIONS (bb)) and no unprofiled oracle orders the pool.
        """
        presets = self._resolve_utr_presets(inp.utr_mode)
        pool5: list[dict[str, Any]] = []
        pool3: list[dict[str, Any]] = []

        for e in utr_pool.load_utr_benchmarks():
            entry = {
                "id": e["id"],
                "origin": "benchmark",
                "preset": "benchmark",
                "sequence": e["sequence"],
                "length_nt": e["length_nt"],
            }
            if e["side"] == "5utr":
                entry["admission"] = utr_pool.admit_utr5(e["sequence"])
                pool5.append(entry)
            else:
                entry["admission"] = utr_pool.admit_utr3(e["sequence"])
                pool3.append(entry)

        for preset in presets:
            for k in range(1, utr_pool.GEMORNA_5UTR_DRAWS_PER_PRESET + 1):
                seq = self._generate_utr("5utr", preset)
                if seq is None:
                    continue
                pool5.append(
                    {
                        "id": f"gemorna_5utr_{preset}_{k}",
                        "origin": "gemorna",
                        "preset": preset,
                        "sequence": seq,
                        "length_nt": len(seq),
                        "admission": utr_pool.admit_utr5(seq),
                    }
                )
        for preset in presets:
            draws = utr_pool.GEMORNA_3UTR_DRAWS_PER_PRESET.get(preset, 0)
            for k in range(1, draws + 1):
                seq = self._generate_utr("3utr", preset)
                if seq is None:
                    continue
                pool3.append(
                    {
                        "id": f"gemorna_3utr_{preset}_{k}",
                        "origin": "gemorna",
                        "preset": preset,
                        "sequence": seq,
                        "length_nt": len(seq),
                        "admission": utr_pool.admit_utr3(seq),
                    }
                )

        survivors5 = [e for e in pool5 if e["admission"]["ok"]]
        survivors3 = [e for e in pool3 if e["admission"]["ok"]]

        # 5'UTR ranking: certified MRL oracle over admission survivors. The
        # evaluator reuses the audited capability path (pseudo-candidate).
        context: dict[str, Any] = {"workflow_state": self._workflow_state}
        for e in survivors5:
            pseudo = Candidate(
                sequence=e["sequence"],
                sequence_type="rna",
                source=f"utr_pool:{e['id']}",
                metadata={"utr5_sequence": e["sequence"]},
            )
            mrl_metrics = self._utr5_mrl_evaluator.evaluate(pseudo, context)
            e["predicted_mrl"] = mrl_metrics.get("utr5_predicted_mrl")
        survivors5.sort(
            key=lambda e: (
                -(e["predicted_mrl"] if e["predicted_mrl"] is not None else float("-inf")),
                # stable tie-break keeps benchmark entries ahead on exact ties
                # (including the no-oracle MRL=None case)
                0 if e["origin"] == "benchmark" else 1,
                e["id"],
            )
        )
        shortlist5 = survivors5[: utr_pool.UTR5_SHORTLIST_MAX]

        # 3'UTR shortlist: admission-survival order (benchmarks first, then
        # generation order) capped for compute — explicitly NOT oracle-ranked.
        shortlist3 = sorted(
            survivors3, key=lambda e: (0 if e["origin"] == "benchmark" else 1, e["id"])
        )[: utr_pool.UTR3_SHORTLIST_MAX]

        pool_state = {
            "policy": "gemorna_screening_scale_plus_benchmarks (DECISIONS (bb))",
            "utr5_pool": pool5,
            "utr3_pool": pool3,
            "utr5_shortlist": shortlist5,
            "utr3_shortlist": shortlist3,
        }
        expected5 = len(presets) * utr_pool.GEMORNA_5UTR_DRAWS_PER_PRESET
        expected3 = sum(utr_pool.GEMORNA_3UTR_DRAWS_PER_PRESET.get(p, 0) for p in presets)
        pool_state["gemorna_draw_failures_5utr"] = expected5 - sum(
            1 for e in pool5 if e["origin"] == "gemorna"
        )
        pool_state["gemorna_draw_failures_3utr"] = expected3 - sum(
            1 for e in pool3 if e["origin"] == "gemorna"
        )
        self._workflow_state["_utr_pool"] = pool_state
        _LOGGER.info(
            "utr_pool_built pool5=%d(surv=%d,shortlist=%d) pool3=%d(surv=%d,shortlist=%d)",
            len(pool5), len(survivors5), len(shortlist5),
            len(pool3), len(survivors3), len(shortlist3),
        )
        return pool_state

    def _fold_mfe(self, seq: str) -> Optional[float]:
        """Fold a short subsequence via LinearFold (ViennaRNA fallback) for
        the Kozak admission gates — same invoke pattern as
        :class:`SecondaryStructureEvaluator`. Returns None on any failure
        (the gate then records ``unverified`` and never rejects on outage)."""
        try:
            fp = save_sequence(seq, prefix="utr_admission_fold")
            args = {"filepath": fp}
            for cap_name in (
                "predict_rna_secondary_structure_with_linearfold",
                "predict_rna_secondary_structure",
            ):
                if not self.capabilities.has(cap_name):
                    continue
                res = self.capabilities.get(cap_name).invoke(
                    args, state=self._workflow_state
                )
                if res.success:
                    mfe = res.output.get("mfe")
                    return float(mfe) if mfe is not None else None
            return None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("utr_admission_fold_failed err=%s", exc)
            return None

    def _resolve_utr_presets(self, utr_mode: str) -> list[str]:
        if utr_mode == "all":
            return list(_UTR_PRESETS)
        if utr_mode in _UTR_PRESETS:
            return [utr_mode]
        return list(_UTR_PRESETS)

    def _generate_utr(self, utr_type: str, preset: str) -> Optional[str]:
        """Generate a single UTR sequence via GEMORNA.

        *utr_type* is ``5utr`` or ``3utr``.
        Returns the generated sequence string, or ``None`` on failure.
        """
        cap_name = f"design_{utr_type}_with_gemorna"
        if not self.capabilities.has(cap_name):
            _LOGGER.warning("utr_capability missing: %s", cap_name)
            return None

        try:
            cap = self.capabilities.get(cap_name)
            cap_result = cap.invoke(
                {"utr_length": preset},
                state=self._workflow_state,
            )
            if not cap_result.success:
                _LOGGER.warning(
                    "utr_design failed type=%s preset=%s error=%s",
                    utr_type,
                    preset,
                    cap_result.error,
                )
                return None

            seq = str(cap_result.output.get("generated_sequence", ""))
            if not seq:
                _LOGGER.warning("utr_design empty type=%s preset=%s", utr_type, preset)
                return None

            return seq
        except Exception as exc:
            _LOGGER.error("utr_design exception type=%s preset=%s err=%s", utr_type, preset, exc)
            return None

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run incremental evaluation on a full-length candidate.

        CDS metrics are evaluated via :class:`SubWorkflowEvaluator` wrapping
        :class:`MrnaCdsDesignWorkflow`. Full-length and UTR metrics are
        evaluated via reusable evaluator components.
        """
        seq = candidate.sequence
        utr5 = candidate.metadata.get("utr5_sequence", "")
        cds = candidate.metadata.get("cds_sequence", "")
        utr3 = candidate.metadata.get("utr3_sequence", "")

        context: dict[str, Any] = {"workflow_state": self._workflow_state}

        # ── CDS metrics via SubWorkflowEvaluator (cached by sequence) ──
        cds_metrics = self._cds_evaluator.evaluate(candidate, context)

        # Save full-length sequence to workspace
        full_fp = save_sequence(seq, prefix="full_mrna")
        candidate.metadata["workspace_filepath"] = full_fp

        # ── Full-length fold (run on candidate so structure is in metadata) ──
        full_fold = self._full_fold_evaluator.evaluate(candidate, context)
        # Expose the full-length fold so JunctionEvaluator can reuse the
        # unconstrained MFE for its ddG metric instead of re-folding.
        context["full_length_fold"] = {
            "mfe": full_fold.get("mfe_kcal_per_mol"),
            "fold_tool": full_fold.get("fold_tool"),
        }

        # ── Junction evaluation ──
        junction = self._junction_evaluator.evaluate(candidate, context)

        # ── Full-length U content and GC content ──
        full_u_content = self._u_content_evaluator.evaluate(candidate, context)
        full_gc = self._full_gc_evaluator.evaluate(candidate, context)

        # NOTE: IRES and 5'UTR fold evaluators are skipped in benchmark mode
        # to avoid timeout on large candidate sets. RNASTOP is evaluated
        # because overall stability is an important full-length mRNA metric.
        rnastop = self._rnastop_evaluator.evaluate(candidate, context)
        ires: dict[str, Any] = {}
        utr5_fold: dict[str, Any] = {}

        # 5'UTR MRL and 3'UTR stability evaluation (GEMORNA)
        utr5_mrl = self._utr5_mrl_evaluator.evaluate(candidate, context)
        utr3_stab = self._utr3_stability_evaluator.evaluate(candidate, context)

        # Compute length-normalized MFE and paired fraction from structure
        full_mfe = full_fold.get("mfe_kcal_per_mol")
        total_len = len(seq)
        mfe_per_nt = (float(full_mfe) / total_len) if full_mfe is not None and total_len > 0 else None

        structure = full_fold.get("structure", "")
        paired_count = structure.count("(") + structure.count(")") if structure else 0
        paired_fraction = (paired_count / len(structure)) if structure else None

        metrics: dict[str, Any] = {
            "full_length_mfe": full_mfe,
            "full_length_structure": structure,
            "full_mfe_per_nt": mfe_per_nt,
            "full_paired_fraction": paired_fraction,
            "cds_cai": cds_metrics.get("cds_cai"),
            "cds_mfe": cds_metrics.get("cds_mfe"),
            "cds_gc": cds_metrics.get("cds_gc"),
            "cds_u_fraction": cds_metrics.get("cds_u_fraction"),
            "cds_length": cds_metrics.get("cds_length", len(cds)),
            "utr5_ires_potential": ires.get("utr5_ires_potential", 0),
            "utr5_length": len(utr5),
            "utr3_length": len(utr3),
            "utr5_mfe": utr5_fold.get("mfe_kcal_per_mol"),
            "overall_stability": rnastop.get("rnastop_overall_stability"),
            "total_length": total_len,
            "full_u_fraction": full_u_content.get("u_fraction"),
            "full_length_gc": full_gc.get("gc_content"),
            "fold_tool": full_fold.get("fold_tool", "unknown"),
            "utr5_predicted_mrl": utr5_mrl.get("utr5_predicted_mrl"),
            "utr3_predicted_stability": utr3_stab.get("utr3_predicted_stability"),
            # Junction metrics
            "junction_5utr_cds_mfe": junction.get("junction_5utr_cds_mfe"),
            "junction_5utr_cds_mfe_per_nt": junction.get("junction_5utr_cds_mfe_per_nt"),
            "junction_5utr_cds_length": junction.get("junction_5utr_cds_length"),
            "junction_5utr_cds_structure": junction.get("junction_5utr_cds_structure"),
            "junction_5utr_cds_gc_diff": junction.get("junction_5utr_cds_gc_diff"),
            "junction_5utr_cds_left_gc": junction.get("junction_5utr_cds_left_gc"),
            "junction_5utr_cds_right_gc": junction.get("junction_5utr_cds_right_gc"),
            # Full-length ddG report metrics at the 5'UTR-CDS junction (W1/W2)
            "junction_5utr_cds_ddg_open_w1": junction.get("junction_5utr_cds_ddg_open_w1"),
            "junction_5utr_cds_ddg_open_w2": junction.get("junction_5utr_cds_ddg_open_w2"),
            "junction_5utr_cds_ddg_w1_start": junction.get("junction_5utr_cds_ddg_w1_start"),
            "junction_5utr_cds_ddg_w1_end": junction.get("junction_5utr_cds_ddg_w1_end"),
            "junction_5utr_cds_ddg_w2_start": junction.get("junction_5utr_cds_ddg_w2_start"),
            "junction_5utr_cds_ddg_w2_end": junction.get("junction_5utr_cds_ddg_w2_end"),
            "junction_cds_3utr_mfe": junction.get("junction_cds_3utr_mfe"),
            "junction_cds_3utr_mfe_per_nt": junction.get("junction_cds_3utr_mfe_per_nt"),
            "junction_cds_3utr_length": junction.get("junction_cds_3utr_length"),
            "junction_cds_3utr_structure": junction.get("junction_cds_3utr_structure"),
            "junction_cds_3utr_gc_diff": junction.get("junction_cds_3utr_gc_diff"),
            "junction_cds_3utr_left_gc": junction.get("junction_cds_3utr_left_gc"),
            "junction_cds_3utr_right_gc": junction.get("junction_cds_3utr_right_gc"),
        }

        candidate.metadata["metrics_bundle"] = metrics
        candidate.metadata["fold_tool"] = full_fold.get("fold_tool")
        candidate.metadata["utr5_mfe"] = metrics.get("utr5_mfe")
        return metrics

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        # Per-module raw scores for reference-point optimization.
        return FullLengthScoringFunction().score(metrics)

    def _apply_reference_point_and_pareto(
        self,
        candidates: list[Candidate],
        inp: FullLengthMrnaDesignInput,
    ) -> tuple[Candidate | None, list[Candidate], dict[str, float] | None, dict[str, float]]:
        """Reference-point optimization + Pareto frontier (default behaviour).

        Thin wrapper over the shared ``apply_reference_point_ranking`` layer
        (ASF audit 2026-08-20): per-candidate missing dimensions are imputed
        at pool-worst, pool-wide unmeasured dimensions drop for everyone, and
        a partial user reference point restricts the ranking loudly.

        Returns ``(best_candidate, pareto_frontier, raw_reference_point, candidate_asf_map)``.
        """
        objectives = list(_USER_FACING_OBJECTIVES)
        # Ranking governance (DECISIONS (p)): assemble the objective set from
        # CapGate verdicts before ranking — mode-independent; demoted dims
        # drop for the whole pool equally and survive as annotations.
        assembly = assemble_for_workflow(
            objectives, _ORACLE_BACKED_OBJECTIVES, self.task_type
        )
        self._workflow_state["_ranking_governance"] = assembly.to_state()
        ranking = apply_reference_point_ranking(
            candidates,
            assembly.ranking_dims,
            inp.reference_point,
            maximize={key: True for key in assembly.ranking_dims},
        )
        notes: list[str] = []
        if ranking.dropped_dims:
            notes.append(f"dropped_dims(unmeasured)={ranking.dropped_dims}")
        if ranking.partial_reference:
            notes.append(
                f"partial_reference_point: ranking restricted to "
                f"{ranking.ranking_dims} of measurable {assembly.ranking_dims}"
            )
        # A user reference point naming a demoted dim must be told why the
        # key no longer ranks (loud, not silent — DECISIONS (o) semantics).
        for key in (inp.reference_point or {}):
            if key in assembly.demoted:
                notes.append(
                    f"reference_point key '{key}' ignored: demoted by ranking "
                    f"governance ({assembly.demoted[key]})"
                )
        if assembly.kept_flags:
            notes.append(f"objective_flags={assembly.kept_flags}")
        if notes:
            _LOGGER.warning("full_length_asf_ranking_notes %s", "; ".join(notes))
            self._workflow_state["_asf_ranking_note"] = "; ".join(notes)
        return (
            ranking.best,
            ranking.pareto_frontier,
            ranking.raw_reference_point,
            ranking.asf_map,
        )

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            return self._empty_result("No candidates produced.")

        inp = self._workflow_state.get("_full_length_input")
        if inp:
            best, pareto_frontier, raw_ref_point, candidate_asf_map = (
                self._apply_reference_point_and_pareto(candidates, inp)
            )
        else:
            best = candidates[0] if candidates else None
            pareto_frontier = []
            raw_ref_point = None
            candidate_asf_map = {}

        # Sort candidates by ASF distance to the reference point (lower = better).
        # Candidates without an ASF value fall back to the end.
        ranked = sorted(
            candidates,
            key=lambda c: candidate_asf_map.get(c.id, float("inf")),
        )
        for i, c in enumerate(ranked, start=1):
            c.rank = i
            c.scores["asf_distance"] = candidate_asf_map.get(c.id)

        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            line_parts = [
                f"#{i}",
                f"source={c.source}",
                f"total_len={mb.get('total_length')}nt",
                f"utr5={mb.get('utr5_length')}nt({c.metadata.get('utr5_id', '?')})",
                f"utr3={mb.get('utr3_length')}nt({c.metadata.get('utr3_id', '?')})",
                f"cds_source={c.metadata.get('cds_source', '?')}",
                f"GC={mb.get('cds_gc'):.3f}" if mb.get("cds_gc") is not None else "GC=N/A",
                f"fullGC={mb.get('full_length_gc'):.3f}" if mb.get("full_length_gc") is not None else "fullGC=N/A",
                f"cdsU={mb.get('cds_u_fraction'):.3f}" if mb.get("cds_u_fraction") is not None else "cdsU=N/A",
                f"fullU={mb.get('full_u_fraction'):.3f}" if mb.get("full_u_fraction") is not None else "fullU=N/A",
                f"fullMFE={mb.get('full_length_mfe'):.2f}({mb.get('fold_tool', '?')})"
                if mb.get("full_length_mfe") is not None
                else "fullMFE=N/A",
                f"utr5IRES={mb.get('utr5_ires_potential'):.3f}"
                if mb.get("utr5_ires_potential") is not None
                else "utr5IRES=N/A",
                f"utr5MRL={mb.get('utr5_predicted_mrl'):.2f}"
                if mb.get("utr5_predicted_mrl") is not None
                else "utr5MRL=N/A",
                f"utr3Stab={mb.get('utr3_predicted_stability'):.4f}"
                if mb.get("utr3_predicted_stability") is not None
                else "utr3Stab=N/A",
                f"RNASTOP={mb.get('overall_stability'):.4f}"
                if mb.get("overall_stability") is not None
                else "RNASTOP=N/A",
                f"CAI={mb.get('cds_cai'):.4f}" if mb.get("cds_cai") is not None else "CAI=N/A",
                f"cdsComponent={scores.get('cds_component'):.4f}" if scores.get('cds_component') is not None else "cdsComponent=N/A",
                f"asf={scores.get('asf_distance'):.4f}" if scores.get('asf_distance') is not None else "asf=N/A",
            ]
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_asf_distance={best.scores.get('asf_distance') if best else None}",
            f"best_candidate_source=reference_point_optimization",
        ]
        if raw_ref_point is not None:
            summary_parts.append(f"reference_point={raw_ref_point}")
        asf_note = self._workflow_state.get("_asf_ranking_note")
        if asf_note:
            summary_parts.append(f"asf_ranking_note={asf_note}")
        if pareto_frontier:
            summary_parts.append(f"pareto_frontier_size={len(pareto_frontier)}")
        summary_parts.append("---")
        summary_parts.extend(detail_lines)

        extras: dict[str, Any] = {
            "best_candidate_source": "reference_point_optimization",
        }
        if pareto_frontier:
            extras["pareto_frontier"] = pareto_frontier
        if raw_ref_point is not None:
            extras["reference_point"] = raw_ref_point

        return WorkflowResult(
            success=True,
            task_id=f"full_mrna_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
            **extras,
        )
