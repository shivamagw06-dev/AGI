"""Materiality — only meaningful market changes regenerate learning."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MarketKnowledgeObject
from continuous_market_knowledge.store import STORE


def evaluate_materiality(mko: MarketKnowledgeObject) -> dict[str, Any]:
    prior = STORE.latest(mko.domain_key)
    if not prior:
        mko.materiality_tier = "Medium"
        mko.materiality_score = 55.0
        return {
            "tier": "Medium",
            "score": 55.0,
            "reason": "first_publication",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    regime_changed = prior.market_regime != mko.market_regime
    sentiment_changed = prior.risk_sentiment != mko.risk_sentiment
    trend_changed = prior.trend != mko.trend
    health_delta = abs(float(prior.health_score) - float(mko.health_score))
    trigger = str(mko.trigger or "")

    # Explicit material triggers from ops
    if trigger in {"breadth_surge", "regime_change", "liquidity_shock", "flow_reversal"}:
        mko.materiality_tier = "Critical" if trigger != "breadth_surge" else "High"
        mko.materiality_score = 90.0 if mko.materiality_tier == "Critical" else 78.0
        return {
            "tier": mko.materiality_tier,
            "score": mko.materiality_score,
            "reason": f"trigger:{trigger}",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    if regime_changed:
        mko.materiality_tier = "Critical"
        mko.materiality_score = 88.0
        return {
            "tier": "Critical",
            "score": 88.0,
            "reason": "regime_changed",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    if sentiment_changed or health_delta >= 5.0:
        mko.materiality_tier = "High"
        mko.materiality_score = 75.0
        return {
            "tier": "High",
            "score": 75.0,
            "reason": "sentiment_or_health_shift",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    if trend_changed or health_delta >= 2.0:
        mko.materiality_tier = "Medium"
        mko.materiality_score = 58.0
        return {
            "tier": "Medium",
            "score": 58.0,
            "reason": "trend_or_modest_health_shift",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    # Breadth participation material example: ignore tiny moves
    prior_part = float((prior.breadth or {}).get("participation_pct") or 0)
    cur_part = float((mko.breadth or {}).get("participation_pct") or 0)
    if prior_part and cur_part and abs(cur_part - prior_part) >= 10:
        mko.materiality_tier = "High"
        mko.materiality_score = 80.0
        return {
            "tier": "High",
            "score": 80.0,
            "reason": "breadth_participation_material",
            "learn": True,
            "filtered": False,
            "domain_key": mko.domain_key,
        }

    # Unchanged — publish but Ignore learning (e.g. NIFTY +0.08%)
    mko.materiality_tier = "Ignore"
    mko.materiality_score = 5.0
    return {
        "tier": "Ignore",
        "score": 5.0,
        "reason": "immaterial_unchanged",
        "learn": False,
        "filtered": True,
        "domain_key": mko.domain_key,
    }
