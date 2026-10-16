"""Macro Knowledge Store — append-only versioned MKOs + learning + ops metrics."""

from __future__ import annotations

import copy
import time
from typing import Any

from continuous_macro_knowledge.schema import LearningEvent, MacroKnowledgeObject


class MacroKnowledgeStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MacroKnowledgeObject] = {}
        self._by_indicator: dict[str, list[str]] = {}  # country:indicator -> mko ids
        self._learnings: list[LearningEvent] = []
        self._collector_health: dict[str, dict[str, Any]] = {}
        self._runs: list[dict[str, Any]] = []
        self._publications: list[dict[str, Any]] = []

    def put(self, mko: MacroKnowledgeObject) -> MacroKnowledgeObject:
        frozen = MacroKnowledgeObject.model_validate(copy.deepcopy(mko.model_dump(mode="json")))
        self._by_id[frozen.mko_id] = frozen
        key = f"{frozen.country}:{frozen.indicator}".upper()
        self._by_indicator.setdefault(key, []).append(frozen.mko_id)
        return frozen

    def get(self, mko_id: str) -> MacroKnowledgeObject | None:
        return self._by_id.get(mko_id)

    def latest(self, indicator: str, *, country: str = "India") -> MacroKnowledgeObject | None:
        key = f"{country}:{indicator}".upper()
        ids = self._by_indicator.get(key) or []
        if not ids:
            # fuzzy: indicator only
            for k, v in self._by_indicator.items():
                if k.endswith(f":{indicator.upper()}") and v:
                    return self._by_id.get(v[-1])
            return None
        return self._by_id.get(ids[-1])

    def list_all(self, *, limit: int = 200, country: str | None = None, category: str | None = None) -> list[MacroKnowledgeObject]:
        rows = list(self._by_id.values())
        if country:
            rows = [r for r in rows if r.country.lower() == country.lower()]
        if category:
            rows = [r for r in rows if r.category.lower() == category.lower()]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[:limit]

    def published(self, *, limit: int = 200, country: str | None = None) -> list[MacroKnowledgeObject]:
        rows = [r for r in self.list_all(limit=1000, country=country) if r.published]
        return rows[:limit]

    def versions(self, indicator: str, *, country: str = "India") -> list[MacroKnowledgeObject]:
        key = f"{country}:{indicator}".upper()
        ids = self._by_indicator.get(key) or []
        return [self._by_id[i] for i in ids if i in self._by_id]

    def add_learning(self, event: LearningEvent) -> LearningEvent:
        frozen = LearningEvent.model_validate(copy.deepcopy(event.model_dump(mode="json")))
        self._learnings.append(frozen)
        if len(self._learnings) > 1000:
            del self._learnings[:-1000]
        return frozen

    def learnings(self, *, limit: int = 50) -> list[LearningEvent]:
        return list(reversed(self._learnings[-limit:]))

    def tick_collector(self, source: str, *, ok: bool, meta: dict[str, Any] | None = None) -> None:
        prev = self._collector_health.get(source) or {}
        self._collector_health[source] = {
            "source": source,
            "ok": ok,
            "success_count": int(prev.get("success_count") or 0) + (1 if ok else 0),
            "failure_count": int(prev.get("failure_count") or 0) + (0 if ok else 1),
            "last_ok": ok,
            "ts": time.time(),
            "meta": meta or {},
        }

    def collector_health(self) -> dict[str, dict[str, Any]]:
        return dict(self._collector_health)

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._runs[-limit:]))

    def record_publication(self, row: dict[str, Any]) -> None:
        self._publications.append({**row, "ts": time.time()})
        if len(self._publications) > 500:
            del self._publications[:-500]

    def publications(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self._publications[-limit:]))

    def coverage(self) -> dict[str, Any]:
        by_cat: dict[str, int] = {}
        by_country: dict[str, int] = {}
        indicators: set[str] = set()
        for m in self._by_id.values():
            if m.published:
                by_cat[m.category] = by_cat.get(m.category, 0) + 1
                by_country[m.country] = by_country.get(m.country, 0) + 1
                indicators.add(f"{m.country}:{m.indicator}")
        return {
            "published_objects": sum(1 for m in self._by_id.values() if m.published),
            "total_objects": len(self._by_id),
            "unique_indicators": len(indicators),
            "by_category": by_cat,
            "by_country": by_country,
            "learning_events": len(self._learnings),
        }

    def clear(self) -> None:
        self._by_id.clear()
        self._by_indicator.clear()
        self._learnings.clear()
        self._collector_health.clear()
        self._runs.clear()
        self._publications.clear()


STORE = MacroKnowledgeStore()


def reset() -> None:
    STORE.clear()
