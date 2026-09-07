"""Historical Knowledge Builder — canonical rows → versioned HistoricalKnowledgeObjects."""

from __future__ import annotations

from typing import Any

from app.contracts.models import (
    EntityRefs,
    HistoricalKnowledgeObject,
    HistoricalObjectType,
    HistoricalProvenance,
    PeriodKind,
    Source,
    utc_now,
)
from app.hko.shape import (
    shape_historical_action,
    shape_historical_event,
    shape_historical_financial,
    shape_historical_price,
)
from app.storage.db import HipStore
from app.timeline import traces


class HistoricalKnowledgeBuilder:
    def __init__(self, store: HipStore) -> None:
        self.store = store

    def build(
        self,
        *,
        canonical: dict[str, Any],
        entity_refs: EntityRefs,
        source: Source,
        collector_id: str,
        ingestion_run_id: str | None = None,
    ) -> HistoricalKnowledgeObject | None:
        span = traces.begin("historical_normalization", meta={"object_type": canonical.get("object_type")})
        try:
            object_type = HistoricalObjectType(canonical["object_type"])
        except Exception:
            traces.end(span, ok=False)
            return None
        symbol = (canonical.get("company_symbol") or entity_refs.company_symbol or "").upper()
        if not symbol:
            traces.end(span, ok=False)
            return None
        effective_date = str(canonical.get("effective_date") or "")
        if not effective_date:
            traces.end(span, ok=False)
            return None
        try:
            period_kind = PeriodKind(canonical.get("period_kind") or PeriodKind.POINT_IN_TIME.value)
        except Exception:
            period_kind = PeriodKind.POINT_IN_TIME

        subject_key = symbol
        version = self.store.latest_version(object_type, subject_key, effective_date) + 1
        previous_id = None

        now = utc_now()
        provenance = HistoricalProvenance(
            source=source,
            collector_id=collector_id,
            retrieved_at=now,
            effective_date=effective_date,
            version=version,
            checksum=None,
            source_event_ids=[canonical["source_event_id"]] if canonical.get("source_event_id") else [],
            ingestion_run_id=ingestion_run_id,
        )
        raw_knowledge = dict(canonical.get("knowledge") or {})
        knowledge = self._institutional_knowledge(object_type, raw_knowledge, symbol, effective_date, source)

        ko = HistoricalKnowledgeObject(
            object_type=object_type,
            company_symbol=symbol,
            subject_key=subject_key,
            effective_date=effective_date,
            period_kind=period_kind,
            version=version,
            previous_object_id=previous_id,
            knowledge=knowledge,
            entity_refs=entity_refs,
            provenance=provenance,
            created_at=now,
        )
        traces.end(span, output={"object_type": object_type.value, "version": version})
        return ko

    @staticmethod
    def _institutional_knowledge(
        object_type: HistoricalObjectType,
        knowledge: dict[str, Any],
        symbol: str,
        effective_date: str,
        source: Source,
    ) -> dict[str, Any]:
        """Embed Sprint 8.2 HKO shaped view alongside raw metrics (immutable facts)."""
        out = dict(knowledge)
        if object_type == HistoricalObjectType.PRICE_HISTORY:
            out["hko"] = shape_historical_price(knowledge, company=symbol, date=effective_date, source=source)
        elif object_type == HistoricalObjectType.FINANCIAL_STATEMENT:
            out["hko"] = shape_historical_financial(
                knowledge, company=symbol, period=effective_date, source=source
            )
        elif object_type == HistoricalObjectType.CORPORATE_EVENT:
            out["hko"] = shape_historical_event(
                knowledge, company=symbol, date=effective_date, source=source
            )
        elif object_type in {
            HistoricalObjectType.CORPORATE_ACTION,
            HistoricalObjectType.DIVIDEND_HISTORY,
        }:
            payload = dict(knowledge)
            if object_type == HistoricalObjectType.DIVIDEND_HISTORY:
                payload.setdefault("action_type", "dividend")
            out["hko"] = shape_historical_action(
                payload, company=symbol, date=effective_date, source=source
            )
        return out
