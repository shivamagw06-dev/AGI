"""Dependency monitoring for outage diagnosis (PRP-03)."""

from __future__ import annotations

from typing import Any, List, Tuple

from institutional_observability.alerts import record_dependency_alert
from institutional_observability.health import check_service
from institutional_observability.schema import MONITORED_SERVICES

# Directed edges: from → to
DEPENDENCY_EDGES: Tuple[Tuple[str, str], ...] = (
    ("browser", "api"),
    ("api", "security"),
    ("api", "performance"),
    ("api", "observability"),
    ("security", "uag"),
    ("uag", "rw"),
    ("uag", "cci"),
    ("uag", "pub"),
    ("rw", "knowledge_graph"),
    ("cci", "knowledge_graph"),
    ("pub", "queue"),
    ("performance", "redis"),
    ("performance", "queue"),
    ("api", "database"),
    ("queue", "storage"),
)


def dependency_graph() -> dict[str, Any]:
    nodes = sorted({n for edge in DEPENDENCY_EDGES for n in edge} | set(MONITORED_SERVICES))
    return {
        "nodes": [{"id": n, "service": n} for n in nodes],
        "edges": [{"from": a, "to": b} for a, b in DEPENDENCY_EDGES],
        "changes_platform_behavior": False,
    }


def probe_dependencies() -> dict[str, Any]:
    statuses = []
    unhealthy: List[str] = []
    for svc in MONITORED_SERVICES:
        h = check_service(svc)
        row = h.to_dict()
        statuses.append(row)
        if row["status"] in {"unhealthy", "degraded"} and row["status"] == "unhealthy":
            unhealthy.append(svc)
            record_dependency_alert(svc, row["status"])
    return {
        "ok": not unhealthy,
        "dependencies": statuses,
        "unhealthy": unhealthy,
        "graph": dependency_graph(),
    }
