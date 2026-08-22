"""Strict, auditable tool interface specification layer.

This module is intentionally decoupled from LangChain/LangGraph runtime wiring.
It defines a schema for tool metadata and IO contracts so we can:

- generate docs that match real wrapper behavior
- validate tool inputs/outputs deterministically
- constrain routing/tool selection to supported task boundaries
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field


class ToolTransport(str, Enum):
    http = "http"
    subprocess = "subprocess"
    python_api = "python_api"


class ToolStatus(str, Enum):
    available = "available"
    partial = "partial"
    unavailable = "unavailable"
    mock = "mock"


class ToolKind(str, Enum):
    """Intrinsic nature of a tool — the platform's governance taxonomy.

    Boundary decision (2026-08-18, docs/DECISIONS.md): learned predictors of
    biological outcomes whose scores are consumed as candidate-quality
    evidence are ``predictor`` and carry an ``OracleDescriptor``; thermodynamic
    and algorithmic structure computation (ViennaRNA, LinearFold, BLAST, CAI,
    ...) is ``compute`` — its conventions are established and it is not gated.
    Candidate producers are ``generator``; I/O and formatting helpers are
    ``utility``.
    """

    compute = "compute"
    generator = "generator"
    predictor = "predictor"
    utility = "utility"


class OracleGovernance(str, Enum):
    """How a managed oracle's DecisionGate verdict affects the call.

    ``enforce``: blocked under the enforce runtime policy when the SelfModel
    denies the evidence (grade failed, or unprofiled with no donor).
    ``pending``: reviewed and audited like enforced oracles, but never
    blocked — the profiling campaign (E16+) has not yet delivered a verdict;
    flipping to ``enforce`` happens only when SelfModel records exist.
    """

    enforce = "enforce"
    pending = "pending"


class OracleEvidenceUse(str, Enum):
    """The use a calling workflow makes of the oracle's output."""

    ranking_objective = "ranking_objective"
    screening_evaluation = "screening_evaluation"
    docking_validation = "docking_validation"
    scoring_annotation = "scoring_annotation"


class OracleDescriptor(BaseModel):
    """Declares a tool as a managed predictive oracle (CapGate ontology).

    ``oracle_id`` is the SelfModel key the profiling campaigns record under
    (e.g. ``egarps_native_probability``); ``default_task_type`` is the
    fallback task context until per-callsite task propagation lands.
    """

    model_config = ConfigDict(extra="forbid")

    oracle_id: str = Field(..., description="SelfModel oracle key this tool's evidence is graded under.")
    evidence_use: OracleEvidenceUse = Field(..., description="How calling workflows consume the output.")
    governance: OracleGovernance = Field(..., description="enforce (block on missing evidence) or pending (audit only).")
    default_task_type: str = Field(..., description="Fallback task_type for SelfModel queries.")
    oracle_version: Optional[str] = Field(
        default=None,
        description=(
            "Version of the deployed oracle artifact (microservice) this "
            "descriptor currently pins. Compared against the profiling-time "
            "oracle_version stamped on SelfModel records: a mismatch means the "
            "grades describe a different artifact than the one declared "
            "(warn + audit, never block; DECISIONS (w))."
        ),
    )


class ToolDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Dependency name, e.g. 'GPU', 'ViennaRNA', 'Cas-OFFinder'.")
    detail: Optional[str] = Field(default=None, description="Concrete requirement (paths, versions, etc).")


class ToolExample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    input: Dict[str, Any]
    output_excerpt: Optional[Dict[str, Any]] = None


class ToolSpec(BaseModel):
    """A strict tool interface contract (metadata + IO schemas)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    identity: str = Field(..., description="Stable tool identity, typically matches LangChain tool name.")
    display_name: str = Field(..., description="Human-friendly name.")
    version: str = Field(..., description="Wrapper/microservice version (as implemented in this repo).")
    source: str = Field(..., description="Upstream repo/paper/website (URL or citation string).")

    kind: ToolKind = Field(..., description="Intrinsic nature of the tool (compute / generator / predictor / utility).")
    oracle: Optional[OracleDescriptor] = Field(
        default=None,
        description="Required for predictors whose scores are consumed as candidate-quality "
        "evidence; drives the CapGate managed-oracle set.",
    )

    transport: ToolTransport = Field(..., description="How this tool is invoked in this repo.")
    endpoint: Optional[str] = Field(
        default=None,
        description="HTTP endpoint URL (if transport=http) as used by wrappers (default).",
    )

    capabilities: List[str] = Field(default_factory=list, description="What the tool can do (bounded, concrete).")
    limitations: List[str] = Field(default_factory=list, description="What the tool cannot/should not do.")
    task_tags: List[str] = Field(default_factory=list, description="Tasks this tool is intended to support.")

    requires: List[ToolDependency] = Field(default_factory=list, description="Runtime dependencies/constraints.")
    produces: List[str] = Field(default_factory=list, description="Key output artifacts/fields produced.")

    input_model: Type[BaseModel] = Field(..., description="Pydantic model class for tool inputs.")
    output_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model class for tool outputs (wrapper return payload).",
    )

    error_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model class for structured errors (if implemented).",
    )

    status: ToolStatus = Field(..., description="Current support status in this repository.")
    examples: List[ToolExample] = Field(default_factory=list)

    def input_json_schema(self) -> Dict[str, Any]:
        return self.input_model.model_json_schema()

    def output_json_schema(self) -> Optional[Dict[str, Any]]:
        return self.output_model.model_json_schema() if self.output_model else None
