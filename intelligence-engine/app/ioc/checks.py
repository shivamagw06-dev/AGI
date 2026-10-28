"""IOC operational checks — probe existing platforms only."""

from __future__ import annotations

import time
from typing import Any, Callable

from app.ioc.models import ComponentCheck, ComponentHealth, HealthStatus, STATUS_RANK


def soft_health(fn: Callable[[], Any] | None) -> tuple[dict[str, Any] | None, float, str | None]:
    if fn is None:
        return None, 0.0, "not_wired"
    t0 = time.perf_counter()
    try:
        raw = fn()
        ms = (time.perf_counter() - t0) * 1000.0
        if isinstance(raw, dict):
            return raw, ms, None
        if hasattr(raw, "model_dump"):
            return raw.model_dump(mode="json"), ms, None
        return {"value": raw}, ms, None
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000.0
        return None, ms, str(exc)


def status_from_payload(payload: dict[str, Any] | None, *, error: str | None = None) -> HealthStatus:
    if error:
        return HealthStatus.CRITICAL if "timeout" not in error.lower() else HealthStatus.WARNING
    if payload is None:
        return HealthStatus.OFFLINE
    # disabled platforms
    if payload.get("status") == "disabled":
        return HealthStatus.OFFLINE
    if payload.get("ok") is False:
        return HealthStatus.CRITICAL
    if payload.get("status") in {"error", "failed"}:
        return HealthStatus.CRITICAL
    # circuit / recovering heuristics
    circuit = str(payload.get("circuit_state") or "").lower()
    if circuit == "open":
        return HealthStatus.CRITICAL
    if circuit == "half_open":
        return HealthStatus.RECOVERING
    # stale hints
    if payload.get("stale") is True or payload.get("freshness") in {"stale", "old"}:
        return HealthStatus.STALE
    freshness = payload.get("freshness_score")
    if isinstance(freshness, (int, float)) and freshness < 0.4:
        return HealthStatus.STALE
    if payload.get("ok") is True or payload.get("status") in {"ok", "healthy", None}:
        return HealthStatus.HEALTHY
    if "warning" in str(payload.get("status", "")).lower():
        return HealthStatus.WARNING
    return HealthStatus.HEALTHY


def worst_status(*statuses: HealthStatus) -> HealthStatus:
    if not statuses:
        return HealthStatus.OFFLINE
    return max(statuses, key=lambda s: STATUS_RANK[s])


def check_component(
    component: str,
    category: str,
    name: str,
    payload: dict[str, Any] | None,
    *,
    latency_ms: float | None = None,
    error: str | None = None,
    extra_status: HealthStatus | None = None,
) -> ComponentCheck:
    status = status_from_payload(payload, error=error)
    if extra_status is not None:
        status = worst_status(status, extra_status)
    msg = error or str((payload or {}).get("status") or (payload or {}).get("service") or name)
    if status == HealthStatus.HEALTHY:
        msg = f"{name} healthy"
    return ComponentCheck(
        component=component,
        category=category,
        name=name,
        status=status,
        message=msg[:400],
        details=payload or {},
        latency_ms=round(latency_ms, 3) if latency_ms is not None else None,
    )


def rollup(component: str, checks: list[ComponentCheck]) -> ComponentHealth:
    status = worst_status(*(c.status for c in checks)) if checks else HealthStatus.OFFLINE
    bad = [c for c in checks if c.status != HealthStatus.HEALTHY]
    summary = "all checks healthy" if not bad else f"{len(bad)} issue(s): " + ", ".join(c.name for c in bad[:5])
    return ComponentHealth(component=component, status=status, checks=checks, summary=summary)


def check_provider_snapshot(snapshot: dict[str, Any] | None, *, latency_ms: float | None = None) -> list[ComponentCheck]:
    if snapshot is None:
        return [
            ComponentCheck(
                component="market_data",
                category="provider",
                name="provider_freshness",
                status=HealthStatus.OFFLINE,
                message="Market data health unavailable",
                latency_ms=latency_ms,
            )
        ]
    checks: list[ComponentCheck] = []
    overall = HealthStatus.HEALTHY if snapshot.get("ok") else HealthStatus.CRITICAL
    checks.append(
        ComponentCheck(
            component="market_data",
            category="provider",
            name="provider_freshness",
            status=overall,
            message="providers ok" if snapshot.get("ok") else "no healthy providers",
            details={"checked_at": snapshot.get("checked_at"), "metrics": snapshot.get("metrics")},
            latency_ms=latency_ms,
        )
    )
    for p in snapshot.get("providers") or []:
        circuit = str(p.get("circuit_state") or "").lower()
        if not p.get("configured"):
            st = HealthStatus.OFFLINE
        elif circuit == "open":
            st = HealthStatus.CRITICAL
        elif circuit == "half_open":
            st = HealthStatus.RECOVERING
        elif p.get("ok"):
            st = HealthStatus.HEALTHY
        else:
            st = HealthStatus.WARNING
        checks.append(
            ComponentCheck(
                component=f"provider:{p.get('provider_id')}",
                category="provider",
                name="provider_health",
                status=st,
                message=p.get("last_error") or f"{p.get('provider_id')} {circuit or 'closed'}",
                details=p,
            )
        )
    return checks


def check_latency(name: str, component: str, latency_ms: float | None, *, warn_ms: float = 500, crit_ms: float = 2000) -> ComponentCheck:
    if latency_ms is None:
        return ComponentCheck(
            component=component,
            category="pipeline",
            name=name,
            status=HealthStatus.WARNING,
            message="latency unknown",
        )
    if latency_ms >= crit_ms:
        st = HealthStatus.CRITICAL
        msg = f"latency {latency_ms:.1f}ms exceeds critical threshold"
    elif latency_ms >= warn_ms:
        st = HealthStatus.WARNING
        msg = f"latency {latency_ms:.1f}ms elevated"
    else:
        st = HealthStatus.HEALTHY
        msg = f"latency {latency_ms:.1f}ms"
    return ComponentCheck(
        component=component,
        category="pipeline",
        name=name,
        status=st,
        message=msg,
        latency_ms=round(latency_ms, 3),
    )
