"""Validation result persistence — replay schema only (never production)."""

from __future__ import annotations

import threading
from typing import Any

from app.validation.models import ReplayResult, ReplayRun


class ValidationStore:
    """In-memory *_replay store. No production table writes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, ReplayRun] = {}
        self._results: dict[str, ReplayResult] = {}
        self._order: list[str] = []

    def put(self, result: ReplayResult) -> None:
        with self._lock:
            rid = result.run.run_id
            self._runs[rid] = result.run
            self._results[rid] = result
            if rid not in self._order:
                self._order.append(rid)

    def get_run(self, run_id: str) -> ReplayRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def get_result(self, run_id: str) -> ReplayResult | None:
        with self._lock:
            return self._results.get(run_id)

    def list_runs(self, limit: int = 50) -> list[ReplayRun]:
        with self._lock:
            ids = list(reversed(self._order[-limit:]))
            return [self._runs[i] for i in ids if i in self._runs]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"runs": len(self._runs), "results": len(self._results), "schema": "replay"}
