"""Full-length mRNA design workflow — 5'UTR + CDS + 3'UTR (Layer 2).

Protein sequence → CDS candidates via MrnaCdsDesignWorkflow (generate + evaluate)
→ UTR combinations (GEMORNA short/medium/long) → full-length / UTR incremental
evaluation → full-length scoring → ranking → WorkflowResult.

Architecture: Full-length workflow reuses MrnaCdsDesignWorkflow for CDS
generation and evaluation; only full-length and UTR metrics are computed here.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  FullLengthMrnaDesignWorkflow INTERFACE LOCK (v2.8.0) —— 禁止单方面变更       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 full_length_mrna_design workflow 的权威实现。任何字段增删、         ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试： ║
║                                                                               ║
║    - agent_core/workflows/full_length_mrna_design.py  ← 本文件               ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/workflows/mrna_cds_design.py                                  ║
║    - agent_core/workflows/evaluators.py                                       ║
║    - agent_core/workflows/scoring.py                                          ║
║    - agent_core/workflows/coordinator.py                                      ║
║    - agent_core/sequence_utils.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/agents/quality_agent.py                                       ║
║    - agent_core/agents/specialist_agent.py                                    ║
║    - agent_core/agents/pipeline_agent.py                                      ║
║    - agent_core/agents/coordinator_agent.py                                   ║
║    - agent_core/quality_profiles/full_length_mrna_design.py                   ║
║    - agent_core/tool_specs.py                                                 ║
║    - tests/test_full_length_mrna_design.py                                    ║
║    - tests/test_full_length_mrna_design_layer3.py                             ║
║    - tests/test_bmc_full_length_mrna.py                                       ║
║    - tests/test_bmc_workflow_e2e_mock.py                                      ║
║    - tests/test_full_length_mrna_e2e_live.py                                  ║
║    - test_pa003_full_length_end_to_end.py                                     ║
║    - test_pa004_full_length_end_to_end.py                                     ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_core.constants.species import (
    DEFAULT_CAI_SPECIES,
    DEFAULT_RNARL_MODEL_TYPE,
    RNARL_MODEL_TYPES_LIST,
    format_cai_species_aliases,
)
from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.workflow_models import Candidate, WorkflowResult
from agent_core.workflows.base import BaseDomainWorkflow, SubWorkflowEvaluator
from agent_core.workflows.coordinator import (
    CoordinationRound,
    Issue,
    ReferencePointCoordinator,
)
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
from agent_core.workflows.mrna_cds_design import MrnaCdsDesignInput, MrnaCdsDesignWorkflow
from agent_core.workflows.multi_objective import (
    achievement_scalarizing_function,
    assign_pareto_tags,
    build_normalized_reference_point,
    cap_pareto_frontier,
    compute_pareto_frontier,
    compute_utopian_reference_point,
    extract_objective_vector,
    normalize_to_unit_range,
)
from agent_core.workflows.scoring import FullLengthBMCScoringFunction
from agent_core.sequence_utils import score_mrna_candidate

_LOGGER = logging.getLogger("agent_core.workflows.full_length_mrna_design")

# UTR length presets exposed by GEMORNA
_UTR_PRESETS: list[str] = ["short", "medium", "long"]


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
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = Field(default="all", description="CDS design engine(s) to run. 'lineardesign' uses LinearDesign; 'rnarl' uses RNARL; 'gemorna' uses GEMORNA; 'all' runs all three and merges candidates.")
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
    utr_mode: Literal["short", "medium", "long", "all"] = Field(default="all", description="UTR generation mode. 'gemorna' generates 5'/3' UTRs with GEMORNA; 'none' skips UTR generation.")
    run_fold: bool = Field(default=True, description="Whether to fold the full-length mRNA sequence for secondary-structure evaluation.")
    run_gc: bool = Field(default=True, description="Whether to compute GC-content of the full-length mRNA sequence.")
    bmc_mode: Literal["rp"] = Field(
        default="rp",
        description=(
            "BMC coordinator mode. 'rp'=reference-point driven coordinator."
        ),
    )
    bmc_max_rounds: int = Field(
        default=1,
        ge=0,
        description=(
            "Maximum number of BMC coordination rounds. 0 disables iterative refinement. "
            "Higher values allow the workflow to progressively improve the candidate pool "
            "toward the reference point, at the cost of additional microservice calls."
        ),
    )
    bmc_improvement_threshold: float = Field(
        default=0.05,
        ge=0.0,
        description=(
            "Minimum normalized ASF improvement required to continue BMC iterations. "
            "If the best candidate's ASF distance to the reference point does not improve "
            "by at least this amount in a round, iteration stops early."
        ),
    )
    reference_point: Optional[dict[str, float]] = Field(
        default=None,
        description=(
            "Per-objective reference point for Achievement Scalarizing Function selection "
            "and BMC coordination. If omitted, a utopian point is derived from the candidate pool. "
            "User-facing keys: utr5_mrl, utr3_stability, full_mfe_score. "
            "Use target_cds_mfe and target_cds_cai to specify CDS objectives; they are "
            "automatically converted into the internal cds_component."
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
            allowed = {"utr5_mrl", "utr3_stability", "full_mfe_score"}
            unknown = set(self.reference_point.keys()) - allowed
            if unknown:
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
    input_model = FullLengthMrnaDesignInput
    description = (
        "Design full-length mRNA (5'UTR + CDS + 3'UTR) from protein sequence, "
        "reuse MrnaCdsDesignWorkflow for CDS generation and evaluation, "
        "evaluate full-length + UTR metrics incrementally, score, and rank candidates."
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
        # Reference-point stability across BMC rounds (see INTERFACE_LOCKS.md §14)
        self._fixed_norm_ref_point: Optional[dict[str, float]] = None
        self._fixed_dim_bounds: Optional[dict[str, dict[str, float]]] = None
        self._reference_point_mode: Literal["user", "utopian"] = "utopian"
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
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """BMC-enabled run: delegate to CoordinatorAgent.

        The convergence loop lives in ``CoordinatorAgent``; this workflow exposes
        the BMC-capable interface (``run_initial``, ``bmc_prepare``,
        ``bmc_run_round``, ``bmc_finalize``) so the agent can orchestrate
        generation, diagnosis, and regeneration.
        """
        # Lazy import avoids any circular dependency between agents and workflows.
        from agent_core.agents.coordinator_agent import CoordinatorAgent

        return CoordinatorAgent(self).run(inp, progress_callback=progress_callback)

    def run_initial(
        self,
        inp: FullLengthMrnaDesignInput | dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Phase 1 & 2: generate full-length candidates, evaluate, score, and rank.

        Resets per-run workflow state and returns the initial ``WorkflowResult``.
        State writeback is intentionally left to ``bmc_finalize()`` so that both
        early-exit and fully-coordinated runs attach state consistently.
        """
        if isinstance(inp, dict):
            inp = FullLengthMrnaDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._cds_state_writeback = {}  # reset per run
        self._workflow_state["_full_length_input"] = inp
        self._bmc_trace: list[CoordinationRound] = []

        # ── Phase 1 & 2: Standard generate → evaluate → score → rank ──
        return super().run(inp, progress_callback=progress_callback)

    def bmc_prepare(
        self,
        initial_result: WorkflowResult,
    ) -> dict[str, Any]:
        """Prepare BMC state from the initial ranked candidate pool.

        Returns a dict containing the coordinator, reference point, normalization
        bounds, current best candidate, and round budget. The reference point is
        fixed to the initial pool when user-provided, otherwise derived as a
        utopian point that may evolve across rounds.
        """
        inp = self._workflow_state.get("_full_length_input")
        if inp is None:
            raise RuntimeError("bmc_prepare called before run_initial")

        self._workflow_state["_bmc_mode"] = inp.bmc_mode
        coordinator = ReferencePointCoordinator()
        max_rounds = inp.bmc_max_rounds
        improvement_threshold = inp.bmc_improvement_threshold

        # Initial reference point and ASF for the current best candidate.
        # If the user supplied a reference point, we fix its normalization to the
        # initial candidate pool so the aspiration level stays stable across BMC
        # rounds.  The utopian point is allowed to evolve as the pool improves.
        norm_ref_point, _, dim_bounds = build_normalized_reference_point(
            initial_result.all_candidates,
            ReferencePointCoordinator.USER_FACING_OBJECTIVES,
            user_reference_point=inp.reference_point,
        )
        if inp.reference_point is not None:
            self._reference_point_mode = "user"
            self._fixed_norm_ref_point = dict(norm_ref_point)
            self._fixed_dim_bounds = {
                k: dict(v) for k, v in dim_bounds.items()
            }
        else:
            self._reference_point_mode = "utopian"
            self._fixed_norm_ref_point = None
            self._fixed_dim_bounds = None

        best = initial_result.best_candidate
        best_asf = self._candidate_asf(best, norm_ref_point, dim_bounds)

        return {
            "coordinator": coordinator,
            "norm_ref_point": norm_ref_point,
            "dim_bounds": dim_bounds,
            "best": best,
            "best_asf": best_asf,
            "max_rounds": max_rounds,
            "improvement_threshold": improvement_threshold,
            "inp": inp,
        }

    def bmc_run_round(
        self,
        round_num: int,
        result: WorkflowResult,
        bmc_state: dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> tuple[WorkflowResult, dict[str, Any], bool, str]:
        """Execute one BMC coordination round.

        Diagnoses the current candidate pool against the reference point,
        broadcasts feedback, regenerates affected modules, evaluates new
        candidates, and re-ranks the merged pool.

        Returns ``(result, bmc_state, should_stop, reason)``.
        """
        # Service pre-flight: a service may have gone down between the initial
        # run and this BMC round; recover it before doing real work.
        preflight = self._service_preflight_result()
        if preflight is not None:
            return preflight, bmc_state, True, "service_preflight_failed"

        coordinator = bmc_state["coordinator"]
        max_rounds = bmc_state["max_rounds"]
        improvement_threshold = bmc_state["improvement_threshold"]
        inp = bmc_state["inp"]
        best = bmc_state["best"]
        best_asf = bmc_state["best_asf"]

        if best is None:
            return result, bmc_state, True, "no_best_candidate"

        # Select the reference point for this round.
        # User-provided reference points are fixed to the initial candidate
        # pool's normalization bounds; utopian points are re-derived from the
        # current candidate pool.
        if self._reference_point_mode == "user":
            norm_ref_point = self._fixed_norm_ref_point
            dim_bounds = self._fixed_dim_bounds
        else:
            norm_ref_point, _, dim_bounds = build_normalized_reference_point(
                result.all_candidates,
                ReferencePointCoordinator.USER_FACING_OBJECTIVES,
                user_reference_point=None,
            )

        # Diagnose a representative set: ASF best + per-objective leaders.
        # This exposes trade-offs that a single best candidate may hide.
        diagnosis_candidates = self._select_diagnosis_candidates(
            result.all_candidates,
            ReferencePointCoordinator.USER_FACING_OBJECTIVES,
            best,
        )
        _LOGGER.info(
            "bmc_diagnosis_set size=%d best_id=%s",
            len(diagnosis_candidates),
            best.id if best else None,
        )

        raw_issues_with_sources: list[tuple[Issue, dict[str, Any]]] = []
        for cand in diagnosis_candidates:
            norm_vec = self._build_norm_candidate_vector(cand, dim_bounds)
            cand_metrics = cand.metadata.get("metrics_bundle", {})
            for issue in coordinator.diagnose(norm_vec, norm_ref_point):
                raw_issues_with_sources.append((issue, cand_metrics))
        issues, issue_source_metrics = self._merge_issues_with_sources(
            raw_issues_with_sources
        )
        total_violation = sum(issue.violation for issue in issues)

        if total_violation <= 0.0:
            _LOGGER.info(
                "bmc_converged_no_violation round=%d total_violation=%.4f",
                round_num,
                total_violation,
            )
            return result, bmc_state, True, "no_violation"

        # For CDS-level feedback, prefer the metrics of the candidate that
        # actually triggered the worst CDS gap. Fallback to best metrics.
        feedback_metrics = best.metadata.get("metrics_bundle", {})
        if "CDS_COMPONENT_BELOW_REFERENCE" in issue_source_metrics:
            feedback_metrics = issue_source_metrics["CDS_COMPONENT_BELOW_REFERENCE"]
        elif "FULL_MFE_SCORE_BELOW_REFERENCE" in issue_source_metrics:
            feedback_metrics = issue_source_metrics["FULL_MFE_SCORE_BELOW_REFERENCE"]

        feedback = coordinator.broadcast_feedback(issues, feedback_metrics)
        affected_modules = list(feedback.keys())

        _LOGGER.info(
            "bmc_round_start round=%d issues=%d total_violation=%.4f modules=%s",
            round_num,
            len(issues),
            total_violation,
            affected_modules,
        )

        # Generate new candidates with adjusted parameters
        t0 = time.perf_counter()
        new_candidates = self._regenerate_modules(
            inp,
            feedback,
            best,
            result.all_candidates,
            diagnosis_candidates,
        )

        if not new_candidates:
            _LOGGER.info("bmc_no_new_candidates round=%d", round_num)
            return result, bmc_state, True, "no_new_candidates"

        # Evaluate new candidates
        for i, candidate in enumerate(new_candidates):
            _LOGGER.info(
                "bmc_evaluating_new idx=%d total=%d round=%d",
                i + 1,
                len(new_candidates),
                round_num,
            )
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
            if progress_callback:
                progress_callback({
                    "event": "bmc_evaluate_progress",
                    "round": round_num,
                    "current": i + 1,
                    "total": len(new_candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

        # Merge and re-rank
        all_candidates = result.all_candidates + new_candidates
        result = self.rank_and_format(all_candidates)

        new_best = result.best_candidate
        new_asf = self._candidate_asf(new_best, norm_ref_point, dim_bounds)

        # Record round trace
        time_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        round_trace = CoordinationRound(
            round_num=round_num,
            best_candidate_id=new_best.id if new_best else "",
            best_total_score=-new_asf,  # negated for display: higher = better
            issues_found=issues,
            feedback_dispatched=feedback,
            modules_reinvoked=affected_modules,
            time_elapsed_ms=time_elapsed_ms,
            diagnosis_candidate_ids=[c.id for c in diagnosis_candidates],
            reference_point_mode=self._reference_point_mode,
            reference_point=dict(norm_ref_point) if norm_ref_point else {},
            dim_bounds={
                k: dict(v) for k, v in dim_bounds.items()
            } if dim_bounds else {},
        )
        self._bmc_trace.append(round_trace)

        should_stop, reason = coordinator.has_converged(
            -new_asf,
            -best_asf,
            round_num,
            max_rounds=max_rounds,
            improvement_threshold=improvement_threshold,
        )

        _LOGGER.info(
            "bmc_round_complete round=%d old_asf=%.3f new_asf=%.3f reason=%s",
            round_num,
            best_asf,
            new_asf,
            reason,
        )

        # Update BMC state for the next round
        bmc_state["best"] = new_best
        bmc_state["best_asf"] = new_asf
        bmc_state["norm_ref_point"] = norm_ref_point
        bmc_state["dim_bounds"] = dim_bounds

        return result, bmc_state, should_stop, reason

    def bmc_finalize(
        self,
        result: WorkflowResult,
    ) -> WorkflowResult:
        """Attach final state writeback and return the result."""
        inp = self._workflow_state.get("_full_length_input")
        if inp is None:
            return result

        # Merge state writeback
        merged_wb = dict(self._workflow_state)
        for key, value in self._cds_state_writeback.items():
            if isinstance(value, dict) and isinstance(merged_wb.get(key), dict):
                merged_wb[key].update(value)
            else:
                merged_wb[key] = value
        merged_wb["_workflow_params"] = inp.model_dump()
        merged_wb["_bmc_trace"] = [r.to_dict() for r in self._bmc_trace]
        merged_wb["_reference_point"] = (
            inp.reference_point if inp.reference_point is not None else "utopian"
        )
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def _candidate_asf(
        self,
        cand: Candidate | None,
        ref_point: dict[str, float],
        bounds: dict[str, dict[str, float]],
    ) -> float:
        """Achievement Scalarizing Function distance for a candidate (lower = better)."""
        if cand is None:
            return float("inf")
        vec = self._build_norm_candidate_vector(cand, bounds)
        common = {k: v for k, v in vec.items() if k in ref_point}
        if not common:
            return float("inf")
        weights = {k: 1.0 / len(ref_point) for k in ref_point}
        return achievement_scalarizing_function(
            common, ref_point, weights, rho=1e-3
        )

    @staticmethod
    def _build_norm_candidate_vector(
        candidate: Candidate,
        dim_bounds: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Build a normalized objective vector for a single candidate.

        Uses the same min/max bounds that were used to normalize the reference
        point so that gaps are comparable.
        """
        vector: dict[str, float] = {}
        for key, bounds in dim_bounds.items():
            raw = candidate.scores.get(key)
            if raw is None:
                continue
            min_val = bounds["min"]
            max_val = bounds["max"]
            span = max_val - min_val
            if span == 0:
                vector[key] = 0.5
            else:
                vector[key] = (float(raw) - min_val) / span
        return vector

    @staticmethod
    def _select_diagnosis_candidates(
        candidates: list[Candidate],
        objectives: tuple[str, ...],
        best_candidate: Candidate | None,
    ) -> list[Candidate]:
        """Return the set of candidates that should be diagnosed by BMC.

        Always includes the ASF best candidate. Additionally includes the
        per-objective leader (highest raw score) for each user-facing objective.
        This gives the coordinator visibility into trade-offs that the single
        best candidate may not represent.
        """
        selected: dict[str, Candidate] = {}
        if best_candidate is not None:
            selected[best_candidate.id] = best_candidate

        for key in objectives:
            champion: Candidate | None = None
            best_value: float | None = None
            for c in candidates:
                value = c.scores.get(key)
                if value is None:
                    continue
                try:
                    value_f = float(value)
                except (TypeError, ValueError):
                    continue
                if best_value is None or value_f > best_value:
                    best_value = value_f
                    champion = c
            if champion is not None:
                selected[champion.id] = champion

        return list(selected.values())

    @staticmethod
    def _merge_issues_with_sources(
        issues_with_sources: list[tuple[Issue, dict[str, Any]]],
    ) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
        """Merge issues by type, keeping the one with the largest violation.

        When multiple diagnosis candidates flag the same kind of gap, only the
        most severe instance should drive module adjustments, to avoid
        duplicating feedback for the same module.

        Additionally returns a mapping from issue_type to the metrics bundle of
        the candidate that contributed the worst instance. This lets downstream
        feedback (e.g. CDS lambda direction) be based on the candidate that
        actually triggered the issue, rather than always the ASF best.

        Args:
            issues_with_sources: List of (issue, source_candidate_metrics)
                tuples collected from all diagnosis candidates.

        Returns:
            Tuple of (merged_issues, issue_type -> source_metrics).
        """
        merged: dict[str, Issue] = {}
        source_metrics: dict[str, dict[str, Any]] = {}
        for issue, metrics in issues_with_sources:
            existing = merged.get(issue.issue_type)
            if existing is None or issue.violation > existing.violation:
                merged[issue.issue_type] = issue
                source_metrics[issue.issue_type] = metrics
        return list(merged.values()), source_metrics

    def generate_candidates(self, inp: FullLengthMrnaDesignInput) -> list[Candidate]:
        """Generate full-length candidates: CDS baseline + UTR append.

        Step 1: Delegate CDS generation to MrnaCdsDesignWorkflow (evaluate via
        SubWorkflowEvaluator in ``evaluate()``).
        Step 2: For each CDS, generate 3×3 UTR combinations.
        Total: up to 6 unique CDS × 9 UTR combos = 54 candidates.
        """
        # ── Step 1: Generate CDS candidates (evaluation deferred to evaluate()) ──
        cds_inp = MrnaCdsDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=inp.design_tool,
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

        # ── Step 2: UTR combinations ──
        utr_presets = self._resolve_utr_presets(inp.utr_mode)
        full_candidates: list[Candidate] = []

        for cds_cand in cds_candidates:
            cds_seq = cds_cand.sequence
            if len(cds_seq) % 3 != 0:
                _LOGGER.warning(
                    "cds_length_not_multiple_of_3 source=%s len=%d",
                    cds_cand.source,
                    len(cds_seq),
                )
                continue

            for utr5_preset in utr_presets:
                utr5_seq = self._generate_utr("5utr", utr5_preset)
                if utr5_seq is None:
                    continue
                for utr3_preset in utr_presets:
                    utr3_seq = self._generate_utr("3utr", utr3_preset)
                    if utr3_seq is None:
                        continue

                    full_seq = utr5_seq + cds_seq + utr3_seq
                    candidate = Candidate(
                        sequence=full_seq,
                        sequence_type="mrna",
                        source=f"full_length:{cds_cand.source}:utr5_{utr5_preset}:utr3_{utr3_preset}",
                        metadata={
                            "utr5_sequence": utr5_seq,
                            "cds_sequence": cds_seq,
                            "utr3_sequence": utr3_seq,
                            "utr5_length": len(utr5_seq),
                            "utr3_length": len(utr3_seq),
                            "utr5_preset": utr5_preset,
                            "utr3_preset": utr3_preset,
                            "cds_length": len(cds_seq),
                            "cds_source": cds_cand.source,
                            "protein_sequence": inp.protein_sequence,
                            "cai_species": inp.cai_species,
                        },
                    )
                    full_candidates.append(candidate)
                    _LOGGER.info(
                        "full_candidate_generated cds_source=%s utr5=%s utr3=%s total_len=%d",
                        cds_cand.source,
                        utr5_preset,
                        utr3_preset,
                        len(full_seq),
                    )

        # Deduplicate by full sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in full_candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

        _LOGGER.info(
            "full_candidates_generated total=%d unique=%d",
            len(full_candidates),
            len(unique),
        )
        return unique

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
        return FullLengthBMCScoringFunction().score(metrics)

    # ─────────────────────────────────────────────────────────────────────────
    # BMC module regeneration helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _adjust_input_from_feedback(
        self,
        inp: FullLengthMrnaDesignInput,
        feedback: dict[str, Any],
    ) -> FullLengthMrnaDesignInput:
        """Build a parameter-adjusted input from coordinator feedback.

        Only CDS-level adjustments are actionable in the current architecture;
        UTR adjustments are realized via preset switching in
        ``_regenerate_modules()``.
        """
        # Start from current input values
        new_lambda = inp.lambda_value
        new_design_tool = inp.design_tool
        lambda_adjusted = False

        cds_feedback = feedback.get("CDS")
        if cds_feedback is not None:
            for adj in cds_feedback.adjustments:
                if adj.param == "lambda_value":
                    lambda_adjusted = True
                    if new_lambda is not None:
                        new_lambda = max(0.0, min(20.0, new_lambda + adj.delta))
                    else:
                        # If lambda was not set, start from a heuristic default
                        new_lambda = max(0.0, min(20.0, 2.0 + adj.delta))

        # If lambda is being adjusted but design_tool is "all", the adjustment
        # would be ignored because generate_candidates uses a fixed lambda grid
        # for "all". Switch to "lineardesign" so the lambda change takes effect.
        if lambda_adjusted and new_design_tool == "all":
            new_design_tool = "lineardesign"

        # If no actionable CDS adjustments but UTR is affected, we still
        # return a copy so that _regenerate_modules can try different presets.
        # The internal cds_component must be stripped from the user-facing
        # reference_point; it will be re-synthesized from target_cds_mfe/cai
        # by the input validator.
        user_reference_point = None
        if inp.reference_point is not None:
            user_reference_point = {
                k: v
                for k, v in inp.reference_point.items()
                if k != "cds_component"
            }
        return FullLengthMrnaDesignInput(
            protein_sequence=inp.protein_sequence,
            design_tool=new_design_tool,
            lambda_value=new_lambda,
            model_type=inp.model_type,
            cai_species=inp.cai_species,
            utr_mode=inp.utr_mode,
            run_fold=inp.run_fold,
            run_gc=inp.run_gc,
            bmc_mode=inp.bmc_mode,
            bmc_max_rounds=inp.bmc_max_rounds,
            bmc_improvement_threshold=inp.bmc_improvement_threshold,
            reference_point=user_reference_point,
            target_cds_mfe=inp.target_cds_mfe,
            target_cds_cai=inp.target_cds_cai,
        )

    def _regenerate_modules(
        self,
        inp: FullLengthMrnaDesignInput,
        feedback: dict[str, Any],
        current_best: Candidate,
        existing_candidates: list[Candidate],
        diagnosis_candidates: list[Candidate] | None = None,
    ) -> list[Candidate]:
        """Generate new candidates by adjusting parameters per coordinator feedback.

        Strategy:
        1. Adjust CDS parameters (lambda, tool) based on CDS feedback.
        2. Collect CDS seeds from the diagnosis set (best + per-objective leaders).
           When CDS parameters are unchanged, these seeds preserve trade-off
           diversity instead of only reusing the current best CDS.
        3. If UTR feedback exists, explore alternative UTR presets to change
           the junction sequence context.
        4. Combine all CDS candidates (λ-adjusted + seeds) with UTR presets.
        5. Deduplicate against existing candidates.
        """
        adjusted_inp = self._adjust_input_from_feedback(inp, feedback)

        # Determine whether CDS parameters actually changed.
        # If only junction issues exist (no cds_component / full_mfe_score gap),
        # the reference-point coordinator does not emit lambda adjustments, so
        # re-generating CDS with the same parameters is wasteful.  In that case
        # we reuse the current best CDS and rely on UTR exploration.
        cds_params_unchanged = (
            adjusted_inp.design_tool == inp.design_tool
            and adjusted_inp.lambda_value == inp.lambda_value
        )

        if cds_params_unchanged:
            # Reuse CDS seeds from the whole diagnosis set, not just the best.
            # This preserves trade-off diversity: a candidate that leads in one
            # objective can contribute its CDS to the new UTR combinations.
            seeds: list[str] = []
            seed_labels: list[str] = []
            best_cds_seq = current_best.metadata.get("cds_sequence", "") if current_best else ""
            if best_cds_seq:
                seeds.append(best_cds_seq)
                seed_labels.append("current_best")
            for cand in diagnosis_candidates or []:
                cds_seq = cand.metadata.get("cds_sequence", "")
                if cds_seq and cds_seq not in seeds:
                    seeds.append(cds_seq)
                    seed_labels.append(f"diagnosis_seed:{cand.id}")

            cds_candidates = [
                Candidate(
                    sequence=cds_seq,
                    sequence_type="cds",
                    source=label,
                    metadata={"cds_sequence": cds_seq},
                )
                for cds_seq, label in zip(seeds, seed_labels)
            ]
            _LOGGER.info(
                "bmc_reusing_diagnosis_cds_seeds count=%d labels=%s",
                len(cds_candidates),
                seed_labels,
            )
        else:
            cds_inp = MrnaCdsDesignInput(
                protein_sequence=adjusted_inp.protein_sequence,
                design_tool=adjusted_inp.design_tool,
                lambda_value=adjusted_inp.lambda_value,
                model_type=adjusted_inp.model_type,
                cai_species=adjusted_inp.cai_species,
                run_fold=adjusted_inp.run_fold,
                run_gc=adjusted_inp.run_gc,
            )
            cds_workflow = MrnaCdsDesignWorkflow(self.capabilities)
            cds_candidates = cds_workflow.generate_candidates(cds_inp)

        # Track the provenance of each CDS sequence for source labeling.
        cds_source_map: dict[str, str] = {}
        for c in cds_candidates:
            cds_source_map[c.sequence] = c.source
        all_cds_seqs = list(cds_source_map.keys())

        # UTR presets always honour the user's ``utr_mode`` selection; BMC
        # rounds never expand beyond it (the coordinator no longer emits
        # ``utr_preset_exploration`` overrides).
        utr_presets = self._resolve_utr_presets(adjusted_inp.utr_mode)
        # Limit presets to avoid explosion during BMC
        if len(utr_presets) > 2:
            utr_presets = utr_presets[:2]

        seen = {c.sequence for c in existing_candidates}
        new_candidates: list[Candidate] = []

        for cds_seq in all_cds_seqs[:6]:  # cap at 6 CDS to avoid explosion
            for utr5_preset in utr_presets:
                utr5_seq = self._generate_utr("5utr", utr5_preset)
                if utr5_seq is None:
                    continue
                for utr3_preset in utr_presets:
                    utr3_seq = self._generate_utr("3utr", utr3_preset)
                    if utr3_seq is None:
                        continue

                    full_seq = utr5_seq + cds_seq + utr3_seq
                    if full_seq in seen:
                        continue
                    seen.add(full_seq)

                    # Determine source label for traceability
                    cds_origin = cds_source_map.get(cds_seq, "unknown")
                    is_current_best = cds_origin == "current_best"
                    if is_current_best:
                        source_label = f"bmc:current_best:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "current_best"
                    elif cds_origin.startswith("diagnosis_seed:"):
                        seed_id = cds_origin.split(":", 1)[1]
                        source_label = f"bmc:diagnosis_seed:{seed_id}:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "diagnosis_seed"
                    else:
                        source_label = f"bmc:lambda_adjusted:utr5_{utr5_preset}:utr3_{utr3_preset}"
                        cds_source = "lambda_adjusted"

                    candidate = Candidate(
                        sequence=full_seq,
                        sequence_type="mrna",
                        source=source_label,
                        metadata={
                            "utr5_sequence": utr5_seq,
                            "cds_sequence": cds_seq,
                            "utr3_sequence": utr3_seq,
                            "utr5_length": len(utr5_seq),
                            "utr3_length": len(utr3_seq),
                            "utr5_preset": utr5_preset,
                            "utr3_preset": utr3_preset,
                            "cds_length": len(cds_seq),
                            "cds_source": cds_source,
                            "protein_sequence": adjusted_inp.protein_sequence,
                            "cai_species": adjusted_inp.cai_species,
                            "bmc_regenerated": True,
                            "bmc_feedback_modules": list(feedback.keys()),
                        },
                    )
                    new_candidates.append(candidate)
                    _LOGGER.info(
                        "bmc_candidate_generated source=%s utr5=%s utr3=%s len=%d",
                        source_label,
                        utr5_preset,
                        utr3_preset,
                        len(full_seq),
                    )

        # Hard cap to keep microservice call volume bounded when multiple
        # diagnosis candidates trigger overlapping module feedback.
        _MAX_BMC_NEW_CANDIDATES = 24
        if len(new_candidates) > _MAX_BMC_NEW_CANDIDATES:
            # Preserve source diversity by keeping a spread across source labels.
            # Simple deterministic fallback: keep the first N generated.
            new_candidates = new_candidates[:_MAX_BMC_NEW_CANDIDATES]
            _LOGGER.info(
                "bmc_capped_new_candidates kept=%d",
                _MAX_BMC_NEW_CANDIDATES,
            )

        _LOGGER.info(
            "bmc_regeneration_complete new=%d seen_total=%d",
            len(new_candidates),
            len(seen),
        )
        return new_candidates

    def _apply_reference_point_and_pareto(
        self,
        candidates: list[Candidate],
        inp: FullLengthMrnaDesignInput,
    ) -> tuple[Candidate | None, list[Candidate], dict[str, float] | None, dict[str, float]]:
        """Reference-point optimization + Pareto frontier (default behaviour).

        The best candidate is always selected via the Achievement Scalarizing
        Function (ASF).  If the user does not supply a ``reference_point``, a
        utopian point is derived from the candidate pool.  The Pareto-optimal
        frontier is always computed and returned.

        Only user-facing objectives are used for reference-point selection and
        the Pareto frontier; junction scores remain internal diagnostics.

        Returns ``(best_candidate, pareto_frontier, raw_reference_point, candidate_asf_map)``.
        """
        objectives = list(ReferencePointCoordinator.USER_FACING_OBJECTIVES)
        maximize = {key: True for key in objectives}

        # Build per-dimension value tables, skipping candidates with missing dims.
        dim_values: dict[str, list[float]] = {key: [] for key in objectives}
        candidate_vectors: list[tuple[Candidate, dict[str, float]]] = []
        for candidate in candidates:
            vec = extract_objective_vector(candidate, objectives)
            if not vec:
                continue
            candidate_vectors.append((candidate, vec))
            for key, value in vec.items():
                dim_values[key].append(value)

        candidate_asf_map: dict[str, float] = {}
        if not candidate_vectors:
            best = candidates[0] if candidates else None
            return best, [], None, candidate_asf_map

        # Normalize each dimension to [0, 1] based on the candidate pool.
        normalized_dim_values: dict[str, list[float]] = {}
        for key, values in dim_values.items():
            normalized_dim_values[key] = normalize_to_unit_range(values)

        # Map each candidate to its normalized vector.
        normalized_vectors: list[tuple[Candidate, dict[str, float]]] = []
        dim_index: dict[str, int] = {key: 0 for key in objectives}
        for candidate, vec in candidate_vectors:
            norm_vec: dict[str, float] = {}
            for key, value in vec.items():
                norm_vec[key] = normalized_dim_values[key][dim_index[key]]
                dim_index[key] += 1
            normalized_vectors.append((candidate, norm_vec))

        # Pareto frontier (computed on raw objective values for interpretability).
        all_candidates_for_pareto = [c for c, _ in normalized_vectors]
        pareto_frontier = compute_pareto_frontier(
            all_candidates_for_pareto, objectives, maximize
        )
        if pareto_frontier:
            assign_pareto_tags(pareto_frontier, objectives, maximize)
            pareto_frontier = cap_pareto_frontier(pareto_frontier, max_size=10)

        # Reference point: user-provided or auto-derived utopian point.
        raw_ref_point: dict[str, float]
        if inp.reference_point is not None:
            raw_ref_point = dict(inp.reference_point)
        else:
            raw_ref_point = compute_utopian_reference_point(
                all_candidates_for_pareto, objectives, maximize
            )

        # Normalize the reference point with the same min/max as candidates.
        norm_ref_point: dict[str, float] = {}
        for key in objectives:
            if key not in raw_ref_point or key not in dim_values:
                continue
            user_val = float(raw_ref_point[key])
            values = dim_values[key]
            min_val = min(values)
            max_val = max(values)
            span = max_val - min_val
            if span == 0:
                norm_ref_point[key] = 0.5
            else:
                norm_ref_point[key] = (user_val - min_val) / span

        if not norm_ref_point:
            best = candidates[0] if candidates else None
            return best, pareto_frontier, raw_ref_point or None, candidate_asf_map

        default_weight = 1.0 / len(norm_ref_point)
        weights = {key: default_weight for key in norm_ref_point}

        best_candidate: Candidate | None = None
        best_asf = float("inf")
        for candidate, norm_vec in normalized_vectors:
            # Only consider objectives present in both candidate and reference point.
            common_vec = {k: v for k, v in norm_vec.items() if k in norm_ref_point}
            if not common_vec:
                continue
            asf = achievement_scalarizing_function(
                common_vec, norm_ref_point, weights, rho=1e-3
            )
            candidate_asf_map[candidate.id] = asf
            if asf < best_asf:
                best_asf = asf
                best_candidate = candidate

        if best_candidate is None:
            best_candidate = candidates[0] if candidates else None

        return best_candidate, pareto_frontier, raw_ref_point, candidate_asf_map

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
                f"utr5={mb.get('utr5_length')}nt({c.metadata.get('utr5_preset', '?')})",
                f"utr3={mb.get('utr3_length')}nt({c.metadata.get('utr3_preset', '?')})",
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
