"""Market Knowledge Store — published MKTOs + learning events."""

from __future__ import annotations

import copy
import time
from typing import Any

from continuous_market_knowledge.schema import MarketKnowledgeObject, MarketLearningEvent


class MarketKnowledgeStore:
    def __init__(self) -> None:
        self._by_domain: dict[str, list[MarketKnowledgeObject]] = {}
        self._learnings: list[MarketLearningEvent] = []
        self._runs: list[dict[str, Any]] = []
        self._builder_health: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self._by_domain.clear()
        self._learnings.clear()
        self._runs.clear()
        self._builder_health.clear()

    def put(self, mko: MarketKnowledgeObject) -> MarketKnowledgeObject:
        frozen = MarketKnowledgeObject.model_validate(copy.deepcopy(mko.model_dump(mode="json")))
        bucket = self._by_domain.setdefault(frozen.domain_key, [])
        bucket.append(frozen)
        if len(bucket) > 50:
            del bucket[:-50]
        return frozen

    def latest(self, domain_key: str) -> MarketKnowledgeObject | None:
        rows = self._by_domain.get(domain_key) or []
        published = [r for r in rows if r.published]
        return published[-1] if published else None

    def versions(self, domain_key: str) -> list[MarketKnowledgeObject]:
        return list(self._by_domain.get(domain_key) or [])

    def list_all(self, *, limit: int = 200, published_only: bool = True) -> list[MarketKnowledgeObject]:
        rows: list[MarketKnowledgeObject] = []
        for bucket in self._by_domain.values():
            if not bucket:
                continue
            tip = bucket[-1]
            if published_only and not tip.published:
                continue
            rows.append(tip)
        rows.sort(key=lambda r: r.label)
        return rows[:limit]

    def add_learning(self, event: MarketLearningEvent) -> None:
        self._learnings.append(event)
        if len(self._learnings) > 500:
            del self._learnings[:-500]

    def learnings(self, *, limit: int = 50, domain_key: str | None = None) -> list[MarketLearningEvent]:
        rows = self._learnings
        if domain_key:
            rows = [e for e in rows if e.domain_key == domain_key]
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
        by_regime: dict[str, int] = {}
        by_sentiment: dict[str, int] = {}
        for r in tips:
            by_regime[r.market_regime] = by_regime.get(r.market_regime, 0) + 1
            by_sentiment[r.risk_sentiment] = by_sentiment.get(r.risk_sentiment, 0) + 1
        return {
            "published_domains": len(tips),
            "unique_domains": len(tips),
            "learning_events": len(self._learnings),
            "regime_distribution": by_regime,
            "sentiment_distribution": by_sentiment,
            "versions_total": sum(len(v) for v in self._by_domain.values()),
            "mean_health_score": round(
                sum(r.health_score for r in tips) / len(tips), 1
            )
            if tips
            else None,
        }


STORE = MarketKnowledgeStore()


def reset() -> None:
    STORE.clear()
