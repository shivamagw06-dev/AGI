"""Phase 3.3 — Portfolio Intelligence Engine schemas.

Deterministic portfolio evaluation. Never issues BUY/SELL.
Consumes Investment Intelligence + Industry DNA. Does not modify Core.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

PI_VERSION = "3.3.0"
PROGRAMME = "Phase 3.3 — Portfolio Intelligence Engine"
SPEC = "AGI-PORTFOLIO-INTELLIGENCE-3.3"
ASK_WIRED = True  # Phase 3.3.5 — wired via KUL provider only (Acceptance = 100%)
ASK_WIRED_VIA = "knowledge_unification.providers.portfolio_intelligence"
RECOMMENDATION_POLICY = "observations_only_no_buy_sell"

STYLE_FACTORS = ("growth", "value", "quality", "momentum", "low_volatility")


@dataclass
class PortfolioPackage:
    ok: bool
    question: str
    portfolio_id: Optional[str] = None
    portfolio_name: Optional[str] = None
    modules_used: list[str] = field(default_factory=list)
    portfolio_summary: str = ""
    diversification: Optional[dict[str, Any]] = None
    key_risks: list[str] = field(default_factory=list)
    sector_exposures: Optional[dict[str, Any]] = None
    monitoring_priorities: list[str] = field(default_factory=list)
    evidence: Optional[dict[str, Any]] = None
    unknowns: list[str] = field(default_factory=list)
    portfolio_object: Optional[dict[str, Any]] = None
    construction: Optional[dict[str, Any]] = None
    exposures: Optional[dict[str, Any]] = None
    risk_budget: Optional[dict[str, Any]] = None
    correlation: Optional[dict[str, Any]] = None
    quality: Optional[dict[str, Any]] = None
    attribution: Optional[dict[str, Any]] = None
    rebalancing: Optional[dict[str, Any]] = None
    scenarios: Optional[dict[str, Any]] = None
    monitoring: Optional[dict[str, Any]] = None
    graph: Optional[dict[str, Any]] = None
    compare: Optional[dict[str, Any]] = None
    confidence: float = 0.0
    fabricated: bool = False
    recommendation: None = None
    recommendation_policy: str = RECOMMENDATION_POLICY
    ask_wired: bool = ASK_WIRED
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation"] = None
        d["summary"] = self.portfolio_summary or self.summary
        return d
