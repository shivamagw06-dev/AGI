"""Step 17 — Continuous ingestion schedule (status + soft triggers)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SCHEDULE = [
    {"stream": "company_filings", "cadence": "immediate", "tiers": [1, 2]},
    {"stream": "news", "cadence": "every_5_15_minutes", "tiers": [4]},
    {"stream": "government", "cadence": "hourly", "tiers": [2, 3]},
    {"stream": "annual_reports", "cadence": "detect_automatically", "tiers": [1]},
    {"stream": "quarterly_reports", "cadence": "detect_automatically", "tiers": [1]},
    {"stream": "macro_prints", "cadence": "hourly", "tiers": [2, 3]},
]


class FreScheduler:
    def __init__(self) -> None:
        self.enabled = True
        self.last_run_at: str | None = None
        self.runs: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "schedule": SCHEDULE,
            "last_run_at": self.last_run_at,
            "recent_runs": self.runs[-20:],
        }

    def mark_run(self, stream: str, *, documents: int = 0, note: str = "") -> dict[str, Any]:
        row = {
            "stream": stream,
            "documents": documents,
            "note": note,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.last_run_at = row["at"]
        self.runs.append(row)
        self.runs = self.runs[-100:]
        return row
