"""Bounded Multi-Module Coordination (BMC) coordinator for full-length mRNA design.

Provides a deterministic, rule-based coordinator that diagnoses inter-module
conflicts in assembled full-length mRNA candidates and broadcasts structured
feedback to affected module agents for iterative refinement.

The coordinator is intentionally NOT an LLM — its decisions are fully auditable,
testable, and grounded in explicit tool-derived thresholds.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from agent_core.workflows.multi_objective import compute_violation

_LOGGER = logging.getLogger("agent_core.workflows.coordinator")

# NOTE (Fig 5b mechanism ablation, docs/MANUSCRIPT.md §7 panel b):
# ``APTAMER_FEEDBACK_MODE`` selects which metrics drive the per-module
# parameter adjustments in ``AptamerCoordinator.broadcast_feedback``.
#   - ``source_aware`` (default): the metrics bundle of the candidate that
#     triggered the worst violation — the existing behavior, unchanged.
#   - ``pool_average``: candidate-pool mean metrics, supplied by the caller
#     via the optional ``pool_metrics`` argument.
# Read once per process at import time; every CLI subprocess re-imports this
# module, so the env var is naturally honoured per run. Any value other than
# ``pool_average`` falls back to ``source_aware``.
_APTAMER_FEEDBACK_MODE = os.environ.get("APTAMER_FEEDBACK_MODE", "source_aware").strip().lower()


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Issue:
    """One diagnosed inter-module conflict.

    ``violation`` is a continuous non-negative distance from the target.
    ``0.0`` means the target is satisfied; larger values mean larger deviation.
    """

    issue_type: str
    value: float
    target: float
    affected_modules: tuple[str, ...]
    evidence: str
    violation: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "value": self.value,
            "target": self.target,
            "violation": self.violation,
            "affected_modules": list(self.affected_modules),
            "evidence": self.evidence,
        }


@dataclass
class ParamAdjustment:
    """A single parameter adjustment for a module agent."""

    param: str
    delta: float
    reason: str = ""


@dataclass
class ModuleFeedback:
    """Structured feedback sent to one module agent."""

    priority: str  # "high" | "medium" | "low"
    adjustments: list[ParamAdjustment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "adjustments": [
                {"param": a.param, "delta": a.delta, "reason": a.reason}
                for a in self.adjustments
            ],
        }


@dataclass
class CoordinationRound:
    """Trace record for one BMC iteration round."""

    round_num: int
    best_candidate_id: str
    best_total_score: float
    issues_found: list[Issue]
    feedback_dispatched: dict[str, ModuleFeedback]
    modules_reinvoked: list[str]
    time_elapsed_ms: float = 0.0
    diagnosis_candidate_ids: list[str] = field(default_factory=list)
    reference_point_mode: str = "utopian"
    reference_point: dict[str, float] = field(default_factory=dict)
    dim_bounds: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "best_candidate_id": self.best_candidate_id,
            "best_total_score": self.best_total_score,
            "issues_found": [i.to_dict() for i in self.issues_found],
            "feedback_dispatched": {
                k: v.to_dict() for k, v in self.feedback_dispatched.items()
            },
            "modules_reinvoked": self.modules_reinvoked,
            "time_elapsed_ms": self.time_elapsed_ms,
            "diagnosis_candidate_ids": self.diagnosis_candidate_ids,
            "reference_point_mode": self.reference_point_mode,
            "reference_point": self.reference_point,
            "dim_bounds": self.dim_bounds,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Reference-Point Full-Length Coordinator
# ─────────────────────────────────────────────────────────────────────────────


class ReferencePointCoordinator:
    """Reference-point driven coordinator for full-length mRNA design.

    Unlike a threshold-based coordinator, this class diagnoses inter-module
    conflicts by measuring how far the current best candidate is from a
    user-provided or auto-derived reference point in normalized objective
    space.  Every objective dimension is min-max normalized to [0, 1] within
    the candidate pool (in maximization space), so gaps are directly comparable.

    The reference point is the single source of truth for both:
      - selecting ``best_candidate`` via Achievement Scalarizing Function, and
      - diagnosing which modules need adjustment during BMC iteration.
    """

    # Score dimensions used for BMC diagnosis.
    # Includes 4 user-facing objectives plus 2 internal junction diagnostics.
    # All dimensions are constructed so that higher values are better
    # (maximization space).
    OBJECTIVES: tuple[str, ...] = (
        "cds_component",
        "utr5_mrl",
        "utr3_stability",
        "full_mfe_score",
        "junction_5utr_cds_score",
        "junction_cds_3utr_score",
    )

    # User-facing objectives exposed in reference_point.
    USER_FACING_OBJECTIVES: tuple[str, ...] = (
        "cds_component",
        "utr5_mrl",
        "utr3_stability",
        "full_mfe_score",
    )

    # Maps each score dimension to the module(s) that can improve it.
    DIMENSION_TO_MODULES: dict[str, tuple[str, ...]] = {
        "cds_component": ("CDS",),
        "full_mfe_score": ("5UTR", "CDS", "3UTR"),
        "utr5_mrl": ("5UTR",),
        "utr3_stability": ("3UTR",),
        "junction_5utr_cds_score": ("5UTR", "CDS"),
        "junction_cds_3utr_score": ("CDS", "3UTR"),
    }

    def diagnose(
        self,
        norm_candidate_vector: dict[str, float],
        reference_point: dict[str, float],
    ) -> list[Issue]:
        """Return issues for dimensions where candidate is below the reference point.

        Args:
            norm_candidate_vector: Normalized objective values for the candidate
                being diagnosed.  Values are in [0, 1] (may be outside for
                ambitious reference points).
            reference_point: Normalized aspiration level per objective.  Missing
                dimensions are ignored.

        Returns:
            List of ``Issue`` objects, each with a continuous ``violation``
            equal to the normalized gap ``reference - candidate``.
        """
        issues: list[Issue] = []

        for dim in self.OBJECTIVES:
            if dim not in reference_point:
                continue
            ref = float(reference_point[dim])
            val = norm_candidate_vector.get(dim)
            if val is None:
                continue
            val = float(val)
            gap = ref - val
            if gap > 0.0:
                modules = self.DIMENSION_TO_MODULES.get(dim, ())
                issues.append(
                    Issue(
                        issue_type=f"{dim.upper()}_BELOW_REFERENCE",
                        value=val,
                        target=ref,
                        violation=gap,
                        affected_modules=modules,
                        evidence=(
                            f"{dim}={val:.4f} is below reference point "
                            f"{ref:.4f} by {gap:.4f}"
                        ),
                    )
                )

        return issues

    # ── Feedback broadcast ───────────────────────────────────────────────────

    def broadcast_feedback(
        self,
        issues: list[Issue],
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, ModuleFeedback]:
        """Map diagnosed issues to module-specific parameter adjustments."""
        feedback: dict[str, ModuleFeedback] = {}

        for issue in issues:
            for module in issue.affected_modules:
                fb = feedback.get(module, ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._module_adjustments(module, issue, metrics))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback[module] = fb

        return feedback

    @staticmethod
    def _higher_priority(a: str, b: str) -> str:
        order = {"low": 0, "medium": 1, "high": 2}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    # ── Per-module adjustment rules ──────────────────────────────────────────

    def _module_adjustments(
        self,
        module: str,
        issue: Issue,
        metrics: dict[str, Any] | None,
    ) -> list[ParamAdjustment]:
        if module == "CDS":
            return self._cds_adjustments(issue, metrics)
        # 5UTR / 3UTR modules intentionally get no parameter adjustments:
        # UTR presets come from the user's explicit ``utr_mode`` and must not
        # be overridden by the coordinator (junction issues are handled by
        # UTR-preset exploration inside the workflow).
        return []

    def _cds_adjustments(
        self,
        issue: Issue,
        metrics: dict[str, Any] | None,
    ) -> list[ParamAdjustment]:
        """CDS adjustments triggered by reference-point gaps.

        Physics reminder: LinearDesign λ is inversely related to MFE stability.
        Lower λ → more negative MFE (more stable structure).
        Higher λ → more weight on CAI.
        """
        if issue.issue_type in (
            "CDS_COMPONENT_BELOW_REFERENCE",
            "FULL_MFE_SCORE_BELOW_REFERENCE",
        ):
            return self._cds_lambda_adjustments(metrics)
        # Everything else (including pure junction issues) gets no CDS
        # adjustment: λ is a global CDS parameter and has little effect on a
        # 40-nt junction.
        return []

    @staticmethod
    def _cds_lambda_adjustments(
        metrics: dict[str, Any] | None,
    ) -> list[ParamAdjustment]:
        """Choose lambda direction based on whether CAI or MFE is the weaker component.

        If raw metrics are unavailable, default to improving stability (lower λ).
        """
        metrics = metrics or {}
        cds_cai = metrics.get("cds_cai")
        cds_mfe = metrics.get("cds_mfe")

        # Normalize gaps to comparable scales using typical ranges.
        # CAI: target ~0.9, bad ~0.5  → gap magnitude up to ~0.4
        # MFE: target ~-50 (score = 50), bad ~-20 (score = 20) → gap up to ~30
        cai_gap = 0.9 - float(cds_cai) if cds_cai is not None else None
        mfe_gap = 50.0 + float(cds_mfe) if cds_mfe is not None else None

        cai_weak = cai_gap is not None and cai_gap > 0.05
        mfe_weak = mfe_gap is not None and mfe_gap > 0.05

        if cai_weak and not mfe_weak:
            return [
                ParamAdjustment(
                    param="lambda_value",
                    delta=+2.0,
                    reason="CDS CAI is below aspiration; increase λ to favor CAI over MFE",
                )
            ]
        if mfe_weak and not cai_weak:
            return [
                ParamAdjustment(
                    param="lambda_value",
                    delta=-2.0,
                    reason="CDS MFE stability is below aspiration; decrease λ to favor MFE over CAI",
                )
            ]
        if cai_weak and mfe_weak:
            # Both are weak: prefer stability because it is usually the harder
            # constraint to satisfy, but also hint that the user may want a
            # different design tool.
            return [
                ParamAdjustment(
                    param="lambda_value",
                    delta=-2.0,
                    reason="Both CDS CAI and MFE are below aspiration; decrease λ to favor MFE, consider switching design_tool",
                )
            ]
        # No clear component gap (e.g. only the combined score is low) →
        # default to stability-oriented adjustment.
        return [
            ParamAdjustment(
                param="lambda_value",
                delta=-2.0,
                reason="CDS component below reference; decrease λ to favor MFE/stability",
            )
        ]

    # ── Convergence helpers ──────────────────────────────────────────────────

    @staticmethod
    def has_converged(
        current_best: float,
        previous_best: float,
        round_num: int,
        max_rounds: int = 3,
        improvement_threshold: float = 1.0,
    ) -> tuple[bool, str]:
        """Return (should_stop, reason).

        Hard stop conditions:
        - round_num >= max_rounds
        - score did not improve by at least improvement_threshold
        - score degraded
        """
        if round_num >= max_rounds:
            return True, f"max_rounds_reached ({max_rounds})"
        improvement = current_best - previous_best
        if improvement < 0:
            return True, f"score_degraded ({improvement:.3f})"
        if improvement < improvement_threshold:
            return True, f"insufficient_improvement ({improvement:.3f} < {improvement_threshold})"
        return False, f"improved ({improvement:.3f})"


# ─────────────────────────────────────────────────────────────────────────────
# Aptamer Coordinator
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AptamerCoordinationRound:
    """Trace record for one aptamer BMC iteration round."""

    round_num: int
    best_candidate_id: str
    best_total_score: float
    issues_found: list[Issue]
    feedback_dispatched: dict[str, ModuleFeedback]
    modules_reinvoked: list[str]
    time_elapsed_ms: float = 0.0
    diagnosis_candidate_ids: list[str] = field(default_factory=list)
    reference_point_mode: str = "utopian"
    reference_point: dict[str, float] = field(default_factory=dict)
    dim_bounds: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "best_candidate_id": self.best_candidate_id,
            "best_total_score": self.best_total_score,
            "issues_found": [i.to_dict() for i in self.issues_found],
            "feedback_dispatched": {
                k: v.to_dict() for k, v in self.feedback_dispatched.items()
            },
            "modules_reinvoked": self.modules_reinvoked,
            "time_elapsed_ms": self.time_elapsed_ms,
            "diagnosis_candidate_ids": self.diagnosis_candidate_ids,
            "reference_point_mode": self.reference_point_mode,
            "reference_point": self.reference_point,
            "dim_bounds": self.dim_bounds,
        }


class AptamerCoordinator:
    """Reference-point driven coordinator for RNA aptamer design.

    Unlike a threshold-based coordinator, this class diagnoses inter-module
    conflicts by measuring how far the current candidate is from a user-provided
    or auto-derived reference point in normalized objective space. Every objective
    dimension is min-max normalized to [0, 1] within the candidate pool
    (in maximization space), so gaps are directly comparable.

    The reference point is the single source of truth for both:
      - selecting ``best_candidate`` via Achievement Scalarizing Function, and
      - diagnosing which modules need adjustment during BMC iteration.
    """

    # Score dimensions used for BMC diagnosis and reference-point optimization.
    OBJECTIVES: tuple[str, ...] = (
        "egarps_component",
        "rhofold_component",
        "iptm_component",
    )

    # All objectives are user-facing for RNA aptamer design.
    USER_FACING_OBJECTIVES: tuple[str, ...] = OBJECTIVES

    # Maps each score dimension to the module(s) that can improve it.
    DIMENSION_TO_MODULES: dict[str, tuple[str, ...]] = {
        "egarps_component": ("Target", "Aptamer"),
        "rhofold_component": ("Aptamer",),
        "iptm_component": ("Target", "Aptamer"),
    }

    def diagnose(
        self,
        norm_candidate_vector: dict[str, float],
        reference_point: dict[str, float],
    ) -> list[Issue]:
        """Return issues for dimensions where candidate is below the reference point.

        Args:
            norm_candidate_vector: Normalized objective values for the candidate
                being diagnosed. Values are in [0, 1] (may be outside for
                ambitious reference points).
            reference_point: Normalized aspiration level per objective. Missing
                dimensions are ignored.

        Returns:
            List of ``Issue`` objects, each with a continuous ``violation``
            equal to the normalized gap ``reference - candidate``.
        """
        issues: list[Issue] = []

        for dim in self.OBJECTIVES:
            if dim not in reference_point:
                continue
            ref = float(reference_point[dim])
            val = norm_candidate_vector.get(dim)
            if val is None:
                continue
            val = float(val)
            gap = ref - val
            if gap > 0.0:
                modules = self.DIMENSION_TO_MODULES.get(dim, ())
                issues.append(
                    Issue(
                        issue_type=f"{dim.upper()}_BELOW_REFERENCE",
                        value=val,
                        target=ref,
                        violation=gap,
                        affected_modules=modules,
                        evidence=(
                            f"{dim}={val:.4f} is below reference point "
                            f"{ref:.4f} by {gap:.4f}"
                        ),
                    )
                )

        return issues

    # ── Feedback broadcast ───────────────────────────────────────────────────

    def broadcast_feedback(
        self,
        issues: list[Issue],
        metrics: dict[str, Any],
        pool_metrics: dict[str, Any] | None = None,
    ) -> dict[str, ModuleFeedback]:
        """Map diagnosed reference-point gaps to module-specific adjustments.

        Args:
            issues: Diagnosed reference-point gaps.
            metrics: Metrics bundle of the candidate that triggered the worst
                violation (source-aware feedback).
            pool_metrics: Optional candidate-pool mean metrics. Only used when
                the ``APTAMER_FEEDBACK_MODE=pool_average`` ablation is active
                (Fig 5b); ignored otherwise, so the default behavior is
                identical to the source-aware path.
        """
        # NOTE (Fig 5b ablation): pool_average mode replaces the worst-violation
        # source metrics with the candidate-pool mean metrics.
        if _APTAMER_FEEDBACK_MODE == "pool_average" and pool_metrics is not None:
            metrics = pool_metrics
        feedback: dict[str, ModuleFeedback] = {}

        for issue in issues:
            for module in issue.affected_modules:
                fb = feedback.get(module, ModuleFeedback(priority="medium"))
                fb.adjustments.extend(self._module_adjustments(module, issue, metrics))
                fb.priority = self._higher_priority(fb.priority, "medium")
                feedback[module] = fb

        return feedback

    @staticmethod
    def _higher_priority(a: str, b: str) -> str:
        order = {"low": 0, "medium": 1, "high": 2}
        return a if order.get(a, 0) >= order.get(b, 0) else b

    # ── Per-module adjustment rules ──────────────────────────────────────────

    def _module_adjustments(
        self,
        module: str,
        issue: Issue,
        metrics: dict[str, Any],
    ) -> list[ParamAdjustment]:
        if module == "Target":
            return self._target_adjustments(issue)
        if module == "Aptamer":
            return self._aptamer_adjustments(issue, metrics)
        return []

    def _target_adjustments(self, issue: Issue) -> list[ParamAdjustment]:
        """Target (hotspot) module adjustments based on reference-point gaps."""
        if issue.issue_type in (
            "EGARPS_COMPONENT_BELOW_REFERENCE",
            "IPTM_COMPONENT_BELOW_REFERENCE",
        ):
            return [
                ParamAdjustment(
                    param="hotspot_expansion",
                    delta=2.0,
                    reason="Expand hotspot window to explore larger binding surface",
                )
            ]
        return []

    def _aptamer_adjustments(
        self,
        issue: Issue,
        metrics: dict[str, Any],
    ) -> list[ParamAdjustment]:
        """Aptamer generation module adjustments based on reference-point gaps."""
        if issue.issue_type == "RHOFOLD_COMPONENT_BELOW_REFERENCE":
            plddt = metrics.get("rhofold_mean_plddt")
            if plddt is not None and plddt < 60.0:
                delta = 10.0
                reason = "RhoFold pLDDT is very low; substantially increase aptamer length"
            else:
                delta = 5.0
                reason = "Increase aptamer length to improve foldability"
            return [
                ParamAdjustment(
                    param="aptamer_length_delta",
                    delta=delta,
                    reason=reason,
                ),
                ParamAdjustment(
                    param="seed_change",
                    delta=0.0,
                    reason="Change random seeds to explore different sequence space",
                ),
            ]
        if issue.issue_type in (
            "EGARPS_COMPONENT_BELOW_REFERENCE",
            "IPTM_COMPONENT_BELOW_REFERENCE",
        ):
            return [
                ParamAdjustment(
                    param="n_samples_delta",
                    delta=5.0,
                    reason="Generate more candidates for diversity",
                ),
                ParamAdjustment(
                    param="seed_change",
                    delta=0.0,
                    reason="Change random seeds to explore different sequence space",
                ),
            ]
        return []

    # ── Convergence helpers ──────────────────────────────────────────────────

    @staticmethod
    def has_converged(
        current_best: float,
        previous_best: float,
        round_num: int,
        max_rounds: int = 3,
        improvement_threshold: float = 1.0,
    ) -> tuple[bool, str]:
        """Return (should_stop, reason).

        Hard stop conditions:
        - round_num >= max_rounds
        - score did not improve by at least improvement_threshold
        - score degraded
        """
        if round_num >= max_rounds:
            return True, f"max_rounds_reached ({max_rounds})"
        improvement = current_best - previous_best
        if improvement < 0:
            return True, f"score_degraded ({improvement:.3f})"
        if improvement < improvement_threshold:
            return True, f"insufficient_improvement ({improvement:.3f} < {improvement_threshold})"
        return False, f"improved ({improvement:.3f})"
