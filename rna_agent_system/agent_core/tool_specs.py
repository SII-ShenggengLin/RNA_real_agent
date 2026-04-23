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


class _OutBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class BlastnSearchOutput(_OutBase):
    hit_count: int
    subject_mode: str
    query_filepath: str
    tabular_tsv_filepath: str
    model: str


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


class ViennaFoldOutput(_OutBase):
    input_filepath: str
    structure: str
    mfe_kcal_per_mol: float
    backend: str = ""
    model: str = "ViennaRNA-RNAfold"


class ViennaDuplexOutput(_OutBase):
    input_filepath: str
    sense: str
    antisense: str
    structure: str
    mfe_kcal_per_mol: float
    backend: str = ""
    model: str


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
    backend: str = ""
    model: str


class LinearFoldOutput(_OutBase):
    filepath: str
    sequence: str
    structure: str
    mfe: float
    backend: str = ""
    model: str


class CodonwSlimOutput(_OutBase):
    input_filepath: str
    metrics_json_filepath: str
    cai_score: float
    enc: float
    fop: float
    cbi: float
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


class SgRNADesignOutput(_OutBase):
    input_filepath: str
    best_sequence: str = ""
    best_sequence_filepath: str = ""
    generated_count: int = 0
    best_nn_score: float = 0.0
    best_mutation_count: int = 0
    model_path: str = ""
    output_fasta_filepath: str = ""
    summary_json_filepath: str = ""
    model: str


class ProteinToCdsOutput(_OutBase):
    input_filepath: str
    output_filepath: str
    generated_sequence: str
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


class LinearDesignCdsOutput(_OutBase):
    input_filepath: str
    output_filepath: str
    generated_sequence: str
    structure: str
    mfe: float
    cai_score: float
    lambda_value: float
    codon_usage_path: str
    raw_output: str
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
    - agent_core/nodes.py :: rhofold result ingestion
    - microservices/rhofold_service/main.py :: RhoFoldPredictResponse
    - docs/tools/predict_rna_tertiary_structure_with_rhofold.md
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
    output_fasta_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    model: str


class RiboDiffusionOutput(_OutBase):
    input_pdb_filepath: str
    output_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    model: str


# ═══════════════════════════════════════════════════════════════════════════════
# RNAsmOL 接口冻结声明 (v0.2.0) —— 禁止单方面变更
# ═══════════════════════════════════════════════════════════════════════════════
# 关联文件清单（修改时必须全部同步）：
#   - microservices/rnasmol_service/main.py
#   - agent_core/tools.py
#   - agent_core/tool_specs.py  ← 本文件
#   - agent_core/state.py
#   - agent_core/nodes.py
#   - docs/tools/score_rna_ligand_binding_with_rnasmol.md
# 规则：任何字段增删、函数签名变动、返回值结构调整，必须同时更新上
# 述全部文件并重新跑通端到端测试。违反此规则的提交将被回退。
# ═══════════════════════════════════════════════════════════════════════════════

class RNAsmolScoreOutput(_OutBase):
    """RNAsmol scoring output schema.

    INTERFACE LOCK (v0.2.0): Locked schema. Any field addition/removal must be synchronized with:
    - agent_core/tools.py :: score_rna_ligand_binding_with_rnasmol (wrapper return dict)
    - microservices/rnasmol_service/main.py :: ScoreResponse
    - agent_core/state.py :: rnasmol_* fields
    - docs/tools/score_rna_ligand_binding_with_rnasmol.md
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
    - docs/tools/score_rna_ligand_binding_with_gernabind.md
    """
    input_filepath: str
    smiles: str
    probability_positive: float
    predicted_label: int
    checkpoint_path: str = ""
    preprocessing_pdb_path: str = ""
    model: str


class RNASTOPPredictionOutput(_OutBase):
    """RNASTOP prediction output schema.

    INTERFACE LOCK (v0.1.0): Locked schema. Any field addition/removal must be
    synchronized with:
    - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    - agent_core/tools.py :: predict_mrna_stability_with_rnastop return dict
    - agent_core/nodes.py :: tool_execution_node RNASTOP branch
    - agent_core/state.py :: rnastop_* fields
    - docs/tools/predict_mrna_stability_with_rnastop.md
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


class IRESfinderPredictionOutput(_OutBase):
    input_filepath: str
    result_tsv_filepath: str
    has_putative_ires: bool
    max_score: float
    best_fragment_id: str
    positive_count: int
    fragment_count: int
    model: str


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


class RnaGcContentOutput(_OutBase):
    input_filepath: str
    resolved_filepath: str
    sequence_length: int
    g_count: int
    c_count: int
    gc_count: int
    gc_content: float
    model: str


class DotBracketUnpairedFractionOutput(_OutBase):
    input_filepath: str
    resolved_filepath: str
    structure_length: int
    dot_count: int
    unpaired_fraction: float
    model: str


TOOL_SPECS: Dict[str, ToolSpec] = {
    "compute_sirna_duplex_binding_vienna": ToolSpec(
        identity="compute_sirna_duplex_binding_vienna",
        display_name="ViennaRNA duplex cofold (siRNA sense/antisense)",
        version="0.2.0-port8003",
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
    "design_sirna_with_evitar": ToolSpec(
        identity="design_sirna_with_evitar",
        display_name="Evitar siRNA/Cas13 design",
        version="0.1.0",
        source="https://github.com/dingyaozhang/Evitar",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8016/design",
        capabilities=["Design siRNA/Cas13 guides via Evitar CLI wrapper."],
        limitations=["Upstream binaries are Linux-only (as documented in repo guide)."],
        task_tags=["sirna_design", "cas13_guide_design"],
        requires=[
            ToolDependency(name="Linux", detail="Evitar upstream binaries are Linux executables"),
            ToolDependency(name="Evitar microservice", detail="microservices/evitar_service (port 8016)"),
        ],
        produces=["output_filepath", "top_results"],
        input_model=tool_wrappers.EvitarDesignInput,
        output_model=EvitarDesignOutput,
        status=ToolStatus.partial,
    ),
    "run_blastn_similarity_search": ToolSpec(
        identity="run_blastn_similarity_search",
        display_name="BLAST+ blastn similarity search",
        version="0.1.0",
        source="https://blast.ncbi.nlm.nih.gov/Blast.cgi",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8019/blastn",
        capabilities=["Run blastn search against a subject FASTA or existing BLAST DB."],
        limitations=["Not a siRNA off-target production pipeline by itself; returns alignments/hits only."],
        task_tags=["blastn_similarity_search", "off_target_screening_support"],
        requires=[ToolDependency(name="BLAST+ microservice", detail="microservices/blast_service (port 8019)")],
        produces=["hit_count", "tabular_tsv_filepath"],
        input_model=tool_wrappers.BlastnSearchInput,
        output_model=BlastnSearchOutput,
        status=ToolStatus.partial,
    ),
    "predict_rna_secondary_structure": ToolSpec(
        identity="predict_rna_secondary_structure",
        display_name="ViennaRNA RNAfold (secondary structure)",
        version="0.2.0-port8003",
        source="https://github.com/ViennaRNA/ViennaRNA",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8003/fold",
        capabilities=["Predict secondary structure and MFE for a single RNA sequence."],
        limitations=["Returns thermodynamic MFE only; no experimental constraints unless implemented server-side."],
        task_tags=["rna_secondary_structure_prediction"],
        requires=[ToolDependency(name="ViennaRNA microservice", detail="microservices/viennarna_fold (port 8003)")],
        produces=["structure", "mfe_kcal_per_mol"],
        input_model=tool_wrappers.MrnaToolInput,
        output_model=ViennaFoldOutput,
        status=ToolStatus.available,
    ),
    "compute_aso_target_accessibility_vienna": ToolSpec(
        identity="compute_aso_target_accessibility_vienna",
        display_name="ViennaRNA RNAplfold accessibility (ASO)",
        version="0.2.0-port8003",
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
        version="0.3.0-port8003",
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
        version="0.2.0-port8003",
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
    "predict_rna_secondary_structure_with_linearfold": ToolSpec(
        identity="predict_rna_secondary_structure_with_linearfold",
        display_name="LinearFold secondary structure",
        version="0.1.0-port8015",
        source="https://github.com/LinearFold/LinearFold",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8015/fold",
        capabilities=["Predict RNA secondary structure with linear-time algorithm (beam search)."],
        limitations=["Approximates search with beam; results depend on beam size and parameterization."],
        task_tags=["rna_secondary_structure_prediction"],
        requires=[ToolDependency(name="LinearFold microservice", detail="microservices/linearfold_service (port 8015)")],
        produces=["structure", "mfe"],
        input_model=tool_wrappers.LinearFoldSecondaryInput,
        output_model=LinearFoldOutput,
        status=ToolStatus.available,
    ),
    "design_mrna_cds_with_lineardesign": ToolSpec(
        identity="design_mrna_cds_with_lineardesign",
        display_name="LinearDesign protein→CDS design",
        version="0.1.0-port8014",
        source="https://github.com/LinearDesignSoftware/LinearDesign",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8014/generate/cds",
        capabilities=["Generate CDS sequence from protein sequence via LinearDesign binary wrapper."],
        limitations=["Requires server-side compiled binaries and compatible runtime environment."],
        task_tags=["protein_to_cds_design"],
        requires=[ToolDependency(name="Linux", detail="Documented deployment target"), ToolDependency(name="LinearDesign microservice", detail="microservices/lineardesign_service")],
        produces=["output_filepath", "generated_sequence"],
        input_model=tool_wrappers.LinearDesignCdsInput,
        output_model=LinearDesignCdsOutput,
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
        version="0.1.0",
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
        version="0.1.0",
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
        version="0.1.0",
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
    # INTERFACE LOCK (v0.2.0): RhoFold tool spec. Locked contract. Modify only in sync with:
    # - agent_core/tools.py :: RhoFoldInput / predict_rna_tertiary_structure_with_rhofold
    # - agent_core/tool_specs.py :: RhoFoldOutput
    # - microservices/rhofold_service/main.py :: RhoFoldPredictRequest / RhoFoldPredictResponse
    # - agent_core/nodes.py :: rhofold result ingestion
    # - docs/tools/predict_rna_tertiary_structure_with_rhofold.md
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
        version="0.1.0",
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
    "design_rna_inverse_fold_with_ribodiffusion": ToolSpec(
        identity="design_rna_inverse_fold_with_ribodiffusion",
        display_name="RiboDiffusion tertiary inverse folding",
        version="0.1.0",
        source="https://github.com/ml4bio/RiboDiffusion",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8021/design/from-pdb",
        capabilities=[
            "Sample RNA sequences conditioned on PDB tertiary structure via diffusion (inverse folding).",
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
        produces=["output_filepath", "predicted_sequence", "recovery_rate"],
        input_model=tool_wrappers.RiboDiffusionInput,
        output_model=RiboDiffusionOutput,
        status=ToolStatus.partial,
    ),
    # INTERFACE LOCK (v0.2.0) — RNAsmol scoring tool spec
    # Any field addition/removal must be synchronized with:
    # - microservices/rnasmol_service/main.py :: ScoreRequest / ScoreResponse
    # - agent_core/tools.py :: RNAsmolScoreInput / score_rna_ligand_binding_with_rnasmol
    # - agent_core/tool_specs.py :: RNAsmolScoreOutput
    # - agent_core/state.py :: rnasmol_* fields
    # - docs/tools/score_rna_ligand_binding_with_rnasmol.md
    "score_rna_ligand_binding_with_rnasmol": ToolSpec(
        identity="score_rna_ligand_binding_with_rnasmol",
        display_name="RNAsmol RNA-ligand scoring",
        version="0.2.0",
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
    # - docs/tools/score_rna_ligand_binding_with_gernabind.md
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
    # INTERFACE LOCK (v0.1.0) — predict_mrna_stability_with_rnastop
    # Any field addition/removal in produces[] or capability strings must be
    # synchronized with:
    # - microservices/rnastop_service/main.py :: StabilityPredictionResponse
    # - agent_core/tools.py :: predict_mrna_stability_with_rnastop return dict
    # - agent_core/nodes.py :: tool_execution_node RNASTOP branch
    # - agent_core/state.py :: rnastop_* fields
    # - docs/tools/predict_mrna_stability_with_rnastop.md
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
        limitations=["This repo wrapper exposes prediction only (not beam/MCTS optimization)."],
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
    "predict_putative_ires_with_iresfinder": ToolSpec(
        identity="predict_putative_ires_with_iresfinder",
        display_name="IRESfinder prediction",
        version="0.1.0",
        source="https://github.com/xiaofengsong/IRESfinder",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8013/predict",
        capabilities=["Predict putative IRES elements over sliding fragments (service-side)."],
        limitations=["Requires model/data assets present on server."],
        task_tags=["ires_prediction"],
        requires=[ToolDependency(name="IRESfinder microservice", detail="microservices/iresfinder_service (port 8013)")],
        produces=["result_tsv_filepath", "max_score", "positive_count"],
        input_model=tool_wrappers.IRESfinderPredictionInput,
        output_model=IRESfinderPredictionOutput,
        status=ToolStatus.partial,
    ),
    "analyze_cds_codon_metrics_with_codonw_slim": ToolSpec(
        identity="analyze_cds_codon_metrics_with_codonw_slim",
        display_name="codonw-slim CDS metrics",
        version="0.1.0",
        source="https://github.com/smsaladi/codonw-slim",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8018/analyze/cds",
        capabilities=["Compute codon usage metrics (CAI/Fop/CBI/ENC) and optional tables."],
        limitations=["Requires in-frame CDS input; metrics depend on reference tables/options."],
        task_tags=["cds_codon_metrics"],
        requires=[ToolDependency(name="codonw-slim microservice", detail="microservices/codonw_slim_service (port 8018)")],
        produces=["cai_score", "metrics_json_filepath"],
        input_model=tool_wrappers.CodonwSlimAnalyzeInput,
        output_model=CodonwSlimOutput,
        status=ToolStatus.partial,
    ),
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
        version="0.1.0",
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
    "design_sgrna_handle_with_crgpt": ToolSpec(
        identity="design_sgrna_handle_with_crgpt",
        display_name="CRGPT sgRNA handle design",
        version="0.1.0-port8017",
        source="https://github.com/bitguolab/sgrna_design",
        transport=ToolTransport.http,
        endpoint="http://127.0.0.1:8017/design",
        capabilities=["Generate sgRNA handle candidates from a seed sequence."],
        limitations=["Depends on model assets and torch/runtime constraints."],
        task_tags=["sgrna_handle_design"],
        requires=[ToolDependency(name="sgrna_design microservice", detail="microservices/sgrna_design_service (port 8017)")],
        produces=["best_sequence", "output_fasta_filepath"],
        input_model=tool_wrappers.SgRNADesignInput,
        output_model=SgRNADesignOutput,
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
        produces=["gc_content", "sequence_length", "gc_count"],
        input_model=tool_wrappers.RnaGcContentInput,
        output_model=RnaGcContentOutput,
        status=ToolStatus.available,
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
}

