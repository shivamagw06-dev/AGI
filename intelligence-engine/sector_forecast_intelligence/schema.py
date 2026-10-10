"""SFI contracts — Sector Forecast Intelligence (Sprint 11.5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

SFI_VERSION = "0.1.0"
PROGRAMME = "Sector Forecast Intelligence"
PROGRAMME_SHORT = "SFI"
PRIMARY_PRINCIPLE = (
    "SFI does not predict a single future. It evaluates plausible sector pathways "
    "from AGI-owned sector knowledge — never external providers."
)

ScenarioType = Literal["Bull", "Base", "Bear"]
ImpactLabel = Literal[
    "Strong Positive",
    "Positive",
    "Neutral",
    "Moderate",
    "Negative",
    "Strong Negative",
    "Mixed",
]
ConfidenceLabel = Literal["High", "Medium", "Low"]

FORECAST_DIMENSIONS: tuple[str, ...] = (
    "growth",
    "profitability",
    "valuation",
    "competitive_landscape",
    "policy",
    "market_performance",
)

SUPPORTED_SECTORS: tuple[str, ...] = (
    "Banking",
    "IT Services",
    "FMCG",
    "Auto",
    "Capital Goods",
    "Pharma",
)

NO_SFI_ACTIONS = (
    "call_external_providers",
    "fetch_during_ask",
    "predict_single_path_as_certainty",
    "recommend_buy_sell",
    "set_target_prices",
    "invent_evidence",
    "create_independent_macro_view",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "sfi") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class SectorMetricForecast(BaseModel):
    metric: str
    unit: str = ""
    value: float | None = None
    note: str | None = None


class CompanyImpact(BaseModel):
    ticker: str
    sector: str | None = None
    impact: ImpactLabel
    transmission: list[str] = Field(default_factory=list)
    rationale: str
    relationship_refs: list[str] = Field(default_factory=list)


class PeerSectorImpact(BaseModel):
    sector: str
    impact: ImpactLabel
    rationale: str
    relationship_refs: list[str] = Field(default_factory=list)


class SectorScenario(BaseModel):
    scenario_id: str = Field(default_factory=lambda: new_id("sscen"))
    scenario: ScenarioType
    sector: str
    country: str = "India"
    forecast_horizon: str = "12 Months"
    metrics: list[SectorMetricForecast] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    supporting_relationships: list[dict[str, Any]] = Field(default_factory=list)
    macro_drivers: list[dict[str, Any]] = Field(default_factory=list)
    company_impacts: list[CompanyImpact] = Field(default_factory=list)
    peer_sector_impacts: list[PeerSectorImpact] = Field(default_factory=list)
    probability_pct: int | None = None
    confidence_pct: int | None = None
    confidence_label: ConfidenceLabel = "Medium"
    provenance: dict[str, Any] = Field(default_factory=dict)

    def metric_map(self) -> dict[str, float | None]:
        return {m.metric: m.value for m in self.metrics}

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        mmap = self.metric_map()
        data["revenue_growth"] = mmap.get("Revenue Growth")
        data["earnings_growth"] = mmap.get("Earnings Growth")
        data["margin_outlook"] = mmap.get("EBITDA Margin")
        data["valuation_outlook"] = mmap.get("PE")
        data["expected_relative_performance"] = mmap.get("Relative Performance")
        data["roe"] = mmap.get("ROE")
        data["providers_queried"] = []
        return data


class SectorForecastBundle(BaseModel):
    """Evidence pack assembled from Phase 11 knowledge — no judgment alone."""

    bundle_id: str = Field(default_factory=lambda: new_id("sbundle"))
    sector: str
    country: str = "India"
    horizon: str = "12 Months"
    current_sector: dict[str, Any] = Field(default_factory=dict)
    current_regime: dict[str, Any] = Field(default_factory=dict)
    historical_tip: dict[str, Any] = Field(default_factory=dict)
    analogues: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    macro_forecast_tip: dict[str, Any] = Field(default_factory=dict)
    research: dict[str, Any] = Field(default_factory=dict)
    monitoring: list[dict[str, Any]] = Field(default_factory=list)
    completeness_pct: int = 0
    sources: list[str] = Field(default_factory=list)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    programme_version: str = SFI_VERSION


class SectorForecastReport(BaseModel):
    report_id: str = Field(default_factory=lambda: new_id("sreport"))
    version: int = 1
    sector: str
    country: str = "India"
    horizon: str = "12 Months"
    bundle_id: str | None = None
    current_outlook: dict[str, Any] = Field(default_factory=dict)
    current_regime: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[SectorScenario] = Field(default_factory=list)
    probability_distribution: dict[str, int] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    company_impact_matrix: dict[str, dict[str, str]] = Field(default_factory=dict)
    peer_sector_impact_matrix: dict[str, dict[str, str]] = Field(default_factory=dict)
    key_catalysts: list[dict[str, Any]] = Field(default_factory=list)
    major_risks: list[dict[str, Any]] = Field(default_factory=list)
    macro_inheritance: dict[str, Any] = Field(default_factory=dict)
    contradictions: list[str] = Field(default_factory=list)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = SFI_VERSION
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
