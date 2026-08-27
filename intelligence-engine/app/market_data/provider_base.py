"""Provider abstraction interface (WBS DATA-001)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Literal

from app.market_data.models import (
    CalendarEvent,
    CorporateAction,
    EconomicSeries,
    FundamentalSnapshot,
    MarketDataQuote,
    OHLCVSeries,
    OptionChain,
    Provenance,
    utcnow,
)

Capability = Literal[
    "quote",
    "ohlcv",
    "corporate_action",
    "fundamental",
    "option_chain",
    "economic_series",
    "calendar_event",
]


class ProviderError(Exception):
    def __init__(
        self,
        provider_id: str,
        message: str,
        *,
        retryable: bool = True,
        cooldown_s: float | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.retryable = retryable
        # How long to park the provider when this failure is permanent. A
        # revoked key should sit out far longer than a rate limit, which
        # resets on its own. None means use the breaker's default.
        self.cooldown_s = cooldown_s
        super().__init__(f"{provider_id}: {message}")


class MarketDataProvider(ABC):
    """Third-party adapter. Must normalize into canonical models only."""

    provider_id: str
    priority: int = 100  # lower = preferred

    @abstractmethod
    def capabilities(self) -> set[Capability]:
        raise NotImplementedError

    def is_configured(self) -> bool:
        return True

    def make_provenance(
        self,
        *,
        vendor_as_of: Any = None,
        request_id: str | None = None,
        cache_hit: bool = False,
    ) -> Provenance:
        return Provenance(
            source=self.provider_id,
            provider_id=self.provider_id,
            pulled_at=utcnow(),
            vendor_as_of=vendor_as_of,
            request_id=request_id,
            cache_hit=cache_hit,
        )

    async def get_quote(self, symbol: str) -> MarketDataQuote:
        raise ProviderError(self.provider_id, "quote not supported", retryable=False)

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> OHLCVSeries:
        raise ProviderError(self.provider_id, "ohlcv not supported", retryable=False)

    async def get_corporate_actions(self, symbol: str) -> list[CorporateAction]:
        raise ProviderError(self.provider_id, "corporate_action not supported", retryable=False)

    async def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        raise ProviderError(self.provider_id, "fundamental not supported", retryable=False)

    async def get_option_chain(self, underlying: str) -> OptionChain:
        raise ProviderError(self.provider_id, "option_chain not supported", retryable=False)

    async def get_economic_series(self, series_id: str) -> EconomicSeries:
        raise ProviderError(self.provider_id, "economic_series not supported", retryable=False)

    async def get_calendar_events(
        self,
        *,
        symbol: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarEvent]:
        raise ProviderError(self.provider_id, "calendar_event not supported", retryable=False)

    async def ping(self) -> bool:
        return self.is_configured()
