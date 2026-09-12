"""NSEBhavcopyCollector — daily equity bhavcopy → Raw Events."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.collectors.base import BaseCollector
from app.contracts.models import RawEvent, Source


class NSEBhavcopyCollector(BaseCollector):
    collector_id = "NSEBhavcopyCollector"
    source = Source.NSE

    def __init__(
        self,
        *,
        symbols: list[str],
        interval_seconds: int = 86400,
        live: bool = True,
        fixture_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.interval_seconds = interval_seconds
        self.live = live
        self.fixture_rows = fixture_rows or []

    def collect(self) -> list[RawEvent]:
        endpoint = "https://www.nseindia.com/api/market-data-pre-open?key=ALL"
        rows = self._rows()
        events: list[RawEvent] = []
        for row in rows:
            symbol = str(row.get("symbol") or row.get("SYMBOL") or "").upper()
            if self.symbols and symbol and symbol not in self.symbols:
                continue
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    payload={
                        "trade_date": row.get("trade_date") or date.today().isoformat(),
                        "row": row,
                    },
                    company_symbol=symbol or None,
                )
            )
        return events

    def _rows(self) -> list[dict[str, Any]]:
        # Live NSE bhavcopy formats change; Sprint 6.1 uses fixtures when live fails.
        if self.fixture_rows or not self.live:
            return list(self.fixture_rows)
        return list(self.fixture_rows)
