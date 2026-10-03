"""NSE historical collector — bhavcopy, announcements, corporate actions, constituents."""

from __future__ import annotations

from typing import Any

from app.collectors.base import BaseHistoricalCollector
from app.contracts.models import RawHistoricalEvent, Source


def default_nse_fixture(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    return {
        "bhavcopy": [
            {
                "date": f"{y}-01-15",
                "symbol": symbol,
                "open": 100 + y - 2015,
                "high": 105 + y - 2015,
                "low": 98 + y - 2015,
                "close": 102 + y - 2015,
                "volume": 500000,
            }
            for y in range(2018, 2026)
        ],
        "announcements": [
            {
                "date": f"{y}-07-19",
                "subject": f"{symbol} corporate announcement {y}",
                "category": "Result",
            }
            for y in range(2016, 2026)
        ],
        "corporate_actions": [
            {"date": f"{y}-06-01", "action_type": "dividend", "details": f"Final dividend {y}"}
            for y in range(2016, 2026)
        ],
        "index_constituents": [
            {"index": "NIFTY50", "as_of": "2025-03-31", "member": True},
            {"index": "NIFTY IT", "as_of": "2025-03-31", "member": symbol in {"INFY", "TCS"}},
        ],
    }


class NSEHistoricalCollector(BaseHistoricalCollector):
    collector_id = "NSEHistoricalCollector"
    source = Source.NSE
    categories = (
        "daily_ohlcv",
        "corporate_events",
        "corporate_actions",
        "index_constituents",
    )

    def __init__(
        self,
        *,
        symbols: list[str],
        live: bool = False,
        fixture_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.live = live
        self.fixture_payloads = fixture_payloads or {}

    def collect(self, *, ingestion_run_id: str | None = None) -> list[RawHistoricalEvent]:
        events: list[RawHistoricalEvent] = []
        for symbol in self.symbols:
            payload = self.fixture_payloads.get(symbol) or default_nse_fixture(symbol)
            # Live NSE historical bulk is ops-driven; Sprint 8.1 uses archive fixtures / offline packs.
            _ = self.live
            endpoint = f"nse://historical/{symbol}"
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    category="daily_ohlcv",
                    payload={"bhavcopy": payload.get("bhavcopy") or []},
                    company_symbol=symbol,
                    effective_start="2018-01-01",
                    ingestion_run_id=ingestion_run_id,
                )
            )
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    category="corporate_events",
                    payload={"announcements": payload.get("announcements") or []},
                    company_symbol=symbol,
                    ingestion_run_id=ingestion_run_id,
                )
            )
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    category="corporate_actions",
                    payload={"corporate_actions": payload.get("corporate_actions") or []},
                    company_symbol=symbol,
                    ingestion_run_id=ingestion_run_id,
                )
            )
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    category="index_constituents",
                    payload={"index_constituents": payload.get("index_constituents") or []},
                    company_symbol=symbol,
                    ingestion_run_id=ingestion_run_id,
                )
            )
        return events
