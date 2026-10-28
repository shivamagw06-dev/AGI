"""CIO-01 quality gates for InstitutionalPortfolioDecision."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from institutional_portfolio_decision.models import InstitutionalPortfolioDecision
from institutional_portfolio_decision.schema import PORTFOLIO_RECOMMENDATIONS, VALIDATOR_VERSION


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    gates: dict[str, bool]
    validator_version: str = VALIDATOR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "gates": dict(self.gates),
            "validator_version": self.validator_version,
        }


def validate_decision(
    decision: InstitutionalPortfolioDecision,
    *,
    holding_count: int = 0,
) -> ValidationResult:
    errors: list[str] = []
    if holding_count <= 0 and not decision.supporting_decisions and not decision.contradicting_decisions:
        errors.append("no holdings")
    if not decision.supporting_decisions and not decision.contradicting_decisions:
        errors.append("missing company decisions")
    if decision.calibration is None:
        errors.append("missing calibration")
    if decision.monitoring_plan is None:
        errors.append("missing monitoring plan")
    if not decision.diagnostics:
        errors.append("missing diagnostics")
    if not decision.allocation_actions:
        # Allow empty only for No Action Required / Maintain with explicit scorecard
        if decision.recommendation not in {"No Action Required", "Maintain Allocation"}:
            errors.append("missing allocation actions")
        elif decision.recommendation == "Maintain Allocation":
            # Still require at least empty tuple is ok for maintain — gate passes with note
            pass
    if decision.recommendation not in PORTFOLIO_RECOMMENDATIONS:
        errors.append(f"invalid recommendation: {decision.recommendation}")
    if decision.mutates_company_decisions:
        errors.append("company decisions must remain immutable")
    if not decision.lineage:
        errors.append("missing lineage")
    if decision.scorecard is None:
        errors.append("missing scorecard")

    # Soft: Maintain/No Action may have zero allocation actions
    has_alloc = bool(decision.allocation_actions) or decision.recommendation in {
        "No Action Required",
        "Maintain Allocation",
    }

    gates = {
        "has_holdings_or_refs": bool(
            holding_count > 0 or decision.supporting_decisions or decision.contradicting_decisions
        ),
        "has_company_decisions": bool(
            decision.supporting_decisions or decision.contradicting_decisions
        ),
        "has_calibration": decision.calibration is not None,
        "has_monitoring_plan": decision.monitoring_plan is not None,
        "has_diagnostics": bool(decision.diagnostics),
        "has_allocation_actions": has_alloc,
        "has_scorecard": decision.scorecard is not None,
        "has_lineage": bool(decision.lineage),
        "company_decisions_immutable": not decision.mutates_company_decisions,
        "valid_recommendation": decision.recommendation in PORTFOLIO_RECOMMENDATIONS,
    }
    # Recompute errors for soft allocation gate
    errors = [e for e in errors if e != "missing allocation actions" or not has_alloc]
    if not has_alloc and "missing allocation actions" not in errors:
        errors.append("missing allocation actions")

    return ValidationResult(ok=not errors, errors=tuple(errors), gates=gates)
