"""Research Intelligence Engine — constants."""

from __future__ import annotations

ENGINE_CODE = "research_intelligence_engine"
VERSION = "8.4"
ENGINE_LABEL = "Institutional Research Intelligence Engine"

SECTIONS = (
    "executive",
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
)

# Forbidden recommendation language
FORBIDDEN_TOKENS = (
    "buy",
    "sell",
    "hold",
    "overweight",
    "underweight",
    "accumulate",
    "reduce",
    "strong buy",
    "strong sell",
)
