"""QualityProfile for mrna_cds_design workflow."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile
from agent_core.constants.species import (
    DEFAULT_RNARL_MODEL_TYPE,
    RNARL_MODEL_TYPES_LIST,
    format_cai_species_aliases,
)

MRNA_CDS_QUALITY_PROFILE = QualityProfile(
    workflow_name="mrna_cds_design",
    workflow_description="Design mRNA CDS from protein sequence using LinearDesign, RNARL, or GEMORNA",
    evaluation_dimensions=[
        "CAI (Codon Adaptation Index) measures translation efficiency and is species-dependent — always compare against the table for the requested species. For human, platform null-model evidence: random synonymous redraws already average ~0.67 and optimized designs typically reach ~0.8, so a designed human CDS near or below the random baseline signals failed optimization.",
        "MFE (Minimum Free Energy) measures RNA secondary structure stability. More negative = more stable. MFE scales with sequence length — compare MFE per nucleotide when candidates differ in length. Excessively negative MFE may indicate structure that could impede translation.",
        "GC content is reported for reference but does not directly enter the ranking score.",
        "Unpaired fraction is reported for reference but does not directly enter the ranking score.",
        "If RNASTOP overall_stability is available, LOWER values indicate higher predicted stability: it is the mean of predicted reactivity and degradation metrics (report-only diagnostic, not a normalized [0, 1] score).",
        "LinearDesign lambda parameter controls the MFE/CAI tradeoff: lambda=0 gives the best MFE (most stable structure, most negative) but lowest CAI. As lambda increases (input schema caps it at 20, typical values <=10), CAI gradually improves while MFE gradually worsens (becomes less stable). Lambda cannot directly control GC content.",
        "Diversity of design tools matters: if all candidates come from the same tool, consider switching tools for the retry.",
    ],
    adjustable_params={
        "design_tool": {
            "type": "enum",
            "values": ["lineardesign", "rnarl", "gemorna", "all"],
            "hint": "Which design tool to use. 'all' runs all tools. If one tool consistently underperforms, try a specific tool. GEMORNA and RNARL are both balanced; LinearDesign with high lambda favors stability.",
        },
        "lambda_value": {
            "type": "float",
            "min": 0.0,
            "max": 20.0,
            "hint": "LinearDesign MFE/CAI tradeoff parameter. Input schema range [0, 20], typically <=10. lambda=0 gives the best MFE (most stable structure, most negative) but lowest CAI. As lambda increases, CAI gradually improves while MFE gradually worsens. Decrease lambda to improve poor MFE; increase lambda to improve poor CAI. Only effective when design_tool='lineardesign'; design_tool='all' runs the static lambda grid instead.",
        },
        "model_type": {
            "type": "enum",
            "values": RNARL_MODEL_TYPES_LIST,
            "hint": f"RNARL model type. Only these {len(RNARL_MODEL_TYPES_LIST)} types are supported. If the user asks for a species not in this list, fall back to '{DEFAULT_RNARL_MODEL_TYPE}' or switch to GEMORNA/LinearDesign.",
        },
        "cai_species": {
            "type": "str",
            "hint": f"Species for CAI computation. Built-in: {format_cai_species_aliases()}. For other species, provide a custom codon usage table JSON.",
        },
        "navigation": {
            "type": "bool",
            "hint": "GenNav-λ constraint navigation (v1.2.0): replaces the static LinearDesign lambda grid with an adaptive lambda-curve probe and per-profile matrix delivery (expression/stability/balanced). Zero LLM; empty delivery degrades explicitly.",
        },
        "run_fold": {
            "type": "bool",
            "hint": "Whether to run secondary structure folding (ViennaRNA/LinearFold). Disabling skips the fold evaluator — a fast partial retry when fold results look suspicious.",
        },
        "run_gc": {
            "type": "bool",
            "hint": "Whether to run GC content evaluation. Disabling skips the GC evaluator.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    evaluator_only_params={"run_fold", "run_gc"},
    param_to_evaluators={
        "run_fold": ["SecondaryStructureEvaluator", "UnpairedFractionEvaluator"],
        "run_gc": ["GCContentEvaluator"],
    },
)
