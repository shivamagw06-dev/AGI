"""Generate sector learning events for material updates."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SectorKnowledgeObject, SectorLearningEvent


def generate_learning(
    sko: SectorKnowledgeObject,
    *,
    materiality: dict[str, Any],
) -> SectorLearningEvent | None:
    if not materiality.get("learn"):
        return None
    prior_outlook = (sko.normalized or {}).get("prior_outlook")
    topic = materiality.get("reason") or "sector_update"
    summary = (
        f"{sko.label}: outlook {prior_outlook or 'n/a'} → {sko.current_outlook}; "
        f"trigger={sko.trigger}; tier={materiality.get('tier')}"
    )
    return SectorLearningEvent(
        sko_id=sko.sko_id,
        sector_key=sko.sector_key,
        topic=str(topic),
        summary=summary,
        materiality_tier=sko.materiality_tier,
        trigger=sko.trigger,
        source_layers=list(sko.source_layers),
    )
