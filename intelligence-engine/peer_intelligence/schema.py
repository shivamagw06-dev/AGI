"""Peer Intelligence Layer (PIL) V1 — schemas.

Answers: How does this company compare to the best and most relevant peers?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PIL_VERSION = "peer-intelligence-layer-v1.0.0"

PEER_TIERS = (
    "direct",
    "sector_leader",
    "industry_leader",
    "global_leader",
    "regional_leader",
    "historical_leader",
)

TREND_LABELS = (
    "improving",
    "stable",
    "deteriorating",
    "accelerating",
    "decelerating",
    "recovering",
    "breaking",
)


@dataclass
class PeerIdentity:
    ticker: str
    name: str
    country: str
    sector: str
    sub_sector: str
    business_model: str
    tier: str = "direct"
    market_cap_bn_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricSeries:
    metric: str
    entity: str
    unit: str
    points: dict[str, float]  # period -> value (e.g. FY22..FY26 or Q labels)
    source: str = ""
    data_class: str = "seed_panel"  # seed_panel|filing|estimate|missing

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonEvidence:
    metric: str
    source: str
    period: str
    peer_universe: list[str]
    confidence: float
    missing_data: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
