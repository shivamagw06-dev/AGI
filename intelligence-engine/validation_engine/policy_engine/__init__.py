"""Policy engine — allowed output, recommendation/forecast/evidence policies."""

from __future__ import annotations

from typing import Any

DISALLOWED_PATTERNS = (
    "guaranteed returns",
    "sure shot",
    "cannot lose",
    "insider tip",
    "manipulate",
)


def validate_policy(
    *,
    question: str,
    primary_objective: str | None = None,
    intent_family: str | None = None,
) -> dict[str, Any]:
    q = (question or "").lower()
    issues: list[str] = []
    score = 1.0

    for pat in DISALLOWED_PATTERNS:
        if pat in q:
            issues.append("disallowed_request")
            score = 0.0
            break

    # Unsupported claim requests
    if "guarantee" in q and ("return" in q or "profit" in q):
        issues.append("unsupported_guarantee")
        score = min(score, 0.1)

    # Recommendation policy: buy/sell questions are allowed but must be evidence-backed
    recommendation_allowed = True
    forecast_allowed = True
    if "educational" in (intent_family or "") or "explain" in q:
        # educational should not produce buy/sell
        if "should i buy" in q or "should i sell" in q:
            issues.append("education_recommendation_conflict")
            score -= 0.2

    # Output style policy
    allowed_output = "institutional_research"
    if "explain" in q:
        allowed_output = "educational_guide"
    elif "portfolio" in q:
        allowed_output = "portfolio_memorandum"

    score = max(0.0, min(1.0, score))
    status = "blocked" if score < 0.2 else ("warning" if issues else "compliant")

    return {
        "status": status,
        "score": round(score, 4),
        "issues": issues,
        "allowed_output": allowed_output,
        "recommendation_policy": "evidence_backed" if recommendation_allowed else "disallowed",
        "forecast_policy": "scenario_based" if forecast_allowed else "disallowed",
        "evidence_policy": "tier1_preferred",
        "no_unsupported_claims": "unsupported_guarantee" not in issues and "disallowed_request" not in issues,
    }
