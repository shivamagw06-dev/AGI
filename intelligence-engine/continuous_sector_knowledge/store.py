"""Sector Knowledge Store — published SKOs + learning events."""

from __future__ import annotations

import copy
import time
from typing import Any

from continuous_sector_knowledge.schema import SectorKnowledgeObject, SectorLearningEvent


class SectorKnowledgeStore:
    def __init__(self) -> None:
        self._by_sector: dict[str, list[SectorKnowledgeObject]] = {}
        self._learnings: list[SectorLearningEvent] = []
        self._runs: list[dict[str, Any]] = []
        self._builder_health: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self._by_sector.clear()
        self._learnings.clear()
        self._runs.clear()
        self._builder_health.clear()

    def put(self, sko: SectorKnowledgeObject) -> SectorKnowledgeObject:
        frozen = SectorKnowledgeObject.model_validate(copy.deepcopy(sko.model_dump(mode="json")))
        bucket = self._by_sector.setdefault(frozen.sector_key, [])
        bucket.append(frozen)
        if len(bucket) > 50:
            del bucket[:-50]
        return frozen

    def latest(self, sector_key: str) -> SectorKnowledgeObject | None:
        rows = self._by_sector.get(sector_key) or []
        published = [r for r in rows if r.published]
        return published[-1] if published else None

    def versions(self, sector_key: str) -> list[SectorKnowledgeObject]:
        return list(self._by_sector.get(sector_key) or [])

    def list_all(self, *, limit: int = 200, published_only: bool = True) -> list[SectorKnowledgeObject]:
        rows: list[SectorKnowledgeObject] = []
        for bucket in self._by_sector.values():
            if not bucket:
                continue
            tip = bucket[-1]
            if published_only and not tip.published:
                continue
            rows.append(tip)
        rows.sort(key=lambda r: r.label)
        return rows[:limit]

    def add_learning(self, event: SectorLearningEvent) -> None:
        self._learnings.append(event)
        if len(self._learnings) > 500:
            del self._learnings[:-500]

    def learnings(self, *, limit: int = 50, sector_key: str | None = None) -> list[SectorLearningEvent]:
        rows = self._learnings
        if sector_key:
            rows = [e for e in rows if e.sector_key == sector_key]
        return list(rows[-limit:])

    def tick_builder(self, name: str, *, ok: bool, meta: dict[str, Any] | None = None) -> None:
        self._builder_health[name] = {
            "ok": ok,
            "last_ts": time.time(),
            "meta": meta or {},
        }

    def builder_health(self) -> dict[str, Any]:
        return dict(self._builder_health)

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def coverage(self) -> dict[str, Any]:
        tips = self.list_all(limit=500)
        by_outlook: dict[str, int] = {}
        by_group: dict[str, int] = {}
        company_n = 0
        for r in tips:
            by_outlook[r.current_outlook] = by_outlook.get(r.current_outlook, 0) + 1
            g = str((r.normalized or {}).get("group") or "Other")
            by_group[g] = by_group.get(g, 0) + 1
            company_n += r.company_coverage
        return {
            "published_sectors": len(tips),
            "unique_sectors": len(tips),
            "learning_events": len(self._learnings),
            "outlook_distribution": by_outlook,
            "by_group": by_group,
            "company_coverage_total": company_n,
            "versions_total": sum(len(v) for v in self._by_sector.values()),
        }


STORE = SectorKnowledgeStore()


def reset() -> None:
    STORE.clear()
