"""PRE-01 quality gates — reject incomplete risk objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from institutional_portfolio_risk.models import InstitutionalPortfolioRisk
from institutional_portfolio_risk.schema import VALIDATOR_VERSION


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


def validate_risk(
    risk: InstitutionalPortfolioRisk,
    *,
    holding_count: int = 0,
) -> ValidationResult:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    has_holdings = holding_count > 0 or bool(risk.concentration.largest_position_ticker)
    gates["holdings_present"] = has_holdings
    if not has_holdings:
        errors.append("Missing holdings")

    has_exposures = bool(risk.sector_exposure)
    gates["exposures_present"] = has_exposures
    if not has_exposures:
        errors.append("Missing exposures")

    has_diagnostics = bool(risk.diagnostics)
    gates["diagnostics_present"] = has_diagnostics
    if not has_diagnostics:
        errors.append("Missing diagnostics")

    has_stress = bool(risk.stress_results)
    gates["stress_present"] = has_stress
    if not has_stress:
        errors.append("Missing stress results")

    has_conc = risk.concentration is not None and bool(risk.concentration.level)
    gates["concentration_present"] = has_conc
    if not has_conc:
        errors.append("Missing concentration analysis")

    has_liquidity = risk.liquidity is not None and bool(risk.liquidity.level)
    gates["liquidity_present"] = has_liquidity
    if not has_liquidity:
        errors.append("Missing liquidity analysis")

    has_corr = risk.correlations is not None and bool(risk.correlations.level)
    gates["correlation_present"] = has_corr
    if not has_corr:
        errors.append("Missing correlation analysis")

    has_scorecard = risk.scorecard is not None
    gates["scorecard_present"] = has_scorecard
    if not has_scorecard:
        errors.append("Missing scorecard")

    return ValidationResult(ok=len(errors) == 0, errors=tuple(errors), gates=gates)
