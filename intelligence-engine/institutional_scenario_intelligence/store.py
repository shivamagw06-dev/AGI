"""In-process ISI metrics for Mission Control."""

from __future__ import annotations

import time
from typing import Any


class IsiMetricsStore:
    def __init__(self) -> None:
        self._reports: list[dict[str, Any]] = []

    def record(self, *, scope: str, entity: str, scenario_types: list[str], contradictions: int, ok: bool) -> None:
        self._reports.append(
            {
                "scope": scope,
                "entity": entity,
                "scenario_types": scenario_types,
                "contradictions": contradictions,
                "ok": ok,
                "ts": time.time(),
            }
        )
        if len(self._reports) > 500:
            del self._reports[:-500]

    def dashboard(self) -> dict[str, Any]:
        rows = self._reports
        n = len(rows)
        coverage = sum(1 for r in rows if set(r.get("scenario_types") or []) >= {"Bull", "Base", "Bear"})
        return {
            "active_scenario_reports": n,
            "bull_base_bear_coverage_rate": round(coverage / n, 4) if n else None,
            "reports_with_contradictions": sum(1 for r in rows if int(r.get("contradictions") or 0) > 0),
            "recent": list(reversed(rows[-15:])),
        }


METRICS = IsiMetricsStore()
