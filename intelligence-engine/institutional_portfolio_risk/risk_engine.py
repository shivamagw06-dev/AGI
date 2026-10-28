"""PRE-01 risk engine — assemble InstitutionalPortfolioRisk."""

from __future__ import annotations

import hashlib
from typing import Any, Optional, Sequence

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_portfolio_risk.concentration import evaluate_concentration
from institutional_portfolio_risk.correlation import evaluate_correlation
from institutional_portfolio_risk.exposures import country_exposure_rows, sector_exposure_rows
from institutional_portfolio_risk.factor import evaluate_factors, market_beta_estimate
from institutional_portfolio_risk.liquidity import evaluate_liquidity
from institutional_portfolio_risk.models import (
    InstitutionalPortfolioRisk,
    RiskMonitoring,
    RiskScorecard,
)
from institutional_portfolio_risk.schema import (
    LINEAGE_CHAIN,
    RISK_ENGINE_VERSION,
    VALIDATOR_VERSION,
)
from institutional_portfolio_risk.stress import evaluate_stress, worst_stress

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_LEVEL_RANK = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}


def _risk_id(portfolio_id: str, version: int, overall: str) -> str:
    raw = f"{portfolio_id}|{version}|{overall}|{RISK_ENGINE_VERSION}"
    return f"pre-{portfolio_id.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _max_level(*levels: str) -> str:
    best = "Low"
    for lv in levels:
        if _LEVEL_RANK.get(lv, 0) > _LEVEL_RANK.get(best, 0):
            best = lv
    return best


def _score_from_level(level: str) -> int:
    return {"Low": 85, "Moderate": 65, "High": 40, "Critical": 20}.get(level, 50)


def _invert_score(level: str) -> int:
    """For resilience / diversification — higher is better."""
    return {"Low": 90, "Moderate": 70, "High": 45, "Critical": 20}.get(level, 50)


def _build_warnings(
    *,
    conc_level: str,
    liq_level: str,
    corr_level: str,
    overall: str,
    worst_impact: float,
    top_sector: str,
    largest_ticker: str,
    largest_w: float,
) -> tuple[str, ...]:
    warnings: list[str] = []
    if conc_level in {"High", "Critical"}:
        warnings.append(
            f"Concentration {conc_level}: {largest_ticker} at {largest_w:.0%}; "
            f"{top_sector or 'sector'} dominates"
        )
    if liq_level in {"High", "Critical"}:
        warnings.append(f"Liquidity {liq_level}: elevated exit-day profile")
    if corr_level in {"High", "Critical"}:
        warnings.append(f"Correlation {corr_level}: holdings move together under shared drivers")
    if worst_impact <= -12:
        warnings.append(f"Stress impact severe: worst scenario {worst_impact:.1f}%")
    if overall == "Critical":
        warnings.append("Overall portfolio risk Critical — escalate to Investment Committee")
    return tuple(warnings)


def _build_recommendations(
    *,
    conc_level: str,
    liq_level: str,
    corr_level: str,
    cash_weight: float,
    top_sector: str,
) -> tuple[str, ...]:
    recs: list[str] = []
    if conc_level in {"High", "Critical"}:
        recs.append(f"Trim largest {top_sector or 'sector'} names; raise cash / diversifiers")
    if corr_level in {"High", "Critical"}:
        recs.append("Add non-correlated sectors to reduce common-factor exposure")
    if liq_level in {"High", "Critical"}:
        recs.append("Reduce illiquid sleeves or stage exits over multiple sessions")
    if cash_weight < 0.08 and conc_level != "Low":
        recs.append("Increase cash buffer toward 10–12% for risk absorption")
    if not recs:
        recs.append("Maintain risk posture; re-run stress after material allocation changes")
    return tuple(recs)


def _monitoring(
    *,
    warnings: Sequence[str],
    conc_level: str,
    worst_label: str,
    overall: str,
) -> RiskMonitoring:
    critical = tuple(w for w in warnings if "Critical" in w or "severe" in w.lower())
    emerging: list[str] = []
    if conc_level == "High":
        emerging.append("Concentration approaching Critical threshold")
    if worst_label:
        emerging.append(f"Watch scenario: {worst_label}")
    drift = ()
    if overall in {"High", "Critical"}:
        drift = ("Risk elevated vs diversified policy book",)
    reviews = (
        "Quarterly portfolio risk review",
        "Post-RBI policy stress refresh",
    )
    obs = ("IO-01 concentration observations", "Company decision confidence drift")
    return RiskMonitoring(
        critical_risks=critical,
        emerging_risks=tuple(emerging),
        risk_drift=drift,
        upcoming_reviews=reviews,
        observation_dependencies=obs,
    )


def generate_portfolio_risk(
    portfolio: InstitutionalPortfolio,
    *,
    previous_version: int = 0,
) -> InstitutionalPortfolioRisk:
    """Build authoritative InstitutionalPortfolioRisk from PKG-01 portfolio."""
    conc = evaluate_concentration(
        portfolio.holdings,
        portfolio.exposures,
        cash_weight=float(portfolio.cash_weight or 0.0),
    )
    liq = evaluate_liquidity(
        portfolio.holdings,
        cash_weight=float(portfolio.cash_weight or 0.0),
    )
    corr = evaluate_correlation(portfolio.holdings)
    factors = evaluate_factors(portfolio.holdings)
    stress = evaluate_stress(
        portfolio.holdings,
        cash_weight=float(portfolio.cash_weight or 0.0),
    )
    sectors = sector_exposure_rows(portfolio.holdings, portfolio.exposures)
    countries = country_exposure_rows(portfolio.holdings, portfolio.exposures)
    beta = market_beta_estimate(portfolio.holdings)

    worst = worst_stress(stress)
    worst_impact = float(worst.portfolio_impact_pct) if worst else 0.0
    stress_level = "Low"
    if worst_impact <= -15:
        stress_level = "Critical"
    elif worst_impact <= -10:
        stress_level = "High"
    elif worst_impact <= -5:
        stress_level = "Moderate"

    overall = _max_level(conc.level, liq.level, corr.level, stress_level)

    warnings = _build_warnings(
        conc_level=conc.level,
        liq_level=liq.level,
        corr_level=corr.level,
        overall=overall,
        worst_impact=worst_impact,
        top_sector=conc.top_sector,
        largest_ticker=conc.largest_position_ticker,
        largest_w=conc.largest_position_weight,
    )
    recommendations = _build_recommendations(
        conc_level=conc.level,
        liq_level=liq.level,
        corr_level=corr.level,
        cash_weight=float(portfolio.cash_weight or 0.0),
        top_sector=conc.top_sector,
    )

    # Coverage: decisions attached / holdings
    with_decisions = sum(1 for h in portfolio.holdings if h.decision_id or h.recommendation)
    coverage = int(
        round(100.0 * with_decisions / len(portfolio.holdings)) if portfolio.holdings else 0
    )

    scorecard = RiskScorecard(
        overall_risk=overall,
        concentration=_score_from_level(conc.level),
        liquidity=_score_from_level(liq.level),
        correlation=_score_from_level(corr.level),
        stress_resilience=_invert_score(stress_level),
        diversification=int(round(conc.diversification_score)),
        coverage=coverage,
        warning_count=len(warnings),
    )
    monitoring = _monitoring(
        warnings=warnings,
        conc_level=conc.level,
        worst_label=worst.label if worst else "",
        overall=overall,
    )

    version = int(previous_version or 0) + 1
    rid = _risk_id(portfolio.portfolio_id, version, overall)

    return InstitutionalPortfolioRisk(
        portfolio_id=portfolio.portfolio_id,
        risk_id=rid,
        risk_version=version,
        generated_at=now_iso(),
        overall_risk=overall,
        concentration=conc,
        sector_exposure=sectors,
        factor_exposure=factors,
        liquidity=liq,
        correlations=corr,
        stress_results=stress,
        market_beta=beta,
        country_exposure=countries,
        warnings=warnings,
        recommendations=recommendations,
        scorecard=scorecard,
        monitoring=monitoring,
        diagnostics=None,
        lineage=LINEAGE_CHAIN,
        portfolio_graph_id=portfolio.graph_id,
        risk_engine_version=RISK_ENGINE_VERSION,
        validator_version=VALIDATOR_VERSION,
        llm=False,
    )


def risk_summary_for_cio(risk: InstitutionalPortfolioRisk) -> dict[str, Any]:
    """Compact risk dict consumed by CIO-01 decision engine."""
    return {
        "risk_id": risk.risk_id,
        "risk_version": risk.risk_version,
        "overall_risk": risk.overall_risk,
        "hhi": risk.hhi,
        "sector_concentration": risk.sector_concentration,
        "top_sector": risk.top_sector,
        "concentration_level": risk.concentration.level,
        "liquidity_level": risk.liquidity.level,
        "correlation_level": risk.correlations.level,
        "market_beta": risk.market_beta,
        "warnings": list(risk.warnings),
        "recommendations": list(risk.recommendations),
        "worst_stress": (
            min(risk.stress_results, key=lambda s: s.portfolio_impact_pct).to_dict()
            if risk.stress_results
            else None
        ),
        "scorecard": risk.scorecard.to_dict() if risk.scorecard else None,
        "authoritative": True,
        "source": "PRE-01",
    }
