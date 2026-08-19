"""QualityProfile for rna_aptamer_design workflow."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

RNA_APTAMER_QUALITY_PROFILE = QualityProfile(
    workflow_name="rna_aptamer_design",
    workflow_description=(
        "Design RNA aptamers against a protein target using 3D-structure-guided generation. "
        "Candidates are ranked by Achievement Scalarizing Function distance to a "
        "user-provided or auto-derived reference point. "
        "This quality profile focuses on user-intent alignment and exploration strategy, "
        "not threshold enforcement."
    ),
    evaluation_dimensions=[
        "User priority alignment: Check whether the user explicitly prioritized binding affinity over foldability (or vice versa). If so, verify that the reference_point reflects that priority; you handle intent.",
        "Reference point alignment: If the user provided a reference_point, verify that the best candidate is close to it across the specified dimensions. If no reference point was provided, the system uses the utopian point derived from the candidate pool.",
        "Candidate diversity: If all top candidates come from the same ODesign seed or have nearly identical sequences, recommend increasing sample count or changing seeds for broader exploration.",
        "Target suitability: If the protein target is very small or has no obvious binding pockets, flag that the problem may be ill-posed rather than suggesting parameter tweaks.",
        "CRITICAL: Do NOT apply hard thresholds for EGARPS, pLDDT, ipTM, or GC content — the reference-point coordinator already measures gaps in normalized objective space. Focus on whether the results align with the user's stated goals and constraints.",
    ],
    adjustable_params={
        "aptamer_length": {
            "type": "int",
            "min": 10,
            "max": 200,
            "hint": "Desired RNA aptamer length in nucleotides. Adjust if candidates are consistently too short or too long for the target pocket.",
        },
        "n_odesign_samples": {
            "type": "int",
            "min": 1,
            "max": 20,
            "hint": "Number of ODesign samples to generate. Increase if the candidate pool lacks diversity.",
        },
        "odesign_seeds": {
            "type": "list",
            "hint": "Random seeds for ODesign inference. Change to explore different sequence space.",
        },
        "navigation": {
            "type": "bool",
            "hint": "GenNav multi-profile constraint navigation (E14 protocol). Enable when a delivery batch across length profiles (compact/standard/extended) under the pre-registered constraint matrix is wanted instead of a single static gear.",
        },
        "reference_point": {
            "type": "dict",
            "hint": "Optional per-objective aspiration point for ASF selection. Keys: egarps_component, rhofold_component, iptm_component.",
        },
        "hotspot_residues": {
            "type": "str",
            "hint": "Explicit hotspot residues, e.g. 'A/18,A/90'. Use when automatic hotspot identification does not match the intended binding site.",
        },
    },
    retry_strategy="adjust_params",
    max_retries=2,
)
