"""UAG-01 diagnostics — planner / coverage / latency (no business state)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_orchestrator.models import InstitutionalQuery, InstitutionalResponse
from institutional_orchestrator.schema import (
    ORCHESTRATOR_VERSION,
    UAG_VERSION,
    UAG_WORKSTREAM_ID,
    VALIDATOR_VERSION,
)


def build_diagnostics(
    query: InstitutionalQuery,
    response: Optional[InstitutionalResponse] = None,
    *,
    validation: Optional[dict[str, Any]] = None,
    latency_ms: float = 0.0,
    routed: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    steps = list(response.execution_plan) if response else list(query.execution_plan)
    return {
        "workstream_id": UAG_WORKSTREAM_ID,
        "version": UAG_VERSION,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "query_id": query.query_id,
        "intent": query.intent,
        "planner_chosen": list(query.planners),
        "objects_consulted": list(response.objects_consulted) if response else [],
        "required_objects": list(query.required_objects),
        "missing_objects": list(response.missing_objects) if response else [],
        "coverage": (
            round(
                100.0
                * sum(1 for s in steps if s.status == "ok")
                / max(1, len(steps)),
                1,
            )
        ),
        "latency_ms": round(float(latency_ms), 2),
        "fallbacks": [s.object_type for s in steps if s.status == "missing"],
        "execution_graph": [s.to_dict() for s in steps],
        "routed": routed or [],
        "validation": validation or {},
        "llm": False,
        "generates_recommendations": False,
        "owns_business_state": False,
        "stateless": True,
    }
