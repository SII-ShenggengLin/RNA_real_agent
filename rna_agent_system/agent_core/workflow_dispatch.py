"""Lightweight task_type classification for RNA workflows (no planner, no DSL).

Used by HTTP ``/v1/workflows/run`` and future CLIs. ``mrna`` is the only implemented type;
others are explicit placeholders until a dedicated workflow module exists.
"""

from __future__ import annotations

from typing import Literal, Optional

# Canonical names (stable API contract).
IMPLEMENTED_TASK_TYPES = frozenset({"mrna"})
PLACEHOLDER_TASK_TYPES = frozenset({"utr5", "utr3", "circrna", "ires", "intron"})
KNOWN_TASK_TYPES = IMPLEMENTED_TASK_TYPES | PLACEHOLDER_TASK_TYPES


class UnknownTaskTypeError(ValueError):
    """Raised when ``task_type`` is not in the known vocabulary."""

    def __init__(self, message: str, *, raw: str, normalized: Optional[str] = None):
        super().__init__(message)
        self.raw = raw
        self.normalized = normalized


class TaskPlaceholderError(ValueError):
    """Raised when ``task_type`` is known but no workflow implementation exists yet."""

    def __init__(self, message: str, *, task_type: str):
        super().__init__(message)
        self.task_type = task_type


def normalize_task_type(raw: str) -> str:
    """Map user/agent strings to canonical task keys."""

    if raw is None or not str(raw).strip():
        return "mrna"
    x = str(raw).strip().lower()
    x = x.replace("'", "").replace("“", "").replace("”", "").replace("-", "").replace("_", "")
    # Common aliases
    if x in {"5utr", "fiveutr", "utr5prime"}:
        return "utr5"
    if x in {"3utr", "threeutr", "utr3prime"}:
        return "utr3"
    if x == "circ":
        return "circrna"
    if x in {"intron", "introns"}:
        return "intron"
    return x


def classify_task_type(raw: str) -> Literal["implemented", "placeholder", "unknown"]:
    """Return lifecycle bucket for dispatch decisions."""

    n = normalize_task_type(raw)
    if n not in KNOWN_TASK_TYPES:
        return "unknown"
    if n in IMPLEMENTED_TASK_TYPES:
        return "implemented"
    return "placeholder"


def assert_dispatchable(raw: str) -> str:
    """Return canonical task_type or raise."""

    bucket = classify_task_type(raw)
    n = normalize_task_type(raw)
    if bucket == "unknown":
        raise UnknownTaskTypeError(
            f"unknown task_type {raw!r}; known={sorted(KNOWN_TASK_TYPES)}",
            raw=str(raw),
            normalized=n,
        )
    if bucket == "placeholder":
        raise TaskPlaceholderError(
            f"task_type {n!r} is planned but not implemented yet",
            task_type=n,
        )
    return n
