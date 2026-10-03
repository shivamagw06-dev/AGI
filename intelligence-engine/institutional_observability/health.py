"""Liveness / readiness / dependency health aggregation (PRP-03)."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from institutional_observability.models import InstitutionalHealth
from institutional_observability.schema import HEALTH_STATUSES, MONITORED_SERVICES

_LAST_CHECK: dict[str, float] = {}
_STALE_SECONDS = 120.0


def reset_for_tests() -> None:
    _LAST_CHECK.clear()


def _probe(name: str, fn: Callable[[], dict[str, Any]]) -> InstitutionalHealth:
    t0 = time.perf_counter()
    try:
        result = fn()
        latency = round((time.perf_counter() - t0) * 1000.0, 3)
        status = str(result.get("status") or "healthy").lower()
        if status in {"ok", "up", "ready"}:
            status = "healthy"
        if status not in HEALTH_STATUSES:
            status = "unknown"
        deps = tuple(result.get("dependencies") or ())
        _LAST_CHECK[name] = time.time()
        return InstitutionalHealth(
            service=name,
            status=status,
            latency_ms=latency,
            dependencies=deps,
            diagnostics=dict(result.get("diagnostics") or result),
        )
    except Exception as exc:  # noqa: BLE001
        return InstitutionalHealth(
            service=name,
            status="unhealthy",
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            dependencies=(),
            diagnostics={"error": str(exc)},
        )


def _soft_health(module_path: str, attr: str = "health") -> dict[str, Any]:
    import importlib

    mod = importlib.import_module(module_path)
    fn = getattr(mod, attr)
    h = fn()
    status = h.get("status") or ("healthy" if h.get("ok") is not False else "degraded")
    return {"status": status, "diagnostics": {"enabled": h.get("enabled", True)}}


def check_service(service: str) -> InstitutionalHealth:
    probes: Dict[str, Callable[[], dict[str, Any]]] = {
        "api": lambda: {"status": "healthy", "dependencies": ["security", "uag"]},
        "security": lambda: _soft_health("institutional_security.production"),
        "uag": lambda: _soft_health("institutional_orchestrator.production"),
        "rw": lambda: _soft_health("institutional_workspace.production"),
        "pub": lambda: _soft_health("institutional_publishing.production"),
        "cci": lambda: _soft_health("institutional_cross_company.production"),
        "mpc": lambda: _soft_health("institutional_multi_portfolio.production"),
        "performance": lambda: _soft_health("institutional_performance.production"),
        "knowledge_graph": lambda: _soft_kg(),
        "redis": lambda: _soft_redis(),
        "database": lambda: {"status": "healthy", "diagnostics": {"mode": "soft"}},
        "queue": lambda: _soft_queue(),
        "storage": lambda: {"status": "healthy", "diagnostics": {"mode": "soft"}},
    }
    fn = probes.get(service)
    if not fn:
        return InstitutionalHealth(service=service, status="unknown")
    return _probe(service, fn)


def _soft_kg() -> dict[str, Any]:
    try:
        from institutional_graph.production import health  # type: ignore

        h = health()
        return {"status": h.get("status") or "healthy", "diagnostics": {"module": "institutional_graph"}}
    except Exception:
        return {"status": "degraded", "diagnostics": {"available": False}}


def _soft_redis() -> dict[str, Any]:
    try:
        from institutional_performance.cache import stats

        s = stats()
        if s.get("redis_enabled"):
            return {"status": "healthy", "diagnostics": s}
        if s.get("redis_attempted"):
            return {"status": "degraded", "diagnostics": {"fallback": "memory", **s}}
        return {"status": "degraded", "diagnostics": {"fallback": "memory", **s}}
    except Exception as exc:
        return {"status": "unhealthy", "diagnostics": {"error": str(exc)}}


def _soft_queue() -> dict[str, Any]:
    try:
        from institutional_performance.job_queue import get_queue

        q = get_queue().stats()
        depth = int(q.get("queue_depth") or 0)
        status = "healthy" if depth < 25 else "degraded"
        return {"status": status, "diagnostics": q, "dependencies": ["performance"]}
    except Exception as exc:
        return {"status": "unhealthy", "diagnostics": {"error": str(exc)}}


def aggregate_health() -> dict[str, Any]:
    services = [check_service(s).to_dict() for s in MONITORED_SERVICES]
    statuses = {s["service"]: s["status"] for s in services}
    unhealthy = [s for s in services if s["status"] == "unhealthy"]
    degraded = [s for s in services if s["status"] == "degraded"]
    if unhealthy:
        overall = "unhealthy"
    elif degraded:
        overall = "degraded"
    else:
        overall = "healthy"
    stale = [
        name
        for name, ts in _LAST_CHECK.items()
        if time.time() - ts > _STALE_SECONDS
    ]
    return {
        "status": overall,
        "liveness": "alive",
        "readiness": "ready" if overall != "unhealthy" else "not_ready",
        "services": services,
        "by_service": statuses,
        "unhealthy_count": len(unhealthy),
        "degraded_count": len(degraded),
        "stale_checks": stale,
        "changes_platform_behavior": False,
    }


def liveness() -> dict[str, Any]:
    return {"status": "alive", "workstream_id": "PRP-03"}


def readiness() -> dict[str, Any]:
    agg = aggregate_health()
    return {
        "status": agg["readiness"],
        "overall": agg["status"],
        "unhealthy_count": agg["unhealthy_count"],
    }
