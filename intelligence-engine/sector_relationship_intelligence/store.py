"""Versioned Sector Relationship Graph store."""

from __future__ import annotations

import copy
import time
from typing import Any

from sector_relationship_intelligence.schema import SectorRelationship


class SectorRelationshipStore:
    def __init__(self) -> None:
        self._by_id: dict[str, SectorRelationship] = {}
        self._by_source: dict[str, list[str]] = {}
        self._by_target: dict[str, list[str]] = {}
        self._runs: list[dict[str, Any]] = []
        self._discoveries: list[dict[str, Any]] = []
        self._validation_failures: list[dict[str, Any]] = []

    def clear(self) -> None:
        self._by_id.clear()
        self._by_source.clear()
        self._by_target.clear()
        self._runs.clear()
        self._discoveries.clear()
        self._validation_failures.clear()

    def publish(self, rel: SectorRelationship) -> SectorRelationship:
        frozen = SectorRelationship.model_validate(copy.deepcopy(rel.model_dump(mode="json")))
        existing = self._by_id.get(frozen.relationship_id)
        if existing:
            frozen.version = existing.version + 1
            frozen.parent_relationship_id = existing.relationship_id
        frozen.published = True
        from sector_relationship_intelligence.schema import utc_now

        frozen.published_at = utc_now()
        self._by_id[frozen.relationship_id] = frozen
        self._index(frozen)
        return frozen

    def _index(self, rel: SectorRelationship) -> None:
        sk = rel.source.upper()
        tk = rel.target.upper()
        if rel.relationship_id not in (self._by_source.get(sk) or []):
            self._by_source.setdefault(sk, []).append(rel.relationship_id)
        if rel.relationship_id not in (self._by_target.get(tk) or []):
            self._by_target.setdefault(tk, []).append(rel.relationship_id)

    def get(self, relationship_id: str) -> SectorRelationship | None:
        return self._by_id.get(relationship_id)

    def list_all(self, *, limit: int = 500, published_only: bool = True) -> list[SectorRelationship]:
        rows = list(self._by_id.values())
        if published_only:
            rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_endpoint(self, name: str, *, limit: int = 100) -> list[SectorRelationship]:
        key = name.upper()
        ids = set(self._by_source.get(key) or []) | set(self._by_target.get(key) or [])
        rows = [self._by_id[i] for i in ids if i in self._by_id]
        if not rows:
            rows = [
                r
                for r in self._by_id.values()
                if key in r.source.upper()
                or key in r.target.upper()
                or name.lower() in (r.source_label or "").lower()
                or name.lower() in (r.target_label or "").lower()
            ]
        rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_sector(self, sector: str, *, limit: int = 100) -> list[SectorRelationship]:
        return self.for_endpoint(sector, limit=limit)

    def for_company(self, ticker: str, *, limit: int = 100) -> list[SectorRelationship]:
        return self.for_endpoint(ticker, limit=limit)

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def record_discovery(self, row: dict[str, Any]) -> None:
        self._discoveries.append({**row, "ts": time.time()})
        if len(self._discoveries) > 300:
            del self._discoveries[:-300]

    def recent_discoveries(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._discoveries[-limit:])

    def record_validation_failure(self, row: dict[str, Any]) -> None:
        self._validation_failures.append({**row, "ts": time.time()})
        if len(self._validation_failures) > 200:
            del self._validation_failures[:-200]

    def validation_failures(self, limit: int = 40) -> list[dict[str, Any]]:
        return list(self._validation_failures[-limit:])

    def coverage(self) -> dict[str, Any]:
        rows = [r for r in self._by_id.values() if r.published]
        by_conf: dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        by_kind: dict[str, int] = {}
        sectors: set[str] = set()
        for r in rows:
            by_conf[r.confidence_label] = by_conf.get(r.confidence_label, 0) + 1
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
            if r.kind in {"macro_to_sector", "sector_to_sector", "sector_to_company", "sector_to_market"}:
                sectors.add(r.target if "sector" in r.kind and r.kind != "sector_to_company" else r.source)
            if r.kind in {"sector_to_sector", "company_to_sector", "sector_to_company", "macro_to_sector"}:
                for name in (r.source, r.target):
                    if name.upper() not in {"NIFTY", "REPO RATE", "CPI", "USDINR", "FEDERAL FUNDS RATE", "FISCAL DEFICIT"}:
                        if not name.isupper() or len(name) > 6:  # rough sector vs ticker
                            sectors.add(name)
        return {
            "total_relationships": len(rows),
            "active_relationships": sum(1 for r in rows if not r.stale),
            "confidence_distribution": by_conf,
            "by_kind": by_kind,
            "sectors_covered": sorted(sectors),
            "stale": sum(1 for r in rows if r.stale),
        }


STORE = SectorRelationshipStore()


def reset() -> None:
    STORE.clear()
