"""Versioned Market Relationship Graph store."""

from __future__ import annotations

import copy
import time
from typing import Any

from market_relationship_intelligence.schema import MarketRelationship


class MarketRelationshipStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MarketRelationship] = {}
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

    def publish(self, rel: MarketRelationship) -> MarketRelationship:
        frozen = MarketRelationship.model_validate(copy.deepcopy(rel.model_dump(mode="json")))
        existing = self._by_id.get(frozen.relationship_id)
        if existing:
            frozen.version = existing.version + 1
            frozen.parent_relationship_id = existing.relationship_id
        frozen.published = True
        from market_relationship_intelligence.schema import utc_now

        frozen.published_at = utc_now()
        self._by_id[frozen.relationship_id] = frozen
        self._index(frozen)
        return frozen

    def _index(self, rel: MarketRelationship) -> None:
        sk = rel.source.upper()
        tk = rel.target.upper()
        if rel.relationship_id not in (self._by_source.get(sk) or []):
            self._by_source.setdefault(sk, []).append(rel.relationship_id)
        if rel.relationship_id not in (self._by_target.get(tk) or []):
            self._by_target.setdefault(tk, []).append(rel.relationship_id)

    def get(self, relationship_id: str) -> MarketRelationship | None:
        return self._by_id.get(relationship_id)

    def list_all(self, *, limit: int = 500, published_only: bool = True) -> list[MarketRelationship]:
        rows = list(self._by_id.values())
        if published_only:
            rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_endpoint(self, name: str, *, limit: int = 100) -> list[MarketRelationship]:
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
                or any(name.lower() in c.lower() for c in r.chain)
            ]
        rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: r.confidence_pct, reverse=True)
        return rows[:limit]

    def for_sector(self, sector: str, *, limit: int = 100) -> list[MarketRelationship]:
        return self.for_endpoint(sector, limit=limit)

    def for_company(self, ticker: str, *, limit: int = 100) -> list[MarketRelationship]:
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
        markets: set[str] = set()
        sectors: set[str] = set()
        assets: set[str] = set()
        for r in rows:
            by_conf[r.confidence_label] = by_conf.get(r.confidence_label, 0) + 1
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
            if r.kind in {"macro_to_market", "sector_to_market", "flows", "volatility"}:
                markets.add(r.target if "market" in r.target.lower() or r.target.upper() in {"NIFTY", "SENSEX"} else r.source)
            if r.kind in {"market_to_sector", "sector_to_market"}:
                for name in (r.source, r.target):
                    if name.upper() not in {"NIFTY", "SENSEX", "REPO RATE", "CPI", "INDIA VIX"}:
                        sectors.add(name)
            if r.kind == "cross_asset":
                assets.add(r.source)
                assets.add(r.target)
        return {
            "total_relationships": len(rows),
            "active_relationships": sum(1 for r in rows if not r.stale),
            "confidence_distribution": by_conf,
            "by_kind": by_kind,
            "markets_covered": sorted(markets),
            "sectors_covered": sorted(sectors),
            "asset_classes_covered": sorted(assets),
            "stale": sum(1 for r in rows if r.stale),
        }


STORE = MarketRelationshipStore()


def reset() -> None:
    STORE.clear()
