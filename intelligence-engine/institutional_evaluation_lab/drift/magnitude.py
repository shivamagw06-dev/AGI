"""Drift magnitude — compare all major outputs, not only the recommendation."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.drift.schema import MAGNITUDE_FIELDS


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def field_delta(prev: dict[str, Any] | None, cur: dict[str, Any], field: str) -> dict[str, Any]:
    a = _f((prev or {}).get(field))
    b = _f(cur.get(field))
    delta = None
    if a is not None and b is not None:
        delta = round(b - a, 3)
    return {
        "field": field,
        "previous": a,
        "current": b,
        "delta": delta,
        "changed": delta is not None and abs(delta) > 1e-9,
    }


def compute_magnitude(prev: dict[str, Any] | None, cur: dict[str, Any]) -> dict[str, Any]:
    fields = [field_delta(prev, cur, f) for f in MAGNITUDE_FIELDS]
    by_field = {f["field"]: f for f in fields}
    material = [
        f
        for f in fields
        if f["delta"] is not None
        and (
            (f["field"] == "recommendation_readiness" and abs(f["delta"]) >= 2)
            or (f["field"] != "recommendation_readiness" and abs(f["delta"]) >= 0.5)
        )
    ]
    return {
        "fields": fields,
        "by_field": by_field,
        "material_changes": material,
        "decision": {
            "previous": (prev or {}).get("decision"),
            "current": cur.get("decision"),
            "changed": str((prev or {}).get("decision") or "") != str(cur.get("decision") or ""),
        },
    }
