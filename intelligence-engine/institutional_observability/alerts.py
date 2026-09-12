"""Alert evaluation from metrics — never inspects business objects (PRP-03)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, List, Optional

from institutional_observability.flags import alerts_enabled
from institutional_observability.metrics import snapshot
from institutional_observability.schema import (
    ALERT_RULES,
    AUTH_FAILURE_SPIKE,
    CACHE_MISS_SURGE_RATE,
    P95_LATENCY_ALERT_MS,
    QUEUE_BACKLOG_ALERT,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_ALERTS: Deque[dict[str, Any]] = deque(maxlen=500)
_DELIVERY_FAILURES = 0


def reset_for_tests() -> None:
    global _DELIVERY_FAILURES
    with _LOCK:
        _ALERTS.clear()
        _DELIVERY_FAILURES = 0


def _emit(rule: str, severity: str, message: str, *, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    global _DELIVERY_FAILURES
    row = {
        "alert_id": f"al_{int(time.time() * 1000)}_{rule[:12]}",
        "rule": rule,
        "severity": severity,
        "message": message,
        "timestamp": now_iso(),
        "metadata": dict(meta or {}),
        "delivered": True,
    }
    try:
        with _LOCK:
            _ALERTS.append(row)
    except Exception:
        _DELIVERY_FAILURES += 1
        row["delivered"] = False
    return row


def evaluate(metrics: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Consume metrics snapshot; never reads intelligence objects."""
    if not alerts_enabled():
        return []
    m = metrics or snapshot()
    fired: List[dict[str, Any]] = []

    p95 = m.get("p95_latency_ms")
    if p95 is not None and p95 > P95_LATENCY_ALERT_MS:
        fired.append(
            _emit(
                "p95_latency_exceeded",
                "warning",
                f"P95 latency {p95}ms exceeds {P95_LATENCY_ALERT_MS}ms",
                meta={"p95_latency_ms": p95},
            )
        )

    depth = m.get("queue_depth")
    if depth is not None and float(depth) >= QUEUE_BACKLOG_ALERT:
        fired.append(
            _emit(
                "queue_backlog",
                "warning",
                f"Queue depth {depth} >= {QUEUE_BACKLOG_ALERT}",
                meta={"queue_depth": depth},
            )
        )

    auth_fail = int(m.get("authentication_failures") or 0)
    if auth_fail >= AUTH_FAILURE_SPIKE:
        fired.append(
            _emit(
                "authentication_spike",
                "warning",
                f"Authentication failures {auth_fail} >= {AUTH_FAILURE_SPIKE}",
                meta={"authentication_failures": auth_fail},
            )
        )

    hit = m.get("cache_hit_rate")
    if hit is not None and float(hit) < (1.0 - CACHE_MISS_SURGE_RATE):
        # hit rate very low → miss surge
        fired.append(
            _emit(
                "cache_miss_surge",
                "info",
                f"Cache hit rate {hit} indicates miss surge",
                meta={"cache_hit_rate": hit},
            )
        )

    err = int(m.get("api_errors") or 0)
    if err >= 5 and float(m.get("error_rate") or 0) > 0.2:
        fired.append(
            _emit(
                "publication_failures",
                "warning",
                f"Elevated API error rate {m.get('error_rate')}",
                meta={"api_errors": err, "error_rate": m.get("error_rate")},
            )
        )

    return fired


def record_dependency_alert(service: str, status: str) -> dict[str, Any]:
    return _emit(
        "dependency_unavailable",
        "critical" if status == "unhealthy" else "warning",
        f"Dependency {service} is {status}",
        meta={"service": service, "status": status},
    )


def record_worker_failure(detail: str = "") -> dict[str, Any]:
    return _emit(
        "worker_failures",
        "warning",
        f"Worker failure: {detail or 'unknown'}",
        meta={"detail": detail},
    )


def list_alerts(limit: int = 40) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_ALERTS)[-limit:]
    return list(reversed(rows))


def alert_metrics() -> dict[str, Any]:
    with _LOCK:
        n = len(_ALERTS)
        undelivered = sum(1 for a in _ALERTS if not a.get("delivered"))
    return {
        "alert_count": n,
        "delivery_failures": _DELIVERY_FAILURES + undelivered,
        "rules": list(ALERT_RULES),
        "recent": list_alerts(8),
    }
