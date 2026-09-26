"""PCE-01 quality gates — reject incomplete policy assessments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from institutional_policy.models import InstitutionalPolicyAssessment
from institutional_policy.schema import VALIDATOR_VERSION


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    gates: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "gates": dict(self.gates),
            "validator_version": VALIDATOR_VERSION,
        }


def validate_assessment(
    assessment: InstitutionalPolicyAssessment,
    *,
    holding_count: int = 0,
) -> ValidationResult:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    has_holdings = holding_count > 0
    gates["holdings_present"] = has_holdings
    if not has_holdings:
        errors.append("Missing holdings")

    has_mandate = bool(assessment.mandate) and bool(assessment.profile_id)
    gates["mandate_present"] = has_mandate
    if not has_mandate:
        errors.append("Missing mandate / policy profile")

    has_results = bool(assessment.passed_constraints) or bool(assessment.failed_constraints)
    gates["constraints_evaluated"] = has_results
    if not has_results:
        errors.append("Missing constraint evaluation results")

    has_diagnostics = bool(assessment.diagnostics)
    gates["diagnostics_present"] = has_diagnostics
    if not has_diagnostics:
        errors.append("Missing diagnostics")

    has_status = bool(assessment.overall_status)
    gates["status_present"] = has_status
    if not has_status:
        errors.append("Missing overall status")

    # Consistency: every failed constraint should appear as a violation
    failed_ids = {c.constraint_id for c in assessment.failed_constraints}
    viol_ids = {v.constraint_id for v in assessment.violations}
    consistent = failed_ids <= viol_ids or not failed_ids
    gates["violations_consistent"] = consistent
    if not consistent:
        errors.append("Failed constraints missing from violations")

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors), gates=gates)
