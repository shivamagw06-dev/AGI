"""BSE historical collector — announcements and corporate actions."""

from __future__ import annotations

from typing import Any

from app.collectors.base import BaseHistoricalCollector
from app.contracts.models import RawHistoricalEvent, Source


def default_bse_fixture(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    return {
        "announcements": [
            {
                "date": f"{y}-07-20",
                "subject": f"{symbol} BSE filing {y}",
                "category": "Board Meeting",
            }
            for y in range(2017, 2026)
        ],
        "corporate_actions": [
            {"date": f"{y}-08-01", "action_type": "bonus", "details": f"Bonus issue record {y}"}
            for y in (2018, 2022)
        ],
    }


class BSEHistoricalCollector(BaseHistoricalCollector):
    collector_id = "BSEHistoricalCollector"
    source = Source.BSE
    categories = ("corporate_events", "corporate_actions")

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
        _ = self.live
        events: list[RawHistoricalEvent] = []
        for symbol in self.symbols:
            payload = self.fixture_payloads.get(symbol) or default_bse_fixture(symbol)
            endpoint = f"bse://historical/{symbol}"
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
        return events
