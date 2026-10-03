"""Institutional policy validation."""

from __future__ import annotations

from typing import Any


def validate_policy(
    trace: dict[str, Any],
    evidence_trace: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    decision = trace["stage_data"].get("Decision Readiness") or {}
    policy_context = payload.get("policy_context")
    policy_context = (
        policy_context if isinstance(policy_context, dict) else {}
    )
    decision_policy = (
        (decision.get("dimensions") or {}).get("Policy")
        or decision.get("policy")
        or {}
    )
    citations = [
        evidence.get("source")
        for conclusion in evidence_trace.get("conclusion_traces") or []
        for evidence in conclusion.get("evidence") or []
    ]
    violations = list(policy_context.get("violations") or [])
    violations.extend(decision_policy.get("violations") or [])
    critical = [
        violation
        for violation in violations
        if isinstance(violation, dict)
        and str(violation.get("severity") or "").lower() == "critical"
    ]
    checks = {
        "recommendation_policy": bool(
            policy_context.get(
                "recommendation_policy",
                decision_policy.get("recommendation_allowed", True),
            )
        ),
        "evidence_policy": bool(
            policy_context.get("evidence_policy", True)
        )
        and evidence_trace.get("traceability") == 1.0,
        "citation_policy": bool(citations)
        and all(source for source in citations),
        "transparency_policy": bool(trace.get("nodes"))
        and bool(evidence_trace.get("conclusion_traces")),
        "institutional_governance": bool(
            policy_context.get("institutional_governance", True)
        )
        and not critical,
    }
    score = sum(1 for passed in checks.values() if passed) / len(checks)
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()) and not critical,
        "checks": checks,
        "violations": violations,
        "critical_violations": critical,
        "critical_violation_count": len(critical),
        "citation_count": len(citations),
        "uncited_evidence_count": sum(1 for source in citations if not source),
    }
