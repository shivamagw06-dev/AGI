"""Versioned Macro Relationship Graph store — append revisions, never invent edges."""

from __future__ import annotations

import copy
import time
from typing import Any

from macroeconomic_relationship_intelligence.schema import MacroRelationship


class MacroRelationshipStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MacroRelationship] = {}
        self._by_source: dict[str, list[str]] = {}
        self._by_target: dict[str, list[str]] = {}
        self._runs: list[dict[str, Any]] = []
        self._discoveries: list[dict[str, Any]] = []

    def clear(self) -> None:
        self._by_id.clear()
        self._by_source.clear()
        self._by_target.clear()
        self._runs.clear()
        self._discoveries.clear()

    def publish(self, rel: MacroRelationship) -> MacroRelationship:
        frozen = MacroRelationship.model_validate(copy.deepcopy(rel.model_dump(mode="json")))
        # Version bump if same logical id already present with different content
        existing = self._by_id.get(frozen.relationship_id)
        if existing:
            frozen.version = existing.version + 1
            frozen.parent_relationship_id = existing.relationship_id
            # Keep same id for graph stability — store as new version replacing tip
        frozen.published = True
        from macroeconomic_relationship_intelligence.schema import utc_now

        frozen.published_at = utc_now()
        self._by_id[frozen.relationship_id] = frozen
        self._index(frozen)
        return frozen

    def _index(self, rel: MacroRelationship) -> None:
        sk = rel.source.upper()
        tk = rel.target.upper()
        if rel.relationship_id not in (self._by_source.get(sk) or []):
            self._by_source.setdefault(sk, []).append(rel.relationship_id)
        if rel.relationship_id not in (self._by_target.get(tk) or []):
            self._by_target.setdefault(tk, []).append(rel.relationship_id)

    def get(self, relationship_id: str) -> MacroRelationship | None:
        return self._by_id.get(relationship_id)

    def list_all(self, *, limit: int = 500, published_only: bool = True) -> list[MacroRelationship]:
        rows = list(self._by_id.values())
        if published_only:
            rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_indicator(self, indicator: str, *, limit: int = 100) -> list[MacroRelationship]:
        key = indicator.upper()
        ids = set(self._by_source.get(key) or []) | set(self._by_target.get(key) or [])
        # Also match label-like substring
        rows = [self._by_id[i] for i in ids if i in self._by_id]
        if not rows:
            rows = [
                r
                for r in self._by_id.values()
                if key in r.source.upper() or key in r.target.upper()
            ]
        rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_company(self, ticker: str, *, limit: int = 100) -> list[MacroRelationship]:
        return self.for_indicator(ticker, limit=limit)

    def for_sector(self, sector: str, *, limit: int = 100) -> list[MacroRelationship]:
        key = sector.upper().replace(" ", "_")
        rows = [
            r
            for r in self._by_id.values()
            if r.published
            and (
                key in r.target.upper().replace(" ", "_")
                or key in r.source.upper().replace(" ", "_")
                or sector.lower() in (r.target_label or "").lower()
                or sector.lower() in r.target.lower()
            )
        ]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._runs[-limit:]))

    def record_discovery(self, row: dict[str, Any]) -> None:
        self._discoveries.append({**row, "ts": time.time()})
        if len(self._discoveries) > 200:
            del self._discoveries[:-200]

    def recent_discoveries(self, limit: int = 30) -> list[dict[str, Any]]:
        return list(reversed(self._discoveries[-limit:]))

    def coverage(self) -> dict[str, Any]:
        rows = [r for r in self._by_id.values() if r.published]
        by_kind: dict[str, int] = {}
        by_strength: dict[str, int] = {}
        indicators: set[str] = set()
        companies: set[str] = set()
        sectors: set[str] = set()
        for r in rows:
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
            by_strength[r.confidence_label] = by_strength.get(r.confidence_label, 0) + 1
            indicators.add(r.source)
            if r.kind == "macro_to_company":
                companies.add(r.target)
            elif r.kind == "macro_to_sector":
                sectors.add(r.target)
        return {
            "total_relationships": len(rows),
            "by_kind": by_kind,
            "confidence_distribution": by_strength,
            "indicators_covered": len(indicators),
            "companies_covered": len(companies),
            "sectors_covered": len(sectors),
            "stale": sum(1 for r in rows if r.stale),
        }


STORE = MacroRelationshipStore()


def reset() -> None:
    STORE.clear()
