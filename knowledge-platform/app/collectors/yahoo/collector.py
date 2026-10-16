"""YahooCollector — market/profile fetch → Raw Events only."""

from __future__ import annotations

from typing import Any

import httpx

from app.collectors.base import BaseCollector
from app.contracts.models import RawEvent, Source


class YahooCollector(BaseCollector):
    collector_id = "YahooCollector"
    source = Source.YAHOO

    def __init__(
        self,
        *,
        symbols: list[str],
        interval_seconds: int = 30,
        live: bool = True,
        base_url: str = "https://query1.finance.yahoo.com",
        fixture_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.interval_seconds = interval_seconds
        self.live = live
        self.base_url = base_url.rstrip("/")
        self.fixture_payloads = fixture_payloads or {}

    def collect(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        for symbol in self.symbols:
            yahoo_symbol = f"{symbol}.NS"
            endpoint = f"{self.base_url}/v8/finance/chart/{yahoo_symbol}"
            payload = self._fetch(symbol, yahoo_symbol, endpoint)
            if payload is None:
                continue
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    payload=payload,
                    company_symbol=symbol,
                )
            )
        return events

    def _fetch(self, symbol: str, yahoo_symbol: str, endpoint: str) -> dict[str, Any] | None:
        if not self.live:
            fixture = self.fixture_payloads.get(symbol) or self.fixture_payloads.get(yahoo_symbol)
            return fixture
        try:
            with httpx.Client(timeout=12.0, headers={"User-Agent": "AGI-KAIP/0.1"}) as client:
                chart = client.get(endpoint, params={"interval": "1d", "range": "1d"})
                chart.raise_for_status()
                chart_json = chart.json()
                summary_url = (
                    f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yahoo_symbol}"
                )
                summary = client.get(
                    summary_url,
                    params={
                        "modules": "assetProfile,summaryDetail,defaultKeyStatistics,price,financialData"
                    },
                )
                summary_json = summary.json() if summary.status_code == 200 else {}
                return {
                    "yahoo_symbol": yahoo_symbol,
                    "chart": chart_json,
                    "quote_summary": summary_json,
                }
        except Exception:
            fixture = self.fixture_payloads.get(symbol)
            return fixture
