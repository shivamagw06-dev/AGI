"""Versioned Macro Forecast Report store."""

from __future__ import annotations

import copy
import time
from typing import Any

from macroeconomic_forecast_intelligence.schema import MacroForecastReport, utc_now


class MacroForecastStore:
    def __init__(self) -> None:
        self._reports: dict[str, MacroForecastReport] = {}
        self._by_country: dict[str, list[str]] = {}
        self._history: list[str] = []
        self._runs: list[dict[str, Any]] = []
        self._version: int = 0

    def clear(self) -> None:
        self._reports.clear()
        self._by_country.clear()
        self._history.clear()
        self._runs.clear()
        self._version = 0

    def publish(self, report: MacroForecastReport) -> MacroForecastReport:
        self._version += 1
        frozen = MacroForecastReport.model_validate(copy.deepcopy(report.model_dump(mode="json")))
        frozen.version = self._version
        frozen.published = True
        frozen.published_at = utc_now()
        self._reports[frozen.report_id] = frozen
        key = frozen.country.upper()
        self._by_country.setdefault(key, []).append(frozen.report_id)
        self._history.append(frozen.report_id)
        if len(self._history) > 100:
            del self._history[:-100]
        return frozen

    def latest(self, *, country: str | None = None) -> MacroForecastReport | None:
        if country:
            ids = self._by_country.get(country.upper()) or []
            for rid in reversed(ids):
                if rid in self._reports:
                    return self._reports[rid]
            return None
        if not self._history:
            return None
        return self._reports.get(self._history[-1])

    def history(self, *, limit: int = 20, country: str | None = None) -> list[MacroForecastReport]:
        if country:
            ids = list(self._by_country.get(country.upper()) or [])
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
        return {
            "total_reports": len(self._reports),
            "latest_version": self._version,
            "countries": sorted(self._by_country.keys()),
            "has_published": latest is not None and latest.published,
            "latest_report_id": latest.report_id if latest else None,
            "probability_distribution": latest.probability_distribution if latest else {},
        }


STORE = MacroForecastStore()


def reset() -> None:
    STORE.clear()
