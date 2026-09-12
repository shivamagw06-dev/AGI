"""Canonical connector contract for institutional data acquisition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConnectorResult:
    ok: bool
    connector_id: str
    source_id: str
    records: list[dict[str, Any]] = field(default_factory=list)
    normalized: list[dict[str, Any]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    mode: str = "live"
    coverage_pct: float | None = None
    quality_score: float | None = None
    repair_items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "connector_id": self.connector_id,
            "source_id": self.source_id,
            "record_count": len(self.records),
            "normalized_count": len(self.normalized),
            "validation": self.validation,
            "diagnostics": self.diagnostics,
            "error": self.error,
            "mode": self.mode,
            "coverage_pct": self.coverage_pct,
            "quality_score": self.quality_score,
            "repair_items": self.repair_items,
            "generated_at": _now(),
        }


class Connector(ABC):
    """Every institutional collector implements this surface — nowhere else."""

    connector_id: str = "base"
    source_id: str = "base"
    official_source: str = "unknown"

    @abstractmethod
    def collect(self, **kwargs: Any) -> ConnectorResult:
        ...

    @abstractmethod
    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        ...

    @abstractmethod
    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        ...

    def health(self) -> dict[str, Any]:
        try:
            from live_data import store as lidi_store

            h = lidi_store.get_collector_health(self.connector_id) or {}
        except Exception:
            h = {}
        succ = int(h.get("success_count") or 0)
        fail = int(h.get("failure_count") or 0)
        n = succ + fail
        return {
            "connector_id": self.connector_id,
            "source_id": self.source_id,
            "official_source": self.official_source,
            "success_count": succ,
            "failure_count": fail,
            "success_pct": round(100.0 * succ / n, 1) if n else None,
            "failure_pct": round(100.0 * fail / n, 1) if n else None,
            "last_success": h.get("last_success"),
            "last_failure": h.get("last_failure"),
            "last_error": h.get("last_error"),
        }

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        return {"connector_id": self.connector_id, "coverage_pct": None, "detail": "not_implemented"}

    def run(self, **kwargs: Any) -> ConnectorResult:
        """Full collect → validate → normalize → store with repair enqueue on failure."""
        result = self.collect(**kwargs)
        if result.records:
            result.normalized = self.normalize(result.records, **kwargs)
            result.validation = self.validate(result.normalized or result.records, **kwargs)
            if result.validation.get("ok", True):
                stored = self.store(result.normalized or result.records, **kwargs)
                result.diagnostics["stored"] = stored
            else:
                result.ok = False
                result.repair_items.append(
                    {
                        "reason": "validation_failed",
                        "connector": self.connector_id,
                        "detail": result.validation,
                    }
                )
        if not result.ok:
            self._enqueue_repair(result)
        self._record_reliability(result)
        return result

    def _enqueue_repair(self, result: ConnectorResult) -> None:
        try:
            from knowledge_factory.historical_depth.coverage_audit import load_repair_queue
            from institutional_data.persistence.queue_persistence import QueuePersistence

            qp = QueuePersistence()
            q = load_repair_queue()
            items = list(q.get("items") or [])
            for item in result.repair_items or [
                {"reason": result.error or "collect_failed", "connector": self.connector_id, "priority": 2}
            ]:
                items.append({**item, "enqueued_at": _now()})
            qp.save_repair_queue({"items": items[-500:], "source": "connector"})
        except Exception:
            pass

    def _record_reliability(self, result: ConnectorResult) -> None:
        try:
            from institutional_data.reliability.scores import record_connector_sample

            record_connector_sample(
                self.source_id,
                ok=bool(result.ok),
                latency_ms=(result.diagnostics or {}).get("latency_ms"),
                coverage_pct=result.coverage_pct,
                parser_path=(result.diagnostics or {}).get("parse_path"),
            )
        except Exception:
            pass
