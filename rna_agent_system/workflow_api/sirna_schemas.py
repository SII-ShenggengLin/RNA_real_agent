"""HTTP/CLI JSON schemas for siRNA workflow APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_api.mrna_schemas import CandidateJson


class SirnaWorkflowHttpRequest(BaseModel):
    """Dedicated request body for siRNA design workflows.

    Supports antiviral (Evitar-based) and generic (sliding-window) modes.
    """

    model_config = ConfigDict(extra="allow")

    mode: Literal["antiviral", "generic"] = "generic"
    target_sequence: Optional[str] = Field(
        default=None,
        description="Plain RNA/DNA target sequence (generic mode primary).",
    )
    target_fasta_path: Optional[str] = Field(
        default=None,
        description="FASTA filepath (antiviral mode primary; generic fallback).",
    )
    candidate_count: int = Field(default=10, ge=1, le=100)
    species: str = Field(
        default="homo_sapiens",
        description="Species ID for auto-resolving default transcriptome.",
    )
    off_target_scan: bool = True
    transcriptome_fasta_path: Optional[str] = None
    evitar_mode: Literal["existing", "predesign"] = Field(
        default="existing",
        description="Evitar mode. Only used when mode='antiviral'. "
                    "'existing' for known-virus design; 'predesign' for future-virus pre-design.",
    )
    evitar_predict: Literal["predsi", "rnaxs", "multifapredsi", "CRISPR"] = Field(
        default="predsi",
        description="Evitar prediction algorithm. Only used when mode='antiviral'. "
                    "'CRISPR' is for Cas13 guide design.",
    )
    task_type: str = Field(default="sirna", description="Reserved for routing; default sirna.")
    task_id: Optional[str] = Field(default=None, description="Optional stable id for tracing.")
    top_k: Optional[int] = Field(default=None, ge=1, le=256)
    debug: bool = False

    @model_validator(mode="after")
    def _at_least_one_target(self) -> "SirnaWorkflowHttpRequest":
        seq = self.target_sequence is not None and str(self.target_sequence).strip() != ""
        fasta = self.target_fasta_path is not None and str(self.target_fasta_path).strip() != ""
        if not seq and not fasta:
            raise ValueError(
                "Provide at least one of: non-empty `target_sequence` or non-empty `target_fasta_path`."
            )
        return self


class SirnaWorkflowHttpResponse(BaseModel):
    """Normalized siRNA workflow response (HTTP and CLI ``--json``)."""

    model_config = ConfigDict(extra="allow")

    task_id: str
    success: bool
    task_type: str = "sirna"
    best_candidate: Optional[CandidateJson] = None
    candidates: List[CandidateJson] = Field(default_factory=list)
    summary: str = ""
    operational_summary: str = ""
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    trace: Optional[List[Dict[str, Any]]] = None
    debug_detail: Optional[str] = None
