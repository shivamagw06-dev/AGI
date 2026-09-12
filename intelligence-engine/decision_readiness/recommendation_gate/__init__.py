"""Policy and recommendation gate."""

from __future__ import annotations

from typing import Any


def evaluate_policy(
    thesis: dict[str, Any],
    debate: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    policy = payload.get("policy_context")
    policy = policy if isinstance(policy, dict) else {}
    violations = [
        v for v in (policy.get("violations") or []) if isinstance(v, dict)
    ]
    critical = [
        v for v in violations
        if str(v.get("severity") or "").lower() == "critical"
    ]
    checks = {
        "evidence_policy": bool(policy.get("evidence_policy", True)),
        "recommendation_policy": bool(policy.get("recommendation_policy", True)),
        "analyst_scope": bool(policy.get("analyst_scope", True)),
        "research_standards": bool(policy.get("research_standards", True)),
        "audit_complete": bool(
            policy.get(
                "audit_complete",
                (thesis.get("audit") or {}).get("passed", True)
                and (debate.get("audit") or {}).get("passed", True),
            )
        ),
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    score -= min(0.5, 0.25 * len(critical))
    score = max(0.0, min(1.0, score))
    return {
        "dimension": "Policy",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()) and not critical,
        "checks": checks,
        "violations": violations,
        "critical_violations": critical,
        "critical_violation_count": len(critical),
        "recommendation_allowed": not critical
        and checks["recommendation_policy"],
        "strengths": [
            name.replace("_", " ").title()
            for name, passed in checks.items()
            if passed
        ],
        "weaknesses": [
            name.replace("_", " ").title()
            for name, passed in checks.items()
            if not passed
        ],
    }
