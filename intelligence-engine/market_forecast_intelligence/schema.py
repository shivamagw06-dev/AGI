"""MKFI contracts — Market Forecast Intelligence (Sprint 12.5).

Programme short is MKFI to avoid collision with Macroeconomic Forecast Intelligence (MFI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MKFI_VERSION = "0.1.0"
PROGRAMME = "Market Forecast Intelligence"
PROGRAMME_SHORT = "MKFI"
PRIMARY_PRINCIPLE = (
    "MKFI does not predict a single future. It evaluates plausible market pathways "
    "from AGI-owned Market, Macro, Sector and Company Intelligence — never external feeds."
)

ScenarioType = Literal["Bull", "Base", "Bear"]
DirectionLabel = Literal["Bullish", "Neutral", "Bearish"]
TrendLabel = Literal["Improving", "Stable", "Weakening", "Expanding", "Contracting", "Falling", "Rising", "Moderate"]
ConfidenceLabel = Literal["High", "Medium", "Low"]
ImpactLabel = Literal[
    "Strong Positive",
    "Positive",
    "Neutral",
    "Moderate",
    "Negative",
    "Strong Negative",
    "Mixed",
]

FORECAST_HORIZONS: tuple[str, ...] = (
    "1 Month",
    "3 Months",
    "6 Months",
    "12 Months",
)

FORECAST_DIMENSIONS: tuple[str, ...] = (
    "market_direction",
    "breadth",
    "liquidity",
    "volatility",
    "institutional_flows",
    "leadership",
    "cross_asset",
)

SUPPORTED_MARKETS: tuple[str, ...] = (
    "India",
    "Global",
)

NO_MKFI_ACTIONS = (
    "call_external_providers",
    "fetch_during_ask",
    "predict_single_path_as_certainty",
    "recommend_buy_sell",
    "set_target_prices",
    "invent_evidence",
    "query_live_market_feeds",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "mkfi") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class MarketDimensionForecast(BaseModel):
    dimension: str
    value: str | None = None
    note: str | None = None


class SectorLeadershipImpact(BaseModel):
    sector: str
    impact: ImpactLabel
    role: str = "leader"  # leader | weak | emerging | fading
    rationale: str
    relationship_refs: list[str] = Field(default_factory=list)


class MarketScenario(BaseModel):
    scenario_id: str = Field(default_factory=lambda: new_id("mscen"))
    scenario: ScenarioType
    market: str
    country: str = "India"
    forecast_horizon: str = "6 Months"
    market_regime: str | None = None
    market_direction: DirectionLabel = "Neutral"
    breadth: str = "Stable"
    liquidity: str = "Stable"
    volatility: str = "Moderate"
    institutional_flows: str = "Balanced"
    sector_leadership: list[str] = Field(default_factory=list)
    weak_sectors: list[str] = Field(default_factory=list)
    cross_asset_outlook: dict[str, str] = Field(default_factory=dict)
    dimensions: list[MarketDimensionForecast] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    invalidators: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    supporting_relationships: list[dict[str, Any]] = Field(default_factory=list)
    macro_assumptions: list[dict[str, Any]] = Field(default_factory=list)
    sector_impacts: list[SectorLeadershipImpact] = Field(default_factory=list)
    probability_pct: int | None = None
    confidence_pct: int | None = None
    confidence_label: ConfidenceLabel = "Medium"
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["providers_queried"] = []
        return data


class MarketForecastBundle(BaseModel):
    """Evidence pack assembled from Phase 12 + inherited Macro/Sector knowledge."""

    bundle_id: str = Field(default_factory=lambda: new_id("mbundle"))
    market: str
    country: str = "India"
    horizon: str = "6 Months"
    current_market: dict[str, Any] = Field(default_factory=dict)
    current_regime: dict[str, Any] = Field(default_factory=dict)
    historical_tip: dict[str, Any] = Field(default_factory=dict)
    analogues: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    macro_forecast_tip: dict[str, Any] = Field(default_factory=dict)
    sector_forecast_tip: dict[str, Any] = Field(default_factory=dict)
    research: dict[str, Any] = Field(default_factory=dict)
    monitoring: list[dict[str, Any]] = Field(default_factory=list)
    completeness_pct: int = 0
    sources: list[str] = Field(default_factory=list)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MKFI_VERSION


class MarketForecastReport(BaseModel):
    report_id: str = Field(default_factory=lambda: new_id("mreport"))
    version: int = 1
    market: str
    country: str = "India"
    horizon: str = "6 Months"
    bundle_id: str | None = None
    current_outlook: dict[str, Any] = Field(default_factory=dict)
    current_regime: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[MarketScenario] = Field(default_factory=list)
    probability_distribution: dict[str, int] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    sector_leadership_forecast: dict[str, list[str]] = Field(default_factory=dict)
    sector_impact_matrix: dict[str, dict[str, str]] = Field(default_factory=dict)
    key_catalysts: list[dict[str, Any]] = Field(default_factory=list)
    major_risks: list[dict[str, Any]] = Field(default_factory=list)
    invalidation_alerts: list[str] = Field(default_factory=list)
    macro_inheritance: dict[str, Any] = Field(default_factory=dict)
    sector_inheritance: dict[str, Any] = Field(default_factory=dict)
    contradictions: list[str] = Field(default_factory=list)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MKFI_VERSION
    providers_queried: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["scenarios"] = [s.to_public_dict() for s in self.scenarios]
        data["is_recommendation"] = False
        data["is_price_prediction"] = False
        data["predicts_single_path"] = False
        data["providers_queried"] = []
        data["collected_on_request"] = False
        return data
