"""IPI schema — Institutional Portfolio Intelligence Phase 5 targets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IPI_VERSION = "institutional-portfolio-intelligence-v1.0.0"
MODULE_CODE = "IPI"
PROGRAMME = "Institutional Portfolio Intelligence"

ACTIONS = (
    "Increase",
    "Reduce",
    "Hold",
    "Exit",
    "Watch",
    "Replace",
    "Hedge",
    "Withhold",
)

PHASE5_TARGETS: dict[str, float] = {
    "portfolio_suite": 95.0,
    "pdg_coverage": 100.0,
    "unsupported_recommendations": 0.0,
}


@dataclass
class PortfolioPolicy:
    max_stock_weight: float = 0.07
    max_sector_weight: float = 0.25
    max_country_weight: float = 0.90
    max_theme_weight: float = 0.30
    min_liquidity_score: float = 0.55
    max_drawdown: float = 0.28
    max_single_name_risk_contribution: float = 0.18
    risk_budget: float = 0.12
    cash_reserve_min: float = 0.05

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_POLICY = PortfolioPolicy()


@dataclass
class PortfolioHolding:
    symbol: str
    weight: float
    sector: str
    industry: str = ""
    country: str = "IN"
    currency: str = "INR"
    market_cap: str = "large"
    theme: str = ""
    liquidity_score: float = 0.85
    beta: float = 1.0
    volatility: float = 0.22
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
