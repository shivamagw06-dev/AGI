"""Observability counters for the in-process event bus."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
_STATE: dict[str, Any] = {
    "published": 0,
    "dispatched": 0,
    "delivered": 0,
    "failed_handlers": 0,
    "subscriber_count": 0,
    "latency_ms_sum": 0.0,
    "latency_ms_count": 0,
    "dispatch_ms_sum": 0.0,
    "dispatch_ms_count": 0,
    "by_type": {},
    "recent_events": [],
    "recent_failures": [],
}
_RECENT_LIMIT = 100


def set_subscriber_count(n: int) -> None:
    with _LOCK:
        _STATE["subscriber_count"] = int(n)


def record_publish(event_type: str) -> None:
    with _LOCK:
        _STATE["published"] = int(_STATE["published"]) + 1
        by = _STATE["by_type"]
        row = by.setdefault(event_type, {"published": 0, "delivered": 0, "failed": 0})
        row["published"] = int(row["published"]) + 1


def record_delivery(event_type: str, latency_ms: float) -> None:
    with _LOCK:
        _STATE["delivered"] = int(_STATE["delivered"]) + 1
        _STATE["latency_ms_sum"] = float(_STATE["latency_ms_sum"]) + float(latency_ms)
        _STATE["latency_ms_count"] = int(_STATE["latency_ms_count"]) + 1
        by = _STATE["by_type"]
        row = by.setdefault(event_type, {"published": 0, "delivered": 0, "failed": 0})
        row["delivered"] = int(row["delivered"]) + 1


def record_handler_failure(event_type: str, subscriber_id: str, error: str) -> None:
    with _LOCK:
        _STATE["failed_handlers"] = int(_STATE["failed_handlers"]) + 1
        by = _STATE["by_type"]
        row = by.setdefault(event_type, {"published": 0, "delivered": 0, "failed": 0})
        row["failed"] = int(row["failed"]) + 1
        fails = _STATE["recent_failures"]
        fails.append({"event_type": event_type, "subscriber_id": subscriber_id, "error": error})
        if len(fails) > _RECENT_LIMIT:
            del fails[: len(fails) - _RECENT_LIMIT]


def record_dispatch(event_type: str, dispatch_ms: float, matched: int) -> None:
    with _LOCK:
        _STATE["dispatched"] = int(_STATE["dispatched"]) + 1
        _STATE["dispatch_ms_sum"] = float(_STATE["dispatch_ms_sum"]) + float(dispatch_ms)
        _STATE["dispatch_ms_count"] = int(_STATE["dispatch_ms_count"]) + 1
        _ = (event_type, matched)


def remember_event(event: dict[str, Any], deliveries: list[dict[str, Any]]) -> None:
    with _LOCK:
        recent = _STATE["recent_events"]
        recent.append(
            {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "producer": event.get("producer"),
                "timestamp": event.get("timestamp"),
                "correlation_id": event.get("correlation_id"),
                "matched": len(deliveries),
                "failures": sum(1 for d in deliveries if d.get("status") == "error"),
            }
        )
        if len(recent) > _RECENT_LIMIT:
            del recent[: len(recent) - _RECENT_LIMIT]


def statistics() -> dict[str, Any]:
    with _LOCK:
        s = deepcopy(_STATE)
    lat_n = int(s.get("latency_ms_count") or 0)
    disp_n = int(s.get("dispatch_ms_count") or 0)
    return {
        "published": s["published"],
        "dispatched": s["dispatched"],
        "delivered": s["delivered"],
        "failed_handlers": s["failed_handlers"],
        "subscribers": s["subscriber_count"],
        "average_handler_latency_ms": round(float(s["latency_ms_sum"]) / lat_n, 3) if lat_n else 0.0,
        "average_dispatch_ms": round(float(s["dispatch_ms_sum"]) / disp_n, 3) if disp_n else 0.0,
        "by_type": s["by_type"],
        "panels": {
            "events_published": s["published"],
            "events_dispatched": s["dispatched"],
            "subscribers": s["subscriber_count"],
            "average_latency": round(float(s["latency_ms_sum"]) / lat_n, 3) if lat_n else 0.0,
            "failures": s["failed_handlers"],
        },
    }


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_STATE["recent_events"])
    return rows[-max(0, int(limit)) :]


def recent_failures(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_STATE["recent_failures"])
    return rows[-max(0, int(limit)) :]


def reset_for_tests() -> None:
    with _LOCK:
        _STATE["published"] = 0
        _STATE["dispatched"] = 0
        _STATE["delivered"] = 0
        _STATE["failed_handlers"] = 0
        _STATE["subscriber_count"] = 0
        _STATE["latency_ms_sum"] = 0.0
        _STATE["latency_ms_count"] = 0
        _STATE["dispatch_ms_sum"] = 0.0
        _STATE["dispatch_ms_count"] = 0
        _STATE["by_type"] = {}
        _STATE["recent_events"] = []
        _STATE["recent_failures"] = []
