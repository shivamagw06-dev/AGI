"""CMKTP contracts — Continuous Market Knowledge Platform (Sprint 12.1).

Programme short is CMKTP to avoid collision with Continuous Macro Knowledge (CMKP).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

CMKTP_VERSION = "0.1.0"
PROGRAMME = "Continuous Market Knowledge Platform"
PROGRAMME_SHORT = "CMKTP"
PRIMARY_PRINCIPLE = (
    "CMKTP is not a market data service. It transforms live market tips into institutional "
    "Market Knowledge Objects — regime, breadth, liquidity, leadership, risk sentiment and "
    "market health — that downstream systems consume. User requests never trigger collection."
)

RegimeLabel = Literal[
    "Bull",
    "Bear",
    "Sideways",
    "Recovery",
    "Capitulation",
    "Distribution",
    "Expansion",
    "Contraction",
    "Unknown",
]
RiskSentiment = Literal[
    "Risk On",
    "Risk Off",
    "Defensive Rotation",
    "Growth Rotation",
    "Value Rotation",
    "Mixed",
    "Unknown",
]
Trend = Literal["Improving", "Stable", "Deteriorating", "Mixed", "Unknown"]
Importance = Literal["Critical", "High", "Medium", "Low"]
MaterialityTier = Literal["Ignore", "Low", "Medium", "High", "Critical"]

# Domain universe — each publishes a Market Knowledge Object slice
MARKET_UNIVERSE: tuple[str, ...] = (
    "india_equity",
    "global_equity",
    "breadth",
    "liquidity",
    "volatility",
    "institutional_flows",
    "leadership",
    "cross_asset",
    "risk_sentiment",
    "market_health",
)

MARKET_ALIASES: dict[str, str] = {
    "nifty": "india_equity",
    "nifty50": "india_equity",
    "sensex": "india_equity",
    "india": "india_equity",
    "india_equity": "india_equity",
    "bank_nifty": "india_equity",
    "global": "global_equity",
    "global_equity": "global_equity",
    "spx": "global_equity",
    "nasdaq": "global_equity",
    "breadth": "breadth",
    "advance_decline": "breadth",
    "liquidity": "liquidity",
    "volume": "liquidity",
    "volatility": "volatility",
    "vix": "volatility",
    "flows": "institutional_flows",
    "fii": "institutional_flows",
    "dii": "institutional_flows",
    "institutional_flows": "institutional_flows",
    "leadership": "leadership",
    "rotation": "leadership",
    "sectors": "leadership",
    "cross_asset": "cross_asset",
    "commodities": "cross_asset",
    "fx": "cross_asset",
    "risk": "risk_sentiment",
    "risk_sentiment": "risk_sentiment",
    "sentiment": "risk_sentiment",
    "health": "market_health",
    "market_health": "market_health",
    "regime": "india_equity",
}

NO_CMKTP_ACTIONS = (
    "call_external_providers_on_ask",
    "fetch_during_ask",
    "rebuild_on_user_query",
    "serve_raw_quotes_as_knowledge",
    "recommend_buy_sell",
    "set_target_prices",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "cmktp") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def canonicalize(name: str | None) -> str | None:
    if not name:
        return None
    key = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    return MARKET_ALIASES.get(key, key if key in MARKET_UNIVERSE else None)


class RawMarketDraft(BaseModel):
    domain_key: str
    label: str
    trigger: str = "ops_refresh"
    importance: Importance = "Medium"
    catalog: dict[str, Any] = Field(default_factory=dict)
    groww_tip: dict[str, Any] = Field(default_factory=dict)
    yahoo_tip: dict[str, Any] = Field(default_factory=dict)
    macro_tip: dict[str, Any] = Field(default_factory=dict)
    sector_tip: dict[str, Any] = Field(default_factory=dict)
    company_tip: dict[str, Any] = Field(default_factory=dict)
    fpi_tip: dict[str, Any] = Field(default_factory=dict)
    computed: dict[str, Any] = Field(default_factory=dict)
    providers_queried: list[str] = Field(default_factory=list)
    ask_triggered: bool = False


class MarketKnowledgeObject(BaseModel):
    """Published institutional market knowledge — versioned."""

    mkto_id: str = Field(default_factory=lambda: new_id("mkto"))
    domain_key: str
    label: str
    market_regime: RegimeLabel = "Unknown"
    breadth: dict[str, Any] = Field(default_factory=dict)
    liquidity: dict[str, Any] = Field(default_factory=dict)
    volatility: dict[str, Any] = Field(default_factory=dict)
    institutional_flows: dict[str, Any] = Field(default_factory=dict)
    leadership: dict[str, Any] = Field(default_factory=dict)
    cross_asset_state: dict[str, Any] = Field(default_factory=dict)
    risk_sentiment: RiskSentiment = "Unknown"
    market_health: dict[str, Any] = Field(default_factory=dict)
    health_score: float = 50.0
    summary: str | None = None
    trend: Trend = "Unknown"
    confidence: float = 0.7
    knowledge_freshness_sec: int = 0
    materiality_tier: MaterialityTier = "Low"
    materiality_score: float = 0.0
    learning_generated: bool = False
    version: int = 1
    parent_mkto_id: str | None = None
    source_layers: list[str] = Field(default_factory=list)
    normalized: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = CMKTP_VERSION
    trigger: str = "ops_refresh"

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        data["collected_on_request"] = False
        data["constructed_on_request"] = False
        data["is_recommendation"] = False
        return data


class MarketLearningEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("mlearn"))
    domain_key: str
    summary: str
    tier: MaterialityTier
    reason: str
    trigger: str
    created_at: datetime = Field(default_factory=utc_now)

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
