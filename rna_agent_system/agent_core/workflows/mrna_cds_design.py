"""mRNA CDS design & optimisation workflow — the golden path (Layer 2).

Protein sequence → CDS design (GenNav-λ constraint navigation, or the static
recipe LinearDesign λ=[0,1,4,10] + RNARL + GEMORNA) → fold + GC +
unpaired-fraction evaluation → scoring → ranking → WorkflowResult.

v2.0.0 (2026-09-05): GenNav-λ constraint navigation (E6 evidence, E8–E14
levers; ``agent_core/generation/gennav_mrna_lambda.py``) is the platform
DEFAULT design mode — λ-curve probe → gap-driven interstitial reinforcement
under a 35-raw budget → per-profile matrix delivery (expression / stability /
balanced, 5 each, D1 diversity). Deterministic, zero LLM. The ``navigation``
input is a tristate: unset (``None``) navigates whenever ``design_tool`` is
the platform default recipe (``"all"``) and honours an explicitly pinned
engine (``lineardesign``/``rnarl``/``gemorna``) by running that static path;
``True``/``False`` always override. Registered instruments that pin the
static pool semantics pass ``navigation=False`` explicitly. RNARL/GEMORNA
are not called on the navigation path; CapGate (audit trail + gate
decisions) is mode-independent and active on every path through the
capability layer.

"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import (
    _load_builtin_codon_tables,
    _pick_float,
    lineardesign_codon_table_for_species,
    resolve_species_name,
)
from agent_core.constants.species import DEFAULT_CAI_SPECIES, DEFAULT_RNARL_MODEL_TYPE, RNARLModelType, format_cai_species_aliases, format_rnarl_model_types
from agent_core.generation.gennav_mrna_lambda import (
    codon_synonyms,
    longest_stem_bp,
    synonymous_diversify,
    MrnaNavConfig,
    deliver_profile,
    evaluate_matrix,
    gc_fraction,
    guarantee_round,
    max_homopolymer_run,
    mechanized_proposals,
    utility_key,
    profile_gaps,
)
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.multi_objective import (
    assign_pareto_tags,
    compute_pareto_frontier,
)
from agent_core.sequence_utils import (
    compute_mrna_metric_bundle,
    score_mrna_candidate,
)
from agent_core.workflows.evaluators import (
    CAIEvaluator,
    CompositeEvaluator,
    GCContentEvaluator,
    RNASTOPEvaluator,
    SecondaryStructureEvaluator,
    UContentEvaluator,
    UnpairedFractionEvaluator,
)

_LOGGER = logging.getLogger("agent_core.workflows.mrna_cds_design")


# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsDesignInput(BaseModel):
    """Input for the mRNA CDS design golden path."""
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    lineardesign_filepath: Any = Field(default=None, description="[lineardesign] filepath: Workspace file path that contains the input protein sequence. The wrapper reads the sequence from this file and sends it to the LinearDesign microservice.")
    lineardesign_service_url: Any = Field(default='http://127.0.0.1:8014/generate/cds', description="[lineardesign] service_url: REST endpoint of the LinearDesign microservice.")
    lineardesign_lambda_value: float = Field(default=0.0, description="[lineardesign] lambda_value: LinearDesign hyperparameter that balances minimum free energy (MFE) against codon adaptation index (CAI). In the CLI/binary it is passed as the first positional argument; the C++ engine multiplies this value by 100 internally, while verbose output divides it back by 100 for display. A value of 0.0 optimizes MFE only; larger values increasingly weight CAI in the joint objective.")
    lineardesign_codon_usage_path: Any = Field(default=None, description="[lineardesign] codon_usage_path: Optional path to a codon-usage frequency table in CSV format. When omitted, the service uses external_repos/LinearDesign/codon_usage_freq_table_human.csv.")
    lineardesign_verbose: Any = Field(default=False, description="[lineardesign] verbose: Enables extra textual output from the LinearDesign binary (input protein echo, effective lambda, codon table path, runtime).")
    rnarl_filepath: Any = Field(default=None, description="[rnarl] filepath: Workspace file path containing the input protein sequence. The wrapper extracts the first FASTA/plain-text sequence and sends it to the RNARL service.")
    rnarl_service_url: Any = Field(default='http://127.0.0.1:8008/generate/cds', description="[rnarl] service_url: REST endpoint of the RNARL CDS generation microservice.")
    rnarl_model_type: Any = Field(
        default=DEFAULT_RNARL_MODEL_TYPE,
        description=f"[rnarl] model_type: RNARL trained variant. Supported values: {format_rnarl_model_types()}.",
    )
    rnarl_checkpoint_path: Any = Field(default=None, description="[rnarl] checkpoint_path: Optional override for the RNARL actor checkpoint. When omitted, the service resolves checkpoints/RNARL/<model_type>.pt.")
    rnarl_esm2_model_path: Any = Field(default=None, description="[rnarl] esm2_model_path: Optional override for the local ESM-2 model directory used to encode the protein. Default is external_repos/RNARL/esm2_model_t33_650M_UR50D.")
    rnarl_device: Any = Field(default=None, description="[rnarl] device: Optional torch device string such as cuda:0 or cpu. The service defaults to CUDA if available, otherwise cpu.")
    gemorna_filepath: Any = Field(default=None, description="[gemorna] filepath: Workspace file path containing the protein sequence. The service requires at least 10 canonical amino acids (CDS >= 30 nt).")
    gemorna_service_url: Any = Field(default='http://127.0.0.1:8004/generate/cds', description="[gemorna] service_url: REST endpoint of the GEMORNA CDS microservice.")
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
    gc_filepath: str = Field(default=None, description="[gc] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    gc_service_url: str = Field(default='http://127.0.0.1:8020/gc-content', description="[gc] service_url: POST endpoint for GC content microservice.")
    gc_timeout_seconds: float = Field(default=120.0, description="[gc] timeout_seconds: HTTP request timeout in seconds.")
    u_content_filepath: str = Field(default=None, description="[u_content] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    u_content_service_url: str = Field(default='http://127.0.0.1:8020/u-content', description="[u_content] service_url: POST endpoint for U content microservice.")
    u_content_timeout_seconds: float = Field(default=120.0, description="[u_content] timeout_seconds: HTTP request timeout in seconds.")
    unpaired_filepath: str = Field(default=None, description="[unpaired] filepath: Path to dot-bracket secondary structure (first structural line used; FASTA header skipped).")
    unpaired_service_url: str = Field(default='http://127.0.0.1:8020/unpaired-fraction', description="[unpaired] service_url: POST endpoint for unpaired-fraction microservice.")
    unpaired_timeout_seconds: float = Field(default=120.0, description="[unpaired] timeout_seconds: HTTP request timeout in seconds.")
    rnastop_filepath: Any = Field(default=None, description="[rnastop] filepath: Workspace file path containing the RNA sequence. Non-ACGU characters are removed and T is converted to U.")
    rnastop_service_url: Any = Field(default='http://127.0.0.1:8009/predict/stability', description="[rnastop] service_url: REST endpoint of the RNASTOP stability microservice.")
    rnastop_structure: Any = Field(default=None, description="[rnastop] structure: Optional secondary structure in dot-bracket notation. Must be the same length as the normalized sequence. If omitted, the service folds the sequence with ViennaRNA.")
    rnastop_loop_type: Any = Field(default=None, description="[rnastop] loop_type: Optional loop-type annotation string in the OpenVaccine alphabet (S/M/I/H/B/E). Must match sequence length. If omitted, it is derived from the structure with RNA.db_to_element_string or a fallback S/E string.")
    rnastop_checkpoint_path: Any = Field(default=None, description="[rnastop] checkpoint_path: Optional override for the RNASTOP checkpoint. Default resolves to external_repos/RNASTOP/models/best_model_weights or best_model_weights_withoutDNABERT.")
    rnastop_device: Any = Field(default=None, description="[rnastop] device: Optional torch device string such as cuda:0 or cpu. Default is CUDA if available, otherwise cpu.")
    rnastop_rnafm_model_path: Any = Field(default=None, description="[rnastop] rnafm_model_path: Hidden service parameter not exposed by the wrapper. Default resolves to external_repos/RNASTOP/RNA-FM-main/pretrained/RNA-FM_pretrained.pth.")
    rnastop_dnabert_model_path: Any = Field(default=None, description="[rnastop] dnabert_model_path: Hidden service parameter not exposed by the wrapper. Default resolves to external_repos/RNASTOP/DNABERT6 or scripts/DNABERT6.")
    cai_filepath: str = Field(default=None, description="[cai] filepath: Path to CDS sequence file (workspace or absolute); FASTA or plain text. Must be in-frame (length multiple of 3).")
    cai_custom_codon_table_path: Optional[str] = Field(default=None, description="[cai] custom_codon_table_path: Optional path to a custom codon usage JSON file. Format: {\"codon\": {\"aa\": \"X\", \"fraction\": 0.42}, ...}. When provided, ``species`` is used only for metadata/labeling.")
    protein_sequence: str = Field(..., description="Amino-acid string (uppercase, 1-letter codes).")
    truncate_n_terminal: Optional[int] = Field(
        default=None,
        description="If set, keep only the first N amino acids of protein_sequence before design.",
    )
    truncate_c_terminal: Optional[int] = Field(
        default=None,
        description="If set, keep only the last N amino acids of protein_sequence before design.",
    )
    design_tool: Literal["lineardesign", "rnarl", "gemorna", "all"] = Field(default="all", description="CDS design engine(s) to run. 'lineardesign' uses LinearDesign; 'rnarl' uses RNARL; 'gemorna' uses GEMORNA; 'all' runs all three and merges candidates.")
    navigation: Optional[bool] = Field(
        default=None,
        description=(
            "GenNav-λ constraint navigation mode (E6 evidence, E8–E14 levers): "
            "λ-curve probe → gap-driven interstitial reinforcement under a "
            "35-raw budget → per-profile matrix delivery (expression/stability/"
            "balanced, 5 each, D1 diversity). Deterministic, zero LLM. When "
            "active, RNARL/GEMORNA are not called and design_tool is ignored "
            "for generation (evaluation/scoring/ranking unchanged). "
            "v2.0.0 platform default: None (unset) navigates when design_tool "
            "is the default recipe ('all') and honours an explicitly pinned "
            "engine; True/False always override."
        ),
    )
    lambda_value: Optional[float] = Field(
        default=None,
        description="LinearDesign MFE/CAI balance (0-20). Required when design_tool='lineardesign'; ignored otherwise.",
    )
    model_type: RNARLModelType = Field(
        default=DEFAULT_RNARL_MODEL_TYPE, description="RNARL model type."
    )
    cai_species: str = Field(
        default=DEFAULT_CAI_SPECIES,
        description=f"Species for CAI computation. Built-in: {format_cai_species_aliases()}.",
    )
    run_fold: bool = Field(default=True, description="Whether to fold designed CDS sequences with ViennaRNA/LinearFold for secondary-structure evaluation.")
    run_gc: bool = Field(default=True, description="Whether to compute GC-content of designed CDS sequences.")
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
    def _check_mutually_exclusive_truncation(self) -> "MrnaCdsDesignInput":
        """Only one terminal truncation direction may be specified."""
        if self.truncate_n_terminal is not None and self.truncate_c_terminal is not None:
            raise ValueError("truncate_n_terminal and truncate_c_terminal are mutually exclusive")
        return self

    @model_validator(mode="after")
    def _require_resolvable_species_for_lineardesign(self) -> "MrnaCdsDesignInput":
        """Species-correct design contract (2026-08-25 fix).

        When LinearDesign will run, ``cai_species`` must resolve to a built-in
        codon table (or an explicit ``lineardesign_codon_usage_path`` must be
        provided) — otherwise the service would silently design against its
        default human table. Fail fast at the input layer instead.
        """
        uses_lineardesign = (
            self.design_tool in ("all", "lineardesign")
            or resolved_navigation(self)
        )
        if (
            uses_lineardesign
            and not self.lineardesign_codon_usage_path
            and lineardesign_codon_table_for_species(self.cai_species) is None
        ):
            raise ValueError(
                f"No codon-usage table for cai_species {self.cai_species!r}: "
                "LinearDesign would fall back to its default human table. Use a "
                f"built-in species ({format_cai_species_aliases()}) or provide "
                "lineardesign_codon_usage_path (LinearDesign CSV) and "
                "cai_custom_codon_table_path (CAI JSON)."
            )
        return self


def resolved_navigation(inp: "MrnaCdsDesignInput") -> bool:
    """Resolve the tristate ``navigation`` input to the effective mode.

    v2.0.0 platform default: GenNav-λ navigation is the default design mode
    of the platform's default recipe (``design_tool="all"``); an explicitly
    pinned engine (``lineardesign``/``rnarl``/``gemorna``) honours the pin
    and runs the static recipe path. An explicit ``navigation`` value always
    wins over the default resolution.
    """
    if inp.navigation is not None:
        return bool(inp.navigation)
    return inp.design_tool == "all"


def _lineardesign_codon_table(inp: "MrnaCdsDesignInput") -> Optional[str]:
    """Codon table LinearDesign must design against (species-correct design).

    The explicit ``lineardesign_codon_usage_path`` override wins; otherwise the
    species-resolved CSV shipped with the platform — generated from the same
    Kazusa tables the CAI evaluator uses — is passed, so the generator and the
    evaluator always work against the same species table. Fails fast for
    unresolvable species instead of letting the service silently design
    against its default human table.
    """
    if inp.lineardesign_codon_usage_path:
        return str(inp.lineardesign_codon_usage_path)
    path = lineardesign_codon_table_for_species(inp.cai_species)
    if path is None:
        raise ValueError(
            f"No codon-usage table for cai_species {inp.cai_species!r}: "
            "LinearDesign would fall back to its default human table. Use a "
            f"built-in species ({format_cai_species_aliases()}) or provide "
            "lineardesign_codon_usage_path (LinearDesign CSV) and "
            "cai_custom_codon_table_path (CAI JSON)."
        )
    return path


# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsDesignWorkflow(BaseDomainWorkflow[MrnaCdsDesignInput, WorkflowResult]):
    """Golden-path workflow: protein → multi-tool CDS → fold + GC + unpaired → score → rank."""

    name = "mrna_cds_design"
    task_type = "mrna_cds_design"
    description = "Design mRNA CDS from protein sequence using multiple tools, evaluate, score, and rank candidates."
    input_model = MrnaCdsDesignInput
    required_capabilities = [
        "design_mrna_cds_with_lineardesign",
        "design_mrna_cds_with_rnarl",
        "design_mrna_cds_with_gemorna",
        "predict_rna_secondary_structure",
        "predict_rna_secondary_structure_with_linearfold",
        "compute_rna_sequence_gc_content",
        "compute_rna_sequence_u_content",
        "compute_dot_bracket_unpaired_fraction",
        "predict_mrna_stability_with_rnastop",
        "compute_cai_for_cds_sequence",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._run_fold = True
        self._run_gc = True
        self._generation_errors: list[str] = []
        self.evaluator = CompositeEvaluator([
            GCContentEvaluator(self.capabilities),
            UContentEvaluator(self.capabilities),
            SecondaryStructureEvaluator(self.capabilities, run_fold=True),
            UnpairedFractionEvaluator(self.capabilities),
            RNASTOPEvaluator(self.capabilities),
            CAIEvaluator(self.capabilities, species_key="cai_species"),
        ])

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        inp: MrnaCdsDesignInput | dict[str, Any],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Accept either ``MrnaCdsDesignInput`` or a plain dict."""
        if isinstance(inp, dict):
            inp = MrnaCdsDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._run_fold = inp.run_fold
        self._run_gc = inp.run_gc
        result = super().run(inp, progress_callback=progress_callback)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def partial_rerun(
        self,
        inp: MrnaCdsDesignInput | dict[str, Any],
        existing_candidates: list[Candidate],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResult:
        """Re-run evaluate → score → rank on existing candidates.

        Updates evaluator flags (``run_fold``, ``run_gc``) from *inp* without
        regenerating candidates.
        """
        if isinstance(inp, dict):
            inp = MrnaCdsDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._run_fold = inp.run_fold
        self._run_gc = inp.run_gc

        # Service pre-flight: auto-start required microservices when enabled.
        preflight = self._service_preflight_result()
        if preflight is not None:
            return preflight

        for i, candidate in enumerate(existing_candidates):
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
            if progress_callback:
                progress_callback({
                    "event": "evaluate_progress",
                    "current": i + 1,
                    "total": len(existing_candidates),
                    "candidate_id": candidate.id,
                    "workflow": self.name,
                })

        result = self.rank_and_format(existing_candidates)
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        result._state_writeback = merged_wb  # type: ignore[attr-defined]
        return result

    def generate_candidates(self, inp: MrnaCdsDesignInput) -> list[Candidate]:
        """Design CDS candidates from the protein sequence using multiple tools.

        Default strategy (``design_tool="all"``):
        - LinearDesign: λ = 0, 1, 4, 10  → 4 candidates
        - RNARL: 1 call → 1 candidate
        - GEMORNA: 1 call → 1 candidate
        Total = 6 candidates (deduplicated).
        """
        protein_sequence = inp.protein_sequence
        if inp.truncate_n_terminal is not None:
            protein_sequence = protein_sequence[: inp.truncate_n_terminal]
        elif inp.truncate_c_terminal is not None:
            protein_sequence = protein_sequence[-inp.truncate_c_terminal :]

        protein_fp = save_sequence(protein_sequence, prefix="protein")
        _LOGGER.info(
            "mrna_cds_design protein_saved filepath=%s original_len_aa=%d used_len_aa=%d",
            protein_fp,
            len(inp.protein_sequence),
            len(protein_sequence),
        )

        if resolved_navigation(inp):
            return self._generate_cds_navigation(inp, protein_fp)

        # Species-correct design: resolve the LinearDesign codon table from
        # cai_species (explicit override wins) before any generator call.
        uses_lineardesign = inp.design_tool in ("all", "lineardesign")
        ld_codon_table = _lineardesign_codon_table(inp) if uses_lineardesign else None

        design_configs: list[tuple[str, dict[str, Any]]] = []

        def _ld_args(lam: float) -> dict[str, Any]:
            extra: dict[str, Any] = {"lambda_value": lam}
            if ld_codon_table:
                extra["codon_usage_path"] = ld_codon_table
            return extra

        if inp.design_tool in ("all", "lineardesign"):
            if inp.design_tool == "all":
                for lam in (0.0, 1.0, 4.0, 10.0):
                    design_configs.append(("lineardesign", _ld_args(lam)))
            else:  # design_tool == "lineardesign"
                # Validator ensures lambda_value is not None; guard anyway.
                lam = inp.lambda_value if inp.lambda_value is not None else 0.0
                design_configs.append(("lineardesign", _ld_args(lam)))

        if inp.design_tool in ("all", "rnarl"):
            design_configs.append(
                ("rnarl", {"model_type": inp.model_type})
            )

        if inp.design_tool in ("all", "gemorna"):
            design_configs.append(("gemorna", {}))

        self._generation_errors = []
        candidates: list[Candidate] = []
        for tool_name, extra_args in design_configs:
            try:
                cap_name = f"design_mrna_cds_with_{tool_name}"
                if not self.capabilities.has(cap_name):
                    err_msg = f"capability missing: {cap_name}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
                    continue

                cap = self.capabilities.get(cap_name)
                args: dict[str, Any] = {"filepath": protein_fp, **extra_args}
                cap_result = cap.invoke(args, state=self._workflow_state)

                if not cap_result.success:
                    err_msg = f"design failed tool={tool_name} error={cap_result.error}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
                    continue

                seq = str(cap_result.output.get("generated_sequence", ""))
                if not seq:
                    err_msg = f"design empty tool={tool_name}"
                    _LOGGER.warning(err_msg)
                    self._generation_errors.append(err_msg)
                    continue

                param_label = ""
                if tool_name == "lineardesign" and "lambda_value" in extra_args:
                    param_label = f"_lambda{extra_args['lambda_value']}"

                candidate = Candidate(
                    sequence=seq,
                    sequence_type="mrna",
                    source=f"cds_design:{tool_name}{param_label}",
                    metadata={
                        "design_tool": tool_name,
                        "design_params": extra_args,
                        "protein_sequence": inp.protein_sequence,
                        "protein_sequence_used": protein_sequence,
                        "protein_filepath": protein_fp,
                        "design_output": cap_result.output,
                        "cai_species": inp.cai_species,
                    },
                )
                design_record = ToolCallRecord(
                    step_name=f"cds_design:{tool_name}",
                    tool_name=cap_name,
                    input_summary=json.dumps(args, default=str),
                    output_summary=json.dumps(cap_result.output, default=str)[:500],
                    success=cap_result.success,
                    error=cap_result.error,
                    elapsed_time=cap_result.elapsed_time,
                    artifacts=dict(cap_result.output) if cap_result.success else {},
                    metrics={"lambda_value": extra_args["lambda_value"]} if "lambda_value" in extra_args else {},
                )
                candidate.add_tool_record(design_record)
                candidates.append(candidate)
                _LOGGER.info(
                    "candidate_generated tool=%s params=%s len_nt=%d",
                    tool_name,
                    extra_args,
                    len(seq),
                )
            except Exception as exc:
                err_msg = f"design exception tool={tool_name} err={exc}"
                _LOGGER.error(err_msg)
                self._generation_errors.append(err_msg)

        # Deduplicate by sequence
        seen: set[str] = set()
        unique: list[Candidate] = []
        for c in candidates:
            if c.sequence not in seen:
                seen.add(c.sequence)
                unique.append(c)

        _LOGGER.info(
            "candidates_generated total=%d unique=%d",
            len(candidates),
            len(unique),
        )
        return unique

    # ─────────────────────────────────────────────────────────────────────────
    # GenNav-λ navigation path (E6 evidence; production wiring 2026-08-22)
    # ─────────────────────────────────────────────────────────────────────────

    def _nav_invoke(
        self,
        cap_name: str,
        args: dict[str, Any],
        records: list[ToolCallRecord],
        step_name: str,
    ) -> Any:
        """One capability call through the audit layer, recorded into *records*."""
        cap = self.capabilities.get(cap_name)
        res = cap.invoke(args, state=self._workflow_state)
        records.append(ToolCallRecord(
            step_name=step_name,
            tool_name=cap_name,
            input_summary=json.dumps(args, default=str),
            output_summary=json.dumps(res.output, default=str)[:500],
            success=res.success,
            error=res.error,
            elapsed_time=res.elapsed_time,
            artifacts=dict(res.output) if res.success else {},
            metrics={},
        ))
        return res

    def _generate_cds_navigation(
        self,
        inp: MrnaCdsDesignInput,
        protein_fp: str,
    ) -> list[Candidate]:
        """GenNav-λ: probe → reinforce → deliver, deterministic and zero-LLM.

        Every LinearDesign / CAI / LinearFold call goes through the capability
        layer (hence the CapGate audit trail); the full navigation trace is
        written to ``_workflow_state["_gennav_trace"]``.
        """
        config = MrnaNavConfig()
        # Species-correct design on the navigation path too: every probe /
        # reinforcement LinearDesign call designs against the species table.
        ld_codon_table = _lineardesign_codon_table(inp)
        pool: list[dict] = []
        gears: list[dict] = []
        seen: set[str] = set()
        raw_spent = 0
        rounds: list[dict] = []
        guaranteed_bands: set[str] = set()
        records_by_lam: dict[float, list[ToolCallRecord]] = {}
        fold_cache: dict[str, Optional[float]] = {}
        struct_cache: dict[str, str] = {}
        cai_cache: dict[str, Optional[float]] = {}
        gear_lam: float = 0.0
        nav_lock = threading.Lock()

        def _mfe_per_nt(seq: str, lam: Optional[float] = None) -> Optional[float]:
            """LinearFold MFE/nt for one CDS; records attribute to *lam*
            (``gear_lam`` fallback keeps the sequential reinforcement path)."""
            if seq in fold_cache:
                return fold_cache[seq]
            fp = save_sequence(seq, prefix="gennav_mrna_fold")
            res = self._nav_invoke(
                "predict_rna_secondary_structure_with_linearfold",
                {"filepath": fp},
                records_by_lam.setdefault(gear_lam if lam is None else lam, []),
                step_name="gennav_linearfold",
            )
            mfe = _pick_float(res.output, "mfe") if res.success else None
            value = (mfe / len(seq)) if mfe is not None else None
            fold_cache[seq] = value
            if res.success:
                struct_cache[seq] = str(res.output.get("structure", ""))
            return value

        def _cai(seq: str, lam: Optional[float] = None) -> Optional[float]:
            if seq in cai_cache:
                return cai_cache[seq]
            fp = save_sequence(seq, prefix="gennav_mrna_cai")
            res = self._nav_invoke(
                "compute_cai_for_cds_sequence",
                {"filepath": fp, "species": inp.cai_species},
                records_by_lam.setdefault(gear_lam if lam is None else lam, []),
                step_name="gennav_cai",
            )
            value = _pick_float(res.output, "cai_score") if res.success else None
            cai_cache[seq] = value
            return value

        def _probe_or_reinforce(lam: float) -> None:
            """One LinearDesign gear call at λ; adds a matrix-evaluated entry."""
            nonlocal raw_spent, gear_lam
            gear_lam = lam
            records = records_by_lam.setdefault(lam, [])
            args: dict[str, Any] = {"filepath": protein_fp, "lambda_value": lam}
            if ld_codon_table:
                args["codon_usage_path"] = ld_codon_table
            res = self._nav_invoke(
                "design_mrna_cds_with_lineardesign", args, records,
                step_name=f"gennav_lineardesign:lambda{lam:g}",
            )
            raw_spent += 1
            gears.append({"lambda": lam})
            if not res.success:
                return
            seq = str(res.output.get("generated_sequence", ""))
            if not seq or seq in seen:
                return
            seen.add(seq)
            gc = gc_fraction(seq)
            homo = max_homopolymer_run(seq)
            cai = _cai(seq)
            mfe_per_nt = _mfe_per_nt(seq)
            stem = (longest_stem_bp(struct_cache[seq])
                    if seq in struct_cache else None)
            pool.append({
                "id": f"nav:lambda{lam:g}",
                "sequence": seq,
                "gear": {"lambda": lam},
                "cai": cai,
                "mfe_per_nt": round(mfe_per_nt, 6) if mfe_per_nt is not None else None,
                "gc": round(gc, 4),
                "max_homopolymer_run": homo,
                "stem_bp": stem,
                "matrix_pass": evaluate_matrix(cai, mfe_per_nt, gc, homo,
                                               config, stem=stem),
            })

        def _probe_call(lam: float) -> Optional[dict[str, Any]]:
            """One LinearDesign gear call at λ (probe phase) — no shared-state
            mutation, so probe λs can be fetched concurrently; the caller
            integrates the results in fixed λ order (deterministic pool).

            ``gear_lam`` bookkeeping and the fold/CAI caches are guarded by
            ``nav_lock`` (double fetches are harmless — both services are
            deterministic — but concurrent dict writes are not."""
            args: dict[str, Any] = {"filepath": protein_fp, "lambda_value": lam}
            if ld_codon_table:
                args["codon_usage_path"] = ld_codon_table
            res = self._nav_invoke(
                "design_mrna_cds_with_lineardesign", args, [],
                step_name=f"gennav_lineardesign:lambda{lam:g}",
            )
            if not res.success:
                return None
            seq = str(res.output.get("generated_sequence", ""))
            if not seq:
                return None
            gc = gc_fraction(seq)
            homo = max_homopolymer_run(seq)
            with nav_lock:
                cai = _cai(seq)
                mfe_per_nt = _mfe_per_nt(seq)
            stem = (longest_stem_bp(struct_cache[seq])
                    if seq in struct_cache else None)
            return {
                "id": f"nav:lambda{lam:g}",
                "sequence": seq,
                "gear": {"lambda": lam},
                "cai": cai,
                "mfe_per_nt": round(mfe_per_nt, 6) if mfe_per_nt is not None else None,
                "gc": round(gc, 4),
                "max_homopolymer_run": homo,
                "stem_bp": stem,
                "matrix_pass": evaluate_matrix(cai, mfe_per_nt, gc, homo,
                                               config, stem=stem),
            }

        def _probe_call(lam: float) -> Optional[dict[str, Any]]:
            """One LinearDesign gear call at λ (probe phase) — no shared-state
            mutation, so probe λs can be fetched concurrently; the caller
            integrates the results in fixed λ order (deterministic pool).

            The CAI/fold measurement calls are serialized behind ``nav_lock``:
            double fetches would be harmless (both services deterministic) but
            concurrent dict writes are not; their records attribute to *lam*."""
            args: dict[str, Any] = {"filepath": protein_fp, "lambda_value": lam}
            if ld_codon_table:
                args["codon_usage_path"] = ld_codon_table
            res = self._nav_invoke(
                "design_mrna_cds_with_lineardesign", args,
                records_by_lam.setdefault(lam, []),
                step_name=f"gennav_lineardesign:lambda{lam:g}",
            )
            if not res.success:
                return None
            seq = str(res.output.get("generated_sequence", ""))
            if not seq:
                return None
            gc = gc_fraction(seq)
            homo = max_homopolymer_run(seq)
            with nav_lock:
                cai = _cai(seq, lam)
                mfe_per_nt = _mfe_per_nt(seq, lam)
            stem = (longest_stem_bp(struct_cache[seq])
                    if seq in struct_cache else None)
            return {
                "id": f"nav:lambda{lam:g}",
                "sequence": seq,
                "gear": {"lambda": lam},
                "cai": cai,
                "mfe_per_nt": round(mfe_per_nt, 6) if mfe_per_nt is not None else None,
                "gc": round(gc, 4),
                "max_homopolymer_run": homo,
                "stem_bp": stem,
                "matrix_pass": evaluate_matrix(cai, mfe_per_nt, gc, homo,
                                               config, stem=stem),
            }

        # ── Phase 1: λ-curve probe (E6 lattice) — concurrent fetch over the
        #    mutually independent probe λs, fixed-order integration (only the
        #    reinforcement rounds depend on earlier results).  Concurrency is
        #    memory-adaptive: LinearDesign RSS grows ~quadratically with
        #    protein length (~7.5 GB at 500 aa), so big proteins probe with 2
        #    workers (thread count affects scheduling only — the integration
        #    order stays fixed and the pool is identical). ──
        n_probe_workers = 2 if len(inp.protein_sequence) > 800 else \
            len(config.probe_lambdas)
        with ThreadPoolExecutor(max_workers=n_probe_workers) as ex:
            probe_futures = {lam: ex.submit(_probe_call, lam)
                             for lam in config.probe_lambdas}
        for lam in config.probe_lambdas:
            if raw_spent >= config.raw_budget:
                break
            cand = probe_futures[lam].result()
            raw_spent += 1
            gears.append({"lambda": lam})
            if cand is None:
                continue
            if cand["sequence"] in seen:
                continue
            seen.add(cand["sequence"])
            pool.append(cand)
        _LOGGER.info(
            "gennav_mrna_probe_done lambdas=%d raw_spent=%d pool=%d",
            len(config.probe_lambdas), raw_spent, len(pool),
        )

        # ── Phase 2: reinforcement — guarantee rounds first, mechanized fill ──
        while raw_spent < config.raw_budget:
            gaps = profile_gaps(pool, config)
            if all(g == 0 for g in gaps.values()):
                break  # every band already deliverable — stop early, save budget
            gear, guaranteed_bands = guarantee_round(
                pool, gears, raw_spent, config, guaranteed_bands=guaranteed_bands
            )
            kind = "guarantee"
            if gear is None:
                proposals, _ = mechanized_proposals(pool, gears, raw_spent, config)
                if not proposals:
                    break
                gear = proposals[0]
                kind = "mechanized"
            rounds.append({
                "kind": kind,
                "lambda": gear["lambda"],
                "region": gear.get("region"),
                "gaps_before": gaps,
            })
            _probe_or_reinforce(gear["lambda"])
            _LOGGER.info(
                "gennav_mrna_round kind=%s lambda=%s raw_spent=%d",
                kind, gear["lambda"], raw_spent,
            )

        # ── Phase 2.5: diversity expansion (E6 component 3, restored) ──
        # Same-λ-region designs are near-clones under the registered 2%
        # floor, so a band can hold ≥ 5 matrix-passing candidates yet deliver
        # < 5 post-D1 (measured by the v2 pilot).  Synonymous diversification
        # of the band's best unexpanded gear restores batch volume WITHOUT
        # spending LinearDesign budget — variants are local codon
        # substitutions, measured through the audited CAI/fold calls and
        # matrix-filtered like any pool entry.  Deterministic: fixed utility
        # order, seeded per (λ, band).
        expansions: list[dict[str, Any]] = []
        variants_by_band: dict[str, int] = {p_: 0 for p_ in config.profile_order}
        syn_table: Optional[dict[str, list[tuple[str, float]]]] = None
        from agent_core.sequence_utils import (
            _load_builtin_codon_tables, resolve_species_name)
        tables = _load_builtin_codon_tables()
        canonical = resolve_species_name(inp.cai_species)
        if canonical in tables:
            syn_table = codon_synonyms(tables[canonical])
        if syn_table:
            expanded_seeds: set[str] = set()
            for prof in config.profile_order:
                for _pass in range(6):  # bounded expansion passes per band
                    d_try = deliver_profile(pool, prof, config)
                    need = config.delivery_size - len(d_try["candidates"])
                    if need <= 0:
                        break
                    seeds = [c for c in pool
                             if c["matrix_pass"].get(prof)
                             and c["id"] not in expanded_seeds]
                    if not seeds:
                        break
                    seeds.sort(key=lambda c: utility_key(c, prof, config))
                    seed = seeds[0]
                    expanded_seeds.add(seed["id"])
                    if variants_by_band[prof] >= config.expansion_variant_cap:
                        break
                    want = min(need * 5, config.expansion_variant_cap
                               - variants_by_band[prof])
                    variants = synonymous_diversify(
                        seed["sequence"], syn_table, config.diversity_density,
                        n=want,
                        seed=int(seed["gear"]["lambda"] * 1000)
                        + 7919 * config.profile_order.index(prof))
                    n_added = 0
                    for v_idx, var in enumerate(variants):
                        if var in seen:
                            continue
                        gc_v = gc_fraction(var)
                        homo_v = max_homopolymer_run(var)
                        with nav_lock:
                            cai_v = _cai(var)
                            mfe_v = _mfe_per_nt(var)
                        stem_v = (longest_stem_bp(struct_cache[var])
                                  if var in struct_cache else None)
                        matrix_v = evaluate_matrix(cai_v, mfe_v, gc_v, homo_v,
                                                   config, stem=stem_v)
                        entry = {
                            "id": (f"nav:lambda{seed['gear']['lambda']:g}"
                                   f":v{v_idx}"),
                            "sequence": var,
                            "gear": {"lambda": seed["gear"]["lambda"]},
                            "cai": cai_v,
                            "mfe_per_nt": (round(mfe_v, 6)
                                           if mfe_v is not None else None),
                            "gc": round(gc_v, 4),
                            "max_homopolymer_run": homo_v,
                            "stem_bp": stem_v,
                            "matrix_pass": matrix_v,
                        }
                        seen.add(var)
                        pool.append(entry)
                        variants_by_band[prof] += 1
                        if matrix_v.get(prof):
                            n_added += 1
                    expansions.append({
                        "profile": prof,
                        "seed_lambda": seed["gear"]["lambda"],
                        "seed_id": seed["id"],
                        "n_variants": len(variants),
                        "n_passing_band": n_added,
                    })
                    _LOGGER.info(
                        "gennav_mrna_expansion prof=%s seed_lambda=%s "
                        "variants=%d passing=%d",
                        prof, seed["gear"]["lambda"], len(variants), n_added)

        # ── Phase 3: per-profile mechanized delivery ──
        deliveries = {
            prof: deliver_profile(pool, prof, config)
            for prof in config.profile_order
        }
        self._workflow_state["_gennav_trace"] = {
            "protocol": "gennav_lambda_production_v1",
            "raw_budget": config.raw_budget,
            "raw_spent": raw_spent,
            "expansions": expansions,
            "probe": {"lambdas": list(config.probe_lambdas)},
            "rounds": rounds,
            "final_gaps": profile_gaps(pool, config),
            "pool_size": len(pool),
            "deliveries": deliveries,
        }

        by_id = {c["id"]: c for c in pool}
        delivered: list[Candidate] = []
        chosen: set[str] = set()
        for prof in config.profile_order:
            for rank, rec in enumerate(deliveries[prof]["candidates"], start=1):
                if rec["id"] in chosen:
                    for cand in delivered:
                        if cand.metadata.get("nav_id") == rec["id"]:
                            cand.metadata["nav_bands"].append(prof)
                    continue
                chosen.add(rec["id"])
                src = by_id[rec["id"]]
                lam = src["gear"]["lambda"]
                cand = Candidate(
                    sequence=src["sequence"],
                    sequence_type="mrna",
                    source=f"cds_design_gennav:lambda{lam:g}",
                    metadata={
                        "design_tool": "lineardesign",
                        "design_params": {"lambda_value": lam},
                        "protein_sequence": inp.protein_sequence,
                        "protein_filepath": protein_fp,
                        "cai_species": inp.cai_species,
                        "nav_id": rec["id"],
                        "nav_bands": [prof],
                        "nav_delivery_rank": rank,
                        "nav_gear": dict(src["gear"]),
                        "nav_matrix_pass": dict(src["matrix_pass"]),
                        "nav_cai": src["cai"],
                        "nav_mfe_per_nt": src["mfe_per_nt"],
                    },
                )
                for record in records_by_lam.get(lam, []):
                    cand.add_tool_record(record)
                delivered.append(cand)
        _LOGGER.info(
            "gennav_mrna_delivery raw_spent=%d pool=%d delivered=%d degraded=%s",
            raw_spent, len(pool), len(delivered),
            {p: deliveries[p]["degraded"] for p in config.profile_order},
        )
        return delivered

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run GC + fold (+ unpaired fraction) on the candidate sequence."""
        filepath = save_sequence(candidate.sequence, prefix="mrna_cds")
        candidate.metadata["workspace_filepath"] = filepath

        # Update evaluator flags from workflow state
        for ev in self.evaluator.evaluators:
            if isinstance(ev, SecondaryStructureEvaluator):
                ev.run_fold = self._run_fold
            if isinstance(ev, GCContentEvaluator):
                ev.run_gc = self._run_gc

        context: dict[str, Any] = {"workflow_state": self._workflow_state}
        if "cai_species" in candidate.metadata:
            context["species"] = candidate.metadata["cai_species"]

        metrics = self.evaluator.evaluate(candidate, context)

        # Domain-specific: warn about missing species when CAI evaluation fails
        cai_species = candidate.metadata.get("cai_species", DEFAULT_CAI_SPECIES)
        if (
            "cai_score" not in metrics
            and self.capabilities.has("compute_cai_for_cds_sequence")
        ):
            try:
                builtin = _load_builtin_codon_tables()
                resolved = resolve_species_name(cai_species)
                if resolved not in builtin:
                    available = ", ".join(sorted(builtin.keys()))
                    _LOGGER.warning(
                        "Species '%s' not available in built-in codon tables. "
                        "Available species: %s. To compute CAI for this species, "
                        "provide a custom codon usage table JSON via the "
                        "compute_cai_for_cds_sequence tool's custom_codon_table_path parameter.",
                        cai_species,
                        available,
                    )
            except Exception:
                pass

        bundle = compute_mrna_metric_bundle(
            sequence=candidate.sequence,
            gc_from_tools=metrics.get("gc_content"),
            sequence_length_from_tools=metrics.get("sequence_length"),
            mfe_kcal_per_mol=metrics.get("mfe_kcal_per_mol"),
            unpaired_fraction=metrics.get("unpaired_fraction"),
            rnastop_overall_stability=metrics.get("rnastop_overall_stability"),
            cai_score=metrics.get("cai_score"),
            u_fraction=metrics.get("u_fraction"),
        )
        bundle["fold_tool"] = metrics.get("fold_tool")
        bundle["cai_species"] = cai_species
        candidate.metadata["metrics_bundle"] = bundle
        candidate.metadata["fold_tool"] = metrics.get("fold_tool")
        if "structure" not in candidate.metadata:
            candidate.metadata["structure"] = metrics.get("structure")
        return bundle

    # ─────────────────────────────────────────────────────────────────────────

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return score_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            errors = ["empty_candidate_list"]
            if self._generation_errors:
                errors.extend(self._generation_errors)
            # Navigation empties are the dedicated degrade (delivery matrix
            # empty in every profile), mirroring the aptamer GenNav semantics.
            if self._workflow_state.get("_gennav_trace") and not self._generation_errors:
                errors = ["navigation_delivery_empty"]
            return WorkflowResult(
                success=False,
                task_id="",
                summary=(
                    "CDS navigation completed but no candidate passed the "
                    "constraint matrix in any profile (explicit degrade)."
                    if "navigation_delivery_empty" in errors
                    else "No candidates produced."
                ),
                errors=errors,
            )

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )

        # Pareto annotation (v1.2.0): CAI (max) × MFE/nt (min) frontier over the
        # measured pool — the classic LinearDesign trade-off view. Ranking stays
        # total_score; the frontier is an extras annotation for consumers.
        pareto_objectives = ["cai_score", "mfe_per_nt"]
        pareto_maximize = {"cai_score": True, "mfe_per_nt": False}
        frontier = compute_pareto_frontier(ranked, pareto_objectives, pareto_maximize)
        assign_pareto_tags(frontier, pareto_objectives, pareto_maximize)

        best = ranked[0] if ranked else None

        # Build rich per-candidate summary lines
        detail_lines: list[str] = []
        for i, c in enumerate(ranked, start=1):
            mb = c.metadata.get("metrics_bundle", {})
            scores = c.scores
            line_parts = [
                f"#{i}",
                f"source={c.source}",
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"MFE={mb.get('mfe_kcal_per_mol'):.2f}({mb.get('fold_tool', '?')})" if mb.get("mfe_kcal_per_mol") is not None else "MFE=N/A",
                f"MFE/nt={mb.get('mfe_per_nt'):.4f}" if mb.get("mfe_per_nt") is not None else "MFE/nt=N/A",
                f"unpaired={mb.get('unpaired_fraction'):.3f}" if mb.get("unpaired_fraction") is not None else "unpaired=N/A",
                f"RNASTOP={mb.get('rnastop_overall_stability'):.4f}" if mb.get("rnastop_overall_stability") is not None else "RNASTOP=N/A",
                f"CAI={mb.get('cai_score'):.4f}" if mb.get("cai_score") is not None else "CAI=N/A",
                f"U={mb.get('u_fraction'):.3f}" if mb.get("u_fraction") is not None else "U=N/A",
                f"total_score={scores.get('total_score', 0.0):.3f}",
            ]
            detail_lines.append(" | ".join(line_parts))

        summary_parts = [
            f"candidates={len(ranked)}",
            f"best_total_score={best.scores.get('total_score') if best else None}",
            f"pareto_frontier_size={len(frontier)}",
            "---",
            *detail_lines,
        ]
        return WorkflowResult(
            success=True,
            task_id=f"mrna_cds_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
            pareto_frontier=frontier,
        )


