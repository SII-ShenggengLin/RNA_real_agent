"""Shared Pydantic schemas for the calibrated Layer-4 stack.

Implements the data contracts of ``docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md``
§2.2 (SelfModel / DecisionGate / ClaimGate / CaseMemory / AuditTrail).
All components in this package are additive; the legacy agent stack is untouched.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "calibrated_v1"

# CASF four-capability decomposition (design doc §2.2).
CapabilityKind = Literal["scoring", "screening", "ranking", "docking"]
CAPABILITY_KINDS: tuple[str, ...] = ("scoring", "screening", "ranking", "docking")

# verified: passed the profiling threshold on an anchor set;
# failed: profiled and did not pass;
# unprofiled: never measured;
# transferred: migrated from a similar campaign via CaseMemory (confidence downgraded).
CapabilityGrade = Literal["verified", "failed", "unprofiled", "transferred"]


class EvidencePointer(BaseModel):
    """Pointer to the profiling evidence backing a grade or a verdict."""

    kind: Literal["summary_json", "jsonl", "audit_event"]
    path: str
    note: str = ""


class CapabilityAssessment(BaseModel):
    """One capability cell of an (oracle, task_type, target_family) record."""

    grade: CapabilityGrade = "unprofiled"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    metrics: dict[str, float] = Field(default_factory=dict)
    evidence: list[EvidencePointer] = Field(default_factory=list)
    profiled_at: str | None = None
    # Required when grade == "transferred": the campaign the grade migrated from.
    source_case_id: str | None = None
    # The donor cell's grade before transfer (verified/failed), so gates can
    # distinguish a transferred pass from a transferred failure.
    transferred_from_grade: CapabilityGrade | None = None


class CapabilityRecord(BaseModel):
    """SelfModel row: (oracle, task_type, target_family) -> four capability cells."""

    oracle: str
    task_type: str
    target_family: str
    capabilities: dict[str, CapabilityAssessment] = Field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        return (self.oracle, self.task_type, self.target_family)

    def assessment(self, capability: CapabilityKind) -> CapabilityAssessment:
        """Return the cell for *capability*, defaulting to unprofiled."""
        return self.capabilities.get(capability, CapabilityAssessment())


class PlannedAction(BaseModel):
    """One action in an experiment plan, as inspected by DecisionGate."""

    action_id: str
    kind: str
    oracle: str | None = None
    use: Literal[
        "ranking_objective",
        "screening_evaluation",
        "docking_validation",
        "scoring_annotation",
        "none",
    ] = "none"
    estimated_budget: int = 0


class GateDecision(BaseModel):
    """DecisionGate verdict for one PlannedAction."""

    action_id: str
    verdict: Literal["allow", "substitute", "downgrade", "reject", "require_profiling"]
    reason: str = ""
    oracle: str | None = None
    required_capability: CapabilityKind | None = None
    evidence: list[EvidencePointer] = Field(default_factory=list)
    substitute: dict[str, Any] | None = None


class ClaimDependency(BaseModel):
    """One oracle/capability dependency declared for a claim (design doc §2.3 step 2)."""

    oracle: str
    capability: CapabilityKind
    scope: str = ""  # e.g. "absolute" / "within_target_relative"
    # Filled by ClaimGate from the SelfModel; None until adjudicated.
    grade: CapabilityGrade | None = None


# Claim-strength ladder; ClaimGate downgrades along it (design doc §2.3 step 6).
ClaimScope = Literal["absolute", "within_target_relative", "trend_only"]
CLAIM_SCOPE_LADDER: tuple[str, ...] = ("absolute", "within_target_relative", "trend_only")


class Claim(BaseModel):
    """One conclusion candidate submitted to ClaimGate before being written."""

    claim_id: str
    text: str
    claim_type: str = "optimization"
    scope: ClaimScope = "absolute"
    dependencies: list[ClaimDependency] = Field(default_factory=list)


class ClaimVerdict(BaseModel):
    """ClaimGate verdict for one claim."""

    claim_id: str
    verdict: Literal["pass", "downgrade", "reject"]
    reason: str = ""
    dependencies: list[ClaimDependency] = Field(default_factory=list)
    evidence: list[EvidencePointer] = Field(default_factory=list)
    rewritten_text: str | None = None


class CampaignRecord(BaseModel):
    """CaseMemory entry: one campaign's archive (design doc §1.3)."""

    campaign_id: str
    task_type: str
    target_family: str = ""
    target_features: dict[str, float | str] = Field(default_factory=dict)
    profiling_used: list[dict[str, Any]] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)
    outcomes: dict[str, Any] = Field(default_factory=dict)
    verdict: str = ""
    created_at: str = ""


class AuditEvent(BaseModel):
    """One append-only audit-trail event."""

    event_type: Literal[
        "self_model_update",
        "profiling_run",
        "gate_decision",
        "claim_verdict",
        "budget_event",
        # E5 constraint-navigation experiment audit events (added 2026-08-07,
        # extend-only; existing five types unchanged).
        "gate_action_reject",
        "gate_constraint_reject",
        "gate_arbitration_reject",
        "gate_repair_round_limit",
        "repair_round",
        "lineardesign_extra",
        # E6 constraint-navigation experiment audit events (added 2026-08-09,
        # extend-only; existing types unchanged).
        "request_generate",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""
