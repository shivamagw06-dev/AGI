"""Historical collector protocol — emit RawHistoricalEvent only."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any

from app.contracts.models import RawHistoricalEvent, Source, utc_now


def checksum_payload(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class BaseHistoricalCollector(ABC):
    collector_id: str
    source: Source
    categories: tuple[str, ...]

    @abstractmethod
    def collect(self, *, ingestion_run_id: str | None = None) -> list[RawHistoricalEvent]:
        """Fetch historical payloads and return append-only raw archive events."""

    def make_event(
        self,
        *,
        endpoint: str,
        category: str,
        payload: dict[str, Any],
        company_symbol: str | None = None,
        effective_start: str | None = None,
        effective_end: str | None = None,
        ingestion_run_id: str | None = None,
    ) -> RawHistoricalEvent:
        return RawHistoricalEvent(
            source=self.source,
            collector_id=self.collector_id,
            endpoint=endpoint,
            company_symbol=company_symbol.upper() if company_symbol else None,
            category=category,
            payload=payload,
            retrieved_at=utc_now(),
            effective_start=effective_start,
            effective_end=effective_end,
            checksum=checksum_payload({"category": category, "symbol": company_symbol, **payload}),
            ingestion_run_id=ingestion_run_id,
        )
