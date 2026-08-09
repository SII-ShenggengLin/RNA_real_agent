"""mRNA CDS design & optimisation workflow — the golden path (Layer 2).

Protein sequence → CDS design (LinearDesign λ=[0,1,4,10] where λ∈[0,+∞), typically ≤10 + RNARL + GEMORNA) →
fold + GC + unpaired-fraction evaluation → scoring → ranking → WorkflowResult.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  MrnaCdsDesignWorkflow INTERFACE LOCK (v1.1.0) —— 禁止单方面变更            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 mrna_cds_design workflow 的权威实现。任何字段增删、函数签名变动、  ║
║  返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：               ║
║                                                                               ║
║    - agent_core/workflows/mrna_cds_design.py  ← 本文件                       ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/capabilities/base.py                                          ║
║    - agent_core/planning/base.py                                              ║
║    - agent_core/agents/quality_agent.py                                       ║
║    - agent_core/agents/specialist_agent.py                                    ║
║    - agent_core/agents/pipeline_agent.py                                      ║
║    - agent_core/quality_profiles/mrna_cds_design.py                           ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_mrna_cds_design_workflow.py                                   ║
║    - docs/INTERFACE_LOCKS.md                                                  ║
║    - docs/WORKFLOWS.md                                                        ║
║    - AGENTS.md                                                                ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_core.capabilities.base import CapabilityRegistry
from agent_core.file_manager import save_sequence
from agent_core.sequence_utils import (
    _load_builtin_codon_tables,
    resolve_species_name,
)
from agent_core.constants.species import (
    DEFAULT_CAI_SPECIES,
    DEFAULT_RNARL_MODEL_TYPE,
    RNARLModelType,
    RNARL_MODEL_TYPES_LIST,
    format_cai_species_aliases,
    format_rnarl_model_types,
)
from agent_core.workflow_models import Candidate, ToolCallRecord, WorkflowResult, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
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
# Input model — INTERFACE LOCKED (v1.0.0)
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
# ─────────────────────────────────────────────────────────────────────────────
# Workflow — INTERFACE LOCKED (v1.0.0)
# ─────────────────────────────────────────────────────────────────────────────


class MrnaCdsDesignWorkflow(BaseDomainWorkflow[MrnaCdsDesignInput, WorkflowResult]):
    """Golden-path workflow: protein → multi-tool CDS → fold + GC + unpaired → score → rank."""

    name = "mrna_cds_design"
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

        design_configs: list[tuple[str, dict[str, Any]]] = []

        def _ld_args(lam: float) -> dict[str, Any]:
            extra: dict[str, Any] = {"lambda_value": lam}
            if inp.lineardesign_codon_usage_path:
                extra["codon_usage_path"] = str(inp.lineardesign_codon_usage_path)
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
    # Scoring — INTERFACE LOCKED (v1.0.0)
    # ─────────────────────────────────────────────────────────────────────────

    def score(self, metrics: dict[str, Any]) -> dict[str, Any]:
        return score_mrna_candidate(metrics)

    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResult:
        if not candidates:
            errors = ["empty_candidate_list"]
            if self._generation_errors:
                errors.extend(self._generation_errors)
            return WorkflowResult(
                success=False,
                task_id="",
                summary="No candidates produced.",
                errors=errors,
            )

        ranked = sort_candidates_by_score(
            candidates, score_key="total_score", descending=True
        )
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
        )


