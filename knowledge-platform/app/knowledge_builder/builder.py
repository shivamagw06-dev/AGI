"""Knowledge Object Builder — Sprint 6.2 Institutional Knowledge Objects."""

from __future__ import annotations

from typing import Any

from app.contracts.iko import shape_institutional_knowledge
from app.contracts.models import (
    EntityRefs,
    KnowledgeMetadata,
    KnowledgeObject,
    KnowledgeObjectType,
    Source,
    utc_now,
)
from app.kce.engine import KnowledgeConfidenceEngine
from app.storage.db import KaipStore

ALLOWED_TYPES = set(KnowledgeObjectType)


def _diff_fields(previous: dict[str, Any] | None, current: dict[str, Any], prefix: str = "") -> list[str]:
    if not previous:
        return sorted(current.keys())
    changed: list[str] = []
    keys = set(previous) | set(current)
    for key in sorted(keys):
        path = f"{prefix}.{key}" if prefix else key
        pv, cv = previous.get(key), current.get(key)
        if isinstance(pv, dict) and isinstance(cv, dict):
            changed.extend(_diff_fields(pv, cv, path))
        elif pv != cv:
            changed.append(path)
    return changed


class KnowledgeObjectBuilder:
    def __init__(self, store: KaipStore) -> None:
        self.store = store
        self.confidence_engine = KnowledgeConfidenceEngine()

    def build(
        self,
        *,
        canonical: dict[str, Any],
        entity_refs: EntityRefs,
        source_event_ids: list[str],
        source: Source = Source.DERIVED,
        collector_id: str | None = None,
    ) -> KnowledgeObject | None:
        type_name = canonical.get("object_type")
        try:
            object_type = KnowledgeObjectType(type_name)
        except Exception:
            return None
        if object_type not in ALLOWED_TYPES:
            return None

        symbol = (canonical.get("company_symbol") or entity_refs.company_symbol or "")
        symbol = symbol.upper() if symbol else None
        sector_key = canonical.get("sector_key") or (
            entity_refs.sector.lower().replace(" ", "_") if entity_refs.sector else None
        )
        market_key = canonical.get("market_key")

        if object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE:
            subject_key = sector_key or "unknown_sector"
        elif object_type == KnowledgeObjectType.MARKET_KNOWLEDGE:
            subject_key = market_key or "india_equity"
        else:
            if not symbol:
                return None
            subject_key = symbol

        knowledge = shape_institutional_knowledge(
            object_type,
            canonical,
            company_name=entity_refs.company_name,
        )

        previous = self.store.latest_ko(object_type, subject_key)
        version = (previous.version + 1) if previous else 1
        prev_knowledge = (previous.knowledge or previous.payload) if previous else None
        changed_fields = _diff_fields(prev_knowledge, knowledge)
        change_summary = None
        if previous and changed_fields:
            change_summary = f"Changed: {', '.join(changed_fields[:12])}"
        elif not previous:
            change_summary = f"Initial {object_type.value}"

        now = utc_now()
        confidence_report = self.confidence_engine.score_from_events(
            self.store,
            object_type=object_type,
            primary_source=source,
            source_event_ids=source_event_ids,
            subject_key=subject_key,
            knowledge=knowledge,
        )
        metadata = KnowledgeMetadata(
            source=source,
            confidence=confidence_report.label,
            confidence_pct=confidence_report.confidence_pct,
            confidence_detail=confidence_report.to_dict(),
            updated_at=now,
            version=version,
            verified=True,
            collector_id=collector_id,
        )

        return KnowledgeObject(
            object_type=object_type,
            company_symbol=symbol,
            sector_key=sector_key if object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE else entity_refs.sector_key,
            market_key=market_key if object_type == KnowledgeObjectType.MARKET_KNOWLEDGE else None,
            subject_key=subject_key,
            version=version,
            previous_object_id=previous.object_id if previous else None,
            changed_fields=changed_fields,
            change_summary=change_summary,
            knowledge=knowledge,
            payload=knowledge,
            metadata=metadata,
            entity_refs=entity_refs,
            source_event_ids=source_event_ids,
            created_at=now,
            updated_at=now,
        )
