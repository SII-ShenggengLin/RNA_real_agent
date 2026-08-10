"""QualityProfile for aso_target_screening workflow (deterministic)."""

from __future__ import annotations

from agent_core.agents.quality_agent import QualityProfile

ASO_TARGET_SCREENING_QUALITY_PROFILE = QualityProfile(
    workflow_name="aso_target_screening",
    workflow_description="Deterministic ASO target screening",
    evaluation_dimensions=[],
    adjustable_params={},
    retry_strategy="abort_only",
    max_retries=0,
)
