"""Calibrated Layer-4 stack: empirical self-model + dual gating.

Additive package implementing ``docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md``
§2.2. The legacy agent stack (``agent_core/agents/``) is untouched and serves
as the E3 control arm.
"""

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.claim_gate import ClaimGate
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.models import (
    CAPABILITY_KINDS,
    CLAIM_SCOPE_LADDER,
    SCHEMA_VERSION,
    AuditEvent,
    CampaignRecord,
    CapabilityAssessment,
    CapabilityGrade,
    CapabilityKind,
    CapabilityRecord,
    Claim,
    ClaimDependency,
    ClaimVerdict,
    EvidencePointer,
    GateDecision,
    PlannedAction,
)
from agent_core.calibrated.self_model import SelfModel

__all__ = [
    "AuditEvent",
    "AuditTrail",
    "CAPABILITY_KINDS",
    "CLAIM_SCOPE_LADDER",
    "CampaignRecord",
    "CapabilityAssessment",
    "CapabilityGrade",
    "CapabilityKind",
    "CapabilityRecord",
    "Claim",
    "ClaimDependency",
    "ClaimGate",
    "ClaimVerdict",
    "DecisionGate",
    "EvidencePointer",
    "GateDecision",
    "PlannedAction",
    "SCHEMA_VERSION",
    "SelfModel",
]
