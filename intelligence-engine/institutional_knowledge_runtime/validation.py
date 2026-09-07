"""Assertion validation gate."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.schema import ASSERTION_STATES


def validate_assertion(assertion: dict[str, Any]) -> dict[str, Any]:
    """Validate a single assertion."""
    issues: list[str] = []
    status = str(assertion.get("status") or "")
    conf = assertion.get("confidence")

    if status not in ASSERTION_STATES:
        issues.append("invalid_status")

    if conf is not None:
        try:
            c = int(conf)
            if c < 0 or c > 100:
                issues.append("confidence_out_of_range")
        except (TypeError, ValueError):
            issues.append("confidence_invalid")

    if status == "SUPPORTED" and not (assertion.get("evidence_refs") or []):
        issues.append("supported_requires_evidence")

    stmt = str(assertion.get("statement") or "").lower()
    for token in ("buy this", "sell this", "target price", "must buy", "must sell"):
        if token in stmt:
            issues.append("forbidden_recommendation_language")

    deps = assertion.get("dependencies") or []
    if deps and not assertion.get("assertion_id"):
        issues.append("dependencies_require_assertion_id")

    return {
        "assertion_id": assertion.get("assertion_id"),
        "valid": len(issues) == 0,
        "issues": issues,
    }


def validate_assertions(assertions: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate all assertions; return summary."""
    results = [validate_assertion(a) for a in assertions]
    invalid = [r for r in results if not r["valid"]]
    return {
        "passed": len(invalid) == 0,
        "total": len(results),
        "valid_count": len(results) - len(invalid),
        "invalid_count": len(invalid),
        "results": results,
    }
