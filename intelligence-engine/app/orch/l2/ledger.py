"""Feature Build Ledger — every feature build row (ORCH-005)."""

from __future__ import annotations

import threading
from typing import Any

from app.orch.l2.models import FeatureBuildRecord


class FeatureBuildLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, FeatureBuildRecord] = {}
        self._by_batch: dict[str, list[str]] = {}

    def record(self, row: FeatureBuildRecord) -> FeatureBuildRecord:
        with self._lock:
            self._by_id[row.build_id] = row
            if row.batch_id:
                self._by_batch.setdefault(row.batch_id, []).append(row.build_id)
            return row

    def get(self, build_id: str) -> FeatureBuildRecord | None:
        with self._lock:
            return self._by_id.get(build_id)

    def list_batch(self, batch_id: str) -> list[FeatureBuildRecord]:
        with self._lock:
            ids = self._by_batch.get(batch_id, [])
            return [self._by_id[i] for i in ids if i in self._by_id]

    def recent(self, limit: int = 50) -> list[FeatureBuildRecord]:
        with self._lock:
            rows = sorted(self._by_id.values(), key=lambda r: r.timestamp, reverse=True)
            return rows[:limit]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for row in self._by_id.values():
                by_status[row.status] = by_status.get(row.status, 0) + 1
            return {
                "builds": len(self._by_id),
                "batches": len(self._by_batch),
                "by_status": by_status,
            }
