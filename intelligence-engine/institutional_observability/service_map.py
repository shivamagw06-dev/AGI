"""Service topology for Mission Control Operations Center (PRP-03)."""

from __future__ import annotations

from typing import Any

from institutional_observability.dependency_monitor import DEPENDENCY_EDGES, dependency_graph
from institutional_observability.health import aggregate_health


def build_service_map() -> dict[str, Any]:
    health = aggregate_health()
    by = health.get("by_service") or {}
    graph = dependency_graph()
    nodes = []
    for n in graph["nodes"]:
        sid = n["id"]
        nodes.append(
            {
                **n,
                "status": by.get(sid) or ("healthy" if sid in {"browser", "observability"} else "unknown"),
                "kind": _kind(sid),
            }
        )
    return {
        "topology": {
            "nodes": nodes,
            "edges": list(graph["edges"]),
        },
        "layers": [
            {"id": "edge", "services": ["browser", "api"]},
            {"id": "control", "services": ["security", "performance", "observability"]},
            {"id": "orchestration", "services": ["uag", "rw", "pub", "cci", "mpc"]},
            {"id": "data", "services": ["knowledge_graph", "redis", "database", "queue", "storage"]},
        ],
        "overall_status": health.get("status"),
        "changes_platform_behavior": False,
    }


def _kind(service: str) -> str:
    if service in {"browser", "api"}:
        return "edge"
    if service in {"security", "performance", "observability"}:
        return "platform"
    if service in {"uag", "rw", "pub", "cci", "mpc"}:
        return "orchestration"
    return "dependency"
