"""SelfModel: the empirical self-model at the core of the calibrated stack.

Maps (oracle, task_type, target_family) -> four CASF capability cells with
grades, confidence and evidence pointers (design doc §2.2). Deterministic; no
LLM. Persisted via CaseMemory.
"""

from __future__ import annotations

import logging
from typing import Iterable

from agent_core.calibrated.audit_trail import AuditTrail
from agent_core.calibrated.models import (
    CapabilityAssessment,
    CapabilityRecord,
    SCHEMA_VERSION,
)

_LOGGER = logging.getLogger(__name__)

# Confidence multiplier applied when a grade migrates from a similar campaign
# (design doc §2.3 step 1: "迁移使用并降级置信度").
TRANSFER_CONFIDENCE_DECAY = 0.5


class SelfModel:
    """In-memory empirical self-model with optional audit logging."""

    def __init__(
        self,
        records: Iterable[CapabilityRecord] | None = None,
        *,
        audit: AuditTrail | None = None,
    ) -> None:
        self._records: dict[tuple[str, str, str], CapabilityRecord] = {}
        self._audit = audit
        for rec in records or ():
            self._records[rec.key()] = rec

    def update(self, record: CapabilityRecord) -> CapabilityRecord:
        """Write or merge a capability record and emit an audit event."""
        self._records[record.key()] = record
        if self._audit is not None:
            self._audit.record(
                "self_model_update",
                {
                    "oracle": record.oracle,
                    "task_type": record.task_type,
                    "target_family": record.target_family,
                    "grades": {k: v.grade for k, v in record.capabilities.items()},
                },
            )
        _LOGGER.info(
            "self_model_update oracle=%s task=%s family=%s grades=%s",
            record.oracle,
            record.task_type,
            record.target_family,
            {k: v.grade for k, v in record.capabilities.items()},
        )
        return record

    def query(self, oracle: str, task_type: str, target_family: str) -> CapabilityRecord:
        """Look up a capability record.

        - Exact hit: returned as stored.
        - No exact hit but the same (oracle, task_type) was profiled on another
          target family: returned as ``transferred`` with decayed confidence and
          the original family recorded as the source.
        - Otherwise: an empty record with all cells ``unprofiled``.
        """
        exact = self._records.get((oracle, task_type, target_family))
        if exact is not None:
            return exact
        donors = [
            rec
            for (o, t, _), rec in self._records.items()
            if o == oracle and t == task_type
        ]
        if donors:
            donors.sort(key=lambda r: r.target_family)
            return self._transfer(donors[0], target_family)
        return CapabilityRecord(oracle=oracle, task_type=task_type, target_family=target_family)

    @staticmethod
    def _transfer(donor: CapabilityRecord, target_family: str) -> CapabilityRecord:
        cells: dict[str, CapabilityAssessment] = {}
        for kind, cell in donor.capabilities.items():
            cells[kind] = CapabilityAssessment(
                grade="transferred",
                confidence=round(cell.confidence * TRANSFER_CONFIDENCE_DECAY, 4),
                metrics=dict(cell.metrics),
                evidence=list(cell.evidence),
                profiled_at=cell.profiled_at,
                source_case_id=f"{donor.oracle}:{donor.task_type}:{donor.target_family}",
                transferred_from_grade=cell.grade,
            )
        return CapabilityRecord(
            oracle=donor.oracle,
            task_type=donor.task_type,
            target_family=target_family,
            capabilities=cells,
        )

    def records(self) -> list[CapabilityRecord]:
        return [self._records[k] for k in sorted(self._records)]

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "records": [r.model_dump(mode="json") for r in self.records()],
        }

    @classmethod
    def from_dict(cls, payload: dict, *, audit: AuditTrail | None = None) -> "SelfModel":
        records = [CapabilityRecord.model_validate(r) for r in payload.get("records", [])]
        return cls(records, audit=audit)
