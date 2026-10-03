"""CompanyIRCollector — IR page discovery → Raw Events."""

from __future__ import annotations

from typing import Any

from app.collectors.base import BaseCollector
from app.contracts.models import RawEvent, Source


# Seed IR endpoints for Sprint 6.1 watchlist — acquisition only.
DEFAULT_IR_ENDPOINTS: dict[str, str] = {
    "INFY": "https://www.infosys.com/investors.html",
    "TCS": "https://www.tcs.com/investor-relations",
    "RELIANCE": "https://www.ril.com/InvestorRelations.aspx",
    "HDFCBANK": "https://www.hdfcbank.com/personal/about-us/investor-relations",
}


class CompanyIRCollector(BaseCollector):
    collector_id = "CompanyIRCollector"
    source = Source.COMPANY_IR

    def __init__(
        self,
        *,
        symbols: list[str],
        interval_seconds: int = 86400,
        live: bool = True,
        endpoints: dict[str, str] | None = None,
        fixture_payloads: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.interval_seconds = interval_seconds
        self.live = live
        self.endpoints = endpoints or DEFAULT_IR_ENDPOINTS
        self.fixture_payloads = fixture_payloads or {}

    def collect(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        for symbol in self.symbols:
            endpoint = self.endpoints.get(symbol)
            if not endpoint:
                continue
            payload = self.fixture_payloads.get(symbol) or {
                "company_symbol": symbol,
                "ir_url": endpoint,
                "discovered": True,
                "documents": [],
            }
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    payload=payload,
                    company_symbol=symbol,
                )
            )
        return events
