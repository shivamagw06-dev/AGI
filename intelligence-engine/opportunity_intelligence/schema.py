"""P4.5 Opportunity Intelligence Engine — schema & constants."""

from __future__ import annotations

ENGINE_CODE = "opportunity_intelligence"
ENGINE_NAME = "Opportunity Intelligence Engine"
VERSION = "p4.5-opportunity-intelligence-v1.0.0"
PROGRAMME = "AGIB_PHASE4_INSTITUTIONAL_REASONING_LAYER"
WORKSTREAM_ID = "P4.5"
MILESTONE = "phase_4_5"

TICKER_ALIASES = {
    "TATAMOTORS": "TMPV",
    "ZOMATO": "ETERNAL",
}

IC10_UNIVERSE = (
    "HDFCBANK",
    "RELIANCE",
    "TCS",
    "ETERNAL",
    "TATAMOTORS",
    "SUNPHARMA",
    "NTPC",
    "HAL",
    "ASIANPAINT",
    "ULTRACEMCO",
)

RESEARCH_PRIORITIES = ("Critical", "High", "Medium", "Low", "Monitor")

DIMENSION_WEIGHTS: dict[str, float] = {
    "valuation": 0.20,
    "financial_momentum": 0.20,
    "ownership_momentum": 0.15,
    "corporate_momentum": 0.15,
    "sector_momentum": 0.10,
    "macro_context": 0.10,
    "catalysts": 0.10,
}

# Technical context is supporting evidence only — never dominates.
TECHNICAL_SOFT_CAP = 3.0

WATCHLIST_VIEWS = (
    "top_emerging",
    "highest_improving_fundamentals",
    "largest_valuation_compression",
    "strongest_ownership_improvement",
    "highest_catalyst_density",
    "most_positive_knowledge_delta",
    "highest_research_priority",
)

RECOMMENDATION_POLICY = "research_priority_only_no_buy_sell"
