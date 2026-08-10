"""Base domain workflow abstraction (Layer 2)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel

from agent_core.workflow_models import Candidate, WorkflowResult

_LOGGER = logging.getLogger("agent_core.workflows.base")

WorkflowInputT = TypeVar("WorkflowInputT")
WorkflowResultT = TypeVar("WorkflowResultT", bound=WorkflowResult)


class SubWorkflowEvaluator:
    """Wrap a sub-workflow as an evaluator for a sub-sequence portion.

    Extracts a sub-sequence from ``candidate.metadata[sequence_key]``,
    creates a temporary candidate, runs the sub-workflow's ``evaluate()`` on it,
    and returns the metrics. Results are cached by sub-sequence to avoid
    redundant evaluations when the same sub-sequence appears in multiple
    candidates (e.g. same CDS with different UTRs).

    ``key_map`` remaps keys from the sub-workflow output to avoid collisions
    when multiple evaluators produce the same key (e.g. both CDS and full-length
    fold produce ``mfe_kcal_per_mol``). Only mapped keys are returned.

    Not a ``BaseEvaluator`` subclass because it delegates to a workflow rather
    than directly invoking capabilities.
    """

    def __init__(
        self,
        workflow_factory: Callable[[], "BaseDomainWorkflow[Any, Any]"],
        *,
        sequence_key: str = "cds_sequence",
        key_map: dict[str, str] | None = None,
    ):
        self.workflow_factory = workflow_factory
        self.sequence_key = sequence_key
        self.key_map = key_map or {}
        self._cache: dict[str, dict[str, Any]] = {}

    def evaluate(
        self, candidate: Candidate, context: dict[str, Any]
    ) -> dict[str, Any]:
        sub_seq = candidate.metadata.get(self.sequence_key, "")
        if not sub_seq:
            return {}

        # Cache hit
        if sub_seq in self._cache:
            cached = self._cache[sub_seq]
            for k, v in cached.get("_metadata", {}).items():
                if k not in candidate.metadata or candidate.metadata[k] is None:
                    candidate.metadata[k] = v
            return dict(cached.get("_metrics", {}))

        # Cache miss – evaluate via sub-workflow
        workflow = self.workflow_factory()
        parent_state = context.get("workflow_state", {})
        if hasattr(workflow, "_workflow_state"):
            workflow._workflow_state = parent_state

        temp = Candidate(
            sequence=sub_seq,
            sequence_type=candidate.sequence_type,
            source=candidate.source,
            metadata=dict(candidate.metadata),
        )
        metrics = workflow.evaluate(temp)

        # Apply key mapping – only mapped keys are returned
        if self.key_map:
            mapped: dict[str, Any] = {}
            for sub_key, out_key in self.key_map.items():
                if sub_key in metrics:
                    mapped[out_key] = metrics[sub_key]
            metrics = mapped

        # Cache results
        self._cache[sub_seq] = {
            "_metrics": dict(metrics),
            "_metadata": dict(temp.metadata),
        }

        # Merge temp candidate metadata back
        for k, v in temp.metadata.items():
            if k not in candidate.metadata or candidate.metadata[k] is None:
                candidate.metadata[k] = v

        # Merge sub-workflow tool records so trace observability is preserved
        # when a parent workflow delegates evaluation to a child workflow.
        candidate.tool_records.extend(temp.tool_records)

        return dict(metrics)


class BaseDomainWorkflow(ABC, Generic[WorkflowInputT, WorkflowResultT]):
    """Domain-specific multi-step pipeline: generate → evaluate → score → rank.

    Each subclass implements the biological-knowledge container for one RNA
    sub-domain (mRNA design, siRNA design, CRISPR evaluation, …).
    """

    name: str = ""
    description: str = ""
    required_capabilities: list[str] = []
    input_model: Optional[type[BaseModel]] = None

    # Service pre-flight configuration.  Subclasses and callers may toggle these.
    auto_start_services: bool = False
    service_startup_timeout: int = 300

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

    def _ensure_required_services(self) -> tuple[bool, list[str]]:
        """Check (and optionally start) all microservices declared by ``required_capabilities``.

        Returns ``(True, [])`` immediately when ``auto_start_services`` is ``False``
        or when no capability maps to a microservice.  Otherwise it polls health
        endpoints and launches missing services via their ``start.sh`` scripts.
        """
        if not self.auto_start_services:
            return True, []

        # Lazy import avoids a hard dependency for tests and pure-computation workflows.
        from agent_core.services.service_manager import (
            ensure_services_ready,
            get_services_for_capabilities,
        )

        services = get_services_for_capabilities(self.required_capabilities)
        if not services:
            return True, []
        return ensure_services_ready(services, timeout=self.service_startup_timeout)

    def _service_preflight_result(self) -> Optional[WorkflowResult]:
        """Run the service pre-flight and return a failed result if not ready.

        Returns ``None`` when pre-flight passes (or is disabled) so callers can
        continue with the real workflow logic.
        """
        ready, errors = self._ensure_required_services()
        if ready:
            return None
        _LOGGER.error(
            "workflow_service_preflight_failed workflow=%s errors=%s",
            self.name, errors,
        )
        return WorkflowResult(
            success=False,
            task_id="",
            summary=(
                "Workflow pre-flight failed: required microservices are not ready: "
                f"{', '.join(errors)}"
            ),
            errors=errors,
        )

    def run(
        self,
        inp: WorkflowInputT,
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> WorkflowResultT:
        """Default orchestration: generate → evaluate → score → rank."""
        preflight = self._service_preflight_result()
        if preflight is not None:
            return preflight

        try:
            candidates = self.generate_candidates(inp)
        except Exception as exc:
            _LOGGER.exception("workflow_generate_failed workflow=%s error=%s", self.name, exc)
            return WorkflowResult(
                success=False,
                task_id="",
                summary=f"Workflow failed during candidate generation: {exc}",
                errors=[f"{type(exc).__name__}: {exc}"],
            )
        _LOGGER.info("workflow_generated_candidates count=%d workflow=%s", len(candidates), self.name)
        if progress_callback:
            progress_callback({
                "event": "generate_complete",
                "candidate_count": len(candidates),
                "workflow": self.name,
            })

        try:
            for i, candidate in enumerate(candidates):
                _LOGGER.info("workflow_evaluating_candidate idx=%d total=%d workflow=%s", i + 1, len(candidates), self.name)
                metrics = self.evaluate(candidate)
                candidate.scores = self.score(metrics)
                candidate.status = "evaluated"
                if progress_callback:
                    progress_callback({
                        "event": "evaluate_progress",
                        "current": i + 1,
                        "total": len(candidates),
                        "candidate_id": candidate.id,
                        "workflow": self.name,
                    })
        except Exception as exc:
            _LOGGER.exception("workflow_evaluate_failed workflow=%s error=%s", self.name, exc)
            return WorkflowResult(
                success=False,
                task_id="",
                summary=f"Workflow failed during evaluation: {exc}",
                errors=[f"{type(exc).__name__}: {exc}"],
            )

        _LOGGER.info("workflow_evaluation_complete count=%d workflow=%s", len(candidates), self.name)
        result = self.rank_and_format(candidates)
        # Aggregate per-candidate tool records into workflow trace
        for c in candidates:
            result.trace.extend(c.tool_records)
        return result

    def _empty_result(self, summary: str) -> WorkflowResult:
        """Return a standard empty-candidate ``WorkflowResult``."""
        return WorkflowResult(
            success=False,
            task_id="",
            summary=summary,
            errors=["empty_candidate_list"],
        )

    @abstractmethod
    def rank_and_format(self, candidates: list[Candidate]) -> WorkflowResultT:
        """Sort candidates, pick best, and build a ``WorkflowResult``."""
        ...

    def partial_rerun(
        self,
        inp: WorkflowInputT,
        existing_candidates: list[Candidate],
        *,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> Optional[WorkflowResultT]:
        """Re-run evaluate → score → rank on *existing_candidates*.

        This is the default implementation; subclasses may override to handle
        workflow-specific evaluator state (e.g. ``run_fold``, ``run_gc`` flags).
        Returns ``None`` when the workflow does not support partial rerun or
        when an error occurs (caller should fall back to a full re-run).
        """
        preflight = self._service_preflight_result()
        if preflight is not None:
            return preflight

        if not existing_candidates:
            return None
        try:
            for i, candidate in enumerate(existing_candidates):
                _LOGGER.info(
                    "partial_rerun_evaluating idx=%d total=%d workflow=%s",
                    i + 1,
                    len(existing_candidates),
                    self.name,
                )
                metrics = self.evaluate(candidate)
                candidate.scores = self.score(metrics)
                candidate.status = "evaluated"
                if progress_callback:
                    progress_callback({
                        "event": "evaluate_progress",
                        "current": i + 1,
                        "total": len(existing_candidates),
                        "candidate_id": candidate.id,
                        "workflow": self.name,
                    })
            _LOGGER.info(
                "partial_rerun_complete count=%d workflow=%s",
                len(existing_candidates),
                self.name,
            )
            result = self.rank_and_format(existing_candidates)
            for c in existing_candidates:
                result.trace.extend(c.tool_records)
            return result
        except Exception as exc:
            _LOGGER.exception(
                "partial_rerun_failed workflow=%s error=%s", self.name, exc
            )
            return None
