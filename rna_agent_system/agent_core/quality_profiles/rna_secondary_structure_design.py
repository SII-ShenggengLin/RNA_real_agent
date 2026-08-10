"""QualityProfile for rna_secondary_structure_design workflow."""

from __future__ import annotations

from typing import Any

from agent_core.agents.quality_agent import QualityAgent, QualityProfile


def _build_secondary_structure_prompt(
    context: dict[str, Any], profile: QualityProfile
) -> list[tuple[str, str]]:
    from agent_core.agents.quality_agent import QualityAgent as _QA

    messages = _QA._build_default_prompt(context, profile)
    score_legend = (
        "\n\n## Score Interpretation (CRITICAL)\n"
        "- total_score = structure_distance_ratio (structure_distance / sequence_length). "
        "0.0 means PERFECT structural match, 1.0 means completely different. SMALLER is better.\n"
        "- mfe = raw MFE value in kcal/mol. More negative = more thermodynamically stable.\n"
        "Do NOT assume total_score follows a 0-1 'higher is better' scale. "
        "A total_score of 0.0 is EXCELLENT, not poor."
    )
    parameter_tuning_guidance = (
        "\n\n## Parameter Tuning Guidance (RNA Secondary Structure Design)\n"
        "The default parameters below are carefully tuned and battle-tested. "
        "Only recommend overrides when you have STRONG evidence that a specific parameter directly caused the issue.\n"
        "- repeats=10: This is an empirically sound value for RNAinverse search repeats. "
        "Only increase if ALL candidates consistently show poor structural fidelity (structure_distance_ratio > 0.3).\n"
        "- num_invocations=3: Sufficient to explore most local optima. "
        "Only increase if candidate sequences show very low diversity (most candidates are identical or nearly identical).\n"
        "- function_mode='m' (MFE target): The most stable and reliable mode. "
        "Do NOT switch to 'p' or 'mp' unless the user explicitly requested partition-function-based design, or MFE mode consistently underperforms across multiple retries.\n"
        "- temp_c=37.0: Standard physiological temperature. "
        "Do NOT change unless the user explicitly requests a different temperature.\n"
        "In short: prefer no parameter changes over speculative adjustments."
    )
    modified = list(messages)
    role, content = modified[-1]
    modified[-1] = (role, content + score_legend + parameter_tuning_guidance)
    return modified


RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE = QualityProfile(
    workflow_name="rna_secondary_structure_design",
    workflow_description="Design RNA sequences that fold into a target secondary structure using ViennaRNA RNAinverse",
    evaluation_dimensions=[
        "Structural fidelity is the primary metric. The designed sequence should fold back into the target secondary structure as closely as possible.",
        "Sequence diversity among candidates is important — all candidates should not be identical, which would indicate poor exploration of the sequence space.",
        "MFE (Minimum Free Energy) should indicate reasonable thermodynamic stability. More negative values suggest more stable structures, but excessively negative values may indicate over-stabilization.",
        "Hamming distance from the inverse-fold tool reflects how much the designed sequence deviates from the provided start sequence, if any.",
        "Score semantics: total_score = structure_distance_ratio (distance / length). 0.0 means PERFECT match, 1.0 means completely different. SMALLER is better. mfe is the raw MFE value in kcal/mol; more negative = more stable.",
    ],
    adjustable_params={
        "repeats": {
            "type": "int",
            "hint": "Number of RNAinverse search repeats per invocation. Increase for more candidates and better exploration.",
        },
        "num_invocations": {
            "type": "int",
            "hint": "Number of independent inverse-fold invocations. Higher values explore more local optima.",
        },
        "temp_c": {
            "type": "float",
            "hint": "Temperature in °C for RNAinverse. Adjust if sequences are too stable or unstable.",
        },
        "function_mode": {
            "type": "enum",
            "values": ["m", "p", "mp"],
            "hint": "RNAinverse objective: 'm' = MFE target, 'p' = partition, 'mp' = both. Switch if one mode underperforms.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
    build_prompt=_build_secondary_structure_prompt,
)
