"""ILR diagnostics for admin / IRS."""

from __future__ import annotations

from typing import Any

from layer_router.schema import REGISTERED_LAYERS


def diagnose(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    required = list(plan.get("required_layers") or [])
    suppressed = list(plan.get("suppressed_layers") or [])
    if not required:
        issues.append("no_required_layers")
    if set(required) & set(suppressed):
        issues.append("required_also_suppressed")
    if plan.get("executed_layers"):
        issues.append("illegal_layer_execution")
    unknown = [x for x in required if x not in REGISTERED_LAYERS]
    if unknown:
        issues.append(f"unknown_layers:{unknown}")
    # Dependency integrity: every dep of required must be in participants
    deps = plan.get("dependencies") or {}
    participants = set(required) | set(plan.get("optional_layers") or [])
    for layer, needs in deps.items():
        if layer not in participants:
            continue
        for n in needs or []:
            if n not in participants:
                issues.append(f"missing_dependency:{layer}->{n}")
    return {
        "ok": not issues,
        "issues": issues,
        "planning_ms": plan.get("planning_ms"),
        "required_count": len(required),
        "suppressed_count": len(suppressed),
        "runtime_reduction": plan.get("runtime_reduction"),
    }
