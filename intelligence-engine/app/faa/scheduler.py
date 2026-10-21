"""Continuous acquisition scheduler — institutional cadences."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEDULE = [
    {"stream": "daily_research", "cadence": "01:00_IST_daily_bounded_60_minutes", "connectors": ["company_ir", "nse", "bse", "sebi", "rbi", "mca", "pib", "news", "rss", "search_api"]},
    {"stream": "evening_filings", "cadence": "18:00_IST_daily_bounded_15_minutes", "connectors": ["nse", "bse", "sebi", "rbi", "company_ir"]},
]

WATCHLIST_QUERIES = [
    "Reliance Industries annual report filings news",
    "Infosys quarterly results guidance transcript",
    "TCS investor presentation and filings",
    "HDFC Bank exchange filings and news",
    "RBI monetary policy press release",
    "SEBI notifications latest",
]

EVENING_FILINGS_QUERIES = [
    "NSE BSE material corporate announcements latest",
    "SEBI RBI regulatory notifications latest",
    "company investor relations results filings latest India",
]


class FaaScheduler:
    def __init__(self) -> None:
        self.enabled = True
        self.last_run_at: str | None = None
        self.runs: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "schedule": SCHEDULE,
            "watchlist_queries": WATCHLIST_QUERIES,
            "last_run_at": self.last_run_at,
            "recent_runs": self.runs[-30:],
        }

    def mark_run(self, stream: str, **kwargs: Any) -> dict[str, Any]:
        row = {
            "stream": stream,
            "at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self.last_run_at = row["at"]
        self.runs.append(row)
        self.runs = self.runs[-120:]
        return row
