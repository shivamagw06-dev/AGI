"""HMKIP contracts — Historical Market Intelligence Platform (Sprint 12.2).

Programme short is HMKIP to avoid collision with Historical Macro Intelligence (HMIP).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

HMKIP_VERSION = "0.1.0"
PROGRAMME = "Historical Market Intelligence Platform"
PROGRAMME_SHORT = "HMKIP"
PRIMARY_PRINCIPLE = (
    "Historical market knowledge is immutable institutional memory. "
    "Analysis consumes the Historical Market Knowledge Store — never external providers."
)

MarketCategory = Literal[
    "Cycles",
    "Breadth",
    "Liquidity",
    "Volatility",
    "Flows",
    "Leadership",
    "CrossAsset",
    "Health",
    "Events",
]

STORAGE_NAMESPACES: tuple[str, ...] = (
    "historical_market",
    "historical_market_cycles",
    "historical_market_breadth",
    "historical_market_liquidity",
    "historical_market_volatility",
    "historical_market_flows",
    "historical_market_leadership",
    "historical_market_cross_asset",
)

CATEGORY_TO_NAMESPACE: dict[str, str] = {
    "Cycles": "historical_market_cycles",
    "Breadth": "historical_market_breadth",
    "Liquidity": "historical_market_liquidity",
    "Volatility": "historical_market_volatility",
    "Flows": "historical_market_flows",
    "Leadership": "historical_market_leadership",
    "CrossAsset": "historical_market_cross_asset",
    "Health": "historical_market",
    "Events": "historical_market_cycles",
}

NO_HMKIP_ACTIONS = (
    "overwrite_historical_records",
    "call_external_providers_during_analysis",
    "fetch_during_ask",
    "mutate_published_hmkto",
    "recommend_buy_sell",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "hmkip") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def checksum_for(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def namespace_for(category: str) -> str:
    return CATEGORY_TO_NAMESPACE.get(category, "historical_market")


class RawHistoricalMarketObservation(BaseModel):
    observation_id: str = Field(default_factory=lambda: new_id("hmraw"))
    source: str
    market_key: str
    market_label: str
    category: str
    indicator: str
    value: float | None = None
    period: str
    previous: float | None = None
    unit: str = ""
    market_regime: str | None = None
    breadth_state: str | None = None
    liquidity_state: str | None = None
    volatility_state: str | None = None
    institutional_flows: str | None = None
    leadership: str | None = None
    cross_asset_state: str | None = None
    major_events: list[str] = Field(default_factory=list)
    publication_date: str
    effective_date: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=utc_now)


class HistoricalMarketKnowledgeObject(BaseModel):
    """Immutable historical market observation — never overwritten; revisions append."""

    hmkto_id: str = Field(default_factory=lambda: new_id("hmkto"))
    market_key: str
    market_label: str
    category: str
    indicator: str
    value: float | None = None
    period: str
    previous: float | None = None
    unit: str = ""
    source: str
    market_regime: str | None = None
    breadth_state: str | None = None
    liquidity_state: str | None = None
    volatility_state: str | None = None
    institutional_flows: str | None = None
    leadership: str | None = None
    cross_asset_state: str | None = None
    major_events: list[str] = Field(default_factory=list)
    publication_date: str
    effective_date: str | None = None
    version: int = 1
    parent_hmkto_id: str | None = None
    historical_confidence: float = 0.9
    provenance: dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""
    namespace: str = "historical_market"
    revision_note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = HMKIP_VERSION
    immutable: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["overwritable"] = False
        data["providers_queried"] = []
        data["collected_on_request"] = False
        return data


class TimelineNode(BaseModel):
    year: int | None = None
    period: str
    label: str
    value: float | None = None
    importance: str = "Medium"
    event: str | None = None
    hmkto_id: str | None = None
    market_regime: str | None = None


class MarketTimeline(BaseModel):
    market_key: str
    market_label: str
    indicator: str
    nodes: list[TimelineNode] = Field(default_factory=list)
    years_span: list[int] = Field(default_factory=list)
    missing_periods: list[str] = Field(default_factory=list)
    completeness_pct: float = 0.0
    namespace: str = "historical_market"

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
