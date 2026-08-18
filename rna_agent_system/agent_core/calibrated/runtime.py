"""CalibratedRuntime: the platform-wide CapGate service.

One optional, process-wide instance connects the calibrated stack to the
platform's execution path:

- ``ToolExecutor.run_tool`` records every tool call to the runtime's audit
  trail (full-pipeline traceability) and consults the DecisionGate for
  managed oracle tools before invoking them.
- ``SynthesisAgent`` routes headline claims of multi-node reports through
  the ClaimGate.

The managed-oracle set is derived from the ToolSpec ontology
(``agent_core/tool_specs.py``): every spec carrying an ``OracleDescriptor``
is managed.  ``enforce``-governance oracles are blocked when the
bundled/loaded SelfModel denies the evidence for the declared use (grade
``failed``, or ``unprofiled`` with no transferable donor) under the
``enforce`` policy.  ``pending``-governance oracles (profiling campaign
E16+ not yet run) are reviewed and audited like enforced ones but never
blocked.  Profiling and annotation callers can wrap calls in
``oracle_use("scoring_annotation")`` to measure an oracle without gating.
Deterministic; no LLM.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.claim_gate import ClaimGate
from agent_core.calibrated.decision_gate import DecisionGate
from agent_core.calibrated.models import Claim, GateDecision, PlannedAction
from agent_core.calibrated.self_model import SelfModel

_LOGGER = logging.getLogger(__name__)

# Directory holding the packaged default SelfModel built from the E1/E7/RNAsmol
# profiling campaigns (generator: experiments/build_default_self_model.py).
_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_SELF_MODEL_PATH = _PACKAGE_DIR / "default_self_model.json"


def _oracle_tables_from_specs() -> tuple[dict[str, tuple[str, str, str]], dict[str, str]]:
    """Derive the managed-oracle tables from the ToolSpec ontology.

    Single source of truth: ``ToolSpec.kind`` / ``ToolSpec.oracle`` in
    ``agent_core/tool_specs.py``.  Returns ``(managed, governance)`` where
    ``managed`` maps tool name -> (oracle, task_type, default use) and
    ``governance`` maps tool name -> ``enforce`` | ``pending``.
    """
    from agent_core.tool_specs import TOOL_SPECS

    managed: dict[str, tuple[str, str, str]] = {}
    governance: dict[str, str] = {}
    for name, spec in TOOL_SPECS.items():
        if spec.oracle is None:
            continue
        managed[name] = (
            spec.oracle.oracle_id,
            spec.oracle.default_task_type,
            spec.oracle.evidence_use.value,
        )
        governance[name] = spec.oracle.governance.value
    return managed, governance


# Tool name -> (oracle, task_type, default use).  The default use is the use
# the calling workflows make of the tool's output; it is what the DecisionGate
# checks unless a caller overrides it via ``oracle_use``.  Derived from the
# ToolSpec oracle descriptors (enforce + pending governance alike).
MANAGED_ORACLE_TOOLS: dict[str, tuple[str, str, str]] = _oracle_tables_from_specs()[0]

# Tool name -> "enforce" | "pending".  Pending oracles are reviewed and audited
# like enforced ones but never blocked: their profiling campaigns (E16+) have
# not yet delivered a SelfModel verdict.
ORACLE_GOVERNANCE: dict[str, str] = _oracle_tables_from_specs()[1]

# Context override for the current oracle use (profiling / annotation callers).
_USE_OVERRIDE: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "calibrated_oracle_use", default=None
)
_FAMILY_OVERRIDE: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "calibrated_oracle_family", default=None
)

# Calling-workflow task context: set by ``BaseDomainWorkflow.run`` from the
# workflow's ``task_type`` declaration, so
# DecisionGate queries are keyed to the *calling* task rather than the
# oracle's registered default (e.g. RhoFold called from tertiary-structure
# design is queried as ``rna_tertiary_structure_design``, not as the E1
# aptamer task it was profiled — and failed — under).
_TASK_TYPE_CONTEXT: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "calibrated_task_type", default=None
)


def task_context(task_type: str) -> Any:
    """Context manager declaring the calling workflow's task type.

    Inside ``with task_context("rna_tertiary_structure_design"):`` every
    managed-oracle review is keyed to that task; the spec's
    ``default_task_type`` applies only outside any workflow context.
    """
    token = _TASK_TYPE_CONTEXT.set(task_type)

    @contextmanager
    def _ctx() -> Iterator[None]:
        try:
            yield
        finally:
            _TASK_TYPE_CONTEXT.reset(token)

    return _ctx()


def current_task_type() -> Optional[str]:
    """The active calling-workflow task type, if any (for audit/reporting)."""
    return _TASK_TYPE_CONTEXT.get()


def oracle_use(use: str, *, target_family: Optional[str] = None) -> Any:
    """Context manager overriding the declared use of oracle tool calls inside.

    ``with oracle_use("scoring_annotation"):`` lets a profiler or a report-only
    caller measure an oracle without triggering the ranking/screening gate.
    """
    token_use = _USE_OVERRIDE.set(use)
    token_family = _FAMILY_OVERRIDE.set(target_family) if target_family else None

    @contextmanager
    def _ctx() -> Iterator[None]:
        try:
            yield
        finally:
            _USE_OVERRIDE.reset(token_use)
            if token_family is not None:
                _FAMILY_OVERRIDE.reset(token_family)

    return _ctx()


class CalibratedRuntime:
    """Process-wide CapGate service owned by ``AgentRunner`` (or tests)."""

    _instance: Optional["CalibratedRuntime"] = None

    def __init__(
        self,
        self_model: SelfModel,
        audit: AuditTrail,
        *,
        policy: str = "enforce",
    ) -> None:
        if policy not in ("enforce", "advisory"):
            raise ValueError(f"policy must be 'enforce' or 'advisory', got {policy!r}")
        self.self_model = self_model
        self.audit = audit
        self.policy = policy
        self.decision_gate = DecisionGate(self_model, audit=audit)
        self.claim_gate = ClaimGate(self_model, audit=audit)

    # ------------------------------------------------------------ construction

    @classmethod
    def configure(
        cls,
        *,
        self_model_path: str | Path | None = None,
        audit_path: str | Path | None = None,
        policy: str = "enforce",
    ) -> "CalibratedRuntime":
        """Install the process-wide runtime (idempotent; replaces existing)."""
        path = Path(self_model_path) if self_model_path else DEFAULT_SELF_MODEL_PATH
        if path.is_file():
            self_model = SelfModel.from_dict(json.loads(path.read_text(encoding="utf-8")))
        else:
            _LOGGER.warning(
                "calibrated_self_model_missing path=%s (empty SelfModel: all "
                "managed oracles gate as unprofiled)", path,
            )
            self_model = SelfModel()
        audit = AuditTrail(audit_path or Path("workspace") / "audit" / "platform_audit.jsonl")
        cls._instance = cls(self_model, audit, policy=policy)
        _LOGGER.info(
            "calibrated_runtime_configured policy=%s records=%d audit=%s",
            policy, len(self_model.records()), audit.path,
        )
        return cls._instance

    @classmethod
    def instance(cls) -> Optional["CalibratedRuntime"]:
        return cls._instance

    @classmethod
    def clear(cls) -> None:
        """Remove the process-wide runtime (tests, explicit opt-out)."""
        cls._instance = None

    # ------------------------------------------------------------- tool calls

    def review_tool_call(self, tool_name: str) -> Optional[GateDecision]:
        """DecisionGate verdict for a managed oracle tool call, else ``None``.

        Uses the context overrides when active — ``oracle_use`` for the
        declared use, ``task_context`` for the calling workflow's task type —
        otherwise the tool's registered defaults.  The target family defaults
        to ``default`` (SelfModel transfer semantics then apply across
        profiled families).
        """
        managed = MANAGED_ORACLE_TOOLS.get(tool_name)
        if managed is None:
            return None
        oracle, default_task_type, default_use = managed
        use = _USE_OVERRIDE.get() or default_use
        family = _FAMILY_OVERRIDE.get() or "default"
        task_type = _TASK_TYPE_CONTEXT.get() or default_task_type
        action = PlannedAction(
            action_id=f"tool:{tool_name}",
            kind="tool_call",
            oracle=oracle,
            use=use,  # type: ignore[arg-type]
        )
        decisions = self.decision_gate.review(
            [action], task_type=task_type, target_family=family
        )
        return decisions[0]

    def should_block(self, decision: GateDecision, tool_name: Optional[str] = None) -> bool:
        """A tool call is blocked only in enforce policy on missing evidence.

        Pending-governance oracles (profiling campaign not yet run, E16+) are
        reviewed and audited but never blocked regardless of verdict.
        ``tool_name`` is optional for backward compatibility; without it the
        verdict alone decides (pending callers must pass the name).
        """
        if tool_name is not None and ORACLE_GOVERNANCE.get(tool_name) == "pending":
            return False
        return self.policy == "enforce" and decision.verdict in ("reject", "require_profiling")

    def record_tool_call(
        self,
        tool_name: str,
        *,
        kwargs_summary: str = "",
        success: bool = False,
        elapsed_time: float = 0.0,
        error_type: str | None = None,
        gated: bool = False,
    ) -> None:
        """Best-effort audit record of one tool call; never raises."""
        try:
            self.audit.record(
                "tool_call",
                {
                    "tool_name": tool_name,
                    "kwargs": kwargs_summary,
                    "success": success,
                    "elapsed_time": round(elapsed_time, 4),
                    "error_type": error_type,
                    "gated": gated,
                },
            )
        except Exception:  # noqa: BLE001 - audit must never fail a run
            _LOGGER.exception("calibrated_audit_write_failed tool=%s", tool_name)

    # ---------------------------------------------------------------- claims

    def gate_claims(
        self, claims: list[Claim], *, task_type: str, target_family: str = "default"
    ) -> list[Any]:
        """ClaimGate verdicts for structured claims (see SynthesisAgent wiring)."""
        return self.claim_gate.review(claims, task_type=task_type, target_family=target_family)


def runtime_from_env() -> Optional[CalibratedRuntime]:
    """Configure the runtime from ``RNADA_CAPGATE`` (off|advisory|enforce).

    Called by ``AgentRunner``; returns ``None`` when the env var is ``off``.
    """
    mode = os.environ.get("RNADA_CAPGATE", "enforce").strip().lower()
    if mode in ("off", "0", "false", "none"):
        CalibratedRuntime.clear()
        return None
    policy = "advisory" if mode in ("advisory", "warn") else "enforce"
    return CalibratedRuntime.configure(
        self_model_path=os.environ.get("RNADA_CAPGATE_SELF_MODEL") or None,
        audit_path=os.environ.get("RNADA_CAPGATE_AUDIT") or None,
        policy=policy,
    )
