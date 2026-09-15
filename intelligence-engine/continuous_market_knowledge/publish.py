"""Publish Market Knowledge Objects to the store."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MarketKnowledgeObject, utc_now
from continuous_market_knowledge.store import STORE


def publish_mko(mko: MarketKnowledgeObject) -> dict[str, Any]:
    mko.published = True
    mko.published_at = utc_now()
    frozen = STORE.put(mko)
    return {
        "mkto_id": frozen.mkto_id,
        "domain_key": frozen.domain_key,
        "version": frozen.version,
        "regime": frozen.market_regime,
        "health_score": frozen.health_score,
        "materiality_tier": frozen.materiality_tier,
        "learning_generated": frozen.learning_generated,
        "published": True,
    }
