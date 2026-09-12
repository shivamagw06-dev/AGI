"""Immutable Historical Macro Knowledge Store — append-only, never overwrite."""

from __future__ import annotations

import copy
import time
from typing import Any

from historical_macro_intelligence.schema import (
    STORAGE_NAMESPACES,
    HistoricalMacroKnowledgeObject,
    IndicatorTimeline,
)


class HistoricalMacroStore:
    def __init__(self) -> None:
        self._by_id: dict[str, HistoricalMacroKnowledgeObject] = {}
        self._by_checksum: set[str] = set()
        self._by_key: dict[str, list[str]] = {}  # country:indicator:period -> hmko ids (versions)
        self._by_namespace: dict[str, list[str]] = {ns: [] for ns in STORAGE_NAMESPACES}
        self._timelines: dict[str, IndicatorTimeline] = {}
        self._runs: list[dict[str, Any]] = []
        self._collector_health: dict[str, dict[str, Any]] = {}

    def append(self, hmko: HistoricalMacroKnowledgeObject) -> HistoricalMacroKnowledgeObject:
        """Append-only. Rejects identical checksum duplicates; allows versioned revisions."""
        if hmko.checksum and hmko.checksum in self._by_checksum:
            # Exact duplicate observation — return existing, do not overwrite
            for existing in self._by_id.values():
                if existing.checksum == hmko.checksum:
                    return existing
        if hmko.hmko_id in self._by_id:
            raise ValueError(f"hmko_id already exists (immutable): {hmko.hmko_id}")

        frozen = HistoricalMacroKnowledgeObject.model_validate(
            copy.deepcopy(hmko.model_dump(mode="json"))
        )
        self._by_id[frozen.hmko_id] = frozen
        if frozen.checksum:
            self._by_checksum.add(frozen.checksum)
        key = self._obs_key(frozen.country, frozen.indicator, frozen.period)
        self._by_key.setdefault(key, []).append(frozen.hmko_id)
        ns = frozen.namespace if frozen.namespace in self._by_namespace else "historical_macro"
        self._by_namespace.setdefault(ns, []).append(frozen.hmko_id)
        return frozen

    def get(self, hmko_id: str) -> HistoricalMacroKnowledgeObject | None:
        return self._by_id.get(hmko_id)

    def versions(self, country: str, indicator: str, period: str) -> list[HistoricalMacroKnowledgeObject]:
        key = self._obs_key(country, indicator, period)
        ids = self._by_key.get(key) or []
        return [self._by_id[i] for i in ids if i in self._by_id]

    def series(self, indicator: str, *, country: str = "India") -> list[HistoricalMacroKnowledgeObject]:
        """Latest version per period, ordered by period."""
        prefix = f"{country.upper()}:{indicator.upper()}:"
        periods: dict[str, HistoricalMacroKnowledgeObject] = {}
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
        country: str | None = None,
        category: str | None = None,
        namespace: str | None = None,
    ) -> list[HistoricalMacroKnowledgeObject]:
        rows = list(self._by_id.values())
        if country:
            rows = [r for r in rows if r.country.lower() == country.lower()]
        if category:
            rows = [r for r in rows if r.category.lower() == category.lower()]
        if namespace:
            rows = [r for r in rows if r.namespace == namespace]
        rows.sort(key=lambda r: (r.period, r.created_at), reverse=True)
        return rows[:limit]

    def put_timeline(self, timeline: IndicatorTimeline) -> IndicatorTimeline:
        key = f"{timeline.country}:{timeline.indicator}".upper()
        frozen = IndicatorTimeline.model_validate(copy.deepcopy(timeline.model_dump(mode="json")))
        self._timelines[key] = frozen
        return frozen

    def get_timeline(self, indicator: str, *, country: str = "India") -> IndicatorTimeline | None:
        return self._timelines.get(f"{country}:{indicator}".upper())

    def list_timelines(self, *, limit: int = 100) -> list[IndicatorTimeline]:
        rows = list(self._timelines.values())
        rows.sort(key=lambda t: t.indicator)
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

    def collector_health(self) -> dict[str, dict[str, Any]]:
        return dict(self._collector_health)

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._runs[-limit:]))

    def coverage(self) -> dict[str, Any]:
        by_ns = {ns: len(ids) for ns, ids in self._by_namespace.items()}
        indicators: set[str] = set()
        countries: set[str] = set()
        years: set[int] = set()
        for m in self._by_id.values():
            indicators.add(f"{m.country}:{m.indicator}")
            countries.add(m.country)
            y = _year(m.period)
            if y:
                years.add(y)
        return {
            "total_observations": len(self._by_id),
            "unique_indicators": len(indicators),
            "countries": sorted(countries),
            "years_available": sorted(years),
            "year_span": [min(years), max(years)] if years else [],
            "by_namespace": by_ns,
            "timelines": len(self._timelines),
            "storage_growth_objects": len(self._by_id),
        }

    def revision_history(self, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = [r for r in self._by_id.values() if r.version > 1 or r.revision_note]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return [
            {
                "hmko_id": r.hmko_id,
                "indicator": r.indicator,
                "period": r.period,
                "version": r.version,
                "parent_hmko_id": r.parent_hmko_id,
                "revision_note": r.revision_note,
                "checksum": r.checksum,
            }
            for r in rows[:limit]
        ]

    def clear(self) -> None:
        self._by_id.clear()
        self._by_checksum.clear()
        self._by_key.clear()
        self._by_namespace = {ns: [] for ns in STORAGE_NAMESPACES}
        self._timelines.clear()
        self._runs.clear()
        self._collector_health.clear()

    @staticmethod
    def _obs_key(country: str, indicator: str, period: str) -> str:
        return f"{country}:{indicator}:{period}".upper()


def _year(period: str) -> int | None:
    raw = str(period or "")
    if raw.startswith("FY") and len(raw) >= 6:
        try:
            return int(raw[2:6])
        except ValueError:
            return None
    try:
        return int(raw[:4])
    except ValueError:
        return None


STORE = HistoricalMacroStore()


def reset() -> None:
    STORE.clear()
