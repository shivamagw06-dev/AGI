"""IOC alert derivation from component checks — monitoring only."""

from __future__ import annotations

from app.ioc.models import AlertSeverity, ComponentCheck, HealthStatus, OpsAlert


KIND_MAP = {
    "engine": "engine_failure",
    "provider": "provider_outage",
    "feature": "stale_data",
    "orch": "engine_failure",
    "platform": "engine_failure",
    "pipeline": "stale_data",
}


def alerts_from_checks(checks: list[ComponentCheck]) -> list[OpsAlert]:
    out: list[OpsAlert] = []
    for c in checks:
        if c.status in {HealthStatus.HEALTHY, HealthStatus.RECOVERING}:
            if c.status == HealthStatus.RECOVERING:
                out.append(
                    OpsAlert(
                        kind="provider_outage" if c.category == "provider" else "engine_failure",
                        severity=AlertSeverity.INFO,
                        component=c.component,
                        message=f"Recovering: {c.message}",
                        status=c.status,
                        details={"check": c.name},
                    )
                )
            continue
        kind = _kind_for(c)
        severity = (
            AlertSeverity.CRITICAL
            if c.status in {HealthStatus.CRITICAL, HealthStatus.OFFLINE}
            else AlertSeverity.WARNING
        )
        out.append(
            OpsAlert(
                kind=kind,
                severity=severity,
                component=c.component,
                message=c.message,
                status=c.status,
                details={"check": c.name, "category": c.category, **(c.details or {})},
            )
        )
    return _dedupe(out)


def _kind_for(c: ComponentCheck) -> str:
    name = c.name.lower()
    comp = c.component.lower()
    if "provider" in c.category or comp.startswith("provider:"):
        return "provider_outage"
    if "stale" in name or c.status == HealthStatus.STALE or "freshness" in name:
        return "stale_data"
    if "replay" in comp or "replay" in name:
        return "replay_failure"
    if "cre" in comp:
        return "cre_regression"
    if "portfolio" in name or comp == "e10":
        return "portfolio_not_generated"
    if "kip" in comp or "ingest" in name or "knowledge" in name:
        return "knowledge_ingestion_failure"
    if "rms" in comp or "research" in name or "publication" in name:
        return "missing_research"
    if c.category == "engine" or comp.startswith("e0") or comp in {"l4", "e10", "e11", "e13", "e14"}:
        return "engine_failure"
    return KIND_MAP.get(c.category, "engine_failure")


def _dedupe(alerts: list[OpsAlert]) -> list[OpsAlert]:
    seen: set[str] = set()
    out: list[OpsAlert] = []
    for a in alerts:
        key = f"{a.kind}:{a.component}:{a.message[:80]}"
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    # critical first
    rank = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}
    out.sort(key=lambda a: (rank[a.severity], a.component))
    return out
