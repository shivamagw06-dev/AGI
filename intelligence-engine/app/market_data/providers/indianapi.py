"""IndianAPI provider adapter — quotes / OHLCV / calendar (normalized)."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.market_data.models import (
    CalendarEvent,
    MarketDataQuote,
    OHLCVBar,
    OHLCVSeries,
)
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError


class IndianApiProvider(MarketDataProvider):
    provider_id = "indianapi"
    priority = 10

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://stock.indianapi.in",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    def capabilities(self) -> set[Capability]:
        return {"quote", "ohlcv", "calendar_event"}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.is_configured():
            raise ProviderError(self.provider_id, "missing API key", retryable=False)
        query = dict(params or {})
        headers = {"x-api-key": self.api_key, "Accept": "application/json"}
        url = f"{self.base_url}{path}"
        try:
            if self._client is not None:
                response = await self._client.get(url, params=query, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.get(url, params=query, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderError(self.provider_id, f"transport error: {exc}", retryable=True) from exc
        if response.status_code == 429:
            # Immediate retries amplify vendor throttling and delay the user;
            # fail over to the next configured provider for this request.
            raise ProviderError(self.provider_id, "rate limited by vendor", retryable=False)
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
        payload = await self._get("/stock", {"name": symbol})
        if not isinstance(payload, dict):
            raise ProviderError(self.provider_id, "unexpected quote payload", retryable=False)
        price = _num(payload.get("currentPrice") or payload.get("price") or payload.get("lastPrice"))
        return MarketDataQuote(
            symbol=str(payload.get("ticker") or payload.get("symbol") or symbol).upper(),
            exchange=str(payload.get("exchange") or "NSE"),
            currency="INR",
            last=price,
            open=_num(payload.get("open")),
            high=_num(payload.get("dayHigh") or payload.get("high")),
            low=_num(payload.get("dayLow") or payload.get("low")),
            previous_close=_num(payload.get("previousClose") or payload.get("close")),
            volume=_num(payload.get("volume")),
            change=_num(payload.get("change")),
            change_percent=_num(payload.get("pChange") or payload.get("percent_change")),
            provenance=self.make_provenance(vendor_as_of=payload.get("lastUpdateTime")),
        )

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        interval: str = "1d",
        start: date | None = None,
        end: date | None = None,
    ) -> OHLCVSeries:
        params: dict[str, Any] = {"name": symbol, "period": interval}
        if start:
            params["start"] = start.isoformat()
        if end:
            params["end"] = end.isoformat()
        payload = await self._get("/historical_data", params)
        rows = payload if isinstance(payload, list) else payload.get("datasets") or payload.get("data") or []
        bars: list[OHLCVBar] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                bars.append(
                    OHLCVBar(
                        ts=row.get("date") or row.get("time") or row.get("timestamp"),
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

    async def get_calendar_events(
        self,
        *,
        symbol: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarEvent]:
        params: dict[str, Any] = {}
        if symbol:
            params["name"] = symbol
        payload = await self._get("/corporate_actions", params) if symbol else []
        events: list[CalendarEvent] = []
        rows = payload if isinstance(payload, list) else []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            events.append(
                CalendarEvent(
                    event_id=str(row.get("id") or f"indianapi-{symbol}-{idx}"),
                    event_type=str(row.get("type") or row.get("purpose") or "corporate"),
                    symbol=symbol,
                    title=str(row.get("purpose") or row.get("type") or "event"),
                    event_time=row.get("date") or row.get("ex_date"),
                    country="IN",
                    details={"raw_keys": sorted(row.keys())},
                    provenance=self.make_provenance(vendor_as_of=row.get("date")),
                )
            )
        return events


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
