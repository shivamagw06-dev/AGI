"""P2.2 Valuation Intelligence — schema & version."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ENGINE_CODE = "valuation_intelligence"
ENGINE_NAME = "Valuation Intelligence"
VERSION = "p2.2-v1.1.0"
WORKSTREAM_ID = "P2.2"
MILESTONE = "phase_2_2"
PROGRAMME = "AGIB_VALUATION_INTELLIGENCE"

FRESHNESS_SLA_DAYS = 14
RUNTIME_BUDGET_S = 3.0

IC10_UNIVERSE = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "ETERNAL",
    "TMPV",
    "SUNPHARMA",
    "NTPC",
    "HAL",
    "ASIANPAINT",
    "ULTRACEMCO",
)


@dataclass
class SubjectMultiples:
    price: float | None = None
    market_cap: float | None = None
    shares_outstanding: float | None = None
    enterprise_value: float | None = None
    net_debt: float | None = None
    pe: float | None = None
    forward_pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    ev_sales: float | None = None
    price_to_sales: float | None = None
    price_to_cash_flow: float | None = None
    peg: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeerSnapshot:
    ticker: str
    price: float | None = None
    pe: float | None = None
    pb: float | None = None
    ev_ebitda: float | None = None
    roe: float | None = None
    eps_cagr_3y: float | None = None
    net_debt: float | None = None
    market_cap: float | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelativeMetric:
    metric: str
    current: float | None = None
    peer_median: float | None = None
    premium_pct: float | None = None
    peer_percentile: float | None = None
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalBand:
    window: str = "10Y"
    median: float | None = None
    high: float | None = None
    low: float | None = None
    current: float | None = None
    percentile: float | None = None
    observations: int = 0
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GrowthMetrics:
    revenue_cagr_3y: float | None = None
    revenue_cagr_5y: float | None = None
    revenue_cagr_10y: float | None = None
    ebitda_cagr_3y: float | None = None
    ebitda_cagr_5y: float | None = None
    ebitda_cagr_10y: float | None = None
    eps_cagr_3y: float | None = None
    eps_cagr_5y: float | None = None
    eps_cagr_10y: float | None = None
    pat_cagr_3y: float | None = None
    pat_cagr_5y: float | None = None
    pat_cagr_10y: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
