"""ICE-01 quality gates — reject incomplete committee resolutions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from institutional_committee.models import InstitutionalCommitteeResolution
from institutional_committee.schema import RESOLUTION_STATUSES, VALIDATOR_VERSION


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


def validate_resolution(resolution: InstitutionalCommitteeResolution) -> ValidationResult:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    has_decision = bool(resolution.portfolio_decision_id)
    gates["portfolio_decision_linked"] = has_decision
    if not has_decision:
        errors.append("No portfolio decision exists")

    has_policy = bool(resolution.policy_id)
    gates["policy_assessment_linked"] = has_policy
    if not has_policy:
        errors.append("No policy assessment is linked")

    has_risk = bool(resolution.portfolio_risk_id)
    gates["risk_assessment_linked"] = has_risk
    if not has_risk:
        errors.append("No risk assessment is linked")

    has_rationale = bool(resolution.rationale)
    gates["rationale_present"] = has_rationale
    if not has_rationale:
        errors.append("No rationale is recorded")

    has_outcome = bool(resolution.outcome) and bool(resolution.status)
    gates["outcome_assigned"] = has_outcome
    if not has_outcome:
        errors.append("No outcome is assigned")

    status_ok = resolution.status in RESOLUTION_STATUSES
    gates["status_valid"] = status_ok
    if not status_ok:
        errors.append(f"Invalid resolution status: {resolution.status}")

    has_votes = bool(resolution.votes)
    gates["votes_present"] = has_votes
    if not has_votes:
        errors.append("No committee votes recorded")

    has_diagnostics = bool(resolution.diagnostics)
    gates["diagnostics_present"] = has_diagnostics
    if not has_diagnostics:
        errors.append("Missing diagnostics")

    gates["mutates_upstream_false"] = resolution.mutates_upstream is False
    if resolution.mutates_upstream:
        errors.append("Committee must not mutate upstream objects")

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors), gates=gates)
