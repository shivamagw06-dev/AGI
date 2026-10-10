"""Phase 3.2 — Investment Intelligence Engine schemas.

Deterministic investment evaluation. Never issues BUY/SELL.
Consumes Business Intelligence + Industry DNA. Does not modify Core.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

IIE_VERSION = "3.2.0"
PROGRAMME = "Phase 3.2 — Investment Intelligence Engine"
SPEC = "AGI-INVESTMENT-INTELLIGENCE-3.2"
ASK_WIRED = True  # Phase 3.2.5 — wired via KUL provider only (Acceptance = 100%)
ASK_WIRED_VIA = "knowledge_unification.providers.investment_intelligence"

EVIDENCE_LEVELS = ("high", "medium", "low", "unknown")
SCENARIO_CASES = ("bull", "base", "bear")
COMMITTEE_ROLES = (
    "business_analyst",
    "financial_analyst",
    "industry_analyst",
    "valuation_analyst",
    "risk_analyst",
    "governance_analyst",
    "portfolio_analyst",
    "macro_analyst",
    "committee_chair",
)

QUALITY_DIMENSIONS = (
    "business_quality",
    "management_quality",
    "financial_quality",
    "capital_allocation",
    "competitive_position",
    "industry_structure",
    "cash_conversion",
    "balance_sheet",
    "governance",
    "evidence_strength",
)

RISK_TYPES = (
    "business",
    "financial",
    "industry",
    "execution",
    "governance",
    "regulatory",
    "technology",
    "macro",
    "commodity",
    "customer",
    "supplier",
    "fx",
    "tail",
)

RECOMMENDATION_POLICY = "observations_only_no_buy_sell"


@dataclass
class EvidenceCard:
    strength: str  # high|medium|low|unknown
    reasons: list[str] = field(default_factory=list)
    coverage: str = ""
    contradictions: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    freshness: str = "mixed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CatalystCard:
    key: str
    name: str
    direction: str  # positive|negative|mixed
    probability: str
    time_horizon: str
    potential_impact: str
    confidence: str
    supporting_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskCard:
    key: str
    name: str
    probability: str
    severity: str
    mitigants: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    leading_indicators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioCard:
    case: str  # bull|base|bear
    revenue: str
    margins: str
    cash_flow: str
    capital_allocation: str
    valuation_drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    key_assumptions: list[str] = field(default_factory=list)
    confidence: str = "medium"
    unknowns: list[str] = field(default_factory=list)
    # Explicit: no price targets
    price_target: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["price_target"] = None  # always none
        d["policy"] = "no_price_targets"
        return d


@dataclass
class QualityDimension:
    key: str
    score: int  # 0-100
    rating: str
    why: str
    helped: list[str] = field(default_factory=list)
    hurt: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommitteeContribution:
    role: str
    observations: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    agreement: list[str] = field(default_factory=list)
    disagreement: list[str] = field(default_factory=list)
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InvestmentThesis:
    entity: str
    industry: Optional[str]
    business_quality: str
    industry_position: str
    competitive_advantage: str
    capital_allocation: str
    financial_strength: str
    growth_drivers: list[str]
    valuation_drivers: list[str]
    key_risks: list[str]
    catalysts: list[str]
    evidence_strength: str
    unknowns: list[str]
    recommendation: None = None  # never set

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = None
        d["recommendation_policy"] = RECOMMENDATION_POLICY
        return d


@dataclass
class InvestmentPackage:
    ok: bool
    question: str
    entity: Optional[str] = None
    industry: Optional[str] = None
    modules_used: list[str] = field(default_factory=list)
    executive_summary: str = ""
    supporting_analysis: list[str] = field(default_factory=list)
    evidence: Optional[dict[str, Any]] = None
    unknowns: list[str] = field(default_factory=list)
    monitoring_points: list[str] = field(default_factory=list)
    thesis: Optional[dict[str, Any]] = None
    quality: Optional[dict[str, Any]] = None
    catalysts: Optional[list[dict[str, Any]]] = None
    risks: Optional[list[dict[str, Any]]] = None
    scenarios: Optional[dict[str, Any]] = None
    valuation: Optional[dict[str, Any]] = None
    capital_allocation: Optional[dict[str, Any]] = None
    committee: Optional[dict[str, Any]] = None
    graph: Optional[dict[str, Any]] = None
    confidence: float = 0.0
    fabricated: bool = False
    recommendation: None = None
    recommendation_policy: str = RECOMMENDATION_POLICY
    ask_wired: bool = ASK_WIRED
    # alias for acceptance suites that look for summary
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = None
        d["summary"] = self.executive_summary or self.summary
        return d
