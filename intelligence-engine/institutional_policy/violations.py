"""PCE-01 violation assembly — actionable policy breaches."""

from __future__ import annotations

from typing import Sequence

from institutional_policy.models import ConstraintResult, PolicyViolation


def _severity(result: ConstraintResult) -> str:
    if result.status != "Violation":
        return "warning"
    # Material breaches by category / magnitude
    if result.category in {"position", "diversification", "risk"}:
        if result.operator == "max" and result.actual >= result.limit * 1.25:
            return "critical"
        return "breach"
    if result.category == "sector" and result.operator == "max" and result.actual >= result.limit * 1.2:
        return "critical"
    return "breach"


def build_violations(results: Sequence[ConstraintResult]) -> tuple[PolicyViolation, ...]:
    out: list[PolicyViolation] = []
    for r in results:
        if r.status != "Violation":
            continue
        out.append(
            PolicyViolation(
                constraint_id=r.constraint_id,
                category=r.category,
                name=r.name,
                severity=_severity(r),
                actual=r.actual,
                limit=r.limit,
                detail=r.detail,
                required_action=r.action or f"Remediate {r.name}",
                action_ticker=r.action_ticker,
                from_value=r.from_value,
                to_value=r.to_value,
            )
        )
    # Critical first, then breach
    order = {"critical": 0, "breach": 1, "warning": 2}
    out.sort(key=lambda v: (order.get(v.severity, 9), -abs(v.actual - v.limit)))
    return tuple(out)


def required_actions(violations: Sequence[PolicyViolation]) -> tuple[str, ...]:
    seen: list[str] = []
    for v in violations:
        text = v.required_action
        if text and text not in seen:
            seen.append(text)
    return tuple(seen)
