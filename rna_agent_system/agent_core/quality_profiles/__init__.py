"""Workflow-specific QualityProfile instances."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile
from agent_core.quality_profiles.aso_target_screening import (
    ASO_TARGET_SCREENING_QUALITY_PROFILE,
)
from agent_core.quality_profiles.full_length_mrna_design import (
    FULL_LENGTH_MRNA_QUALITY_PROFILE,
)
from agent_core.quality_profiles.ires_prediction import IRES_QUALITY_PROFILE
from agent_core.quality_profiles.mrna_cds_design import MRNA_CDS_QUALITY_PROFILE
from agent_core.quality_profiles.mrna_sequence_scoring import (
    MRNA_SEQUENCE_SCORING_QUALITY_PROFILE,
)
from agent_core.quality_profiles.rna_aptamer_design import (
    RNA_APTAMER_QUALITY_PROFILE,
)
from agent_core.quality_profiles.rna_secondary_structure_design import (
    RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
)
from agent_core.quality_profiles.rna_small_molecule_interaction import (
    RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
)
from agent_core.quality_profiles.rna_tertiary_structure_design import (
    RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE,
)
from agent_core.quality_profiles.sgrna_design import SGRNA_QUALITY_PROFILE
from agent_core.quality_profiles.sirna_design import SIRNA_QUALITY_PROFILE

QUALITY_PROFILES: dict[str, QualityProfile] = {
    "mrna_cds_design": MRNA_CDS_QUALITY_PROFILE,
    "sirna_design": SIRNA_QUALITY_PROFILE,
    "sgrna_design": SGRNA_QUALITY_PROFILE,
    "ires_prediction": IRES_QUALITY_PROFILE,
    "rna_secondary_structure_design": RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE,
    "rna_tertiary_structure_design": RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE,
    "full_length_mrna_design": FULL_LENGTH_MRNA_QUALITY_PROFILE,
    "rna_aptamer_design": RNA_APTAMER_QUALITY_PROFILE,
    # Deterministic workflows: empty evaluation_dimensions bypass LLM review.
    "mrna_sequence_scoring": MRNA_SEQUENCE_SCORING_QUALITY_PROFILE,
    "aso_target_screening": ASO_TARGET_SCREENING_QUALITY_PROFILE,
    "rna_small_molecule_interaction": RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE,
}

__all__ = [
    "QUALITY_PROFILES",
    "MRNA_CDS_QUALITY_PROFILE",
    "SIRNA_QUALITY_PROFILE",
    "SGRNA_QUALITY_PROFILE",
    "IRES_QUALITY_PROFILE",
    "RNA_SECONDARY_STRUCTURE_QUALITY_PROFILE",
    "RNA_TERTIARY_STRUCTURE_QUALITY_PROFILE",
    "FULL_LENGTH_MRNA_QUALITY_PROFILE",
    "RNA_APTAMER_QUALITY_PROFILE",
    "MRNA_SEQUENCE_SCORING_QUALITY_PROFILE",
    "ASO_TARGET_SCREENING_QUALITY_PROFILE",
    "RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE",
]
