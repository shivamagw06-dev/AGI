"""Versioned Market Forecast Report store."""

from __future__ import annotations

import copy
import time
from typing import Any

from market_forecast_intelligence.schema import MarketForecastReport, utc_now


class MarketForecastStore:
    def __init__(self) -> None:
        self._reports: dict[str, MarketForecastReport] = {}
        self._by_market: dict[str, list[str]] = {}
        self._by_key: dict[str, list[str]] = {}  # market:horizon
        self._history: list[str] = []
        self._runs: list[dict[str, Any]] = []
        self._version: int = 0

    def clear(self) -> None:
        self._reports.clear()
        self._by_market.clear()
        self._by_key.clear()
        self._history.clear()
        self._runs.clear()
        self._version = 0

    def publish(self, report: MarketForecastReport) -> MarketForecastReport:
        self._version += 1
        frozen = MarketForecastReport.model_validate(copy.deepcopy(report.model_dump(mode="json")))
        frozen.version = self._version
        frozen.published = True
        frozen.published_at = utc_now()
        self._reports[frozen.report_id] = frozen
        self._by_market.setdefault(frozen.market, []).append(frozen.report_id)
        key = f"{frozen.market}:{frozen.horizon}"
        self._by_key.setdefault(key, []).append(frozen.report_id)
        self._history.append(frozen.report_id)
        if len(self._history) > 200:
            del self._history[:-200]
        return frozen

    def latest(
        self, *, market: str | None = None, horizon: str | None = None
    ) -> MarketForecastReport | None:
        if market and horizon:
            ids = self._by_key.get(f"{market}:{horizon}") or []
            for rid in reversed(ids):
                if rid in self._reports:
                    return self._reports[rid]
            return None
        if market:
            ids = self._by_market.get(market) or []
            for rid in reversed(ids):
                if rid in self._reports:
                    return self._reports[rid]
            return None
        if not self._history:
            return None
        return self._reports.get(self._history[-1])

    def history(
        self, *, limit: int = 20, market: str | None = None, horizon: str | None = None
    ) -> list[MarketForecastReport]:
        if market and horizon:
            ids = list(self._by_key.get(f"{market}:{horizon}") or [])
        elif market:
            ids = list(self._by_market.get(market) or [])
        else:
            ids = list(self._history)
        rows = [self._reports[i] for i in reversed(ids) if i in self._reports]
        return rows[:limit]

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def coverage(self) -> dict[str, Any]:
        latest = self.latest()
        markets = sorted(self._by_market.keys())
        horizons = sorted({r.horizon for r in self._reports.values()})
        return {
            "total_reports": len(self._reports),
            "latest_version": self._version,
            "markets": markets,
            "horizons": horizons,
            "has_published": latest is not None and latest.published,
            "latest_report_id": latest.report_id if latest else None,
            "probability_distribution": latest.probability_distribution if latest else {},
        }


STORE = MarketForecastStore()


def reset() -> None:
    STORE.clear()
