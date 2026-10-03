"""Phase 3.0 — Business Intelligence Foundation schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

BI_VERSION = "3.0.0"
PROGRAMME = "Phase 3.0 — Business Intelligence Foundation"
SPEC = "AGI-BI-FOUNDATION-3.0"

BUSINESS_TYPES = (
    "subscription",
    "marketplace",
    "manufacturer",
    "retail",
    "bank",
    "insurance",
    "saas",
    "conglomerate",
    "platform",
    "utility",
    "infrastructure",
    "commodity",
    "nbfc",
    "hospital",
    "airline",
    "cement",
    "it_services",
    "unknown",
)

MOAT_DIMENSIONS = (
    "brand",
    "network_effects",
    "scale",
    "switching_costs",
    "cost_leadership",
    "technology",
    "licensing",
    "distribution",
    "customer_lock_in",
)

LIFECYCLE_STAGES = (
    "startup",
    "hypergrowth",
    "growth",
    "expansion",
    "mature",
    "turnaround",
    "decline",
    "cyclical_recovery",
)

RISK_TYPES = (
    "demand",
    "execution",
    "commodity",
    "currency",
    "technology_disruption",
    "regulatory",
    "customer_concentration",
    "supplier_concentration",
    "refinancing",
    "political",
)

GROWTH_MODES = (
    "organic",
    "acquisition_led",
    "pricing_led",
    "volume_led",
    "mix_improvement",
    "geographic_expansion",
    "cross_selling",
    "upselling",
    "capacity_expansion",
    "market_share_gains",
)


@dataclass
class ScoredDimension:
    key: str
    score: int  # 0–100
    rating: str  # Strong | Medium | Weak | Unknown
    evidence: list[str] = field(default_factory=list)
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessModelCard:
    business_type: str
    how_it_makes_money: str
    revenue_streams: list[str]
    customer_segments: list[str]
    distribution_channels: list[str]
    cost_structure: list[str]
    fixed_vs_variable: dict[str, str]
    unit_economics_summary: str
    recurring_vs_one_time: str
    capital_intensity: str
    working_capital_profile: str
    operating_leverage: str
    pricing_model: str
    confidence: float
    evidence: list[dict[str, Any]] = field(default_factory=list)
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MoatCard:
    dimensions: list[ScoredDimension]
    primary_moats: list[str]
    durability: str
    summary: str
    confidence: float
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "primary_moats": self.primary_moats,
            "durability": self.durability,
            "summary": self.summary,
            "confidence": self.confidence,
            "fabricated": self.fabricated,
        }


@dataclass
class IndustryCard:
    industry: str
    value_drivers: list[str]
    porter: dict[str, Any]
    concentration: str
    summary: str
    confidence: float
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonCard:
    companies: list[str]
    axes: dict[str, dict[str, Any]]
    summary: str
    confidence: float
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BusinessIntelligencePackage:
    ok: bool
    question: str
    company: Optional[str]
    ticker: Optional[str]
    industry: Optional[str]
    modules_used: list[str]
    business_model: Optional[dict[str, Any]] = None
    value_drivers: Optional[dict[str, Any]] = None
    unit_economics: Optional[dict[str, Any]] = None
    moat: Optional[dict[str, Any]] = None
    industry_structure: Optional[dict[str, Any]] = None
    growth: Optional[dict[str, Any]] = None
    management: Optional[dict[str, Any]] = None
    risks: Optional[dict[str, Any]] = None
    lifecycle: Optional[dict[str, Any]] = None
    comparison: Optional[dict[str, Any]] = None
    knowledge_graph: Optional[dict[str, Any]] = None
    summary: str = ""
    why: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    fabricated: bool = False
    version: str = BI_VERSION
    programme: str = PROGRAMME

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
