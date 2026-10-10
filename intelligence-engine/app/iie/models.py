"""IIE domain models — versioned investment intelligence objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class EvidenceRef:
    evidence_id: str
    claim_text: str = ""
    confidence: float = 0.0
    status: str = ""
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Explainability:
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""
    confidence: float = 0.0
    conflicting_evidence: list[dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=_now)
    responsible_engine: str = "iie"
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VersionedAnalysis:
    object_id: str
    object_type: str
    entity_id: str
    version: int
    assessment: str
    confidence: float
    reasoning_summary: str
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    conflicting_evidence: list[dict[str, Any]] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    superseded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DnaDimension:
    dimension: str
    assessment: str
    confidence: float
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    historical_evolution: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompanyDna:
    company_id: str
    dimensions: dict[str, DnaDimension] = field(default_factory=dict)
    version: int = 1
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "version": self.version,
            "updated_at": self.updated_at,
        }


@dataclass
class CompanyIntelligenceProfile:
    company_id: str
    company_name: str
    sections: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class SectorIntelligence:
    sector_id: str
    name: str
    industry_structure: str = ""
    growth_drivers: list[str] = field(default_factory=list)
    competitive_intensity: str = ""
    regulation: str = ""
    demand_outlook: str = ""
    supply_outlook: str = ""
    key_listed_companies: list[str] = field(default_factory=list)
    capacity_additions: list[str] = field(default_factory=list)
    valuation_trends: str = ""
    industry_risks: list[str] = field(default_factory=list)
    industry_catalysts: list[str] = field(default_factory=list)
    government_influence: str = ""
    global_comparisons: str = ""
    version: int = 1
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ThemeIntelligence:
    theme_id: str
    name: str
    description: str = ""
    company_ids: list[str] = field(default_factory=list)
    sector_ids: list[str] = field(default_factory=list)
    version: int = 1
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MacroImpact:
    impact_id: str
    macro_event: str
    chain: list[str]
    direct_impacts: list[dict[str, Any]] = field(default_factory=list)
    indirect_impacts: list[dict[str, Any]] = field(default_factory=list)
    affected_companies: list[str] = field(default_factory=list)
    affected_sectors: list[str] = field(default_factory=list)
    version: int = 1
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Catalyst:
    catalyst_id: str
    title: str
    catalyst_type: str
    expected_date: str | None = None
    probability: float = 0.5
    potential_impact: str = "moderate"
    affected_companies: list[str] = field(default_factory=list)
    affected_sectors: list[str] = field(default_factory=list)
    status: str = "upcoming"
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    version: int = 1
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskItem:
    risk_id: str
    company_id: str
    risk_type: str
    title: str
    description: str = ""
    severity: str = "medium"
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    version: int = 1
    status: str = "active"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OpportunityItem:
    opportunity_id: str
    company_id: str
    opportunity_type: str
    title: str
    description: str = ""
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    version: int = 1
    status: str = "active"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioCase:
    case_type: str  # bull | base | bear
    assumptions: list[str] = field(default_factory=list)
    key_drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    potential_triggers: list[str] = field(default_factory=list)
    probability: float = 0.33
    confidence: float = 0.0
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioSet:
    scenario_id: str
    company_id: str
    bull: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="bull"))
    base: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="base"))
    bear: ScenarioCase = field(default_factory=lambda: ScenarioCase(case_type="bear"))
    version: int = 1
    evidence_ids: list[str] = field(default_factory=list)
    explainability: Explainability = field(default_factory=Explainability)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "company_id": self.company_id,
            "bull": self.bull.to_dict(),
            "base": self.base.to_dict(),
            "bear": self.bear.to_dict(),
            "version": self.version,
            "evidence_ids": self.evidence_ids,
            "explainability": self.explainability.to_dict(),
            "updated_at": self.updated_at,
        }


@dataclass
class InvestmentThesis:
    thesis_id: str
    company_id: str
    business_overview: str = ""
    investment_thesis: str = ""
    competitive_advantages: list[str] = field(default_factory=list)
    growth_drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    valuation_considerations: str = ""
    catalysts: list[str] = field(default_factory=list)
    monitoring_checklist: list[str] = field(default_factory=list)
    evidence_references: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1
    confidence: float = 0.0
    explainability: Explainability = field(default_factory=Explainability)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MonitorItem:
    metric: str
    status: str = "watch"
    last_value: str = ""
    notes: str = ""
    evidence_ids: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MonitoringChecklist:
    company_id: str
    items: list[MonitorItem] = field(default_factory=list)
    version: int = 1
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "items": [i.to_dict() for i in self.items],
            "version": self.version,
            "updated_at": self.updated_at,
        }


@dataclass
class RelationshipEdge:
    edge_id: str
    from_id: str
    to_id: str
    relation_type: str
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonResult:
    comparison_id: str
    company_ids: list[str]
    dimensions: list[str]
    matrix: dict[str, dict[str, Any]] = field(default_factory=dict)
    summary: str = ""
    version: int = 1
    confidence: float = 0.0
    evidence_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_id(prefix: str) -> str:
    return _id(prefix)


def now_iso() -> str:
    return _now()
