"""QualityProfile for sgrna_design workflow."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

SGRNA_QUALITY_PROFILE = QualityProfile(
    workflow_name="sgrna_design",
    workflow_description="Design sgRNA handle candidates using CRGPT with optional CRISOT off-target scoring",
    evaluation_dimensions=[
        "CRGPT nn_score is perplexity (lower is better, range ~[1, +inf)). Values close to 1.0 indicate excellent on-target activity; values above 3.0 suggest poor quality.",
        "CRISOT score should indicate low off-target potential. Higher is generally better.",
        "Sequence diversity among candidates is important — if all candidates are very similar, the search may be stuck in a local optimum.",
        "Mutation count should be reasonable relative to the seed sequence — too many mutations may destabilize the structure.",
        "MFE (Minimum Free Energy) from structure prediction should indicate a stable secondary structure.",
    ],
    adjustable_params={
        "n_samples": {
            "type": "int",
            "min": 1,
            "max": 200,
            "hint": "Number of CRGPT samples to generate. Increase to explore more sequence space.",
        },
        "mutation_number": {
            "type": "int",
            "min": 1,
            "max": 40,
            "hint": "Number of positions to mutate. Higher values increase diversity but may reduce structural stability.",
        },
        "temperature": {
            "type": "float",
            "min": 0.0,
            "max": 100.0,
            "hint": "MCMC annealing temperature (mcmc mode) or transformer sampling temperature (naive mode). Higher = more diverse but potentially lower quality.",
        },
        "sampling_mode": {
            "type": "enum",
            "values": ["mcmc", "naive"],
            "hint": "Sampling strategy. 'mcmc' uses Monte Carlo search for better exploration; 'naive' uses direct transformer sampling.",
        },
        "max_overlap": {
            "type": "int",
            "min": 1,
            "max": 60,
            "hint": "Maximum overlap between consecutive mutations. Lower = more independent mutations.",
        },
        "evaluate_crgpt_score": {
            "type": "bool",
            "hint": "Whether to re-score with CRGPT. Keep True for accurate scoring.",
        },
        "evaluate_crisot": {
            "type": "bool",
            "hint": "Whether to run CRISOT off-target scoring. Keep True if guide and target sequences are provided.",
        },
        "weight_nn_score": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for CRGPT nn_score in composite scoring. Increase to prioritize on-target activity.",
        },
        "weight_crisot": {
            "type": "float",
            "min": 0.0,
            "max": 1.0,
            "hint": "Weight for CRISOT score in composite scoring. Increase to prioritize off-target safety.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)
