"""Immutable Historical Sector Knowledge Store — append-only."""

from __future__ import annotations

import copy
import time
from typing import Any

from historical_sector_intelligence.schema import (
    STORAGE_NAMESPACES,
    HistoricalSectorKnowledgeObject,
    SectorTimeline,
)


class HistoricalSectorStore:
    def __init__(self) -> None:
        self._by_id: dict[str, HistoricalSectorKnowledgeObject] = {}
        self._by_checksum: set[str] = set()
        self._by_key: dict[str, list[str]] = {}
        self._by_namespace: dict[str, list[str]] = {ns: [] for ns in STORAGE_NAMESPACES}
        self._by_sector: dict[str, list[str]] = {}
        self._timelines: dict[str, SectorTimeline] = {}
        self._runs: list[dict[str, Any]] = []
        self._collector_health: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self._by_id.clear()
        self._by_checksum.clear()
        self._by_key.clear()
        self._by_namespace = {ns: [] for ns in STORAGE_NAMESPACES}
        self._by_sector.clear()
        self._timelines.clear()
        self._runs.clear()
        self._collector_health.clear()

    def append(self, hsko: HistoricalSectorKnowledgeObject) -> HistoricalSectorKnowledgeObject:
        if hsko.checksum and hsko.checksum in self._by_checksum:
            for existing in self._by_id.values():
                if existing.checksum == hsko.checksum:
                    return existing
        if hsko.hsko_id in self._by_id:
            raise ValueError(f"hsko_id already exists (immutable): {hsko.hsko_id}")

        frozen = HistoricalSectorKnowledgeObject.model_validate(
            copy.deepcopy(hsko.model_dump(mode="json"))
        )
        self._by_id[frozen.hsko_id] = frozen
        if frozen.checksum:
            self._by_checksum.add(frozen.checksum)
        key = self._obs_key(frozen.sector_key, frozen.indicator, frozen.period)
        self._by_key.setdefault(key, []).append(frozen.hsko_id)
        ns = frozen.namespace if frozen.namespace in self._by_namespace else "historical_sector"
        self._by_namespace.setdefault(ns, []).append(frozen.hsko_id)
        self._by_sector.setdefault(frozen.sector_key, []).append(frozen.hsko_id)
        return frozen

    def get(self, hsko_id: str) -> HistoricalSectorKnowledgeObject | None:
        return self._by_id.get(hsko_id)

    def versions(
        self, sector_key: str, indicator: str, period: str
    ) -> list[HistoricalSectorKnowledgeObject]:
        key = self._obs_key(sector_key, indicator, period)
        ids = self._by_key.get(key) or []
        return [self._by_id[i] for i in ids if i in self._by_id]

    def series(
        self, indicator: str, *, sector_key: str
    ) -> list[HistoricalSectorKnowledgeObject]:
        prefix = f"{sector_key.upper()}:{indicator.upper()}:"
        periods: dict[str, HistoricalSectorKnowledgeObject] = {}
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
        sector_key: str | None = None,
        category: str | None = None,
        namespace: str | None = None,
    ) -> list[HistoricalSectorKnowledgeObject]:
        rows = list(self._by_id.values())
        if sector_key:
            rows = [r for r in rows if r.sector_key == sector_key]
        if category:
            rows = [r for r in rows if r.category.lower() == category.lower()]
        if namespace:
            rows = [r for r in rows if r.namespace == namespace]
        rows.sort(key=lambda r: (r.period, r.created_at), reverse=True)
        return rows[:limit]

    def put_timeline(self, timeline: SectorTimeline) -> SectorTimeline:
        key = f"{timeline.sector_key}:{timeline.indicator}".upper()
        frozen = SectorTimeline.model_validate(copy.deepcopy(timeline.model_dump(mode="json")))
        self._timelines[key] = frozen
        return frozen

    def get_timeline(self, sector_key: str, *, indicator: str = "Revenue Growth") -> SectorTimeline | None:
        return self._timelines.get(f"{sector_key}:{indicator}".upper())

    def list_timelines(self, *, limit: int = 200, sector_key: str | None = None) -> list[SectorTimeline]:
        rows = list(self._timelines.values())
        if sector_key:
            rows = [t for t in rows if t.sector_key == sector_key]
        rows.sort(key=lambda t: (t.sector_label, t.indicator))
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
            "unique_sectors": len(self._by_sector),
            "years_available": sorted(years),
            "year_span": [min(years), max(years)] if years else [],
            "timelines": len(self._timelines),
            "by_namespace": {ns: len(ids) for ns, ids in self._by_namespace.items()},
        }

    @staticmethod
    def _obs_key(sector_key: str, indicator: str, period: str) -> str:
        return f"{sector_key.upper()}:{indicator.upper()}:{period}"


def _year(period: str) -> int | None:
    raw = str(period or "").replace("FY", "")
    try:
        return int(raw[:4])
    except ValueError:
        return None


STORE = HistoricalSectorStore()


def reset() -> None:
    STORE.clear()
