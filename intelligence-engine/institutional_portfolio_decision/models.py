"""CIO-01 InstitutionalPortfolioDecision — immutable, versioned, referential."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AllocationAction:
    ticker: str
    from_weight: float
    to_weight: float
    reason: str
    company_decision_id: str = ""
    company_recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "from_weight": float(self.from_weight),
            "to_weight": float(self.to_weight),
            "delta_weight": round(float(self.to_weight) - float(self.from_weight), 6),
            "reason": self.reason,
            "company_decision_id": self.company_decision_id,
            "company_recommendation": self.company_recommendation,
            "mutates_company_decision": False,
        }


@dataclass(frozen=True)
class ExposureAction:
    dimension: str
    name: str
    from_weight: float
    to_weight: float
    action: str  # Increase | Reduce | Maintain | Diversify
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name": self.name,
            "from_weight": float(self.from_weight),
            "to_weight": float(self.to_weight),
            "delta_weight": round(float(self.to_weight) - float(self.from_weight), 6),
            "action": self.action,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DecisionScorecard:
    sector_diversification: int
    allocation_balance: int
    risk: int
    forecast_alignment: int
    observation_health: int
    decision_agreement: int
    coverage: int
    final_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector_diversification": int(self.sector_diversification),
            "allocation_balance": int(self.allocation_balance),
            "risk": int(self.risk),
            "forecast_alignment": int(self.forecast_alignment),
            "observation_health": int(self.observation_health),
            "decision_agreement": int(self.decision_agreement),
            "coverage": int(self.coverage),
            "final_recommendation": self.final_recommendation,
        }


@dataclass(frozen=True)
class PortfolioCalibration:
    confidence: int
    conviction: str
    decision_agreement: float
    diversification_score: float
    coverage_score: float
    risk_concentration_score: float
    forecast_stability: float
    observation_health: float
    profile_version: str
    contributors_positive: tuple[str, ...] = ()
    contributors_negative: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "confidence": int(self.confidence),
            "conviction": self.conviction,
            "decision_agreement": float(self.decision_agreement),
            "diversification_score": float(self.diversification_score),
            "coverage_score": float(self.coverage_score),
            "risk_concentration_score": float(self.risk_concentration_score),
            "forecast_stability": float(self.forecast_stability),
            "observation_health": float(self.observation_health),
            "profile_version": self.profile_version,
            "contributors_positive": list(self.contributors_positive),
            "contributors_negative": list(self.contributors_negative),
            "llm": False,
        }


@dataclass(frozen=True)
class MonitoringPlan:
    high_priority_holdings: tuple[str, ...] = ()
    required_reviews: tuple[str, ...] = ()
    upcoming_earnings: tuple[str, ...] = ()
    observation_watch: tuple[str, ...] = ()
    scenario_reruns: tuple[str, ...] = ()
    committee_items: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_priority_holdings": list(self.high_priority_holdings),
            "required_reviews": list(self.required_reviews),
            "upcoming_earnings": list(self.upcoming_earnings),
            "observation_watch": list(self.observation_watch),
            "scenario_reruns": list(self.scenario_reruns),
            "committee_items": list(self.committee_items),
        }


@dataclass(frozen=True)
class CompanyDecisionRef:
    """Referential link to an immutable company InstitutionalDecision."""

    ticker: str
    decision_id: str
    recommendation: str
    confidence: int
    conviction: str = ""
    weight: float = 0.0
    role: str = "supporting"  # supporting | contradicting | neutral

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "decision_id": self.decision_id,
            "recommendation": self.recommendation,
            "confidence": int(self.confidence),
            "conviction": self.conviction,
            "weight": float(self.weight),
            "role": self.role,
            "immutable": True,
        }


@dataclass(frozen=True)
class InstitutionalPortfolioDecision:
    """First-class portfolio decision — does not mutate company decisions."""

    portfolio_id: str
    decision_id: str
    decision_version: int
    generated_at: str
    recommendation: str
    confidence: int
    conviction: str
    investment_posture: str
    supporting_decisions: tuple[CompanyDecisionRef, ...] = ()
    contradicting_decisions: tuple[CompanyDecisionRef, ...] = ()
    allocation_actions: tuple[AllocationAction, ...] = ()
    exposure_actions: tuple[ExposureAction, ...] = ()
    portfolio_risks: tuple[dict[str, Any], ...] = ()
    monitoring_items: tuple[str, ...] = ()
    monitoring_plan: Optional[MonitoringPlan] = None
    calibration: Optional[PortfolioCalibration] = None
    scorecard: Optional[DecisionScorecard] = None
    diagnostics: Optional[dict[str, Any]] = None
    lineage: tuple[str, ...] = (
        "Portfolio",
        "Holding",
        "Portfolio Risk",
        "Policy Constraint",
        "Company Decision",
        "Reason",
        "Evidence",
    )
    portfolio_graph_id: str = ""
    portfolio_risk_id: str = ""
    overall_risk: str = ""
    portfolio_risk_summary: Optional[dict[str, Any]] = None
    policy_id: str = ""
    policy_status: str = ""
    policy_summary: Optional[dict[str, Any]] = None
    decision_engine_version: str = ""
    validator_version: str = ""
    rule_path: str = ""
    llm: bool = False
    mutates_company_decisions: bool = False
    consumes_pre01: bool = True
    consumes_pce01: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "decision_id": self.decision_id,
            "decision_version": int(self.decision_version),
            "generated_at": self.generated_at,
            "recommendation": self.recommendation,
            "confidence": int(self.confidence),
            "conviction": self.conviction,
            "investment_posture": self.investment_posture,
            "supporting_decisions": [d.to_dict() for d in self.supporting_decisions],
            "contradicting_decisions": [d.to_dict() for d in self.contradicting_decisions],
            "allocation_actions": [a.to_dict() for a in self.allocation_actions],
            "exposure_actions": [a.to_dict() for a in self.exposure_actions],
            "portfolio_risks": [dict(r) for r in self.portfolio_risks],
            "monitoring_items": list(self.monitoring_items),
            "monitoring_plan": self.monitoring_plan.to_dict() if self.monitoring_plan else None,
            "calibration": self.calibration.to_dict() if self.calibration else None,
            "scorecard": self.scorecard.to_dict() if self.scorecard else None,
            "diagnostics": dict(self.diagnostics or {}),
            "lineage": list(self.lineage),
            "portfolio_graph_id": self.portfolio_graph_id,
            "portfolio_risk_id": self.portfolio_risk_id,
            "overall_risk": self.overall_risk,
            "portfolio_risk_summary": dict(self.portfolio_risk_summary or {}),
            "policy_id": self.policy_id,
            "policy_status": self.policy_status,
            "policy_summary": dict(self.policy_summary or {}),
            "decision_engine_version": self.decision_engine_version,
            "validator_version": self.validator_version,
            "rule_path": self.rule_path,
            "llm": False,
            "mutates_company_decisions": False,
            "consumes_pre01": True,
            "consumes_pce01": True,
        }
