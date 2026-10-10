"""QUE quality gates and validation."""

from __future__ import annotations

from typing import Any

UNDERSTANDING_REQUIRED: tuple[str, ...] = (
    "literal_question",
    "investor_meaning",
    "decision_type",
    "research_objective",
    "primary_investment_question",
    "response_objective",
    "expected_deliverable",
)

BRIEF_REQUIRED: tuple[str, ...] = (
    *UNDERSTANDING_REQUIRED,
    "required_information",
    "optional_information",
    "irrelevant_information",
    "knowledge_gap",
    "top_research_questions",
    "response_promise",
    "success_criteria",
)


def validate_understanding(qu: dict[str, Any]) -> dict[str, Any]:
    """QUE v1.0 gates — understanding fields."""
    missing = [f for f in UNDERSTANDING_REQUIRED if not qu.get(f)]
    checks = {f: bool(qu.get(f)) for f in UNDERSTANDING_REQUIRED}
    checks["decision_not_unknown"] = qu.get("decision_type") not in (None, "", "Unknown")
    checks["confidence_gt_zero"] = (qu.get("confidence") or 0) > 0
    return {
        "passed": len(missing) == 0 and checks["confidence_gt_zero"],
        "missing_fields": missing,
        "checks": checks,
    }


def validate_research_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """QUE v1.1 gates — full research brief."""
    missing = [f for f in BRIEF_REQUIRED if not brief.get(f)]
    checks = {f: bool(brief.get(f)) for f in BRIEF_REQUIRED}
    checks["three_top_questions"] = len(brief.get("top_research_questions") or []) >= 3
    checks["decision_not_unknown"] = brief.get("decision_type") not in (None, "", "Unknown")
    checks["confidence_gt_zero"] = (brief.get("confidence") or 0) > 0
    return {
        "passed": len(missing) == 0 and all(checks.values()),
        "missing_fields": missing,
        "checks": checks,
    }
