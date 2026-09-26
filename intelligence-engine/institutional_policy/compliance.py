"""PCE-01 compliance scoring and overall status."""

from __future__ import annotations

from typing import Sequence

from institutional_policy.models import ConstraintResult, PolicyViolation


def overall_status(
    violations: Sequence[PolicyViolation],
    nearing: Sequence[ConstraintResult],
) -> str:
    if any(v.severity == "critical" for v in violations):
        return "Critical Breach"
    if violations:
        return "Breach"
    if nearing:
        return "Warning"
    return "Compliant"


def compliance_score(
    *,
    total_constraints: int,
    passed: int,
    warnings: int,
    violations: Sequence[PolicyViolation],
) -> int:
    if total_constraints <= 0:
        return 100
    score = 100.0
    # Each pass contributes; violations and warnings deduct
    score = 100.0 * (passed / total_constraints)
    score -= 5.0 * warnings
    for v in violations:
        if v.severity == "critical":
            score -= 20.0
        else:
            score -= 12.0
    return int(max(0, min(100, round(score))))
