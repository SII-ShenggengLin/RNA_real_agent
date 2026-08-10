"""Calibrated Layer-4 stack: empirical self-model + dual gating.

Additive package implementing ``docs/REDESIGN_2026-08-03_CALIBRATED_AGENT.md``
§2.2. The legacy agent stack (``agent_core/agents/``) is untouched and serves
as the E3 control arm.
"""

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.campaign_runner import CalibratedCampaignRunner, CampaignResult
from agent_core.calibrated.case_memory import CaseMemory
from agent_core.calibrated.claim_gate import ClaimGate
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.experiment_planner import (
    CampaignDeclaration,
    ExperimentPlanner,
    ProfilingSpec,
)
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
from agent_core.calibrated.profiler import CapabilityProfiler, ProfileRequest
from agent_core.calibrated.self_model import SelfModel

__all__ = [
    "AuditEvent",
    "AuditTrail",
    "CAPABILITY_KINDS",
    "CLAIM_SCOPE_LADDER",
    "CalibratedCampaignRunner",
    "CampaignDeclaration",
    "CampaignRecord",
    "CampaignResult",
    "CapabilityAssessment",
    "CapabilityGrade",
    "CapabilityKind",
    "CapabilityProfiler",
    "CapabilityRecord",
    "CaseMemory",
    "Claim",
    "ClaimDependency",
    "ClaimGate",
    "ClaimVerdict",
    "DecisionGate",
    "EvidencePointer",
    "ExperimentPlanner",
    "GateDecision",
    "PlannedAction",
    "ProfileRequest",
    "ProfilingSpec",
    "SCHEMA_VERSION",
    "SelfModel",
]
