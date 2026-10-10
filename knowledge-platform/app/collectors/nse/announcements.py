"""NSEAnnouncementCollector — corporate announcements → Raw Events."""

from __future__ import annotations

from typing import Any

import httpx

from app.collectors.base import BaseCollector
from app.contracts.models import RawEvent, Source


class NSEAnnouncementCollector(BaseCollector):
    collector_id = "NSEAnnouncementCollector"
    source = Source.NSE

    def __init__(
        self,
        *,
        symbols: list[str],
        interval_seconds: int = 30,
        live: bool = True,
        fixture_payloads: list[dict[str, Any]] | None = None,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.interval_seconds = interval_seconds
        self.live = live
        self.fixture_payloads = fixture_payloads or []

    def collect(self) -> list[RawEvent]:
        events: list[RawEvent] = []
        endpoint = "https://www.nseindia.com/api/corporate-announcements"
        rows = self._fetch(endpoint)
        for row in rows:
            symbol = str(row.get("symbol") or row.get("company_symbol") or "").upper()
            if self.symbols and symbol and symbol not in self.symbols:
                continue
            events.append(
                self.make_event(
                    endpoint=endpoint,
                    payload=row,
                    company_symbol=symbol or None,
                )
            )
        return events

    def _fetch(self, endpoint: str) -> list[dict[str, Any]]:
        if not self.live:
            return list(self.fixture_payloads)
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; AGI-KAIP/0.1)",
                "Accept": "application/json",
            }
            with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
                client.get("https://www.nseindia.com/")
                resp = client.get(endpoint)
                if resp.status_code != 200:
                    return list(self.fixture_payloads)
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    for key in ("data", "announcements", "rows"):
                        if isinstance(data.get(key), list):
                            return data[key]
                return list(self.fixture_payloads)
        except Exception:
            return list(self.fixture_payloads)
