"""LEO usage / API metrics store — auditable contribution tracking."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class LeoUsageStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.queries = 0
        self.calls_today = 0
        self.latencies: list[float] = []
        self.by_source_calls: dict[str, int] = defaultdict(int)
        self.by_source_used: dict[str, int] = defaultdict(int)
        self.by_source_failures: dict[str, int] = defaultdict(int)
        self.evidence_objects_created = 0
        self.external_contributions = 0
        self.reasoning_contributions = 0
        self.recent: list[dict[str, Any]] = []
        self.day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _roll_day(self) -> None:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if d != self.day:
            self.day = d
            self.calls_today = 0

    def record(self, package: dict[str, Any]) -> None:
        with self._lock:
            self._roll_day()
            self.queries += 1
            usage = package.get("usage") or {}
            calls = usage.get("api_calls") or []
            self.calls_today += len(calls)
            for c in calls:
                sid = c.get("source_id") or "unknown"
                self.by_source_calls[sid] += 1
                if c.get("status") == "error":
                    self.by_source_failures[sid] += 1
                lat = c.get("latency_ms")
                if isinstance(lat, (int, float)):
                    self.latencies.append(float(lat))
                    self.latencies = self.latencies[-500:]
            for sid in usage.get("sources_used") or []:
                self.by_source_used[str(sid)] += 1
            n_obj = len(package.get("evidence_objects") or [])
            self.evidence_objects_created += n_obj
            if usage.get("external_api_contributed"):
                self.external_contributions += 1
            if package.get("influenced_reasoning"):
                self.reasoning_contributions += 1
            self.recent.append(
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "ticker": package.get("ticker"),
                    "intent": package.get("intent"),
                    "sources_used": usage.get("sources_used"),
                    "external": usage.get("external_api_contributed"),
                    "objects": n_obj,
                    "confidence": package.get("evidence_confidence"),
                }
            )
            self.recent = self.recent[-100:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._roll_day()
            avg_lat = sum(self.latencies) / len(self.latencies) if self.latencies else 0.0
            calls_per_query = (self.calls_today / self.queries) if self.queries else 0.0
            reasoning_pct = (
                (self.reasoning_contributions / self.queries) * 100.0 if self.queries else 0.0
            )
            return {
                "queries": self.queries,
                "calls_today": self.calls_today,
                "calls_per_query": round(calls_per_query, 3),
                "average_latency_ms": round(avg_lat, 2),
                "evidence_objects_created": self.evidence_objects_created,
                "external_contributions": self.external_contributions,
                "reasoning_contributions": self.reasoning_contributions,
                "reasoning_contribution_pct": round(reasoning_pct, 2),
                "by_source_calls": dict(self.by_source_calls),
                "by_source_used": dict(self.by_source_used),
                "by_source_failures": dict(self.by_source_failures),
                "recent": list(self.recent)[-20:],
                "day": self.day,
            }


_STORE: LeoUsageStore | None = None


def get_leo_store() -> LeoUsageStore:
    global _STORE
    if _STORE is None:
        _STORE = LeoUsageStore()
    return _STORE
