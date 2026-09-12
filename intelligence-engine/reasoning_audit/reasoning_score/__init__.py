"""Institutional reasoning scorecard and certification state."""

from __future__ import annotations

from statistics import pstdev
from typing import Any

from reasoning_audit.schema import AUDIT_STATES, AUDIT_WEIGHTS


def score_reasoning(
    *,
    traceability: dict[str, Any],
    logic: dict[str, Any],
    assumptions: dict[str, Any],
    contradictions: dict[str, Any],
    calibration: dict[str, Any],
    scope: dict[str, Any],
    policy: dict[str, Any],
    completeness: float,
) -> dict[str, Any]:
    dimensions = {
        "Evidence Traceability": float(traceability.get("traceability") or 0),
        "Logical Consistency": float(logic.get("score") or 0),
        "Assumption Quality": float(assumptions.get("score") or 0),
        "Contradiction Handling": float(contradictions.get("score") or 0),
        "Confidence Calibration": float(calibration.get("score") or 0),
        "Policy Compliance": float(policy.get("score") or 0),
        "Analyst Scope": float(scope.get("score") or 0),
        "Reasoning Completeness": float(completeness),
    }
    overall = sum(
        AUDIT_WEIGHTS[name] * dimensions[name]
        for name in AUDIT_WEIGHTS
    )
    hard_failures = {
        "orphan_conclusions": int(traceability.get("orphan_count") or 0),
        "unsupported_inferences": len(
            logic.get("unsupported_inferences") or []
        ),
        "critical_policy_violations": int(
            policy.get("critical_violation_count") or 0
        ),
        "analyst_scope_violations": int(
            scope.get("violation_count") or 0
        ),
    }
    hard_blocked = any(value > 0 for value in hard_failures.values())
    quality_complete = (
        traceability.get("traceability") == 1.0
        and logic.get("passed")
        and contradictions.get("all_contradictions_disclosed")
        and calibration.get("passed")
        and scope.get("passed")
        and policy.get("passed")
        and completeness == 1.0
    )
    if hard_blocked or overall < 0.55:
        status = "FAIL"
    elif overall < 0.75 or not logic.get("passed"):
        status = "REVIEW REQUIRED"
    elif overall >= 0.9 and quality_complete and assumptions.get("passed"):
        status = "PASS"
    else:
        status = "PASS WITH OBSERVATIONS"
    assert status in AUDIT_STATES

    explainability = (
        0.5 * dimensions["Evidence Traceability"]
        + 0.5 * dimensions["Reasoning Completeness"]
    )
    scorecard = {
        "evidence_traceability": round(
            dimensions["Evidence Traceability"] * 100
        ),
        "logic": round(dimensions["Logical Consistency"] * 100),
        "calibration": round(
            dimensions["Confidence Calibration"] * 100
        ),
        "assumptions": round(dimensions["Assumption Quality"] * 100),
        "contradictions": round(
            dimensions["Contradiction Handling"] * 100
        ),
        "explainability": round(explainability * 100),
        "policy": round(dimensions["Policy Compliance"] * 100),
        "analyst_scope": round(dimensions["Analyst Scope"] * 100),
        "reasoning_completeness": round(
            dimensions["Reasoning Completeness"] * 100
        ),
    }
    values = list(dimensions.values())
    confidence = max(
        0.2,
        min(0.98, overall * (1.0 - min(0.3, pstdev(values)))),
    )
    return {
        "audit_status": status,
        "reasoning_score": round(overall, 4),
        "reasoning_score_pct": round(overall * 100),
        "dimensions": {
            name: {
                "score": round(score, 4),
                "score_pct": round(score * 100),
                "weight": AUDIT_WEIGHTS[name],
                "weighted_contribution": round(
                    score * AUDIT_WEIGHTS[name], 4
                ),
            }
            for name, score in dimensions.items()
        },
        "scorecard": {
            **scorecard,
            "overall_institutional_reasoning_score": round(overall * 100),
        },
        "hard_failures": hard_failures,
        "hard_blocked": hard_blocked,
        "quality_complete": quality_complete,
        "confidence": round(confidence, 4),
        "confidence_pct": round(confidence * 100),
    }
