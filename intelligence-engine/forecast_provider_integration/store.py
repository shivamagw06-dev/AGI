"""AGI-owned published knowledge for Forecast Provider Integration."""

from __future__ import annotations

import copy
import time
from typing import Any

from forecast_provider_integration.schema import (
    CompanyKnowledgeObject,
    FailoverEvent,
    MarketSnapshot,
)


class KnowledgeStore:
    """Published Company / Market knowledge — forecast consumes this, not raw APIs."""

    def __init__(self) -> None:
        self._company: dict[str, CompanyKnowledgeObject] = {}
        self._market_snapshots: dict[str, MarketSnapshot] = {}  # entity -> latest
        self._failover: list[FailoverEvent] = []
        self._collector_ticks: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def publish_company(self, obj: CompanyKnowledgeObject) -> CompanyKnowledgeObject:
        frozen = CompanyKnowledgeObject.model_validate(copy.deepcopy(obj.model_dump(mode="json")))
        self._company[frozen.entity.upper()] = frozen
        if frozen.dynamic.snapshot:
            self._market_snapshots[frozen.entity.upper()] = frozen.dynamic.snapshot
        self._events.append({"event": "publish_company", "entity": frozen.entity, "ts": time.time()})
        return frozen

    def get_company(self, entity: str) -> CompanyKnowledgeObject | None:
        return self._company.get(entity.upper())

    def publish_snapshot(self, snap: MarketSnapshot) -> MarketSnapshot:
        frozen = MarketSnapshot.model_validate(copy.deepcopy(snap.model_dump(mode="json")))
        self._market_snapshots[frozen.entity.upper()] = frozen
        company = self._company.get(frozen.entity.upper())
        if company:
            company.dynamic.snapshot = frozen
            company.dynamic.updated_at = frozen.as_of
            company.dynamic.stale = frozen.stale
        self._events.append(
            {
                "event": "publish_snapshot",
                "entity": frozen.entity,
                "provider": frozen.source_provider,
                "ts": time.time(),
            }
        )
        return frozen

    def get_snapshot(self, entity: str) -> MarketSnapshot | None:
        return self._market_snapshots.get(entity.upper())

    def record_failover(self, event: FailoverEvent) -> None:
        self._failover.append(event)
        if len(self._failover) > 200:
            del self._failover[:-200]

    def failover_events(self, limit: int = 50) -> list[FailoverEvent]:
        return list(reversed(self._failover[-limit:]))

    def tick_collector(self, provider: str, *, ok: bool, meta: dict[str, Any] | None = None) -> None:
        self._collector_ticks[provider] = {
            "provider": provider,
            "ok": ok,
            "ts": time.time(),
            "meta": meta or {},
        }

    def collector_ticks(self) -> dict[str, dict[str, Any]]:
        return dict(self._collector_ticks)

    def recent_events(self, limit: int = 30) -> list[dict[str, Any]]:
        return list(reversed(self._events[-limit:]))

    def clear(self) -> None:
        self._company.clear()
        self._market_snapshots.clear()
        self._failover.clear()
        self._collector_ticks.clear()
        self._events.clear()


STORE = KnowledgeStore()


def reset() -> None:
    STORE.clear()
