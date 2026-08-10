"""RNA aptamer design workflow — structure-driven generation against protein targets (Layer 2).

Protein (sequence or 3D structure) → hotspot identification →
ODesign aptamer generation → fold + GC + RhoFold (+ EGARPS) evaluation →
scoring → ranking → WorkflowResult.

Key design principles
---------------------
1. **Structure-first**: ODesign is the only tool in the project that supports
   3D-structure-guided RNA design against a protein target.
2. **Binding-centric scoring**: Unlike mRNA workflows that optimise CAI/MFE,
   aptamer workflows optimise binding affinity (EGARPS native_probability)
   and foldability (RhoFold pLDDT, ViennaRNA MFE).
3. **Graceful degradation**: EGARPS requires a complex PDB; if it is unavailable
   or the file format does not match, the workflow continues with the remaining
   metrics rather than failing entirely.

╔═══════════════════════════════════════════════════════════════════════════════╗
║  RnaAptamerDesignWorkflow INTERFACE LOCK (v1.4.2) —— 禁止单方面变更         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  本文件为 rna_aptamer_design workflow 的权威实现。任何字段增删、            ║
║  函数签名变动、返回值结构调整，必须同时更新以下全部文件并重新跑通端到端测试：║
║                                                                               ║
║    - agent_core/workflows/rna_aptamer_design.py  ← 本文件                   ║
║    - agent_core/workflows/base.py                                             ║
║    - agent_core/quality_profiles/__init__.py                                  ║
║    - agent_core/workflows/__init__.py                                         ║
║    - agent_core/runner.py                                                     ║
║    - agent_core/state.py                                                      ║
║    - agent_core/agents/quality_agent.py                                       ║
║    - agent_core/agents/specialist_agent.py                                    ║
║    - agent_core/agents/pipeline_agent.py                                      ║
║    - agent_core/agents/coordinator_agent.py                                   ║
║    - agent_core/quality_profiles/rna_aptamer_design.py                        ║
║    - agent_core/tool_specs.py                                                 ║
║    - agent_core/tools.py                                                      ║
║    - tests/test_rna_aptamer_design.py                                         ║
║                                                                               ║
║  规则：违反此规则的提交将被回退。                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_core.capabilities.base import CapabilityRegistry, CapabilityResult
from agent_core.file_manager import (
    read_sequence,
    resolve_project_path,
    save_sequence,
    save_text_file,
)
from agent_core.sequence_utils import _pick_float
from agent_core.workflow_models import Candidate, WorkflowResult, ToolCallRecord, sort_candidates_by_score
from agent_core.workflows.base import BaseDomainWorkflow
from agent_core.workflows.coordinator import (
    AptamerCoordinationRound,
    AptamerCoordinator,
    Issue,
    ModuleFeedback,
)
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

_LOGGER = logging.getLogger("agent_core.workflows.rna_aptamer_design")

# Input model


class RnaAptamerDesignInput(BaseModel):
    """Input for the RNA aptamer design workflow."""
    # Tool-level parameter overrides (from tools_parameter_analysis.json)
    hotspots_protein_structure_path: str = Field(default=None, description="[hotspots] protein_structure_path: Path to protein PDB or CIF file.")
    hotspots_chain_id: str = Field(default='', description="[hotspots] chain_id: Protein chain ID to analyze.")
    odesign_input_protein_structure_path: str = Field(default=None, description="[odesign_input] protein_structure_path: Path to protein PDB or CIF file.")
    odesign_input_protein_chain_id: str = Field(default=None, description="[odesign_input] protein_chain_id: Protein chain ID, e.g. 'C'.")
    odesign_input_protein_sequence_length: int = Field(default=None, description="[odesign_input] protein_sequence_length: Protein sequence length.")
    odesign_input_hotspot_residues: str = Field(default=None, description="[odesign_input] hotspot_residues: Hotspot residues, format like 'C/18,C/90,C/79,C/49'.")
    odesign_input_aptamer_length: int = Field(default=None, description="[odesign_input] aptamer_length: Desired RNA aptamer length in nucleotides.")
    odesign_input_output_prefix: Optional[str] = Field(default=None, description="[odesign_input] output_prefix: Output filename prefix.")
    odesign_input_json_filepath: str = Field(default=None, description="[odesign] input_json_filepath: Path to an ODesign input JSON file following the upstream format (target structure, hotspot residues/atoms, chain_type, etc.).")
    odesign_service_url: str = Field(default='http://127.0.0.1:8012/design/from-json', description="[odesign] service_url: HTTP endpoint of the ODesign microservice.")
    odesign_infer_model_name: str = Field(default='odesign_base_na_rigid', description="[odesign] infer_model_name: Upstream ODesign model checkpoint name (without .pt). Examples: odesign_base_na_rigid, odesign_base_prot_flex, odesign_base_prot_rigid, odesign_base_ligand_rigid.")
    odesign_design_modality: str = Field(default='rna', description="[odesign] design_modality: Design modality passed to ODesign. Must be one of: protein, ligand, dna, rna.")
    odesign_exp_name: str = Field(default=None, description="[odesign] exp_name: Custom experiment name for the output directory. If omitted, a unique name is auto-generated.")
    odesign_seeds_json: str = Field(default='[42]', description="[odesign] seeds_json: JSON list string of integer random seeds (e.g. '[42]' or '[42, 123]').")
    odesign_n_sample: int = Field(default=1, description="[odesign] n_sample: Number of generated samples per seed.")
    odesign_use_msa: bool = Field(default=False, description="[odesign] use_msa: Whether the input JSON provides MSA features for ODesign inference.")
    odesign_num_workers: int = Field(default=2, description="[odesign] num_workers: Number of dataloader workers.")
    odesign_cuda_visible_devices: str = Field(default=None, description="[odesign] cuda_visible_devices: Override for CUDA_VISIBLE_DEVICES (e.g. '0' or '0,1').")
    odesign_enable_partial_diff: bool = Field(default=False, description="[odesign] enable_partial_diff: Enable ODesign partial diffusion mode, which redesigns only specified regions of an existing molecule.")
    odesign_snr: float = Field(default=0.1, description="[odesign] snr: Signal-to-noise ratio for partial diffusion.")
    odesign_ckpt_root_dir: str = Field(default=None, description="[odesign] ckpt_root_dir: Optional checkpoint root directory override.")
    odesign_data_root_dir: str = Field(default=None, description="[odesign] data_root_dir: Optional data root directory override (must contain components.cif and rdkit pickle).")
    odesign_invfold_topk: int = Field(default=1, description="[odesign] invfold_topk: Number of designed sequences per backbone structure from the inverse-folding head.")
    odesign_invfold_temp: float = Field(default=1.0, description="[odesign] invfold_temp: Inverse-folding sampling temperature.")
    odesign_invfold_use_beam: bool = Field(default=True, description="[odesign] invfold_use_beam: Whether to use beam search in inverse folding.")
    odesign_timeout_seconds: int = Field(default=14400, description="[odesign] timeout_seconds: Subprocess timeout for one ODesign inference request.")
    odesign_config_architecture_hyperparameters: Any = Field(default='See external_repos/ODesign/configs/model/_base.yaml', description="[odesign] config architecture hyperparameters (upstream only): Many architecture and diffusion hyperparameters (hidden dims, number of layers, noise schedule, etc.) live in the Hydra configs and are not exposed by the wrapper.")
    gc_filepath: str = Field(default=None, description="[gc] filepath: Path to RNA or DNA sequence (workspace or server absolute); FASTA or plain text.")
    gc_service_url: str = Field(default='http://127.0.0.1:8020/gc-content', description="[gc] service_url: POST endpoint for GC content microservice.")
    gc_timeout_seconds: float = Field(default=120.0, description="[gc] timeout_seconds: HTTP request timeout in seconds.")
    rhofold_filepath: str = Field(default=None, description="[rhofold] filepath: Path to a file containing the RNA sequence (plain text or FASTA). The wrapper reads the sequence and sends it to the microservice.")
    rhofold_service_url: str = Field(default='http://127.0.0.1:8005/predict', description="[rhofold] service_url: HTTP endpoint of the RhoFold microservice.")
    rhofold_relax_steps: int = Field(default=0, description="[rhofold] relax_steps: Number of Amber relaxation iterations applied to the unrelaxed structure. 0 skips relaxation.")
    rhofold_checkpoint_path: str = Field(default=None, description="[rhofold] checkpoint_path: Path to a custom RhoFold checkpoint. If omitted, the service searches standard pretrained paths.")
    rhofold_device: str = Field(default=None, description="[rhofold] device: Torch device string passed to upstream inference.py, e.g. 'cpu', 'cuda', 'cuda:0'.")
    rhofold_single_seq_pred: bool = Field(default=True, description="[rhofold] single_seq_pred: Microservice-only flag. If True, RhoFold uses only the input sequence (input_fas) as the MSA. If False, an A3M file is generated or supplied.")
    rhofold_input_a3m_path: str = Field(default=None, description="[rhofold] input_a3m_path: Microservice-only path to a precomputed A3M MSA file. Used only when single_seq_pred is False.")
    rhofold_timeout_seconds: int = Field(default=7200, description="[rhofold] timeout_seconds: Subprocess timeout for one RhoFold run (microservice level).")
    rhofold_database_dpath_binary_dpath: str = Field(default='./database and ./rhofold/data/bin', description="[rhofold] database_dpath / binary_dpath: Upstream-only paths to BLAST databases and BLAST binaries for MSA generation. Not exposed by the microservice.")
    egarps_filepath: str = Field(default=None, description="[egarps] filepath: Path to a PDB file containing the RNA-protein complex structure to score.")
    egarps_academic: bool = Field(default=False, description="[egarps] academic: If True, use full academic mode with DSSR and NACCESS features. If False, use the reduced non-academic mode.")
    egarps_service_url: str = Field(default='http://127.0.0.1:8023/score', description="[egarps] service_url: HTTP endpoint of the EGARPS+ microservice.")
    egarps_mini: bool = Field(default=False, description="[egarps] -mini (upstream-only flag): Upstream predict.py supports a '-mini' flag that uses a single lightweight model in academic mode. Not exposed by the microservice.")
    extract_rna_cif_filepath: str = Field(default=None, description="[extract_rna] cif_filepath: Path to CIF/MMCIF file (workspace or absolute).")
    extract_rna_chain_id: Optional[str] = Field(default=None, description="[extract_rna] chain_id: Chain ID to extract; auto-detect first RNA chain if omitted.")
    proteinx_protein_filepath: str = Field(default=None, description="[proteinx] protein_filepath: Path to a FASTA file containing the protein sequence.")
    proteinx_rna_filepath: str = Field(default=None, description="[proteinx] rna_filepath: Path to a FASTA file containing the RNA sequence.")
    proteinx_num_models: int = Field(default=1, description="[proteinx] num_models: Number of inference samples to generate.")
    proteinx_num_recycles: int = Field(default=10, description="[proteinx] num_recycles: Number of Pairformer cycles. Ignored when use_default_params is True.")
    proteinx_msa_mode: str = Field(default='none', description="[proteinx] msa_mode: MSA generation mode. 'none' disables MSA; 'protenix' enables the Protenix MSA server.")
    proteinx_service_url: str = Field(default='http://127.0.0.1:8022/predict/complex', description="[proteinx] service_url: HTTP endpoint of the ProteinX complex microservice.")
    proteinx_timeout_seconds: int = Field(default=7200, description="[proteinx] timeout_seconds: Wrapper-level request timeout.")
    proteinx_model_name: str = Field(default='protenix_base_default_v1.0.0', description="[proteinx] model_name: Protenix model checkpoint name. Microservice-only; wrapper does not expose it.")
    proteinx_use_default_params: bool = Field(default=True, description="[proteinx] use_default_params: Use recommended default parameters for the selected model. Microservice-only.")
    proteinx_step_dtype_use_template_use_rna_msa: Any = Field(default='step=200, dtype=bf16, use_template=False, use_rna_msa=False', description="[proteinx] step / dtype / use_template / use_rna_msa (upstream CLI): Additional Protenix CLI flags not exposed by the wrapper. They control diffusion steps, precision, templates, and RNA MSA.")
    interface_complex_pdb_filepath: str = Field(default=None, description="[interface] complex_pdb_filepath: Path to RNA-protein complex PDB or CIF file.")
    interface_protein_chain_id: str = Field(default='A', description="[interface] protein_chain_id: Protein chain ID.")
    interface_rna_chain_id: str = Field(default='B', description="[interface] rna_chain_id: RNA chain ID.")
    interface_contact_cutoff: float = Field(default=5.0, description="[interface] contact_cutoff: Distance cutoff (\u00c5) for interface contacts.")
    protein_sequence: Optional[str] = Field(
        default=None,
        description="Amino-acid string (uppercase, 1-letter codes). "
                    "Either this or protein_structure_path must be provided.",
    )
    protein_structure_path: Optional[str] = Field(
        default=None,
        description="Path to protein PDB or CIF file. "
                    "Either this or protein_sequence must be provided.",
    )
    chain_id: str = Field(default="A", description="Protein chain ID to target.")
    aptamer_length: int = Field(
        default=30, ge=10, le=200, description="Desired aptamer length in nucleotides."
    )
    hotspot_residues: Optional[str] = Field(
        default=None,
        description="Explicit hotspot residues, e.g. 'A/18,A/90'. "
                    "If omitted, automatic identification is performed.",
    )
    n_odesign_samples: int = Field(
        default=8, ge=1, le=20, description="Number of ODesign samples to generate."
    )
    odesign_seeds: list[int] = Field(
        default_factory=lambda: [42, 123],
        description="Random seeds for ODesign inference.",
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
            "Optional per-objective reference point for Achievement Scalarizing Function "
            "selection and BMC coordination. Keys must be one of: egarps_component, "
            "rhofold_component, iptm_component. If omitted, a utopian point is derived "
            "from the candidate pool."
        ),
    )

    @field_validator("protein_sequence")
    @classmethod
    def _validate_protein_sequence(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        seq = v.strip().upper()
        invalid = set(ch for ch in seq if ch not in "ACDEFGHIKLMNPQRSTVWY")
        if invalid:
            raise ValueError(
                f"Invalid amino-acid characters: {''.join(sorted(invalid))}. "
                "Only standard 1-letter codes are allowed."
            )
        return seq
    @field_validator("hotspot_residues")
    @classmethod
    def _validate_hotspot_residues(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = re.compile(r"^([A-Za-z]/\d+|\d+)(,([A-Za-z]/\d+|\d+))*$")
        if not pattern.match(v.strip()):
            raise ValueError(
                "Hotspot residues must be formatted as 'chain/num,chain/num' or 'num,num', "
                "e.g. 'A/18,A/90' or '18,90'."
            )
        return v.strip()

    @model_validator(mode="after")
    def _validate_reference_point(self) -> "RnaAptamerDesignInput":
        """Validate reference_point keys if provided."""
        if self.reference_point is None:
            return self
        allowed = {"egarps_component", "rhofold_component", "iptm_component"}
        unknown = set(self.reference_point.keys()) - allowed
        if unknown:
            raise ValueError(
                f"reference_point contains unknown objectives: {unknown}. "
                f"Allowed: {allowed}"
            )
        return self

class RnaAptamerDesignWorkflow(BaseDomainWorkflow[RnaAptamerDesignInput, WorkflowResult]):
    input_model = RnaAptamerDesignInput
    """Structure-driven RNA aptamer design: protein target → ODesign → evaluate → rank."""

    name = "rna_aptamer_design"
    description = (
        "Design RNA aptamers against a protein target using 3D-structure-guided generation. "
        "Pipeline: hotspot identification → ODesign generation → fold + RhoFold + EGARPS evaluation → scoring → ranking."
    )
    required_capabilities = [
        "identify_protein_binding_hotspots",
        "build_odesign_aptamer_input_json",
        "run_odesign_inference",
        "compute_rna_sequence_gc_content",
        "predict_rna_tertiary_structure_with_rhofold",
        "score_rna_protein_complex_with_egarps",
        "extract_rna_sequence_from_cif",
        "predict_rna_protein_complex_with_proteinx",
        "analyze_rna_protein_interface",
        "predict_protein_structure_with_proteinx",
    ]

    def __init__(self, capability_registry: CapabilityRegistry):
        self.capabilities = capability_registry
        self._workflow_state: dict[str, Any] = {}
        self._bmc_trace: list[AptamerCoordinationRound] = []
        self._workflow_trace: list[ToolCallRecord] = []
        # Reference-point stability across BMC rounds.
        self._fixed_norm_ref_point: Optional[dict[str, float]] = None
        self._fixed_dim_bounds: Optional[dict[str, dict[str, float]]] = None
        self._reference_point_mode: Literal["user", "utopian"] = "utopian"

    def _ensure_services_running(self) -> Optional[WorkflowResult]:
        """Check required microservices and auto-start any that are down.

        This is the RNA-aptamer-specific entry point kept for backward
        compatibility; the actual logic is delegated to the base-class service
        pre-flight.  Tests may still patch this method to a no-op (returning
        ``None`` implicitly means success).

        Returns ``None`` when services are ready, otherwise a failed
        ``WorkflowResult`` that ``run_initial()`` can return directly.
        """
        return self._service_preflight_result()

    # ─────────────────────────────────────────────────────────────────────────
    # Structured tracing helper
    # ─────────────────────────────────────────────────────────────────────────

    def _invoke_and_record(
        self,
        cap_name: str,
        args: dict[str, Any],
        *,
        candidate: Optional[Candidate] = None,
        step_name: Optional[str] = None,
        required: bool = False,
    ) -> CapabilityResult:
        """Invoke a capability and create a structured ToolCallRecord.

        Records are attached to *candidate* when provided, otherwise to the
        workflow-level ``_workflow_trace``.  Missing capabilities are logged
        and return a failed CapabilityResult unless *required* is True.
        """
        if not self.capabilities.has(cap_name):
            msg = f"Capability '{cap_name}' not registered"
            if required:
                raise KeyError(msg)
            _LOGGER.warning("capability_missing %s", cap_name)
            return CapabilityResult(success=False, tool_name=cap_name, error=msg)

        cap = self.capabilities.get(cap_name)
        start = time.perf_counter()
        cap_result = cap.invoke(args, state=self._workflow_state)
        elapsed = time.perf_counter() - start

        record = ToolCallRecord(
            step_name=step_name or cap_name,
            tool_name=cap_name,
            input_summary=str(args)[:500],
            output_summary=str(cap_result.output)[:500] if cap_result.success else "",
            success=cap_result.success,
            error=cap_result.error,
            elapsed_time=elapsed,
            artifacts=dict(cap_result.output) if cap_result.success else {},
            metrics={"elapsed_time": elapsed},
        )

        if candidate is not None:
            candidate.add_tool_record(record)
        else:
            self._workflow_trace.append(record)

        return cap_result

    # ─────────────────────────────────────────────────────────────────────────
    # BaseDomainWorkflow interface
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, inp: Any, *, progress_callback=None) -> WorkflowResult:
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
        inp: Any,
        *,
        progress_callback=None,
    ) -> WorkflowResult:
        """Phase 1 & 2: prepare target, generate aptamers, evaluate, score, and rank.

        Resets per-run workflow state and returns the initial ``WorkflowResult``.
        State writeback is intentionally left to ``bmc_finalize()`` so that both
        early-exit and fully-coordinated runs attach state consistently.
        """
        if isinstance(inp, dict):
            inp = RnaAptamerDesignInput(**inp)
        self._workflow_state = {}  # reset per run
        self._workflow_state["_aptamer_input"] = inp
        self._bmc_trace: list[AptamerCoordinationRound] = []

        # ── Pre-flight: ensure all required microservices are running ──
        preflight = self._ensure_services_running()
        if preflight is not None:
            return preflight

        # ── Phase 1: Module preparation and initial generation ──
        protein_path, hotspot, protein_seq_len = self._prepare_target_module(inp)
        if not protein_path or not hotspot:
            merged_wb = dict(self._workflow_state)
            merged_wb["_workflow_params"] = inp.model_dump()
            return WorkflowResult(
                success=False,
                task_id="",
                summary="Aptamer design failed during target preparation.",
                errors=["target_preparation_failed"],
                _state_writeback=merged_wb,  # type: ignore[attr-defined]
            )

        # Cache target info for BMC rounds so regeneration can reuse it without
        # re-resolving the protein structure.
        self._workflow_state["_bmc_protein_path"] = protein_path
        self._workflow_state["_bmc_hotspot"] = hotspot
        self._workflow_state["_bmc_protein_seq_len"] = protein_seq_len

        candidates = self._generate_aptamer_module(
            protein_path, hotspot, inp, protein_seq_len=protein_seq_len
        )
        if not candidates:
            merged_wb = dict(self._workflow_state)
            merged_wb["_workflow_params"] = inp.model_dump()
            return WorkflowResult(
                success=False,
                task_id="",
                summary="Aptamer design failed during candidate generation.",
                errors=["candidate_generation_failed"],
                _state_writeback=merged_wb,  # type: ignore[attr-defined]
            )

        # ── Phase 2: Two-stage concurrent evaluation (light on all, heavy on top-k) ──
        evaluated_candidates = self._evaluate_candidates_concurrent(
            candidates,
            progress_callback=progress_callback,
            progress_event="evaluate_progress",
        )

        return self.rank_and_format(evaluated_candidates)

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
        inp = self._workflow_state.get("_aptamer_input")
        if inp is None:
            raise RuntimeError("bmc_prepare called before run_initial")

        self._workflow_state["_bmc_max_rounds"] = inp.bmc_max_rounds
        self._workflow_state["_bmc_improvement_threshold"] = inp.bmc_improvement_threshold

        coordinator = AptamerCoordinator()
        max_rounds = inp.bmc_max_rounds
        improvement_threshold = inp.bmc_improvement_threshold

        # Initial reference point and ASF for the current best candidate.
        # If the user supplied a reference point, fix its normalization to the
        # initial candidate pool so the aspiration level stays stable across BMC
        # rounds. The utopian point is allowed to evolve as the pool improves.
        norm_ref_point, _, dim_bounds = build_normalized_reference_point(
            initial_result.all_candidates,
            AptamerCoordinator.USER_FACING_OBJECTIVES,
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
        progress_callback=None,
    ) -> tuple[WorkflowResult, dict[str, Any], bool, str]:
        """Execute one BMC coordination round.

        Diagnoses the current candidate pool against the reference point,
        broadcasts feedback, regenerates affected modules, evaluates new
        candidates, and re-ranks the merged pool.

        Returns ``(result, bmc_state, should_stop, reason)``.
        """
        # Service pre-flight: recover any service that went down between rounds.
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

        protein_path = self._workflow_state.get("_bmc_protein_path")
        hotspot = self._workflow_state.get("_bmc_hotspot")
        protein_seq_len = self._workflow_state.get("_bmc_protein_seq_len")
        if not protein_path or not hotspot:
            return result, bmc_state, True, "missing_target_info"

        # Select the reference point for this round.
        if self._reference_point_mode == "user":
            norm_ref_point = self._fixed_norm_ref_point
            dim_bounds = self._fixed_dim_bounds
        else:
            norm_ref_point, _, dim_bounds = build_normalized_reference_point(
                result.all_candidates,
                AptamerCoordinator.USER_FACING_OBJECTIVES,
                user_reference_point=None,
            )

        # Diagnose a representative set: ASF best + per-objective leaders.
        diagnosis_candidates = self._select_diagnosis_candidates(
            result.all_candidates,
            AptamerCoordinator.USER_FACING_OBJECTIVES,
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

        # Use the metrics of the candidate that triggered the worst issue,
        # not necessarily the ASF best, when broadcasting feedback.
        worst_issue = max(issues, key=lambda i: i.violation)
        feedback_metrics = issue_source_metrics[worst_issue.issue_type]

        # NOTE (Fig 5b ablation): pool-mean metrics over the current candidate
        # pool. Only consumed by broadcast_feedback when the subprocess runs
        # with APTAMER_FEEDBACK_MODE=pool_average; ignored otherwise, so the
        # default source-aware behavior is unchanged.
        pool_metrics = self._pool_mean_metrics(result.all_candidates)
        feedback = coordinator.broadcast_feedback(
            issues, feedback_metrics, pool_metrics=pool_metrics
        )
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
            protein_path,
            hotspot,
            protein_seq_len,
            best,
            issues=issues,
            issue_source_metrics=issue_source_metrics,
        )

        if not new_candidates:
            _LOGGER.info("bmc_no_new_candidates round=%d", round_num)
            return result, bmc_state, True, "no_new_candidates"

        # Evaluate new candidates (two-stage concurrent)
        new_evaluated = self._evaluate_candidates_concurrent(
            new_candidates,
            progress_callback=progress_callback,
            progress_event="bmc_evaluate_progress",
            progress_extra={"round": round_num},
        )

        # Merge and re-rank
        all_candidates = result.all_candidates + new_evaluated
        result = self.rank_and_format(all_candidates)

        new_best = result.best_candidate
        new_asf = self._candidate_asf(new_best, norm_ref_point, dim_bounds)

        # Record round trace
        time_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        round_trace = AptamerCoordinationRound(
            round_num=round_num,
            best_candidate_id=new_best.id if new_best else "",
            best_total_score=-new_asf,
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
        inp = self._workflow_state.get("_aptamer_input")
        if inp is None:
            return result

        # Aggregate per-candidate and workflow-level tool records into result.trace
        for c in result.all_candidates:
            result.trace.extend(c.tool_records)
        result.trace.extend(self._workflow_trace)

        # Attach BMC trace and state writeback
        merged_wb = dict(self._workflow_state)
        merged_wb["_workflow_params"] = inp.model_dump()
        merged_wb["_bmc_trace"] = [r.to_dict() for r in self._bmc_trace]
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

    # ─────────────────────────────────────────────────────────────────────────
    # BMC Module-level helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _select_diagnosis_candidates(
        self,
        candidates: list[Candidate],
        objectives: tuple[str, ...],
        best_candidate: Candidate | None,
    ) -> list[Candidate]:
        """Return the set of candidates that should be diagnosed by BMC.

        Always includes the current best candidate. Additionally includes the
        per-objective leader (highest raw score) for each diagnostic objective.
        This exposes trade-offs that the single best candidate may hide.
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
    def _pool_mean_metrics(candidates: list[Candidate]) -> dict[str, float]:
        """Mean of each numeric metric across the candidate pool.

        Averages every numeric entry of each candidate's ``metrics_bundle``
        (e.g. ``rhofold_mean_plddt``) over all candidates that report it.
        Used only by the ``APTAMER_FEEDBACK_MODE=pool_average`` ablation
        (Fig 5b); non-numeric and boolean entries are skipped.
        """
        sums: dict[str, float] = {}
        counts: dict[str, int] = {}
        for cand in candidates:
            bundle = cand.metadata.get("metrics_bundle", {}) or {}
            for key, value in bundle.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                sums[key] = sums.get(key, 0.0) + float(value)
                counts[key] = counts.get(key, 0) + 1
        return {k: sums[k] / counts[k] for k in sums if counts[k]}

    @staticmethod
    def _merge_issues_with_sources(
        issues_with_sources: list[tuple[Issue, dict[str, Any]]],
    ) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
        """Merge issues by type, keeping the one with the largest violation.

        Returns a mapping from issue_type to the metrics bundle of the candidate
        that contributed the worst instance. This lets downstream feedback be
        based on the candidate that actually triggered the issue, rather than
        always the ASF best.
        """
        merged: dict[str, Issue] = {}
        source_metrics: dict[str, dict[str, Any]] = {}
        for issue, metrics in issues_with_sources:
            existing = merged.get(issue.issue_type)
            if existing is None or issue.violation > existing.violation:
                merged[issue.issue_type] = issue
                source_metrics[issue.issue_type] = metrics
        return list(merged.values()), source_metrics

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

    def _prepare_target_module(
        self, inp: RnaAptamerDesignInput
    ) -> tuple[Optional[str], Optional[str], Optional[int]]:
        """Module 1: Resolve protein structure and identify binding hotspots.

        Returns:
            (protein_path, hotspot_residues, protein_seq_len) or (None, None, None) on failure.
        """
        # ── 1. Resolve protein structure ──
        protein_path = self._resolve_protein_structure(inp)
        if not protein_path:
            _LOGGER.error("No valid protein structure available")
            return None, None, None

        # Use cached protein length across BMC rounds when target is unchanged
        protein_seq_len = self._workflow_state.get("_cached_protein_seq_len")
        if protein_seq_len is None:
            protein_seq_len = self._resolve_protein_length(
                protein_path, inp.protein_sequence, chain_id=inp.chain_id
            )
            if protein_seq_len is not None and protein_seq_len > 0:
                self._workflow_state["_cached_protein_seq_len"] = protein_seq_len
        if protein_seq_len is None or protein_seq_len <= 0:
            _LOGGER.error("Cannot determine protein sequence length")
            return None, None, None

        # ── 2. Hotspot identification ──
        hotspot = inp.hotspot_residues
        # Normalize numeric-only hotspots to chain/num format expected by ODesign
        if hotspot and "/" not in hotspot:
            hotspot = ",".join(
                f"{inp.chain_id}/{part.strip()}" for part in hotspot.split(",")
            )
            _LOGGER.info("hotspot_normalized format=%s", hotspot)
        if not hotspot:
            hotspot = self._workflow_state.get("_cached_hotspot")
            if not hotspot:
                _LOGGER.info("hotspot_not_provided running_auto_identification")
                hotspot = self._auto_identify_hotspots(protein_path, inp.chain_id)
                if hotspot:
                    self._workflow_state["_cached_hotspot"] = hotspot
            if not hotspot:
                _LOGGER.error("hotspot_identification_failed")
                return None, None, None
            _LOGGER.info("hotspot_auto_identified residues=%s", hotspot)

        return protein_path, hotspot, protein_seq_len

    def _generate_aptamer_module(
        self,
        protein_path: str,
        hotspot: str,
        inp: RnaAptamerDesignInput,
        *,
        protein_seq_len: Optional[int] = None,
        length_override: Optional[int] = None,
        seeds_override: Optional[list[int]] = None,
        samples_override: Optional[int] = None,
    ) -> list[Candidate]:
        """Module 2: Generate aptamer candidates via ODesign structure-guided generation.

        Supports parameter overrides for BMC regeneration.
        """
        # Resolve protein length if not provided (use cache across BMC rounds)
        if protein_seq_len is None:
            protein_seq_len = self._workflow_state.get("_cached_protein_seq_len")
        if protein_seq_len is None:
            protein_seq_len = self._resolve_protein_length(
                protein_path, inp.protein_sequence, chain_id=inp.chain_id
            )
            if protein_seq_len is not None and protein_seq_len > 0:
                self._workflow_state["_cached_protein_seq_len"] = protein_seq_len
        if protein_seq_len is None or protein_seq_len <= 0:
            _LOGGER.error("Cannot determine protein sequence length")
            return []

        # Apply parameter overrides
        aptamer_length = length_override if length_override is not None else inp.aptamer_length
        seeds = seeds_override if seeds_override is not None else inp.odesign_seeds
        n_sample = samples_override if samples_override is not None else inp.n_odesign_samples

        # ── Build ODesign input JSON ──
        json_result = self._build_odesign_json(
            protein_path=protein_path,
            chain_id=inp.chain_id,
            seq_len=protein_seq_len,
            hotspot=hotspot,
            aptamer_length=aptamer_length,
        )
        if not json_result:
            _LOGGER.error("odesign_json_build_failed")
            return []
        json_path = json_result.get("input_json_filepath", "")
        _LOGGER.info("odesign_json_built path=%s", json_path)

        # ── Run ODesign inference ──
        odesign_result = self._run_odesign_inference(
            json_path=json_path,
            n_sample=n_sample,
            seeds=seeds,
        )
        if not odesign_result:
            _LOGGER.error("odesign_inference_failed")
            return []

        prediction_paths = odesign_result.get("prediction_filepaths", [])
        _LOGGER.info("odesign_predictions count=%d", len(prediction_paths))

        # ── Extract RNA sequences from prediction files ──
        sequences = self._extract_sequences_from_predictions(prediction_paths)
        if not sequences:
            # CAVEAT (2026-07-27): zero sequences is a TARGET-SIDE boundary on
            # some proteins, not a transient failure. In the Fig-4 matrix
            # Ferritin (1FHA) produced zero ODesign sequences in all 12 cells
            # and across 3 resume retries — the protein offers no RNA-binding
            # surface ODesign can design against. Do not "fix" this by
            # retrying; record it as a limitation (see RESUME_CHECKPOINT §4).
            _LOGGER.error("no_sequences_extracted_from_odesign_output")
            return []

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for idx, seq in enumerate(sequences):
            if not seq or seq in seen:
                continue
            seen.add(seq)
            candidates.append(
                Candidate(
                    sequence=seq,
                    sequence_type="rna_aptamer",
                    source=f"odesign_aptamer:s{seeds[0]}:i{idx}",
                    metadata={
                        "protein_structure_path": protein_path,
                        "protein_chain_id": inp.chain_id,
                        "hotspot_residues": hotspot,
                        "aptamer_length": aptamer_length,
                        "odesign_prediction_path": prediction_paths[idx] if idx < len(prediction_paths) else None,
                        "odesign_input_json": json_path,
                        "design_params": {
                            "n_sample": n_sample,
                            "seeds": seeds,
                        },
                    },
                )
            )

        _LOGGER.info("candidates_generated total=%d unique=%d", len(sequences), len(candidates))
        return candidates

    def generate_candidates(self, inp: RnaAptamerDesignInput) -> list[Candidate]:
        """Generate aptamer candidates via ODesign structure-guided generation.

        Public API kept unchanged; delegates to BMC module helpers.
        """
        protein_path, hotspot, protein_seq_len = self._prepare_target_module(inp)
        if not protein_path or not hotspot:
            return []
        return self._generate_aptamer_module(
            protein_path, hotspot, inp, protein_seq_len=protein_seq_len
        )

    def _regenerate_modules(
        self,
        inp: RnaAptamerDesignInput,
        feedback: dict[str, ModuleFeedback],
        protein_path: str,
        hotspot: str,
        protein_seq_len: Optional[int],
        best: Candidate,
        issues: list[Issue],
        issue_source_metrics: dict[str, dict[str, Any]],
    ) -> list[Candidate]:
        """Regenerate candidates based on AptamerCoordinator feedback.

        Maps feedback adjustments to concrete parameter changes and invokes
        the appropriate module regeneration methods.

        Args:
            issues: Diagnosed issues for this round.
            issue_source_metrics: Mapping from issue_type to the metrics bundle
                of the candidate that contributed the worst instance.
        """
        new_candidates: list[Candidate] = []

        # ── Target module regeneration (hotspot expansion) ──
        if "Target" in feedback:
            target_fb = feedback["Target"]
            current_window = 3
            for adj in target_fb.adjustments:
                if adj.param == "hotspot_expansion":
                    current_window += int(adj.delta)
            current_window = max(3, min(current_window, 10))  # clamp [3, 10]

            expanded_hotspot = self._expand_hotspot_residues(
                protein_path, inp.chain_id, hotspot, window=current_window
            )
            if expanded_hotspot and expanded_hotspot != hotspot:
                _LOGGER.info(
                    "bmc_regenerating_target expanded_window=%d old=%s new=%s",
                    current_window,
                    hotspot,
                    expanded_hotspot,
                )
                new_candidates = self._generate_aptamer_module(
                    protein_path,
                    expanded_hotspot,
                    inp,
                    protein_seq_len=protein_seq_len,
                )
                # Tag new candidates with regeneration info
                for c in new_candidates:
                    c.metadata["bmc_round"] = len(self._bmc_trace) + 1
                    c.metadata["bmc_module"] = "Target"
                    c.metadata["hotspot_before"] = hotspot
                    c.metadata["hotspot_after"] = expanded_hotspot
            else:
                _LOGGER.info("bmc_hotspot_expansion_no_change fallback_to_aptamer")

        # ── Aptamer module regeneration (length / seeds / samples) ──
        if "Aptamer" in feedback and not new_candidates:
            aptamer_fb = feedback["Aptamer"]
            length_override = None
            seeds_override = None
            samples_override = None

            for adj in aptamer_fb.adjustments:
                if adj.param == "aptamer_length_delta":
                    length_override = min(200, inp.aptamer_length + int(adj.delta))
                elif adj.param == "seed_change":
                    # Shift all seeds by +1 to explore new sequence space
                    seeds_override = [s + 1 for s in inp.odesign_seeds]
                elif adj.param == "n_samples_delta":
                    samples_override = min(20, inp.n_odesign_samples + int(adj.delta))

            _LOGGER.info(
                "bmc_regenerating_aptamer length=%s seeds=%s samples=%s",
                length_override,
                seeds_override,
                samples_override,
            )
            new_candidates = self._generate_aptamer_module(
                protein_path,
                hotspot,
                inp,
                protein_seq_len=protein_seq_len,
                length_override=length_override,
                seeds_override=seeds_override,
                samples_override=samples_override,
            )
            for c in new_candidates:
                c.metadata["bmc_round"] = len(self._bmc_trace) + 1
                c.metadata["bmc_module"] = "Aptamer"
                c.metadata["length_override"] = length_override
                c.metadata["seeds_override"] = seeds_override
                c.metadata["samples_override"] = samples_override

        return new_candidates

    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Evaluate an aptamer candidate.

        Metrics collected:
          - gc_content (for critic quality gating)
          - rhofold_mean_plddt (RNA monomer foldability)
          - egarps_native_probability (ODesign complex quality)
          - proteinx_ipTM (AlphaFold-family complex confidence)
          - interface_contacts, buried_sasa, hydrogen_bonds, salt_bridges
        """
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="aptamer")
        candidate.metadata["workspace_filepath"] = filepath

        metrics: dict[str, Any] = {
            "sequence_length": len(seq),
        }

        # ── GC content (retained for critic quality gating) ──
        gc_content = self._run_capability_float(
            "compute_rna_sequence_gc_content",
            {"filepath": filepath},
            "gc_content",
            candidate=candidate,
            step_name="compute_rna_sequence_gc_content",
        )
        metrics["gc_content"] = gc_content

        # ── RhoFold tertiary structure ──
        rhofold_plddt: Optional[float] = None
        rhofold_pdb: Optional[str] = None
        if self.capabilities.has("predict_rna_tertiary_structure_with_rhofold"):
            rh_res = self._invoke_and_record(
                "predict_rna_tertiary_structure_with_rhofold",
                {"filepath": filepath},
                candidate=candidate,
                step_name="predict_rna_tertiary_structure_with_rhofold",
            )
            if rh_res.success:
                rhofold_plddt = _pick_float(rh_res.output, "mean_plddt")
                rhofold_pdb = rh_res.output.get("pdb_filepath", "")
            else:
                _LOGGER.warning("aptamer_rhofold_failed error=%s", rh_res.error)
        metrics["rhofold_mean_plddt"] = rhofold_plddt
        metrics["rhofold_pdb_path"] = rhofold_pdb
        candidate.metadata["rhofold_pdb_path"] = rhofold_pdb

        # ── EGARPS complex scoring (best-effort, gated by fast metrics) ──
        egarps_prob: Optional[float] = None
        odesign_pred_path = candidate.metadata.get("odesign_prediction_path")
        gc_content = metrics.get("gc_content")
        should_run_egarps = True
        if gc_content is not None and (gc_content < 0.25 or gc_content > 0.85):
            _LOGGER.debug(
                "egarps_skipped_extreme_gc gc=%.3f candidate=%s", gc_content, candidate.id
            )
            should_run_egarps = False
        if rhofold_plddt is not None and rhofold_plddt < 65.0:
            _LOGGER.debug(
                "egarps_skipped_low_rhofold plddt=%.2f candidate=%s", rhofold_plddt, candidate.id
            )
            should_run_egarps = False

        if should_run_egarps and odesign_pred_path and self.capabilities.has("score_rna_protein_complex_with_egarps"):
            pred_path_obj = Path(odesign_pred_path)
            suffix = pred_path_obj.suffix.lower()
            if suffix == ".pdb":
                egarps_prob = self._run_egarps(str(pred_path_obj.resolve()), candidate=candidate)
            elif suffix in {".cif", ".mmcif"}:
                egarps_prob = self._try_egarps_from_cif(str(pred_path_obj.resolve()), candidate=candidate)
            else:
                _LOGGER.debug("egarps_skipped_unknown_suffix suffix=%s", suffix)
        else:
            _LOGGER.debug("egarps_skipped_no_odesign_structure")
        metrics["egarps_native_probability"] = egarps_prob

        # ── ProteinX RNA-protein complex prediction (required) ──
        iptm: Optional[float] = None
        proteinx_plddt: Optional[float] = None
        proteinx_pdb: Optional[str] = None
        protein_seq = self._resolve_protein_sequence_for_candidate(candidate)
        if protein_seq and self.capabilities.has("predict_rna_protein_complex_with_proteinx"):
            # Save protein and RNA sequences as FASTA files
            protein_fasta = save_sequence(f">protein\n{protein_seq}\n", prefix="protein_for_complex")
            rna_fasta = save_sequence(f">rna\n{seq}\n", prefix="rna_for_complex")
            px_res = self._invoke_and_record(
                "predict_rna_protein_complex_with_proteinx",
                {
                    "protein_filepath": protein_fasta,
                    "rna_filepath": rna_fasta,
                    "num_models": 1,
                },
                candidate=candidate,
                step_name="predict_rna_protein_complex_with_proteinx",
            )
            if px_res.success:
                iptm = _pick_float(px_res.output, "ipTM")
                proteinx_plddt = _pick_float(px_res.output, "mean_plddt")
                proteinx_pdb = px_res.output.get("pdb_filepath", "")
            else:
                raise RuntimeError(
                    f"ProteinX complex prediction failed: {px_res.error}"
                )
        metrics["proteinx_ipTM"] = iptm
        metrics["proteinx_mean_plddt"] = proteinx_plddt
        metrics["proteinx_pdb_path"] = proteinx_pdb

        # ── Interface analysis on ODesign complex structure (best-effort) ──
        interface_contacts: Optional[int] = None
        buried_sasa: Optional[float] = None
        hydrogen_bonds: Optional[int] = None
        salt_bridges: Optional[int] = None
        if odesign_pred_path and self.capabilities.has("analyze_rna_protein_interface"):
            try:
                # Try to determine chain IDs from the structure; fallback to defaults
                protein_chain = candidate.metadata.get("protein_chain_id", "A")
                rna_chain = "B"  # ODesign typically outputs RNA as chain B

                # ODesign outputs CIF files that lack _atom_site.B_iso_or_equiv,
                # which Bio.PDB.MMCIFParser requires. Convert to PDB on-the-fly.
                iface_input_path = self._ensure_pdb_for_interface_analysis(
                    odesign_pred_path
                )
                if not iface_input_path:
                    _LOGGER.debug("interface_analysis_skipped_cif_conversion_failed")
                else:
                    # ODesign renames chains to A (protein) and B (RNA) regardless
                    # of the original PDB chain IDs. Detect actual chains in the
                    # converted structure to avoid "0 atoms" failures.
                    detected_protein_chain, detected_rna_chain = (
                        self._detect_chains_in_pdb(iface_input_path, protein_chain, rna_chain)
                    )
                    iface_res = self._invoke_and_record(
                        "analyze_rna_protein_interface",
                        {
                            "complex_pdb_filepath": iface_input_path,
                            "protein_chain_id": detected_protein_chain,
                            "rna_chain_id": detected_rna_chain,
                            "contact_cutoff": 5.0,
                        },
                        candidate=candidate,
                        step_name="analyze_rna_protein_interface",
                    )
                    if iface_res.success:
                        interface_contacts = iface_res.output.get("interface_contacts")
                        buried_sasa = _pick_float(iface_res.output, "buried_sasa")
                        hydrogen_bonds = iface_res.output.get("hydrogen_bonds")
                        salt_bridges = iface_res.output.get("salt_bridges")
                    else:
                        _LOGGER.warning("interface_analysis_failed error=%s", iface_res.error)
            except Exception as exc:
                _LOGGER.warning("interface_analysis_exception exc=%s", exc)
        metrics["interface_contacts"] = interface_contacts
        metrics["buried_sasa"] = buried_sasa
        metrics["hydrogen_bonds"] = hydrogen_bonds
        metrics["salt_bridges"] = salt_bridges

        candidate.metadata["metrics_bundle"] = metrics
        return metrics

    def _evaluate_light(self, candidate: Candidate) -> dict[str, Any]:
        """Lightweight evaluation: GC content + RhoFold pLDDT only.

        Used for coarse pre-filtering before invoking expensive tools
        (EGARPS, ProteinX, interface analysis).
        """
        seq = candidate.sequence
        filepath = save_sequence(seq, prefix="aptamer")
        candidate.metadata["workspace_filepath"] = filepath

        metrics: dict[str, Any] = {"sequence_length": len(seq)}

        gc_content = self._run_capability_float(
            "compute_rna_sequence_gc_content",
            {"filepath": filepath},
            "gc_content",
            candidate=candidate,
            step_name="compute_rna_sequence_gc_content",
        )
        metrics["gc_content"] = gc_content

        rhofold_plddt: Optional[float] = None
        rhofold_pdb: Optional[str] = None
        if self.capabilities.has("predict_rna_tertiary_structure_with_rhofold"):
            rh_res = self._invoke_and_record(
                "predict_rna_tertiary_structure_with_rhofold",
                {"filepath": filepath},
                candidate=candidate,
                step_name="predict_rna_tertiary_structure_with_rhofold",
            )
            if rh_res.success:
                rhofold_plddt = _pick_float(rh_res.output, "mean_plddt")
                rhofold_pdb = rh_res.output.get("pdb_filepath", "")
            else:
                _LOGGER.warning("aptamer_rhofold_failed error=%s", rh_res.error)
        metrics["rhofold_mean_plddt"] = rhofold_plddt
        metrics["rhofold_pdb_path"] = rhofold_pdb
        candidate.metadata["rhofold_pdb_path"] = rhofold_pdb

        return metrics

    def _coarse_score(self, metrics: dict[str, Any]) -> float:
        """Coarse score for hierarchical filtering before expensive tools.

        Uses RhoFold pLDDT as the primary fast filter; foldability is the
        strongest predictor of whether full complex evaluation is worthwhile.
        """
        plddt = metrics.get("rhofold_mean_plddt")
        if plddt is not None:
            return float(plddt)
        return 0.0

    def _evaluate_candidates_concurrent(
        self,
        candidates: list[Candidate],
        *,
        progress_callback: Optional[Any] = None,
        progress_event: str = "evaluate_progress",
        progress_extra: Optional[dict[str, Any]] = None,
        top_k_base: int = 5,
    ) -> list[Candidate]:
        """Two-stage concurrent evaluation: light on all, heavy on top-k.

        Returns the subset of candidates that received full evaluation.
        Non-selected candidates are retained in *candidate.status*
        ``filtered_out`` with their light metrics for audit transparency.
        """
        if not candidates:
            return []

        total = len(candidates)
        top_k = max(top_k_base, int(total * 0.5))
        top_k = min(top_k, total)

        _LOGGER.info(
            "hierarchical_filter_start total=%d top_k=%d event=%s",
            total,
            top_k,
            progress_event,
        )

        # Stage 1: light evaluation (GC + RhoFold) for all candidates in parallel
        light_results: list[tuple[Candidate, dict[str, Any], float]] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_candidate = {
                executor.submit(self._evaluate_light, c): c for c in candidates
            }
            completed = 0
            for future in as_completed(future_to_candidate):
                candidate = future_to_candidate[future]
                completed += 1
                try:
                    metrics = future.result()
                except Exception as exc:
                    _LOGGER.warning(
                        "light_eval_failed candidate=%s exc=%s", candidate.id, exc
                    )
                    metrics = {"sequence_length": len(candidate.sequence)}
                coarse = self._coarse_score(metrics)
                light_results.append((candidate, metrics, coarse))
                if progress_callback:
                    payload = {
                        "event": progress_event,
                        "current": completed,
                        "total": total,
                        "candidate_id": candidate.id,
                        "workflow": self.name,
                        "stage": "light",
                    }
                    if progress_extra:
                        payload.update(progress_extra)
                    progress_callback(payload)

        # Select top-k by coarse score
        light_results.sort(key=lambda x: x[2], reverse=True)
        selected = light_results[:top_k]
        selected_ids = {c.id for c, _, _ in selected}

        # Retain light metrics for non-selected candidates
        for candidate, metrics, coarse in light_results:
            if candidate.id not in selected_ids:
                candidate.status = "filtered_out"
                candidate.metadata["metrics_bundle"] = metrics
                candidate.scores = self.score(metrics)

        _LOGGER.info(
            "hierarchical_filter_selected top_k=%d total=%d",
            len(selected),
            total,
        )

        # Stage 2: full evaluation on top-k in parallel
        evaluated: list[Candidate] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_item = {
                executor.submit(self.evaluate, c): (c, m) for c, m, _ in selected
            }
            completed = 0
            for future in as_completed(future_to_item):
                candidate, light_metrics = future_to_item[future]
                completed += 1
                try:
                    full_metrics = future.result()
                except Exception as exc:
                    _LOGGER.warning(
                        "full_eval_failed candidate=%s exc=%s", candidate.id, exc
                    )
                    full_metrics = dict(light_metrics)
                candidate.metadata["metrics_bundle"] = full_metrics
                candidate.scores = self.score(full_metrics)
                candidate.status = "evaluated"
                evaluated.append(candidate)
                if progress_callback:
                    payload = {
                        "event": progress_event,
                        "current": completed,
                        "total": len(selected),
                        "candidate_id": candidate.id,
                        "workflow": self.name,
                        "stage": "full",
                    }
                    if progress_extra:
                        payload.update(progress_extra)
                    progress_callback(payload)

        return evaluated

    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Return per-objective raw scores for ASF-based reference-point ranking."""
        return score_aptamer_candidate(metrics)

    def _apply_reference_point_and_pareto(
        self,
        candidates: list[Candidate],
        inp: RnaAptamerDesignInput,
    ) -> tuple[Candidate | None, list[Candidate], dict[str, float] | None, dict[str, float]]:
        """Reference-point optimization + Pareto frontier (default behaviour).

        The best candidate is always selected via the Achievement Scalarizing
        Function (ASF).  If the user does not supply a ``reference_point``, a
        utopian point is derived from the candidate pool.  The Pareto-optimal
        frontier is always computed and returned.

        Returns ``(best_candidate, pareto_frontier, raw_reference_point, candidate_asf_map)``.
        """
        objectives = ["egarps_component", "rhofold_component", "iptm_component"]
        maximize = {key: True for key in objectives}

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

        normalized_dim_values: dict[str, list[float]] = {}
        for key, values in dim_values.items():
            normalized_dim_values[key] = normalize_to_unit_range(values)

        normalized_vectors: list[tuple[Candidate, dict[str, float]]] = []
        dim_index: dict[str, int] = {key: 0 for key in objectives}
        for candidate, vec in candidate_vectors:
            norm_vec: dict[str, float] = {}
            for key, value in vec.items():
                norm_vec[key] = normalized_dim_values[key][dim_index[key]]
                dim_index[key] += 1
            normalized_vectors.append((candidate, norm_vec))

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
            return self._empty_result("No aptamer candidates produced.")

        inp = self._workflow_state.get("_aptamer_input")
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
                f"len={len(c.sequence)}nt",
                f"GC={mb.get('gc_content'):.3f}" if mb.get("gc_content") is not None else "GC=N/A",
                f"RhoFold={mb.get('rhofold_mean_plddt'):.2f}"
                if mb.get("rhofold_mean_plddt") is not None
                else "RhoFold=N/A",
                f"EGARPS={mb.get('egarps_native_probability'):.4f}"
                if mb.get("egarps_native_probability") is not None
                else "EGARPS=N/A",
                f"ipTM={mb.get('proteinx_ipTM'):.4f}"
                if mb.get("proteinx_ipTM") is not None
                else "ipTM=N/A",
                f"contacts={mb.get('interface_contacts')}"
                if mb.get("interface_contacts") is not None
                else "contacts=N/A",
                f"bSASA={mb.get('buried_sasa'):.1f}"
                if mb.get("buried_sasa") is not None
                else "bSASA=N/A",
                f"HB={mb.get('hydrogen_bonds')}"
                if mb.get("hydrogen_bonds") is not None
                else "HB=N/A",
                f"SB={mb.get('salt_bridges')}"
                if mb.get("salt_bridges") is not None
                else "SB=N/A",
                f"asf={scores.get('asf_distance'):.4f}"
                if scores.get("asf_distance") is not None
                else "asf=N/A",
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
            task_id=f"aptamer_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            best_candidate=best,
            all_candidates=ranked,
            summary="\n".join(summary_parts),
            errors=[],
            **extras,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _resolve_protein_structure(self, inp: RnaAptamerDesignInput) -> Optional[str]:
        """Return a valid protein structure path, or None."""
        structure_path = inp.protein_structure_path
        # Defensive: ignore placeholder paths the LLM may have invented.
        if structure_path and ("$" in str(structure_path) or "<" in str(structure_path)):
            _LOGGER.warning("ignoring_placeholder_protein_structure_path path=%s", structure_path)
            structure_path = None
        if structure_path:
            path = resolve_project_path(structure_path)
            if Path(path).exists():
                return path
            _LOGGER.warning("protein_structure_path_not_found path=%s", path)
        # If only sequence is provided, predict structure with ProteinX
        if inp.protein_sequence and not structure_path:
            _LOGGER.info("protein_sequence_only predicting_structure_with_proteinx")
            if not self.capabilities.has("predict_protein_structure_with_proteinx"):
                _LOGGER.warning("capability_missing predict_protein_structure_with_proteinx")
                return None
            # Save sequence as FASTA
            fasta_content = f">protein\n{inp.protein_sequence}\n"
            fasta_path = save_sequence(fasta_content, prefix="protein")
            abs_fasta = resolve_project_path(fasta_path)
            try:
                cap_result = self._invoke_and_record(
                    "predict_protein_structure_with_proteinx",
                    {
                        "filepath": abs_fasta,
                        "num_models": 1,
                        "msa_mode": "none",
                    },
                    step_name="predict_protein_structure_with_proteinx",
                )
                pdb_path = cap_result.output.get("pdb_filepath", "") if cap_result.success else ""
                if pdb_path and Path(pdb_path).exists():
                    _LOGGER.info("protein_structure_predicted path=%s", pdb_path)
                    return pdb_path
                _LOGGER.error("proteinx_returned_invalid_path path=%s", pdb_path)
            except Exception as exc:
                _LOGGER.error("proteinx_prediction_failed exc=%s", exc)
            return None
        return None

    def _resolve_protein_length(
        self,
        protein_path: str,
        explicit_sequence: Optional[str],
        *,
        chain_id: Optional[str] = None,
    ) -> Optional[int]:
        """Determine protein sequence length from structure or explicit input."""
        if explicit_sequence:
            return len(explicit_sequence)
        # Fallback: parse from PDB/CIF using biopython
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.warning("biopython_not_installed cannot_parse_structure_length")
            return None
        path_obj = Path(protein_path)
        suffix = path_obj.suffix.lower()
        try:
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
            # Count residues in the requested chain, or the first chain if none specified
            target_chain = (chain_id or "").strip()
            for model in structure:
                for chain in model:
                    if target_chain and chain.id.strip() != target_chain:
                        continue
                    count = sum(
                        1 for r in chain if not r.id[0].strip()
                    )
                    if count > 0:
                        return count
            # If a specific chain was requested but not found, fall back to the first chain
            if target_chain:
                for model in structure:
                    for chain in model:
                        count = sum(
                            1 for r in chain if not r.id[0].strip()
                        )
                        if count > 0:
                            _LOGGER.warning(
                                "chain_id_not_found_in_structure falling_back_to_first_chain "
                                "requested=%s found=%s count=%d",
                                target_chain,
                                chain.id.strip(),
                                count,
                            )
                            return count
        except Exception as exc:
            _LOGGER.warning("structure_parse_failed_for_length err=%s", exc)
        return None

    def _auto_identify_hotspots(self, protein_path: str, chain_id: str) -> Optional[str]:
        """Run the hotspot identification capability."""
        cap_result = self._invoke_and_record(
            "identify_protein_binding_hotspots",
            {"protein_structure_path": protein_path, "chain_id": chain_id},
            step_name="identify_protein_binding_hotspots",
        )
        if not cap_result.success:
            _LOGGER.warning("hotspot_identification_failed error=%s", cap_result.error)
            return None
        hotspot = cap_result.output.get("hotspot_residues", "")
        if not hotspot:
            _LOGGER.warning("hotspot_identification_returned_empty")
        return hotspot if hotspot else None

    def _build_odesign_json(
        self,
        protein_path: str,
        chain_id: str,
        seq_len: int,
        hotspot: str,
        aptamer_length: int,
    ) -> Optional[dict[str, Any]]:
        """Build ODesign aptamer input JSON."""
        cap_result = self._invoke_and_record(
            "build_odesign_aptamer_input_json",
            {
                "protein_structure_path": protein_path,
                "protein_chain_id": chain_id,
                "protein_sequence_length": seq_len,
                "hotspot_residues": hotspot,
                "aptamer_length": aptamer_length,
            },
            step_name="build_odesign_aptamer_input_json",
        )
        if not cap_result.success:
            _LOGGER.warning("odesign_json_build_failed error=%s", cap_result.error)
            return None
        return dict(cap_result.output)

    def _run_odesign_inference(
        self,
        json_path: str,
        n_sample: int,
        seeds: list[int],
    ) -> Optional[dict[str, Any]]:
        """Run ODesign inference and return the result dict.

        NOTE (2026-07 experiment incident): ODesign featurization hard-crashes with
        ``AssertionError`` in ``add_distogram_rep_atom_mask`` when the input PDB has
        any non-glycine residue with CA but no CB (incomplete side chain, e.g.
        3v03/BSA LYS-316, ALA-367), because the assert requires one representative
        atom per token. Symptom at this level: ``candidate_generation_failed`` with
        ``no_sequences_extracted_from_odesign_output`` (the service HTTP call itself
        returns 200). Structures must be CB-complete before inference — repair with
        ``experiments/repair_structure_cb.py`` (originals under
        ``data/benchmarks/RNA-BioBench-Aptamer/structures/originals/``).
        """
        cap_result = self._invoke_and_record(
            "run_odesign_inference",
            {
                "input_json_filepath": json_path,
                "design_modality": "rna",
                "seeds_json": json.dumps(seeds),
                "n_sample": n_sample,
                "infer_model_name": "odesign_base_na_rigid",
            },
            step_name="run_odesign_inference",
        )
        if not cap_result.success:
            _LOGGER.warning("odesign_inference_failed error=%s", cap_result.error)
            return None
        return dict(cap_result.output)

    def _extract_sequences_from_predictions(self, prediction_paths: list[str]) -> list[str]:
        """Extract RNA sequences from ODesign prediction file paths.

        ODesign outputs can be CIF, PDB, or FASTA depending on version/config.
        We attempt extraction in order of reliability.
        """
        sequences: list[str] = []
        for path in prediction_paths:
            if not path:
                continue
            abs_path = resolve_project_path(path)
            suffix = Path(abs_path).suffix.lower()
            seq: Optional[str] = None

            if suffix in {".cif", ".mmcif"}:
                seq = self._extract_rna_from_cif(abs_path)
            elif suffix == ".pdb":
                seq = self._extract_rna_from_pdb(abs_path)
            elif suffix in {".fasta", ".fa", ".seq", ".txt"}:
                try:
                    content = read_sequence(abs_path)
                    # Strip FASTA header if present
                    lines = [ln.strip() for ln in content.splitlines() if not ln.startswith(">")]
                    candidate_seq = "".join(lines).upper().replace("T", "U")
                    # Keep only AUGC
                    candidate_seq = "".join(ch for ch in candidate_seq if ch in "AUGC")
                    if candidate_seq:
                        seq = candidate_seq
                except Exception as exc:
                    _LOGGER.debug("fasta_read_failed path=%s err=%s", path, exc)
            else:
                _LOGGER.debug("unknown_prediction_suffix suffix=%s path=%s", suffix, path)

            if seq:
                sequences.append(seq)
            else:
                _LOGGER.warning("sequence_extraction_failed path=%s", path)

        return sequences

    def _extract_rna_from_cif(self, cif_path: str) -> Optional[str]:
        """Delegate to the extract_rna_sequence_from_cif capability."""
        cap_result = self._invoke_and_record(
            "extract_rna_sequence_from_cif",
            {"cif_filepath": cif_path},
            step_name="extract_rna_sequence_from_cif",
        )
        if cap_result.success:
            return cap_result.output.get("sequence", "")
        _LOGGER.debug("cif_extraction_failed error=%s", cap_result.error)
        return None

    def _extract_rna_from_pdb(self, pdb_path: str) -> Optional[str]:
        """Extract RNA sequence from a PDB file using biopython.

        Detects RNA by checking for the O2' atom (same heuristic as CIF extractor).
        """
        try:
            from Bio.PDB import PDBParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_extract_from_pdb")
            return None
        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("rna", pdb_path)
            for model in structure:
                for chain in model:
                    is_rna = False
                    for residue in chain:
                        if residue.id[0].strip():
                            continue
                        atom_names = {atom.name for atom in residue}
                        if "O2'" in atom_names:
                            is_rna = True
                            break
                    if is_rna:
                        base_map = {
                            "A": "A", "U": "U", "G": "G", "C": "C",
                            "DA": "A", "DT": "T", "DG": "G", "DC": "C",
                        }
                        parts = []
                        for residue in chain:
                            if residue.id[0].strip():
                                continue
                            resname = residue.resname.strip()
                            base = base_map.get(resname)
                            if base is None:
                                if len(resname) == 1 and resname in "AUGC":
                                    base = resname
                                else:
                                    base = "N"
                            parts.append(base)
                        return "".join(parts)
            _LOGGER.debug("no_rna_chain_found_in_pdb path=%s", pdb_path)
        except Exception as exc:
            _LOGGER.debug("pdb_extraction_failed path=%s err=%s", pdb_path, exc)
        return None

    def _run_egarps(
        self,
        complex_pdb_path: str,
        *,
        candidate: Optional[Candidate] = None,
    ) -> Optional[float]:
        """Run EGARPS on an RNA-protein complex PDB."""
        cap_result = self._invoke_and_record(
            "score_rna_protein_complex_with_egarps",
            {"filepath": complex_pdb_path, "academic": False},
            candidate=candidate,
            step_name="score_rna_protein_complex_with_egarps",
        )
        if cap_result.success:
            return _pick_float(cap_result.output, "native_probability")
        _LOGGER.debug("egarps_scoring_failed error=%s", cap_result.error)
        return None

    def _try_egarps_from_cif(
        self,
        cif_path: str,
        *,
        candidate: Optional[Candidate] = None,
    ) -> Optional[float]:
        """Convert CIF to PDB, rebuild RNA bases, and run EGARPS."""
        complete_pdb = self._get_complete_complex_pdb(cif_path)
        if not complete_pdb:
            return None
        return self._run_egarps(complete_pdb, candidate=candidate)

    def _run_capability_float(
        self,
        cap_name: str,
        args: dict[str, Any],
        key: str,
        *,
        candidate: Optional[Candidate] = None,
        step_name: Optional[str] = None,
    ) -> Optional[float]:
        """Invoke a capability and safely extract a float field."""
        cap_result = self._invoke_and_record(
            cap_name,
            args,
            candidate=candidate,
            step_name=step_name or cap_name,
        )
        if cap_result.success:
            return _pick_float(cap_result.output, key)
        _LOGGER.warning("%s_failed error=%s", cap_name, cap_result.error)
        return None

    def _resolve_protein_sequence_for_candidate(
        self, candidate: Candidate
    ) -> Optional[str]:
        """Return the protein amino-acid sequence if available."""
        # 1. Try the workflow input cached in state
        inp = self._workflow_state.get("_aptamer_input")
        if inp and getattr(inp, "protein_sequence", None):
            return str(inp.protein_sequence)
        # 2. Try to parse from the protein structure file
        protein_path = candidate.metadata.get("protein_structure_path")
        if protein_path:
            parsed = self._extract_protein_sequence_from_structure(protein_path)
            if parsed:
                return parsed
        return None

    def _extract_protein_sequence_from_structure(
        self, protein_path: str
    ) -> Optional[str]:
        """Extract protein sequence from a PDB/CIF file using biopython."""
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_extract_protein_sequence")
            return None
        try:
            path_obj = Path(protein_path)
            suffix = path_obj.suffix.lower()
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
            aa_map = {
                "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
                "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
                "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
                "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y",
            }
            seq_parts: list[str] = []
            for model in structure:
                for chain in model:
                    for residue in chain:
                        if residue.id[0].strip():
                            continue
                        resname = residue.resname.strip().upper()
                        if resname in aa_map:
                            seq_parts.append(aa_map[resname])
                    break  # Only first chain
                break  # Only first model
            # CAVEAT (2026-07-27, from the Fig-4 campaign): the protein sequence
            # is always taken from the FIRST chain of the file, regardless of the
            # workflow's chain_id. When that chain is not the protein target —
            # e.g. benchmark structure 1HAO, whose first chain (D) is the DNA
            # aptamer itself — the extracted "protein" is garbage/none, ProteinX
            # complex prediction is skipped downstream, and every designed
            # candidate gets iptm_component = 0. This is silent: scoring still
            # "works". Before changing this, check experiments/
            # run_known_aptamer_validation.py, which deliberately extracts from
            # the target chain instead and documents the comparability caveat.
            return "".join(seq_parts) if seq_parts else None
        except Exception as exc:
            _LOGGER.debug("protein_sequence_extraction_failed err=%s", exc)
            return None

    def _expand_hotspot_residues(
        self, protein_path: str, chain_id: str, hotspot: str, window: int = 3
    ) -> str:
        """Expand hotspot by adding adjacent residue numbers that exist in the structure.

        For each residue in *hotspot* (format "chain/num"), add residues
        within ±*window* positions. Only residue numbers that actually exist
        in the target chain are kept.
        """
        try:
            from Bio.PDB import PDBParser, MMCIFParser
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_expand_hotspot")
            return hotspot

        path_obj = Path(protein_path)
        suffix = path_obj.suffix.lower()
        try:
            if suffix in {".cif", ".mmcif"}:
                parser = MMCIFParser(QUIET=True)
            else:
                parser = PDBParser(QUIET=True)
            structure = parser.get_structure("prot", protein_path)
        except Exception as exc:
            _LOGGER.debug("structure_parse_failed_for_hotspot_expansion err=%s", exc)
            return hotspot

        # Collect existing residue numbers for the target chain
        existing_resnums: set[int] = set()
        for model in structure:
            for ch in model:
                if ch.id == chain_id:
                    for residue in ch:
                        if not residue.id[0].strip():  # skip hetero / water
                            existing_resnums.add(residue.id[1])

        if not existing_resnums:
            return hotspot

        expanded: set[str] = set()
        for part in hotspot.split(","):
            part = part.strip()
            if not part:
                continue
            if "/" in part:
                cid, num_str = part.split("/", 1)
            else:
                cid, num_str = chain_id, part
            try:
                num = int(num_str)
            except ValueError:
                continue
            for offset in range(-window, window + 1):
                new_num = num + offset
                if new_num in existing_resnums:
                    expanded.add(f"{cid}/{new_num}")

        # Sort by residue number for stable output
        sorted_expanded = sorted(
            expanded, key=lambda x: int(x.split("/", 1)[1])
        )
        return ",".join(sorted_expanded) if sorted_expanded else hotspot

    def _get_complete_complex_pdb(self, cif_path: str) -> Optional[str]:
        """Convert ODesign CIF to a complete PDB with rebuilt RNA bases.

        ODesign outputs backbone-only RNA structures (missing base atoms).
        This helper: (1) converts CIF→PDB, (2) rebuilds RNA base atoms by
        superimposing standard base templates onto the backbone.

        Returns the path to the complete PDB, or None on failure.
        """
        # Step 1: CIF → backbone-only PDB
        backbone_pdb = self._convert_odesign_cif_to_pdb(cif_path)
        if not backbone_pdb:
            return None

        # Step 2: Rebuild RNA bases
        complete_pdb = self._rebuild_rna_bases_in_pdb(backbone_pdb)
        if complete_pdb:
            _LOGGER.info(
                "rna_bases_rebuilt input=%s output=%s",
                backbone_pdb,
                complete_pdb,
            )
            return complete_pdb
        return backbone_pdb

    def _convert_odesign_cif_to_pdb(self, cif_path: str) -> Optional[str]:
        """Convert ODesign mmCIF (which lacks B_iso_or_equiv) to PDB."""
        path_obj = Path(cif_path)
        suffix = path_obj.suffix.lower()
        if suffix not in {".cif", ".mmcif"}:
            return str(path_obj.resolve())

        try:
            from Bio.PDB.MMCIF2Dict import MMCIF2Dict
            from Bio.PDB.StructureBuilder import StructureBuilder
            from Bio.PDB import PDBIO
        except ImportError:
            _LOGGER.debug("biopython_not_installed cannot_convert_cif_to_pdb")
            return str(path_obj.resolve())

        try:
            d = MMCIF2Dict(str(path_obj))
            cartn_x = d.get("_atom_site.Cartn_x", [])
            if not cartn_x:
                return str(path_obj.resolve())

            label_atom_id = d.get("_atom_site.label_atom_id", [])
            type_symbol = d.get("_atom_site.type_symbol", [])
            label_comp_id = d.get("_atom_site.label_comp_id", [])
            label_asym_id = d.get("_atom_site.label_asym_id", [])
            auth_seq_id = d.get("_atom_site.auth_seq_id", [])
            auth_comp_id = d.get("_atom_site.auth_comp_id", [])
            auth_asym_id = d.get("_atom_site.auth_asym_id", [])
            cartn_y = d.get("_atom_site.Cartn_y", [])
            cartn_z = d.get("_atom_site.Cartn_z", [])
            occupancy = d.get("_atom_site.occupancy", [])

            builder = StructureBuilder()
            builder.init_structure("odesign")
            builder.init_model("0", 0)
            current_chain: Optional[str] = None
            current_residue: Optional[tuple] = None
            serial = 1

            for i in range(len(cartn_x)):
                chain_id = auth_asym_id[i] if i < len(auth_asym_id) else label_asym_id[i]
                res_name = auth_comp_id[i] if i < len(auth_comp_id) else label_comp_id[i]
                res_seq = auth_seq_id[i] if i < len(auth_seq_id) else "1"
                atom_name = label_atom_id[i] if i < len(label_atom_id) else "X"
                element = type_symbol[i] if i < len(type_symbol) else ""
                x, y, z = float(cartn_x[i]), float(cartn_y[i]), float(cartn_z[i])
                occ = float(occupancy[i]) if i < len(occupancy) else 1.0

                if current_chain != chain_id:
                    builder.init_chain(chain_id)
                    current_chain = chain_id
                    current_residue = None

                res_id = (" ", int(res_seq), " ")
                if current_residue != res_id:
                    builder.init_residue(res_name, *res_id)
                    current_residue = res_id

                coord = np.array([x, y, z])
                builder.init_atom(
                    atom_name, coord, occ, 0.0, " ",
                    atom_name, serial_number=serial, element=element,
                )
                serial += 1

            structure = builder.get_structure()
            io = PDBIO()
            io.set_structure(structure)
            pdb_path = resolve_project_path(
                save_text_file("", prefix="odesign_backbone", suffix=".pdb")
            )
            io.save(pdb_path)
            return pdb_path
        except Exception as exc:
            _LOGGER.debug("cif_to_pdb_conversion_failed path=%s err=%s", cif_path, exc)
            return str(path_obj.resolve())

    def _load_rna_base_templates(self) -> dict[str, Any]:
        """Load standard RNA base templates from EGARPS example PDB.

        Templates are cached per workflow instance.
        """
        if hasattr(self, "_rna_base_templates_cache"):
            return self._rna_base_templates_cache

        templates: dict[str, Any] = {}
        ref_pdb = (
            Path(__file__).resolve().parents[2]
            / "external_repos"
            / "EGARPS"
            / "example"
            / "complex1_rna.pdb"
        )
        try:
            from Bio.PDB import PDBParser
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("ref", str(ref_pdb))
            for model in structure:
                for chain in model:
                    for residue in chain:
                        resname = residue.resname.strip().upper()
                        if resname in ("A", "U", "G", "C") and resname not in templates:
                            templates[resname] = residue
                    if len(templates) == 4:
                        break
                if len(templates) == 4:
                    break
        except Exception as exc:
            _LOGGER.debug("rna_base_template_load_failed err=%s", exc)

        self._rna_base_templates_cache = templates
        return templates

    def _rebuild_rna_bases_in_pdb(self, pdb_path: str) -> Optional[str]:
        """Rebuild missing RNA base atoms in a backbone-only PDB.

        Uses Kabsch alignment on three reference atoms (C1', glycosidic N,
        C2') to superimpose standard base templates onto each RNA residue.
        """
        try:
            from Bio.PDB import PDBParser, PDBIO
            from Bio.PDB.Atom import Atom
        except ImportError:
            return None

        templates = self._load_rna_base_templates()
        if len(templates) != 4:
            _LOGGER.debug("rna_base_templates_not_available")
            return None

        # Backbone atoms that are already present in the ODesign output
        backbone_atoms = {
            "P", "OP1", "OP2", "O5'", "C5'", "C4'", "O4'",
            "C3'", "O3'", "C2'", "O2'", "C1'",
        }

        # Glycosidic bond atom: N9 for purines, N1 for pyrimidines
        glyco_n = {"A": "N9", "G": "N9", "C": "N1", "U": "N1"}

        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("complex", pdb_path)

            for model in structure:
                for chain in model:
                    for residue in chain:
                        resname = residue.resname.strip().upper()
                        if resname not in ("A", "U", "G", "C"):
                            continue

                        template = templates.get(resname)
                        if template is None:
                            continue

                        # Collect reference atoms for Kabsch
                        # Template uses standard names (N9 for purines, N1 for pyrimidines).
                        # ODesign outputs backbone-only structures where the glycosidic
                        # nitrogen is simply named "N".  We therefore map the template
                        # reference atom to the target "N" when the standard name is absent.
                        template_ref = glyco_n[resname]
                        target_ref = template_ref
                        if not any(a.name == target_ref for a in residue):
                            if any(a.name == "N" for a in residue):
                                target_ref = "N"

                        ref_atoms = [("C1'", "C1'"), (template_ref, target_ref), ("C2'", "C2'")]
                        P = []
                        Q = []
                        for t_name, r_name in ref_atoms:
                            t_atom = None
                            r_atom = None
                            for a in template:
                                if a.name == t_name:
                                    t_atom = a.coord.copy()
                                    break
                            for a in residue:
                                if a.name == r_name:
                                    r_atom = a.coord.copy()
                                    break
                            if t_atom is None or r_atom is None:
                                break
                            P.append(t_atom)
                            Q.append(r_atom)

                        if len(P) != 3:
                            _LOGGER.debug(
                                "rna_base_rebuild_missing_ref_atoms residue=%s%s found=%s",
                                resname, residue.id[1], [a.name for a in residue]
                            )
                            continue

                        P = np.array(P)
                        Q = np.array(Q)

                        # Kabsch algorithm
                        P_center = P.mean(axis=0)
                        Q_center = Q.mean(axis=0)
                        P_norm = P - P_center
                        Q_norm = Q - Q_center
                        H = P_norm.T @ Q_norm
                        U, S, Vt = np.linalg.svd(H)
                        R = Vt.T @ U.T
                        if np.linalg.det(R) < 0:
                            Vt[-1, :] *= -1
                            R = Vt.T @ U.T
                        t_vec = Q_center - R @ P_center

                        # Remove the placeholder "N" atom left by ODesign
                        # (it will be replaced by the proper glycosidic N from the template)
                        for a in list(residue.get_atoms()):
                            if a.name == "N":
                                residue.detach_child(a.id)

                        # Add missing base atoms from template
                        for t_atom in template:
                            if t_atom.name in backbone_atoms:
                                continue
                            if t_atom.name in [a.name for a in residue]:
                                continue
                            new_coord = R @ t_atom.coord + t_vec
                            new_atom = Atom(
                                t_atom.name,
                                new_coord,
                                t_atom.bfactor,
                                t_atom.occupancy,
                                t_atom.altloc,
                                t_atom.fullname,
                                serial_number=t_atom.serial_number,
                                element=t_atom.element,
                            )
                            residue.add(new_atom)

            io = PDBIO()
            io.set_structure(structure)
            out_path = resolve_project_path(
                save_text_file("", prefix="odesign_complete", suffix=".pdb")
            )
            io.save(out_path)
            return out_path

        except Exception as exc:
            _LOGGER.debug("rna_base_rebuild_failed path=%s err=%s", pdb_path, exc)
            return None

    def _ensure_pdb_for_interface_analysis(
        self, structure_path: str
    ) -> Optional[str]:
        """Return a PDB filepath suitable for analyze_rna_protein_interface.

        ODesign outputs mmCIF files that omit ``_atom_site.B_iso_or_equiv``
        and contain backbone-only RNA structures.  This helper produces a
        complete PDB with rebuilt RNA bases and caches the result per path.
        """
        path_obj = Path(structure_path)
        suffix = path_obj.suffix.lower()
        if suffix not in {".cif", ".mmcif"}:
            return structure_path

        cache_key = f"_pdb_conversion:{structure_path}"
        cached_path = self._workflow_state.get(cache_key)
        if cached_path and Path(cached_path).exists():
            _LOGGER.debug("pdb_conversion_cache_hit path=%s", structure_path)
            return cached_path

        result_path = self._get_complete_complex_pdb(structure_path)
        if result_path:
            self._workflow_state[cache_key] = result_path
        return result_path

    def _detect_chains_in_pdb(
        self,
        pdb_path: str,
        fallback_protein_chain: str,
        fallback_rna_chain: str,
    ) -> tuple[str, str]:
        """Detect actual chain IDs in a PDB file.

        ODesign always outputs protein as chain A and RNA as chain B,
        regardless of the original input chain IDs.  This helper peeks
        at the first model and returns the most likely protein/RNA
        chain IDs based on residue composition.
        """
        try:
            from Bio.PDB import PDBParser
        except ImportError:
            return fallback_protein_chain, fallback_rna_chain

        try:
            parser = PDBParser(QUIET=True)
            structure = parser.get_structure("complex", pdb_path)
        except Exception:
            return fallback_protein_chain, fallback_rna_chain

        chain_candidates: list[tuple[str, int, int]] = []
        for model in structure:
            for chain in model:
                protein_like = 0
                rna_like = 0
                for residue in chain:
                    if residue.id[0].strip():
                        continue  # skip hetero/water
                    resname = residue.resname.strip().upper()
                    # Standard amino-acid 3-letter codes
                    if resname in {
                        "ALA", "CYS", "ASP", "GLU", "PHE", "GLY", "HIS", "ILE",
                        "LYS", "LEU", "MET", "ASN", "PRO", "GLN", "ARG", "SER",
                        "THR", "VAL", "TRP", "TYR",
                    }:
                        protein_like += 1
                    # Standard RNA nucleotides
                    elif resname in {"A", "U", "G", "C", "DA", "DT", "DG", "DC"}:
                        rna_like += 1
                chain_candidates.append((chain.id, protein_like, rna_like))

        if not chain_candidates:
            return fallback_protein_chain, fallback_rna_chain

        # Sort by protein-like count descending, then by rna-like count ascending
        chain_candidates.sort(key=lambda x: (x[1], -x[2]), reverse=True)
        best_protein = chain_candidates[0][0]

        # For RNA, pick the chain with the most RNA-like residues that isn't the protein chain
        rna_candidates = [c for c in chain_candidates if c[0] != best_protein]
        if rna_candidates:
            rna_candidates.sort(key=lambda x: x[2], reverse=True)
            best_rna = rna_candidates[0][0]
        else:
            best_rna = chain_candidates[-1][0] if len(chain_candidates) > 1 else fallback_rna_chain

        if best_protein != fallback_protein_chain or best_rna != fallback_rna_chain:
            _LOGGER.info(
                "chain_ids_detected_from_structure detected_protein=%s detected_rna=%s "
                "fallback_protein=%s fallback_rna=%s",
                best_protein,
                best_rna,
                fallback_protein_chain,
                fallback_rna_chain,
            )

        return best_protein, best_rna


# Aptamer-specific scoring helpers


def score_aptamer_candidate(metrics: dict[str, Any]) -> dict[str, float]:
    """Standalone scoring function for aptamer candidates (reusable outside the workflow).

    Returns per-objective raw scores for ASF-based reference-point ranking.
    EGARPS native probability, RhoFold pLDDT, and ProteinX ipTM are each
    normalised to [0, 1]. The workflow does not compute a weighted-sum
    total_score; ranking is performed via Achievement Scalarizing Function
    distance to a reference point.
    """
    egarps_prob = metrics.get("egarps_native_probability")
    rhofold_plddt = metrics.get("rhofold_mean_plddt")
    iptm = metrics.get("proteinx_ipTM")

    scores: dict[str, float] = {}

    if egarps_prob is not None:
        scores["egarps_component"] = max(0.0, min(1.0, float(egarps_prob)))
    else:
        scores["egarps_component"] = 0.0

    if rhofold_plddt is not None:
        scores["rhofold_component"] = max(0.0, min(1.0, float(rhofold_plddt) / 100.0))
    else:
        scores["rhofold_component"] = 0.0

    if iptm is not None:
        scores["iptm_component"] = max(0.0, min(1.0, float(iptm)))
    else:
        scores["iptm_component"] = 0.0

    return scores
