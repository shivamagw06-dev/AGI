"""Portfolio-level calibration — separate from company IDS-02 calibration."""

from __future__ import annotations

from typing import Sequence

from institutional_portfolio.portfolio_entities import InstitutionalPortfolio
from institutional_portfolio_decision.models import (
    CompanyDecisionRef,
    DecisionScorecard,
    PortfolioCalibration,
)
from institutional_portfolio_decision.schema import CALIBRATION_VERSION


def _agreement(refs: Sequence[CompanyDecisionRef]) -> float:
    if not refs:
        return 0.0
    weights = { "BUY": 0.0, "HOLD": 0.0, "SELL": 0.0 }
    total = 0.0
    for r in refs:
        rec = (r.recommendation or "HOLD").upper()
        w = float(r.weight or 0.0)
        weights[rec] = weights.get(rec, 0.0) + w
        total += w
    if total <= 0:
        return 0.0
    return max(weights.values()) / total


def calibrate_portfolio(
    portfolio: InstitutionalPortfolio,
    *,
    refs: Sequence[CompanyDecisionRef],
    hhi: float,
    sector_concentration: float,
    recommendation: str,
    observation_health: float = 0.7,
    forecast_stability: float = 0.7,
) -> tuple[PortfolioCalibration, DecisionScorecard]:
    agreement = _agreement(refs)
    # Effective N from HHI
    eff_n = (1.0 / hhi) if hhi > 0 else 0.0
    diversification = max(0.0, min(1.0, eff_n / 8.0))
    if sector_concentration >= 0.80:
        diversification *= 0.55
    elif sector_concentration >= 0.60:
        diversification *= 0.75

    covered = sum(1 for r in refs if r.decision_id and r.recommendation)
    coverage = covered / max(1, len(portfolio.holdings))
    risk_conc = min(1.0, max(hhi, sector_concentration * 0.5))

    # Confidence blend (0-100)
    base = 55
    base += int(agreement * 18)
    base += int(diversification * 12)
    base += int(coverage * 10)
    base += int(forecast_stability * 6)
    base += int(observation_health * 6)
    base -= int(risk_conc * 16)
    confidence = max(35, min(92, base))

    if confidence >= 78:
        conviction = "HIGH"
    elif confidence >= 60:
        conviction = "MEDIUM"
    else:
        conviction = "LOW"

    positive: list[str] = []
    negative: list[str] = []
    if agreement >= 0.7:
        positive.append("Decision agreement across holdings")
    else:
        negative.append("Mixed company decision references")
    if coverage >= 0.9:
        positive.append("Full company decision coverage")
    else:
        negative.append("Incomplete company decision coverage")
    if diversification >= 0.45:
        positive.append("Acceptable diversification")
    else:
        negative.append("Weak diversification / sector concentration")
    if risk_conc >= 0.25:
        negative.append("Elevated concentration risk")
    if observation_health >= 0.7:
        positive.append("Observation health adequate")
    else:
        negative.append("Observation health weak")

    cal = PortfolioCalibration(
        confidence=confidence,
        conviction=conviction,
        decision_agreement=round(agreement, 4),
        diversification_score=round(diversification, 4),
        coverage_score=round(coverage, 4),
        risk_concentration_score=round(risk_conc, 4),
        forecast_stability=round(forecast_stability, 4),
        observation_health=round(observation_health, 4),
        profile_version=CALIBRATION_VERSION,
        contributors_positive=tuple(positive),
        contributors_negative=tuple(negative),
    )

    scorecard = DecisionScorecard(
        sector_diversification=int(diversification * 100),
        allocation_balance=int(max(0, 100 - risk_conc * 80)),
        risk=int(risk_conc * 100),
        forecast_alignment=int(forecast_stability * 100),
        observation_health=int(observation_health * 100),
        decision_agreement=int(agreement * 100),
        coverage=int(coverage * 100),
        final_recommendation=recommendation,
    )
    return cal, scorecard
