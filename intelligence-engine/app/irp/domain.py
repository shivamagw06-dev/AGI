"""Step 3 — Investment domain classification."""

from __future__ import annotations

from app.irp.models import DomainType, IntentType, ResolvedEntityPack


_INTENT_DOMAIN: dict[str, DomainType] = {
    "company_research": "company",
    "sector_research": "sector",
    "theme_research": "theme",
    "macro_research": "macro",
    "portfolio_construction": "portfolio",
    "valuation": "valuation",
    "compare_companies": "company",
    "risk_analysis": "risk",
    "earnings_analysis": "earnings",
    "prediction": "company",
    "market_outlook": "market",
    "investment_thesis": "company",
    "event_impact": "event",
    "screening": "market",
}


def classify_domain(intent: IntentType | str, entities: ResolvedEntityPack) -> DomainType:
    if entities.sector_key and intent in {"sector_research", "general_research", "market_outlook"}:
        return "sector"
    if entities.primary_ticker and intent in {
        "company_research",
        "investment_thesis",
        "valuation",
        "earnings_analysis",
        "prediction",
        "general_research",
    }:
        return "company"
    if intent == "theme_research" or (entities.themes and not entities.primary_ticker and not entities.sector_key):
        return "theme"
    return _INTENT_DOMAIN.get(str(intent), "market")
