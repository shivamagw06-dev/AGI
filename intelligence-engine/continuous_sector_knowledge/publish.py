"""Publish Sector Knowledge Objects into the Sector Knowledge Store."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SectorKnowledgeObject, utc_now
from continuous_sector_knowledge.store import STORE


def publish_sko(sko: SectorKnowledgeObject) -> dict[str, Any]:
    sko.published = True
    sko.published_at = utc_now()
    frozen = STORE.put(sko)
    return {
        "sko_id": frozen.sko_id,
        "sector_key": frozen.sector_key,
        "version": frozen.version,
        "outlook": frozen.current_outlook,
        "materiality_tier": frozen.materiality_tier,
        "learning_generated": frozen.learning_generated,
        "providers_queried": [],
    }
