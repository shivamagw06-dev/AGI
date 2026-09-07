"""FMP provider adapter — quotes / OHLCV / fundamentals (normalized)."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.market_data.models import (
    FundamentalSnapshot,
    MarketDataQuote,
    OHLCVBar,
    OHLCVSeries,
)
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError


class FmpProvider(MarketDataProvider):
    provider_id = "fmp"
    priority = 30

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://financialmodelingprep.com/api/v3",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    def capabilities(self) -> set[Capability]:
        return {"quote", "ohlcv", "fundamental"}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.is_configured():
            raise ProviderError(self.provider_id, "missing API key", retryable=False)
        query = dict(params or {})
        query["apikey"] = self.api_key
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                response = await self._client.get(url, params=query)
            else:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.get(url, params=query)
        except httpx.HTTPError as exc:
            raise ProviderError(self.provider_id, f"transport error: {exc}", retryable=True) from exc
        if response.status_code == 429:
            raise ProviderError(self.provider_id, "rate limited by vendor", retryable=True)
        if response.status_code >= 500:
            raise ProviderError(self.provider_id, f"vendor {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise ProviderError(
                self.provider_id,
                f"vendor {response.status_code}: {response.text[:200]}",
                retryable=False,
            )
        return response.json()

    async def get_quote(self, symbol: str) -> MarketDataQuote:
        payload = await self._get(f"/quote/{symbol}")
        row = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(row, dict):
            raise ProviderError(self.provider_id, "unexpected quote payload", retryable=False)
        return MarketDataQuote(
            symbol=str(row.get("symbol") or symbol).upper(),
            exchange=str(row.get("exchange") or "") or None,
            currency=str(row.get("currency") or "") or None,
            last=_num(row.get("price")),
            open=_num(row.get("open")),
            high=_num(row.get("dayHigh")),
            low=_num(row.get("dayLow")),
            previous_close=_num(row.get("previousClose")),
            volume=_num(row.get("volume")),
            change=_num(row.get("change")),
            change_percent=_num(row.get("changesPercentage")),
            provenance=self.make_provenance(vendor_as_of=row.get("timestamp")),
        )

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> OHLCVSeries:
        params: dict[str, Any] = {}
        if start:
            params["from"] = start.isoformat()
        if end:
            params["to"] = end.isoformat()
        # daily-chart endpoint for 1d; intraday uses historical-chart path patterns
        path = f"/historical-price-full/{symbol}" if interval in {"1d", "d", "day"} else f"/historical-chart/{interval}/{symbol}"
        payload = await self._get(path, params)
        rows = []
        if isinstance(payload, dict):
            rows = payload.get("historical") or []
        elif isinstance(payload, list):
            rows = payload
        bars: list[OHLCVBar] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            bars.append(
                OHLCVBar(
                    ts=row.get("date"),
                    open=float(row.get("open")),
                    high=float(row.get("high")),
                    low=float(row.get("low")),
                    close=float(row.get("close")),
                    volume=_num(row.get("volume")),
                )
            )
        return OHLCVSeries(
            symbol=symbol.upper(),
            interval=interval,
            bars=bars,
            provenance=self.make_provenance(),
        )

    async def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        payload = await self._get(f"/key-metrics-ttm/{symbol}")
        row = payload[0] if isinstance(payload, list) and payload else payload
        if not isinstance(row, dict):
            row = {}
        metrics = {
            key: _num(value) if not isinstance(value, str) else value
            for key, value in row.items()
            if key not in {"symbol", "date"}
        }
        return FundamentalSnapshot(
            symbol=symbol.upper(),
            as_of=row.get("date"),
            metrics=metrics,
            provenance=self.make_provenance(vendor_as_of=row.get("date")),
        )


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
