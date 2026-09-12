"""Portfolio Intelligence Office (PIO) V1 — schemas.

Primary question: Does this company improve this specific portfolio?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PIO_VERSION = "portfolio-intelligence-office-v1.0.0"

SUITABILITY_DIMS = (
    "strategic_fit",
    "portfolio_fit",
    "diversification_benefit",
    "risk_contribution",
    "capital_efficiency",
    "monitoring_requirement",
)

# Portfolio Quality Engine dimensions (portfolio-level, not company-only)
PQE_DIMENSIONS = (
    "business_quality",
    "financial_quality",
    "management_quality",
    "accounting_quality",
    "capital_allocation_quality",
    "valuation_discipline",
    "evidence_coverage",
    "knowledge_confidence",
)


@dataclass
class Holding:
    ticker: str
    weight: float
    sector: str
    industry: str = ""
    country: str = "IN"
    market_cap: str = "large"
    style: str = "quality"
    thesis: str = ""
    conviction: str = "medium"  # high|medium|low
    entry_date: str = ""
    cost_basis: float | None = None
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioProfile:
    portfolio_id: str
    name: str
    objective: str
    benchmark: str
    base_currency: str = "INR"
    risk_tolerance: str = "moderate"
    horizon: str = "5y+"
    target_return: str = ""
    max_drawdown: float = 0.25
    liquidity_requirement: str = "institutional"
    tax_preferences: str = ""
    sector_limits: dict[str, float] = field(default_factory=dict)
    single_name_limit: float = 0.12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
