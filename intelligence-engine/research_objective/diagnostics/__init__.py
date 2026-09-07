"""ROE diagnostics for admin / IRS."""

from __future__ import annotations

from typing import Any


def diagnose(plan: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not plan.get("primary_objective"):
        issues.append("missing_primary_objective")
    if plan.get("requires_clarification"):
        issues.append("requires_clarification")
    conf = (plan.get("routing_confidence") or {}).get("objective_confidence")
    if conf is not None and float(conf) < 0.85:
        issues.append("objective_confidence_below_threshold")
    if plan.get("executed_layers"):
        issues.append("illegal_layer_execution")
    if plan.get("executed_analysts"):
        issues.append("illegal_analyst_execution")
    return {
        "ok": not issues,
        "issues": issues,
        "primary_objective": plan.get("primary_objective"),
        "question_type": plan.get("question_type"),
        "expected_output": plan.get("expected_output"),
        "planning_ms": plan.get("planning_ms"),
    }
