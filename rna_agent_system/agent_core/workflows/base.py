"""Base domain workflow abstraction (Layer 2)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from agent_core.workflow_models import Candidate, WorkflowResult

WorkflowInputT = TypeVar("WorkflowInputT")
WorkflowResultT = TypeVar("WorkflowResultT", bound=WorkflowResult)


class BaseDomainWorkflow(ABC, Generic[WorkflowInputT, WorkflowResultT]):
    """Domain-specific multi-step pipeline: generate → evaluate → score → rank.

    Each subclass implements the biological-knowledge container for one RNA
    sub-domain (mRNA design, siRNA design, CRISPR evaluation, …).
    """

    name: str = ""
    description: str = ""
    required_capabilities: list[str] = []

    @abstractmethod
    def generate_candidates(self, inp: WorkflowInputT) -> list[Candidate]:
        """Produce one or more candidate sequences from the workflow input."""
        ...

    @abstractmethod
    def evaluate(self, candidate: Candidate) -> dict[str, Any]:
        """Run Layer-1 capabilities on *candidate* and return raw metrics."""
        ...

    @abstractmethod
    def score(self, metrics: dict[str, Any]) -> dict[str, float]:
        """Turn raw metrics into normalized score components."""
        ...

    def run(self, inp: WorkflowInputT) -> WorkflowResultT:
        """Default orchestration: generate → evaluate → score → rank."""
        candidates = self.generate_candidates(inp)
        for candidate in candidates:
            metrics = self.evaluate(candidate)
            candidate.scores = self.score(metrics)
            candidate.status = "evaluated"
        return self.rank_and_format(candidates)

    @abstractmethod
    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResultT:
        """Sort candidates, pick best, and build a ``WorkflowResult``."""
        ...
