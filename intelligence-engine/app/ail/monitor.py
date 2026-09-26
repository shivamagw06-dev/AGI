"""Continuous Monitoring Engine (CME) — watchlists + institutional cadences."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

SCHEDULE = [
    {"stream": "exchange_filings", "cadence": "every_5_minutes"},
    {"stream": "news", "cadence": "every_5_minutes"},
    {"stream": "government", "cadence": "hourly"},
    {"stream": "annual_reports", "cadence": "daily"},
    {"stream": "investor_relations", "cadence": "daily"},
]


class ContinuousMonitoringEngine:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.last_run_at: str | None = None
        self.runs: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        return {
            "programme": "CME",
            "schedule": SCHEDULE,
            "watchlists": dict(self.store.watchlists),
            "last_run_at": self.last_run_at,
            "recent_runs": self.runs[-30:],
        }

    def set_watchlist(self, name: str, tickers: list[str]) -> dict[str, Any]:
        self.store.watchlists[name] = [t.upper() for t in tickers]
        return {"watchlist": name, "tickers": self.store.watchlists[name]}

    def run(
        self,
        analyse_fn: Callable[[str], dict[str, Any]],
        *,
        watchlist: str = "default",
        limit: int = 20,
    ) -> dict[str, Any]:
        tickers = list(self.store.watchlists.get(watchlist) or [])[:limit]
        results = []
        for t in tickers:
            try:
                results.append({"ticker": t, "ok": True, "pack": analyse_fn(t)})
            except Exception as exc:
                results.append({"ticker": t, "ok": False, "error": str(exc)[:200]})
        row = {
            "at": datetime.now(timezone.utc).isoformat(),
            "watchlist": watchlist,
            "tickers": tickers,
            "ok": sum(1 for r in results if r.get("ok")),
            "failed": sum(1 for r in results if not r.get("ok")),
        }
        self.last_run_at = row["at"]
        self.runs.append(row)
        self.runs = self.runs[-120:]
        return {"programme": "CME", "run": row, "results": results}
