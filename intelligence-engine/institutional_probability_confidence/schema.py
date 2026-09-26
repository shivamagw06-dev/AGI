"""IPCI contracts — scenario probabilities and independent confidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

IPCI_VERSION = "0.1.0"
PROGRAMME = "Institutional Probability & Confidence Intelligence"
PROGRAMME_SHORT = "IPCI"
PRIMARY_QUESTION = "How likely is each scenario, and how confident are we?"

NO_IPCI_JUDGMENT = (
    "predict_stock_prices",
    "recommend_buy_sell",
    "set_target_prices",
    "optimise_portfolios",
    "execute_trades",
    "guess_without_evidence",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class ScenarioProbability(BaseModel):
    scenario: str  # Bull | Base | Bear
    probability_pct: int
    supporting_evidence_level: str = "Medium"  # High | Medium | Low
    historical_analogues: int = 0
    contradictions: int = 0
    missing_evidence: int = 0
    drivers: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None


class ConfidenceBreakdown(BaseModel):
    overall_pct: int
    evidence_quality_pct: int
    historical_coverage_pct: int
    historical_analogue_strength_pct: int
    knowledge_freshness_pct: int
    knowledge_completeness_pct: int
    contradiction_level: str  # Low | Moderate | High
    missing_evidence_level: str  # Low | Moderate | High
    trigger_uncertainty_pct: int
    research_quality_pct: int
    scenario_consistency_pct: int
    components: dict[str, Any] = Field(default_factory=dict)


class ScenarioAssessment(BaseModel):
    scenario: str
    probability_pct: int
    confidence_pct: int
    supporting_evidence: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    catalysts: list[dict[str, Any]] = Field(default_factory=list)
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)


class ForecastAssessment(BaseModel):
    assessment_id: str = Field(default_factory=new_id)
    entity: str
    entity_label: str | None = None
    scope: str = "company"
    scenario_report_id: str | None = None
    forecast_bundle_id: str | None = None
    assessments: list[ScenarioAssessment] = Field(default_factory=list)
    probabilities: list[ScenarioProbability] = Field(default_factory=list)
    probability_sum_pct: int = 100
    confidence: ConfidenceBreakdown
    overall_forecast_quality_pct: int
    missing_evidence: list[str] = Field(default_factory=list)
    contradictions_summary: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    providers_queried: list[str] = Field(default_factory=list)
    prepared_at: datetime = Field(default_factory=utc_now)
    version: str = IPCI_VERSION
    is_recommendation: bool = False
    is_price_prediction: bool = False
    note: str = (
        "Probability quantifies scenario likelihood; confidence quantifies assessment certainty. "
        "FVL (9.5) will validate outcomes. No trading recommendations."
    )

    def to_public_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        data["programme"] = PROGRAMME
        data["programme_short"] = PROGRAMME_SHORT
        data["primary_question"] = PRIMARY_QUESTION
        data["does_not"] = list(NO_IPCI_JUDGMENT)
        # Convenience map
        data["distribution"] = {
            a["scenario"]: {"probability_pct": a["probability_pct"], "confidence_pct": a["confidence_pct"]}
            for a in data.get("assessments") or []
        }
        return data
