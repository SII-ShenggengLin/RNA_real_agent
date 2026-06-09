"""HTTP/CLI JSON schemas for IRES prediction workflow APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_api.mrna_schemas import CandidateJson


class IresWorkflowHttpRequest(BaseModel):
    """Dedicated request body for IRES prediction & validation workflows."""

    model_config = ConfigDict(extra="allow")

    sequence: Optional[str] = Field(
        default=None,
        description="Plain RNA/DNA sequence to screen for IRES elements.",
    )
    sequence_filepath: Optional[str] = Field(
        default=None,
        description="Path to an existing FASTA or plain-sequence file.",
    )
    iresfinder_mode: int = Field(
        default=0,
        ge=0,
        le=2,
        description="IRESfinder mode: 0=full sequence, 1=header-specified subsequence, 2=sliding window.",
    )
    probability_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Probability threshold for labeling a fragment as IRES.",
    )
    window_size: int = Field(
        default=174,
        ge=20,
        le=5000,
        description="Sliding-window size (mode 2 only).",
    )
    step_size: int = Field(
        default=50,
        ge=1,
        le=5000,
        description="Sliding-window step size (mode 2 only).",
    )
    top_n_candidates: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Keep top-N candidate regions after merging.",
    )
    run_structural_validation: bool = Field(
        default=True,
        description="Run ViennaRNA fold + RNAplfold + dot-bracket analysis on each candidate region.",
    )
    task_type: str = Field(default="ires", description="Reserved for routing; default ires.")
    task_id: Optional[str] = Field(default=None, description="Optional stable id for tracing.")
    top_k: Optional[int] = Field(default=None, ge=1, le=256)
    debug: bool = False

    @model_validator(mode="after")
    def _at_least_one_sequence_source(self) -> "IresWorkflowHttpRequest":
        seq = self.sequence is not None and str(self.sequence).strip() != ""
        fp = self.sequence_filepath is not None and str(self.sequence_filepath).strip() != ""
        if not seq and not fp:
            raise ValueError(
                "Provide at least one of: non-empty `sequence` or non-empty `sequence_filepath`."
            )
        return self


class IresWorkflowHttpResponse(BaseModel):
    """Normalized IRES workflow response (HTTP and CLI ``--json``)."""

    model_config = ConfigDict(extra="allow")

    task_id: str
    success: bool
    task_type: str = "ires"
    best_candidate: Optional[CandidateJson] = None
    candidates: List[CandidateJson] = Field(default_factory=list)
    summary: str = ""
    operational_summary: str = ""
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    trace: Optional[List[Dict[str, Any]]] = None
    debug_detail: Optional[str] = None
