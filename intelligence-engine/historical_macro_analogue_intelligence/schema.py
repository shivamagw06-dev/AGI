"""HMAI contracts — Historical Macro Analogue Intelligence (Sprint 10.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field

HMAI_VERSION = "0.1.0"
PROGRAMME = "Historical Macro Analogue Intelligence"
PROGRAMME_SHORT = "HMAI"
PRIMARY_PRINCIPLE = (
    "Analogues must be deterministic, explainable and fully traceable to historical evidence. "
    "No analogue is returned without an explainable similarity calculation across macro dimensions."
)

ConfidenceLabel = Literal["High", "Medium", "Low"]

SIMILARITY_DIMENSIONS: tuple[str, ...] = (
    "interest_rate",
    "inflation",
    "gdp",
    "liquidity",
    "fiscal",
    "currency",
    "bond_yield",
    "global_growth",
    "commodity",
)

NO_HMAI_ACTIONS = (
    "return_analogue_without_similarity",
    "call_external_providers",
    "fetch_during_ask",
    "invent_historical_outcomes",
    "recommend_buy_sell",
    "forecast_without_evidence",  # forecasting is Sprint 10.5
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "hmai") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def stable_analogue_id(country: str, current_period: str, matched_period: str) -> str:
    return str(
        uuid5(NAMESPACE_URL, f"hmai:{country}:{current_period}:{matched_period}")
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
    kind: str  # historical_macro | timeline | relationship | research | continuous_macro
    summary: str
    period: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    weight: float = 1.0


class MacroRegime(BaseModel):
    """Point-in-time macro environment vector for a country/period."""

    regime_id: str = Field(default_factory=lambda: new_id("regime"))
    country: str = "India"
    period: str
    label: str
    features: dict[str, float] = Field(default_factory=dict)
    feature_units: dict[str, str] = Field(default_factory=dict)
    outcome: str | None = None
    equity_outcome: str | None = None
    timeline_refs: list[str] = Field(default_factory=list)
    relationship_refs: list[str] = Field(default_factory=list)
    research_refs: list[str] = Field(default_factory=list)
    source_layers: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


class HistoricalMacroAnalogue(BaseModel):
    analogue_id: str = Field(default_factory=lambda: new_id("analogue"))
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
    key_differences: list[str] = Field(default_factory=list)
    relevant_relationships: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[SupportingEvidence] = Field(default_factory=list)
    timeline_refs: list[str] = Field(default_factory=list)
    research_refs: list[str] = Field(default_factory=list)
    rank: int = 0
    explainability: dict[str, Any] = Field(default_factory=dict)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = HMAI_VERSION
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["providers_queried"] = []
        data["similarity_explainable"] = True
        data["collected_on_request"] = False
        return data
