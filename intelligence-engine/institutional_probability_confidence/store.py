"""In-process IPCI metrics for Mission Control."""

from __future__ import annotations

import time
from typing import Any


class IpciMetricsStore:
    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    def record(self, row: dict[str, Any]) -> None:
        self._rows.append({**row, "ts": time.time()})
        if len(self._rows) > 500:
            del self._rows[:-500]

    def dashboard(self) -> dict[str, Any]:
        rows = self._rows
        n = len(rows)
        avg_q = round(sum(float(r.get("forecast_quality") or 0) for r in rows) / n, 2) if n else 0.0
        avg_c = round(sum(float(r.get("overall_confidence") or 0) for r in rows) / n, 2) if n else 0.0
        return {
            "assessments_executed": n,
            "average_forecast_quality_pct": avg_q,
            "average_overall_confidence_pct": avg_c,
            "confidence_history": [
                {
                    "entity": r.get("entity"),
                    "overall_confidence": r.get("overall_confidence"),
                    "forecast_quality": r.get("forecast_quality"),
                    "distribution": r.get("distribution"),
                }
                for r in list(reversed(rows[-20:]))
            ],
            "recent": list(reversed(rows[-15:])),
        }


METRICS = IpciMetricsStore()
