"""UAG-01 router — resolve execution steps to registered providers."""

from __future__ import annotations

from typing import Any

from institutional_orchestrator.models import ExecutionStep, InstitutionalQuery
from institutional_orchestrator.object_registry import get


def route_plan(query: InstitutionalQuery) -> list[dict[str, Any]]:
    """Return routed steps with callable provider metadata (no execution)."""
    routed: list[dict[str, Any]] = []
    for step in query.execution_plan:
        reg = get(step.object_type)
        routed.append(
            {
                "step": step.to_dict(),
                "registered": reg is not None,
                "provider": reg.provider if reg else step.provider,
                "has_retrieve": bool(reg and reg.retrieve),
                "planner": reg.planner if reg else "",
            }
        )
    return routed


def resolve_provider(object_type: str) -> dict[str, Any]:
    reg = get(object_type)
    if reg is None:
        return {"ok": False, "object_type": object_type, "error": "unregistered"}
    return {
        "ok": True,
        "object_type": reg.object_type,
        "provider": reg.provider,
        "planner": reg.planner,
        "routes": list(reg.routes),
        "has_retrieve": reg.retrieve is not None,
    }
