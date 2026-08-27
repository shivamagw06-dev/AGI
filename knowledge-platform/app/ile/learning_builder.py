"""Step 4 — Learning Event Builder: institutional observations, not raw numbers."""

from __future__ import annotations

from app.contracts.models import (
    Confidence,
    Importance,
    KnowledgeObject,
    LearningCategory,
    LearningEvent,
)
from app.ile.impact import ImpactAssessment
from app.ile.materiality import ScoredChange
from app.ile.policy import MaterialityTier


CATEGORY_MAP = {
    "Financial Performance": LearningCategory.FINANCIAL,
    "Valuation": LearningCategory.VALUATION,
    "Ownership": LearningCategory.OWNERSHIP,
    "Corporate": LearningCategory.CORPORATE,
    "Market": LearningCategory.MARKET,
    "Business": LearningCategory.BUSINESS,
    "General": LearningCategory.FINANCIAL,
}


def _observation(field: str, prev, new) -> str:
    try:
        p = float(prev)
        n = float(new)
        up = n > p
    except (TypeError, ValueError):
        return f"{field.replace('_', ' ').title()} changed."

    if field == "revenue_growth":
        return (
            "Revenue acceleration exceeded previous trend."
            if up
            else "Revenue growth decelerated versus prior trend."
        )
    if field == "earnings_growth":
        return "Earnings growth accelerated." if up else "Earnings growth slowed."
    if field in {"pat_margin", "ebitda_margin"}:
        return "Operating margins improved." if up else "Margins declined versus prior period."
    if field == "debt":
        return "Balance sheet deleveraged as debt declined." if not up else "Leverage increased as debt rose."
    if field == "cash":
        return "Cash flow / cash position strengthened." if up else "Cash position weakened."
    if field in {"pe", "pe_ratio"}:
        return "Valuation multiple expanded." if up else "Valuation multiple compressed."
    if field in {"price", "last_price"}:
        return "Share price moved materially."
    if field == "target_price":
        return "Analyst target price revised upward." if up else "Analyst target price revised downward."
    if field.endswith("_pct"):
        return f"{field.replace('_', ' ').title()} ownership stake changed materially."
    if field == "object_created":
        return f"New institutional {new} observed."
    if field in {"action_type", "corporate_action"}:
        return f"Corporate action observed: {new}."
    if field in {"sector", "industry"}:
        return f"Business classification updated ({field})."
    return f"{field.replace('_', ' ').title()} changed in a material way."


def _evidence(ko: KnowledgeObject) -> str:
    mapping = {
        "FinancialStatement": "Quarterly Financials",
        "CompanyProfile": "Company Profile Update",
        "MarketSnapshot": "Market Snapshot",
        "CorporateEvent": "Corporate Event / Filing",
        "CorporateAction": "Corporate Action",
        "Ownership": "Shareholding Pattern",
        "AnalystConsensus": "Analyst Consensus",
        "NewsEvent": "News Event",
    }
    return mapping.get(ko.object_type.value, ko.object_type.value)


class LearningEventBuilder:
    def build(
        self,
        ko: KnowledgeObject,
        learnable: list[ScoredChange],
        impact: ImpactAssessment,
    ) -> list[LearningEvent]:
        events: list[LearningEvent] = []
        for scored in learnable:
            mat = scored.materiality
            ch = scored.change
            importance = (
                Importance.HIGH
                if mat.tier == MaterialityTier.HIGH
                else Importance.MEDIUM
                if mat.tier == MaterialityTier.MEDIUM
                else Importance.LOW
            )
            confidence = (
                Confidence.HIGH
                if mat.score >= 80
                else Confidence.MEDIUM
                if mat.score >= 55
                else Confidence.LOW
            )
            category = CATEGORY_MAP.get(mat.category, LearningCategory.FINANCIAL)
            observation = _observation(ch.field_name, ch.previous_value, ch.new_value)
            try:
                delta = (
                    float(ch.new_value) - float(ch.previous_value)
                    if ch.previous_value is not None
                    else None
                )
            except (TypeError, ValueError):
                delta = None
            events.append(
                LearningEvent(
                    company_symbol=ko.company_symbol,
                    sector_key=ko.entity_refs.sector_key,
                    category=category,
                    category_label=mat.category,
                    importance=importance,
                    confidence=confidence,
                    field_name=ch.field_name,
                    previous_value=ch.previous_value,
                    new_value=ch.new_value,
                    delta=round(delta, 6) if delta is not None else None,
                    materiality="material",
                    materiality_score=mat.score,
                    reason=observation,
                    observation=observation,
                    evidence=_evidence(ko),
                    affected=list(impact.affected),
                    object_type=ko.object_type,
                    object_id=ko.object_id,
                    source_event_ids=list(ko.source_event_ids),
                )
            )
        return events
