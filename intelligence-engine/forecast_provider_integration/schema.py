"""Forecast Provider Integration contracts — India-first, Knowledge-Platform-first."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

FPI_VERSION = "0.1.0"
PROGRAMME = "Forecast Provider Integration"
PROGRAMME_SHORT = "FPI"
PRIMARY_PRINCIPLE = (
    "External providers supply raw market information. "
    "The Knowledge Platform transforms it into institutional knowledge. "
    "Forecast Intelligence never reasons over raw APIs."
)

ProviderId = Literal["groww", "yahoo", "nse", "bse", "company_ir"]

PROVIDER_PRIORITY: tuple[dict[str, Any], ...] = (
    {
        "provider": "groww",
        "role": "primary_live_market",
        "priority": 1,
        "uses": [
            "ltp",
            "ohlc",
            "intraday_candles",
            "market_depth",
            "bid_ask",
            "volume",
            "vwap",
            "open_interest",
            "index_quotes",
            "websocket_streaming",
            "live_market_status",
        ],
        "does_not": [
            "financial_statements",
            "income_statement",
            "balance_sheet",
            "cash_flow",
            "analyst_estimates",
            "historical_institutional_research",
        ],
    },
    {
        "provider": "yahoo",
        "role": "research_and_historical",
        "priority": 2,
        "uses": [
            "company_profile",
            "financial_statements",
            "earnings",
            "historical_ohlc",
            "dividends_splits",
            "recommendations",
            "holders",
            "news_calendar",
        ],
        "does_not": ["poll_every_few_seconds", "primary_live_ltp_when_groww_available"],
    },
    {
        "provider": "nse",
        "role": "official_disclosure",
        "priority": 3,
        "uses": ["corporate_announcements", "filings", "bhavcopy", "earnings_releases", "exchange_notices"],
    },
    {
        "provider": "bse",
        "role": "corporate_actions",
        "priority": 4,
        "uses": ["corporate_actions", "announcements", "exchange_notices"],
    },
    {
        "provider": "company_ir",
        "role": "official_documents",
        "priority": 5,
        "uses": [
            "annual_reports",
            "quarterly_reports",
            "investor_presentations",
            "earnings_transcripts",
            "esg_governance",
        ],
    },
)

# Refresh policy (seconds) — collectors / knowledge platform side
REFRESH_POLICY: dict[str, dict[str, Any]] = {
    "groww_live_market": {
        "mode": "websocket_market_hours",
        "snapshot_interval_sec": 45,
        "stale_after_sec": 60,
        "fallback": "yahoo",
        "fallback_only_if_groww_unavailable": True,
    },
    "yahoo_fundamentals": {
        "mode": "daily",
        "stale_after_sec": 86400,
        "immediate_triggers": ["earnings"],
    },
    "yahoo_financial_statements": {
        "mode": "event_triggered",
        "triggers": ["quarterly_results", "annual_results"],
        "stale_after_sec": 7 * 86400,
    },
    "nse_corporate_events": {
        "interval_sec": 30,
        "stale_after_sec": 90,
    },
    "bse_corporate_events": {
        "interval_sec": 30,
        "stale_after_sec": 90,
    },
    "company_ir_documents": {
        "market_hours_interval_sec": 600,
        "off_hours_interval_sec": 3600,
        "stale_after_sec": 3600,
    },
}

FORECAST_FORBIDDEN_DIRECT_CALLS = ("groww", "yahoo", "nse", "bse", "company_ir")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "fpi") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class MarketSnapshot(BaseModel):
    """Dynamic market state published into AGI knowledge (Groww-primary)."""

    snapshot_id: str = Field(default_factory=lambda: new_id("msnap"))
    entity: str
    scope: str = "company"  # company | market | index
    ltp: float | None = None
    change_pct: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    vwap: float | None = None
    bid: float | None = None
    ask: float | None = None
    market_depth: dict[str, Any] = Field(default_factory=dict)
    index_move_pct: float | None = None
    market_status: str = "unknown"  # open | closed | pre | post | unknown
    source_provider: str = "groww"
    fallback_used: bool = False
    published_at: datetime = Field(default_factory=utc_now)
    as_of: datetime = Field(default_factory=utc_now)
    freshness_sec: int = 0
    stale: bool = False
    websocket: bool = False
    note: str = "AGI-owned market snapshot — not a raw provider payload for forecasting."

    def to_public_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class StaticKnowledge(BaseModel):
    """Slow-changing institutional knowledge (Yahoo / IR / NSE / BSE)."""

    business_profile: dict[str, Any] = Field(default_factory=dict)
    financial_statements: dict[str, Any] = Field(default_factory=dict)
    historical_financials: dict[str, Any] = Field(default_factory=dict)
    historical_valuation: dict[str, Any] = Field(default_factory=dict)
    historical_ratios: dict[str, Any] = Field(default_factory=dict)
    historical_ownership: dict[str, Any] = Field(default_factory=dict)
    historical_relationships: list[dict[str, Any]] = Field(default_factory=list)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    research: dict[str, Any] = Field(default_factory=dict)
    primary_sources: list[str] = Field(default_factory=lambda: ["yahoo", "company_ir", "nse", "bse"])
    updated_at: datetime = Field(default_factory=utc_now)
    freshness_sec: int = 0


class DynamicMarketState(BaseModel):
    """Fast-changing market state (Groww WebSocket / snapshot)."""

    snapshot: MarketSnapshot | None = None
    primary_source: str = "groww"
    fallback_source: str = "yahoo"
    updated_at: datetime | None = None
    stale: bool = True


class CompanyKnowledgeObject(BaseModel):
    """Company Knowledge with explicit static vs dynamic layers."""

    entity: str
    static: StaticKnowledge = Field(default_factory=StaticKnowledge)
    dynamic: DynamicMarketState = Field(default_factory=DynamicMarketState)
    knowledge_confidence: float = 0.7
    published_at: datetime = Field(default_factory=utc_now)
    version: str = FPI_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["layers"] = {"static": True, "dynamic_market_state": True}
        data["forecast_may_direct_call_providers"] = False
        return data


class ProviderHealth(BaseModel):
    provider: ProviderId | str
    status: str  # healthy | degraded | unavailable | unknown
    configured: bool = False
    connection: str = "unknown"
    latency_ms: float | None = None
    websocket_latency_ms: float | None = None
    snapshot_freshness_sec: int | None = None
    knowledge_freshness_sec: int | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    failover_events: int = 0
    detail: str = ""
    role: str = ""


class FailoverEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("fail"))
    from_provider: str
    to_provider: str
    reason: str
    entity: str | None = None
    at: datetime = Field(default_factory=utc_now)
