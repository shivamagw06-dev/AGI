"""IFI contracts — Forecast Bundle preparation only."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

IFI_VERSION = "0.1.0"
PROGRAMME = "Institutional Forecast Intelligence"
PROGRAMME_SHORT = "IFI"
PRIMARY_QUESTION = "What evidence-backed context should inform forward-looking institutional scenarios?"

NO_IFI_JUDGMENT = (
    "predict_stock_prices",
    "recommend_buy_sell",
    "assign_probabilities",
    "choose_bull_base_bear",
    "optimise_portfolios",
    "execute_trades",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class ForecastScope(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MARKET = "market"
    MACRO = "macro"
    THEME = "theme"


class CompletenessStatus(str, Enum):
    COMPLETE = "Complete"
    PARTIAL = "Partial"
    SPARSE = "Sparse"
    MISSING = "Missing"


class KnowledgeCompleteness(BaseModel):
    company_knowledge: CompletenessStatus = CompletenessStatus.MISSING
    historical_coverage: CompletenessStatus = CompletenessStatus.MISSING
    sector_intelligence: CompletenessStatus = CompletenessStatus.MISSING
    macro_intelligence: CompletenessStatus = CompletenessStatus.MISSING
    relationships: CompletenessStatus = CompletenessStatus.MISSING
    monitoring_current: CompletenessStatus = CompletenessStatus.MISSING
    research_current: CompletenessStatus = CompletenessStatus.MISSING
    historical_analogues: CompletenessStatus = CompletenessStatus.MISSING
    pattern_intelligence: CompletenessStatus = CompletenessStatus.MISSING
    overall: CompletenessStatus = CompletenessStatus.MISSING
    missing_evidence: list[str] = Field(default_factory=list)
    score: float = 0.0  # 0-1


class ForecastBundle(BaseModel):
    """Sole preparation object for the Scenario Engine (Sprint 9.2)."""

    bundle_id: str = Field(default_factory=new_id)
    scope: ForecastScope
    entity: str
    entity_label: str | None = None
    current_knowledge: dict[str, Any] = Field(default_factory=dict)
    historical_intelligence: dict[str, Any] = Field(default_factory=dict)
    historical_analogues: list[dict[str, Any]] = Field(default_factory=list)
    relationship_intelligence: list[dict[str, Any]] = Field(default_factory=list)
    pattern_intelligence: dict[str, Any] = Field(default_factory=dict)
    research_intelligence: dict[str, Any] = Field(default_factory=dict)
    sector_intelligence: dict[str, Any] = Field(default_factory=dict)
    market_intelligence: dict[str, Any] = Field(default_factory=dict)
    macro_intelligence: dict[str, Any] = Field(default_factory=dict)
    monitoring_events: list[dict[str, Any]] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    contradictory_evidence: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    outlook_dimensions: list[str] = Field(default_factory=list)
    confidence_inputs: dict[str, Any] = Field(default_factory=dict)
    knowledge_freshness: dict[str, Any] = Field(default_factory=dict)
    knowledge_coverage: dict[str, Any] = Field(default_factory=dict)
    completeness: KnowledgeCompleteness = Field(default_factory=KnowledgeCompleteness)
    provenance: dict[str, Any] = Field(default_factory=dict)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    version: str = IFI_VERSION
    # Explicit non-judgment markers
    chooses_scenario: bool = False
    assigns_probabilities: bool = False
    is_price_prediction: bool = False
    is_recommendation: bool = False
    note: str = (
        "Forecast preparation only — Scenario Engine (9.2) evaluates alternative futures."
    )

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["primary_question"] = PRIMARY_QUESTION
        data["does_not"] = list(NO_IFI_JUDGMENT)
        return data
