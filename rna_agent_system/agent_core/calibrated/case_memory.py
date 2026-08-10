"""CaseMemory: campaign archive + similarity retrieval + SelfModel persistence.

CaseMemory is the persistent carrier of the SelfModel (design doc §2.2):
campaign records are appended as JSONL; the SelfModel snapshot is stored as a
single JSON document. Retrieval is a deterministic weighted feature distance —
no embeddings, no LLM.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from agent_core.calibrated.models import CampaignRecord, SCHEMA_VERSION
from agent_core.calibrated.self_model import SelfModel
from agent_core.file_manager import PROJECT_ROOT

_LOGGER = logging.getLogger(__name__)

# Similarity weights (design doc §2.3 step 1: "相似战役画像 → 迁移使用").
_W_TASK_TYPE = 2.0
_W_TARGET_FAMILY = 1.0


class CaseMemory:
    """File-backed case memory rooted at *root* (default ``workspace/case_memory``)."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else PROJECT_ROOT / "workspace" / "case_memory"
        self.campaigns_path = self.root / "campaigns.jsonl"
        self.self_model_path = self.root / "self_model.json"

    def add_campaign(self, record: CampaignRecord) -> CampaignRecord:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.campaigns_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=True, default=str))
            fh.write("\n")
        _LOGGER.info("case_memory_add campaign=%s", record.campaign_id)
        return record

    def campaigns(self) -> list[CampaignRecord]:
        if not self.campaigns_path.is_file():
            return []
        out: list[CampaignRecord] = []
        with self.campaigns_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(CampaignRecord.model_validate(json.loads(line)))
        return out

    def similar(
        self,
        task_type: str,
        target_family: str = "",
        target_features: dict[str, float | str] | None = None,
        *,
        k: int = 3,
    ) -> list[CampaignRecord]:
        """Return the *k* most similar campaigns (deterministic ordering).

        Score = 2.0 * (task_type match) + 1.0 * (target_family match)
        + mean numeric-feature similarity over shared numeric keys.
        Ties break by campaign_id for reproducibility.
        """
        features = target_features or {}
        numeric_query = {kk: float(vv) for kk, vv in features.items() if isinstance(vv, (int, float))}

        scored: list[tuple[float, str, CampaignRecord]] = []
        for rec in self.campaigns():
            score = 0.0
            if rec.task_type == task_type:
                score += _W_TASK_TYPE
            if target_family and rec.target_family == target_family:
                score += _W_TARGET_FAMILY
            rec_numeric = {
                kk: float(vv)
                for kk, vv in rec.target_features.items()
                if isinstance(vv, (int, float))
            }
            shared = sorted(set(numeric_query) & set(rec_numeric))
            if shared:
                sims = [
                    1.0 - abs(numeric_query[kk] - rec_numeric[kk])
                    / (abs(numeric_query[kk]) + abs(rec_numeric[kk]) + 1e-9)
                    for kk in shared
                ]
                score += sum(sims) / len(sims)
            scored.append((score, rec.campaign_id, rec))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [rec for _, _, rec in scored[:k]]

    def save_self_model(self, self_model: SelfModel) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = self_model.to_dict()
        payload["schema_version"] = SCHEMA_VERSION
        self.self_model_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True, default=str), encoding="utf-8"
        )
        _LOGGER.info("case_memory_save_self_model path=%s", self.self_model_path)

    def load_self_model(self, *, audit=None) -> SelfModel:
        if not self.self_model_path.is_file():
            return SelfModel(audit=audit)
        payload = json.loads(self.self_model_path.read_text(encoding="utf-8"))
        return SelfModel.from_dict(payload, audit=audit)
