"""Serializable workflow models for iterative candidate-based agent runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolCallRecord(BaseModel):
    """One tool invocation record inside a workflow step."""

    model_config = ConfigDict(extra="allow")

    step_name: str
    tool_name: str
    input_summary: str = ""
    output_summary: str = ""
    success: bool
    error: Optional[str] = None
    elapsed_time: float = 0.0
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)


# Alias for naming aligned with "step log" / trace terminology.
StepRecord = ToolCallRecord


class Candidate(BaseModel):
    """Candidate sequence object shared across design/evaluation/ranking loops."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: f"cand_{uuid4().hex[:12]}")
    sequence: str
    sequence_type: str = "mrna"
    source: str = ""
    scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_records: List[ToolCallRecord] = Field(default_factory=list)
    rank: Optional[int] = None
    status: str = "new"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    def add_tool_record(self, record: ToolCallRecord) -> None:
        """Append one tool record and refresh update timestamp."""

        self.tool_records.append(record)
        self.updated_at = _utc_now()


class TaskState(BaseModel):
    """Task-level state object for iterative workflow execution."""

    model_config = ConfigDict(extra="allow")

    task_id: str = Field(default_factory=lambda: f"task_{uuid4().hex[:12]}")
    task_type: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    candidates: List[Candidate] = Field(default_factory=list)
    best_candidate: Optional[Candidate] = None
    iteration_index: int = 0
    messages: List[str] = Field(default_factory=list)
    logs: List[ToolCallRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    status: str = "created"

    def append_candidate(self, candidate: Candidate) -> None:
        self.candidates.append(candidate)
        self.updated_at = _utc_now()

    def append_log(self, record: ToolCallRecord) -> None:
        self.logs.append(record)
        self.updated_at = _utc_now()

    def update_best_candidate(self, score_key: str, descending: bool = True) -> Optional[Candidate]:
        """Update best candidate according to one score field."""

        ordered = sort_candidates_by_score(self.candidates, score_key=score_key, descending=descending)
        self.best_candidate = ordered[0] if ordered else None
        self.updated_at = _utc_now()
        return self.best_candidate


class WorkflowResult(BaseModel):
    """Final serializable workflow output."""

    model_config = ConfigDict(extra="allow")

    success: bool
    task_id: str
    best_candidate: Optional[Candidate] = None
    all_candidates: List[Candidate] = Field(default_factory=list)
    summary: str = ""
    errors: List[str] = Field(default_factory=list)
    trace: List[ToolCallRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Workflow completion time when run finished successfully or with errors.",
    )
    public_summary: str = Field(
        default="",
        description="Short client-facing line (experiment logs); full detail stays in summary/trace/files.",
    )
    run_artifact_dir: Optional[str] = Field(
        default=None,
        description="Relative directory under repo root where request.json / result.json were written.",
    )
    run_result_json_path: Optional[str] = Field(
        default=None,
        description="Relative path to persisted result.json when persistence is enabled.",
    )


def sort_candidates_by_score(
    candidates: List[Candidate],
    score_key: str,
    descending: bool = True,
) -> List[Candidate]:
    """Return candidates sorted by one score key.

    Candidates missing the score are always placed at the end.
    """

    with_score = [c for c in candidates if score_key in c.scores]
    without_score = [c for c in candidates if score_key not in c.scores]
    ordered = sorted(with_score, key=lambda c: c.scores[score_key], reverse=descending)
    for idx, candidate in enumerate(ordered, start=1):
        candidate.rank = idx
    return ordered + without_score
