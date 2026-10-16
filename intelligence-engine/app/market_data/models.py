"""Canonical, versioned market-data objects (Architecture v1.0.1 / E00 §2.1).

No engine may consume provider-native responses.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provenance(BaseModel):
    """Pull stamping — WBS DATA-005."""

    model_config = ConfigDict(extra="forbid")

    source: str
    provider_id: str
    pulled_at: datetime
    vendor_as_of: datetime | date | str | None = None
    request_id: str | None = None
    cache_hit: bool = False


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_type: str
    schema_version: str
    provenance: Provenance


class MarketDataQuote(CanonicalModel):
    object_type: Literal["MarketDataQuote"] = "MarketDataQuote"
    schema_version: Literal["market_data.quote.v1"] = "market_data.quote.v1"
    symbol: str
    exchange: str | None = None
    currency: str | None = None
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    change: float | None = None
    change_percent: float | None = None
    session_date: date | None = None


class OHLCVBar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime | date | str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class OHLCVSeries(CanonicalModel):
    object_type: Literal["OHLCV"] = "OHLCV"
    schema_version: Literal["market_data.ohlcv.v1"] = "market_data.ohlcv.v1"
    symbol: str
    interval: str
    bars: list[OHLCVBar] = Field(default_factory=list)


class CorporateAction(CanonicalModel):
    object_type: Literal["CorporateAction"] = "CorporateAction"
    schema_version: Literal["market_data.corporate_action.v1"] = "market_data.corporate_action.v1"
    symbol: str
    action_type: str
    ex_date: date | str | None = None
    record_date: date | str | None = None
    pay_date: date | str | None = None
    ratio: float | None = None
    amount: float | None = None
    currency: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FundamentalSnapshot(CanonicalModel):
    object_type: Literal["FundamentalSnapshot"] = "FundamentalSnapshot"
    schema_version: Literal["market_data.fundamental.v1"] = "market_data.fundamental.v1"
    symbol: str
    as_of: date | str | None = None
    currency: str | None = None
    metrics: dict[str, float | int | str | None] = Field(default_factory=dict)


class OptionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    expiry: date | str
    strike: float
    option_type: Literal["call", "put"]
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: float | None = None
    open_interest: float | None = None
    iv: float | None = None


class OptionChain(CanonicalModel):
    object_type: Literal["OptionChain"] = "OptionChain"
    schema_version: Literal["market_data.option_chain.v1"] = "market_data.option_chain.v1"
    underlying: str
    as_of: datetime | date | str | None = None
    contracts: list[OptionContract] = Field(default_factory=list)


class EconomicSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: date | str
    value: float | None = None


class EconomicSeries(CanonicalModel):
    object_type: Literal["EconomicSeries"] = "EconomicSeries"
    schema_version: Literal["market_data.economic_series.v1"] = "market_data.economic_series.v1"
    series_id: str
    name: str | None = None
    unit: str | None = None
    frequency: str | None = None
    points: list[EconomicSeriesPoint] = Field(default_factory=list)


class CalendarEvent(CanonicalModel):
    object_type: Literal["CalendarEvent"] = "CalendarEvent"
    schema_version: Literal["market_data.calendar_event.v1"] = "market_data.calendar_event.v1"
    event_id: str
    event_type: str
    symbol: str | None = None
    title: str
    event_time: datetime | date | str | None = None
    country: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
