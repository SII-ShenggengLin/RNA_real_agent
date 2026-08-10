"""QualityProfile for mrna_sequence_scoring workflow (deterministic)."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

MRNA_SEQUENCE_SCORING_QUALITY_PROFILE = QualityProfile(
    workflow_name="mrna_sequence_scoring",
    workflow_description="Deterministic mRNA sequence scoring",
    evaluation_dimensions=[],
    adjustable_params={},
    retry_strategy="abort_only",
    max_retries=0,
)
