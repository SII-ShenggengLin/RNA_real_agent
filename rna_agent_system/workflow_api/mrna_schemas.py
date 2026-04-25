"""HTTP/CLI JSON schemas for RNA workflow APIs (mRNA today; same envelope for other task_type)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MrnaWorkflowHttpRequest(BaseModel):
    """Shared request body for RNA ranking workflows.

    Used by ``POST /v1/workflows/mrna/run`` and ``POST /v1/workflows/run``.
    Exactly one sequence source: ``sequence``, ``sequences``, or ``protein``.
    """

    model_config = ConfigDict(extra="forbid")

    sequence: Optional[str] = Field(default=None, description="Single RNA/DNA coding sequence.")
    sequences: Optional[List[str]] = Field(default=None, description="Multiple sequences (rank together).")
    protein: Optional[str] = Field(
        default=None,
        description="Amino-acid sequence; CDS is produced via LinearDesign tool (needs service on port 8014).",
    )

    task_type: str = Field(default="mrna", description="Reserved for routing; default mrna.")
    task_id: Optional[str] = Field(default=None, description="Optional stable id for tracing (maps to TaskState.task_id).")
    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional workflow knobs: candidate_mode, target_length_nt, gc_service_url, fold_service_url, "
            "lineardesign_service_url, lineardesign_lambda, lineardesign_codon_usage_path, lineardesign_verbose, "
            "run_gc_tool, run_fold_tool, max_synonymous_variants, synonym_source, etc."
        ),
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=256, description="Limit returned ranked candidates.")
    debug: bool = Field(default=False, description="Include trace snippets and exception detail when allowed.")

    @model_validator(mode="after")
    def _one_sequence_source(self) -> MrnaWorkflowHttpRequest:
        seq = self.sequence is not None and str(self.sequence).strip() != ""
        mul = bool(self.sequences)
        prot = self.protein is not None and str(self.protein).strip() != ""
        n = sum(1 for x in (seq, mul, prot) if x)
        if n != 1:
            raise ValueError(
                "Provide exactly one of: non-empty `sequence`, non-empty `sequences`, or non-empty `protein`."
            )
        return self


class CandidateJson(BaseModel):
    """Serializable candidate for API responses."""

    model_config = ConfigDict(extra="allow")

    id: str
    sequence: str
    sequence_type: str = "mrna"
    source: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rank: Optional[int] = None
    status: str = "new"


class ToolCallRecordJson(BaseModel):
    model_config = ConfigDict(extra="allow")

    step_name: str
    tool_name: str
    success: bool
    error: Optional[str] = None
    elapsed_time: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)


class MrnaWorkflowHttpResponse(BaseModel):
    """Normalized workflow response (HTTP and CLI ``--json``)."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    success: bool
    task_type: str = "mrna"
    best_candidate: Optional[Dict[str, Any]] = None
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = Field("", description="Short ``public_summary`` line for dashboards and logs.")
    operational_summary: str = Field(
        "",
        description="Richer counters from workflow (matches ``WorkflowResult.summary`` on disk).",
    )
    artifact_directory: Optional[str] = Field(
        default=None,
        description="Relative path to run folder (request.json / result.json).",
    )
    result_json_path: Optional[str] = Field(default=None, description="Relative path to persisted result.json.")
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    trace: Optional[List[Dict[str, Any]]] = None
    debug_detail: Optional[str] = Field(
        default=None,
        description="Present only when debug=true and an internal error occurred.",
    )


# Alias for unified naming (same payload / validation).
RnaWorkflowHttpRequest = MrnaWorkflowHttpRequest
RnaWorkflowHttpResponse = MrnaWorkflowHttpResponse
