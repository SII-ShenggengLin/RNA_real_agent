"""QualityProfile for rna_small_molecule_interaction workflow (deterministic)."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

RNA_SMALL_MOLECULE_INTERACTION_QUALITY_PROFILE = QualityProfile(
    workflow_name="rna_small_molecule_interaction",
    workflow_description="Deterministic RNA-small molecule interaction prediction",
    evaluation_dimensions=[],
    adjustable_params={},
    retry_strategy="abort_only",
    max_retries=0,
)
