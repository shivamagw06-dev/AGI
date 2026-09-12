"""MFI contracts — Macroeconomic Forecast Intelligence (Sprint 10.5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MFI_VERSION = "0.1.0"
PROGRAMME = "Macroeconomic Forecast Intelligence"
PROGRAMME_SHORT = "MFI"
PRIMARY_PRINCIPLE = (
    "MFI does not predict a single future. It evaluates plausible macroeconomic paths "
    "from AGI-owned macro knowledge — never external providers."
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
    "monetary_policy",
    "inflation",
    "growth",
    "fiscal",
    "external_sector",
    "financial_markets",
)

NO_MFI_ACTIONS = (
    "call_external_providers",
    "fetch_during_ask",
    "predict_single_path_as_certainty",
    "recommend_buy_sell",
    "set_target_prices",
    "invent_evidence",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "mfi") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class MacroIndicatorForecast(BaseModel):
    indicator: str
    unit: str = ""
    value: float | None = None
    note: str | None = None


class SectorImpact(BaseModel):
    sector: str
    impact: ImpactLabel
    rationale: str
    relationship_refs: list[str] = Field(default_factory=list)


class CompanyImpact(BaseModel):
    ticker: str
    sector: str | None = None
    impact: ImpactLabel
    transmission: list[str] = Field(default_factory=list)
    rationale: str
    relationship_refs: list[str] = Field(default_factory=list)


class MacroScenario(BaseModel):
    scenario_id: str = Field(default_factory=lambda: new_id("mscen"))
    scenario: ScenarioType
    country: str = "India"
    forecast_horizon: str = "12 Months"
    indicators: list[MacroIndicatorForecast] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)
    drivers: list[str] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    sector_impacts: list[SectorImpact] = Field(default_factory=list)
    company_impacts: list[CompanyImpact] = Field(default_factory=list)
    probability_pct: int | None = None
    confidence_pct: int | None = None
    confidence_label: ConfidenceLabel = "Medium"
    provenance: dict[str, Any] = Field(default_factory=dict)

    def indicator_map(self) -> dict[str, float | None]:
        return {i.indicator: i.value for i in self.indicators}

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["gdp"] = self.indicator_map().get("GDP")
        data["inflation"] = self.indicator_map().get("CPI")
        data["repo_rate"] = self.indicator_map().get("Repo Rate")
        data["fiscal_deficit"] = self.indicator_map().get("Fiscal Deficit")
        data["usdinr"] = self.indicator_map().get("USDINR")
        data["providers_queried"] = []
        return data


class MacroForecastBundle(BaseModel):
    """Evidence pack assembled from Phase 10 knowledge — no judgment alone."""

    bundle_id: str = Field(default_factory=lambda: new_id("mbundle"))
    country: str = "India"
    region: str = "India"  # India | Global
    horizon: str = "12 Months"
    current_regime: dict[str, Any] = Field(default_factory=dict)
    current_macro: dict[str, Any] = Field(default_factory=dict)
    historical_tip: dict[str, Any] = Field(default_factory=dict)
    analogues: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    research: dict[str, Any] = Field(default_factory=dict)
    monitoring: list[dict[str, Any]] = Field(default_factory=list)
    completeness_pct: int = 0
    sources: list[str] = Field(default_factory=list)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MFI_VERSION


class MacroForecastReport(BaseModel):
    report_id: str = Field(default_factory=lambda: new_id("mreport"))
    version: int = 1
    country: str = "India"
    region: str = "India"
    horizon: str = "12 Months"
    bundle_id: str | None = None
    current_regime: dict[str, Any] = Field(default_factory=dict)
    scenarios: list[MacroScenario] = Field(default_factory=list)
    probability_distribution: dict[str, int] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    sector_impact_matrix: dict[str, dict[str, str]] = Field(default_factory=dict)
    company_impact_matrix: dict[str, dict[str, str]] = Field(default_factory=dict)
    key_catalysts: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_events: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    published: bool = False
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    programme_version: str = MFI_VERSION
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
