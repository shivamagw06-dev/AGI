"""Platform metrics store — observe only (PRP-03)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Optional

from institutional_observability.models import InstitutionalMetric

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


_LOCK = threading.Lock()
_COUNTERS: Dict[str, float] = defaultdict(float)
_GAUGES: Dict[str, float] = {}
_SAMPLES: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=2000))
_SERIES: Deque[InstitutionalMetric] = deque(maxlen=5000)
_REQUEST_TIMES: Deque[float] = deque(maxlen=500)


def reset_for_tests() -> None:
    with _LOCK:
        _COUNTERS.clear()
        _GAUGES.clear()
        _SAMPLES.clear()
        _SERIES.clear()
        _REQUEST_TIMES.clear()


def emit(
    metric_name: str,
    value: float,
    *,
    labels: Optional[dict[str, str]] = None,
) -> InstitutionalMetric:
    m = InstitutionalMetric(
        metric_name=metric_name,
        value=float(value),
        labels=dict(labels or {}),
        timestamp=now_iso(),
    )
    key = metric_name
    with _LOCK:
        _SERIES.append(m)
        if metric_name.endswith("_count") or metric_name in {
            "request_count",
            "api_errors",
            "authentication_failures",
            "background_jobs",
        }:
            _COUNTERS[key] += float(value)
        elif metric_name in {
            "cache_hit_rate",
            "queue_depth",
            "error_rate",
            "active_traces",
            "worker_utilization",
        }:
            _GAUGES[key] = float(value)
        else:
            _SAMPLES[key].append(float(value))
            if metric_name == "latency_ms":
                _REQUEST_TIMES.append(time.time())
    return m


def incr(metric_name: str, amount: float = 1.0, *, labels: Optional[dict[str, str]] = None) -> None:
    emit(metric_name, amount, labels=labels)


def set_gauge(metric_name: str, value: float, *, labels: Optional[dict[str, str]] = None) -> None:
    emit(metric_name, value, labels=labels)


def observe_latency(ms: float, *, component: str = "api") -> None:
    emit("latency_ms", ms, labels={"component": component})


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    vals = sorted(values)
    idx = max(0, min(len(vals) - 1, int(p * (len(vals) - 1))))
    return round(vals[idx], 3)


def snapshot() -> dict[str, Any]:
    with _LOCK:
        lat = list(_SAMPLES.get("latency_ms", []))
        pub = list(_SAMPLES.get("publication_duration_ms", []))
        ws = list(_SAMPLES.get("workspace_load_ms", []))
        graph = list(_SAMPLES.get("graph_update_ms", []))
        recent = list(_REQUEST_TIMES)
        counters = dict(_COUNTERS)
        gauges = dict(_GAUGES)
        series_n = len(_SERIES)
    # Request rate over last 60s
    cutoff = time.time() - 60.0
    rate = sum(1 for t in recent if t >= cutoff)
    req = float(counters.get("request_count") or 0)
    err = float(counters.get("api_errors") or 0)
    error_rate = round(err / req, 4) if req else 0.0
    return {
        "request_count": int(req),
        "request_rate_per_min": rate,
        "p50_latency_ms": _percentile(lat, 0.50),
        "p95_latency_ms": _percentile(lat, 0.95),
        "p99_latency_ms": _percentile(lat, 0.99),
        "cache_hit_rate": gauges.get("cache_hit_rate"),
        "queue_depth": gauges.get("queue_depth"),
        "background_jobs": int(counters.get("background_jobs") or 0),
        "publication_duration_ms_p95": _percentile(pub, 0.95),
        "workspace_load_ms_p95": _percentile(ws, 0.95),
        "graph_update_ms_p95": _percentile(graph, 0.95),
        "api_errors": int(err),
        "authentication_failures": int(counters.get("authentication_failures") or 0),
        "active_traces": gauges.get("active_traces"),
        "error_rate": gauges.get("error_rate", error_rate),
        "worker_utilization": gauges.get("worker_utilization"),
        "sample_count": series_n,
        "latency_samples": len(lat),
    }


def recent_metrics(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_SERIES)[-limit:]
    return [m.to_dict() for m in reversed(rows)]
