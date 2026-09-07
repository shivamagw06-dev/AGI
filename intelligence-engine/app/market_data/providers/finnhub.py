"""Finnhub provider adapter — quotes / calendar / economics (normalized)."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.market_data.models import (
    CalendarEvent,
    EconomicSeries,
    EconomicSeriesPoint,
    MarketDataQuote,
)
from app.market_data.provider_base import Capability, MarketDataProvider, ProviderError


class FinnhubProvider(MarketDataProvider):
    provider_id = "finnhub"
    priority = 20

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://finnhub.io/api/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    def capabilities(self) -> set[Capability]:
        return {"quote", "calendar_event", "economic_series"}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.is_configured():
            raise ProviderError(self.provider_id, "missing API key", retryable=False)
        query = dict(params or {})
        query["token"] = self.api_key
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
        payload = await self._get("/quote", {"symbol": symbol})
        if not isinstance(payload, dict):
            raise ProviderError(self.provider_id, "unexpected quote payload", retryable=False)
        return MarketDataQuote(
            symbol=symbol.upper(),
            last=_num(payload.get("c")),
            open=_num(payload.get("o")),
            high=_num(payload.get("h")),
            low=_num(payload.get("l")),
            previous_close=_num(payload.get("pc")),
            change=_num(payload.get("d")),
            change_percent=_num(payload.get("dp")),
            provenance=self.make_provenance(vendor_as_of=payload.get("t")),
        )

    async def get_calendar_events(
        self,
        *,
        symbol: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CalendarEvent]:
        params: dict[str, Any] = {}
        if start:
            params["from"] = start.isoformat()
        if end:
            params["to"] = end.isoformat()
        payload = await self._get("/calendar/earnings", params)
        rows = []
        if isinstance(payload, dict):
            rows = payload.get("earningsCalendar") or []
        events: list[CalendarEvent] = []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "")
            if symbol and sym.upper() != symbol.upper():
                continue
            events.append(
                CalendarEvent(
                    event_id=f"finnhub-earn-{sym}-{row.get('date')}-{idx}",
                    event_type="earnings",
                    symbol=sym or None,
                    title=f"Earnings {sym}",
                    event_time=row.get("date"),
                    country=None,
                    details={
                        "eps_estimate": row.get("epsEstimate"),
                        "revenue_estimate": row.get("revenueEstimate"),
                    },
                    provenance=self.make_provenance(vendor_as_of=row.get("date")),
                )
            )
        return events

    async def get_economic_series(self, series_id: str) -> EconomicSeries:
        # Finnhub economic endpoint varies by plan; normalize a list-or-dict payload.
        payload = await self._get("/economic", {"code": series_id})
        points: list[EconomicSeriesPoint] = []
        rows = payload if isinstance(payload, list) else []
        for row in rows:
            if isinstance(row, list) and len(row) >= 2:
                points.append(EconomicSeriesPoint(ts=str(row[0]), value=_num(row[1])))
            elif isinstance(row, dict):
                points.append(
                    EconomicSeriesPoint(
                        ts=str(row.get("time") or row.get("date")),
                        value=_num(row.get("value")),
                    )
                )
        return EconomicSeries(
            series_id=series_id,
            name=series_id,
            points=points,
            provenance=self.make_provenance(),
        )


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
