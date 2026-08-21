"""Ranking governance: assemble ASF objective sets from CapGate verdicts.

Implements ``docs/RANKING_GOVERNANCE.md`` (DECISIONS (p), 2026-08-21): the
shared ASF ranking layer consumes the DecisionGate verdict as a first-class
input. A dimension backed by an oracle without verified (or
transferred-verified) ranking power is demoted to ``scoring_annotation`` —
excluded from the ASF for the whole pool equally — *before*
``apply_reference_point_ranking`` runs, instead of being steered by an
enforced tool-call block (workflow-level failure or silent arbitrary order)
or left ranking in advisory (contradicting the oracle's falsified profile).

Assembly is **mode-independent**: it never reads ``RNADA_CAPGATE`` or the
runtime policy, so advisory and enforce produce the same ranking wherever
SelfModel records exist; the modes differ only in whether annotation values
were actually computed (enforce blocks demoted calls → annotation ``gated``).

Verdict → action mapping (``_review`` reuses DecisionGate semantics so
assembly and tool-call gating can never disagree about a record):

- ``allow``                (verified)              → keep
- ``downgrade``            (transferred-verified)  → keep + ``transferred`` flag
- ``reject``               (failed, direct or
                            transferred failure)    → demote to annotation
- ``require_profiling``    (unprofiled)            → governance-dependent:
  pending (registered campaign, e.g. CRISOT-Score / CRGPT)  → keep + ``pending``
  enforce-governed without records                          → keep + ``unprofiled``
  (no verdict exists; demoting would punish without evidence. Known
  divergence: enforce-mode tool-call blocking still drops the dimension at
  measurement time — RANKING_GOVERNANCE.md §8.2.)

Deterministic; no LLM. The ``RNADA_CAPGATE=off`` escape hatch disables the
whole mechanism (all-keep, no state flags).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.models import GateDecision, PlannedAction
from agent_core.calibrated.runtime import (
    MANAGED_ORACLE_TOOLS,
    ORACLE_GOVERNANCE,
    CalibratedRuntime,
)
from agent_core.calibrated.self_model import SelfModel

# Dims without a ref (deterministic compute per the DECISIONS (j) ontology)
# never enter the mechanism; they are always kept.


@dataclass(frozen=True)
class ObjectiveRef:
    """One oracle-backed ASF dimension and its evidence source."""

    dim: str
    tool_name: str
    oracle_id: str


@dataclass
class AssembledObjectives:
    """Outcome of :func:`assemble_ranking_objectives`.

    ``ranking_dims`` preserves the caller's objective order; ``demoted`` maps
    a demoted dim to the DecisionGate's verdict reason (human-readable
    annotation for the state writeback). ``degrade_reason`` is set iff no
    dimension survives — the workflow must then deliver the
    ``ranking_evidence_unavailable`` degrade (RANKING_GOVERNANCE.md §3.6).
    """

    ranking_dims: list[str] = field(default_factory=list)
    kept_flags: dict[str, str] = field(default_factory=dict)
    demoted: dict[str, str] = field(default_factory=dict)
    degrade_reason: Optional[str] = None
    governance: str = "self_model"

    def to_state(self) -> dict:
        """Serializable form for ``_state_writeback["_ranking_governance"]``."""
        return {
            "governance": self.governance,
            "ranking_dims": list(self.ranking_dims),
            "kept_flags": dict(self.kept_flags),
            "demoted": dict(self.demoted),
            "degrade_reason": self.degrade_reason,
        }


def review_oracle_use(
    tool_name: str,
    use: str,
    self_model: SelfModel,
    task_type: str,
    target_family: str = "default",
) -> Optional[GateDecision]:
    """DecisionGate verdict for one (tool, use) under the calling task type.

    Pure query — no contextvars, no policy, no side effects. Returns ``None``
    when the tool is not a managed oracle (deterministic compute never gates).
    """
    managed = MANAGED_ORACLE_TOOLS.get(tool_name)
    if managed is None:
        return None
    oracle_id = managed[0]
    action = PlannedAction(
        action_id=f"assemble:{tool_name}",
        kind="ranking_dim",
        oracle=oracle_id,
        use=use,  # type: ignore[arg-type]
    )
    decision = DecisionGate(self_model).review(
        [action], task_type=task_type, target_family=target_family
    )
    return decision[0]


def assemble_ranking_objectives(
    objectives: list[str],
    refs: dict[str, ObjectiveRef],
    self_model: SelfModel,
    task_type: str,
    target_family: str = "default",
    *,
    governance: Optional[dict[str, str]] = None,
    use: str = "ranking_objective",
) -> AssembledObjectives:
    """Assemble the ASF objective set from CapGate verdicts.

    Args:
        objectives: The workflow's ordered objective dimensions.
        refs: Oracle-backed dims only, keyed by dimension. Dims absent from
            ``refs`` are deterministic compute (DECISIONS (j)) and always kept.
        self_model: The SelfModel to query (conservative default-family
            transfer semantics apply).
        task_type: The calling workflow's task type (never the oracle's
            registered default; DECISIONS (k)).
        target_family: Defaults to ``"default"`` — deliberately, so the
            SelfModel's worst-grade-across-families transfer (anti-cherry-
            pick rule) adjudicates.
        governance: Tool-name → ``enforce`` | ``pending`` table; defaults to
            the ToolSpec-derived ``ORACLE_GOVERNANCE``.
        use: The declared evidence use of the dims (``ranking_objective``
            for ASF dimensions).

    Returns:
        An :class:`AssembledObjectives`; ``ranking_dims`` is the filtered
        objective list to hand to ``apply_reference_point_ranking``.
    """
    gov = ORACLE_GOVERNANCE if governance is None else governance
    result = AssembledObjectives()
    for dim in objectives:
        ref = refs.get(dim)
        if ref is None:
            result.ranking_dims.append(dim)
            continue
        decision = review_oracle_use(
            ref.tool_name, use, self_model, task_type, target_family
        )
        if decision is None or decision.verdict == "allow":
            result.ranking_dims.append(dim)
        elif decision.verdict == "downgrade":
            result.ranking_dims.append(dim)
            result.kept_flags[dim] = "transferred"
        elif decision.verdict == "reject":
            result.demoted[dim] = decision.reason
        else:  # require_profiling: unprofiled under this task key
            result.ranking_dims.append(dim)
            result.kept_flags[dim] = (
                "pending" if gov.get(ref.tool_name) == "pending" else "unprofiled"
            )
    if objectives and not result.ranking_dims:
        result.degrade_reason = (
            "all ranking objectives demoted to scoring_annotation by CapGate "
            "verdicts; no evidence-based ordering is available"
        )
    return result


def assemble_for_workflow(
    objectives: list[str],
    refs: dict[str, ObjectiveRef],
    task_type: str,
    target_family: str = "default",
) -> AssembledObjectives:
    """Workflow-side entry point: assemble against the live runtime.

    With no runtime installed (``RNADA_CAPGATE=off``) every dimension is kept
    and the state marks ``governance: off`` — the escape hatch disables the
    whole mechanism, not just the blocking. Emits one
    ``ranking_objective_assembly`` audit event per call (best-effort, never
    raises).
    """
    runtime = CalibratedRuntime.instance()
    if runtime is None:
        return AssembledObjectives(
            ranking_dims=list(objectives), governance="off"
        )
    assembled = assemble_ranking_objectives(
        objectives, refs, runtime.self_model, task_type, target_family
    )
    try:
        runtime.audit.record(
            "ranking_objective_assembly",
            {
                "task_type": task_type,
                "target_family": target_family,
                "ranking_dims": assembled.ranking_dims,
                "kept_flags": assembled.kept_flags,
                "demoted": assembled.demoted,
                "degrade_reason": assembled.degrade_reason,
            },
        )
    except Exception:  # noqa: BLE001 - audit must never fail a run
        pass
    return assembled


def screening_filter_demoted(
    tool_name: str, task_type: str, target_family: str = "default"
) -> bool:
    """True when the tool's ``screening_evaluation`` verdict is a rejection.

    Used by in-pipeline filters (e.g. the aptamer light-stage RhoFold pLDDT
    top-k gate, RANKING_GOVERNANCE.md §3.5): a failed screening profile must
    not arbitrate candidate selection — the caller degrades to deterministic
    pool order. Mode-independent; ``False`` when governance is off or the
    tool is not a managed oracle.
    """
    runtime = CalibratedRuntime.instance()
    if runtime is None:
        return False
    decision = review_oracle_use(
        tool_name, "screening_evaluation", runtime.self_model, task_type, target_family
    )
    return decision is not None and decision.verdict == "reject"


def is_gated_error(error: Optional[dict]) -> bool:
    """True when a ToolResult error is a CapGate block (``GatedActionError``).

    Gated calls on *demoted* dims are expected-missing annotations, not
    evaluation failures: no warning escalation, no retry contribution. On
    *kept* dims a gated call is still an ordinary missing measurement.
    """
    return bool(error) and error.get("type") == "GatedActionError"
