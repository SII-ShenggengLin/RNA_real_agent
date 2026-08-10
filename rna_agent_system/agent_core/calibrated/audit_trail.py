"""AuditTrail: append-only JSONL event log for the calibrated stack.

Every SelfModel update, profiling run, gate decision, claim verdict and budget
event is persisted for paper-grade reproducibility (design doc §2.2).
Deterministic; no LLM.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agent_core.calibrated.models import AuditEvent

_LOGGER = logging.getLogger(__name__)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditTrail:
    """Append-only JSONL writer/reader.

    The file is created lazily on first record. Readers tolerate a missing
    file (empty trail).
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, event_type: str, payload: dict) -> AuditEvent:
        event = AuditEvent(event_type=event_type, payload=payload, timestamp=_utc_iso())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=True, default=str))
            fh.write("\n")
        _LOGGER.debug("audit_event type=%s path=%s", event_type, self.path)
        return event

    def events(self) -> list[AuditEvent]:
        if not self.path.is_file():
            return []
        out: list[AuditEvent] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(AuditEvent.model_validate(json.loads(line)))
        return out
