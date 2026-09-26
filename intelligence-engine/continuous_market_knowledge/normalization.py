"""Draft → versioned Market Knowledge Object."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import (
    MarketKnowledgeObject,
    RegimeLabel,
    RiskSentiment,
    Trend,
)
from continuous_market_knowledge.store import STORE


def _regime(value: Any) -> RegimeLabel:
    allowed = {
        "Bull",
        "Bear",
        "Sideways",
        "Recovery",
        "Capitulation",
        "Distribution",
        "Expansion",
        "Contraction",
        "Unknown",
    }
    s = str(value or "Unknown")
    return s if s in allowed else "Unknown"  # type: ignore[return-value]


def _sentiment(value: Any) -> RiskSentiment:
    allowed = {
        "Risk On",
        "Risk Off",
        "Defensive Rotation",
        "Growth Rotation",
        "Value Rotation",
        "Mixed",
        "Unknown",
    }
    s = str(value or "Unknown")
    return s if s in allowed else "Unknown"  # type: ignore[return-value]


def _trend(value: Any) -> Trend:
    allowed = {"Improving", "Stable", "Deteriorating", "Mixed", "Unknown"}
    s = str(value or "Unknown")
    return s if s in allowed else "Unknown"  # type: ignore[return-value]


def normalize_draft(draft) -> MarketKnowledgeObject:
    cat = draft.catalog or {}
    computed = draft.computed or {}
    prior = STORE.latest(draft.domain_key)
    version = (prior.version + 1) if prior else 1

    breadth = {}
    liquidity = {}
    volatility = {}
    flows = {}
    leadership = {}
    cross_asset = {}
    health = {}

    if draft.domain_key == "breadth" or computed.get("metrics"):
        if draft.domain_key == "breadth":
            breadth = dict(computed.get("metrics") or cat.get("metrics") or {})
    if draft.domain_key == "liquidity":
        liquidity = dict(computed.get("metrics") or cat.get("metrics") or {})
    if draft.domain_key == "volatility":
        volatility = dict(computed.get("metrics") or cat.get("metrics") or {})
    if draft.domain_key == "institutional_flows":
        flows = dict(computed.get("metrics") or cat.get("metrics") or {})
    if draft.domain_key == "leadership":
        leadership = {
            "leading_sectors": computed.get("leading_sectors") or cat.get("leading_sectors"),
            "weak_sectors": computed.get("weak_sectors") or cat.get("weak_sectors"),
            "leading_stocks": cat.get("leading_stocks"),
            "weak_stocks": cat.get("weak_stocks"),
            "rotation": computed.get("rotation") or cat.get("rotation"),
            "forecast_supported_leaders": computed.get("forecast_supported_leaders"),
        }
    if draft.domain_key == "cross_asset":
        cross_asset = dict(computed.get("metrics") or cat.get("metrics") or {})
    if draft.domain_key == "market_health":
        health = {
            "score": computed.get("health_score") or cat.get("health_base"),
            "formula": computed.get("formula"),
            "components": computed.get("components") or cat.get("components"),
        }
    elif draft.domain_key in {"india_equity", "global_equity"}:
        health = {"score": cat.get("health_base"), "indices": cat.get("indices")}

    # For non-specialized domains, still attach catalog metrics into normalized slice
    if draft.domain_key == "breadth" and not breadth:
        breadth = dict(cat.get("metrics") or {})

    health_score = float(
        computed.get("health_score")
        or (health.get("score") if isinstance(health.get("score"), (int, float)) else None)
        or cat.get("health_base")
        or 50.0
    )

    layers = ["market_catalog", "internal_computation"]
    if (draft.macro_tip or {}).get("available"):
        layers.append("CMKP")
    if (draft.sector_tip or {}).get("available"):
        layers.append("CSKP")
    if (draft.fpi_tip or {}).get("available"):
        layers.append("FPI_status")

    return MarketKnowledgeObject(
        domain_key=draft.domain_key,
        label=draft.label,
        market_regime=_regime(computed.get("regime") or cat.get("regime")),
        breadth=breadth,
        liquidity=liquidity,
        volatility=volatility,
        institutional_flows=flows,
        leadership=leadership,
        cross_asset_state=cross_asset,
        risk_sentiment=_sentiment(cat.get("risk_sentiment")),
        market_health=health,
        health_score=health_score,
        summary=cat.get("summary"),
        trend=_trend(cat.get("trend")),
        confidence=float(cat.get("confidence") or 0.7),
        knowledge_freshness_sec=0,
        version=version,
        parent_mkto_id=prior.mkto_id if prior else None,
        source_layers=layers,
        normalized={
            "domain": draft.domain_key,
            "computed": computed,
            "primary_source": cat.get("primary_source"),
            "indices": cat.get("indices"),
        },
        provenance={
            "gateway": "CMKTP",
            "trigger": draft.trigger,
            "importance": draft.importance,
            "ask_triggered": False,
            "providers_queried": [],
            "mode": "event_driven_derived",
        },
        trigger=draft.trigger,
    )
