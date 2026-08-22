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

from agent_core.tool_interface import (
    OracleDescriptor,
    OracleEvidenceUse,
    OracleGovernance,
    ToolDependency,
    ToolExample,
    ToolKind,
    ToolSpec,
    ToolStatus,
    ToolTransport,
)
from agent_core import tools as tool_wrappers
from agent_core.constants.species import format_cai_species_aliases


class _OutBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class BlastnSearchOutput(_OutBase):
    """BLAST+ blastn search output schema.

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

    """

    input_filepath: str
    output_filepath: str
    generated_sequence: str
    raw_output: str
    model: str


class Gemorna5UtrOutput(_OutBase):
    """GEMORNA 5'UTR design output schema.

    """

    output_filepath: str
    generated_sequence: str
    utr_length: str
    raw_output: str
    model: str


class Gemorna3UtrOutput(_OutBase):
    """GEMORNA 3'UTR design output schema.

    """

    output_filepath: str
    generated_sequence: str
    utr_length: str
    raw_output: str
    model: str


class Gemorna5UtrMrlPredictionOutput(_OutBase):
    """GEMORNA 5'UTR MRL prediction output schema.

    """

    input_filepath: str
    input_sequence: str
    predicted_mrl: float
    model: str


class Gemorna3UtrStabilityPredictionOutput(_OutBase):
    """GEMORNA 3'UTR stability prediction output schema.

    """

    input_filepath: str
    input_sequence: str
    predicted_stability: float
    model: str


class LinearDesignCdsOutput(_OutBase):
    """LinearDesign single-sequence CDS design output schema.

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


# Junction-aware LinearDesign tool (2026-08, additive; v0.2.0 locked schemas above
# are untouched). Mirrors microservices/lineardesign_service/main.py ::
# LinearDesignJunctionAwareResponse.


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

    """

    input_pdb_filepath: str
    output_filepath: str = ""
    output_fasta_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    model: str


class RiboDiffusionOutput(_OutBase):
    """RiboDiffusion tertiary inverse folding output schema.

    """

    input_pdb_filepath: str
    output_filepath: str
    predicted_sequence: str
    recovery_rate: float = 0.0
    checkpoint_path: str
    generated_sequences: list[str] = []
    output_fasta_filepaths: list[str] = []
    model: str


class RNAsmolScoreOutput(_OutBase):
    """RNAsmol scoring output schema.

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

    """
    complex_id: str
    native_probability: float
    academic: bool
    model: str
    pdb_path: str


class RNASTOPPredictionOutput(_OutBase):
    """RNASTOP prediction output schema.

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
    """IRESfinder prediction output schema.

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

    """
    input_json_filepath: str
    design_config: Dict[str, Any]
    model: str


class ExtractRnaFromCifOutput(_OutBase):
    """Extract RNA from CIF output schema.

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


class RnaGcContentOutput(_OutBase):
    """GC content output schema.

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

    """

    input_filepath: str
    resolved_filepath: str
    structure_length: int
    dot_count: int
    unpaired_fraction: float
    model: str


class RnaUContentOutput(_OutBase):
    """U content output schema.

    """

    input_filepath: str
    resolved_filepath: str
    sequence_length: int
    u_count: int
    u_fraction: float
    model: str


class CaiForCdsOutput(_OutBase):
    """CAI output schema for CDS sequences.

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


class WorkflowDemoEchoOutput(_OutBase):
    """Workflow demo echo output schema.

    """

    echo: str
    length: int
    model: str


TOOL_SPECS: Dict[str, ToolSpec] = {
    "compute_sirna_duplex_binding_vienna": ToolSpec(
        identity="compute_sirna_duplex_binding_vienna",
        kind=ToolKind.compute,

        display_name="ViennaRNA duplex cofold (siRNA sense/antisense)",
        version="0.5.0-port8003",
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
        kind=ToolKind.generator,

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
    "run_blastn_similarity_search": ToolSpec(
        identity="run_blastn_similarity_search",
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
        kind=ToolKind.generator,

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
    "predict_rna_secondary_structure_with_linearfold": ToolSpec(
        identity="predict_rna_secondary_structure_with_linearfold",
        kind=ToolKind.compute,

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
    "design_mrna_cds_with_lineardesign": ToolSpec(
        identity="design_mrna_cds_with_lineardesign",
        kind=ToolKind.generator,

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
    "design_mrna_cds_with_rnarl": ToolSpec(
        identity="design_mrna_cds_with_rnarl",
        kind=ToolKind.generator,

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
    "design_mrna_cds_with_gemorna": ToolSpec(
        identity="design_mrna_cds_with_gemorna",
        kind=ToolKind.generator,

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
    "design_5utr_with_gemorna": ToolSpec(
        identity="design_5utr_with_gemorna",
        kind=ToolKind.generator,

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
    "design_3utr_with_gemorna": ToolSpec(
        identity="design_3utr_with_gemorna",
        kind=ToolKind.generator,

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
    "predict_5utr_mrl_with_gemorna": ToolSpec(
        identity="predict_5utr_mrl_with_gemorna",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="gemorna_5utr_mrl",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="full_length_mrna",
        ),

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
    "predict_3utr_stability_with_gemorna": ToolSpec(
        identity="predict_3utr_stability_with_gemorna",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="gemorna_3utr_stability",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="full_length_mrna",
        ),

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
    "predict_rna_tertiary_structure_with_rhofold": ToolSpec(
        identity="predict_rna_tertiary_structure_with_rhofold",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="rhofold_mean_plddt",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="rna_aptamer_design",
        ),

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
    "design_rna_sequence_with_rhodesign": ToolSpec(
        identity="design_rna_sequence_with_rhodesign",
        kind=ToolKind.generator,

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
    "design_rna_inverse_fold_with_ribodiffusion": ToolSpec(
        identity="design_rna_inverse_fold_with_ribodiffusion",
        kind=ToolKind.generator,

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
    "score_rna_ligand_binding_with_rnasmol": ToolSpec(
        identity="score_rna_ligand_binding_with_rnasmol",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="rnasmol",
            evidence_use=OracleEvidenceUse.screening_evaluation,
            governance=OracleGovernance.enforce,
            default_task_type="rna_small_molecule",
        ),

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
    "score_rna_ligand_binding_with_gernabind": ToolSpec(
        identity="score_rna_ligand_binding_with_gernabind",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="gernabind_probability",
            evidence_use=OracleEvidenceUse.screening_evaluation,
            governance=OracleGovernance.enforce,
            default_task_type="rna_small_molecule",
        ),

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
    "score_rna_protein_complex_with_egarps": ToolSpec(
        identity="score_rna_protein_complex_with_egarps",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="egarps_native_probability",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="rna_aptamer_design",
        ),

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
    "predict_mrna_stability_with_rnastop": ToolSpec(
        identity="predict_mrna_stability_with_rnastop",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="rnastop_stability",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="full_length_mrna",
        ),

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
    "predict_putative_ires_with_iresfinder": ToolSpec(
        identity="predict_putative_ires_with_iresfinder",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="iresfinder_score",
            evidence_use=OracleEvidenceUse.screening_evaluation,
            governance=OracleGovernance.enforce,
            default_task_type="ires_prediction",
        ),

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
    "score_crispr_off_target_with_crisot": ToolSpec(
        identity="score_crispr_off_target_with_crisot",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="crisot_off_target_score",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.pending,
            default_task_type="sgrna_design",
        ),

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
        kind=ToolKind.compute,

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
    "design_sgrna_handle_with_crgpt": ToolSpec(
        identity="design_sgrna_handle_with_crgpt",
        kind=ToolKind.generator,

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
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="crgpt_handle_score",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.pending,
            default_task_type="sgrna_design",
        ),

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
    "run_odesign_inference": ToolSpec(
        identity="run_odesign_inference",
        kind=ToolKind.generator,

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
    "build_odesign_aptamer_input_json": ToolSpec(
        identity="build_odesign_aptamer_input_json",
        kind=ToolKind.utility,

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
    "extract_rna_sequence_from_cif": ToolSpec(
        identity="extract_rna_sequence_from_cif",
        kind=ToolKind.utility,

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
    "predict_protein_structure_with_proteinx": ToolSpec(
        identity="predict_protein_structure_with_proteinx",
        kind=ToolKind.predictor,

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
    "predict_rna_protein_complex_with_proteinx": ToolSpec(
        identity="predict_rna_protein_complex_with_proteinx",
        kind=ToolKind.predictor,
        oracle=OracleDescriptor(
            oracle_id="proteinx_ipTM",
            evidence_use=OracleEvidenceUse.ranking_objective,
            governance=OracleGovernance.enforce,
            default_task_type="rna_aptamer_design",
        ),

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
    "analyze_rna_protein_interface": ToolSpec(
        identity="analyze_rna_protein_interface",
        kind=ToolKind.compute,

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
    "identify_protein_binding_hotspots": ToolSpec(
        identity="identify_protein_binding_hotspots",
        kind=ToolKind.compute,

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
    "score_structure_alignment": ToolSpec(
        identity="score_structure_alignment",
        kind=ToolKind.compute,

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
    "compute_rna_sequence_gc_content": ToolSpec(
        identity="compute_rna_sequence_gc_content",
        kind=ToolKind.compute,

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
        kind=ToolKind.compute,

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
    "compute_rna_sequence_u_content": ToolSpec(
        identity="compute_rna_sequence_u_content",
        kind=ToolKind.compute,

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
    "compute_cai_for_cds_sequence": ToolSpec(
        identity="compute_cai_for_cds_sequence",
        kind=ToolKind.compute,

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
    "workflow_demo_echo": ToolSpec(
        identity="workflow_demo_echo",
        kind=ToolKind.utility,

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
