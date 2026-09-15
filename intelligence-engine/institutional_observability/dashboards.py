"""Operations Center dashboard assembly (PRP-03)."""

from __future__ import annotations

from typing import Any

from institutional_observability.alerts import alert_metrics, evaluate
from institutional_observability.dependency_monitor import probe_dependencies
from institutional_observability.health import aggregate_health
from institutional_observability.logging import recent_logs
from institutional_observability.metrics import snapshot
from institutional_observability.service_map import build_service_map
from institutional_observability.tracing import active_trace_count, recent_traces


def operations_center_board() -> dict[str, Any]:
    # Soft-sync gauges from sibling PRP packages (observe only)
    _sync_external_gauges()
    m = snapshot()
    evaluate(m)  # fire alerts from metrics
    health = aggregate_health()
    alerts = alert_metrics()
    smap = build_service_map()
    return {
        "operations_center": True,
        "live_request_rate": m.get("request_rate_per_min"),
        "active_traces": active_trace_count(),
        "p95_latency_ms": m.get("p95_latency_ms"),
        "p99_latency_ms": m.get("p99_latency_ms"),
        "error_rate": m.get("error_rate"),
        "queue_health": {
            "depth": m.get("queue_depth"),
            "status": (health.get("by_service") or {}).get("queue"),
        },
        "cache_health": {
            "hit_rate": m.get("cache_hit_rate"),
            "status": (health.get("by_service") or {}).get("redis"),
        },
        "worker_utilization": m.get("worker_utilization"),
        "dependency_status": health.get("by_service"),
        "overall_health": health.get("status"),
        "alert_timeline": alerts.get("recent") or [],
        "service_topology": smap.get("topology"),
        "recent_traces": recent_traces(6),
        "recent_logs": recent_logs(limit=6),
        "metrics": m,
        "changes_platform_behavior": False,
        "enters_intelligence_layer": False,
    }


def _sync_external_gauges() -> None:
    from institutional_observability.metrics import set_gauge
    from institutional_observability.tracing import active_trace_count

    try:
        from institutional_performance.cache import stats as cache_stats

        set_gauge("cache_hit_rate", float(cache_stats().get("hit_rate") or 0.0))
    except Exception:
        pass
    try:
        from institutional_performance.job_queue import get_queue

        q = get_queue().stats()
        set_gauge("queue_depth", float(q.get("queue_depth") or 0))
        max_w = float(q.get("max_workers") or 1)
        active = float(q.get("active_workers") or 0)
        set_gauge("worker_utilization", round(active / max_w, 4) if max_w else 0.0)
    except Exception:
        pass
    set_gauge("active_traces", float(active_trace_count()))
