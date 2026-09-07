"""Phase 3.1 — Industry Intelligence Engine schemas.

Industry DNA is the canonical first-class object consumed by later phases.
Deterministic only — no LLM, no fabrication.
Does not modify AGI Core v1.0.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

II_VERSION = "3.1.0"
PROGRAMME = "Phase 3.1 — Industry Intelligence Engine"
SPEC = "AGI-INDUSTRY-INTELLIGENCE-3.1"
ASK_WIRED = True  # Phase 3.1.5 — wired via KUL provider only (Acceptance = 100%)
ASK_WIRED_VIA = "knowledge_unification.providers.industry_intelligence"

COMPETITIVE_STRUCTURES = (
    "fragmented",
    "consolidated",
    "monopoly",
    "duopoly",
    "oligopoly",
    "platform",
    "government",
    "commodity",
    "global",
    "local",
)

CYCLE_TYPES = (
    "expansion",
    "peak",
    "slowdown",
    "recovery",
    "commodity_cycle",
    "credit_cycle",
    "housing_cycle",
    "technology_cycle",
    "interest_rate_cycle",
)

LIFECYCLE_STAGES = (
    "emerging",
    "growth",
    "mature",
    "declining",
    "cyclical",
    "structural_transition",
)


@dataclass
class KPIDefinition:
    key: str
    name: str
    definition: str
    importance: str
    good_range: str
    poor_range: str
    relationships: list[str] = field(default_factory=list)
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PorterForces:
    entry_barriers: str
    supplier_power: str
    buyer_power: str
    substitutes: str
    rivalry: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndustryDNA:
    """Canonical Industry DNA — single source for industry knowledge."""

    key: str
    name: str
    aliases: list[str]
    # Economics
    revenue_drivers: list[str]
    margin_drivers: list[str]
    cost_drivers: list[str]
    value_drivers: list[str]
    capital_intensity: str
    working_capital: str
    cash_conversion: str
    operating_leverage: str
    pricing_power: str
    # Structure
    competitive_structure: str
    porter: PorterForces
    concentration: str
    # Regulation / valuation / lifecycle
    regulators: list[str]
    regulatory_risks: list[str]
    valuation_methods: list[str]
    valuation_why: str
    lifecycle: str
    typical_roic: str
    typical_growth: str
    typical_risks: list[str]
    risk_weightings: dict[str, str]
    # Macro / relationships
    macro_sensitivity: list[str]
    customers: list[str]
    suppliers: list[str]
    adjacent_industries: list[str]
    substitutes: list[str]
    capital_allocation_typical: str
    # KPIs
    kpis: list[KPIDefinition]
    # Causal economics narrative
    why_margins: str
    why_roic: str
    why_leverage: str
    why_working_capital: str
    why_valuation: str
    primary_cycle: str
    fabricated: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class IndustryIntelligencePackage:
    ok: bool
    question: str
    industry: Optional[str] = None
    industry_name: Optional[str] = None
    modules_used: list[str] = field(default_factory=list)
    dna: Optional[dict[str, Any]] = None
    summary: str = ""
    why: list[str] = field(default_factory=list)
    kpis: Optional[list[dict[str, Any]]] = None
    economics: Optional[dict[str, Any]] = None
    valuation: Optional[dict[str, Any]] = None
    regulation: Optional[dict[str, Any]] = None
    competition: Optional[dict[str, Any]] = None
    cycle: Optional[dict[str, Any]] = None
    risks: Optional[dict[str, Any]] = None
    graph: Optional[dict[str, Any]] = None
    cross_industry: Optional[dict[str, Any]] = None
    confidence: float = 0.0
    fabricated: bool = False
    ask_wired: bool = ASK_WIRED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
