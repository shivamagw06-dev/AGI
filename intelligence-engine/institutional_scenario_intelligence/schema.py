"""ISI contracts — Bull / Base / Bear scenario evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

ISI_VERSION = "0.1.0"
PROGRAMME = "Institutional Scenario Intelligence"
PROGRAMME_SHORT = "ISI"
PRIMARY_QUESTION = "What are the plausible outcomes?"

NO_ISI_JUDGMENT = (
    "predict_stock_prices",
    "recommend_buy_sell",
    "assign_probabilities",  # Sprint 9.4 PCI
    "set_target_prices",
    "optimise_portfolios",
    "execute_trades",
    "discard_contradictions",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class ScenarioType(str, Enum):
    BULL = "Bull"
    BASE = "Base"
    BEAR = "Bear"


class ScenarioScope(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"
    MACRO = "macro"


class ScenarioDrivers(BaseModel):
    revenue: str | None = None
    margins: str | None = None
    cash_flow: str | None = None
    valuation: str | None = None
    growth: str | None = None
    macro: str | None = None
    sector: str | None = None
    competition: str | None = None


class InstitutionalScenario(BaseModel):
    scenario_id: str = Field(default_factory=new_id)
    type: ScenarioType
    narrative: list[str] = Field(default_factory=list)
    drivers: ScenarioDrivers = Field(default_factory=ScenarioDrivers)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str = "Medium"  # qualitative only — not a probability
    completeness: str = "Partial"
    probability: None = None  # explicitly deferred to PCI 9.4
    is_recommendation: bool = False
    is_price_prediction: bool = False
    version: str = ISI_VERSION


class ScenarioComparison(BaseModel):
    strongest_evidence: list[dict[str, Any]] = Field(default_factory=list)
    weakest_assumptions: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    common_drivers: list[str] = Field(default_factory=list)
    conflicting_drivers: list[dict[str, Any]] = Field(default_factory=list)
    why_all_remain_plausible: list[str] = Field(default_factory=list)


class ScenarioReport(BaseModel):
    report_id: str = Field(default_factory=new_id)
    scope: ScenarioScope
    entity: str
    entity_label: str | None = None
    forecast_bundle_id: str | None = None
    scenarios: list[InstitutionalScenario] = Field(default_factory=list)
    comparison: ScenarioComparison = Field(default_factory=ScenarioComparison)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    investment_thesis: str | None = None
    monitoring_events: list[dict[str, Any]] = Field(default_factory=list)
    completeness: dict[str, Any] = Field(default_factory=dict)
    freshness: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    version: str = ISI_VERSION
    chooses_single_future: bool = False
    assigns_probabilities: bool = False
    is_price_prediction: bool = False
    is_recommendation: bool = False
    note: str = (
        "Scenario evaluation only — PCI (9.4) assigns probabilities; "
        "CTI (9.3) identifies triggers that move scenarios."
    )

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["primary_question"] = PRIMARY_QUESTION
        data["does_not"] = list(NO_ISI_JUDGMENT)
        data["bull_base_bear_coverage"] = sorted(
            {
                (s.get("type") if isinstance(s, dict) else s.type.value)
                for s in (data.get("scenarios") or [])
            }
        )
        return data
