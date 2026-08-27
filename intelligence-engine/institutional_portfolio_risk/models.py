"""PRE-01 InstitutionalPortfolioRisk — immutable, versioned, authoritative."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ConcentrationRisk:
    level: str  # Low | Moderate | High | Critical
    hhi: float
    effective_n: float
    largest_position_ticker: str
    largest_position_weight: float
    top_5_weight: float
    sector_concentration: float
    top_sector: str
    single_theme_exposure: float
    diversification_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "hhi": float(self.hhi),
            "effective_n": float(self.effective_n),
            "largest_position_ticker": self.largest_position_ticker,
            "largest_position_weight": float(self.largest_position_weight),
            "top_5_weight": float(self.top_5_weight),
            "sector_concentration": float(self.sector_concentration),
            "top_sector": self.top_sector,
            "single_theme_exposure": float(self.single_theme_exposure),
            "diversification_score": float(self.diversification_score),
        }


@dataclass(frozen=True)
class LiquidityRisk:
    level: str
    portfolio_liquidity_score: float
    average_exit_days: float
    illiquid_weight: float
    cash_weight: float
    positions: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "portfolio_liquidity_score": float(self.portfolio_liquidity_score),
            "average_exit_days": float(self.average_exit_days),
            "illiquid_weight": float(self.illiquid_weight),
            "cash_weight": float(self.cash_weight),
            "positions": [dict(p) for p in self.positions],
        }


@dataclass(frozen=True)
class CorrelationRisk:
    level: str
    average_correlation: float
    max_pair_correlation: float
    pairs: tuple[dict[str, Any], ...] = ()
    provider: str = "proxy_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "average_correlation": float(self.average_correlation),
            "max_pair_correlation": float(self.max_pair_correlation),
            "pairs": [dict(p) for p in self.pairs],
            "provider": self.provider,
            "estimated": True,
        }


@dataclass(frozen=True)
class FactorExposure:
    factors: tuple[dict[str, Any], ...]
    dominant_factor: str
    dominant_weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "factors": [dict(f) for f in self.factors],
            "dominant_factor": self.dominant_factor,
            "dominant_weight": float(self.dominant_weight),
        }


@dataclass(frozen=True)
class StressResult:
    scenario: str
    label: str
    portfolio_impact_pct: float
    severity: str
    affected_holdings: tuple[str, ...]
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "label": self.label,
            "portfolio_impact_pct": float(self.portfolio_impact_pct),
            "severity": self.severity,
            "affected_holdings": list(self.affected_holdings),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class RiskScorecard:
    overall_risk: str
    concentration: int
    liquidity: int
    correlation: int
    stress_resilience: int
    diversification: int
    coverage: int
    warning_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_risk": self.overall_risk,
            "concentration": int(self.concentration),
            "liquidity": int(self.liquidity),
            "correlation": int(self.correlation),
            "stress_resilience": int(self.stress_resilience),
            "diversification": int(self.diversification),
            "coverage": int(self.coverage),
            "warning_count": int(self.warning_count),
        }


@dataclass(frozen=True)
class RiskMonitoring:
    critical_risks: tuple[str, ...] = ()
    emerging_risks: tuple[str, ...] = ()
    risk_drift: tuple[str, ...] = ()
    upcoming_reviews: tuple[str, ...] = ()
    observation_dependencies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "critical_risks": list(self.critical_risks),
            "emerging_risks": list(self.emerging_risks),
            "risk_drift": list(self.risk_drift),
            "upcoming_reviews": list(self.upcoming_reviews),
            "observation_dependencies": list(self.observation_dependencies),
        }


@dataclass(frozen=True)
class InstitutionalPortfolioRisk:
    """Authoritative portfolio risk object for the Investment Office."""

    portfolio_id: str
    risk_id: str
    risk_version: int
    generated_at: str
    overall_risk: str
    concentration: ConcentrationRisk
    sector_exposure: tuple[dict[str, Any], ...]
    factor_exposure: FactorExposure
    liquidity: LiquidityRisk
    correlations: CorrelationRisk
    stress_results: tuple[StressResult, ...]
    market_beta: float = 1.0
    country_exposure: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    scorecard: Optional[RiskScorecard] = None
    monitoring: Optional[RiskMonitoring] = None
    diagnostics: Optional[dict[str, Any]] = None
    lineage: tuple[str, ...] = (
        "Portfolio",
        "Holding",
        "Risk Dimension",
        "Company Decision",
        "Reason",
        "Evidence",
    )
    portfolio_graph_id: str = ""
    risk_engine_version: str = ""
    validator_version: str = ""
    llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "risk_id": self.risk_id,
            "risk_version": int(self.risk_version),
            "generated_at": self.generated_at,
            "overall_risk": self.overall_risk,
            "concentration": self.concentration.to_dict(),
            "sector_exposure": [dict(s) for s in self.sector_exposure],
            "factor_exposure": self.factor_exposure.to_dict(),
            "liquidity": self.liquidity.to_dict(),
            "correlations": self.correlations.to_dict(),
            "stress_results": [s.to_dict() for s in self.stress_results],
            "market_beta": float(self.market_beta),
            "country_exposure": [dict(c) for c in self.country_exposure],
            "warnings": list(self.warnings),
            "recommendations": list(self.recommendations),
            "scorecard": self.scorecard.to_dict() if self.scorecard else None,
            "monitoring": self.monitoring.to_dict() if self.monitoring else None,
            "diagnostics": dict(self.diagnostics or {}),
            "lineage": list(self.lineage),
            "portfolio_graph_id": self.portfolio_graph_id,
            "risk_engine_version": self.risk_engine_version,
            "validator_version": self.validator_version,
            "llm": False,
        }

    # Convenience accessors for CIO-01
    @property
    def hhi(self) -> float:
        return float(self.concentration.hhi)

    @property
    def sector_concentration(self) -> float:
        return float(self.concentration.sector_concentration)

    @property
    def top_sector(self) -> str:
        return self.concentration.top_sector
