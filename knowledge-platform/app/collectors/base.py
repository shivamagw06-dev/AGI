"""Collector protocol — emit Raw Events only. No finance logic in the scheduler."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.contracts.models import RawEvent, Source, utc_now


def checksum_payload(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class CollectorJob:
    job_id: str
    collector_id: str
    interval_seconds: int


class BaseCollector(ABC):
    collector_id: str
    source: Source
    interval_seconds: int

    def job_spec(self) -> CollectorJob:
        return CollectorJob(
            job_id=self.collector_id,
            collector_id=self.collector_id,
            interval_seconds=self.interval_seconds,
        )

    @abstractmethod
    def collect(self) -> list[RawEvent]:
        """Fetch source data and return append-only raw events."""

    def make_event(
        self,
        *,
        endpoint: str,
        payload: dict[str, Any],
        company_symbol: str | None = None,
    ) -> RawEvent:
        return RawEvent(
            source=self.source,
            collector_id=self.collector_id,
            endpoint=endpoint,
            company_symbol=company_symbol.upper() if company_symbol else None,
            payload=payload,
            timestamp=utc_now(),
            checksum=checksum_payload(payload),
        )
