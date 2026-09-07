"""HMKAI contracts — Historical Market Analogue Intelligence (Sprint 12.4).

Programme short is HMKAI to avoid collision with Historical Macro Analogue Intelligence (HMAI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field

HMKAI_VERSION = "0.1.0"
PROGRAMME = "Historical Market Analogue Intelligence"
PROGRAMME_SHORT = "HMKAI"
PRIMARY_PRINCIPLE = (
    "Analogues must be deterministic, explainable and fully traceable to historical evidence. "
    "No analogue is returned without an explainable similarity calculation across market dimensions."
)

ConfidenceLabel = Literal["High", "Medium", "Low"]

SIMILARITY_DIMENSIONS: tuple[str, ...] = (
    "market_regime",
    "breadth",
    "liquidity",
    "volatility",
    "fii_flows",
    "dii_flows",
    "leadership",
    "bond_yields",
    "usd_index",
    "interest_rate",
    "inflation",
)

NO_HMKAI_ACTIONS = (
    "return_analogue_without_similarity",
    "call_external_providers",
    "fetch_during_ask",
    "invent_historical_outcomes",
    "recommend_buy_sell",
    "forecast_without_evidence",  # forecasting is Sprint 12.5
)

SUPPORTED_MARKETS: tuple[str, ...] = (
    "India",
    "Global",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "hmkai") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def stable_analogue_id(market: str, current_period: str, matched_period: str) -> str:
    return str(
        uuid5(NAMESPACE_URL, f"hmkai:{market}:{current_period}:{matched_period}")
    )


class DimensionScore(BaseModel):
    dimension: str
    dimension_key: str
    current_value: float | None = None
    historical_value: float | None = None
    score: float
    weight: float
    matched: bool
    scale: float


class SupportingEvidence(BaseModel):
    kind: str  # historical_market | timeline | relationship | research | continuous_market | historical_macro
    summary: str
    period: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    weight: float = 1.0


class MarketRegime(BaseModel):
    """Point-in-time market environment vector for a market/period."""

    regime_id: str = Field(default_factory=lambda: new_id("mregime"))
    market: str
    market_key: str | None = None
    country: str = "India"
    period: str
    label: str
    regime_label: str | None = None  # Bull / Bear / Recovery / ...
    features: dict[str, float] = Field(default_factory=dict)
    feature_units: dict[str, str] = Field(default_factory=dict)
    outcome: str | None = None
    equity_outcome: str | None = None
    historical_outcome_bundle: dict[str, Any] = Field(default_factory=dict)
    timeline_refs: list[str] = Field(default_factory=list)
    relationship_refs: list[str] = Field(default_factory=list)
    research_refs: list[str] = Field(default_factory=list)
    source_layers: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class HistoricalMarketAnalogue(BaseModel):
    analogue_id: str = Field(default_factory=lambda: new_id("manalogue"))
    market: str
    market_key: str | None = None
    country: str = "India"
    current_regime: str
    current_period: str
    matched_period: str
    matched_label: str
    similarity_score: float
    confidence: ConfidenceLabel = "Medium"
    matching_dimensions: list[str] = Field(default_factory=list)
    non_matching_dimensions: list[str] = Field(default_factory=list)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    historical_outcome: str | None = None
    equity_outcome: str | None = None
    historical_outcome_bundle: dict[str, Any] = Field(default_factory=dict)
    key_differences: list[str] = Field(default_factory=list)
    relevant_relationships: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[SupportingEvidence] = Field(default_factory=list)
    supporting_research: list[str] = Field(default_factory=list)
    supporting_relationships: list[dict[str, Any]] = Field(default_factory=list)
    timeline_refs: list[str] = Field(default_factory=list)
    research_refs: list[str] = Field(default_factory=list)
    rank: int = 0
    version: int = 1
    explainability: dict[str, Any] = Field(default_factory=dict)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = HMKAI_VERSION
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        data["similarity_explainable"] = True
        data["collected_on_request"] = False
        return data
