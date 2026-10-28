"""IAR diagnostics for admin / IRS."""

from __future__ import annotations

from typing import Any

from analyst_router.schema import ANALYST_REGISTRY


def diagnose(route: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    required = list(route.get("required_analysts") or [])
    optional = list(route.get("optional_analysts") or [])
    suppressed = list(route.get("suppressed_analysts") or [])
    if not required:
        issues.append("no_required_analysts")
    overlap = set(required) & set(suppressed)
    if overlap:
        issues.append(f"required_also_suppressed:{sorted(overlap)}")
    if set(required) & set(optional):
        issues.append("required_optional_overlap")
    if route.get("executed_analysts"):
        issues.append("illegal_analyst_execution")
    unknown = [a for a in required + optional + suppressed if a not in ANALYST_REGISTRY]
    if unknown:
        issues.append(f"unknown_analysts:{unknown}")
    weights = route.get("weights") or {}
    if weights and abs(sum(float(v) for v in weights.values()) - 1.0) > 0.02:
        issues.append("weights_do_not_sum_to_one")
    return {
        "ok": not issues,
        "issues": issues,
        "required_count": len(required),
        "optional_count": len(optional),
        "suppressed_count": len(suppressed),
        "routing_ms": route.get("routing_ms"),
    }
