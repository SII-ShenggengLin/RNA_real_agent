"""ClaimGate: pre-publication gating of conclusions by capability grade.

Every claim must carry (oracle, capability, grade, evidence) dependencies
(design doc §2.2). Verdicts: pass when every dependency is verified; downgrade
along the scope ladder (absolute -> within_target_relative -> trend_only) when
a dependency is only transferred; reject when a dependency failed profiling or
was never profiled. Downgraded wording is produced by deterministic templates;
an optional LLM pass (off by default) only polishes wording.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import (
    CLAIM_SCOPE_LADDER,
    Claim,
    ClaimDependency,
    ClaimVerdict,
    EvidencePointer,
)
from agent_core.calibrated.self_model import SelfModel
from agent_core.llm_config import get_deepseek_llm

_LOGGER = logging.getLogger(__name__)

_SCOPE_TEMPLATE = {
    "within_target_relative": (
        "[DOWNGRADED: {reason}] Within {target_family} only, and only as a relative "
        "comparison between candidates: {text}"
    ),
    "trend_only": (
        "[DOWNGRADED: {reason}] Reported as an unquantified trend within "
        "{target_family} only: {text}"
    ),
}

# Claim types that assert a comparative/ordinal conclusion and therefore
# require a declared, capability-checked basis (uniform basis rule).
COMPARATIVE_CLAIM_TYPES = ("ranking", "screening")


class ClaimGate:
    """Adjudicates claims against the SelfModel before they are written."""

    def __init__(
        self,
        self_model: SelfModel,
        *,
        audit: AuditTrail | None = None,
        llm: Any | None = None,
        polish_with_llm: bool = False,
    ) -> None:
        self._self_model = self_model
        self._audit = audit
        self._llm = llm
        self._polish = polish_with_llm

    @property
    def llm(self) -> Any:
        if self._llm is None:
            self._llm = get_deepseek_llm(temperature=0.0)
        return self._llm

    def review(
        self,
        claims: Iterable[Claim],
        *,
        task_type: str,
        target_family: str,
    ) -> list[ClaimVerdict]:
        verdicts = [
            self._review_one(c, task_type=task_type, target_family=target_family)
            for c in claims
        ]
        if self._audit is not None:
            for verdict in verdicts:
                self._audit.record(
                    "claim_verdict",
                    {
                        "claim_id": verdict.claim_id,
                        "verdict": verdict.verdict,
                        "reason": verdict.reason,
                        "grades": {d.oracle: d.grade for d in verdict.dependencies},
                    },
                )
        return verdicts

    # ------------------------------------------------------------------ internals

    def _review_one(self, claim: Claim, *, task_type: str, target_family: str) -> ClaimVerdict:
        resolved: list[ClaimDependency] = []
        evidence: list[EvidencePointer] = []
        worst = "verified"
        for dep in claim.dependencies:
            record = self._self_model.query(dep.oracle, task_type, target_family)
            cell = record.assessment(dep.capability)
            resolved.append(dep.model_copy(update={"grade": cell.grade}))
            evidence.extend(cell.evidence)
            if cell.grade == "unprofiled":
                worst = "unprofiled"
            elif cell.grade == "failed" and worst != "unprofiled":
                worst = "failed"
            elif cell.grade == "transferred" and worst == "verified":
                worst = (
                    "transferred_failed"
                    if cell.transferred_from_grade == "failed"
                    else "transferred_verified"
                )

        if not claim.dependencies:
            if claim.claim_type in COMPARATIVE_CLAIM_TYPES:
                # Uniform basis rule: every comparative conclusion must declare
                # an evidentiary basis that capability profiling can check —
                # deterministic metrics used as proxies enter the same protocol
                # as structural oracles (no free back door).
                return ClaimVerdict(
                    claim_id=claim.claim_id,
                    verdict="reject",
                    reason=(
                        f"{claim.claim_type} claim without declared evidentiary basis; "
                        f"declare the basis (oracle or deterministic proxy) so it can "
                        f"be capability-checked"
                    ),
                )
            return ClaimVerdict(
                claim_id=claim.claim_id,
                verdict="pass",
                reason="no oracle dependencies declared; deterministic content",
            )
        if worst == "verified":
            return ClaimVerdict(
                claim_id=claim.claim_id,
                verdict="pass",
                reason="all dependencies verified on this target family",
                dependencies=resolved,
                evidence=evidence,
            )
        if worst == "unprofiled":
            return ClaimVerdict(
                claim_id=claim.claim_id,
                verdict="reject",
                reason="dependency never profiled; run CapabilityProfiler before claiming",
                dependencies=resolved,
                evidence=evidence,
            )
        if worst in ("failed", "transferred_failed"):
            return ClaimVerdict(
                claim_id=claim.claim_id,
                verdict="reject",
                reason=(
                    "dependency failed capability profiling on this target family; "
                    "no strength of this claim is supported"
                ),
                dependencies=resolved,
                evidence=evidence,
            )
        # transferred_verified: downgrade one step along the scope ladder.
        idx = CLAIM_SCOPE_LADDER.index(claim.scope)
        if idx >= len(CLAIM_SCOPE_LADDER) - 1:
            return ClaimVerdict(
                claim_id=claim.claim_id,
                verdict="reject",
                reason="transferred grade cannot support even a trend-only claim",
                dependencies=resolved,
                evidence=evidence,
            )
        new_scope = CLAIM_SCOPE_LADDER[idx + 1]
        reason = f"dependency grade transferred with decayed confidence; scope {claim.scope} -> {new_scope}"
        rewritten = self._rewrite(claim, new_scope, reason, target_family)
        return ClaimVerdict(
            claim_id=claim.claim_id,
            verdict="downgrade",
            reason=reason,
            dependencies=resolved,
            evidence=evidence,
            rewritten_text=rewritten,
        )

    def _rewrite(self, claim: Claim, new_scope: str, reason: str, target_family: str) -> str:
        text = _SCOPE_TEMPLATE[new_scope].format(
            reason=reason, target_family=target_family, text=claim.text
        )
        if self._polish:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                raw = self.llm.invoke([
                    SystemMessage(content=(
                        "Rewrite the gated scientific claim below into cautious, "
                        "publication-grade wording. Preserve the downgrade marker and "
                        "every numeric value verbatim; output only the rewritten claim."
                    )),
                    HumanMessage(content=text),
                ])
                polished = raw.content if hasattr(raw, "content") else str(raw)
                polished = polished.strip()
                if polished:
                    return polished
            except Exception:  # noqa: BLE001 - LLM polish is best-effort
                _LOGGER.exception("ClaimGate LLM polish failed; keeping template wording")
        return text
