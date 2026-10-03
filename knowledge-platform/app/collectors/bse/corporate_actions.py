"""BSECorporateActionCollector — corporate actions → Raw Events."""

from __future__ import annotations

from typing import Any

from app.collectors.base import BaseCollector
from app.contracts.models import RawEvent, Source


class BSECorporateActionCollector(BaseCollector):
    collector_id = "BSECorporateActionCollector"
    source = Source.BSE

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
        endpoint = "https://api.bseindia.com/BseIndiaAPI/api/DefaultData/w"
        events: list[RawEvent] = []
        for row in self.fixture_rows:
            symbol = str(row.get("symbol") or row.get("scrip_code") or "").upper()
            if self.symbols and symbol and symbol not in {s.upper() for s in self.symbols}:
                # allow scrip-code fixtures that carry company_symbol
                symbol = str(row.get("company_symbol") or symbol).upper()
                if symbol not in self.symbols:
                    continue
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    payload=row,
                    company_symbol=str(row.get("company_symbol") or symbol or None),
                )
            )
        return events
