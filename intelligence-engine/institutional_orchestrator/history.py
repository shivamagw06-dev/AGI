"""UAG-01 query result cache — observability only; not business-state ownership."""

from __future__ import annotations

from typing import Any, Optional

from institutional_orchestrator.models import InstitutionalQuery, InstitutionalResponse

# Session-scoped caches for GET /query/{id} — orchestrator remains logically stateless
# regarding domain objects (IDS/PRE/PCE/CIO/ICE remain system of record).
_QUERIES: dict[str, InstitutionalQuery] = {}
_RESPONSES: dict[str, InstitutionalResponse] = {}
_METRICS = {
    "query_count": 0,
    "failed_plans": 0,
    "total_latency_ms": 0.0,
}


def reset_for_tests() -> None:
    _QUERIES.clear()
    _RESPONSES.clear()
    _METRICS["query_count"] = 0
    _METRICS["failed_plans"] = 0
    _METRICS["total_latency_ms"] = 0.0


def record(
    query: InstitutionalQuery,
    response: InstitutionalResponse,
    *,
    ok: bool,
    latency_ms: float,
) -> None:
    _QUERIES[query.query_id] = query
    _RESPONSES[response.query_id] = response
    _METRICS["query_count"] += 1
    _METRICS["total_latency_ms"] += float(latency_ms)
    if not ok:
        _METRICS["failed_plans"] += 1
    # Cap
    if len(_RESPONSES) > 200:
        for key in list(_RESPONSES.keys())[:50]:
            _RESPONSES.pop(key, None)
            _QUERIES.pop(key, None)


def get_query(query_id: str) -> Optional[dict[str, Any]]:
    q = _QUERIES.get(str(query_id) or "")
    r = _RESPONSES.get(str(query_id) or "")
    if q is None and r is None:
        return None
    return {
        "query": q.to_dict() if q else None,
        "response": r.to_dict() if r else None,
    }


def recent(limit: int = 12) -> list[dict[str, Any]]:
    rows = list(_RESPONSES.values())[-limit:]
    return [
        {
            "query_id": r.query_id,
            "intent": r.intent,
            "question": r.question,
            "confidence": r.confidence,
            "objects_consulted": list(r.objects_consulted),
        }
        for r in rows
    ]


def metrics() -> dict[str, Any]:
    n = max(1, _METRICS["query_count"])
    return {
        "query_count": _METRICS["query_count"],
        "failed_plans": _METRICS["failed_plans"],
        "average_latency_ms": round(_METRICS["total_latency_ms"] / n, 2)
        if _METRICS["query_count"]
        else 0.0,
        "active_cached": len(_RESPONSES),
    }
