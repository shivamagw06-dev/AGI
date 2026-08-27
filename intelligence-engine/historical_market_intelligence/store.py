"""Immutable Historical Market Knowledge Store — append-only."""

from __future__ import annotations

import copy
import time
from typing import Any

from historical_market_intelligence.schema import (
    STORAGE_NAMESPACES,
    HistoricalMarketKnowledgeObject,
    MarketTimeline,
)


class HistoricalMarketStore:
    def __init__(self) -> None:
        self._by_id: dict[str, HistoricalMarketKnowledgeObject] = {}
        self._by_checksum: set[str] = set()
        self._by_key: dict[str, list[str]] = {}
        self._by_namespace: dict[str, list[str]] = {ns: [] for ns in STORAGE_NAMESPACES}
        self._by_market: dict[str, list[str]] = {}
        self._timelines: dict[str, MarketTimeline] = {}
        self._runs: list[dict[str, Any]] = []
        self._collector_health: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self._by_id.clear()
        self._by_checksum.clear()
        self._by_key.clear()
        self._by_namespace = {ns: [] for ns in STORAGE_NAMESPACES}
        self._by_market.clear()
        self._timelines.clear()
        self._runs.clear()
        self._collector_health.clear()

    def append(self, hmkto: HistoricalMarketKnowledgeObject) -> HistoricalMarketKnowledgeObject:
        if hmkto.checksum and hmkto.checksum in self._by_checksum:
            for existing in self._by_id.values():
                if existing.checksum == hmkto.checksum:
                    return existing
        if hmkto.hmkto_id in self._by_id:
            raise ValueError(f"hmkto_id already exists (immutable): {hmkto.hmkto_id}")

        frozen = HistoricalMarketKnowledgeObject.model_validate(
            copy.deepcopy(hmkto.model_dump(mode="json"))
        )
        self._by_id[frozen.hmkto_id] = frozen
        if frozen.checksum:
            self._by_checksum.add(frozen.checksum)
        key = self._obs_key(frozen.market_key, frozen.indicator, frozen.period)
        self._by_key.setdefault(key, []).append(frozen.hmkto_id)
        ns = frozen.namespace if frozen.namespace in self._by_namespace else "historical_market"
        self._by_namespace.setdefault(ns, []).append(frozen.hmkto_id)
        self._by_market.setdefault(frozen.market_key, []).append(frozen.hmkto_id)
        return frozen

    def get(self, hmkto_id: str) -> HistoricalMarketKnowledgeObject | None:
        return self._by_id.get(hmkto_id)

    def versions(
        self, market_key: str, indicator: str, period: str
    ) -> list[HistoricalMarketKnowledgeObject]:
        key = self._obs_key(market_key, indicator, period)
        ids = self._by_key.get(key) or []
        return [self._by_id[i] for i in ids if i in self._by_id]

    def series(
        self, indicator: str, *, market_key: str
    ) -> list[HistoricalMarketKnowledgeObject]:
        prefix = f"{market_key.upper()}:{indicator.upper()}:"
        periods: dict[str, HistoricalMarketKnowledgeObject] = {}
        for key, ids in self._by_key.items():
            if not key.startswith(prefix) or not ids:
                continue
            period = key.split(":", 2)[-1]
            latest = self._by_id.get(ids[-1])
            if latest:
                periods[period] = latest
        return sorted(periods.values(), key=lambda r: r.period)

    def list_all(
        self,
        *,
        limit: int = 500,
        market_key: str | None = None,
        category: str | None = None,
        namespace: str | None = None,
    ) -> list[HistoricalMarketKnowledgeObject]:
        rows = list(self._by_id.values())
        if market_key:
            rows = [r for r in rows if r.market_key == market_key]
        if category:
            rows = [r for r in rows if r.category.lower() == category.lower()]
        if namespace:
            rows = [r for r in rows if r.namespace == namespace]
        rows.sort(key=lambda r: (r.period, r.created_at), reverse=True)
        return rows[:limit]

    def put_timeline(self, timeline: MarketTimeline) -> MarketTimeline:
        key = f"{timeline.market_key}:{timeline.indicator}".upper()
        frozen = MarketTimeline.model_validate(copy.deepcopy(timeline.model_dump(mode="json")))
        self._timelines[key] = frozen
        return frozen

    def get_timeline(
        self, market_key: str, *, indicator: str = "Market Health"
    ) -> MarketTimeline | None:
        return self._timelines.get(f"{market_key}:{indicator}".upper())

    def list_timelines(
        self, *, limit: int = 200, market_key: str | None = None
    ) -> list[MarketTimeline]:
        rows = list(self._timelines.values())
        if market_key:
            rows = [t for t in rows if t.market_key == market_key]
        rows.sort(key=lambda t: (t.market_label, t.indicator))
        return rows[:limit]

    def tick_collector(self, source: str, *, ok: bool, n: int = 0) -> None:
        prev = self._collector_health.get(source) or {}
        self._collector_health[source] = {
            "source": source,
            "ok": ok,
            "success_count": int(prev.get("success_count") or 0) + (1 if ok else 0),
            "failure_count": int(prev.get("failure_count") or 0) + (0 if ok else 1),
            "last_n": n,
            "ts": time.time(),
        }

    def collector_health(self) -> dict[str, Any]:
        return dict(self._collector_health)

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def coverage(self) -> dict[str, Any]:
        years: set[int] = set()
        for r in self._by_id.values():
            y = _year(r.period)
            if y:
                years.add(y)
        return {
            "total_observations": len(self._by_id),
            "unique_markets": len(self._by_market),
            "years_available": sorted(years),
            "year_span": [min(years), max(years)] if years else [],
            "timelines": len(self._timelines),
            "by_namespace": {ns: len(ids) for ns, ids in self._by_namespace.items()},
            "by_market": {mk: len(ids) for mk, ids in self._by_market.items()},
        }

    @staticmethod
    def _obs_key(market_key: str, indicator: str, period: str) -> str:
        return f"{market_key.upper()}:{indicator.upper()}:{period}"


def _year(period: str) -> int | None:
    raw = str(period or "").replace("FY", "")
    try:
        return int(raw[:4])
    except ValueError:
        return None


STORE = HistoricalMarketStore()


def reset() -> None:
    STORE.clear()
