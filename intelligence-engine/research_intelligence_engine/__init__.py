"""Institutional Research Intelligence Engine (RIE) — Phase 8.4.

Consumes warehouse + UVE/HVIE/VARIE/VPAE into evidence-backed research dossiers.
Never calls vendors. Never issues BUY/SELL recommendations.
"""

from research_intelligence_engine.models import ENGINE_CODE, VERSION
from research_intelligence_engine.production import (
    ask_slice,
    business,
    capital_allocation,
    catalysts,
    company,
    confidence,
    coverage,
    dashboard,
    financial_quality,
    growth,
    health,
    monitoring,
    ownership,
    profitability,
    risk,
    section,
    timeline,
    valuation,
)

__all__ = [
    "ENGINE_CODE",
    "VERSION",
    "health",
    "company",
    "section",
    "business",
    "financial_quality",
    "growth",
    "profitability",
    "capital_allocation",
    "valuation",
    "ownership",
    "risk",
    "catalysts",
    "monitoring",
    "timeline",
    "confidence",
    "coverage",
    "dashboard",
    "ask_slice",
]
