"""IFAC models — composition contracts only."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

LAYER = "intelligence_fusion_answer_composer"
VERSION = "1.0"

# Provider ids that are external market reference — never executive headlines.
CONSENSUS_PROVIDERS = frozenset(
    {
        "valuation_consensus",
        "capiq_ikt",
    }
)

INSTITUTIONAL_PROVIDERS = frozenset(
    {
        "research_intelligence_engine",
        "forecast_intelligence_engine",
        "macro_intelligence_engine",
        "unified_valuation_engine",
        "historical_valuation_intelligence",
        "valuation_attribution_engine",
        "valuation_policy_engine",
        "market_intelligence_engine",
        "hedge_fund_screens",
        "historical_intelligence",
        "institutional_warehouse",
        "business_intelligence",
        "industry_intelligence",
        "investment_intelligence",
        "valuation_terminal",
    }
)

TEMPLATE_IDS = (
    "company",
    "valuation",
    "forecast",
    "historical",
    "macro",
    "market",
    "compare",
    "hedge_fund",
    "attribution",
)


@dataclass
class EnginePack:
    provider_id: str
    summary: str = ""
    why: list[str] = field(default_factory=list)
    confidence: float = 0.0
    explainability: dict[str, list[str]] = field(default_factory=dict)
    facts: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    empty: bool = True
    ok: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Section:
    id: str
    title: str
    body: str
    primary_engine: Optional[str] = None
    supporting_engines: list[str] = field(default_factory=list)
    explainability: dict[str, list[str]] = field(default_factory=dict)
    confidence: Optional[float] = None
    missing: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComposeResult:
    ok: bool
    layer: str = LAYER
    version: str = VERSION
    template: str = "company"
    family: str = "company"
    summary: str = ""
    why: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    explainability: dict[str, list[str]] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    engines_used: list[str] = field(default_factory=list)
    primary_engine: Optional[str] = None
    consensus_demoted: bool = False
    dqiv: dict[str, Any] = field(default_factory=dict)
    debug: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sections"] = [s if isinstance(s, dict) else s.to_dict() for s in self.sections]
        return d
