"""Repository-grounded ToolSpec registry.

This file is the single source of truth for:
- tool identity / upstream sources
- capability boundaries
- strict IO schemas (via Pydantic models)
- runtime constraints (OS/GPU/weights)

Docs under ``docs/tools/`` should match these specs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from agent_core.tool_interface import ToolDependency, ToolExample, ToolSpec, ToolStatus, ToolTransport
from agent_core import tools as tool_wrappers
from agent_core.constants.species import format_cai_species_aliases


class _OutBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class BlastnSearchOutput(_OutBase):
    """BLAST+ blastn search output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: run_blastn_similarity_search (wrapper return dict)
    - microservices/blast_service/main.py :: BlastnResponse
    - agent_core/state.py :: blast_* fields
    """

    hit_count: int
    hits_preview: str = ""
    preview_truncated: bool = False
    tabular_output_truncated: bool = False
    blastn_command: str = ""
    makeblastdb_command: Optional[str] = None
    stderr: str = ""
    subject_mode: str
    resolved_query_path: str = ""
    resolved_subject: str = ""
    model: str
    query_filepath: str
    tabular_tsv_filepath: str = ""


class Bowtie2AlignOutput(_OutBase):
    """Bowtie2 short-alignment output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: run_bowtie2_short_alignment (wrapper return dict)
    - microservices/bowtie2_service/main.py :: Bowtie2AlignResponse
    """

    hit_count: int
    hits_preview: str = ""
    preview_truncated: bool = False
    tabular_output_truncated: bool = False
    bowtie2_command: str = ""
    bowtie2_build_command: Optional[str] = None
    stderr: str = ""
    subject_mode: str
    resolved_query_path: str = ""
    resolved_subject: str = ""
    model: str
    query_filepath: str
    tabular_sam_filepath: str = ""


class EvitarDesignOutput(_OutBase):
    input_filepath: str
    output_filepath: str
    raw_output_path: str
    mode: str
    predict: str
    result_count: int
    top_results: List[Dict[str, Any]]
    model: str
    command: str
    # Extended fields for full upstream CLI transparency
    strains_path: str = ""
    off_target: bool = False
    p3utr_path: str = ""
    transcriptome_path: str = ""
    weight_path: str = ""
    sumtype: str = ""
    limitnum: int = 0
    repeatnum: int = 0
    pmcuff: int = 0
    umcuff: float = 0.0
    mircuff: float = 0.0
    maxgc: float = 0.0
    mingc: float = 0.0
    middlegc: float = 0.0
    allow_path: str = ""
    ban_path: str = ""


class ViennaFoldOutput(_OutBase):
    input_filepath: str
    structure: str
    mfe_kcal_per_mol: float
    backend: str = ""
    model: str = "ViennaRNA-RNAfold"
    ensemble_free_energy: Optional[float] = None
    centroid_structure: Optional[str] = None
    centroid_distance: Optional[float] = None
    mea_structure: Optional[str] = None
    mea_score: Optional[float] = None
    mea_gamma: Optional[float] = None


class ViennaDuplexOutput(_OutBase):
    input_filepath: str
    sense: str
    antisense: str
    cofold_sequence: str = ""
    structure: str
    mfe_kcal_per_mol: float
    backend: str = ""
    model: str
    ensemble_free_energy: Optional[float] = None
    equilibrium_concentrations: Optional[Dict[str, float]] = None


class ViennaRnaUpOutput(_OutBase):
    input_filepath1: str
    input_filepath2: str
    sequence1: str
    sequence2: str
    interaction_energy: Optional[float] = None
    interaction_structure: Optional[str] = None
    raw_stdout: str = ""
    backend: str = ""
    model: str = "ViennaRNA-RNAup"


class ViennaAsoAccessibilityOutput(_OutBase):
    input_filepath: str
    sequence_length: int
    region_start: int
    region_end: int
    mean_unpaired_prob_single_nt: Optional[float] = None
    joint_unpaired_prob_stretch_ending_at_region_end: Optional[float] = None
    aso_oligo_length_used: int
    plfold_winsize: int
    plfold_span: int
    plfold_unpaired_ulength: int
    backend: str = ""
    model: str


class ViennaPlfoldLocalProfileOutput(_OutBase):
    input_filepath: str
    sequence_length: int
    profile_positions_count: int
    mean_unpaired_prob_1nt: float
    min_unpaired_prob_1nt: float
    max_unpaired_prob_1nt: float
    plfold_winsize: int
    plfold_span: int
    plfold_unpaired_ulength_effective: int
    lunp_profile_tsv_filepath: str
    backend: str = ""
    model: str


class ViennaInverseFoldOutput(_OutBase):
    input_filepath: str
    target_structure: str
    best_sequence: str
    best_sequence_filepath: str
    hamming_distance: Optional[int] = None
    partition_probability: Optional[float] = None
    backend: str = ""
    model: str


class LinearFoldOutput(_OutBase):
    filepath: str
    sequence: str
    structure: str
    mfe: float
    backend: str = ""
    model: str


class LinearFoldEvalOutput(_OutBase):
    sequence_filepath: str = ""
    structure_filepath: str = ""
    sequence: str
    structure: str
    energy: float
    backend: str = ""
    model: str
    verbose_details: Optional[str] = None


class LinearFoldZukerSuboptOutput(_OutBase):
    filepath: str
    sequence: str
    mfe: float
    structures: List[Dict[str, Any]]
    backend: str = ""
    model: str


# codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更

class CodonwSlimOutput(_OutBase):
    """Full output schema for codonw-slim CDS metrics.

    Every scalar metric and optional table exposed by the upstream CodonSeq
    class is represented here so that the agent has a complete, typed contract.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: analyze_cds_codon_metrics_with_codonw_slim (wrapper return dict)
    - microservices/codonw_slim_service/main.py :: CodonwAnalyzeResponse
    - agent_core/state.py :: codonw_* fields
    """

    input_filepath: str
    metrics_json_filepath: str
    cai_score: float
    enc: float
    fop: float
    cbi: float
    hydropathy: float = 0.0
    aromaticity: float = 0.0
    genetic_code: int = 0
    cds_length_nt: int = 0
    cds_length_codons: int = 0
    normalization_note: str = ""
    silent_base_usage: dict[str, Any] = {}
    bases2: dict[str, Any] = {}
    codon_usage: Optional[dict[str, Any]] = None
    rscu: Optional[dict[str, Any]] = None
    dinuc: Optional[dict[str, Any]] = None
    aa_usage: Optional[dict[str, Any]] = None
    raau: Optional[dict[str, Any]] = None
    bases: Optional[dict[str, Any]] = None
    model: str


class CrisotScoreOutput(_OutBase):
    input_filepath: str
    sgrna: str
    target_sequence: str
    crisot_score: float
    model: str


class CrisotSpecOutput(_OutBase):
    input_csv_filepath: str
    scored_csv_filepath: str
    crisot_spec: float
    model: str


class CrisotOffSpecOutput(_OutBase):
    input_filepath: str
    sgrna: str
    target_sequence: str
    genome_path: str
    crisot_spec: float
    off_target_count: int
    scored_csv_filepath: str
    model: str


class CrisotOptimizeOutput(_OutBase):
    input_filepath: str
    target_sequence: str
    genome_path: str
    optimized_available: bool
    best_sgrna: str = ""
    best_mutation: str = ""
    best_delta_spec: float = 0.0
    best_crisot_score: float = 0.0
    best_crisot_spec: float = 0.0
    optimization_csv_filepath: str = ""
    optimized_sgrna_filepath: str = ""
    model: str


class CrisotScoresOutput(_OutBase):
    input_csv_filepath: str
    scored_csv_filepath: str
    row_count: int
    model: str


class CrisotRescoreOutput(_OutBase):
    input_txt_filepath: str
    rescore_csv_filepath: str
    genome_path: str
    sgrna_count: int
    model: str


class CrisotFpOutput(_OutBase):
    input_csv_filepath: str
    fp_csv_filepath: str
    xgb_model: str
    row_count: int
    model: str


class CrisotGenFpOutput(_OutBase):
    sgrna: str
    target_sequence: str
    fp_csv_filepath: str
    model: str


class SgRNADesignOutput(_OutBase):
    seed_sequence: str = ""
    input_filepath: Optional[str] = None
    best_sequence: str = ""
    best_sequence_filepath: str = ""
    generated_count: int = 0
    best_nn_score: float = 0.0
    best_log_likelihood: Optional[float] = None
    best_mutation_count: int = 0
    sampling_mode: str = "mcmc"
    model_path: str = ""
    output_fasta_filepath: str = ""
    output_ali_filepath: Optional[str] = None
    summary_json_filepath: str = ""
    model: str


class SgRNADesignScoreOutput(_OutBase):
    sequence: str = ""
    normalized_sequence: str = ""
    nn_score: float = 0.0
    log_likelihood: float = 0.0
    structure_distance: Optional[int] = None
    mfe: Optional[float] = None
    constraint_mutation_count: int = 0
    model: str


class GemornaCdsOutput(_OutBase):
    """GEMORNA CDS design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_mrna_cds_with_gemorna (wrapper return dict)
    - microservices/gemorna_service/main.py :: CdsDesignResponse
    """

    input_filepath: str
    output_filepath: str
    generated_sequence: str
    raw_output: str
    model: str


class Gemorna5UtrOutput(_OutBase):
    """GEMORNA 5'UTR design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_5utr_with_gemorna (wrapper return dict)
    - microservices/gemorna_service/main.py :: UtrDesignResponse
    """

    output_filepath: str
    generated_sequence: str
    utr_length: str
    raw_output: str
    model: str


class Gemorna3UtrOutput(_OutBase):
    """GEMORNA 3'UTR design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_3utr_with_gemorna (wrapper return dict)
    - microservices/gemorna_service/main.py :: UtrDesignResponse
    """

    output_filepath: str
    generated_sequence: str
    utr_length: str
    raw_output: str
    model: str


class Gemorna5UtrMrlPredictionOutput(_OutBase):
    """GEMORNA 5'UTR MRL prediction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: predict_5utr_mrl_with_gemorna (wrapper return dict)
    - microservices/gemorna_service/main.py :: Utr5MrlPredictionResponse
    """

    input_filepath: str
    input_sequence: str
    predicted_mrl: float
    model: str


class Gemorna3UtrStabilityPredictionOutput(_OutBase):
    """GEMORNA 3'UTR stability prediction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: predict_3utr_stability_with_gemorna (wrapper return dict)
    - microservices/gemorna_service/main.py :: Utr3StabilityPredictionResponse
    """

    input_filepath: str
    input_sequence: str
    predicted_stability: float
    model: str


# LinearDesign INTERFACE LOCK (v0.2.0) —— 禁止单方面变更


class LinearDesignCdsOutput(_OutBase):
    """LinearDesign single-sequence CDS design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: design_mrna_cds_with_lineardesign return dict
    - microservices/lineardesign_service/main.py :: LinearDesignResponse
    - agent_core/state.py :: lineardesign_* fields
    """

    input_filepath: str
    output_filepath: str
    generated_sequence: str
    structure: str
    mfe: float
    cai_score: float
    lambda_value: float
    codon_usage_path: str
    raw_output: str
    stderr: str = ""
    model: str


class LinearDesignCdsBatchItemOutput(_OutBase):
    """Per-item result inside a LinearDesign batch response."""

    success: bool
    generated_sequence: str = ""
    structure: str = ""
    mfe: float = 0.0
    cai_score: float = 0.0
    raw_output: str = ""
    stderr: str = ""
    error: str = ""


class LinearDesignCdsBatchOutput(_OutBase):
    """LinearDesign batch CDS design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: design_mrna_cds_batch_with_lineardesign return dict
    - microservices/lineardesign_service/main.py :: LinearDesignBatchResponse
    - agent_core/state.py :: lineardesign_* fields
    """

    input_filepath: str
    output_filepath: str
    best_generated_sequence: str = ""
    best_structure: str = ""
    best_mfe: float = 0.0
    best_cai_score: float = 0.0
    count: int
    success_count: int
    items: List[LinearDesignCdsBatchItemOutput]
    lambda_value: float
    codon_usage_path: str
    batch_json_filepath: str
    model: str


# Junction-aware LinearDesign tool (2026-08, additive; v0.2.0 locked schemas above
# are untouched). Mirrors microservices/lineardesign_service/main.py ::
# LinearDesignJunctionAwareResponse.


class LinearDesignCdsJunctionAwareOutput(_OutBase):
    """Junction-aware LinearDesign CDS design output schema.

    Synchronized with:
    - agent_core/tools.py :: design_mrna_cds_junction_aware_with_lineardesign return dict
    - microservices/lineardesign_service/main.py :: LinearDesignJunctionAwareResponse
    """

    input_filepath: str
    output_filepath: str
    generated_sequence: str
    structure: str
    mfe: float
    cai_score: float
    cds_sequence: str = ""
    cds_cai: float = 0.0
    full_construct_sequence: str = ""
    utr5_flank: str = ""
    utr3_flank: str = ""
    junction_weight: float = 0.0
    junction_window_nt: int = 20
    flank_nt: int = 21
    junction_window_pair_count: int = 0
    mfe_thermo: float = 0.0
    lambda_value: float
    codon_usage_path: str
    raw_output: str
    stderr: str = ""
    model: str


class RNARLCdsOutput(_OutBase):
    """RNARL CDS design output schema.

    WARNING: Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_mrna_cds_with_rnarl (wrapper return dict)
    - microservices/rnarl_service/main.py :: CdsDesignResponse
    - docs/tools/design_mrna_cds_with_rnarl.md
    """

    input_filepath: str
    output_filepath: str
    generated_sequence: str
    model_type: str
    checkpoint_path: str
    esm2_model_path: str
    device: str
    model: str


class RhoFoldOutput(_OutBase):
    """RhoFold tertiary structure prediction output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: predict_rna_tertiary_structure_with_rhofold (wrapper return dict)
    - microservices/rhofold_service/main.py :: RhoFoldPredictResponse
    """

    input_filepath: str
    pdb_filepath: str
    ct_filepath: str = ""
    results_filepath: str = ""
    log_filepath: str = ""
    service_output_dir: str = ""
    mean_plddt: float = 0.0
    model: str


class RhoDesignOutput(_OutBase):
    """RhoDesign structure→sequence design output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_rna_sequence_with_rhodesign (wrapper return dict)
    - microservices/rhodesign_service/main.py :: RhoDesignResponse
    - docs/tools/design_rna_sequence_with_rhodesign.md
    """

    input_pdb_filepath: str
    output_filepath: str = ""
    output_fasta_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    model: str


# RiboDiffusion INTERFACE LOCK (v0.2.0) —— 禁止单方面变更

class RiboDiffusionOutput(_OutBase):
    """RiboDiffusion tertiary inverse folding output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: design_rna_inverse_fold_with_ribodiffusion (wrapper return dict)
    - microservices/ribodiffusion_service/main.py :: RiboDiffusionResponse
    - agent_core/state.py :: ribodiffusion_* fields
    """

    input_pdb_filepath: str
    output_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    checkpoint_path: str
    generated_sequences: list[str] = []
    output_fasta_filepaths: list[str] = []
    model: str


# RNAsmOL 接口冻结声明 (v0.3.0) —— 禁止单方面变更
# 关联文件清单（修改时必须全部同步）：
#   - microservices/rnasmol_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py  ← 本文件
#   - agent_core/state.py
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。

class RNAsmolScoreOutput(_OutBase):
    """RNAsmol scoring output schema.

    INTERFACE LOCK (v0.3.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: score_rna_ligand_binding_with_rnasmol (wrapper return dict)
    - microservices/rnasmol_service/main.py :: ScoreResponse
    - agent_core/state.py :: rnasmol_* fields
    """
    input_filepath: str
    smiles: str
    rna_sequence: str = ""
    probability_positive: float
    predicted_label: int
    raw_logits: list[float] = []
    checkpoint_path: str = ""
    device: str = ""
    dataset: str = ""
    perturbation_type: str = ""
    model: str


class GerNABindScoreOutput(_OutBase):
    """GerNA-Bind scoring output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: score_rna_ligand_binding_with_gernabind (wrapper return dict)
    - microservices/gernabind_service/main.py :: ScoreResponse
    - agent_core/state.py :: gernabind_* fields
    """
    input_filepath: str
    smiles: str
    probability_positive: float
    predicted_label: int
    checkpoint_path: str = ""
    preprocessing_pdb_path: str = ""
    model: str


class EGARPSOutput(_OutBase):
    """EGARPS+ RNA-protein complex scoring output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: score_rna_protein_complex_with_egarps (wrapper return dict)
    - microservices/egarps_service/main.py :: EGARPSResponse
    - agent_core/state.py :: egarps_* fields
    """
    complex_id: str
    native_probability: float
    academic: bool
    model: str
    pdb_path: str


class RNASTOPPredictionOutput(_OutBase):
    """RNASTOP prediction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be
    synchronized with:
    - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    - agent_core/tools.py :: predict_mrna_stability_with_rnastop return dict
    - agent_core/state.py :: rnastop_* fields
    """

    input_filepath: str
    prediction_filepath: str
    sequence: str = ""
    used_sequence: str = ""
    sequence_length: int = 0
    used_length: int = 0
    truncated: bool = False
    structure: str = ""
    loop_type: str = ""
    mfe: float = 0.0
    mean_reactivity: float = 0.0
    mean_deg_mg_ph10: float = 0.0
    mean_deg_mg_50c: float = 0.0
    overall_stability: float = 0.0
    checkpoint_path: str = ""
    device: str = ""
    model: str


# IRESfinder 接口冻结声明 (v0.2.0) —— 禁止单方面变更
# 关联文件清单（修改时必须全部同步）：
#   - microservices/iresfinder_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py  ← 本文件
#   - agent_core/state.py
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# 本次修改的基准日期：2026-04-23。

class IRESfinderPredictionOutput(_OutBase):
    """IRESfinder prediction output schema.

    INTERFACE LOCK (v0.2.0): Locked schema — the canonical contract is the
    state after the 2026-04-23 refactor. Any field addition/removal must be
    synchronized with:
    - agent_core/tools.py :: predict_putative_ires_with_iresfinder return dict
    - microservices/iresfinder_service/main.py :: IRESfinderPredictResponse
    - agent_core/state.py :: iresfinder_* fields
    """

    input_filepath: str
    result_tsv_filepath: str
    mode: int
    window_size: int
    step_size: int
    decision_threshold: float
    has_putative_ires: bool
    max_score: float
    best_fragment_id: str
    positive_count: int
    fragment_count: int
    model: str
    predictions: list[dict[str, Any]] = []
    predictions_note: str = ""


class ODesignInferenceOutput(_OutBase):
    """ODesign inference output schema.

    INTERFACE LOCK (v0.3.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: run_odesign_inference (wrapper return dict)
    - microservices/odesign_service/main.py :: ODesignInferenceResponse
    - docs/tools/run_odesign_inference.md
    """
    input_json_filepath: str
    infer_model_name: str
    design_modality: str
    exp_name: str
    output_dir: str
    prediction_count: int = 0
    prediction_filepaths: List[str] = Field(default_factory=list)
    sample_names: List[str] = Field(default_factory=list)
    run_log_filepath: str = ""
    stdout_filepath: str = ""
    stderr_filepath: str = ""
    error_filepaths: List[str] = Field(default_factory=list)
    ckpt_root_dir: str = ""
    data_root_dir: str = ""
    timeout_seconds: int = 14400
    model: str


class BuildOdesignAptamerOutput(_OutBase):
    """ODesign aptamer input JSON builder output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: build_odesign_aptamer_input_json (wrapper return dict)
    - agent_core/state.py :: odesign_aptamer_input_* fields
    """
    input_json_filepath: str
    design_config: Dict[str, Any]
    model: str


class ExtractRnaFromCifOutput(_OutBase):
    """Extract RNA from CIF output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: extract_rna_sequence_from_cif (wrapper return dict)
    - agent_core/state.py :: extract_rna_from_cif_* fields
    """
    sequence: str
    chain_id: str
    residue_count: int
    is_rna: bool
    cif_filepath: str
    warnings: str = ""
    model: str


class ProteinXProteinOutput(_OutBase):
    """ProteinX protein structure prediction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: predict_protein_structure_with_proteinx (wrapper return dict)
    - agent_core/state.py :: protein_structure_* fields
    """
    pdb_filepath: str = ""
    mean_pae: float = 0.0
    mean_plddt: float = 0.0
    ranking_confidence: float = 0.0
    model_scores: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = "proteinx"


class ProteinXComplexOutput(_OutBase):
    """ProteinX RNA-protein complex prediction output schema."""

    pdb_filepath: str = ""
    mean_pae: float = 0.0
    mean_plddt: float = 0.0
    ipTM: float = 0.0
    ranking_confidence: float = 0.0
    model_scores: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = "proteinx"


class RnaProteinInterfaceOutput(_OutBase):
    """RNA-protein interface analysis output schema."""

    interface_contacts: int = 0
    buried_sasa: float = 0.0
    hydrogen_bonds: int = 0
    salt_bridges: int = 0
    interface_area: float = 0.0
    protein_surface_area: float = 0.0
    rna_surface_area: float = 0.0
    contact_cutoff: float = 5.0
    complex_pdb_filepath: str = ""


class IdentifyProteinBindingHotspotsOutput(_OutBase):
    """Protein binding hotspot identification output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: identify_protein_binding_hotspots (wrapper return dict)
    - agent_core/state.py :: hotspot_* fields
    """
    hotspot_residues: str
    hotspot_patch_size: int
    patch_center_coords: List[float]
    exposed_basic_count: int
    protein_structure_path: str
    chain_id: str
    model: str
    warning: str = ""


class StructureAlignmentOutput(_OutBase):
    """Structure alignment (RMSD + TM-score) output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: score_structure_alignment (wrapper return dict)
    - agent_core/state.py :: structure_rmsd / structure_tm_score fields
    """
    rmsd: float
    tm_score: float
    aligned_residue_count: int
    superposition_matrix: List[List[float]]
    reference_pdb_filepath: str
    predicted_pdb_filepath: str
    chain_id: str
    atom_type: str
    warning: str = ""
    model: str


# RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class RnaGcContentOutput(_OutBase):
    """GC content output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: compute_rna_sequence_gc_content (wrapper return dict)
    - microservices/rna_sequence_metrics_service/main.py :: GcContentResponse
    - agent_core/state.py :: sequence_gc_* fields
    """

    input_filepath: str
    resolved_filepath: str
    sequence_length: int
    g_count: int
    c_count: int
    gc_count: int
    gc_content: float
    model: str


class DotBracketUnpairedFractionOutput(_OutBase):
    """Dot-bracket unpaired fraction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: compute_dot_bracket_unpaired_fraction (wrapper return dict)
    - microservices/rna_sequence_metrics_service/main.py :: UnpairedFractionResponse
    - agent_core/state.py :: dot_bracket_* fields
    """

    input_filepath: str
    resolved_filepath: str
    structure_length: int
    dot_count: int
    unpaired_fraction: float
    model: str


# RNA sequence U content INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class RnaUContentOutput(_OutBase):
    """U content output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: compute_rna_sequence_u_content (wrapper return dict)
    - microservices/rna_sequence_metrics_service/main.py :: UContentResponse
    - agent_core/state.py :: sequence_u_* fields
    """

    input_filepath: str
    resolved_filepath: str
    sequence_length: int
    u_count: int
    u_fraction: float
    model: str


# CAI for CDS INTERFACE LOCK (v0.1.0) —— 禁止单方面变更

class CaiForCdsOutput(_OutBase):
    """CAI output schema for CDS sequences.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: compute_cai_for_cds_sequence (wrapper return dict)
    - agent_core/state.py :: cai_for_cds_* fields
    """

    input_filepath: str
    cai_score: float
    species: str
    cds_length_nt: int
    codon_count: int
    valid_codons: int
    invalid_codons: int
    stop_codons_encountered: int
    model: str


class ShuffleCdsJunctionCodonsOutput(_OutBase):
    """Junction codon shuffler output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Modify only in sync with:
    - agent_core/tools.py :: shuffle_cds_junction_codons (wrapper return dict)
    - agent_core/state.py :: shuffle_cds_junction_* fields
    """

    original_sequence: str
    junction_end: str
    shuffled_region_start: int
    shuffled_region_end: int
    variants: list[dict[str, Any]]
    model: str


class WorkflowDemoEchoOutput(_OutBase):
    """Workflow demo echo output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: workflow_demo_echo (wrapper return dict)
    """

    echo: str
    length: int
    model: str


# ViennaRNA INTERFACE LOCK (v0.4.0) —— 禁止单方面变更

TOOL_SPECS: Dict[str, ToolSpec] = {
    "compute_sirna_duplex_binding_vienna": ToolSpec(
        identity="compute_sirna_duplex_binding_vienna",
        display_name="ViennaRNA duplex cofold (siRNA sense/antisense)",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/sirna-duplex",
        capabilities=[
            "Compute sense/antisense cofold secondary structure and duplex MFE (kcal/mol).",
        ],
        limitations=[
            "Does not predict siRNA efficacy or genome-wide off-targets.",
            "Requires two strands (sense + antisense) as input.",
        ],
        task_tags=["sirna_duplex_energy", "rna_secondary_structure"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["structure", "mfe_kcal_per_mol"],
        input_model=tool_wrappers.SirnaDuplexViennaInput,
        output_model=ViennaDuplexOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Cofold duplex energy from two-record FASTA",
                input={"filepath": "workspace/sirna_duplex_*.fasta"},
                output_excerpt={"mfe_kcal_per_mol": -12.3},
            )
        ],
    ),
    # Evitar 接口冻结声明 (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/evitar_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # 本次修改的基准日期：2026-04-24。
    "design_sirna_with_evitar": ToolSpec(
        identity="design_sirna_with_evitar",
        display_name="Evitar siRNA/Cas13 design",
        version="0.2.0",
        source="https://github.com/dingyaozhang/Evitar",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8016/design",
        capabilities=[
            "Design siRNA/Cas13 guides via Evitar CLI wrapper.",
            "Support existing-virus mode (with optional strains) and future-virus predesign mode.",
            "Off-target analysis with transcriptome / 3'UTR / tissue-specific gene weights.",
            "GC-content filtering, allow/ban lists, and SGAR/greedy selection algorithms.",
        ],
        limitations=[
            "Upstream binaries are Linux-only (as documented in repo guide).",
            "CRISPR mode (--predict CRISPR) requires R (>=3.4) runtime installed on server; will fail if Rscript is missing.",
            "Off-target analysis requires pre-built transcriptome and 3'UTR FASTA files (not bundled). Run GenomeData.sh to generate.",
            "Real tissue-specific off-target weights require GTEx-derived gene weight files (weightedgene/ already bundled).",
        ],
        task_tags=["sirna_design", "cas13_guide_design", "antiviral_rna_design"],
        requires=[
            ToolDependency(name="Linux", detail="Evitar upstream binaries are Linux executables"),
            ToolDependency(name="Evitar microservice", detail="microservices/evitar_service (port 8016)"),
            ToolDependency(name="Perl", detail="Evitar.pl requires Perl 5 runtime"),
            ToolDependency(name="ViennaRNA", detail="RNAfold / RNAplfold / RNAduplex bundled in Evitar/bin/"),
            ToolDependency(name="R (optional)", detail="Required only for --predict CRISPR mode (R >= 3.4)"),
            ToolDependency(name="MUSCLE", detail="Bundled in Evitar/bin/ for predesign mode"),
        ],
        produces=["output_filepath", "top_results", "command"],
        input_model=tool_wrappers.EvitarDesignInput,
        output_model=EvitarDesignOutput,
        status=ToolStatus.partial,
    ),
    # BLAST+ INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/blast_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    "run_blastn_similarity_search": ToolSpec(
        identity="run_blastn_similarity_search",
        display_name="BLAST+ blastn similarity search",
        version="0.2.0",
        source="https://blast.ncbi.nlm.nih.gov/Blast.cgi",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8019/blastn",
        capabilities=["Run blastn search against a subject FASTA or existing BLAST DB."],
        limitations=["Not a siRNA off-target production pipeline by itself; returns alignments/hits only."],
        task_tags=["blastn_similarity_search", "off_target_screening_support"],
        requires=[ToolDependency(name="BLAST+ microservice", detail="microservices/blast_service (port 8019)")],
        produces=["hit_count", "hits_preview", "tabular_tsv_filepath", "subject_mode", "blastn_command", "makeblastdb_command", "stderr"],
        input_model=tool_wrappers.BlastnSearchInput,
        output_model=BlastnSearchOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="blastn against subject FASTA",
                input={"filepath": "workspace/query.fa", "subject_fasta_path": "workspace/subject.fa", "task": "blastn-short"},
                output_excerpt={"hit_count": 3, "subject_mode": "fasta"},
            )
        ],
    ),
    "run_bowtie2_short_alignment": ToolSpec(
        identity="run_bowtie2_short_alignment",
        display_name="Bowtie2 short-sequence alignment",
        version="0.1.0",
        source="https://bowtie-bio.sourceforge.net/bowtie2/index.shtml",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8024/align",
        capabilities=["Fast short-sequence alignment using bowtie2 --local."],
        limitations=["Returns SAM-format alignments; identity filtering must be done post-hoc or via --score-min."],
        task_tags=["short_read_alignment", "off_target_screening_support"],
        requires=[ToolDependency(name="Bowtie2 microservice", detail="microservices/bowtie2_service (port 8024)")],
        produces=["hit_count", "hits_preview", "tabular_sam_filepath", "subject_mode", "bowtie2_command", "bowtie2_build_command", "stderr"],
        input_model=tool_wrappers.Bowtie2AlignInput,
        output_model=Bowtie2AlignOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="bowtie2 local alignment against subject FASTA",
                input={"filepath": "workspace/query.fa", "subject_fasta_path": "workspace/subject.fa", "mode": "local"},
                output_excerpt={"hit_count": 5, "subject_mode": "fasta"},
            )
        ],
    ),
    "predict_rna_secondary_structure": ToolSpec(
        identity="predict_rna_secondary_structure",
        display_name="ViennaRNA RNAfold (secondary structure)",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/fold",
        capabilities=["Predict secondary structure and MFE for a single RNA sequence."],
        limitations=["Returns thermodynamic MFE only; no experimental constraints unless implemented server-side."],
        task_tags=["rna_secondary_structure_prediction"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["structure", "mfe_kcal_per_mol", "ensemble_free_energy", "centroid_structure", "centroid_distance", "mea_structure", "mea_score", "mea_gamma"],
        input_model=tool_wrappers.FoldViennaInput,
        output_model=ViennaFoldOutput,
        status=ToolStatus.available,
    ),
    "compute_rna_rna_interaction_vienna": ToolSpec(
        identity="compute_rna_rna_interaction_vienna",
        display_name="ViennaRNA RNAup (RNA-RNA interaction thermodynamics)",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/rnaup",
        capabilities=[
            "Calculate thermodynamics of RNA-RNA interactions: accessibility + binding energy.",
        ],
        limitations=[
            "Requires RNAup executable on PATH; RNAlib Python API not used for RNAup.",
        ],
        task_tags=["rna_rna_interaction", "rnaup"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["interaction_energy", "interaction_structure", "raw_stdout"],
        input_model=tool_wrappers.RnaUpViennaInput,
        output_model=ViennaRnaUpOutput,
        status=ToolStatus.available,
    ),
    "compute_aso_target_accessibility_vienna": ToolSpec(
        identity="compute_aso_target_accessibility_vienna",
        display_name="ViennaRNA RNAplfold accessibility (ASO)",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/aso-accessibility",
        capabilities=["Estimate local target accessibility for an ASO binding region via RNAplfold."],
        limitations=["Accessibility is model-based; requires full-length target context for meaningful results."],
        task_tags=["aso_accessibility"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["mean_unpaired_prob_single_nt", "joint_unpaired_prob_stretch_ending_at_region_end"],
        input_model=tool_wrappers.AsoAccessibilityViennaInput,
        output_model=ViennaAsoAccessibilityOutput,
        status=ToolStatus.available,
    ),
    "predict_rna_local_accessibility_profile_vienna": ToolSpec(
        identity="predict_rna_local_accessibility_profile_vienna",
        display_name="ViennaRNA RNAplfold local accessibility profile",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/plfold-profiles",
        capabilities=[
            "Compute whole-sequence local unpaired probabilities (RNAplfold lunp, single-nt column) for accessibility curves.",
        ],
        limitations=[
            "Server caps sequence length (default 8000 nt); returns first lunp column only in the API (stretch columns not exported).",
        ],
        task_tags=["rna_local_accessibility", "rna_plfold_profile"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["lunp_profile_tsv_filepath", "mean_unpaired_prob_1nt"],
        input_model=tool_wrappers.PlfoldLocalProfileViennaInput,
        output_model=ViennaPlfoldLocalProfileOutput,
        status=ToolStatus.available,
    ),
    "inverse_fold_rna_secondary_structure_vienna": ToolSpec(
        identity="inverse_fold_rna_secondary_structure_vienna",
        display_name="ViennaRNA RNAinverse (inverse folding)",
        version="0.4.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/inverse-fold",
        capabilities=["Generate a sequence that folds into a target dot-bracket structure (heuristic search)."],
        limitations=["Inverse folding is heuristic; returned sequence may not be unique or globally optimal."],
        task_tags=["inverse_folding"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["best_sequence", "best_sequence_filepath"],
        input_model=tool_wrappers.InverseFoldViennaInput,
        output_model=ViennaInverseFoldOutput,
        status=ToolStatus.available,
    ),
    # LinearFold INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/linearfold_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - docs/tools/predict_rna_secondary_structure_with_linearfold.md
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    "predict_rna_secondary_structure_with_linearfold": ToolSpec(
        identity="predict_rna_secondary_structure_with_linearfold",
        display_name="LinearFold secondary structure",
        version="0.2.0-port8015",
        source="https://github.com/LinearFold/LinearFold",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8015/fold",
        capabilities=[
            "Predict RNA secondary structure with linear-time algorithm (beam search).",
            "Supports constrained folding and SHAPE-guided folding.",
        ],
        limitations=["Approximates search with beam; results depend on beam size and parameterization."],
        task_tags=["rna_secondary_structure_prediction"],
        requires=[ToolDependency(name="LinearFold microservice", detail="microservices/linearfold_service (port 8015)")],
        produces=["structure", "mfe"],
        input_model=tool_wrappers.LinearFoldSecondaryInput,
        output_model=LinearFoldOutput,
        status=ToolStatus.available,
    ),
    "evaluate_rna_structure_with_linearfold": ToolSpec(
        identity="evaluate_rna_structure_with_linearfold",
        display_name="LinearFold structure energy evaluation",
        version="0.2.0-port8015",
        source="https://github.com/LinearFold/LinearFold",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8015/eval",
        capabilities=["Evaluate free energy of a given RNA secondary structure."],
        limitations=["Only supports dot-bracket notation; pseudoknots are ignored."],
        task_tags=["rna_secondary_structure_evaluation"],
        requires=[ToolDependency(name="LinearFold microservice", detail="microservices/linearfold_service (port 8015)")],
        produces=["energy"],
        input_model=tool_wrappers.LinearFoldEvalInput,
        output_model=LinearFoldEvalOutput,
        status=ToolStatus.available,
    ),
    "predict_rna_secondary_structure_with_linearfold_zuker": ToolSpec(
        identity="predict_rna_secondary_structure_with_linearfold_zuker",
        display_name="LinearFold Zuker suboptimal structures",
        version="0.2.0-port8015",
        source="https://github.com/LinearFold/LinearFold",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8015/fold/zuker_subopt",
        capabilities=["Enumerate Zuker suboptimal RNA secondary structures within an energy window."],
        limitations=["Number of suboptimal structures grows with sequence length and energy window."],
        task_tags=["rna_secondary_structure_prediction"],
        requires=[ToolDependency(name="LinearFold microservice", detail="microservices/linearfold_service (port 8015)")],
        produces=["structures", "mfe"],
        input_model=tool_wrappers.LinearFoldZukerSuboptInput,
        output_model=LinearFoldZukerSuboptOutput,
        status=ToolStatus.available,
    ),
    # LinearDesign INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/lineardesign_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - workflow_api/mrna_handler.py
    #   - workflow_api/mrna_schemas.py
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # 本次修改的基准日期：2026-04-24。
    "design_mrna_cds_with_lineardesign": ToolSpec(
        identity="design_mrna_cds_with_lineardesign",
        display_name="LinearDesign protein→CDS design",
        version="0.2.0-port8014",
        source="https://github.com/LinearDesignSoftware/LinearDesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8014/generate/cds",
        capabilities=[
            "Generate CDS sequence from a single protein sequence via LinearDesign binary wrapper.",
            "Expose lambda (MFE/CAI balance), custom codon usage tables, and verbose logging.",
        ],
        limitations=[
            "Requires server-side compiled binaries (run `make` in external_repos/LinearDesign).",
            "Single-sequence endpoint; for bulk design use the batch tool.",
        ],
        task_tags=["protein_to_cds_design"],
        requires=[
            ToolDependency(name="Linux", detail="Documented deployment target"),
            ToolDependency(name="LinearDesign microservice", detail="microservices/lineardesign_service (port 8014)"),
        ],
        produces=["output_filepath", "generated_sequence", "structure", "mfe", "cai_score", "raw_output", "stderr"],
        input_model=tool_wrappers.LinearDesignCdsInput,
        output_model=LinearDesignCdsOutput,
        status=ToolStatus.partial,
    ),
    "design_mrna_cds_batch_with_lineardesign": ToolSpec(
        identity="design_mrna_cds_batch_with_lineardesign",
        display_name="LinearDesign protein→CDS batch design",
        version="0.2.0-port8014",
        source="https://github.com/LinearDesignSoftware/LinearDesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8014/generate/cds/batch",
        capabilities=[
            "Batch-generate CDS sequences from multiple protein sequences (FASTA or plain text).",
            "Mirrors upstream ``cat FASTA_FILE | ./lineardesign`` capability.",
        ],
        limitations=[
            "Requires server-side compiled binaries (run `make` in external_repos/LinearDesign).",
            "All sequences share the same lambda and codon usage settings.",
        ],
        task_tags=["protein_to_cds_design", "batch_design"],
        requires=[
            ToolDependency(name="Linux", detail="Documented deployment target"),
            ToolDependency(name="LinearDesign microservice", detail="microservices/lineardesign_service (port 8014)"),
        ],
        produces=["output_filepath", "best_generated_sequence", "count", "success_count", "items", "batch_json_filepath"],
        input_model=tool_wrappers.LinearDesignCdsBatchInput,
        output_model=LinearDesignCdsBatchOutput,
        status=ToolStatus.partial,
    ),
    # Junction-aware LinearDesign tool (2026-08, additive; v0.2.0 locked specs above
    # are untouched). Synchronized with microservices/lineardesign_service/main.py ::
    # /generate/cds_junction_aware and agent_core/tools.py ::
    # design_mrna_cds_junction_aware_with_lineardesign.
    "design_mrna_cds_junction_aware_with_lineardesign": ToolSpec(
        identity="design_mrna_cds_junction_aware_with_lineardesign",
        display_name="LinearDesign junction-aware protein→CDS design",
        version="0.1.0-port8014",
        source="https://github.com/LinearDesignSoftware/LinearDesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8014/generate/cds_junction_aware",
        capabilities=[
            "Generate CDS with fixed UTR flank slices folded into the full construct (cross-junction pairs visible to the optimizer).",
            "Apply a junction-window pair penalty (junction_weight, kcal/mol) inside the CKY objective.",
            "Report CDS-only sequence/CAI, window pair count, and thermodynamic MFE alongside the objective value.",
        ],
        limitations=[
            "Requires the patched LinearDesign binary (JUNCTION-PATCH 2026-08; run `make` in external_repos/LinearDesign).",
            "Single-sequence endpoint; `mfe` is the CKY objective value (thermodynamic MFE + penalty), see `mfe_thermo` for the pure MFE.",
        ],
        task_tags=["protein_to_cds_design", "junction_aware_design"],
        requires=[
            ToolDependency(name="Linux", detail="Documented deployment target"),
            ToolDependency(name="LinearDesign microservice", detail="microservices/lineardesign_service (port 8014)"),
        ],
        produces=["output_filepath", "generated_sequence", "cds_sequence", "cds_cai", "junction_window_pair_count", "mfe_thermo"],
        input_model=tool_wrappers.LinearDesignCdsJunctionAwareInput,
        output_model=LinearDesignCdsJunctionAwareOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): RNARL tool spec. See docs/tools/design_mrna_cds_with_rnarl.md
    # for the canonical contract. Modify only in sync with wrapper + microservice.
    "design_mrna_cds_with_rnarl": ToolSpec(
        identity="design_mrna_cds_with_rnarl",
        display_name="RNARL protein→CDS design",
        version="0.2.0",
        source="https://github.com/SII-ShenggengLin/RNARL",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8008/generate/cds",
        capabilities=["Generate CDS from protein sequence via RNARL actor inference."],
        limitations=["Requires GPU + checkpoints + local ESM2 model as documented."],
        task_tags=["protein_to_cds_design"],
        requires=[ToolDependency(name="GPU", detail="RNARL inference"), ToolDependency(name="RNARL microservice", detail="microservices/rnarl_service (port 8008)")],
        produces=["output_filepath", "generated_sequence"],
        input_model=tool_wrappers.RNARLCdsInput,
        output_model=RNARLCdsOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): GEMORNA CDS tool spec. Modify only in sync with:
    # - agent_core/tools.py :: design_mrna_cds_with_gemorna
    # - microservices/gemorna_service/main.py :: CdsDesignRequest / CdsDesignResponse
    "design_mrna_cds_with_gemorna": ToolSpec(
        identity="design_mrna_cds_with_gemorna",
        display_name="GEMORNA protein→CDS design",
        version="0.2.0",
        source="https://github.com/RainaBio/GEMORNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8004/generate/cds",
        capabilities=["Generate CDS from protein sequence via GEMORNA."],
        limitations=["Requires Linux GPU and checkpoints; Python ABI constraints (3.10) as documented."],
        task_tags=["protein_to_cds_design"],
        requires=[ToolDependency(name="GPU", detail="GEMORNA inference"), ToolDependency(name="GEMORNA microservice", detail="microservices/gemorna_service (port 8004)")],
        produces=["output_filepath", "generated_sequence"],
        input_model=tool_wrappers.GemornaCdsInput,
        output_model=GemornaCdsOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): GEMORNA 5'UTR tool spec. Modify only in sync with:
    # - agent_core/tools.py :: design_5utr_with_gemorna
    # - microservices/gemorna_service/main.py :: UtrDesignRequest / UtrDesignResponse
    "design_5utr_with_gemorna": ToolSpec(
        identity="design_5utr_with_gemorna",
        display_name="GEMORNA 5'UTR design",
        version="0.2.0",
        source="https://github.com/RainaBio/GEMORNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8004/generate/5utr",
        capabilities=["Generate 5'UTR sequence via GEMORNA."],
        limitations=["Requires Linux GPU and checkpoints; Python ABI constraints (3.10) as documented."],
        task_tags=["utr_design", "5utr_design"],
        requires=[ToolDependency(name="GPU", detail="GEMORNA inference"), ToolDependency(name="GEMORNA microservice", detail="microservices/gemorna_service (port 8004)")],
        produces=["output_filepath", "generated_sequence"],
        input_model=tool_wrappers.Gemorna5UtrInput,
        output_model=Gemorna5UtrOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): GEMORNA 3'UTR tool spec. Modify only in sync with:
    # - agent_core/tools.py :: design_3utr_with_gemorna
    # - microservices/gemorna_service/main.py :: UtrDesignRequest / UtrDesignResponse
    "design_3utr_with_gemorna": ToolSpec(
        identity="design_3utr_with_gemorna",
        display_name="GEMORNA 3'UTR design",
        version="0.2.0",
        source="https://github.com/RainaBio/GEMORNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8004/generate/3utr",
        capabilities=["Generate 3'UTR sequence via GEMORNA."],
        limitations=["Requires Linux GPU and checkpoints; Python ABI constraints (3.10) as documented."],
        task_tags=["utr_design", "3utr_design"],
        requires=[ToolDependency(name="GPU", detail="GEMORNA inference"), ToolDependency(name="GEMORNA microservice", detail="microservices/gemorna_service (port 8004)")],
        produces=["output_filepath", "generated_sequence"],
        input_model=tool_wrappers.Gemorna3UtrInput,
        output_model=Gemorna3UtrOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.1.0): GEMORNA 5'UTR MRL prediction tool spec. Modify only in sync with:
    # - agent_core/tools.py :: predict_5utr_mrl_with_gemorna
    # - microservices/gemorna_service/main.py :: UtrPredictionRequest / Utr5MrlPredictionResponse
    "predict_5utr_mrl_with_gemorna": ToolSpec(
        identity="predict_5utr_mrl_with_gemorna",
        display_name="GEMORNA 5'UTR MRL prediction",
        version="0.1.0",
        source="https://github.com/RainaBio/GEMORNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8004/predict/5utr_mrl",
        capabilities=["Predict 5'UTR Mean Ribosomal Load (MRL) via GEMORNA."],
        limitations=["Requires Linux GPU and checkpoints; Python ABI constraints (3.10) as documented."],
        task_tags=["utr_prediction", "5utr_mrl_prediction"],
        requires=[ToolDependency(name="GPU", detail="GEMORNA inference"), ToolDependency(name="GEMORNA microservice", detail="microservices/gemorna_service (port 8004)")],
        produces=["input_sequence", "predicted_mrl"],
        input_model=tool_wrappers.Gemorna5UtrPredictionInput,
        output_model=Gemorna5UtrMrlPredictionOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.1.0): GEMORNA 3'UTR stability prediction tool spec. Modify only in sync with:
    # - agent_core/tools.py :: predict_3utr_stability_with_gemorna
    # - microservices/gemorna_service/main.py :: UtrPredictionRequest / Utr3StabilityPredictionResponse
    "predict_3utr_stability_with_gemorna": ToolSpec(
        identity="predict_3utr_stability_with_gemorna",
        display_name="GEMORNA 3'UTR stability prediction",
        version="0.1.0",
        source="https://github.com/RainaBio/GEMORNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8004/predict/3utr_stability",
        capabilities=["Predict 3'UTR stability via GEMORNA."],
        limitations=["Requires Linux GPU and checkpoints; Python ABI constraints (3.10) as documented."],
        task_tags=["utr_prediction", "3utr_stability_prediction"],
        requires=[ToolDependency(name="GPU", detail="GEMORNA inference"), ToolDependency(name="GEMORNA microservice", detail="microservices/gemorna_service (port 8004)")],
        produces=["input_sequence", "predicted_stability"],
        input_model=tool_wrappers.Gemorna3UtrPredictionInput,
        output_model=Gemorna3UtrStabilityPredictionOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): RhoFold tool spec. Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: RhoFoldInput / predict_rna_tertiary_structure_with_rhofold
    # - agent_core/tool_specs.py :: RhoFoldOutput
    # - microservices/rhofold_service/main.py :: RhoFoldPredictRequest / RhoFoldPredictResponse
    "predict_rna_tertiary_structure_with_rhofold": ToolSpec(
        identity="predict_rna_tertiary_structure_with_rhofold",
        display_name="RhoFold tertiary structure prediction",
        version="0.2.0",
        source="https://github.com/ml4bio/RhoFold",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8005/predict",
        capabilities=["Predict RNA tertiary structure (single-sequence mode in this repo)."],
        limitations=["Depends on GPU/weights; results depend on model assets and runtime config."],
        task_tags=["rna_tertiary_structure_prediction"],
        requires=[ToolDependency(name="GPU", detail="RhoFold inference"), ToolDependency(name="RhoFold microservice", detail="microservices/rhofold_service (port 8005)")],
        produces=["pdb_filepath", "ct_filepath", "results_filepath", "log_filepath", "mean_plddt"],
        input_model=tool_wrappers.RhoFoldInput,
        output_model=RhoFoldOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): RhoDesign tool spec. Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: RhoDesignInput / design_rna_sequence_with_rhodesign
    # - microservices/rhodesign_service/main.py :: RhoDesignRequest / RhoDesignResponse
    # - docs/tools/design_rna_sequence_with_rhodesign.md
    "design_rna_sequence_with_rhodesign": ToolSpec(
        identity="design_rna_sequence_with_rhodesign",
        display_name="RhoDesign structure→sequence design",
        version="0.2.0",
        source="https://github.com/ml4bio/RhoDesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8006/design/from-structure",
        capabilities=["Design RNA sequence conditioned on input 3D structure (PDB)."],
        limitations=["Depends on GPU/weights; requires valid PDB input."],
        task_tags=["rna_structure_to_sequence_design"],
        requires=[ToolDependency(name="GPU", detail="RhoDesign inference"), ToolDependency(name="RhoDesign microservice", detail="microservices/rhodesign_service (port 8006)")],
        produces=["output_fasta_filepath", "predicted_sequence"],
        input_model=tool_wrappers.RhoDesignInput,
        output_model=RhoDesignOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): RiboDiffusion tool spec. Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: RiboDiffusionInput / design_rna_inverse_fold_with_ribodiffusion
    # - microservices/ribodiffusion_service/main.py :: RiboDiffusionRequest / RiboDiffusionResponse
    # - agent_core/workflows/rna_tertiary_structure_design.py
    "design_rna_inverse_fold_with_ribodiffusion": ToolSpec(
        identity="design_rna_inverse_fold_with_ribodiffusion",
        display_name="RiboDiffusion tertiary inverse folding",
        version="0.2.0",
        source="https://github.com/ml4bio/RiboDiffusion",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8021/design/from-pdb",
        capabilities=[
            "Sample RNA sequences conditioned on PDB tertiary structure via diffusion (inverse folding).",
            "Supports checkpoint selection (exp_inf / exp_inf_large) for diversity control.",
        ],
        limitations=[
            "Requires GPU + upstream checkpoint under external_repos/RiboDiffusion/ckpts/; "
            "PyTorch Geometric CUDA wheels must match the installed torch build.",
        ],
        task_tags=["rna_structure_to_sequence_design", "rna_inverse_folding_diffusion"],
        requires=[
            ToolDependency(name="GPU", detail="RiboDiffusion inference"),
            ToolDependency(name="RiboDiffusion microservice", detail="microservices/ribodiffusion_service (port 8021)"),
        ],
        produces=["output_filepath", "predicted_sequence", "recovery_rate", "checkpoint_path"],
        input_model=tool_wrappers.RiboDiffusionInput,
        output_model=RiboDiffusionOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.3.0) — RNAsmol scoring tool spec
    # Any field addition/removal must be synchronized with:
    # - microservices/rnasmol_service/main.py :: ScoreRequest / ScoreResponse
    # - agent_core/tools.py :: RNAsmolScoreInput / score_rna_ligand_binding_with_rnasmol
    # - agent_core/tool_specs.py :: RNAsmolScoreOutput
    # - agent_core/state.py :: rnasmol_* fields
    # - agent_core/workflows/rna_small_molecule_interaction.py :: evaluate() consumption
    "score_rna_ligand_binding_with_rnasmol": ToolSpec(
        identity="score_rna_ligand_binding_with_rnasmol",
        display_name="RNAsmol RNA-ligand scoring",
        version="0.3.0",
        source="https://github.com/hongli-ma/RNAsmol",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8007/score",
        capabilities=["Score RNA-ligand interaction with RNAsmol classifier."],
        limitations=["Classifier output is model-dependent; requires correct checkpoint and device config."],
        task_tags=["rna_ligand_scoring"],
        requires=[ToolDependency(name="GPU", detail="Recommended for model"), ToolDependency(name="RNAsmol microservice", detail="microservices/rnasmol_service (port 8007)")],
        produces=["probability_positive", "predicted_label", "raw_logits", "checkpoint_path", "device", "dataset", "perturbation_type"],
        input_model=tool_wrappers.RNAsmolScoreInput,
        output_model=RNAsmolScoreOutput,
        status=ToolStatus.available,
    ),
    # INTERFACE LOCK (v0.1.0) — GerNA-Bind scoring tool spec
    # Any field addition/removal must be synchronized with:
    # - microservices/gernabind_service/main.py :: ScoreRequest / ScoreResponse
    # - agent_core/tools.py :: GerNABindScoreInput / score_rna_ligand_binding_with_gernabind
    # - agent_core/tool_specs.py :: GerNABindScoreOutput
    # - agent_core/state.py :: gernabind_* fields
    # - agent_core/workflows/rna_small_molecule_interaction.py :: evaluate() consumption
    "score_rna_ligand_binding_with_gernabind": ToolSpec(
        identity="score_rna_ligand_binding_with_gernabind",
        display_name="GerNA-Bind RNA-ligand scoring",
        version="0.1.0",
        source="https://github.com/GENTEL-lab/GerNA-Bind",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8010/score",
        capabilities=["Score RNA-ligand affinity with GerNA-Bind; wrapper may trigger 3D preprocessing. Supports dataset/split_method hints for automatic checkpoint selection."],
        limitations=["Depends on GPU/weights; binding-site prediction is a separate endpoint/tool path. Default affinity checkpoint is Robin_random.pth when no hint is given."],
        task_tags=["rna_ligand_scoring"],
        requires=[ToolDependency(name="GPU", detail="GerNA-Bind inference"), ToolDependency(name="GerNA-Bind microservice", detail="microservices/gernabind_service (port 8010)")],
        produces=["probability_positive", "predicted_label"],
        input_model=tool_wrappers.GerNABindScoreInput,
        output_model=GerNABindScoreOutput,
        status=ToolStatus.available,
    ),
    # INTERFACE LOCK (v0.1.0) — score_rna_protein_complex_with_egarps
    # Any field addition/removal must be synchronized with:
    # - microservices/egarps_service/main.py :: EGARPSRequest / EGARPSResponse
    # - agent_core/tools.py :: EGARPSInput / score_rna_protein_complex_with_egarps
    # - agent_core/tool_specs.py :: EGARPSOutput
    # - agent_core/state.py :: egarps_* fields
    "score_rna_protein_complex_with_egarps": ToolSpec(
        identity="score_rna_protein_complex_with_egarps",
        display_name="EGARPS+ RNA-protein complex scoring",
        version="0.1.0",
        source="https://github.com/hzau-liulab/EGARPS",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8023/score",
        capabilities=["Score RNA-protein complex structures with EGARPS+ graph learning model."],
        limitations=["Non-academic mode uses reduced features (no DSSR/NACCESS). Academic mode requires DSSR and NACCESS licenses. GPU required for inference."],
        task_tags=["rna_protein_scoring"],
        requires=[ToolDependency(name="GPU", detail="EGARPS+ inference"), ToolDependency(name="EGARPS+ microservice", detail="microservices/egarps_service (port 8023)")],
        produces=["complex_id", "native_probability", "academic", "pdb_path"],
        input_model=tool_wrappers.EGARPSInput,
        output_model=EGARPSOutput,
        status=ToolStatus.available,
    ),
    # INTERFACE LOCK (v0.1.0) — predict_mrna_stability_with_rnastop
    # Any field addition/removal in produces[] or capability strings must be
    # synchronized with:
    # - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    # - agent_core/tools.py :: predict_mrna_stability_with_rnastop return dict
    # - agent_core/state.py :: rnastop_* fields
    "predict_mrna_stability_with_rnastop": ToolSpec(
        identity="predict_mrna_stability_with_rnastop",
        display_name="RNASTOP stability/degradation prediction",
        version="0.1.0",
        source="https://github.com/SII-ShenggengLin/RNASTOP",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8009/predict/stability",
        capabilities=[
            "Predict stability/degradation-related summary scores with RNASTOP.",
            "Accepts optional pre-computed secondary structure and loop-type annotation.",
        ],
        limitations=[
            "This repo wrapper exposes prediction only (not beam/MCTS optimization).",
            "Sequences longer than 512 nt are truncated to the first 512 nt by the service (truncated=True).",
        ],
        task_tags=["mrna_stability_prediction"],
        requires=[ToolDependency(name="GPU", detail="RNASTOP inference"), ToolDependency(name="RNASTOP microservice", detail="microservices/rnastop_service (port 8009)")],
        produces=[
            "prediction_filepath",
            "structure",
            "loop_type",
            "mean_reactivity",
            "mean_deg_mg_ph10",
            "mean_deg_mg_50c",
            "overall_stability",
        ],
        input_model=tool_wrappers.RNASTOPPredictionInput,
        output_model=RNASTOPPredictionOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0): IRESfinder tool spec. Locked contract.
    # Modify only in sync with:
    # - agent_core/tools.py :: IRESfinderPredictionInput / predict_putative_ires_with_iresfinder
    # - microservices/iresfinder_service/main.py :: IRESfinderPredictRequest / IRESfinderPredictResponse
    # - agent_core/state.py :: iresfinder_* fields
    "predict_putative_ires_with_iresfinder": ToolSpec(
        identity="predict_putative_ires_with_iresfinder",
        display_name="IRESfinder prediction",
        version="0.2.0",
        source="https://github.com/xiaofengsong/IRESfinder",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8013/predict",
        capabilities=[
            "Predict putative IRES elements using the published IRESfinder logistic-regression model.",
            "Supports mode 0 (full sequence), mode 1 (header-specified subsequence), and mode 2 (sliding window).",
        ],
        limitations=[
            "Requires model/data assets (external_repos/IRESfinder/module/train.data) present on server.",
            "Sequence is normalized to DNA (U->T); only A/C/G/T are accepted after normalization.",
        ],
        task_tags=["ires_prediction"],
        requires=[ToolDependency(name="IRESfinder microservice", detail="microservices/iresfinder_service (port 8013)")],
        produces=[
            "result_tsv_filepath",
            "has_putative_ires",
            "max_score",
            "best_fragment_id",
            "positive_count",
            "fragment_count",
            "mode",
            "window_size",
            "step_size",
            "decision_threshold",
            "predictions",
        ],
        input_model=tool_wrappers.IRESfinderPredictionInput,
        output_model=IRESfinderPredictionOutput,
        status=ToolStatus.available,
    ),
    # codonw-slim INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单见本文件上方 CodonwSlimOutput 的 INTERFACE LOCK 注释。
    "analyze_cds_codon_metrics_with_codonw_slim": ToolSpec(
        identity="analyze_cds_codon_metrics_with_codonw_slim",
        display_name="codonw-slim CDS metrics",
        version="0.2.0",
        source="https://github.com/smsaladi/codonw-slim",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8018/analyze/cds",
        capabilities=[
            "Compute codon usage metrics: CAI, Fop, CBI, Nc (ENC), hydropathy, aromaticity.",
            "Compute base composition (overall, by codon position, silent sites): GC3s, GC1/2/3, A3s/T3s/C3s/G3s.",
            "Optional tables: codon usage counts, RSCU, dinucleotide by frame, amino-acid usage, RAAU, base composition matrix.",
            "Support multiple genetic codes (0--7) and reference species indices for CAI/CBI/Fop.",
        ],
        limitations=[
            "Requires in-frame CDS input (length multiple of 3); trailing bases are trimmed server-side.",
            "No error checking for start/stop codons, internal stops, or partial codons (upstream CodonW behaviour).",
        ],
        task_tags=["cds_codon_metrics", "codon_usage", "cai", "cbi", "fop", "enc", "nc"],
        requires=[ToolDependency(name="codonw-slim microservice", detail="microservices/codonw_slim_service (port 8018)")],
        produces=[
            "cai_score", "enc", "fop", "cbi",
            "hydropathy", "aromaticity",
            "silent_base_usage", "bases2",
            "metrics_json_filepath",
            "codon_usage", "rscu", "dinuc",
            "aa_usage", "raau", "bases",
        ],
        input_model=tool_wrappers.CodonwSlimAnalyzeInput,
        output_model=CodonwSlimOutput,
        status=ToolStatus.available,
    ),
    # CRISOT INTERFACE LOCK (v0.2.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/crisot_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - cli/ entrypoints
    # 规则：任何字段增删、端点路径变更、输入/输出模型变动、返回值结构调整，
    #      必须同时更新上述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # 本次修改的基准日期：2026-04-24。
    "score_crispr_off_target_with_crisot": ToolSpec(
        identity="score_crispr_off_target_with_crisot",
        display_name="CRISOT score (single pair)",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/score",
        capabilities=["Score a single sgRNA-target pair with CRISOT."],
        limitations=["Input normalization enforces 23-nt sequences; does not search genome-wide off-targets."],
        task_tags=["crispr_offtarget_scoring"],
        requires=[ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["crisot_score"],
        input_model=tool_wrappers.CrisotScoreInput,
        output_model=CrisotScoreOutput,
        status=ToolStatus.partial,
    ),
    "calculate_crispr_specificity_with_crisot": ToolSpec(
        identity="calculate_crispr_specificity_with_crisot",
        display_name="CRISOT specificity (CSV)",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/spec",
        capabilities=["Compute CRISOT specificity score over pairs in a CSV."],
        limitations=["Requires CSV with expected column names; does not discover off-targets itself."],
        task_tags=["crispr_specificity_csv"],
        requires=[ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["crisot_spec", "scored_csv_filepath"],
        input_model=tool_wrappers.CrisotSpecInput,
        output_model=CrisotSpecOutput,
        status=ToolStatus.partial,
    ),
    "search_crispr_off_targets_with_crisot": ToolSpec(
        identity="search_crispr_off_targets_with_crisot",
        display_name="CRISOT genome-wide off-spec search",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/off-spec",
        capabilities=["Search genome-wide off-targets and compute specificity with Cas-OFFinder + CRISOT."],
        limitations=["Requires reference genome FASTA and Cas-OFFinder installed in service env."],
        task_tags=["crispr_offtarget_search"],
        requires=[ToolDependency(name="Reference genome", detail="FASTA path"), ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["off_target_count", "scored_csv_filepath"],
        input_model=tool_wrappers.CrisotOffSpecInput,
        output_model=CrisotOffSpecOutput,
        status=ToolStatus.partial,
    ),
    "optimize_sgrna_with_crisot": ToolSpec(
        identity="optimize_sgrna_with_crisot",
        display_name="CRISOT sgRNA optimization",
        version="0.2.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/optimize",
        capabilities=["Optimize sgRNA mutations to improve specificity under mismatch constraints."],
        limitations=["Can be slow on large genomes; requires genome FASTA and Cas-OFFinder."],
        task_tags=["crispr_sgrna_optimization"],
        requires=[ToolDependency(name="Reference genome", detail="FASTA path"), ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["best_sgrna", "best_delta_spec"],
        input_model=tool_wrappers.CrisotOptimizeInput,
        output_model=CrisotOptimizeOutput,
        status=ToolStatus.partial,
    ),
    "score_batch_crispr_off_targets_with_crisot": ToolSpec(
        identity="score_batch_crispr_off_targets_with_crisot",
        display_name="CRISOT batch scoring (CSV)",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/scores",
        capabilities=["Batch calculate CRISOT-Score for sgRNA-target pairs in a CSV."],
        limitations=["Requires CSV with expected column names; does not search genome-wide off-targets."],
        task_tags=["crispr_offtarget_scoring"],
        requires=[ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["scored_csv_filepath"],
        input_model=tool_wrappers.CrisotScoresInput,
        output_model=CrisotScoresOutput,
        status=ToolStatus.partial,
    ),
    "rescore_sgrnas_with_crisot": ToolSpec(
        identity="rescore_sgrnas_with_crisot",
        display_name="CRISOT genome-wide rescore and reranking",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/rescore",
        capabilities=["Rescore and rerank sgRNAs by CRISOT-Score and CRISOT-Spec using Cas-OFFinder genome-wide search."],
        limitations=["Requires reference genome FASTA and Cas-OFFinder installed in service env."],
        task_tags=["crispr_sgrna_rescore"],
        requires=[ToolDependency(name="Reference genome", detail="FASTA path"), ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["rescore_csv_filepath", "sgrna_count"],
        input_model=tool_wrappers.CrisotRescoreInput,
        output_model=CrisotRescoreOutput,
        status=ToolStatus.partial,
    ),
    "predict_crispr_off_target_with_crisot_fp": ToolSpec(
        identity="predict_crispr_off_target_with_crisot_fp",
        display_name="CRISOT-FP XGBoost off-target prediction",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/crisot-fp",
        capabilities=["Predict CRISPR off-target effects using CRISOT-FP molecular interaction fingerprints and XGBoost."],
        limitations=["Requires trained XGBoost models (trained_models.zip unzipped). Supports Circle-seq, Site-seq, and Change-seq models."],
        task_tags=["crispr_offtarget_scoring"],
        requires=[ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["fp_csv_filepath"],
        input_model=tool_wrappers.CrisotFpInput,
        output_model=CrisotFpOutput,
        status=ToolStatus.partial,
    ),
    "generate_crispr_fingerprint_with_crisot": ToolSpec(
        identity="generate_crispr_fingerprint_with_crisot",
        display_name="CRISOT-FP fingerprint encoding",
        version="0.1.0",
        source="https://github.com/bm2-lab/CRISOT",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8011/gen-fp",
        capabilities=["Generate CRISOT-FP molecular interaction fingerprint encoding for a single sgRNA-target pair."],
        limitations=["Input normalization enforces 23-nt sequences."],
        task_tags=["crispr_fingerprint_encoding"],
        requires=[ToolDependency(name="CRISOT microservice", detail="microservices/crisot_service (port 8011)")],
        produces=["fp_csv_filepath"],
        input_model=tool_wrappers.CrisotGenFpInput,
        output_model=CrisotGenFpOutput,
        status=ToolStatus.partial,
    ),
    # sgrna_design INTERFACE LOCK (v0.3.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/sgrna_design_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - docs/tools/design_sgrna_handle_with_crgpt.md
    # 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
    # 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
    # 本次修改的基准日期：2026-04-24。
    "design_sgrna_handle_with_crgpt": ToolSpec(
        identity="design_sgrna_handle_with_crgpt",
        display_name="CRGPT sgRNA handle design",
        version="0.3.0-port8017",
        source="https://github.com/bitguolab/sgrna_design",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8017/design",
        capabilities=[
            "Generate sgRNA handle candidates from a seed sequence.",
            "Supports both MCMC annealing (original sample.py) and naive model.generate modes.",
        ],
        limitations=["Depends on model assets and torch/runtime constraints.", "MCMC mode requires ViennaRNA."],
        task_tags=["sgrna_handle_design"],
        requires=[ToolDependency(name="sgrna_design microservice", detail="microservices/sgrna_design_service (port 8017)")],
        produces=["best_sequence", "output_fasta_filepath", "output_ali_filepath", "summary_json_filepath", "best_log_likelihood"],
        input_model=tool_wrappers.SgRNADesignInput,
        output_model=SgRNADesignOutput,
        status=ToolStatus.partial,
    ),
    "score_sgrna_handle_with_crgpt": ToolSpec(
        identity="score_sgrna_handle_with_crgpt",
        display_name="CRGPT sgRNA handle scoring",
        version="0.2.0-port8017",
        source="https://github.com/bitguolab/sgrna_design",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8017/score",
        capabilities=[
            "Score a single sgRNA handle sequence with CRGPT (nn_score + log_likelihood).",
            "Also returns ViennaRNA structure distance / MFE and constraint mutation count.",
        ],
        limitations=["Depends on model assets and torch/runtime constraints.", "Requires ViennaRNA for structure metrics."],
        task_tags=["sgrna_handle_scoring"],
        requires=[ToolDependency(name="sgrna_design microservice", detail="microservices/sgrna_design_service (port 8017)")],
        produces=["nn_score", "log_likelihood", "structure_distance", "mfe", "constraint_mutation_count"],
        input_model=tool_wrappers.SgRNADesignScoreInput,
        output_model=SgRNADesignScoreOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.3.0): ODesign tool spec. Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: ODesignInferenceInput / run_odesign_inference
    # - microservices/odesign_service/main.py :: ODesignInferenceRequest / ODesignInferenceResponse
    # - docs/tools/run_odesign_inference.md
    "run_odesign_inference": ToolSpec(
        identity="run_odesign_inference",
        display_name="ODesign inference (from JSON)",
        version="0.3.0",
        source="https://github.com/OTeam-AI4S/ODesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8012/design/from-json",
        capabilities=["Run ODesign inference for explicit JSON-defined design tasks."],
        limitations=["Natural-language coverage is limited; complex tasks should prepare JSON explicitly."],
        task_tags=["odesign_inference"],
        requires=[ToolDependency(name="GPU", detail="ODesign inference"), ToolDependency(name="ODesign microservice", detail="microservices/odesign_service (port 8012)")],
        produces=["output_dir", "prediction_filepaths", "sample_names", "run_log_filepath", "error_filepaths"],
        input_model=tool_wrappers.ODesignInferenceInput,
        output_model=ODesignInferenceOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.1.0): ODesign aptamer input JSON builder tool spec.
    # Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: BuildOdesignAptamerInput / build_odesign_aptamer_input_json
    # - agent_core/state.py :: odesign_aptamer_input_* fields
    "build_odesign_aptamer_input_json": ToolSpec(
        identity="build_odesign_aptamer_input_json",
        display_name="ODesign aptamer input JSON builder",
        version="0.1.0",
        source="in-repo utility (no external algorithm)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=["Generate ODesign input JSON for protein-targeted RNA aptamer design."],
        limitations=["Does not validate that the protein structure or hotspot residues are biologically correct."],
        task_tags=["odesign_aptamer_input", "rna_aptamer_design"],
        requires=[],
        produces=["input_json_filepath", "design_config"],
        input_model=tool_wrappers.BuildOdesignAptamerInput,
        output_model=BuildOdesignAptamerOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Build ODesign aptamer input JSON",
                input={
                    "protein_structure_path": "workspace/protein.pdb",
                    "protein_chain_id": "C",
                    "protein_sequence_length": 300,
                    "hotspot_residues": "C/18,C/90",
                    "aptamer_length": 30,
                },
                output_excerpt={"input_json_filepath": "workspace/odesign_aptamer_input_abc123.json"},
            )
        ],
    ),
    # INTERFACE LOCK (v0.1.0): Extract RNA from CIF tool spec.
    # Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: ExtractRnaFromCifInput / extract_rna_sequence_from_cif
    # - agent_core/state.py :: extract_rna_from_cif_* fields
    "extract_rna_sequence_from_cif": ToolSpec(
        identity="extract_rna_sequence_from_cif",
        display_name="Extract RNA sequence from CIF/MMCIF",
        version="0.1.0",
        source="in-repo utility (biopython)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=["Extract RNA sequence from a CIF/MMCIF file using O2' atom detection."],
        limitations=["Requires biopython. Non-standard nucleotides are reported as 'N'."],
        task_tags=["rna_sequence_extraction", "structure_parsing"],
        requires=[ToolDependency(name="biopython", detail="pip install biopython")],
        produces=["sequence", "chain_id", "residue_count", "is_rna", "warnings"],
        input_model=tool_wrappers.ExtractRnaFromCifInput,
        output_model=ExtractRnaFromCifOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Extract RNA from CIF",
                input={"cif_filepath": "workspace/structure.cif"},
                output_excerpt={"sequence": "AUGC...", "chain_id": "A", "residue_count": 50},
            )
        ],
    ),
    # INTERFACE LOCK (v0.1.0): ProteinX protein structure prediction tool spec.
    # Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: ProteinXProteinInput / predict_protein_structure_with_proteinx
    # - microservices/proteinx_service/main.py
    # - agent_core/state.py :: protein_structure_* fields
    "predict_protein_structure_with_proteinx": ToolSpec(
        identity="predict_protein_structure_with_proteinx",
        display_name="ProteinX (Protenix) protein structure prediction",
        version="0.1.0",
        source="https://github.com/bytedance/Protenix",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8022/predict/protein",
        capabilities=["Predict protein 3D structure from sequence using Protenix."],
        limitations=[
            "Requires GPU for inference. MSA disabled by default (use msa_mode='protenix' to enable).",
        ],
        task_tags=["protein_structure_prediction", "proteinx"],
        requires=[
            ToolDependency(name="GPU", detail="Protenix inference"),
            ToolDependency(name="Proteinx microservice", detail="microservices/proteinx_service (port 8022)"),
        ],
        produces=["pdb_filepath", "mean_pae", "mean_plddt", "ranking_confidence", "model_scores"],
        input_model=tool_wrappers.ProteinXProteinInput,
        output_model=ProteinXProteinOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Predict protein structure",
                input={"filepath": "workspace/protein.fa"},
                output_excerpt={"mean_plddt": 85.0, "pdb_filepath": "workspace/prediction/rank_1.pdb"},
            )
        ],
    ),
    # INTERFACE LOCK (predict_rna_protein_complex_with_proteinx v0.1.0)
    # Do NOT modify output fields, types, or descriptions without updating tools.py, state.py, writebacks.py
    "predict_rna_protein_complex_with_proteinx": ToolSpec(
        identity="predict_rna_protein_complex_with_proteinx",
        display_name="ProteinX RNA-protein complex prediction",
        version="0.1.0",
        source="https://github.com/bytedance/Protenix",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8022/predict/complex",
        capabilities=["Predict RNA-protein complex 3D structure using Protenix."],
        limitations=["Requires GPU for inference."],
        task_tags=["rna_protein_complex", "proteinx", "aptamer_design"],
        requires=[
            ToolDependency(name="GPU", detail="Protenix inference"),
            ToolDependency(name="Proteinx microservice", detail="microservices/proteinx_service (port 8022)"),
        ],
        produces=["pdb_filepath", "mean_plddt", "ipTM", "ranking_confidence", "model_scores"],
        input_model=tool_wrappers.ProteinXComplexInput,
        output_model=ProteinXComplexOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Predict RNA-protein complex",
                input={"protein_filepath": "workspace/protein.fa", "rna_filepath": "workspace/rna.fa"},
                output_excerpt={"ipTM": 0.75, "mean_plddt": 82.0, "pdb_filepath": "workspace/complex.cif"},
            )
        ],
    ),
    # INTERFACE LOCK (analyze_rna_protein_interface v0.1.0)
    # Do NOT modify output fields, types, or descriptions without updating tools.py, state.py, writebacks.py
    "analyze_rna_protein_interface": ToolSpec(
        identity="analyze_rna_protein_interface",
        display_name="Analyze RNA-protein interface",
        version="0.1.0",
        source="in-repo utility (biopython + freesasa)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=["Compute interface contacts, buried SASA, H-bonds, and salt bridges from a complex PDB."],
        limitations=["Requires biopython and freesasa. Geometric criteria are approximate."],
        task_tags=["interface_analysis", "aptamer_design", "structure"],
        requires=[
            ToolDependency(name="biopython", detail="pip install biopython"),
            ToolDependency(name="freesasa", detail="pip install freesasa"),
        ],
        produces=["interface_contacts", "buried_sasa", "hydrogen_bonds", "salt_bridges", "interface_area"],
        input_model=tool_wrappers.RnaProteinInterfaceInput,
        output_model=RnaProteinInterfaceOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Analyze interface",
                input={"complex_pdb_filepath": "workspace/complex.pdb", "protein_chain_id": "A", "rna_chain_id": "B"},
                output_excerpt={"interface_contacts": 24, "buried_sasa": 1250.5, "hydrogen_bonds": 8},
            )
        ],
    ),
    # INTERFACE LOCK (v0.1.0): Protein binding hotspot identification tool spec.
    # Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: IdentifyProteinBindingHotspotsInput / identify_protein_binding_hotspots
    # - agent_core/state.py :: hotspot_* fields
    "identify_protein_binding_hotspots": ToolSpec(
        identity="identify_protein_binding_hotspots",
        display_name="Identify protein binding hotspots (RNA aptamer)",
        version="0.1.0",
        source="in-repo utility (freesasa + biopython + DBSCAN)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=[
            "Identify RNA aptamer binding hotspots on protein surface via SASA + basic residue clustering.",
        ],
        limitations=[
            "Requires biopython, freesasa, and scikit-learn.",
            "Hotspot algorithm is heuristic; results should be validated experimentally.",
        ],
        task_tags=["protein_hotspot", "aptamer_design", "sasa"],
        requires=[
            ToolDependency(name="biopython", detail="pip install biopython"),
            ToolDependency(name="freesasa", detail="pip install freesasa"),
            ToolDependency(name="scikit-learn", detail="pip install scikit-learn"),
        ],
        produces=["hotspot_residues", "hotspot_patch_size", "patch_center_coords", "exposed_basic_count"],
        input_model=tool_wrappers.IdentifyProteinBindingHotspotsInput,
        output_model=IdentifyProteinBindingHotspotsOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Identify hotspots on a protein",
                input={"protein_structure_path": "workspace/protein.pdb", "chain_id": "A"},
                output_excerpt={"hotspot_residues": "A/18,A/90,A/79,A/49", "hotspot_patch_size": 4},
            )
        ],
    ),
    # INTERFACE LOCK (v0.1.0): Structure alignment tool spec.
    # Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: StructureAlignmentInput / score_structure_alignment
    # - agent_core/state.py :: structure_rmsd / structure_tm_score fields
    "score_structure_alignment": ToolSpec(
        identity="score_structure_alignment",
        display_name="RNA structure alignment (RMSD + TM-score)",
        version="0.1.0",
        source="in-repo utility (biopython SVDSuperimposer)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=["Compute RMSD and TM-score between two RNA 3D structures."],
        limitations=[
            "Requires biopython. If residue counts differ, only the shorter length is aligned.",
        ],
        task_tags=["structure_alignment", "rmsd", "tm_score"],
        requires=[ToolDependency(name="biopython", detail="pip install biopython")],
        produces=["rmsd", "tm_score", "aligned_residue_count", "superposition_matrix", "warning"],
        input_model=tool_wrappers.StructureAlignmentInput,
        output_model=StructureAlignmentOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Align two RNA structures",
                input={
                    "reference_pdb_filepath": "workspace/ref.pdb",
                    "predicted_pdb_filepath": "workspace/pred.pdb",
                },
                output_excerpt={"rmsd": 2.5, "tm_score": 0.85, "aligned_residue_count": 50},
            )
        ],
    ),
    # RNA sequence metrics (GC content) INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/rna_sequence_metrics_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - agent_core/workflows/mrna_sequence_scoring.py
    #   - agent_core/sequence_utils.py
    #   - agent_core/workflow_baseline_eval.py
    #   - tests/test_compute_rna_sequence_gc_content.py
    "compute_rna_sequence_gc_content": ToolSpec(
        identity="compute_rna_sequence_gc_content",
        display_name="RNA sequence GC content",
        version="0.1.0-port8020",
        source="in-repo microservice (no external algorithm)",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8020/gc-content",
        capabilities=["Compute (G+C)/N from a sequence file (A/U/G/C only after normalization)."],
        limitations=["Ignores non-AUGC characters; does not check biological correctness beyond parsing."],
        task_tags=["sequence_composition", "gc_content"],
        requires=[ToolDependency(name="rna_sequence_metrics microservice", detail="microservices/rna_sequence_metrics_service (port 8020)")],
        produces=["gc_content", "sequence_length", "gc_count", "g_count", "c_count", "input_filepath", "resolved_filepath", "model"],
        input_model=tool_wrappers.RnaGcContentInput,
        output_model=RnaGcContentOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="GC content of a FASTA sequence",
                input={"filepath": "workspace/sequence.fasta"},
                output_excerpt={"gc_content": 0.52, "sequence_length": 150, "gc_count": 78},
            )
        ],
    ),
    "compute_dot_bracket_unpaired_fraction": ToolSpec(
        identity="compute_dot_bracket_unpaired_fraction",
        display_name="Dot-bracket unpaired fraction",
        version="0.1.0-port8020",
        source="in-repo microservice (Vienna/LinearFold-style dot-bracket notation)",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8020/unpaired-fraction",
        capabilities=["Compute count('.')/length for a dot-bracket secondary structure string in a file."],
        limitations=["Structure must use only . ( ) [ ] { } < >; does not validate balanced brackets."],
        task_tags=["rna_secondary_structure", "unpaired_fraction"],
        requires=[ToolDependency(name="rna_sequence_metrics microservice", detail="microservices/rna_sequence_metrics_service (port 8020)")],
        produces=["unpaired_fraction", "structure_length", "dot_count"],
        input_model=tool_wrappers.DotBracketUnpairedFractionInput,
        output_model=DotBracketUnpairedFractionOutput,
        status=ToolStatus.available,
    ),
    # RNA sequence U content INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - microservices/rna_sequence_metrics_service/main.py
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - agent_core/sequence_utils.py
    #   - tests/test_compute_rna_sequence_u_content.py
    #   - rna_agent_system/docs/CONTRIBUTING.md
    "compute_rna_sequence_u_content": ToolSpec(
        identity="compute_rna_sequence_u_content",
        display_name="RNA sequence U content",
        version="0.1.0-port8020",
        source="in-repo microservice (no external algorithm)",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8020/u-content",
        capabilities=["Compute U/N from a sequence file (A/U/G/C only after normalization)."],
        limitations=["Ignores non-AUGC characters; does not check biological correctness beyond parsing."],
        task_tags=["sequence_composition", "u_content"],
        requires=[ToolDependency(name="rna_sequence_metrics microservice", detail="microservices/rna_sequence_metrics_service (port 8020)")],
        produces=["u_fraction", "sequence_length", "u_count", "input_filepath", "resolved_filepath", "model"],
        input_model=tool_wrappers.RnaUContentInput,
        output_model=RnaUContentOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="U content of a FASTA sequence",
                input={"filepath": "workspace/sequence.fasta"},
                output_excerpt={"u_fraction": 0.25, "sequence_length": 12, "u_count": 3},
            )
        ],
    ),
    # CAI for CDS INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - agent_core/sequence_utils.py
    #   - agent_core/data/codon_usage_kazusa.json
    #   - tests/test_compute_cai_for_cds_sequence.py
    #   - rna_agent_system/docs/CONTRIBUTING.md
    "compute_cai_for_cds_sequence": ToolSpec(
        identity="compute_cai_for_cds_sequence",
        display_name="CAI for CDS (Kazusa tables)",
        version="0.1.0",
        source="https://www.kazusa.or.jp/codon/",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=[
            "Compute Codon Adaptation Index (CAI) for a coding sequence using Kazusa codon usage tables.",
            f"Supports built-in tables for {format_cai_species_aliases()}.",
            "Allows custom codon usage tables via JSON file.",
        ],
        limitations=[
            "Input must be a valid CDS (length multiple of 3, AUGC only after normalization).",
            "Stop codons are excluded from the CAI calculation.",
        ],
        task_tags=["cds_codon_metrics", "cai", "codon_usage"],
        requires=[],
        produces=["cai_score", "species", "cds_length_nt", "codon_count", "valid_codons", "invalid_codons", "stop_codons_encountered"],
        input_model=tool_wrappers.CaiForCdsInput,
        output_model=CaiForCdsOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="CAI of a human CDS",
                input={"filepath": "workspace/cds.fa", "species": "human"},
                output_excerpt={"cai_score": 0.85, "species": "Homo sapiens", "codon_count": 100},
            )
        ],
    ),
    # Shuffle CDS junction codons INTERFACE LOCK (v0.1.0) —— 禁止单方面变更
    # 关联文件清单（修改时必须全部同步）：
    #   - agent_core/tools.py
    #   - agent_core/tool_specs.py  ← 本文件
    #   - agent_core/state.py
    #   - tests/test_shuffle_cds_junction_codons.py
    "shuffle_cds_junction_codons": ToolSpec(
        identity="shuffle_cds_junction_codons",
        display_name="Shuffle CDS junction codons",
        version="0.1.0",
        source="in-repo pure computation (no microservice)",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=[
            "Generate synonymous-codon variants at the N- or C-terminus of a CDS.",
            "Preserves amino-acid sequence; weights choices by species codon usage.",
            "Used to alter local RNA structure at 5'UTR-CDS or CDS-3'UTR junctions.",
        ],
        limitations=[
            "Input must be a valid CDS (length multiple of 3, AUGC only).",
            "Only standard genetic code; no custom tables yet.",
            "Variants are sampled stochastically; exact set depends on seed.",
        ],
        task_tags=["cds_design", "codon_optimization", "junction_engineering"],
        requires=[],
        produces=["original_sequence", "junction_end", "shuffled_region_start", "shuffled_region_end", "variants"],
        input_model=tool_wrappers.ShuffleCdsJunctionCodonsInput,
        output_model=ShuffleCdsJunctionCodonsOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Shuffle first 6 codons of a human CDS",
                input={"filepath": "workspace/cds.fa", "junction_end": "n_terminus", "codon_count": 6, "num_variants": 4},
                output_excerpt={"junction_end": "n_terminus", "variants": [{"cai_score": 0.82, "changed_codons": 3}]},
            )
        ],
    ),
    "workflow_demo_echo": ToolSpec(
        identity="workflow_demo_echo",
        display_name="Workflow Demo Echo",
        version="0.1.0",
        source="internal",
        transport=ToolTransport.python_api,
        endpoint="",
        capabilities=[
            "Minimal echo tool for registry/executor smoke tests.",
        ],
        limitations=[
            "Not used by production routing by default.",
            "Does not perform any real RNA computation.",
        ],
        task_tags=["demo", "workflow_test"],
        requires=[],
        produces=["echo", "length"],
        input_model=tool_wrappers.WorkflowDemoEchoInput,
        output_model=WorkflowDemoEchoOutput,
        status=ToolStatus.available,
        examples=[
            ToolExample(
                title="Echo a short string",
                input={"text": "hello"},
                output_excerpt={"echo": "hello", "length": 5},
            )
        ],
    ),
}
