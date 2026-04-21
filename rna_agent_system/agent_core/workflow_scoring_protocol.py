"""Minimal scoring hook for RNA workflows (optional Protocol).

Concrete workflows (e.g. ``mrna_scoring.score_mrna_candidate``) stay as functions today.
Implement this protocol only when a second workflow needs polymorphic scoring.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class RnaWorkflowScorer(Protocol):
    """Maps a metric bundle into component scores + ``total_score``."""

    def score(self, bundle: Mapping[str, Any], **kwargs: Any) -> dict[str, float]:
        """Return keys such as ``total_score`` and optional ``*_component``."""
