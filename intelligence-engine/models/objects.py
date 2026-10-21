"""Versioned reusable knowledge objects produced by FIML models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from models.base import now_iso


@dataclass
class AccountingAnalysis:
    subject_id: str
    accounting_quality_score: float
    cash_flow_quality: float
    accrual_quality: float
    earnings_quality: float
    cash_conversion: float
    red_flags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence_links: list[str] = field(default_factory=list)
    confidence: float = 0.5
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessModelProfile:
    subject_id: str
    business_quality_score: float
    revenue_streams: list[str] = field(default_factory=list)
    operating_model_summary: str = ""
    revenue_driver_graph: list[dict[str, Any]] = field(default_factory=list)
    cost_driver_graph: list[dict[str, Any]] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recurring_revenue_share: float = 0.0
    customer_concentration: float = 0.0
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndustryModel:
    industry_id: str
    name: str
    demand_drivers: list[str] = field(default_factory=list)
    supply_drivers: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)
    typical_risks: list[str] = field(default_factory=list)
    preferred_valuation_models: list[str] = field(default_factory=list)
    capital_intensity: str = "medium"
    industry_structure: str = ""
    historical_cycles: list[str] = field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompetitionProfile:
    subject_id: str
    competitive_score: float
    moat_strength: float
    competitive_position: str
    threats: list[str] = field(default_factory=list)
    peer_comparison: list[dict[str, Any]] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapitalAllocationProfile:
    subject_id: str
    capital_allocation_score: float
    management_discipline: str
    value_creation: str
    roic: float = 0.0
    roce: float = 0.0
    historical_decisions: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceProfile:
    subject_id: str
    governance_score: float
    red_flags: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskProfile:
    subject_id: str
    overall_risk_score: float
    risk_matrix: list[dict[str, Any]] = field(default_factory=list)
    monitoring_signals: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValuationGuidance:
    subject_id: str
    industry_id: str
    recommended_models: list[str]
    primary_model: str
    rationale: list[str] = field(default_factory=list)
    avoid_models: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionProfile:
    subject_id: str
    investment_quality: float
    conviction: float
    expected_return: float
    expected_downside: float
    margin_of_safety: float
    suggested_action: str
    confidence: float
    key_risks: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    explainability: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
